"""Room lifecycle endpoints: create, join, and start a game.

Route handlers stay thin: parse input, call `app.services.room`, return the
result (`CLAUDE.md`'s folder-structure rule).
"""

from fastapi import APIRouter, HTTPException

from app.models.api import (
    CreateRoomResponse,
    JoinRoomRequest,
    JoinRoomResponse,
    StartGameRequest,
)
from app.services.room import room_store

router = APIRouter(prefix="/rooms", tags=["rooms"])


@router.post("", response_model=CreateRoomResponse)
def create_room() -> CreateRoomResponse:
    """Creates a new, empty room for a host to invite players into.

    Returns:
        The new room's code.
    """
    room = room_store.create_room()
    return CreateRoomResponse(room_code=room.state.room_code)


@router.post("/{code}/join", response_model=JoinRoomResponse)
def join_room(code: str, body: JoinRoomRequest) -> JoinRoomResponse:
    """Adds a player to a room's lobby.

    Args:
        code: The room code from the invite link.
        body: The joining player's chosen name, icon, and Industry.

    Returns:
        The new player's id and reconnect token, to be stored client-side
        and presented on every future WebSocket connection.

    Raises:
        HTTPException: 404 if the room doesn't exist; 400 if the join is
            rejected (game already started, room full, name taken).
    """
    room = room_store.get(code)
    if room is None:
        raise HTTPException(status_code=404, detail="no room with that code")
    try:
        player, token = room.join(body.name, body.icon, body.industry)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return JoinRoomResponse(
        room_code=room.state.room_code,
        player_id=player.id,
        reconnect_token=token,
        is_host=player.is_host,
    )


@router.post("/{code}/start")
async def start_game(code: str, body: StartGameRequest) -> dict[str, str]:
    """Starts a room's game. Only that room's host may call this.

    `async def` on purpose: `Room.start` schedules the room's background
    round-loop task via `asyncio.create_task`, which needs a running event
    loop. A plain `def` handler runs in FastAPI's worker threadpool instead,
    where there isn't one.

    Args:
        code: The room code.
        body: The requester's player id and reconnect token.

    Returns:
        A simple confirmation payload.

    Raises:
        HTTPException: 404 if the room doesn't exist; 400 if the start is
            rejected (bad credentials, not the host, wrong phase, too few
            or too many players).
    """
    room = room_store.get(code)
    if room is None:
        raise HTTPException(status_code=404, detail="no room with that code")
    try:
        room.start(body.player_id, body.reconnect_token)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "started"}
