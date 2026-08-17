"""
Full-game "Power" simulation for the Live Mode redesign.

Tests the structural questions raised in design discussion:
- Does the Building Phase (no attacks) actually protect players from an
  early alliance rush?
- Can a solo player with enough raw Power beat an allied group, or are
  allies a hard requirement in practice?
- Does parking money in Real Estate actually protect it, i.e. is the
  liquid/protected asset split meaningful?
- Does "defender wins ties" (borrowed from Risk) matter?

Round structure per player, per round:
  1. INCOME: existing assets (company, real estate, stocks) generate cash.
  2. ALLOCATE: decide what to do with cash on hand (reinvest, diversify,
     save for a JV/attack, borrow).
  3. JV formation/resolution.
  4. Takeovers (Conflict Phase only).
Company/real-estate/stock values only grow when income is reinvested into
them — they don't also passively compound on top of that, which was a bug
in the first draft (cash was being treated as both "income" and "leftover
principal" at once, so spenders silently ran out of money to act with).

Archetypes (6-player pod, matching the "7 or fewer, Power Cards" format):
- Diversifier: spreads cash across company/real estate/stocks/JVs evenly.
- Turtle: dumps almost everything into Real Estate, avoids allies, plays safe.
- Aggressor: stays liquid, saves up, attacks the richest beatable target
  once the Conflict Phase opens.
- Socialite: prioritizes Joint Ventures with everyone, keeps cash spare for them.
- SoloGrinder: never allies, reinvests aggressively into company/stocks only.
- Leverager: borrows to amplify investment, real bankruptcy risk if overleveraged.
"""

import csv
import random

ARCHETYPES = [
    "Diversifier",
    "Turtle",
    "Aggressor",
    "Socialite",
    "SoloGrinder",
    "Leverager",
]

BUILDING_ROUNDS = 5
TOTAL_ROUNDS = 15
COMPANY_INCOME_RATE = 0.10  # "bank" growth as specified: ~10%/round, paid as income
REAL_ESTATE_INCOME_RATE = 0.05  # slower, but protected from takeover
STOCK_INCOME_RATE = 0.08  # tracks the target's growth, diluted
LOAN_INTEREST_BASE = 0.08
LOAN_RISK_PREMIUM = (
    0.35  # extra interest per unit of leverage ratio (debt/power) — real risk pricing
)
BANKRUPTCY_LIQUIDATION_PCT = 0.85
JV_DRAIN_BONUS = 0.65  # from the earlier, validated JV-only simulation
JV_GROWTH = 0.12
REP_TAX_THRESHOLD = 2
TAKEOVER_CAPTURE_PCT = (
    0.25  # attacker takes this fraction of defender's liquid+company power
)
DEFENDER_TIE_BONUS = 1.05  # "defender wins ties" (Risk-inspired)
ATTACK_FAIL_LOSS_PCT = (
    0.5  # attacker loses this fraction of committed stake on a failed attack
)
POST_ATTACK_SHIELD_ROUNDS = (
    2  # rounds of immunity after being successfully taken over — no perpetual farming
)


class Player:
    def __init__(self, idx, archetype):
        self.idx = idx
        self.archetype = archetype
        self.cash = 20.0
        self.company = 80.0
        self.real_estate = 0.0
        self.stocks = {}  # target_idx -> amount invested
        self.debt = 0.0
        self.captured = 0.0
        self.drain_count = 0
        self.allies = set()
        self.bankrupt = False
        self.shielded_until_round = 0

    def total_power(self):
        return (
            self.cash
            + self.company
            + self.real_estate
            + sum(self.stocks.values())
            + self.captured
            - self.debt
        )


