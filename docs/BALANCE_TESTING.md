# Balance Testing - Joint Ventures & Betrayal Viability

## Method
A strategy tournament, not a spreadsheet guess. 6 archetypes share a pod and
play a season (20 rounds) of forming Joint Ventures (JVs), deciding each
round whether to hold or drain, under our proposed rules. Every parameter
combination was run 500 times (random pairing, random JV duration) and
averaged. Code: `sim/jv_simulation.py`, raw output: `sim/results_baseline.csv`
and `sim/results_reptax.csv`.

**Archetypes tested:**
- **Loyalist** - always holds, partners with anyone (the naive/trusting player).
- **Backstabber** - drains the first chance it gets, partners with anyone.
- **ReputationAware** - never drains, refuses to partner with anyone who's
  ever drained before (zero tolerance).
- **Grudger** - never drains, tolerates one prior offense, refuses after two.
- **Opportunist** - holds normally, but drains pre-emptively against
  bad-reputation partners, and always drains in the final round.
- **EndgameRational** - holds honestly and picks safe partners like
  ReputationAware, but always drains in the final round.

**What was swept:** `DrainBonus` (the % of the pot a drainer keeps - the
core "how tempting is betrayal" dial) from 0.50 to 0.95, and `GrowthRate`
(the % the pot compounds per round while both hold - the "how much does
patience pay" dial) from 0.05 to 0.20.

## Finding 1: the original design (v3, no reputation consequence beyond
partner refusal) breaks down fast
With only "refuse to partner with known offenders" as the punishment,
**blind Backstabber wins outright once DrainBonus reaches ~0.7**, regardless
of growth rate, and even at 0.6 it wins when growth is slow. Refusing to
deal with bad actors just means honest players get fewer opportunities -
it doesn't actually cost the offender enough. This is exactly the collapse
the original "why would anyone ally" critique predicted, and the numbers
confirm it's real, not hypothetical.

## Finding 2: a concrete reputation tax fixes it
Added mechanic, tested as `rep_tax` in the sim: once a player has been
caught draining **2+ times** (publicly visible, matches the GDD's existing
"reputation is visible to the pod" framing), they (a) lose access to safe
idle income - nobody offers them easy deals anymore - and (b) any JV they
still manage to form runs at a **5-percentage-point lower growth rate**
(partners who deal with a known offender anyway protect themselves by
under-investing). This is a small, explainable rule, not a big rewrite.

With it, the "honest strategies win" region expands dramatically - up to
DrainBonus 0.7 across every growth rate tested, and 0.8 in most of them.

## Finding 3: EndgameRational is the strongest honest strategy, consistently
Across almost every viable setting, the best-performing honest archetype
isn't pure Loyalist or strict ReputationAware - it's **EndgameRational**:
play honestly and by-the-reputation-book all season, then take the
expected defection in the guaranteed final round. This directly confirms
the GDD's Section 4.6 design intent (the final round is deliberately
different, and rational endgame defection is a feature, not a flaw) with
actual numbers, not just game-theory citations. It also means onboarding
needs to explicitly teach "the final round works differently" - a player
who stays purely honest through the finale will systematically underperform
players who don't.

## Finding 4: blind trust still gets punished, and betrayal never goes to zero
At high DrainBonus, Loyalist (never checks reputation) consistently posts
the lowest net worth of any strategy - confirms naive trust is a losing
strategy, matching the intended "read your allies or pay for it" tension.
Backstabber's win rate never drops to 0% in any tested setting (it stays a
real, occasionally-winning strategy, typically 5–30% in the recommended
range below) - betrayal remains genuinely tempting, it's just not the
dominant strategy anymore.

## Recommended numbers (with reputation tax enabled)

| Parameter | Recommended value | Why |
|---|---|---|
| Joint Venture drain bonus | **65%** (drainer keeps 65% of pot, partner gets 35%) | Comfortably inside the honest-favorable zone (0.6–0.7 all favor honest play with the tax on) while still being a meaningfully large temptation over a fair 50/50 split |
| Joint Venture growth rate | **12%/round held** | Mid-point of the tested range where patience clearly outpaces smash-and-grab; below ~10% patience stops paying off fast enough |
| Reputation tax threshold | **2 proven drains** | Matches Grudger's one-offense tolerance in the model; harsh enough to bite, not so harsh a single mistake ends a player |
| Reputation tax penalty | **–5 percentage points growth rate** on any JV a repeat offender still finds, **no idle income** while ostracized | Smallest penalty that flipped the outcome in testing - no need to go harsher |
| Final round | **Mechanically distinct**, defection there should be expected/telegraphed to players | EndgameRational's edge over pure-honest strategies is real and consistent - the tutorial should say so explicitly rather than let players discover it the hard way |

