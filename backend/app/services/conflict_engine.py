"""Combat and alliances: Hostile Bids, Joint Ventures, Defense Pacts, Audit.

GDD.md Sections 5 item 5, 6, 7, and 8.3. Ports the math `sim/human_sim.py`
validated for these mechanics, minus the bot-only decision heuristics
(grudge, bandwagon, tactical pre-liquidation, raider sabotage): a real
player picks their own target and decides their own moves through the API,
so only the *resolution* math is ported, not the archetype logic that stood
in for a human's judgment in the simulation.

Audit is deliberately scoped down from GDD.md Section 6/8.3's full
claim/bluff/caught-lying description to a direct "pay to reveal the truth"
action - see `audit_player`'s docstring for why.
"""

from app.core.constants import (
    ALLY_SUPPORT_WEIGHT,
    ATTACK_FAIL_LOSS_PCT,
    ATTACKER_CASH_WEIGHT,
    AUDIT_COST,
    COUNTER_ATTACK_CASH_WEIGHT,
    COUNTER_ATTACK_COMPANY_WEIGHT,
    COUNTER_ATTACK_FAIL_DAMPENER,
    DEFENDER_TIE_BONUS,
    DEFENSE_CASH_WEIGHT,
    DEFENSE_GOLD_WEIGHT,
    DEFENSE_REAL_ESTATE_WEIGHT,
    GOLD_LIQUIDATION_HAIRCUT,
    JV_CONTRIBUTION_UNIT,
    JV_DRAIN_BONUS,
    JV_TOPUP_CASH_BUFFER,
    JV_TOPUP_RATE,
    LEADER_THREATENED_MARGIN,
    MAX_ALLIES,
    POST_ATTACK_SHIELD_ROUNDS,
    RAID_FATIGUE_FLOOR,
    RAID_FATIGUE_PENALTY,
    REAL_ESTATE_LIQUIDATION_HAIRCUT,
    REP_TAX_THRESHOLD,
    REPUTATION_PENALTY_PCT,
    TAKEOVER_CAPTURE_PCT,
    Industry,
)
from app.models.game import Alliance, GameState, JVPot, Player, ScenarioResult, alliance_id
from app.services import endgame_engine


def _allies_of(state: GameState, player_id: str) -> list[Player]:
    """Every player currently allied with `player_id`, real allies only."""
    partners = [a.other(player_id) for a in state.alliances_of(player_id)]
    return [state.players[pid] for pid in partners]


def defense_power(state: GameState, player: Player) -> float:
    """Computes a player's true total defense, allies included.

    Real Estate counts heavily, Gold moderately, cash lightly, matching the
    deliberate "safe harbor" asset hierarchy (GDD.md Section 6). Used to
    resolve actual combat; never sent to another player directly, since
    Section 6 keeps everything but Power hidden by default.

    Args:
        state: The room's game state.
        player: The defending player.

    Returns:
        The defender's true defense power, tie-bonus included.
    """
    own = (
        player.real_estate * DEFENSE_REAL_ESTATE_WEIGHT
        + player.gold * DEFENSE_GOLD_WEIGHT
        + player.cash * DEFENSE_CASH_WEIGHT
    )
    support = sum(ally.cash * ALLY_SUPPORT_WEIGHT for ally in _allies_of(state, player.id))
    return (own + support) * DEFENDER_TIE_BONUS


def _fatigue_multiplier(player: Player) -> float:
    """A repeat Hostile Bid attacker's power shrinks with each prior success."""
    if RAID_FATIGUE_PENALTY <= 0:
        return 1.0
    return max(RAID_FATIGUE_FLOOR, 1.0 - RAID_FATIGUE_PENALTY * player.raid_count)


def hostile_bid_attack_power(state: GameState, attacker: Player) -> float:
    """Computes an attacker's power for a Hostile Bid.

    Their own cash, plus allies backing them, fatigued by prior successful
    raids this game.

    Args:
        state: The room's game state.
        attacker: The attacking player.

    Returns:
        The attacker's effective attack power for a Hostile Bid.
    """
    support = sum(ally.cash * ALLY_SUPPORT_WEIGHT for ally in _allies_of(state, attacker.id))
    return (attacker.cash * ATTACKER_CASH_WEIGHT + support) * _fatigue_multiplier(attacker)