def generate_income(p):
    income = (
        p.company * COMPANY_INCOME_RATE
        + p.real_estate * REAL_ESTATE_INCOME_RATE
        + sum(p.stocks.values()) * STOCK_INCOME_RATE
    )
    p.cash += income

    if p.debt > 0 and not p.bankrupt:
        pre_debt_power = (
            p.cash + p.company + p.real_estate + sum(p.stocks.values()) + p.captured
        )
        leverage_ratio = p.debt / max(1.0, pre_debt_power)
        rate = LOAN_INTEREST_BASE + LOAN_RISK_PREMIUM * leverage_ratio
        p.debt *= 1 + rate

    if p.total_power() < 0 and not p.bankrupt:
        p.bankrupt = True
        p.cash *= 1 - BANKRUPTCY_LIQUIDATION_PCT
        p.company *= 1 - BANKRUPTCY_LIQUIDATION_PCT
        p.real_estate *= 1 - BANKRUPTCY_LIQUIDATION_PCT
        for k in p.stocks:
            p.stocks[k] *= 1 - BANKRUPTCY_LIQUIDATION_PCT
        p.debt = 0.0  # discharged in the workout — diminished but stable, not a spiral


def allocate(p, players, rng):
    cash_available = p.cash
    if p.archetype == "Diversifier":
        p.company += cash_available * 0.35
        p.real_estate += cash_available * 0.30
        target = rng.choice([q for q in players if q.idx != p.idx])
        p.stocks[target.idx] = p.stocks.get(target.idx, 0) + cash_available * 0.20
        p.cash = cash_available * 0.15
    elif p.archetype == "Turtle":
        p.real_estate += cash_available * 0.70
        p.company += cash_available * 0.20
        p.cash = cash_available * 0.10
    elif p.archetype == "Aggressor":
        p.company += cash_available * 0.30
        p.cash = cash_available * 0.70  # stays liquid, hoarding attack power
    elif p.archetype == "Socialite":
        p.company += cash_available * 0.30
        p.real_estate += cash_available * 0.15
        p.cash = cash_available * 0.55  # kept available for JV contributions
    elif p.archetype == "SoloGrinder":
        p.company += cash_available * 0.55
        target = rng.choice([q for q in players if q.idx != p.idx])
        p.stocks[target.idx] = p.stocks.get(target.idx, 0) + cash_available * 0.35
        p.cash = cash_available * 0.10
    elif p.archetype == "Leverager":
        if p.bankrupt:
            p.company += cash_available * 0.5
            p.cash = cash_available * 0.5
            return
        power = max(1.0, p.total_power())
        current_leverage = p.debt / power
        loan_amount = power * 0.15 if current_leverage < 0.6 else 0.0
        p.debt += loan_amount
        p.company += (cash_available + loan_amount) * 0.7
        p.cash = (cash_available + loan_amount) * 0.3


def try_form_jv(p, players, rng):
    if p.archetype not in ("Socialite", "Diversifier"):
        return
    if len(p.allies) >= 2:
        return
    candidates = [
        q
        for q in players
        if q.idx != p.idx
        and q.idx not in p.allies
        and q.drain_count < REP_TAX_THRESHOLD
    ]
    if not candidates:
        return
    partner = rng.choice(candidates)
    if p.cash > 10 and partner.archetype in ("Socialite", "Diversifier", "Turtle"):
        p.allies.add(partner.idx)
        partner.allies.add(p.idx)


def resolve_jvs(players, rng, is_final_round):
    for p in players:
        for ally_idx in list(p.allies):
            if ally_idx < p.idx:
                continue  # process each pair once
            q = players[ally_idx]
            if p.cash < 5 or q.cash < 5:
                continue
            pot = 10.0
            p.cash -= 5
            q.cash -= 5
            pot *= 1 + JV_GROWTH

            p_drains = (p.archetype == "Aggressor" and rng.random() < 0.3) or (
                is_final_round and rng.random() < 0.4
            )
            q_drains = (q.archetype == "Aggressor" and rng.random() < 0.3) or (
                is_final_round and rng.random() < 0.4
            )

            if p_drains and not q_drains:
                p.cash += JV_DRAIN_BONUS * pot
                q.cash += (1 - JV_DRAIN_BONUS) * pot
                p.drain_count += 1
            elif q_drains and not p_drains:
                q.cash += JV_DRAIN_BONUS * pot
                p.cash += (1 - JV_DRAIN_BONUS) * pot
                q.drain_count += 1
            elif p_drains and q_drains:
                p.cash += 0.4 * pot
                q.cash += 0.4 * pot
                p.drain_count += 1
                q.drain_count += 1
            else:
                p.cash += 0.5 * pot
                q.cash += 0.5 * pot


