"""The Hidden Raider, Board Observer/Co-Founder, and Final Round win logic.

GDD.md Sections 8.2, 8.4, 8.5. Ports the math `sim/human_sim.py` validated
for these mechanics. Two behaviors the simulation modeled as bot heuristics
are deliberately not ported, since a real player just does them directly
through the API instead of needing mechanical support: a Raider preferring
their own target when choosing who to attack (GDD.md Section 8.2, "you're
never just wondering whether an ally will choose greed"), and a Raider
withholding Defense Pact support from their target (`consider_raider_pact_break`
in the sim) - a real Raider decides both for themselves.
"""

import random

from app.core.constants import (
    CO_FOUNDER_BUYOUT_CASH_MULTIPLE,
    CO_FOUNDER_BUYOUT_PREMIUM,
    CO_FOUNDER_EQUITY_RATE,
    CO_FOUNDER_PARACHUTE_PCT,
    CO_FOUNDER_RE_NUDGE,
    MIN_PLAYERS_FOR_RAIDER,
    RAIDER_RATIO,
    RAIDER_TARGET_POWER_FRACTION,
    WIN_TIE_EPSILON,
)
from app.models.game import GameState, Player


def assign_raiders(state: GameState, rng: random.Random) -> None:
    """Secretly assigns a minority of players as Raiders, each with a hidden target.

    A no-op below `MIN_PLAYERS_FOR_RAIDER` players, the same floor GDD.md
    Section 8.2 states this role needs to make sense.

    Args:
        state: The room's game state; the chosen players mutate in place.
        rng: The room's seeded random source.
    """
    players = list(state.players.values())
    if len(players) < MIN_PLAYERS_FOR_RAIDER:
        return
    n_raiders = max(1, round(len(players) * RAIDER_RATIO))
    for raider in rng.sample(players, min(n_raiders, len(players))):
        target = rng.choice([p for p in players if p.id != raider.id])
        raider.is_raider = True
        raider.raider_target_id = target.id


def raider_succeeded(raider: Player, state: GameState) -> bool:
    """Checks a Raider's real, hidden win condition at game end.

    Args:
        raider: The player to check.
        state: The room's game state.

    Returns:
        True if their target ended the game bankrupt-equivalent (broke) or
        well below the table's average Power.
    """
    if raider.raider_target_id is None:
        return False
    target = state.players.get(raider.raider_target_id)
    if target is None:
        return False
    if target.is_broke():
        return True
    players = list(state.players.values())
    avg_power = sum(p.total_power() for p in players) / len(players)
    return target.total_power() < avg_power * RAIDER_TARGET_POWER_FRACTION


def recruit_co_founder(state: GameState, host_id: str, broke_player_id: str) -> None:
    """A living player recruits a Board Observer to actively co-run their company.

    Args:
        state: The room's game state; the recruit's `co_founder_of` mutates.
        host_id: The recruiting (living, solvent) player.
        broke_player_id: The Board Observer being recruited.

    Raises:
        ValueError: If the recruit isn't actually broke, already has a host,
            the host is themselves broke, or the host already has a
            co-founder (one per host, GDD.md Section 8.4).
    """
    host = state.players[host_id]
    recruit = state.players[broke_player_id]
    if not recruit.is_broke():
        raise ValueError("only a Board Observer can be recruited as a co-founder")
    if recruit.co_founder_of is not None:
        raise ValueError("that Board Observer already co-founds for someone else")
    if host.is_broke():
        raise ValueError("a Board Observer cannot recruit another one")
    if any(p.co_founder_of == host_id for p in state.players.values()):
        raise ValueError("this host already has a co-founder")

    recruit.co_founder_of = host_id
    recruit.backing_id = None  # recruited is the better outcome; supersedes a fallback backing pick


