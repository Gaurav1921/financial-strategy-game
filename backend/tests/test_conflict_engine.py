"""Tests for Hostile Bids, counter-attacks, Joint Ventures, Defense Pacts, and Audit."""

import pytest

from app.core.constants import (
    AUDIT_COST,
    JV_CONTRIBUTION_UNIT,
    JV_DRAIN_BONUS,
    MAX_ALLIES,
    POST_ATTACK_SHIELD_ROUNDS,
    REP_TAX_THRESHOLD,
    Industry,
)
from app.models.game import GameState, Player, PublicPlayerView
from app.services import conflict_engine as ce


def make_player(player_id: str, industry: Industry = Industry.TECHNOLOGY, **overrides) -> Player:
    """Builds a Player with sane defaults for a test, overriding any field."""
    return Player(id=player_id, name=player_id, industry=industry, **overrides)


def make_state(*players: Player, room_code: str = "TEST") -> GameState:
    """Builds a GameState containing the given players, keyed by their id."""
    return GameState(room_code=room_code, players={p.id: p for p in players})


def test_defense_power_weighs_real_estate_gold_and_cash_differently():
    """Real Estate counts most, Gold in between, cash least, per GDD.md Section 6."""
    player = make_player("p1", cash=0.0, real_estate=0.0, gold=0.0)
    state = make_state(player)
    base = ce.defense_power(state, player)
    assert base == pytest.approx(0.0)

    player.real_estate = 10.0
    re_defense = ce.defense_power(state, player)
    player.real_estate, player.gold = 0.0, 10.0
    gold_defense = ce.defense_power(state, player)
    player.gold, player.cash = 0.0, 10.0
    cash_defense = ce.defense_power(state, player)

    assert re_defense > gold_defense > cash_defense > 0


def test_defense_includes_ally_cash_support():
    """An allied defender's true defense includes their ally's cash contribution."""
    defender = make_player("defender", cash=0.0, real_estate=10.0)
    ally = make_player("ally", cash=50.0)
    state = make_state(defender, ally)
    solo_defense = ce.defense_power(state, defender)

    ce.propose_alliance(state, defender.id, ally.id, jv_industry=None, pact_declared=True)
    allied_defense = ce.defense_power(state, defender)
    assert allied_defense > solo_defense


def test_hostile_bid_success_captures_25_percent_of_target_wealth():
    """A successful Hostile Bid captures exactly TAKEOVER_CAPTURE_PCT of the target's Power."""
    attacker = make_player("attacker", cash=100.0, company=0.0)
    target = make_player("target", cash=5.0, company=0.0, real_estate=0.0)
    state = make_state(attacker, target)
    target_power_before = target.total_power()

    result = ce.resolve_hostile_bid(state, attacker.id, target.id, current_round=6)

    assert result.success
    assert result.amount == pytest.approx(0.25 * target_power_before)
    assert state.players[target.id].shielded_until_round == 6 + POST_ATTACK_SHIELD_ROUNDS
    assert state.players[attacker.id].captured == pytest.approx(result.amount)
    assert state.players[attacker.id].raid_count == 1


def test_hostile_bid_fails_against_a_well_defended_target():
    """A weak attacker against a heavily defended target fails and loses a stake."""
    attacker = make_player("attacker", cash=10.0, company=0.0)
    target = make_player("target", cash=10.0, real_estate=200.0)
    state = make_state(attacker, target)
    attacker_cash_before = attacker.cash

    result = ce.resolve_hostile_bid(state, attacker.id, target.id, current_round=6)

    assert not result.success
    assert state.players[attacker.id].cash < attacker_cash_before
    assert state.players[target.id].shielded_until_round == 0  # a failed attack grants no shield


def test_hostile_bid_rejects_a_shielded_target():
    """A player still under their Post-Attack Shield cannot be targeted again."""
    attacker = make_player("attacker", cash=100.0)
    target = make_player("target", cash=5.0, shielded_until_round=10)
    state = make_state(attacker, target)
    with pytest.raises(ValueError, match="shielded"):
        ce.resolve_hostile_bid(state, attacker.id, target.id, current_round=6)


def test_counter_attack_requires_a_runaway_leader():
    """No counter-attack target exists unless someone is 1.05x past 2nd place."""
    p1 = make_player("p1", cash=20.0, company=80.0)
    p2 = make_player("p2", cash=20.0, company=80.0)
    state = make_state(p1, p2)
    assert ce.find_counter_attack_target(state, current_round=6) is None
    with pytest.raises(ValueError, match="runaway leader"):
        ce.resolve_counter_attack(state, p1.id, current_round=6)


def test_counter_attack_targets_the_threatened_leader():
    """A player far enough ahead of 2nd place becomes counter-attackable."""
    leader = make_player("leader", cash=10.0, company=0.0, real_estate=0.0)
    leader.captured = 200.0  # push them well past the 1.05x margin
    second = make_player("second", cash=20.0, company=80.0)
    challenger = make_player("challenger", cash=100.0, company=100.0)
    state = make_state(leader, second, challenger)

    assert ce.find_counter_attack_target(state, current_round=6) == leader.id
    result = ce.resolve_counter_attack(state, challenger.id, current_round=6)
    assert result.target_id == leader.id
    assert result.success


