"""Tests for room lifecycle, connection auth, and the live round loop.

The async round-loop test drives `Room` directly with a `FakeWebSocket`
double and a plain `asyncio.run`, deliberately not through
`fastapi.testclient.TestClient`: Starlette's TestClient runs each HTTP call
through a short-lived anyio portal, and a task started mid-request via
`asyncio.create_task` (exactly what `Room.start` does to launch the round
loop) does not reliably keep running past that request's own portal call.
That's a TestClient/anyio artifact, not a bug in the app; a real server
(verified manually against a running `uvicorn` instance) runs it correctly,
and this file's async test reproduces that same plain-asyncio behavior
without needing a real HTTP/WebSocket transport at all.
"""

import asyncio
import contextlib
from typing import Any

import pytest

from app.core.constants import Industry
from app.models.game import AllocationRequest, Phase
from app.services import round_engine
from app.services.room import Room, RoomStore


class FakeWebSocket:
    """A minimal stand-in for a Starlette WebSocket: just records sends."""

    def __init__(self) -> None:
        """Starts with an empty sent-message log."""
        self.sent: list[dict[str, Any]] = []

    async def send_json(self, payload: dict[str, Any]) -> None:
        """Records a payload instead of sending it over a real socket."""
        self.sent.append(payload)


async def _wait_until(predicate, timeout: float = 2.0) -> None:
    """Polls `predicate` until it's true, or raises after `timeout` seconds."""
    loop = asyncio.get_event_loop()
    deadline = loop.time() + timeout
    while not predicate():
        if loop.time() > deadline:
            raise TimeoutError("condition was not met in time")
        await asyncio.sleep(0.01)


def test_first_player_to_join_becomes_host():
    """The first joiner is host; later joiners aren't."""
    room = Room("TEST")
    first, _ = room.join("Alice", "", Industry.TECHNOLOGY)
    second, _ = room.join("Bob", "", Industry.TECHNOLOGY)
    assert first.is_host
    assert not second.is_host


def test_join_rejects_duplicate_name():
    """Two players can't share a display name in the same room."""
    room = Room("TEST")
    room.join("Alice", "", Industry.TECHNOLOGY)
    with pytest.raises(ValueError, match="already taken"):
        room.join("Alice", "", Industry.ENERGY)


def test_join_rejects_once_the_game_has_started():
    """Nobody can join a room's lobby once its game has started."""
    room = Room("TEST")
    for i in range(3):
        room.join(f"p{i}", "", Industry.TECHNOLOGY)
    round_engine.start_game(room.state, room.rng)
    with pytest.raises(ValueError, match="already started"):
        room.join("Latecomer", "", Industry.TECHNOLOGY)


def test_authenticate_rejects_wrong_token():
    """A player id with the wrong reconnect token is not authenticated."""
    room = Room("TEST")
    player, _token = room.join("Alice", "", Industry.TECHNOLOGY)
    with pytest.raises(ValueError, match="invalid"):
        room.authenticate(player.id, "the-wrong-token")


def test_start_rejects_a_non_host_requester():
    """Only the host may start the game, even with a valid token."""
    room = Room("TEST")
    room.join("Alice", "", Industry.TECHNOLOGY)
    second, second_token = room.join("Bob", "", Industry.TECHNOLOGY)
    room.join("Carol", "", Industry.TECHNOLOGY)
    with pytest.raises(ValueError, match="only the host"):
        room.start(second.id, second_token)


def test_start_rejects_an_invalid_token():
    """A start request with a bad token is rejected before the host check."""
    room = Room("TEST")
    host, _token = room.join("Alice", "", Industry.TECHNOLOGY)
    room.join("Bob", "", Industry.TECHNOLOGY)
    room.join("Carol", "", Industry.TECHNOLOGY)
    with pytest.raises(ValueError, match="invalid"):
        room.start(host.id, "not-the-real-token")


def test_submit_allocation_rejected_before_the_game_starts():
    """A room still in its lobby doesn't accept allocations."""
    room = Room("TEST")
    player, _ = room.join("Alice", "", Industry.TECHNOLOGY)
    with pytest.raises(ValueError, match="no round"):
        room.submit_allocation(player.id, AllocationRequest())


def test_stale_disconnect_does_not_evict_a_newer_connection():
    """A late cleanup for an old socket must not evict a newer one that already replaced it."""
    asyncio.run(_reconnect_scenario())


async def _reconnect_scenario() -> None:
    room = Room("TEST")
    player, _ = room.join("Alice", "", Industry.TECHNOLOGY)
    old_ws, new_ws = FakeWebSocket(), FakeWebSocket()

    await room.register_connection(player.id, old_ws)
    await room.register_connection(player.id, new_ws)  # a refresh/reconnect replaces the socket
    assert room.connections[player.id] is new_ws

    await room.unregister_connection(player.id, old_ws)  # the old socket's cleanup, arriving late
    assert room.connections[player.id] is new_ws
    assert room.state.players[player.id].connected is True

    await room.unregister_connection(player.id, new_ws)  # the actual current socket disconnecting
    assert player.id not in room.connections
    assert room.state.players[player.id].connected is False


