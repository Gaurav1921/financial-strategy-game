import csv
from collections import defaultdict

HONEST = ["Loyalist", "ReputationAware", "Grudger", "EndgameRational"]


def load(path):
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
    data = load(path)
    print(f"\n=== {label} ===")
    print(
        f"{'DrainBonus':>10} {'GrowthRate':>10} {'Backstabber NW':>15} {'BestHonest':>16} {'BestHonest NW':>14} {'Gap':>8} {'BS WinRate':>11} {'BestHonest WinRate':>19}"
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
            f"{db:>10} {gr:>10} {bs_nw:>15} {best_honest:>16} {best_nw:>14} {gap:>8} {bs_wr:>10}% {best_wr:>18}%  [{flag}]"
        )


report("d:/Game/sim/results_baseline.csv", "BASELINE (no reputation tax)")
report("d:/Game/sim/results_reptax.csv", "WITH REPUTATION TAX")