def defense_power_of(target, players):
    # real estate is the "protected" asset class by design — it should actually protect
    dp = target.real_estate * 0.9 + target.cash * 0.3
    for ally_idx in target.allies:
        ally = players[ally_idx]
        dp += ally.cash * 0.3
    return dp * DEFENDER_TIE_BONUS


def attempt_takeovers(players, rng, current_round):
    attackers = [
        p
        for p in players
        if p.archetype in ("Aggressor", "Leverager") and p.cash > 15 and not p.bankrupt
    ]
    for attacker in attackers:
        candidates = [
            q
            for q in players
            if q.idx != attacker.idx and current_round > q.shielded_until_round
        ]
        if not candidates:
            continue

        support = 0.0
        if attacker.archetype != "SoloGrinder":
            for ally_idx in attacker.allies:
                support += players[ally_idx].cash * 0.3
        attack_power = attacker.cash * 0.5 + support

        # a rational attacker hunts the richest target they can actually beat,
        # not just whoever has the lowest total power
        beatable = [
            q for q in candidates if attack_power > defense_power_of(q, players)
        ]
        if not beatable:
            continue
        target = max(beatable, key=lambda q: q.cash + q.company)

        defense_power = defense_power_of(target, players)
        stake = attacker.cash * 0.5
        if attack_power > defense_power:
            captured = TAKEOVER_CAPTURE_PCT * (target.cash + target.company)
            target.cash = max(0.0, target.cash - captured * 0.5)
            target.company = max(0.0, target.company - captured * 0.5)
            target.shielded_until_round = current_round + POST_ATTACK_SHIELD_ROUNDS
            attacker.captured += captured
            attacker.cash -= stake * 0.2
        else:
            attacker.cash -= stake * ATTACK_FAIL_LOSS_PCT


LEADER_THREATENED_MARGIN = (
    1.3  # leader is "worth ganging up on" once this far ahead of 2nd place
)


def attempt_counter_attacks(players, rng, current_round):
    """
    Anyone (not just Aggressor/Leverager) can take a shot at a runaway leader.
    Models real-player behavior a fixed-archetype tournament otherwise can't:
    people gang up on whoever's winning too much, they don't just let it happen.
    """
    ranked = sorted(players, key=lambda p: p.total_power(), reverse=True)
    leader = ranked[0]
    if len(ranked) < 2:
        return
    second_power = max(1.0, ranked[1].total_power())
    if leader.total_power() < second_power * LEADER_THREATENED_MARGIN:
        return  # nobody's far enough ahead to be worth ganging up on yet

    if current_round <= leader.shielded_until_round:
        return

    challengers = [
        p
        for p in players
        if p.idx != leader.idx
        and p.archetype
        not in ("Aggressor", "Leverager")  # those already got their shot above
        and p.cash > 10
        and not p.bankrupt
    ]
    for challenger in challengers:
        support = sum(players[a].cash * 0.3 for a in challenger.allies)
        # a determined coalition will liquidate some company value to fund a strike,
        # not just whatever loose cash happens to be sitting around
        mobilized = challenger.cash * 0.4 + challenger.company * 0.15
        attack_power = mobilized + support
        defense_power = defense_power_of(leader, players)
        if attack_power > defense_power:
            captured = TAKEOVER_CAPTURE_PCT * (leader.cash + leader.company)
            leader.cash = max(0.0, leader.cash - captured * 0.5)
            leader.company = max(0.0, leader.company - captured * 0.5)
            leader.shielded_until_round = current_round + POST_ATTACK_SHIELD_ROUNDS
            challenger.captured += captured
            challenger.company -= (
                mobilized * 0.2
            )  # the mobilized stake was drawn from the company itself
            return  # one successful pile-on per round is enough to matter
        else:
            challenger.company -= mobilized * ATTACK_FAIL_LOSS_PCT * 0.3


