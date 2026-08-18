"""Request wire schemas for player-initiated WebSocket actions.

Kept separate from `app.models.api` (the HTTP boundary) and
`app.models.game` (server-authoritative state): these describe what a
client can ask the room to do over its live connection.
"""

from pydantic import BaseModel

from app.core.constants import Industry


class ProposeAllianceMessage(BaseModel):
    """A request to invite another player into a Joint Venture and/or Defense Pact."""

    to_id: str
    jv_industry: Industry | None = None
    pact_declared: bool | None = None


class RespondAllianceMessage(BaseModel):
    """A response to a pending alliance invite."""

    proposal_id: str
    accept: bool


class AllyActionMessage(BaseModel):
    """A request naming one existing ally: top up, drain, or break with them."""

    ally_id: str


class TargetActionMessage(BaseModel):
    """A request naming one other player: a Hostile Bid target, or an Audit target."""

    target_id: str