## What this doesn't cover yet (as of Part 1)
- Syndicate Move / Takeover threshold math - addressed below in Part 2.
- Hidden Raider role's effect on these numbers - this tournament assumed
  everyone shares the same win condition (net worth). Raiders whose
  incentives differ could shift the equilibrium and haven't been tested.
- Real players aren't fixed strategies - they adapt mid-season. This
  validates the rules are sound in principle, not that human play will
  feel exactly like this.

---

# Part 2 - Power Score & Takeover Simulation (Live Mode redesign)

## Iteration log, at a glance
Every one of these was a real bug or exploit caught by running the numbers,
not a hypothetical - each row is: what broke, how we know, what fixed it.

| # | What broke | How we caught it | Fix |
|---|---|---|---|
| 1 | Money wasn't actually being earned each round - archetypes that spent aggressively silently ran out of cash to act with | Debug trace showed cash converging to ~0 within a few rounds for high-reinvestment archetypes | Split the round into a proper income step, then an allocation step |
| 2 | Loans were free money forever - borrowed cash grew faster than its own interest, zero risk | Leverager won 100% of 2000 simulated games with a flat interest rate | Interest now scales with leverage; overleveraging triggers real bankruptcy |
| 3 | Attackers targeted the overall-poorest player, hiding the real risk to rich-but-undefended players | Numbers looked "fine" until targeting was corrected to hunt the richest *beatable* mark | Attackers now go after the richest target they can actually beat |
| 4 | Real Estate didn't actually protect anyone (equal weight to cash in defense); takeovers landed 10/10 conflict rounds, same victim farmed every round | Round-by-round trace showed one player pinned near-zero growth for the entire back half of the game | Real Estate now weighted far higher in defense; added a 2-round shield after being hit |
| 5 | Even after all of the above, one aggressive archetype still won 100% of games, because nobody else ever fought back | Win rate stayed 100% for Aggressor even with Building Phase + shield in place | Added "gang up on the runaway leader" behavior for everyone, not just dedicated attackers - see below |

## Method
A second, bigger simulation (`sim/power_simulation.py`) models a full
6-player Live Mode game (15 rounds: 5-round Building Phase, then 10-round
Conflict Phase) using the full Power system - Company, Real Estate, Stocks,
Loans, Joint Ventures, and Takeovers all active together, not just Joint
Ventures in isolation. Six fixed archetypes played 2000 simulated games:
Diversifier, Turtle (real-estate-heavy), Aggressor (attacks weak targets),
Socialite (alliance-focused), SoloGrinder (no allies, aggressive solo
reinvestment), Leverager (borrows to amplify investment).

**Important caveat up front:** these are fixed, non-adaptive bots. A real
human who noticed they were being repeatedly targeted would start
diversifying into Real Estate or seek allies - these bots never adapt
mid-game. So this tournament is good for finding *structural* problems in
the rules (exploits, dead mechanics, runaway snowballs) - it is not a
claim that real friend-group games will play out exactly like this.

## Finding 1: the first draft had a real bug, not just a balance issue
Initial version conflated "cash on hand" with "income" - money spent each
round was never replenished by a separate income step, so archetypes that
reinvested aggressively silently ran out of cash to act with within a few
rounds. Fixed by splitting the round into a proper **income phase** (assets
generate cash each round) followed by an **allocation phase** (decide what
to do with that cash) - this is now how the real game's round structure
should work too, not just the simulation.

## Finding 2: naive loans were a free lunch
With flat 8% interest against 10% company growth, the **Leverager archetype
won 100% of games** with no real downside - borrowed money grew faster than
its own interest, forever, with zero risk. Real financial leverage isn't
like that: it's profitable exactly until it isn't. Fixed by pricing loan
interest by leverage (rate rises the more indebted you are relative to your
total power) and adding a real **bankruptcy** consequence: if debt exceeds
total power, creditors seize ~85% of holdings and the remaining debt is
discharged (a diminished but stable state, matching the Ghost/Observer
design - not an infinite debt spiral). After the fix, Leverager becomes a
high-variance, generally weak archetype - leverage should be a real risk
players can lose to, not a strictly-better move.

