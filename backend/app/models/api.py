"""Request/response wire schemas for the HTTP room API.

Kept separate from `app.models.game`'s domain models: these describe what
crosses the HTTP boundary, not the server's authoritative game state.
"""

from pydantic import BaseModel, Field

from app.core.constants import Industry


class CreateRoomResponse(BaseModel):
    """Returned after creating a new, empty room."""

    room_code: str


class JoinRoomRequest(BaseModel):
    """A player's chosen identity when joining a room's lobby."""

    name: str = Field(min_length=1, max_length=24)
    icon: str = Field(default="", max_length=8)
    industry: Industry


class JoinRoomResponse(BaseModel):
    """Returned after successfully joining a room."""

    room_code: str
    player_id: str
    reconnect_token: str
    is_host: bool


class StartGameRequest(BaseModel):
    """Credentials proving the caller is the room's host."""

    player_id: str
    reconnect_token: str
