"""Tests for the Building Phase round-resolution engine.

Round-resolution math is the most important code in the game (GDD.md
Section 11), so these check it directly against `docs/GDD.md` Section 5B's
rate table rather than against `sim/human_sim.py`'s behavior, since the sim
models bot archetypes, not the explicit-action API this engine actually
exposes.
"""

import random

import pytest

from app.core.constants import (
    BANK_DEPOSIT_RATE,
    GOLD_BASE_RANGE,
    GOLD_TIER_RANGES,
    IDLE_CASH_EROSION_RATE,
    IDLE_CASH_EROSION_THRESHOLD,
    REAL_ESTATE_PURCHASE_COST,
    SCENARIO_TIER_RANGES,
    SCENARIOS,
    STARTING_CASH,
    STARTING_COMPANY,
    Industry,
)
from app.models.game import AllocationRequest, GameState, Phase, Player, ScenarioResult
from app.services import conflict_engine
from app.services.round_engine import (
    advance_round,
    apply_allocation,
    default_hold_allocation,
    draw_scenario,
    resolve_income,
    resolve_taxes_and_upkeep,
    revalue_market,
    start_game,
)

QUIET_SCENARIO = ScenarioResult(text="quiet", industry_deltas={}, gold_delta=0.0)


def make_player(player_id: str, industry: Industry = Industry.TECHNOLOGY, **overrides) -> Player:
    """Builds a Player with sane defaults for a test, overriding any field."""
    return Player(id=player_id, name=player_id, industry=industry, **overrides)


def make_state(*players: Player, room_code: str = "TEST") -> GameState:
    """Builds a GameState containing the given players, keyed by their id."""
    return GameState(room_code=room_code, players={p.id: p for p in players})


def test_starting_power_is_exactly_100():
    """A fresh player's total Power matches GAMEPLAY.md Section 1's table."""
    player = make_player("p1")
    assert player.cash == STARTING_CASH
    assert player.company == STARTING_COMPANY
    assert player.total_power() == pytest.approx(100.0)


def test_company_income_matches_base_rate_with_no_scenario():
    """With no industry delta, Company income is exactly the 10% base rate."""
    player = make_player("p1", company=100.0, cash=0.0)
    state = make_state(player)
    resolve_income(state, QUIET_SCENARIO)
    assert state.players["p1"].cash == pytest.approx(10.0)


def test_company_income_includes_industry_delta():
    """A player's own Industry delta shifts their Company income on top of the base rate."""
    player = make_player("p1", industry=Industry.ENERGY, company=100.0, cash=0.0)
    state = make_state(player)
    scenario = ScenarioResult(
        text="conflict", industry_deltas={Industry.ENERGY: 0.15}, gold_delta=0.0
    )
    resolve_income(state, scenario)
    assert state.players["p1"].cash == pytest.approx(100.0 * (0.10 + 0.15))


def test_real_estate_purchase_costs_exactly_three_percent():
    """Buying Real Estate nets `amount * REAL_ESTATE_PURCHASE_COST`, not the full amount."""
    player = make_player("p1", cash=100.0)
    state = make_state(player)
    apply_allocation(state, "p1", AllocationRequest(buy_real_estate=100.0))
    assert state.players["p1"].real_estate == pytest.approx(100.0 * REAL_ESTATE_PURCHASE_COST)
    assert state.players["p1"].cash == pytest.approx(0.0)


def test_bank_deposit_pays_flat_four_percent():
    """A Bank deposit earns exactly BANK_DEPOSIT_RATE, no leverage or scenario dependence."""
    player = make_player("p1", bank_deposit=50.0, company=0.0, real_estate=0.0, cash=0.0)
    state = make_state(player)
    resolve_income(state, QUIET_SCENARIO)
    assert state.players["p1"].cash == pytest.approx(50.0 * BANK_DEPOSIT_RATE)


def test_idle_cash_above_floor_erodes_at_three_percent():
    """Cash above the protected floor erodes at IDLE_CASH_EROSION_RATE; cash at/under it doesn't."""
    rich = make_player("rich", cash=110.0)
    poor = make_player("poor", cash=5.0)
    state = make_state(rich, poor)
    eroded = resolve_taxes_and_upkeep(state)

    expected_erosion = (110.0 - IDLE_CASH_EROSION_THRESHOLD) * IDLE_CASH_EROSION_RATE
    assert eroded["rich"] == pytest.approx(expected_erosion)
    assert "poor" not in eroded
    assert state.players["rich"].cash == pytest.approx(110.0 - expected_erosion)
    assert state.players["poor"].cash == pytest.approx(5.0)