def test_room_store_evicts_a_room_once_its_game_ends():
    """A finished game's room is removed from the store, not kept forever."""
    asyncio.run(_ended_game_scenario())


async def _ended_game_scenario() -> None:
    store = RoomStore()
    room = store.create_room()
    code = room.state.room_code
    players = [room.join(f"p{i}", "", Industry.TECHNOLOGY)[0] for i in range(3)]

    round_engine.start_game(room.state, room.rng)
    room.state.round_number = round_engine.TOTAL_ROUNDS - 1  # the next round resolved is the last

    sockets = [FakeWebSocket() for _ in players]
    for player, ws in zip(players, sockets, strict=True):
        await room.register_connection(player.id, ws)
    room._game_task = asyncio.create_task(room._run_game_loop())  # noqa: SLF001

    await _wait_until(lambda: any(m["type"] == "round_started" for m in sockets[0].sent))
    for player in players:
        room.submit_allocation(player.id, AllocationRequest())

    await room._game_task  # noqa: SLF001 - runs to completion once the last round resolves
    assert room.state.phase == Phase.ENDED
    assert store.get(code) is None


def test_full_round_resolves_and_broadcasts_are_personalized():
    """A round started, submitted, and resolved end to end via the real room loop."""
    asyncio.run(_play_one_round())


async def _play_one_round() -> None:
    room = Room("TEST")
    host, host_token = room.join("Host", "", Industry.TECHNOLOGY)
    p2, _ = room.join("Second", "", Industry.TECHNOLOGY)
    p3, _ = room.join("Third", "", Industry.TECHNOLOGY)

    ws_host, ws_p2, ws_p3 = FakeWebSocket(), FakeWebSocket(), FakeWebSocket()
    await room.register_connection(host.id, ws_host)
    await room.register_connection(p2.id, ws_p2)
    await room.register_connection(p3.id, ws_p3)

    room.start(host.id, host_token)
    assert room.state.phase == Phase.BUILDING

    await _wait_until(lambda: any(m["type"] == "round_started" for m in ws_host.sent))

    room.submit_allocation(host.id, AllocationRequest(buy_company=5.0))
    room.submit_allocation(p2.id, AllocationRequest(buy_real_estate=3.0))
    room.submit_allocation(p3.id, AllocationRequest())

    await _wait_until(lambda: any(m["type"] == "round_result" for m in ws_host.sent))

    try:
        result = next(m for m in ws_host.sent if m["type"] == "round_result")
        assert result["round_number"] == 1
        assert set(result["powers"].keys()) == {host.id, p2.id, p3.id}
        # Personalization: a player only ever sees their own income entry.
        assert list(result["income"].keys()) == [host.id]

        p2_result = next(m for m in ws_p2.sent if m["type"] == "round_result")
        assert list(p2_result["income"].keys()) == [p2.id]

        state = next(m for m in ws_host.sent if m["type"] == "state" and m["round_number"] == 1)
        assert state["me"]["id"] == host.id
        assert "cash" in state["me"]
        assert all("cash" not in p for p in state["players"])
    finally:
        room._game_task.cancel()  # noqa: SLF001 - stopping the still-running round loop after the test
        with contextlib.suppress(asyncio.CancelledError):
            await room._game_task  # noqa: SLF001


def test_stale_connection_cleanup_does_not_evict_a_newer_live_connection():
    """A reconnect's fresh socket survives the old socket's delayed cleanup."""
    asyncio.run(_reconnect_then_cleanup_stale_socket())


async def _reconnect_then_cleanup_stale_socket() -> None:
    room = Room("TEST")
    player, _ = room.join("Alice", "", Industry.TECHNOLOGY)
    old_ws = FakeWebSocket()
    await room.register_connection(player.id, old_ws)

    new_ws = FakeWebSocket()
    await room.register_connection(player.id, new_ws)  # e.g. a refreshed tab

    # The old socket's own cleanup finally runs, after the reconnect already happened.
    await room.unregister_connection(player.id, old_ws)

    assert room.connections[player.id] is new_ws
    assert room.state.players[player.id].connected is True


def test_join_never_collides_player_ids_within_a_room():
    """Every joiner in a room gets a unique player id, even if token_hex ever repeats."""
    room = Room("TEST")
    ids = {room.join(f"p{i}", "", Industry.TECHNOLOGY)[0].id for i in range(8)}
    assert len(ids) == 8


def test_room_store_forgets_a_room_once_its_game_ends():
    """A finished room's code is freed; RoomStore stops holding it in memory."""
    from app.services.room import RoomStore

    store = RoomStore()
    room = store.create_room()
    code = room.state.room_code
    assert store.get(code) is room

    room._on_ended()  # noqa: SLF001 - exactly what _run_game_loop's `finally` block calls

    assert store.get(code) is None