def apply_co_founder_influence(state: GameState) -> None:
    """Runs every co-founder's real, repeated job: steering the host toward Real Estate.

    Also marks every co-founder's equity to their host's current Company
    value. Called once per round, alongside the rest of the round's
    automatic resolution (GDD.md Section 8.4).

    Args:
        state: The room's game state; hosts and co-founders mutate in place.
    """
    for player in state.players.values():
        if player.co_founder_of is None:
            continue
        host = state.players.get(player.co_founder_of)
        if host is None or host.is_broke():
            player.co_founder_of = None
            player.co_founder_equity = 0.0
            continue

        nudge = min(host.cash * CO_FOUNDER_RE_NUDGE, host.cash)
        host.cash -= nudge
        host.real_estate += nudge
        player.co_founder_equity = host.company * CO_FOUNDER_EQUITY_RATE


def co_founder_buyout_cost(state: GameState, co_founder_id: str) -> float:
    """Computes what it currently costs a host to buy out their co-founder.

    Args:
        state: The room's game state.
        co_founder_id: The co-founder being bought out.

    Returns:
        The buyout price: their current equity, plus a premium.
    """
    return state.players[co_founder_id].co_founder_equity * CO_FOUNDER_BUYOUT_PREMIUM


def buy_out_co_founder(state: GameState, host_id: str, co_founder_id: str) -> float:
    """A host buys their co-founder out entirely, freeing both of them.

    Args:
        state: The room's game state; both players' cash mutates.
        host_id: The host paying for the buyout.
        co_founder_id: The co-founder being bought out.

    Returns:
        The price actually paid.

    Raises:
        ValueError: If this player isn't actually the co-founder's host, or
            the host can't comfortably afford the buyout yet.
    """
    co_founder = state.players[co_founder_id]
    if co_founder.co_founder_of != host_id:
        raise ValueError("that player isn't your co-founder")
    host = state.players[host_id]
    cost = co_founder_buyout_cost(state, co_founder_id)
    if host.cash < cost * CO_FOUNDER_BUYOUT_CASH_MULTIPLE:
        raise ValueError("not enough spare cash for a buyout yet")

    host.cash -= cost
    co_founder.cash += cost
    co_founder.co_founder_of = None
    co_founder.co_founder_equity = 0.0
    return cost


def apply_golden_parachute(state: GameState, host_id: str, captured: float) -> float | None:
    """Pays a captured host's co-founder a severance if the host is successfully attacked.

    Args:
        state: The room's game state; the co-founder's cash mutates.
        host_id: The player who was just successfully attacked.
        captured: How much was captured from them.

    Returns:
        The payout, or None if that host had no active co-founder.
    """
    co_founder = next((p for p in state.players.values() if p.co_founder_of == host_id), None)
    if co_founder is None:
        return None
    payout = captured * CO_FOUNDER_PARACHUTE_PCT
    co_founder.cash += payout
    co_founder.co_founder_of = None
    co_founder.co_founder_equity = 0.0
    return payout


def back_player(state: GameState, backer_id: str, target_id: str) -> None:
    """A Board Observer picks a living player to root for (GDD.md Section 8.4).

    Purely social: no cash or Power changes hands. Only touches the Final
    Round tiebreak (`determine_winner`).

    Args:
        state: The room's game state; the backer's `backing_id` mutates.
        backer_id: The Board Observer making the pick.
        target_id: The living player they're backing.

    Raises:
        ValueError: If the backer isn't actually broke, or the target is.
    """
    backer = state.players[backer_id]
    target = state.players[target_id]
    if not backer.is_broke():
        raise ValueError("only a Board Observer backs a player")
    if target.is_broke():
        raise ValueError("cannot back another Board Observer")
    backer.backing_id = target_id


def determine_winner(state: GameState) -> Player:
    """Picks the winner: highest total Power, ties broken by Board Observer backing.

    Args:
        state: The room's game state.

    Returns:
        The winning player.
    """
    ranked = sorted(state.players.values(), key=lambda p: p.total_power(), reverse=True)
    if len(ranked) < 2 or ranked[0].total_power() - ranked[1].total_power() > WIN_TIE_EPSILON:
        return ranked[0]

    tied_ids = {
        p.id for p in ranked if ranked[0].total_power() - p.total_power() <= WIN_TIE_EPSILON
    }
    votes = dict.fromkeys(tied_ids, 0)
    for player in state.players.values():
        if player.backing_id in votes:
            votes[player.backing_id] += 1
    winner_id = max(votes, key=lambda pid: votes[pid])
    return state.players[winner_id]
