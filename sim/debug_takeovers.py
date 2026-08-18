"""Debug trace of one power_simulation.py game, round by round.

Prints every takeover attempt and each player's stats during the Conflict
Phase. Only exercises power_simulation.py's fixed-bot path, it never calls
attempt_counter_attacks and doesn't reflect human_sim.py's richer,
validated mechanics.
"""

import random

from power_simulation import (
    ARCHETYPES,
    BUILDING_ROUNDS,
    TOTAL_ROUNDS,
    Player,
    allocate,
    attempt_takeovers,
    defense_power_of,
    generate_income,
    resolve_jvs,
    try_form_jv,
)

rng = random.Random(7)
players = [Player(i, ARCHETYPES[i]) for i in range(len(ARCHETYPES))]

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
        before_captured = {p.idx: p.captured for p in players}
        before_cash = {p.idx: p.cash for p in players}
        attempt_takeovers(players, rng, rnd)
        for p in players:
            if p.captured > before_captured[p.idx]:
                gain = p.captured - before_captured[p.idx]
                print(f"round {rnd}: {p.archetype} SUCCEEDS, captures {gain:.1f}")
        for p in players:
            if (
                p.archetype in ("Aggressor", "Leverager")
                and p.captured == before_captured[p.idx]
                and before_cash[p.idx] > 15
            ):
                print(f"round {rnd}: {p.archetype} attacked and FAILED (or had no beatable target)")

    if not is_building:
        for q in players:
            print(
                f"   {q.archetype:<12} cash={q.cash:6.1f} company={q.company:7.1f} "
                f"RE={q.real_estate:6.1f} defense={defense_power_of(q, players):7.1f} "
                f"power={q.total_power():7.1f}"
            )