## Finding 3: naive attacker targeting hid the real risk to undefended players
Attackers initially targeted whoever had the lowest *total* power - which
meant a player who was rich but totally undefended (no Real Estate at all)
was never actually picked on, hiding the real question. Fixed by having
attackers target the **richest target they can actually beat** (comparing
attack power against each candidate's defense) - a much more realistic
"go after the juiciest weak mark" heuristic.

## Finding 4: Real Estate wasn't actually protective, and Takeovers landed
almost every round
With that fixed targeting, two problems showed up together: Real Estate
counted equally to cash in defense (defeating its whole purpose as "the
safe asset"), and takeovers were succeeding essentially every single
Conflict Phase round (10 out of 10) - because SoloGrinder and Leverager (no
Real Estate at all) were always sitting there as free, permanently
exploitable targets. **Aggressor farmed the same undefended victims every
round for the rest of the game and snowballed to more than double everyone
else's power.** This is exactly the "veterans farm weak players forever"
failure mode our own market research flagged as the top complaint in this
genre (see MARKET_RESEARCH.md) - the simulation reproduced it organically,
which is a strong signal it's a real risk, not a hypothetical one.

**Fixes applied, both validated by the numbers:**
- Real Estate now counts far more toward defense than cash (0.9x vs 0.3x
  per unit) - it's the asset that's actually supposed to protect you.
- A **Post-Attack Shield**: after being successfully taken over, a player
  is immune to further takeovers for 2 rounds - the same "protect the
  weak" logic as the Building Phase, applied per-player after a hit instead
  of just at the start of the game.

With both in place: successful takeovers per game dropped from 10 to 7,
and the previously-permanently-farmed SoloGrinder's average power
recovered from 178.8 to 277.9 - a real, measured improvement, though not a
full fix (see below).

## Finding 5 (fixed): a lone unopposed attacker was snowballing - because
nobody else could fight back
Even with all the fixes above, Aggressor still won 100% of simulated games
(avg power 528 vs. next-best 345). Root cause, confirmed by instrumenting
the sim: **only the Aggressor/Leverager archetypes had any "attack" logic
at all** - nobody else could ever hit back at a runaway leader, which isn't
how a real table of friends behaves.

**First attempt at a fix** - let every archetype opportunistically attack
the current leader once they're far enough ahead (1.3x the runner-up) -
made no difference at all. Why: the non-aggressive archetypes reinvest
almost everything each round and keep near-zero idle cash, so they never
had enough liquid "ammo" to strike even against a weakly-defended leader.
That's a genuine, interesting side-finding in its own right (playing pure
defense/growth leaves you unable to punch back even when you want to).

**Second attempt, which worked**: let a challenger mobilize a portion of
their company value too, not just idle cash - i.e. a coalition is willing
to liquidate some of its own position to take down a bully. Result:

| Archetype | Win rate | Avg Power (was, before fix 5) |
|---|---|---|
| Socialite | **100%** | 405.9 (was 330.5, 4th place) |
| Aggressor | 0% | 401.3 (was 528.3, dominant) |
| Diversifier | 0% | 345.0 (unchanged) |
| Turtle | 0% | 311.6 (unchanged) |
| SoloGrinder | 0% | 279.6 (was 277.9) |
| Leverager | 0% | 50.4 (was 40.4) |

Two things changed, both good: the gap between 1st and 2nd place shrank
from 183 points to 4.6 points (no more runaway snowball), **and** the
winning archetype flipped from the pure solo aggressor to the
alliance-focused Socialite - allies help both offense and defense once
"gang up on the bully" is a real option, which is exactly the flavor the
game is supposed to have. Leverager stays a clear cautionary tale (high
risk, usually a losing strategy) - that's intentional, not a bug.

**Design implication for the real game:** this only works if players can
actually *see* that someone's pulling too far ahead - the UI needs to
surface relative Power clearly enough that the table can organize against
a runaway leader. The mechanic is proven; making it visible is now a UI
requirement, not just a rules one.

## Recommended numbers (Power system)

| Parameter | Recommended value | Why |
|---|---|---|
| Company income rate | **10%/round** (as originally specified) | Baseline "bank" growth |
| Real Estate income rate | **5%/round** | Slower, but... |
| Real Estate defense weight | **0.9x** per unit (vs. 0.3x for cash) | ...it's the asset that actually protects you - this is what makes the safe/risky tradeoff real |
| Loan interest | **8% base + up to ~35% risk premium** scaling with leverage ratio | Leverage should get more dangerous the more you use it, like real credit |
| Bankruptcy trigger | **total power < 0** | Seizes ~85% of holdings, discharges remaining debt - diminished but stable, not a spiral |
| Building Phase length | **first 5 of 15 rounds** (1/3 of the game) | No attacks allowed - matches the "protect early players" fix you asked for |
| Post-Attack Shield | **2 rounds of immunity** after being successfully taken over | Stops perpetual farming of the same victim |
| Takeover capture | **25%** of victim's liquid (cash + company) value; Real Estate untouched | Meaningful hit, not a wipeout, and explicitly rewards having diversified into safe assets |
| Defender tie bonus | **defense counted at 1.05x** when compared to attack power | Borrowed from Risk - close fights favor the defender, so attacking only makes sense with a real edge |

## What Part 2 still doesn't cover
- Power Cards (the Coup-style bluffing/blocking layer) - not simulated;
  much harder to model meaningfully without simulating bluffing behavior
  itself, which is its own project.
- The Hidden Raider role's interaction with the Power system.
- This is still fixed, non-adaptive bots. Real friends will play smarter
  and weirder than any of these archetypes - this testing shows the rules
  are structurally sound (no free exploits, no unstoppable snowball), not
  that a real game will feel exactly like this.
