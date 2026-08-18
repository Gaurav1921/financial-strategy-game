"""Round resolution: the per-round economic loop, every phase.

Ports the math `sim/human_sim.py` already validated (see
`docs/BALANCE_TESTING.md`) into a form driven by explicit player actions
instead of bot archetypes. Every function here takes and mutates a
`GameState`/`Player` passed in explicitly, no module-level game state, so
each step is independently unit-testable (see `backend/tests/test_round_engine.py`).

Resolves Income -> Allocate -> Market re-price -> Taxes every round
(GDD.md Section 4). Hostile Bids, counter-attacks, Joint Ventures, Defense
Pacts, and Audit are player-triggered actions the room resolves immediately
through `app.services.conflict_engine`, not part of this per-round loop -
this module calls into it, and into `app.services.endgame_engine`, only for
the pieces that *are* automatic and round-timed: finalizing a declared pact
break at the start of a round, marking Joint Venture pots to market, and
running each co-founder's Real Estate steering. Power Cards are still a
later build pass (GDD.md Section 10 defers them to v2 outright).
"""

import random

from app.core.constants import (
    BANK_DEPOSIT_RATE,
    BANK_POOL_PER_PLAYER,
    BANKRUPTCY_LIQUIDATION_PCT,
    BUILDING_PHASE_RANGE,
    COMPANY_INCOME_RATE,
    GOLD_BASE_RANGE,
    GOLD_LIQUIDATION_HAIRCUT,
    GOLD_TIER_RANGES,
    IDLE_CASH_EROSION_RATE,
    IDLE_CASH_EROSION_THRESHOLD,
    LOAN_INTEREST_BASE,
    LOAN_RISK_PREMIUM,
    MAX_PLAYERS,
    MIN_PLAYERS,
    REAL_ESTATE_INCOME_RATE,
    REAL_ESTATE_LIQUIDATION_HAIRCUT,
    REAL_ESTATE_PURCHASE_COST,
    REAL_ESTATE_SCENARIO_DAMPENER,
    SCENARIO_TIER_RANGES,
    SCENARIOS,
    TOTAL_ROUNDS,
    Industry,
)
from app.models.game import (
    AllocationRequest,
    GameState,
    MarketPosition,
    Phase,
    Player,
    RoundSummary,
    ScenarioResult,
)
from app.services import conflict_engine, endgame_engine


def roll_building_phase_length(rng: random.Random) -> int:
    """Rolls the Building Phase's hidden length for one game.

    Args:
        rng: The room's seeded random source.

    Returns:
        A round count in `BUILDING_PHASE_RANGE`, inclusive, never shown to
        players (GDD.md Section 4).
    """
    return rng.randint(*BUILDING_PHASE_RANGE)


def draw_scenario(rng: random.Random) -> ScenarioResult:
    """Picks this round's scenario and rolls each named tier into a number.

    Args:
        rng: The room's seeded random source.

    Returns:
        The scenario's flavor text plus this round's actual rolled delta for
        every Industry and Gold it names (GDD.md Section 5A).
    """
    scenario = rng.choice(SCENARIOS)
    industry_deltas = {}
    for industry, tier in scenario.industry_tiers.items():
        lo, hi = SCENARIO_TIER_RANGES[tier]
        industry_deltas[industry] = rng.uniform(lo, hi)

    gold_delta = rng.uniform(*GOLD_BASE_RANGE)
    if scenario.gold_tier is not None:
        lo, hi = GOLD_TIER_RANGES[scenario.gold_tier]
        gold_delta += rng.uniform(lo, hi)

    return ScenarioResult(
        text=scenario.text, industry_deltas=industry_deltas, gold_delta=gold_delta
    )


def start_game(state: GameState, rng: random.Random) -> None:
    """Rolls the hidden Building Phase length and opens Round 1.

    Args:
        state: The room's game state, still in the lobby.
        rng: The room's seeded random source.

    Raises:
        ValueError: If the game already started, or too few/many players
            have joined (GAMEPLAY.md's 3-to-10-player range).
    """
    if state.phase != Phase.LOBBY:
        raise ValueError("the game has already started")
    if not MIN_PLAYERS <= len(state.players) <= MAX_PLAYERS:
        raise ValueError(f"need {MIN_PLAYERS} to {MAX_PLAYERS} players to start")

    state.building_phase_length = roll_building_phase_length(rng)
    state.bank_pool = BANK_POOL_PER_PLAYER * len(state.players)
    endgame_engine.assign_raiders(state, rng)
    state.phase = Phase.BUILDING
    state.round_number = 0