def simulate_game(rng):
    players = [Player(i, ARCHETYPES[i]) for i in range(len(ARCHETYPES))]
    takeover_attempts = 0
    takeover_successes = 0

    for rnd in range(1, TOTAL_ROUNDS + 1):
        is_building = rnd <= BUILDING_ROUNDS
        is_final = rnd == TOTAL_ROUNDS

        for p in players:
            generate_income(p)
        for p in players:
            allocate(p, players, rng)
        for p in players:
            try_form_jv(p, players, rng)
        resolve_jvs(players, rng, is_final)

        if not is_building:
            before = {p.idx: p.captured for p in players}
            attempt_takeovers(players, rng, rnd)
            attempt_counter_attacks(players, rng, rnd)
            for p in players:
                if p.captured > before[p.idx]:
                    takeover_successes += 1

        for p in players:
            p.cash = max(0.0, p.cash)

    return players, takeover_attempts, takeover_successes


def run_trials(num_trials, seed=7):
    rng = random.Random(seed)
    win_counts = {a: 0 for a in ARCHETYPES}
    total_power = {a: 0.0 for a in ARCHETYPES}
    solo_beats_allied = 0
    solo_trials_with_allied_rivals = 0
    total_successful_takeovers = 0

    for _ in range(num_trials):
        players, _, successes = simulate_game(rng)
        total_successful_takeovers += successes
        powers = [(p.total_power(), p) for p in players]
        powers.sort(key=lambda t: t[0], reverse=True)
        winner = powers[0][1]
        win_counts[winner.archetype] += 1
        for p in players:
            total_power[p.archetype] += p.total_power()

        solo = next(p for p in players if p.archetype == "SoloGrinder")
        allied_rivals = [p for p in players if len(p.allies) > 0 and p.idx != solo.idx]
        if allied_rivals:
            solo_trials_with_allied_rivals += 1
            if solo.total_power() > max(q.total_power() for q in allied_rivals):
                solo_beats_allied += 1

    rows = []
    for a in ARCHETYPES:
        rows.append(
            {
                "Archetype": a,
                "WinRatePct": round(100.0 * win_counts[a] / num_trials, 1),
                "AvgPower": round(total_power[a] / num_trials, 1),
            }
        )
    solo_pct = (
        round(100.0 * solo_beats_allied / solo_trials_with_allied_rivals, 1)
        if solo_trials_with_allied_rivals
        else 0.0
    )
    avg_takeovers = round(total_successful_takeovers / num_trials, 2)
    return rows, solo_pct, avg_takeovers


if __name__ == "__main__":
    rows, solo_pct, avg_takeovers = run_trials(2000)
    with open("d:/Game/sim/power_results.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["Archetype", "WinRatePct", "AvgPower"])
        writer.writeheader()
        writer.writerows(rows)

    print("=== Archetype performance (2000 trials) ===")
    for r in sorted(rows, key=lambda r: -r["WinRatePct"]):
        print(
            f"{r['Archetype']:<12} win rate {r['WinRatePct']:>5}%   avg power {r['AvgPower']:>7}"
        )
    print(
        f"\nSoloGrinder beats the strongest allied rival in {solo_pct}% of games where allied rivals exist."
    )
    print(f"Average successful takeovers per game: {avg_takeovers}")