def counter_attack_power(state: GameState, challenger: Player) -> tuple[float, float]:
    """Computes a challenger's power for a "gang up on the leader" counter-attack.

    A counter-attack mobilizes both cash and a slice of Company value, not
    cash alone, so a challenger with a big Company can still join a pile-on
    even while holding little liquid cash.

    Args:
        state: The room's game state.
        challenger: The player considering a counter-attack.

    Returns:
        A `(attack_power, mobilized)` pair: `attack_power` includes ally
        support, `mobilized` is the challenger's own contribution alone
        (used to size the failed-attack penalty and the success cost).
    """
    mobilized = (
        challenger.cash * COUNTER_ATTACK_CASH_WEIGHT
        + challenger.company * COUNTER_ATTACK_COMPANY_WEIGHT
    )
    support = sum(ally.cash * ALLY_SUPPORT_WEIGHT for ally in _allies_of(state, challenger.id))
    return mobilized + support, mobilized


def find_counter_attack_target(state: GameState, current_round: int) -> str | None:
    """Finds the runaway leader, if the table currently has one worth ganging up on.

    Args:
        state: The room's game state.
        current_round: The current round number.

    Returns:
        The leader's player id if they're far enough ahead of 2nd place and
        not currently shielded, or None if nobody qualifies right now.
    """
    ranked = sorted(state.players.values(), key=lambda p: p.total_power(), reverse=True)
    if len(ranked) < 2:
        return None
    leader = ranked[0]
    second_power = max(1.0, ranked[1].total_power())
    if leader.total_power() < second_power * LEADER_THREATENED_MARGIN:
        return None
    if leader.shielded_until_round > 0 and current_round <= leader.shielded_until_round:
        return None
    return leader.id


def _collect_payment(player: Player, amount_needed: float) -> float:
    """Raises cash from a player: cash, then Company, then Real Estate, then Gold.

    Each liquidated at its own haircut if still short. Shared by every
    mechanic that forces a payment out of a player (GDD.md Section 6/8.3).

    Args:
        player: The player being charged.
        amount_needed: How much must be raised.

    Returns:
        How much was actually collected, capped by what the player has.
    """
    if amount_needed <= 0:
        return 0.0
    paid = min(player.cash, amount_needed)
    player.cash -= paid
    remaining = amount_needed - paid

    if remaining > 0 and player.company > 0:
        from_company = min(player.company, remaining)
        player.company -= from_company
        paid += from_company
        remaining -= from_company

    if remaining > 0 and player.real_estate > 0:
        re_to_sell = min(player.real_estate, remaining / REAL_ESTATE_LIQUIDATION_HAIRCUT)
        player.real_estate -= re_to_sell
        raised = re_to_sell * REAL_ESTATE_LIQUIDATION_HAIRCUT
        paid += raised
        remaining -= raised

    if remaining > 0 and player.gold > 0:
        gold_to_sell = min(player.gold, remaining / GOLD_LIQUIDATION_HAIRCUT)
        player.gold -= gold_to_sell
        raised = gold_to_sell * GOLD_LIQUIDATION_HAIRCUT
        paid += raised

    return paid


def _capture_from_target(target: Player, capture_pct: float) -> float:
    """Takes `capture_pct` of a target's total wealth via the standard cascade."""
    captured = capture_pct * target.total_power()
    return _collect_payment(target, captured)


class HostileBidResult:
    """The outcome of one resolved Hostile Bid or counter-attack."""

    def __init__(self, attacker_id: str, target_id: str, success: bool, amount: float) -> None:
        """Records who attacked whom, whether it worked, and how much moved.

        Args:
            attacker_id: The attacking player.
            target_id: The defending player.
            success: Whether the attack succeeded.
            amount: Captured value (success) or the attacker's loss (failure).
        """
        self.attacker_id = attacker_id
        self.target_id = target_id
        self.success = success
        self.amount = amount


