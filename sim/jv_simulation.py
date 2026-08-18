"""Joint Venture betrayal-viability simulation (Python port + extension).

Ports the PowerShell tournament (jv_simulation.ps1) and adds a second variant testing a
"reputation tax" mechanic: repeat offenders (drainCount>=2) lose access to easy idle
income and get worse terms (reduced growth rate) on any JV they still manage to join.
Tests whether this closes the gap where reputation-aware/patient players were losing to
blind backstabbers.
"""

import csv
import os
import random

STRATEGIES = [
    "Loyalist",
    "Backstabber",
    "ReputationAware",
    "Grudger",
    "Opportunist",
    "EndgameRational",
]


def willing(strategy, partner_drain_count):
    """Reports whether a strategy will enter a JV with a given partner.

    Args:
        strategy: One of the `STRATEGIES` labels.
        partner_drain_count: How many times the prospective partner has
            drained a JV before.

    Returns:
        True if this strategy is willing to form the JV.

    Raises:
        ValueError: If `strategy` isn't a recognized strategy label.
    """
    if strategy in ("Loyalist", "Backstabber", "Opportunist"):
        return True
    if strategy == "ReputationAware":
        return partner_drain_count == 0
    if strategy == "Grudger":
        return partner_drain_count <= 1
    if strategy == "EndgameRational":
        return partner_drain_count == 0
    raise ValueError(strategy)


def will_drain(strategy, is_final, partner_drain_count, rounds_held):
    """Reports whether a strategy drains (betrays) its current JV this round.

    Args:
        strategy: One of the `STRATEGIES` labels.
        is_final: Whether this is the season's last round.
        partner_drain_count: How many times the current partner has
            drained a JV before.
        rounds_held: How many rounds this specific JV has been active.

    Returns:
        True if this strategy drains the JV this round.

    Raises:
        ValueError: If `strategy` isn't a recognized strategy label.
    """
    if strategy == "Loyalist":
        return False
    if strategy == "Backstabber":
        return rounds_held >= 1
    if strategy == "ReputationAware":
        return False
    if strategy == "Grudger":
        return False
    if strategy == "Opportunist":
        return True if partner_drain_count > 0 else is_final
    if strategy == "EndgameRational":
        return is_final
    raise ValueError(strategy)


def simulate_season(
    drain_bonus,
    growth_rate,
    rng,
    rounds=20,
    contribution=10.0,
    idle_yield=1.0,
    start_cash=100.0,
    rep_tax=False,
    tax_growth_penalty=0.05,
    rep_tax_threshold=2,
):
    """Simulates one season of JV formation, growth, and drains across all strategies.

    Args:
        drain_bonus: Fraction of a drained pot the drainer keeps.
        growth_rate: Per-round growth applied to each active JV's pot.
        rng: The season's random source.
        rounds: How many rounds the season runs for.
        contribution: Cash each partner puts in to form a JV.
        idle_yield: Cash earned per round by anyone not currently in a JV.
        start_cash: Each strategy's starting cash.
        rep_tax: Whether the reputation-tax mechanic is active.
        tax_growth_penalty: Growth-rate reduction applied to a JV involving
            a repeat offender, when `rep_tax` is on.
        rep_tax_threshold: Drain count at which a player is taxed.

    Returns:
        The final cash total for each strategy, indexed to match `STRATEGIES`.
    """
    n = len(STRATEGIES)
    cash = [start_cash] * n
    drain_count = [0] * n
    in_jv = [False] * n
    active = []

    for rnd in range(1, rounds + 1):
        is_final = rnd == rounds
        free = [i for i in range(n) if not in_jv[i]]
        rng.shuffle(free)
        for k in range(0, len(free) - 1, 2):
            a, b = free[k], free[k + 1]
            if willing(STRATEGIES[a], drain_count[b]) and willing(STRATEGIES[b], drain_count[a]):
                cash[a] -= contribution
                cash[b] -= contribution
                max_dur = rng.randint(2, 6)
                active.append(
                    {
                        "a": a,
                        "b": b,
                        "pot": 2 * contribution,
                        "rounds_held": 0,
                        "max_dur": max_dur,
                    }
                )
                in_jv[a] = True
                in_jv[b] = True

        for i in range(n):
            if not in_jv[i]:
                if rep_tax and drain_count[i] >= rep_tax_threshold:
                    continue  # ostracized: no easy idle income
                cash[i] += idle_yield

        still = []
        for jv in active:
            a, b = jv["a"], jv["b"]
            g = growth_rate
            if rep_tax and (
                drain_count[a] >= rep_tax_threshold or drain_count[b] >= rep_tax_threshold
            ):
                g = max(0.0, growth_rate - tax_growth_penalty)  # distrust discount
            jv["pot"] *= 1 + g
            jv["rounds_held"] += 1

            drain_a = will_drain(STRATEGIES[a], is_final, drain_count[b], jv["rounds_held"])
            drain_b = will_drain(STRATEGIES[b], is_final, drain_count[a], jv["rounds_held"])

            if drain_a and drain_b:
                cash[a] += 0.4 * jv["pot"]
                cash[b] += 0.4 * jv["pot"]
                drain_count[a] += 1
                drain_count[b] += 1
                in_jv[a] = False
                in_jv[b] = False
            elif drain_a:
                cash[a] += drain_bonus * jv["pot"]
                cash[b] += (1 - drain_bonus) * jv["pot"]
                drain_count[a] += 1
                in_jv[a] = False
                in_jv[b] = False
            elif drain_b:
                cash[b] += drain_bonus * jv["pot"]
                cash[a] += (1 - drain_bonus) * jv["pot"]
                drain_count[b] += 1
                in_jv[a] = False
                in_jv[b] = False
            elif jv["rounds_held"] >= jv["max_dur"] or is_final:
                cash[a] += 0.5 * jv["pot"]
                cash[b] += 0.5 * jv["pot"]
                in_jv[a] = False
                in_jv[b] = False
            else:
                still.append(jv)
        active = still

    return cash