def test_scenario_rolls_always_land_inside_their_tier_range():
    """Every drawn scenario's rolled delta stays inside the widest documented tier bound.

    The resolved delta alone doesn't say which tier produced it (ranges only
    differ by sign, not by which scenario), so this checks against the
    union of all tier ranges rather than the specific tier - a weaker bound,
    but one that still catches a rate rolled outside every documented
    ceiling entirely.
    """
    rng = random.Random(42)
    industry_lo = min(lo for lo, _ in SCENARIO_TIER_RANGES.values())
    industry_hi = max(hi for _, hi in SCENARIO_TIER_RANGES.values())
    gold_lo = min(lo for lo, _ in GOLD_TIER_RANGES.values())
    gold_hi = max(hi for _, hi in GOLD_TIER_RANGES.values())

    for _ in range(500):
        result = draw_scenario(rng)
        for delta in result.industry_deltas.values():
            assert industry_lo <= delta <= industry_hi
        # Gold always adds its ordinary-year jitter on top of any tier kicker.
        assert GOLD_BASE_RANGE[0] + gold_lo <= result.gold_delta <= GOLD_BASE_RANGE[1] + gold_hi


def test_every_scenario_is_reachable():
    """Every entry in SCENARIOS gets drawn at least once over enough rolls."""
    rng = random.Random(11)
    seen_texts = {draw_scenario(rng).text for _ in range(2000)}
    assert seen_texts == {scenario.text for scenario in SCENARIOS}


def test_market_long_position_gains_with_the_industry():
    """A long Market position gains value when its Industry's delta is positive."""
    player = make_player("p1", cash=20.0)
    state = make_state(player)
    apply_allocation(
        state,
        "p1",
        AllocationRequest(
            market_industry=Industry.ENERGY, market_direction="long", market_amount=20.0
        ),
    )
    revalue_market(state, ScenarioResult(text="", industry_deltas={Industry.ENERGY: 0.10}))
    assert state.players["p1"].market_positions[Industry.ENERGY].principal == pytest.approx(22.0)


def test_market_short_position_loses_when_the_industry_rises():
    """A short Market position loses value when its Industry's delta is positive."""
    player = make_player("p1", cash=20.0)
    state = make_state(player)
    apply_allocation(
        state,
        "p1",
        AllocationRequest(
            market_industry=Industry.ENERGY, market_direction="short", market_amount=20.0
        ),
    )
    revalue_market(state, ScenarioResult(text="", industry_deltas={Industry.ENERGY: 0.10}))
    assert state.players["p1"].market_positions[Industry.ENERGY].principal == pytest.approx(18.0)


def test_allocation_beyond_available_cash_is_rejected():
    """An allocation that spends more than the player has raises ValueError."""
    player = make_player("p1", cash=10.0)
    state = make_state(player)
    with pytest.raises(ValueError, match="more cash"):
        apply_allocation(state, "p1", AllocationRequest(buy_company=50.0))


def test_opposite_direction_market_position_is_rejected():
    """Opening a short in an Industry where the player already holds a long is rejected."""
    player = make_player("p1", cash=50.0)
    state = make_state(player)
    apply_allocation(
        state,
        "p1",
        AllocationRequest(
            market_industry=Industry.ENERGY, market_direction="long", market_amount=10.0
        ),
    )
    with pytest.raises(ValueError, match="already holding"):
        apply_allocation(
            state,
            "p1",
            AllocationRequest(
                market_industry=Industry.ENERGY, market_direction="short", market_amount=10.0
            ),
        )


def test_hold_replays_last_real_split():
    """A player who never submits again keeps compounding their last chosen split."""
    player = make_player("p1", cash=100.0)
    state = make_state(player)
    apply_allocation(state, "p1", AllocationRequest(buy_company=60.0, buy_real_estate=20.0))

    # Real Estate's 3% purchase cost means the RE share reflects what was
    # actually gained, not the raw cash spent on it.
    re_gained = 20.0 * REAL_ESTATE_PURCHASE_COST
    cash_remaining = 100.0 - 60.0 - 20.0
    total = 60.0 + re_gained + cash_remaining
    expected_shares = (60.0 / total, re_gained / total, cash_remaining / total)
    assert state.players["p1"].last_shares == pytest.approx(expected_shares)

    state.players["p1"].cash = 50.0
    hold = default_hold_allocation(state.players["p1"])
    assert hold.buy_company == pytest.approx(50.0 * expected_shares[0])
    assert hold.buy_real_estate == pytest.approx(50.0 * expected_shares[1])


def test_debt_interest_rises_with_leverage():
    """A more leveraged player accrues debt interest at a higher rate."""
    low_leverage = make_player("low", cash=10.0, company=90.0, debt=10.0)
    high_leverage = make_player("high", cash=10.0, company=90.0, debt=60.0)
    state = make_state(low_leverage, high_leverage)
    resolve_income(state, QUIET_SCENARIO)

    low_growth = state.players["low"].debt / 10.0
    high_growth = state.players["high"].debt / 60.0
    assert high_growth > low_growth
    assert state.players["low"].total_power() > 0
    assert state.players["high"].total_power() > 0