def resolve_hostile_bid(
    state: GameState, attacker_id: str, target_id: str, current_round: int
) -> HostileBidResult:
    """Resolves one player's Hostile Bid against another.

    Args:
        state: The room's game state; both players mutate in place.
        attacker_id: The attacking player.
        target_id: The targeted player.
        current_round: The current round number.

    Returns:
        The resolved outcome.

    Raises:
        ValueError: If the attacker targets themselves, or the target is
            still under a Post-Attack Shield.
    """
    if attacker_id == target_id:
        raise ValueError("a player cannot attack themselves")
    attacker = state.players[attacker_id]
    target = state.players[target_id]
    if target.shielded_until_round > 0 and current_round <= target.shielded_until_round:
        raise ValueError("that player is still shielded from a recent attack")

    attack_power = hostile_bid_attack_power(state, attacker)
    stake = attacker.cash * ATTACKER_CASH_WEIGHT
    true_defense = defense_power(state, target)

    if attack_power > true_defense:
        captured = _capture_from_target(target, TAKEOVER_CAPTURE_PCT)
        target.shielded_until_round = current_round + POST_ATTACK_SHIELD_ROUNDS
        attacker.captured += captured
        attacker.cash = max(0.0, attacker.cash - stake * 0.2)
        attacker.raid_count += 1
        endgame_engine.apply_golden_parachute(state, target_id, captured)
        return HostileBidResult(attacker_id, target_id, True, captured)

    loss = _collect_payment(attacker, stake * ATTACK_FAIL_LOSS_PCT)
    half = loss / 2
    target.cash += half
    state.bank_pool += half
    return HostileBidResult(attacker_id, target_id, False, loss)


def resolve_counter_attack(
    state: GameState, challenger_id: str, current_round: int
) -> HostileBidResult:
    """Resolves one player's counter-attack against the current runaway leader.

    Args:
        state: The room's game state; both players mutate in place.
        challenger_id: The player attempting the counter-attack.
        current_round: The current round number.

    Returns:
        The resolved outcome.

    Raises:
        ValueError: If nobody currently qualifies as a threatened leader, or
            the challenger *is* that leader.
    """
    leader_id = find_counter_attack_target(state, current_round)
    if leader_id is None:
        raise ValueError("no player is currently a runaway leader worth ganging up on")
    if leader_id == challenger_id:
        raise ValueError("the runaway leader cannot counter-attack themselves")

    challenger = state.players[challenger_id]
    leader = state.players[leader_id]
    attack_power, mobilized = counter_attack_power(state, challenger)
    true_defense = defense_power(state, leader)

    if attack_power > true_defense:
        captured = _capture_from_target(leader, TAKEOVER_CAPTURE_PCT)
        leader.shielded_until_round = current_round + POST_ATTACK_SHIELD_ROUNDS
        challenger.captured += captured
        challenger.company = max(0.0, challenger.company - mobilized * 0.2)
        endgame_engine.apply_golden_parachute(state, leader_id, captured)
        return HostileBidResult(challenger_id, leader_id, True, captured)

    penalty_target = mobilized * ATTACK_FAIL_LOSS_PCT * COUNTER_ATTACK_FAIL_DAMPENER
    from_company = min(challenger.company, penalty_target)
    challenger.company -= from_company
    remaining = penalty_target - from_company
    loss = from_company + _collect_payment(challenger, remaining)
    half = loss / 2
    leader.cash += half
    state.bank_pool += half
    return HostileBidResult(challenger_id, leader_id, False, loss)


def propose_alliance(
    state: GameState,
    from_id: str,
    to_id: str,
    jv_industry: Industry | None,
    pact_declared: bool | None,
) -> Alliance:
    """Forms an alliance directly; mutual consent is enforced by the caller.

    The WebSocket layer only invokes this once the invited player has
    accepted a pending invite - see `Room.propose_alliance`/`respond_alliance`.

    Args:
        state: The room's game state.
        from_id: One partner.
        to_id: The other partner.
        jv_industry: The Industry to seed a Joint Venture pot in, or None
            for a pure Defense Pact with no shared position.
        pact_declared: True for a declared (public) Defense Pact, False for
            covert, or None for a pure Joint Venture with no pact at all.

    Returns:
        The newly formed alliance.

    Raises:
        ValueError: If either side already has `MAX_ALLIES` alliances, are
            already allied with each other, or neither a JV nor a pact was
            actually requested.
    """
    if jv_industry is None and pact_declared is None:
        raise ValueError("an alliance needs at least a Joint Venture or a Defense Pact")
    if (
        len(state.alliances_of(from_id)) >= MAX_ALLIES
        or len(state.alliances_of(to_id)) >= MAX_ALLIES
    ):
        raise ValueError(f"a player can only have {MAX_ALLIES} alliances at once")
    aid = alliance_id(from_id, to_id)
    if aid in state.alliances:
        raise ValueError("these two players are already allied")

    jv = None
    if jv_industry is not None:
        a, b = state.players[from_id], state.players[to_id]
        if a.cash < JV_CONTRIBUTION_UNIT or b.cash < JV_CONTRIBUTION_UNIT:
            raise ValueError(
                f"both partners need at least {JV_CONTRIBUTION_UNIT} cash to seed a Joint Venture"
            )
        a.cash -= JV_CONTRIBUTION_UNIT
        b.cash -= JV_CONTRIBUTION_UNIT
        jv = JVPot(
            industry=jv_industry,
            value=JV_CONTRIBUTION_UNIT * 2,
            contributed_each=JV_CONTRIBUTION_UNIT,
        )

    alliance = Alliance(
        id=aid, player_a=from_id, player_b=to_id, jv=jv, pact_declared=pact_declared
    )
    state.alliances[aid] = alliance
    _sync_jv_value_share(state, alliance)
    return alliance


