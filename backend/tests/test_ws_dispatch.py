"""Tests for the WebSocket message dispatch layer in `app.api.ws`.

Drives `_dispatch` directly against a `Room` and `FakeWebSocket`s, the same
pattern `test_room.py` uses for the round loop: real validation and
routing logic, no actual network socket needed. Everything below Room/
conflict_engine's own mechanics is already covered by
`test_room.py`/`test_conflict_engine.py`; this file is specifically about
what `ws.py` adds on top - request validation, and which reveals are
public broadcasts versus private replies (GDD.md Section 6).
"""

import asyncio
import contextlib
from typing import Any

from app.api.ws import _dispatch
from app.core.constants import Industry
from app.models.game import Phase
from app.services.room import Room


class FakeWebSocket:
    """A minimal stand-in for a Starlette WebSocket: just records sends."""

    def __init__(self) -> None:
        """Starts with an empty sent-message log."""
        self.sent: list[dict[str, Any]] = []

    async def send_json(self, payload: dict[str, Any]) -> None:
        """Records a payload instead of sending it over a real socket."""
        self.sent.append(payload)


async def _three_player_room() -> tuple[Room, dict[str, str], dict[str, FakeWebSocket]]:
    """Builds a started room with 3 connected players, ready to act.

    Runs the real background round loop (`Room.start`), so it's only safe
    for tests that don't also manually rewrite `room.state.phase`: the loop
    reads and advances that same phase on its own schedule, and the two
    would race. Tests that need a specific phase without the loop running
    should use `_three_player_room_no_loop` instead.
    """
    room, tokens, sockets = await _three_player_room_no_loop()
    host_id = next(pid for pid in tokens if room.state.players[pid].is_host)
    room.start(host_id, tokens[host_id])
    return room, tokens, sockets


async def _three_player_room_no_loop() -> tuple[Room, dict[str, str], dict[str, FakeWebSocket]]:
    """Builds a room with 3 connected players, still in the lobby, no round loop running."""
    room = Room("TEST")
    tokens: dict[str, str] = {}
    sockets: dict[str, FakeWebSocket] = {}
    for name in ("Alice", "Bob", "Carol"):
        player, token = room.join(name, "", Industry.TECHNOLOGY)
        tokens[player.id] = token
        sockets[player.id] = FakeWebSocket()
        await room.register_connection(player.id, sockets[player.id])
    return room, tokens, sockets


async def _cleanup(room: Room) -> None:
    """Stops the room's background round loop so the event loop can close cleanly."""
    if room._game_task is not None:  # noqa: SLF001
        room._game_task.cancel()  # noqa: SLF001
        with contextlib.suppress(asyncio.CancelledError):
            await room._game_task  # noqa: SLF001


def test_unknown_message_type_gets_an_error_reply():
    """An unrecognized message type gets an `error` reply, not a silent drop or crash."""
    asyncio.run(_unknown_message_scenario())


async def _unknown_message_scenario() -> None:
    room, _tokens, sockets = await _three_player_room()
    player_id, ws = next(iter(sockets.items()))

    await _dispatch(room, player_id, ws, {"type": "not_a_real_action"})

    assert ws.sent[-1]["type"] == "error"
    await _cleanup(room)


def test_alliance_proposal_is_private_then_broadcasts_on_acceptance():
    """A proposal reaches only the invited player; acceptance updates everyone's state."""
    asyncio.run(_alliance_scenario())


async def _alliance_scenario() -> None:
    room, _tokens, sockets = await _three_player_room()
    a_id, b_id, c_id = sockets.keys()
    for socket in sockets.values():
        socket.sent.clear()

    await _dispatch(
        room,
        a_id,
        sockets[a_id],
        {"type": "propose_alliance", "to_id": b_id, "jv_industry": None, "pact_declared": True},
    )

    # Only b (the invitee) was told; a and c heard nothing about it.
    assert any(m["type"] == "alliance_proposal" for m in sockets[b_id].sent)
    assert not any(m["type"] == "alliance_proposal" for m in sockets[a_id].sent)
    assert not any(m["type"] == "alliance_proposal" for m in sockets[c_id].sent)

    proposal_id = next(m for m in sockets[b_id].sent if m["type"] == "alliance_proposal")[
        "proposal_id"
    ]
    for socket in sockets.values():
        socket.sent.clear()

    await _dispatch(
        room,
        b_id,
        sockets[b_id],
        {"type": "respond_alliance", "proposal_id": proposal_id, "accept": True},
    )

    assert any(m["type"] == "alliance_response" and m["accepted"] for m in sockets[a_id].sent)
    # Forming the alliance changes declared_allies/Power visibility for
    # everyone, so a fresh state snapshot goes to the whole room, not just
    # the two partners.
    assert all(any(m["type"] == "state" for m in s.sent) for s in sockets.values())
    await _cleanup(room)


def test_audit_result_is_private_to_the_auditor():
    """An Audit's revealed numbers go only to the auditor, never to the target or anyone else."""
    asyncio.run(_audit_scenario())


async def _audit_scenario() -> None:
    room, _tokens, sockets = await _three_player_room()
    auditor_id, target_id, bystander_id = sockets.keys()
    for socket in sockets.values():
        socket.sent.clear()

    await _dispatch(
        room, auditor_id, sockets[auditor_id], {"type": "audit", "target_id": target_id}
    )

    assert any(m["type"] == "audit_result" for m in sockets[auditor_id].sent)
    assert not any(m["type"] == "audit_result" for m in sockets[target_id].sent)
    assert not any(m["type"] == "audit_result" for m in sockets[bystander_id].sent)
    await _cleanup(room)


def test_hostile_bid_rejected_outside_conflict_phase():
    """A Hostile Bid attempted during the Building Phase is rejected, not silently allowed."""
    asyncio.run(_hostile_bid_too_early_scenario())


async def _hostile_bid_too_early_scenario() -> None:
    room, _tokens, sockets = await _three_player_room()
    attacker_id, target_id, _ = sockets.keys()
    for socket in sockets.values():
        socket.sent.clear()

    await _dispatch(
        room, attacker_id, sockets[attacker_id], {"type": "hostile_bid", "target_id": target_id}
    )

    assert sockets[attacker_id].sent[-1]["type"] == "error"
    await _cleanup(room)


def test_hostile_bid_result_is_broadcast_to_the_whole_room():
    """Once the Conflict Phase is open, a resolved Hostile Bid is public to everyone connected."""
    asyncio.run(_hostile_bid_scenario())


async def _hostile_bid_scenario() -> None:
    room, _tokens, sockets = await _three_player_room_no_loop()
    attacker_id, target_id, _bystander_id = sockets.keys()
    room.state.phase = Phase.CONFLICT
    room.state.round_number = 6  # a round number the Conflict Phase could realistically be at
    room.state.players[attacker_id].cash = 1000.0
    for socket in sockets.values():
        socket.sent.clear()

    await _dispatch(
        room, attacker_id, sockets[attacker_id], {"type": "hostile_bid", "target_id": target_id}
    )

    for socket in sockets.values():
        assert any(m["type"] == "hostile_bid_result" for m in socket.sent)