def test_join_venture_formation_seeds_pot_and_updates_power():
    """Forming a Joint Venture seeds the pot from both partners' cash and updates Power."""
    a = make_player("a", cash=50.0)
    b = make_player("b", cash=50.0)
    state = make_state(a, b)
    power_before = a.total_power()

    alliance = ce.propose_alliance(
        state, a.id, b.id, jv_industry=Industry.ENERGY, pact_declared=None
    )

    assert state.players["a"].cash == pytest.approx(50.0 - JV_CONTRIBUTION_UNIT)
    assert state.players["b"].cash == pytest.approx(50.0 - JV_CONTRIBUTION_UNIT)
    assert alliance.jv.value == pytest.approx(JV_CONTRIBUTION_UNIT * 2)
    assert state.players["a"].jv_value_share == pytest.approx(JV_CONTRIBUTION_UNIT)
    # Seeding a JV moves cash into the shared pot 1:1, so Power is unchanged.
    assert state.players["a"].total_power() == pytest.approx(power_before)


def test_alliance_formation_respects_max_allies_cap():
    """A player already at MAX_ALLIES cannot form another alliance."""
    hub = make_player("hub", cash=100.0)
    partners = [make_player(f"p{i}", cash=100.0) for i in range(MAX_ALLIES + 1)]
    state = make_state(hub, *partners)
    for partner in partners[:MAX_ALLIES]:
        ce.propose_alliance(state, hub.id, partner.id, jv_industry=None, pact_declared=True)
    with pytest.raises(ValueError, match="alliances at once"):
        ce.propose_alliance(
            state, hub.id, partners[MAX_ALLIES].id, jv_industry=None, pact_declared=True
        )


def test_drain_jv_pays_drainer_the_majority_share():
    """Draining a Joint Venture pays the drainer JV_DRAIN_BONUS and the partner the rest."""
    a = make_player("a", cash=50.0)
    b = make_player("b", cash=50.0)
    state = make_state(a, b)
    ce.propose_alliance(state, a.id, b.id, jv_industry=Industry.ENERGY, pact_declared=None)

    payout = ce.drain_jv(state, a.id, b.id)

    assert payout == pytest.approx(JV_DRAIN_BONUS * (JV_CONTRIBUTION_UNIT * 2))
    assert state.players["a"].jv_value_share == pytest.approx(0.0)
    assert state.players["b"].jv_value_share == pytest.approx(0.0)
    assert state.players["a"].drain_count == 1


def test_second_jv_drain_triggers_reputation_penalty():
    """A player's second proven JV drain docks them a real, visible Power hit."""
    drainer = make_player("drainer", cash=200.0)
    partners = [make_player(f"partner{i}", cash=200.0) for i in range(REP_TAX_THRESHOLD)]
    state = make_state(drainer, *partners)
    for partner in partners:
        ce.propose_alliance(
            state, drainer.id, partner.id, jv_industry=Industry.ENERGY, pact_declared=None
        )

    power_before_second_drain = state.players["drainer"].total_power()
    for partner in partners:
        ce.drain_jv(state, drainer.id, partner.id)

    assert state.players["drainer"].drain_count == REP_TAX_THRESHOLD
    assert state.players["drainer"].total_power() < power_before_second_drain


def test_covert_pact_break_is_immediate_and_free():
    """Breaking a covert Defense Pact ends it instantly with no penalty."""
    a = make_player("a", cash=50.0)
    b = make_player("b", cash=50.0)
    state = make_state(a, b)
    ce.propose_alliance(state, a.id, b.id, jv_industry=None, pact_declared=False)

    took_effect_now = ce.initiate_pact_break(state, a.id, b.id)

    assert took_effect_now
    assert not state.alliances_of("a")


def test_declared_pact_break_is_deferred_to_next_round():
    """Breaking a declared Defense Pact doesn't end it until finalize_pending_pact_breaks runs."""
    a = make_player("a", cash=50.0)
    b = make_player("b", cash=50.0)
    state = make_state(a, b)
    ce.propose_alliance(state, a.id, b.id, jv_industry=None, pact_declared=True)

    took_effect_now = ce.initiate_pact_break(state, a.id, b.id)
    assert not took_effect_now
    assert len(state.alliances_of("a")) == 1  # still active until next round

    resolved = ce.finalize_pending_pact_breaks(state)
    assert resolved == ["a"]
    assert not state.alliances_of("a")


def test_audit_reveals_true_numbers_at_a_flat_cost():
    """Auditing a player costs a flat fee and reveals their true breakdown."""
    auditor = make_player("auditor", cash=20.0)
    target = make_player("target", cash=42.0, company=13.0, real_estate=7.0, gold=3.0, debt=1.0)
    state = make_state(auditor, target)

    result = ce.audit_player(state, auditor.id, target.id)

    assert state.players["auditor"].cash == pytest.approx(20.0 - AUDIT_COST)
    assert result.cash == pytest.approx(42.0)
    assert result.company == pytest.approx(13.0)
    assert result.real_estate == pytest.approx(7.0)
    assert result.gold == pytest.approx(3.0)
    assert result.debt == pytest.approx(1.0)


def test_audit_requires_enough_cash():
    """A player who can't afford the flat Audit cost is rejected."""
    auditor = make_player("auditor", cash=1.0)
    target = make_player("target", cash=100.0)
    state = make_state(auditor, target)
    with pytest.raises(ValueError, match="costs"):
        ce.audit_player(state, auditor.id, target.id)


def test_a_never_attacked_player_does_not_show_as_shielded_at_round_zero():
    """A fresh player (shielded_until_round=0) isn't shielded at game start (round 0 too)."""
    player = make_player("p1")
    view = PublicPlayerView.of(player, current_round=0, declared_allies=[])
    assert not view.shielded


def test_a_player_shows_as_shielded_only_within_their_actual_shield_window():
    """A real Post-Attack Shield is reflected correctly, and expires on schedule."""
    player = make_player("p1", shielded_until_round=8)
    assert PublicPlayerView.of(player, current_round=7, declared_allies=[]).shielded
    assert PublicPlayerView.of(player, current_round=8, declared_allies=[]).shielded
    assert not PublicPlayerView.of(player, current_round=9, declared_allies=[]).shielded