def _sync_jv_value_share(state: GameState, alliance: Alliance) -> None:
    """Keeps both partners' cached `jv_value_share` matching their live pot."""
    share = (alliance.jv.value / 2) if alliance.jv is not None else 0.0
    for pid in (alliance.player_a, alliance.player_b):
        player = state.players.get(pid)
        if player is None:
            continue
        other_shares = sum(
            (a.jv.value / 2)
            for a in state.alliances_of(pid)
            if a.jv is not None and a.id != alliance.id
        )
        player.jv_value_share = other_shares + share


def top_up_jv(state: GameState, player_id: str, ally_id: str) -> None:
    """Adds a top-up to an existing Joint Venture pot, if both partners can spare it.

    The amount is 20% of whichever partner currently has less cash, floored
    at the original seed stake, and skipped entirely if either partner
    would drop below the spare-cash buffer (GDD.md Section 5 item 5).

    Args:
        state: The room's game state.
        player_id: The partner requesting the top-up.
        ally_id: The other partner.

    Raises:
        ValueError: If no Joint Venture exists between these two players.
    """
    alliance = state.alliances.get(alliance_id(player_id, ally_id))
    if alliance is None or alliance.jv is None:
        raise ValueError("no Joint Venture exists between these two players")
    a, b = state.players[alliance.player_a], state.players[alliance.player_b]
    topup = max(JV_CONTRIBUTION_UNIT, min(a.cash, b.cash) * JV_TOPUP_RATE)
    if a.cash - topup < JV_TOPUP_CASH_BUFFER or b.cash - topup < JV_TOPUP_CASH_BUFFER:
        raise ValueError("one partner can't spare that top-up right now")
    a.cash -= topup
    b.cash -= topup
    alliance.jv.value += topup * 2
    alliance.jv.contributed_each += topup
    _sync_jv_value_share(state, alliance)


def drain_jv(state: GameState, player_id: str, ally_id: str) -> float:
    """Drains a Joint Venture pot: the drainer keeps the majority.

    Ends the alliance's JV (the Defense Pact half, if any, survives), and
    applies the reputation penalty if this is the drainer's second proven
    betrayal.

    Args:
        state: The room's game state.
        player_id: The player draining the pot.
        ally_id: Their partner in this Joint Venture.

    Returns:
        The amount the drainer received.

    Raises:
        ValueError: If no Joint Venture exists between these two players.
    """
    aid = alliance_id(player_id, ally_id)
    alliance = state.alliances.get(aid)
    if alliance is None or alliance.jv is None:
        raise ValueError("no Joint Venture exists between these two players")

    pot = alliance.jv.value
    drainer_payout = JV_DRAIN_BONUS * pot
    partner_payout = (1 - JV_DRAIN_BONUS) * pot
    drainer, partner = state.players[player_id], state.players[ally_id]
    drainer.cash += drainer_payout
    partner.cash += partner_payout
    drainer.drain_count += 1

    alliance.jv = None
    if alliance.pact_declared is None:
        del state.alliances[aid]
    _sync_jv_value_share(state, alliance)

    if drainer.drain_count == REP_TAX_THRESHOLD:
        _collect_payment(drainer, drainer.total_power() * REPUTATION_PENALTY_PCT)

    return drainer_payout


def initiate_pact_break(state: GameState, player_id: str, ally_id: str) -> bool:
    """Ends a Defense Pact, immediately if covert, deferred to next round if declared.

    Args:
        state: The room's game state.
        player_id: The player breaking the pact.
        ally_id: Their partner.

    Returns:
        True if the break took effect immediately (covert), False if it's
        pending until the start of next round (declared).

    Raises:
        ValueError: If no Defense Pact exists between these two players.
    """
    alliance = state.alliances.get(alliance_id(player_id, ally_id))
    if alliance is None or alliance.pact_declared is None:
        raise ValueError("no Defense Pact exists between these two players")

    if not alliance.pact_declared:
        _sever_alliance(state, alliance)
        return True

    alliance.pending_pact_break_by = player_id
    return False