def test_bankruptcy_seizes_85_percent_and_discharges_debt():
    """A player whose Power goes negative from interest alone is bankrupted (GDD.md 5B)."""
    player = make_player("p1", cash=1.0, company=0.0, real_estate=0.0, debt=500.0)
    state = make_state(player)
    resolve_income(state, QUIET_SCENARIO)

    assert state.players["p1"].debt == pytest.approx(0.0)
    assert state.players["p1"].cash == pytest.approx(1.0 * 0.15)


def test_advance_round_transitions_to_conflict_then_final_then_ended():
    """The game moves Building -> Conflict at the hidden length, Conflict -> Final at 14/15."""
    players = [make_player(f"p{i}") for i in range(3)]
    state = make_state(*players)
    rng = random.Random(7)
    start_game(state, rng)
    assert state.building_phase_length is not None
    building_length = state.building_phase_length

    for round_number in range(1, 16):
        summary = advance_round(state, {}, draw_scenario(rng))
        assert summary.round_number == round_number
        if round_number < building_length:
            assert state.phase == Phase.BUILDING
        elif round_number < 14:
            assert state.phase == Phase.CONFLICT
        elif round_number < 15:
            assert state.phase == Phase.FINAL

    assert state.phase == Phase.ENDED
    assert state.winner_id in state.players
    assert state.round_number == 15


def test_advance_round_with_no_allocations_marks_everyone_held():
    """Every player who submits nothing this round shows up in the summary's `held` list."""
    players = [make_player(f"p{i}") for i in range(3)]
    state = make_state(*players)
    rng = random.Random(3)
    start_game(state, rng)

    summary = advance_round(state, {}, draw_scenario(rng))
    assert set(summary.held) == {"p0", "p1", "p2"}


def test_rejected_market_conflict_leaves_cash_untouched():
    """A rejected Market conflict doesn't deduct cash for a position that never opened."""
    player = make_player("p1", cash=50.0)
    state = make_state(player)
    apply_allocation(
        state,
        "p1",
        AllocationRequest(
            market_industry=Industry.ENERGY, market_direction="long", market_amount=10.0
        ),
    )
    cash_before = state.players["p1"].cash
    with pytest.raises(ValueError, match="already holding"):
        apply_allocation(
            state,
            "p1",
            AllocationRequest(
                market_industry=Industry.ENERGY, market_direction="short", market_amount=10.0
            ),
        )
    assert state.players["p1"].cash == pytest.approx(cash_before)


def test_loan_repayment_credits_back_to_the_bank_pool():
    """Repaying a loan returns the amount to the Bank's pool, not just reducing debt."""
    player = make_player("p1", cash=50.0, debt=20.0)
    state = make_state(player)
    state.bank_pool = 100.0
    apply_allocation(state, "p1", AllocationRequest(loan_repay=20.0))
    assert state.players["p1"].debt == pytest.approx(0.0)
    assert state.bank_pool == pytest.approx(120.0)


def test_advance_round_falls_back_to_a_hold_for_one_invalid_allocation():
    """One player's invalid allocation resolves as a hold instead of failing the whole round."""
    players = [make_player("p0", cash=50.0), make_player("p1", cash=10.0), make_player("p2")]
    state = make_state(*players)
    rng = random.Random(1)
    start_game(state, rng)

    allocations = {
        "p0": AllocationRequest(buy_company=10.0),
        "p1": AllocationRequest(buy_company=999.0),  # far more than p1 has
        "p2": AllocationRequest(buy_company=5.0),
    }
    summary = advance_round(state, allocations, draw_scenario(rng))

    assert summary.held == ["p1"]  # only the rejected allocation fell back to a hold


def test_advance_round_revalues_live_joint_venture_pots():
    """A round's scenario delta marks every live Joint Venture pot to market too."""
    a = make_player("a", industry=Industry.ENERGY, cash=50.0)
    b = make_player("b", industry=Industry.ENERGY, cash=50.0)
    state = make_state(a, b)
    state.phase = Phase.BUILDING
    alliance = conflict_engine.propose_alliance(
        state, "a", "b", jv_industry=Industry.ENERGY, pact_declared=None
    )
    pot_before = alliance.jv.value

    scenario = ScenarioResult(text="boom", industry_deltas={Industry.ENERGY: 0.10}, gold_delta=0.0)
    advance_round(state, {}, scenario)

    assert alliance.jv.value == pytest.approx(pot_before * 1.10, rel=1e-6)


def test_advance_round_finalizes_a_declared_pact_break_from_last_round():
    """A declared pact break requested last round is gone by the start of this one."""
    a = make_player("a", cash=50.0)
    b = make_player("b", cash=50.0)
    state = make_state(a, b)
    state.phase = Phase.BUILDING
    conflict_engine.propose_alliance(state, "a", "b", jv_industry=None, pact_declared=True)
    conflict_engine.initiate_pact_break(state, "a", "b")
    assert state.alliances_of("a")  # still active going into the next round

    advance_round(state, {}, QUIET_SCENARIO)

    assert not state.alliances_of("a")
