"""The room WebSocket: live state sync and every player-initiated action.

The connection is authenticated once, at connect time, using the
`player_id`/`reconnect_token` pair `POST /rooms/{code}/join` returned
(passed as query params, since browsers can't set custom headers on a
WebSocket handshake). Every message received afterward on that connection
is treated as coming from that authenticated player - no per-message token
needed, the same way an HTTP session is authenticated once at login.

Each action handler below mutates room state through `app.services.room`/
`app.services.conflict_engine`, then broadcasts whatever the rest of the
table is allowed to learn about it - see each handler's comment for what's
public, what's private to the two people involved, and why (GDD.md Section 6
draws that line deliberately: only Power is public by default).
"""

from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from app.models.game import AllocationRequest
from app.models.ws import (
    AllyActionMessage,
    ProposeAllianceMessage,
    RespondAllianceMessage,
    TargetActionMessage,
)
from app.services.room import Room, room_store

router = APIRouter()


@router.websocket("/ws/rooms/{code}")
async def room_socket(websocket: WebSocket, code: str) -> None:
    """Handles one player's live connection to a room.

    Args:
        websocket: The incoming connection.
        code: The room code from the URL.
    """
    room = room_store.get(code)
    if room is None:
        await websocket.close(code=4404, reason="no room with that code")
        return

    player_id = websocket.query_params.get("player_id", "")
    token = websocket.query_params.get("token", "")
    try:
        room.authenticate(player_id, token)
    except ValueError:
        await websocket.close(code=4401, reason="invalid player id or reconnect token")
        return

    await websocket.accept()
    await room.register_connection(player_id, websocket)

    try:
        while True:
            message = await websocket.receive_json()
            await _dispatch(room, player_id, websocket, message)
    except WebSocketDisconnect:
        pass
    finally:
        await room.unregister_connection(player_id, websocket)


async def _dispatch(
    room: Room, player_id: str, websocket: WebSocket, message: dict[str, Any]
) -> None:
    """Validates and routes one incoming message, replying with `error` on any failure.

    Args:
        room: The room this connection belongs to.
        player_id: The authenticated sender.
        websocket: The sender's connection, for a direct error reply.
        message: The parsed incoming JSON message.
    """
    handler = _HANDLERS.get(message.get("type"))
    if handler is None:
        await websocket.send_json(
            {"type": "error", "message": f"unknown message type '{message.get('type')}'"}
        )
        return
    try:
        await handler(room, player_id, message)
    except ValidationError as exc:
        await websocket.send_json({"type": "error", "message": f"invalid request: {exc}"})
    except ValueError as exc:
        await websocket.send_json({"type": "error", "message": str(exc)})


async def _handle_submit_allocation(room: Room, player_id: str, message: dict[str, Any]) -> None:
    allocation = AllocationRequest.model_validate(message.get("allocation", {}))
    room.submit_allocation(player_id, allocation)


async def _handle_propose_alliance(room: Room, player_id: str, message: dict[str, Any]) -> None:
    body = ProposeAllianceMessage.model_validate(message)
    proposal = room.propose_alliance(player_id, body.to_id, body.jv_industry, body.pact_declared)
    # Private: only the invited player needs to see an incoming proposal.
    await room.send_to(
        body.to_id,
        {
            "type": "alliance_proposal",
            "proposal_id": proposal.id,
            "from_id": player_id,
            "jv_industry": body.jv_industry,
            "pact_declared": body.pact_declared,
        },
    )


async def _handle_respond_alliance(room: Room, player_id: str, message: dict[str, Any]) -> None:
    body = RespondAllianceMessage.model_validate(message)
    proposal = room.pending_proposals.get(body.proposal_id)
    from_id = proposal.from_id if proposal is not None else None

    alliance = room.respond_alliance(player_id, body.proposal_id, body.accept)
    if from_id is not None:
        # Private: the proposer learns the outcome directly; nobody else at
        # the table is told an alliance was even offered (GDD.md Section 6).
        await room.send_to(
            from_id,
            {
                "type": "alliance_response",
                "to_id": player_id,
                "accepted": alliance is not None,
            },
        )
    if alliance is not None:
        await room.broadcast_state()  # Power/declared-ally visibility may have shifted


async def _handle_top_up_jv(room: Room, player_id: str, message: dict[str, Any]) -> None:
    body = AllyActionMessage.model_validate(message)
    room.top_up_jv(player_id, body.ally_id)
    await room.broadcast_state()