def _sever_alliance(state: GameState, alliance: Alliance) -> None:
    """Ends an alliance outright, splitting any live Joint Venture pot evenly.

    A no-fault severance (a Defense Pact ending, or the JV half of a mixed
    alliance being removed alongside it): never touches `drain_count` or the
    reputation penalty, which are reserved for an actual drain (GDD.md
    Section 9).
    """
    if alliance.jv is not None:
        half = alliance.jv.value / 2
        state.players[alliance.player_a].cash += half
        state.players[alliance.player_b].cash += half
        alliance.jv = None
    del state.alliances[alliance.id]
    _sync_jv_value_share(state, alliance)


def finalize_pending_pact_breaks(state: GameState) -> list[str]:
    """Applies every declared pact break initiated last round, at the start of this one.

    Runs before anything else in a round, so a break initiated last round
    takes effect now, never the same round it was requested (GDD.md
    Section 7: a pact can't be un-declared instantly to dodge one attack).

    Args:
        state: The room's game state; affected alliances/players mutate.

    Returns:
        The player ids whose pact break just took effect, for the round summary.
    """
    resolved: list[str] = []
    for alliance in list(state.alliances.values()):
        breaker_id = alliance.pending_pact_break_by
        if breaker_id is None:
            continue
        breaker = state.players[breaker_id]
        breaker.pact_break_count += 1
        _sever_alliance(state, alliance)
        resolved.append(breaker_id)
        if breaker.pact_break_count == REP_TAX_THRESHOLD:
            _collect_payment(breaker, breaker.total_power() * REPUTATION_PENALTY_PCT)
    return resolved


def revalue_jv_pots(state: GameState, scenario: ScenarioResult) -> None:
    """Marks every live Joint Venture pot to this round's scenario delta.

    Args:
        state: The room's game state; every live pot mutates in place.
        scenario: This round's drawn scenario.
    """
    for alliance in state.alliances.values():
        if alliance.jv is None:
            continue
        delta = scenario.industry_deltas.get(alliance.jv.industry, 0.0)
        alliance.jv.value = max(0.0, alliance.jv.value * (1 + delta))
        _sync_jv_value_share(state, alliance)


class AuditResult:
    """What an Audit reveals about the target's true financial position."""

    def __init__(
        self,
        target_id: str,
        cash: float,
        company: float,
        real_estate: float,
        gold: float,
        debt: float,
    ) -> None:
        """Snapshots one player's true breakdown at the moment of the Audit."""
        self.target_id = target_id
        self.cash = cash
        self.company = company
        self.real_estate = real_estate
        self.gold = gold
        self.debt = debt


def audit_player(state: GameState, auditor_id: str, target_id: str) -> AuditResult:
    """Pays to privately reveal a target's true financial breakdown.

    GDD.md Section 6/8.3 describes a fuller mechanic: a player Declares a
    claim about their own position, anyone can Audit that specific claim,
    and the cost is asymmetric (a failed audit refunds the auditor from the
    liar, a true one refunds the auditor from their own 5 cash). The only
    concretely-specified use of that in this project is Power Cards, which
    GDD.md Section 10 defers to v2 outright, and `sim/human_sim.py` never
    modeled a general claim/bluff system either, only a Power-Card-specific
    one. Rather than invent an unvalidated claim format, this implements
    the mechanic's other clearly-specified purpose directly (Section 6:
    "seeing two rivals' cash piles, by choosing to Audit them, is the game
    working as intended"): a flat-cost, always-succeeds reveal. The
    claim/bluff/caught-lying layer on top is a real gap, not a secret one -
    see the project README for what's still open.

    Args:
        state: The room's game state; the auditor's cash mutates.
        auditor_id: The player paying for the audit.
        target_id: The player being audited.

    Returns:
        The target's true cash, Company, Real Estate, Gold, and debt.

    Raises:
        ValueError: If the auditor can't afford the flat cost, or targets
            themselves.
    """
    if auditor_id == target_id:
        raise ValueError("a player cannot audit themselves")
    auditor = state.players[auditor_id]
    if auditor.cash < AUDIT_COST:
        raise ValueError(f"auditing costs {AUDIT_COST} cash")
    auditor.cash -= AUDIT_COST

    target = state.players[target_id]
    return AuditResult(
        target_id, target.cash, target.company, target.real_estate, target.gold, target.debt
    )
