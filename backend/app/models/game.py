"""Domain models: a player's financial position and one room's game state.

These are pure data plus small derived queries (`total_power`, `is_broke`).
Anything that mutates state (income, allocation, combat) lives in
`app.services.round_engine`, per `CLAUDE.md`'s "route handlers/models stay
thin, business logic belongs in services" rule.
"""

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field

from app.core.constants import (
    DISENGAGED_CASH_THRESHOLD,
    DISENGAGED_COMPANY_THRESHOLD,
    STARTING_CASH,
    STARTING_COMPANY,
    Industry,
)

Direction = Literal["long", "short"]


class Phase(StrEnum):
    """Which stage of the game a room is in."""

    LOBBY = "lobby"
    BUILDING = "building"
    CONFLICT = "conflict"
    FINAL = "final"
    ENDED = "ended"


class MarketPosition(BaseModel):
    """A player's long or short bet on one Industry's scenario delta."""

    direction: Direction
    principal: float = 0.0


class Player(BaseModel):
    """One player's full financial position.

    Power Cards are out of scope for this slice (GDD.md Section 10 defers
    them to v2 outright) and deliberately have no fields here.
    """

    id: str
    name: str
    icon: str = ""
    industry: Industry
    cash: float = STARTING_CASH
    company: float = STARTING_COMPANY
    real_estate: float = 0.0
    gold: float = 0.0
    bank_deposit: float = 0.0
    debt: float = 0.0
    market_positions: dict[Industry, MarketPosition] = Field(default_factory=dict)
    is_host: bool = False
    connected: bool = True
    last_shares: tuple[float, float, float] | None = Field(
        default=None,
        description=(
            "Most recent (company_share, re_share, cash_share) split of that "
            "round's available cash, used to replay a hold when a player's "
            "timer expires (GAMEPLAY.md Section 2). None until their first "
            "allocation."
        ),
    )
    captured: float = Field(
        default=0.0,
        description="Power captured from successful Hostile Bids/counter-attacks (GDD.md 3).",
    )
    jv_value_share: float = Field(
        default=0.0,
        description=(
            "This player's half of every live Joint Venture pot they're part "
            "of. A cached total, kept in sync by conflict_engine whenever a "
            "pot forms, tops up, revalues, or drains, so total_power() stays "
            "self-contained instead of needing a live reference to "
            "GameState.alliances."
        ),
    )
    shielded_until_round: int = Field(
        default=0,
        description="A successful hostile bid against this player shields them through this round.",
    )
    raid_count: int = Field(
        default=0,
        description="Successful Hostile Bids landed as the attacker, this game (raid fatigue).",
    )
    drain_count: int = Field(
        default=0, description="Proven Joint Venture betrayals, across any partner."
    )
    pact_break_count: int = Field(
        default=0, description="Declared Defense Pacts this player has broken."
    )
    is_raider: bool = Field(
        default=False,
        description=(
            "Secretly wins if raider_target_id ends the game failed, not by own Power (GDD.md 8.2)."
        ),
    )
    raider_target_id: str | None = Field(
        default=None, description="This Raider's secretly assigned target. Known only to them."
    )
    missed_rounds: int = Field(
        default=0,
        description="Rounds this player's allocation was auto-defaulted (timeout or rejected).",
    )
    afk_kicked: bool = Field(
        default=False,
        description=(
            "Voted out for being disconnected (GDD.md Section 4.1). Routed through the same "
            "Board Observer path as bankruptcy, not a separate status - see is_broke()."
        ),
    )
    co_founder_of: str | None = Field(
        default=None, description="The living host player id this Board Observer co-founds for."
    )
    co_founder_equity: float = Field(
        default=0.0,
        description="This co-founder's live equity stake, marked to the host's Company.",
    )
    backing_id: str | None = Field(
        default=None,
        description="A Board Observer's social pick for the Final Round tiebreak (GDD.md 8.4).",
    )

    def total_power(self) -> float:
        """Sums every Power component this slice models (GDD.md Section 3).

        Returns:
            The player's current total Power.
        """
        market_value = sum(p.principal for p in self.market_positions.values())
        return (
            self.cash
            + self.company
            + self.real_estate
            + self.gold
            + self.bank_deposit
            + market_value
            + self.captured
            + self.jv_value_share
            + self.co_founder_equity
            - self.debt
        )

    def is_broke(self) -> bool:
        """Reports whether this player has next to nothing left to act with.

        A player voted out for being disconnected counts as broke here
        regardless of actual wealth (GDD.md Section 4.1): it routes them
        through the same Board Observer path a bankrupted player uses,
        rather than a separate status, so recruitment, backing, and the
        Final Round tiebreak all just work.

        Returns:
            True if disconnected-and-voted-out, or both cash and company
            are below the disengagement floor.
        """
        return self.afk_kicked or (
            self.cash < DISENGAGED_CASH_THRESHOLD and self.company < DISENGAGED_COMPANY_THRESHOLD
        )


class JVPot(BaseModel):
    """A Joint Venture's shared position in one Industry (GDD.md Section 5 item 5)."""

    industry: Industry
    value: float
    contributed_each: float