def resolve_income(state: GameState, scenario: ScenarioResult) -> dict[str, float]:
    """Pays out Company, Real Estate, Gold, and Bank deposit income.

    Also accrues this round's debt interest (leverage-priced, GDD.md
    Section 5B) and seizes a player's holdings if the interest charge just
    pushed their Power below zero. Market positions are not paid here; they
    mark to market in `revalue_market` instead (GDD.md Section 4 step 6).

    Args:
        state: The room's game state; every player's cash/gold/debt mutate
            in place.
        scenario: This round's drawn scenario.

    Returns:
        Cash income credited to each player this round, keyed by player id
        (for the round summary; excludes gold's gain, which compounds into
        the holding itself rather than paying out as cash).
    """
    income_by_player: dict[str, float] = {}
    for player in state.players.values():
        company_rate = COMPANY_INCOME_RATE + scenario.industry_deltas.get(player.industry, 0.0)
        company_income = player.company * company_rate

        property_delta = scenario.industry_deltas.get(Industry.PROPERTY, 0.0)
        re_rate = REAL_ESTATE_INCOME_RATE + property_delta * REAL_ESTATE_SCENARIO_DAMPENER
        re_income = player.real_estate * re_rate

        deposit_interest = player.bank_deposit * BANK_DEPOSIT_RATE

        income = company_income + re_income + deposit_interest
        player.cash += income
        income_by_player[player.id] = income

        gold_gain = player.gold * scenario.gold_delta
        player.gold = max(0.0, player.gold + gold_gain)

        _accrue_debt_interest(player)
        _check_bankruptcy(player)

    return income_by_player


def _accrue_debt_interest(player: Player) -> None:
    """Charges one round of interest on outstanding debt, leverage-priced."""
    if player.debt <= 0:
        return
    pre_debt_power = player.total_power() + player.debt
    leverage_ratio = player.debt / max(1.0, pre_debt_power)
    rate = LOAN_INTEREST_BASE + LOAN_RISK_PREMIUM * leverage_ratio
    player.debt *= 1 + rate


def _check_bankruptcy(player: Player) -> None:
    """Seizes most of a player's holdings if their Power has gone negative."""
    if player.total_power() >= 0:
        return
    player.cash *= 1 - BANKRUPTCY_LIQUIDATION_PCT
    player.company *= 1 - BANKRUPTCY_LIQUIDATION_PCT
    player.real_estate *= 1 - BANKRUPTCY_LIQUIDATION_PCT
    player.gold *= 1 - BANKRUPTCY_LIQUIDATION_PCT
    for position in player.market_positions.values():
        position.principal *= 1 - BANKRUPTCY_LIQUIDATION_PCT
    player.debt = 0.0


def default_hold_allocation(player: Player) -> AllocationRequest:
    """Builds the "hold" a player gets when their round timer expires.

    Replays their last real split of company/real-estate/cash (or a sane
    default before they have any history), and touches nothing else: no
    liquidation, no loan, no Market bet, no Bank deposit (GAMEPLAY.md
    Section 2, matches `sim/human_sim.py`'s `autopilot_allocation`).

    Args:
        player: The player who didn't act in time.

    Returns:
        The allocation to apply on their behalf.
    """
    company_share, re_share, _cash_share = player.last_shares or (0.4, 0.1, 0.5)
    cash_available = player.cash
    return AllocationRequest(
        buy_company=cash_available * company_share,
        buy_real_estate=cash_available * re_share,
    )