def run_sweep(drain_bonus_values, growth_rate_values, num_trials, rep_tax, seed=42):
    """Runs `simulate_season` across every drain-bonus/growth-rate combination.

    Args:
        drain_bonus_values: Drain-bonus values to sweep over.
        growth_rate_values: Growth-rate values to sweep over.
        num_trials: How many independent seasons to average per combination.
        rep_tax: Whether the reputation-tax mechanic is active.
        seed: The random seed, for reproducible results.

    Returns:
        One result row per (drain_bonus, growth_rate, strategy) combination,
        with each strategy's average net worth and win rate.
    """
    rng = random.Random(seed)
    rows = []
    for db in drain_bonus_values:
        for gr in growth_rate_values:
            totals = {s: 0.0 for s in STRATEGIES}
            wins = {s: 0 for s in STRATEGIES}
            for _ in range(num_trials):
                cash = simulate_season(db, gr, rng, rep_tax=rep_tax)
                best_i = max(range(len(cash)), key=lambda i: cash[i])
                wins[STRATEGIES[best_i]] += 1
                for i, s in enumerate(STRATEGIES):
                    totals[s] += cash[i]
            for s in STRATEGIES:
                rows.append(
                    {
                        "DrainBonus": db,
                        "GrowthRate": gr,
                        "Strategy": s,
                        "AvgNetWorth": round(totals[s] / num_trials, 1),
                        "WinRatePct": round(100.0 * wins[s] / num_trials, 1),
                    }
                )
    return rows


def write_csv(rows, path):
    """Writes `run_sweep`'s result rows to a CSV file.

    Args:
        rows: The result rows to write, as produced by `run_sweep`.
        path: The output CSV file's path.
    """
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "DrainBonus",
                "GrowthRate",
                "Strategy",
                "AvgNetWorth",
                "WinRatePct",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    drain_bonus_values = [0.50, 0.60, 0.65, 0.70, 0.80, 0.95]
    growth_rate_values = [0.05, 0.10, 0.15, 0.20]
    num_trials = 500

    output_dir = os.path.dirname(os.path.abspath(__file__))

    baseline = run_sweep(drain_bonus_values, growth_rate_values, num_trials, rep_tax=False)
    write_csv(baseline, os.path.join(output_dir, "results_baseline.csv"))

    with_tax = run_sweep(drain_bonus_values, growth_rate_values, num_trials, rep_tax=True)
    write_csv(with_tax, os.path.join(output_dir, "results_reptax.csv"))

    print("DONE")
    print(f"baseline rows: {len(baseline)}, reptax rows: {len(with_tax)}")
