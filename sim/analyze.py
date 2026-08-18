"""Compares Backstabber's net worth and win rate against the best honest archetype.

Reads the reputation-tax sweep's CSV output (baseline vs. with-tax) and reports,
for each DrainBonus/GrowthRate combination, whether an honest strategy actually
out-earns Backstabber once the reputation tax is applied.
"""

import csv
import os
from collections import defaultdict

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
HONEST = ["Loyalist", "ReputationAware", "Grudger", "EndgameRational"]


def load(path):
    """Loads one sweep CSV into a dict keyed by (DrainBonus, GrowthRate).

    Args:
        path: Path to the sweep's output CSV.

    Returns:
        A dict mapping (drain_bonus, growth_rate) to a dict of
        strategy name -> {"AvgNetWorth", "WinRatePct"}.
    """
    data = defaultdict(dict)
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            key = (float(row["DrainBonus"]), float(row["GrowthRate"]))
            data[key][row["Strategy"]] = {
                "AvgNetWorth": float(row["AvgNetWorth"]),
                "WinRatePct": float(row["WinRatePct"]),
            }
    return data


def report(path, label):
    """Prints a per-combination comparison of Backstabber vs. the best honest strategy.

    Args:
        path: Path to the sweep's output CSV.
        label: A human-readable label for this report's header.
    """
    data = load(path)
    print(f"\n=== {label} ===")
    print(
        f"{'DrainBonus':>10} {'GrowthRate':>10} {'Backstabber NW':>15} "
        f"{'BestHonest':>16} {'BestHonest NW':>14} {'Gap':>8} "
        f"{'BS WinRate':>11} {'BestHonest WinRate':>19}"
    )
    for key in sorted(data.keys()):
        db, gr = key
        s = data[key]
        bs_nw = s["Backstabber"]["AvgNetWorth"]
        bs_wr = s["Backstabber"]["WinRatePct"]
        best_honest = max(HONEST, key=lambda h: s[h]["AvgNetWorth"])
        best_nw = s[best_honest]["AvgNetWorth"]
        best_wr = s[best_honest]["WinRatePct"]
        gap = round(best_nw - bs_nw, 1)
        flag = "HONEST WINS" if gap > 0 else "backstabber wins"
        print(
            f"{db:>10} {gr:>10} {bs_nw:>15} {best_honest:>16} {best_nw:>14} "
            f"{gap:>8} {bs_wr:>10}% {best_wr:>18}%  [{flag}]"
        )


if __name__ == "__main__":
    report(os.path.join(OUTPUT_DIR, "results_baseline.csv"), "BASELINE (no reputation tax)")
    report(os.path.join(OUTPUT_DIR, "results_reptax.csv"), "WITH REPUTATION TAX")