def apply_allocation(state: GameState, player_id: str, allocation: AllocationRequest) -> None:
    """Applies one player's chosen split of this round's cash.

    Validates everything up front and only then mutates state, so a
    rejected allocation (insufficient cash, an opposite-direction Market
    conflict) never leaves the player in a half-applied state: money
    deducted for a Market bet that never opened, or a loan drawn from the
    Bank's pool that was never credited to the player who wanted it are
    both real corruption, not just a rejected request. `advance_round`
    falls back to a hold for any player whose allocation is rejected here,
    so raising cleanly, before any mutation, is what makes that recovery
    safe.

    Order: voluntary liquidations and the loan draw are projected first,
    since both add to spendable cash, then every requested action is
    checked against that projected cash and the Market's own legality
    rules before a single field is written.

    Args:
        state: The room's game state; the Bank's pool mutates in place if
            a loan is drawn or repaid.
        player_id: Which player this allocation belongs to.
        allocation: The player's requested split.

    Raises:
        ValueError: If the buy-side request costs more than the player's
            projected available cash, or the Market request is malformed
            or conflicts with an existing opposite-direction position.
    """
    player = state.players[player_id]
    cash_available_before = player.cash
    company_before = player.company
    re_before = player.real_estate

    re_to_sell = min(allocation.liquidate_real_estate, player.real_estate)
    gold_to_sell = min(allocation.liquidate_gold, player.gold)
    loan_funded = min(allocation.loan_draw, state.bank_pool) if allocation.loan_draw > 0 else 0.0

    projected_cash = (
        player.cash
        + re_to_sell * REAL_ESTATE_LIQUIDATION_HAIRCUT
        + gold_to_sell * GOLD_LIQUIDATION_HAIRCUT
        + loan_funded
    )
    loan_repay = min(allocation.loan_repay, player.debt, projected_cash)
    requested_spend = (
        allocation.buy_company
        + allocation.buy_real_estate
        + allocation.buy_gold
        + allocation.market_amount
        + allocation.bank_deposit
        + loan_repay
    )
    if requested_spend - projected_cash > 1e-6:
        raise ValueError("allocation requests more cash than the player has available")
    if allocation.market_amount > 0:
        _validate_market_buy(player, allocation.market_industry, allocation.market_direction)

    # Every check above passed; only now does anything actually mutate.
    player.real_estate -= re_to_sell
    player.gold -= gold_to_sell
    player.cash = projected_cash
    if loan_funded > 0:
        state.bank_pool -= loan_funded
        player.debt += loan_funded

    player.cash -= requested_spend
    player.company += allocation.buy_company
    player.real_estate += allocation.buy_real_estate * REAL_ESTATE_PURCHASE_COST
    player.gold += allocation.buy_gold
    player.bank_deposit += allocation.bank_deposit
    player.debt -= loan_repay
    state.bank_pool += loan_repay

    if allocation.market_amount > 0:
        _apply_market_buy(
            player,
            allocation.market_industry,
            allocation.market_direction,
            allocation.market_amount,
        )

    _record_shares(player, cash_available_before, company_before, re_before)


def _validate_market_buy(player: Player, industry: Industry | None, direction: str | None) -> None:
    """Checks a Market request's legality without mutating anything."""
    if industry is None or direction is None:
        raise ValueError("a Market allocation needs both an industry and a direction")
    existing = player.market_positions.get(industry)
    if existing is not None and existing.principal > 0 and existing.direction != direction:
        raise ValueError(
            f"already holding a {existing.direction} position in {industry}; "
            "close it before opening the opposite side"
        )


def _apply_market_buy(player: Player, industry: Industry, direction: str, amount: float) -> None:
    """Opens or tops up one Industry position, cash to principal at 1:1.

    Assumes `_validate_market_buy` already confirmed this request is legal.
    """
    existing = player.market_positions.get(industry)
    if existing is None or existing.principal <= 0:
        player.market_positions[industry] = MarketPosition(direction=direction, principal=amount)
    else:
        existing.principal += amount


def _record_shares(
    player: Player, cash_available: float, company_before: float, re_before: float
) -> None:
    """Remembers this round's company/real-estate/cash split for a future hold."""
    if cash_available <= 0:
        return
    company_share = max(0.0, (player.company - company_before) / cash_available)
    re_share = max(0.0, (player.real_estate - re_before) / cash_available)
    cash_share = max(0.0, player.cash / cash_available)
    total = company_share + re_share + cash_share
    if total > 0:
        player.last_shares = (company_share / total, re_share / total, cash_share / total)