async def _handle_drain_jv(room: Room, player_id: str, message: dict[str, Any]) -> None:
    body = AllyActionMessage.model_validate(message)
    payout = room.drain_jv(player_id, body.ally_id)
    # Public: "a drain is public... everyone at the table sees the pot move"
    # (GDD.md Section 5 item 5 / 7), not a private update between the pair.
    await room.broadcast(
        {
            "type": "jv_drained",
            "drainer_id": player_id,
            "partner_id": body.ally_id,
            "amount": payout,
        }
    )
    await room.broadcast_state()


async def _handle_break_pact(room: Room, player_id: str, message: dict[str, Any]) -> None:
    body = AllyActionMessage.model_validate(message)
    room.break_pact(player_id, body.ally_id)
    await room.broadcast_state()


async def _handle_hostile_bid(room: Room, player_id: str, message: dict[str, Any]) -> None:
    body = TargetActionMessage.model_validate(message)
    result = room.hostile_bid(player_id, body.target_id)
    await room.broadcast(_combat_result_payload("hostile_bid_result", result))
    await room.broadcast_state()


async def _handle_counter_attack(room: Room, player_id: str, _message: dict[str, Any]) -> None:
    result = room.counter_attack(player_id)
    await room.broadcast(_combat_result_payload("counter_attack_result", result))
    await room.broadcast_state()


async def _handle_audit(room: Room, player_id: str, message: dict[str, Any]) -> None:
    body = TargetActionMessage.model_validate(message)
    result = room.audit(player_id, body.target_id)
    # Private: revealing a rival's true numbers is the entire point (GDD.md
    # Section 6/8.3) - broadcasting it would make Audit pointless to pay for.
    await room.send_to(
        player_id,
        {
            "type": "audit_result",
            "target_id": result.target_id,
            "cash": result.cash,
            "company": result.company,
            "real_estate": result.real_estate,
            "gold": result.gold,
            "debt": result.debt,
        },
    )
    await room.broadcast_state()


def _combat_result_payload(message_type: str, result: object) -> dict[str, Any]:
    return {
        "type": message_type,
        "attacker_id": result.attacker_id,
        "target_id": result.target_id,
        "success": result.success,
        "amount": result.amount,
    }


async def _handle_recruit_co_founder(room: Room, player_id: str, message: dict[str, Any]) -> None:
    body = TargetActionMessage.model_validate(message)
    room.recruit_co_founder(player_id, body.target_id)
    await room.broadcast_state()


async def _handle_buy_out_co_founder(room: Room, player_id: str, message: dict[str, Any]) -> None:
    body = TargetActionMessage.model_validate(message)
    cost = room.buy_out_co_founder(player_id, body.target_id)
    await room.broadcast(
        {
            "type": "co_founder_bought_out",
            "host_id": player_id,
            "co_founder_id": body.target_id,
            "cost": cost,
        }
    )
    await room.broadcast_state()


async def _handle_back_player(room: Room, player_id: str, message: dict[str, Any]) -> None:
    body = TargetActionMessage.model_validate(message)
    room.back_player(player_id, body.target_id)
    await room.broadcast_state()


async def _handle_initiate_kick_vote(room: Room, player_id: str, message: dict[str, Any]) -> None:
    body = TargetActionMessage.model_validate(message)
    room.initiate_kick_vote(player_id, body.target_id)
    await room.broadcast_state()


async def _handle_cast_kick_vote(room: Room, player_id: str, message: dict[str, Any]) -> None:
    body = TargetActionMessage.model_validate(message)
    room.cast_kick_vote(player_id, body.target_id)
    await room.broadcast_state()


_HANDLERS = {
    "submit_allocation": _handle_submit_allocation,
    "propose_alliance": _handle_propose_alliance,
    "respond_alliance": _handle_respond_alliance,
    "top_up_jv": _handle_top_up_jv,
    "drain_jv": _handle_drain_jv,
    "break_pact": _handle_break_pact,
    "hostile_bid": _handle_hostile_bid,
    "counter_attack": _handle_counter_attack,
    "audit": _handle_audit,
    "recruit_co_founder": _handle_recruit_co_founder,
    "buy_out_co_founder": _handle_buy_out_co_founder,
    "back_player": _handle_back_player,
    "initiate_kick_vote": _handle_initiate_kick_vote,
    "cast_kick_vote": _handle_cast_kick_vote,
}