class Alliance(BaseModel):
    """The combined Joint Venture + Defense Pact relationship between two players.

    GDD.md Section 9: kept as one relationship sharing one `MAX_ALLIES` cap,
    not two independent ones. `jv` is None if this alliance is a pure
    Defense Pact with no shared position; `pact_declared` is None if it's a
    pure JV with no defense commitment at all.
    """

    id: str
    player_a: str
    player_b: str
    jv: JVPot | None = None
    pact_declared: bool | None = None
    pending_pact_break_by: str | None = Field(
        default=None,
        description="A declared pact's breakup, initiated by this player, takes effect next round.",
    )

    def other(self, player_id: str) -> str:
        """Returns the partner's id from this player's perspective.

        Args:
            player_id: One side of this alliance.

        Returns:
            The other side's player id.
        """
        return self.player_b if player_id == self.player_a else self.player_a


def alliance_id(player_a: str, player_b: str) -> str:
    """Builds the canonical, order-independent id for a pair of players.

    Args:
        player_a: One player's id.
        player_b: The other player's id.

    Returns:
        A stable id identical regardless of argument order.
    """
    return ":".join(sorted((player_a, player_b)))


class PublicPlayerView(BaseModel):
    """What every player is allowed to see about another player, always.

    GDD.md Section 6: only Power is shown, exactly, always; everything else
    (cash, Company, Real Estate, gold, debt, Market positions) is genuinely
    unknown unless it passes through an Audit. A **declared** Defense Pact
    is the one deliberate exception: "the one exception that's automatically
    public, since the deterrent only works if it's visible" - so who a
    player has declared with is here, but nothing about a covert pact is.
    """

    id: str
    name: str
    icon: str
    industry: Industry
    power: float
    is_host: bool
    connected: bool
    shielded: bool
    declared_allies: list[str] = Field(default_factory=list)
    is_broke: bool = False
    co_founder_of: str | None = None
    missed_rounds: int = 0
    afk_kicked: bool = False

    @classmethod
    def of(
        cls, player: Player, current_round: int, declared_allies: list[str]
    ) -> "PublicPlayerView":
        """Builds the public view of a player from their full server state.

        Args:
            player: The player's full, authoritative state.
            current_round: The room's current round number, to derive
                whether the Post-Attack Shield is still active.
            declared_allies: Player ids of this player's declared Defense
                Pact partners (public by design; covert ones are excluded).

        Returns:
            The subset of it every other player is allowed to see.
        """
        return cls(
            id=player.id,
            name=player.name,
            icon=player.icon,
            industry=player.industry,
            power=player.total_power(),
            is_host=player.is_host,
            connected=player.connected,
            # `shielded_until_round` defaults to 0, same as `current_round`
            # before round 1 resolves - without the `> 0` guard, every
            # player would briefly show as shielded at game start.
            shielded=player.shielded_until_round > 0
            and current_round <= player.shielded_until_round,
            declared_allies=declared_allies,
            is_broke=player.is_broke(),
            co_founder_of=player.co_founder_of,
            missed_rounds=player.missed_rounds,
            afk_kicked=player.afk_kicked,
        )


class AllocationRequest(BaseModel):
    """One player's explicit choice for what to do with this round's cash.

    Applied in this order by `round_engine.apply_allocation`: liquidations
    and the loan draw run first (both add to spendable cash), then the
    buy-side fields are validated against whatever cash that produced. A
    player who lets their timer run out never submits one of these at all;
    `round_engine.default_hold_allocation` builds one for them instead,
    replaying their last real split (GAMEPLAY.md Section 2).
    """

    liquidate_real_estate: float = Field(default=0.0, ge=0.0)
    liquidate_gold: float = Field(default=0.0, ge=0.0)
    loan_draw: float = Field(default=0.0, ge=0.0)
    buy_company: float = Field(default=0.0, ge=0.0)
    buy_real_estate: float = Field(default=0.0, ge=0.0)
    buy_gold: float = Field(default=0.0, ge=0.0)
    market_industry: Industry | None = None
    market_direction: Direction | None = None
    market_amount: float = Field(default=0.0, ge=0.0)
    bank_deposit: float = Field(default=0.0, ge=0.0)
    loan_repay: float = Field(default=0.0, ge=0.0)


class ScenarioResult(BaseModel):
    """One round's drawn scenario, resolved to actual rolled deltas."""

    text: str
    industry_deltas: dict[Industry, float] = Field(default_factory=dict)
    gold_delta: float = 0.0


class GameState(BaseModel):
    """The full authoritative state of one room's game."""

    room_code: str
    phase: Phase = Phase.LOBBY
    round_number: int = 0
    building_phase_length: int | None = None  # rolled at start, never shown to players
    players: dict[str, Player] = Field(default_factory=dict)
    bank_pool: float = 0.0
    scenario_history: list[ScenarioResult] = Field(default_factory=list)
    alliances: dict[str, Alliance] = Field(default_factory=dict)
    winner_id: str | None = Field(
        default=None, description="Set once Phase.ENDED: highest Power, ties broken by backing."
    )

    def alliances_of(self, player_id: str) -> list[Alliance]:
        """Every alliance a player currently has, in either relationship slot.

        Args:
            player_id: The player to look up.

        Returns:
            That player's active alliances (at most `MAX_ALLIES` of them).
        """
        return [a for a in self.alliances.values() if player_id in (a.player_a, a.player_b)]


class RoundSummary(BaseModel):
    """Broadcastable result of resolving one round, for the room to send out."""

    round_number: int
    phase: Phase
    scenario: ScenarioResult
    income: dict[str, float] = Field(default_factory=dict)
    eroded_idle_cash: dict[str, float] = Field(default_factory=dict)
    powers: dict[str, float] = Field(default_factory=dict)
    held: list[str] = Field(default_factory=list)