def revalue_market(state: GameState, scenario: ScenarioResult) -> None:
    """Marks every Market position to this round's scenario delta.

    Long gains when the Industry is up, loses when it's down; short is the
    mirror image (GDD.md Section 5A).

    Args:
        state: The room's game state; every player's Market positions
            mutate in place.
        scenario: This round's drawn scenario.
    """
    for player in state.players.values():
        for industry, position in player.market_positions.items():
            delta = scenario.industry_deltas.get(industry, 0.0)
            if position.direction == "short":
                delta = -delta
            position.principal = max(0.0, position.principal * (1 + delta))


def resolve_taxes_and_upkeep(state: GameState) -> dict[str, float]:
    """Erodes idle cash held above the protected working-cash floor.

    Args:
        state: The room's game state; every player's cash mutates in place.

    Returns:
        Cash eroded this round, keyed by player id, for players who had any.
    """
    eroded: dict[str, float] = {}
    for player in state.players.values():
        if player.cash > IDLE_CASH_EROSION_THRESHOLD:
            erosion = (player.cash - IDLE_CASH_EROSION_THRESHOLD) * IDLE_CASH_EROSION_RATE
            player.cash -= erosion
            eroded[player.id] = erosion
    return eroded


def advance_round(
    state: GameState,
    allocations: dict[str, AllocationRequest],
    scenario: ScenarioResult,
) -> RoundSummary:
    """Resolves one full round of the Building Phase economic loop.

    The scenario is a parameter, not drawn here, because players need to
    read it *before* they allocate (GAMEPLAY.md Section 3: "read
    round-by-round scenario text to decide where the money's headed") -
    the caller draws it with `draw_scenario` and reveals it at the start of
    the round's collection window, then passes the same result back in once
    that window closes.

    Any player missing from `allocations` (their timer ran out) gets
    `default_hold_allocation` applied on their behalf instead.

    Args:
        state: The room's game state, already started.
        allocations: This round's submitted allocations, keyed by player id.
        scenario: This round's already-drawn, already-revealed scenario.

    Returns:
        A summary of what happened this round, ready to broadcast.

    Raises:
        ValueError: If the game isn't currently in the Building, Conflict,
            or Final Round phase.
    """
    resolvable_phases = (Phase.BUILDING, Phase.CONFLICT, Phase.FINAL)
    if state.phase not in resolvable_phases:
        raise ValueError(f"cannot advance a round while the game is in the '{state.phase}' phase")

    state.round_number += 1
    state.scenario_history.append(scenario)

    # A declared Defense Pact break requested last round takes effect now,
    # never the same round it was requested (GDD.md Section 7).
    conflict_engine.finalize_pending_pact_breaks(state)

    income = resolve_income(state, scenario)

    held: list[str] = []
    for player_id, player in state.players.items():
        if player_id in allocations:
            try:
                apply_allocation(state, player_id, allocations[player_id])
                continue
            except ValueError:
                # A rejected allocation falls back to the same hold a
                # missed timer already gets (GAMEPLAY.md Section 2), not a
                # failure that ends the round for every other player in
                # the room. apply_allocation validates fully before it
                # mutates anything, so the player's state is still clean
                # here, safe to apply a hold on top of.
                pass
        apply_allocation(state, player_id, default_hold_allocation(player))
        held.append(player_id)
        player.missed_rounds += 1

    endgame_engine.apply_co_founder_influence(state)
    revalue_market(state, scenario)
    conflict_engine.revalue_jv_pots(state, scenario)
    eroded = resolve_taxes_and_upkeep(state)

    for player in state.players.values():
        player.cash = max(0.0, player.cash)

    building_over = (
        state.building_phase_length is not None
        and state.round_number >= state.building_phase_length
    )
    if state.round_number >= TOTAL_ROUNDS:
        state.phase = Phase.ENDED
        state.winner_id = endgame_engine.determine_winner(state).id
    elif state.round_number >= TOTAL_ROUNDS - 1:
        # Round 15 plays differently on purpose (GDD.md Section 8.5): a
        # known final round changes rational play (JV partners have no
        # future reputation left to protect), so it's announced outright
        # rather than discovered mid-round.
        state.phase = Phase.FINAL
    elif building_over:
        state.phase = Phase.CONFLICT

    powers = {pid: p.total_power() for pid, p in state.players.items()}
    return RoundSummary(
        round_number=state.round_number,
        phase=state.phase,
        scenario=scenario,
        income=income,
        eroded_idle_cash=eroded,
        powers=powers,
        held=held,
    )
