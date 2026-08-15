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

---

# Part 3 - Human-shaped testing, without human testers

## Why this exists
There's no playtesting group for this project, it's a solo effort. Parts 1
and 2 validated that the rules have no free exploits using six fixed,
non-adaptive bots that never make a mistake and never react to what just
happened to them. That's a real gap: it proves the math is sound, not that
a table of actual people would have a good time. `sim/human_sim.py` is the
closest available substitute: it extends the Part 2 bots with mistakes,
grudges, bandwagoning, a "Casual" archetype standing in for a first-time or
half-attentive player, and instrumentation aimed specifically at the
questions a rules-only simulation can't answer, like how many rounds a
beaten-down player spends with nothing to do, and whether the fixed round
count holds up outside the six-player pod it was tuned on.

## Method
Same six-player, 15-round (5 Building, 10 Conflict) structure as Part 2,
extended two ways:
- **Trait layer**: each player gets randomized `mistake_rate`,
  `grudge_bias`, `bandwagon_bias`, and `declare_bias` (see below), so a
  "Turtle" in one trial isn't identically cautious to the Turtle in the
  next, the way two real cautious friends wouldn't play identically either.
- **Player-count sweep**: 3 to 7 players, 1000 trials each (`Casual` fills
  the 7th slot), tracking two new metrics: `AvgLockRound` (how early the
  eventual leader becomes permanently the leader) and `AvgDeadRoundsPerPlayer`
  (rounds a player spends bankrupt or too weak to make a meaningful choice).

## Finding 1: the fixed round count doesn't hold up below six players
| Players | Avg dead rounds/player | Worst case | Game locked by round | Winner variety |
|---|---|---|---|---|
| 3 | 0 | 0 | round 1.3 of 15 | 1 archetype ever wins |
| 4 | 0 | 0 | round 1.9 of 15 | 1 archetype ever wins |
| 5 | 0 | 0 | round 14.8 of 15 | 2 archetypes ever win |
| 6 | 1.03 | 7 | round 10.2 of 15 | 3 archetypes ever win |
| 7 | 0.89 | 7 | round 10.3 of 15 | 5 archetypes ever win |

At 3 to 4 players, the eventual winner is locked in almost immediately,
most of a small-group game plays out as a foregone conclusion nobody can
affect. At 6 to 7, someone can spend up to 7 of the 15 rounds, nearly the
whole Conflict Phase, with nothing meaningful to decide. Neither the round
count nor the Building Phase length currently scale with player count.
Logged in GDD.md Section 9, not yet fixed.

## Finding 2: declare-to-reinforce doesn't reopen the Finding 5 exploit
GDD.md Section 7's Defense Pact fix (declared pacts visibly boost defense
and are audit-able for bluffing, covert pacts stay hidden until a fight
actually happens) was tested against a rational, trait-free version of the
six-archetype pod. With roughly half of all pacts going covert, it
reproduced the Part 2 Finding 5 numbers exactly: Socialite 100% win rate,
405.9 avg power. Visible Power and secret alliances no longer contradict
each other, and the fix is free, it doesn't cost anything in balance.

## Finding 3: realistic imperfection alone breaks Finding 5's fix
This is the important one. Turning on `mistake_rate` (each round, a 3-25%
chance a player's allocation reverts to an autopilot repeat of their last
round's habitual split rather than their archetype's calculated one, a
closer model of distraction than a fresh random roll) is enough on its own
to flip the outcome:

| Configuration | Winner | Win rate | Leader/2nd gap |
|---|---|---|---|
| rational bots (Part 2 baseline) | Socialite | 100% | 1.1% |
| + ordinary mistakes | Aggressor | 71-77% | 8-11% |

Average end-of-game holdings barely move between the two conditions
(Turtle's Real Estate: ~178 either way), so this isn't "mistakes erode
everyone's defense on average." It's a **ratchet effect**: across six
players and fifteen rounds, the odds that at least one player has a single
badly-timed off round somewhere in the game are high, even though each
individual round is low-risk. Aggressor only needs one such window. A
successful takeover captures 25% of the victim's liquid value permanently,
which both weakens the victim and strengthens the attacker's relative
position for every round after, so a single lucky opening compounds into a
lead that the anti-snowball fix (keyed to a hard 1.3x leader/second-place
margin) often doesn't catch, because the resulting lead accumulates as a
steady, moderate edge rather than one dramatic spike past the trigger
threshold. Directly confirmed: across 30 sample games with default traits,
the leader/second-place ratio never once crossed 1.3x, peaking around
1.1-1.28, yet Aggressor still won the majority of games.

## Finding 4: two "automatic correction" fixes were tried and rejected
Before landing on a working fix, two designs were built, tested, and thrown
out, kept here so they aren't tried again blindly:
- **Delay captured value from counting toward Power for one round.**
  Reasoning: slow down the compounding. Result: made it worse, even in the
  pure-bot case (Aggressor went from 0% to 100%). Captured value never fed
  attack power in this model to begin with (attack power is purely liquid
  cash), so delaying when it counts toward Power only delayed *detection*
  of the runaway leader, handing them a free extra round to keep
  compounding before anyone noticed.
- **An automatic tax on whoever currently holds the lead** (tried against
  both income and cash). Reasoning: a guaranteed correction shouldn't
  depend on a coalition having the resources or timing to act. Result:
  backfired both times, because it can't distinguish a dangerous lead
  (Aggressor's liquid, attack-ready cash) from a benign one (Socialite or
  Turtle briefly ahead through ordinary diversified growth). It ended up
  taxing the archetypes that were supposed to win.

## Finding 5: raid fatigue works, partially
A repeat successful attacker's future attacks get proportionally weaker
(`fatigue_multiplier`, floor 25% effectiveness), mirroring the reputation
tax Part 1 already validated for Joint Ventures (two proven drains cost you
easy income and worse terms) applied to takeovers instead of draining, and
targeting the actual repeat behavior directly instead of a proxy for it
like "current lead."

| Configuration | Winner | Win rate | Leader/2nd gap |
|---|---|---|---|
| + mistakes, no fix | Aggressor | 71-77% | 8-11% |
| + mistakes, with raid fatigue (0.5) | Aggressor | 62-63% | 5.0-5.1% |

The gap recovers to essentially the validated Part 2 baseline (4.6%), the
game stays close. The win-rate split doesn't fully revert to the pure-bot
result: Aggressor still wins more often than Socialite (62% vs. 36%)
instead of losing outright. This is a genuine, partial improvement, not a
full fix, and is the recommended mitigation until further design work
closes the remaining gap.

## Finding 6: a "fear after being hit" reaction was tried and dropped
Modeling a player who plays scared and defensive for a few rounds after a
takeover was attempted three ways, and every version backfired in an
archetype-specific way that didn't converge with reasonable iteration:
1. Divert new company income into Real Estate. Made the affected player's
   defense stronger for free, since Real Estate is weighted far more
   heavily than cash in defense (0.9x vs 0.3x), regardless of which bucket
   the diverted value was pulled from.
2. Divert proportionally from both company growth and retained cash.
   Same problem, worse: it let *more* total value convert into the
   heavily-weighted Real Estate bucket than the first version did.
3. Freeze into cash instead of Real Estate, so no defense boost at all.
   For the Aggressor archetype specifically, this fed straight into the one
   resource (liquid cash) that archetype's base strategy already wants to
   hoard, so "fear" became a free reinforcement of Aggressor's own play
   instead of a penalty.

Fear is probably a real factor in how actual players behave after being
hit, but it needs a properly scoped, archetype-aware modeling pass on its
own, not a bolt-on trait layered over existing archetypes. Deliberately
left out of `sim/human_sim.py`. Logged in GDD.md Section 9.

## Recommended numbers (Part 3)

| Parameter | Recommended value | Why |
|---|---|---|
| Defense Pact posture | **declared or covert**, player's choice per pact | Declared visibly boosts defense and deters attacks but exposes the alliance; covert stays hidden but is audit-able for bluffing. Validated: doesn't reopen Finding 5 |
| Raid fatigue penalty | **50% per prior successful raid this game**, floor 25% effectiveness | Recovers the Finding 5 power gap to near-baseline (5.1% vs. 4.6%) under realistic mistake rates; higher values plateau around the same result |
| Round count / player count | **not yet fixed** | 15 rounds only holds up at 6-7 players; 3-5 needs a different structure |

## What Part 3 still doesn't cover
- A working fix for the remaining win-rate skew under realistic mistakes
  (raid fatigue closes the power gap but not the win-rate gap).
- A properly modeled "fear after being hit" reaction (see Finding 6).
- A player-count-scaled round/phase structure (see Finding 1).
- Power Cards and the Hidden Raider role, same as Part 2.
- Real human playtesting. This is still bots, now with some randomized
  imperfection layered on, not real people. It's a better proxy for
  structural risk than Parts 1-2, not a replacement for actually watching
  people play.

---

# Part 4 - Board Observer backing (elimination downtime)

## Why this exists
A design review flagged that the original Board Observer status (leak one
piece of information, vote once in the final round, see the old GDD.md
Section 8.4) was too thin for a live, one-sitting session: a heavily-farmed
player has nothing meaningful to do for however many rounds are left.
`sim/human_sim.py`'s `AvgBrokeRoundsPerPlayer` metric (rounds spent with
next to nothing to allocate, tracked independent of any fix) quantified it
first, this Part tests the fix.

## The fix, first version, corrected
The instant a player goes broke, they pick one living player to **back**
(preferring an existing ally if one is still solvent, otherwise whoever
currently holds the most Power). The first version of this gave the Board
Observer a 15% cut of every capture their backed player landed for the rest
of the game. **That was wrong, caught immediately in review**: a Board
Observer's own Power isn't coming back in any real way, they aren't
competing to win anymore, so growing it via a cut is pointless for them,
and worse, it's an unreciprocated tax on the living player, cash leaves
their side of the ledger for no benefit to them at all. There's no good
answer to "why would I give a broke player 15% of what I just earned,"
because there isn't one.

Corrected design: **no financial transfer at all.** Backing is a social and
informational choice, not a stake. What it actually does:
- Ends the "dead rounds" problem, per the metric below, since the decision
  itself is what counts as re-engagement, not an ongoing cash flow.
- Gives the Board Observer's endgame vote real teeth: `determine_winner`
  now breaks a close final-round tie (within 0.5 Power) by counting how
  many Board Observers are backing each tied player, this is the
  "gets a vote in the final round" GDD.md Section 8.4 already promised,
  just made mechanically real instead of flavor text.
Full mechanic in GDD.md Section 8.4.

## Result
`AvgDeadRoundsPerPlayer` is defined as "broke AND haven't picked who to
back yet," to distinguish genuinely idle rounds from rounds where a player
has nothing financial left to decide but has made their backing choice.

| Players | Broke rounds/player (pre-fix baseline) | Dead rounds/player (post-fix) |
|---|---|---|
| 3 | 0 | 0 |
| 4 | 0 | 0 |
| 5 | 0 | 0 |
| 6 | 1.03 | **0** |
| 7 | 0.89 | **0** |

Dead rounds drop to zero at every player count tested, because the fix
only requires one decision, made immediately, not sustained engagement.
Win rates and the power gap are unchanged from the Part 3 baseline, this
mechanic touches nothing financial, so there's nothing for it to distort.

## What Part 4 doesn't cover
- The "leak one piece of information" half of Board Observer status isn't
  modeled at all, this sim has no bluffing/information layer to leak into.
- Whether backing choices feel meaningful to an actual human, versus just
  numerically ending the "dead rounds" metric. Same caveat as always: this
  is bots, not playtesting.

---

# Part 5 - Loan conservation and a windfall tax that didn't work

## Why this exists
A review flagged that Loans, as modeled, break conservation of money: a
Leverager's `allocate()` branch adds a loan straight to cash and company
with no offsetting source, cash was being created, not transferred, and
bankruptcy discharges the debt with no cost anywhere either. Real lending
comes from somewhere finite, and the review specifically asked for a Bank
with limited capital, distinct from player-to-player lending which should
cost more.

## The fix: a Bank with a finite pool
`sim/human_sim.py` now has a `Bank` class holding a `pool`, sized at 100
per seat at the table (one player's starting capital: 20 cash + 80
company). Every Leverager loan draws down the pool; if the pool can't cover
the full loan, the shortfall is clawed back proportionally from wherever it
went (Leverager splits new cash 70% company / 30% cash), a real credit
crunch, not just a rule that exists on paper. Bankruptcy still discharges
the borrower's remaining debt, which was already correctly conserved: the
Bank took its loss the moment it funded the loan, not a second time at
discharge.

**Honest limitation, not yet resolved**: this six-archetype pod only ever
has one Leverager borrowing at a time. At the current pool size (100/seat),
that single borrower never actually exhausts it, average pool remaining at
game end is 428.8 out of an ~600 starting pool at 6 players; real scarcity
only shows up if the pool is cut down to roughly 60, far below a
defensible "the bank has real capital" number. This means the current pool
size doesn't yet demonstrate the credit-crunch dynamic it's meant to model,
because the sim structurally can't put multiple borrowers on it at once,
where a real game (any of 6-7 human players borrowing at different points,
especially catching up late-game) would stress it far more. Needs
retesting once loans aren't restricted to a single fixed archetype.

**Peer-to-peer lending** (a living player lends directly to another, at a
higher rate than the Bank, and eats a real loss if the borrower defaults)
was requested but not yet built. It's a real, well-motivated extension:
counterparty risk between two specific players is exactly the kind of
memorable, personal stake this game is going for, and it would reuse the
Declare/Audit system naturally (a public peer loan deters others from
preying on the borrower, same logic as a declared Defense Pact; a private
one is riskier for the lender since nobody else is watching out for the
borrower's obligations). Queued, not simulated yet.

## The windfall tax: tested thoroughly, doesn't work as designed
Also requested: a progressive capital-gains-style tax on a successful
takeover's proceeds, scaled by the attacker's resulting wealth bracket
(0% under 150 Power, rising to 35% over 450), specifically to test whether
it closes the win-rate gap raid fatigue only partially closed (Part 3,
Finding 5). Three versions were tried, all against the same mistakes-driven
fragility from Part 3:

| Version | Result (top archetype, win rate, gap) |
|---|---|
| Baseline, no tax | Aggressor 72.7%, gap 8.1% |
| Raid fatigue (for comparison) | Aggressor 64.5%, gap 5.0% |
| Windfall tax → Bank pool | Aggressor 99.9%, gap 11.2% |
| Windfall tax → redistributed evenly to all other players | Aggressor 99.9%, gap 8.4% |
| Windfall tax → redistributed, exempting counter-attack captures | Aggressor 97.7%, gap 17.4% |

Every version made it worse, and even on the clean rational-bot baseline
with zero human traits active (where Finding 5 validated Socialite winning
100% of games), turning the tax on alone flips the winner to Aggressor at
100%, with Aggressor's average power actually *increasing* (401.3 → 464.2)
despite being taxed. Root cause, confirmed by comparing raw attempt counts:
redistributing the tax to "every other living player" includes each raid's
own victim. That cushions them, they recover into a worthwhincile target
again faster than they would have unassisted, which lets Aggressor land
raids more often overall (attempts rose from 3000 to 3500 across 500 test
games) even though each individual raid nets less. More frequent smaller
wins beat fewer larger ones, and the extra recovery speed for random
players did nothing for Socialite specifically, since Socialite's own path
to winning depends on landing enough counter-attacks, not on redistributed
pocket change. Sending the tax to the (never-stressed) Bank pool instead
was worse still: it just deleted value from the game with no offsetting
effect on anyone.

**Recommendation: don't ship this in its current form.** Raid fatigue
remains the validated mitigation from Part 3. A windfall tax might still be
worth pursuing as a piece of financial texture on its own terms (it's a
real, thematically justified mechanic), but not as a balance fix, and not
with a redistribution rule that inadvertently subsidizes the attacker's
future victims. `WINDFALL_TAX_ENABLED` defaults to `False` in
`sim/human_sim.py`; the code is kept as documented, tested infrastructure
in case a different distribution rule is worth trying later (e.g.
redistributing only to players below a poverty threshold, not to everyone,
so it can't cushion the attacker's next mark).

## What Part 5 doesn't cover
- Peer-to-peer lending (see above), and the Bank pool sizing needed once it
  exists.
- A working windfall/capital-gains tax design. Tested three variants, none
  viable, this is now a known dead end, not an open question to re-explore
  blindly.
- Progressive income tax, idle cash erosion, and real long/short stock
  positions, three more financial-depth mechanics discussed but not yet
  built or simulated.

---

# Part 6 - Four financial-depth mechanics, built and tested together

## Why this exists
Four more mechanics were requested to make the game rely more on financial
decision-making and less on combat: real long/short stock positions
(closing the gap where the Market paid a flat return regardless of what
happened to the company you'd invested in), a progressive net-worth tax
modeled on how Indian income tax slabs actually work (marginal brackets,
not a cliff), idle cash erosion (inflation on cash sitting uninvested), and
peer-to-peer lending (a living player lends to another at a premium over
the Bank's rate, with real default risk). All four are built in
`sim/human_sim.py`, each behind its own flag, and tested individually
before combining them, per explicit instruction: build everything, test
everything, then fix what the simulation raises one at a time.

## Result: three of four break the validated baseline, one doesn't

Tested against the clean rational-bot baseline (Socialite 100%, 405.9
avg power, 1.1% gap, the same numbers validated in Part 2's Finding 5),
each mechanic in isolation, raid fatigue off:

| Mechanic | Result alone | Verdict |
|---|---|---|
| Long/short stocks | Aggressor 100%, gap 20.8% | Breaks it |
| Progressive income tax (→ Bank) | Aggressor 100%, gap 0.4%* | Breaks it |
| Idle cash erosion | Socialite 100%, gap 0.6% | **Clean** |
| Peer-to-peer lending | Aggressor 99.8%, gap 20.9% | Breaks it |
| All four together | Aggressor 100%, gap 19.8% | Breaks it |

*A small gap number here is misleading: it means the game ends close, not
that it's fair, Aggressor is winning almost every single time regardless of
how close the final score is.

## Root cause: two distinct, now well-confirmed patterns

**1. Aggressor is structurally insulated from anything that doesn't touch
cash.** Aggressor's whole archetype is "stay ~70% liquid, invest lightly
in company, never touch Real Estate or stocks." Long/short stocks add real
risk to Diversifier and SoloGrinder's stock bets (previously a guaranteed
flat 8%/round); income tax hits company/Real Estate income specifically,
which Aggressor barely generates. Both mechanics only add drag to
strategies Aggressor was never using anyway, so on average they weaken
every rival relative to Aggressor without ever touching Aggressor itself.
Isolated confirmation: Diversifier's average power dropped from 345.0 to
315.6 under long/short stocks alone, Aggressor's rose from 401.3 to 454.1,
despite Aggressor never holding a single stock position.

**2. Anything that hands cash to cash-poor players accelerates
re-victimization**, the same mechanism Part 5 found for the windfall tax's
redistribution, now confirmed a third time. Peer loans specifically target
allies whose cash is low, which is very often Aggressor's own recent
victims. A rescue loan lets them recover into a worthwhile target again
sooner than they would have unassisted, so Aggressor lands more total
raids even though each individual raid is unaffected, more frequent
smaller wins beat fewer larger ones, same conclusion as Part 5, different
mechanic.

**Idle cash erosion is the one mechanic that avoids both patterns**: it
taxes cash directly (Aggressor's own core resource, not a strategy they're
insulated from) and has no redistribution at all (nothing to cushion a
victim with). That's exactly why it's the only one of the four that came
back clean.

## What Part 6 doesn't cover
- Fixes for the three broken mechanics. Given the two confirmed patterns
  above, the fix shape is now reasonably clear for each (tax cash directly
  instead of income/stocks specifically; route peer-loan rescue funding
  away from recent-raid-victims specifically, or add a real cost to
  borrowing that offsets the recovery speed), but none has been tried yet.
- Testing these four against the mistakes-driven fragility with a working
  fix in place, only against the unmodified fragility, which they all made
  worse, consistent with everything above.
- Whether idle cash erosion, the one clean mechanic, actually helps close
  the Part 3/5 fragility gap, only tested against the clean baseline so
  far, not against the mistakes scenario in combination with raid fatigue.

---

# Part 7 - Widening the anti-snowball margin itself

## Why this exists
Every fix attempted in Parts 5 and 6 kept flipping the same validated
result, and a review of the actual numbers explained why: Finding 5's
"fix" (Part 2) only wins by 4.6 Power points on average (405.9 vs 401.3,
about 1.1%). That's not a robust margin, it's the specific outcome of one
test configuration that happened to land narrowly on the honest strategy.
A margin that thin has close to even odds of flipping under *any*
additional variable, which is why so many well-intentioned additions kept
breaking it, the foundation itself had no headroom, independent of whether
each new mechanic was well designed.

## What was tried and rejected
**Increasing `COUNTER_ATTACK_CAPTURE_PCT`** (making a coalition's pile-on
capture more than a solo raid, 25% up to 35%) seemed like the obvious
lever, and made things worse: at 30-50%, the winner flipped back to
Aggressor. Root cause, confirmed by counting successful counter-attacks
per game: a bigger single hit drops the leader's Power far enough, in one
shot, to fall back under the 1.3x "runaway leader" threshold immediately,
letting them duck out of further scrutiny. Counter-attack frequency
dropped from 2.0 per game to 1.0. A leader who takes one big hit and then
quietly rebuilds unwatched is worse off for the game than one who stays
flagged and keeps taking smaller hits. Frequency of correction mattered
more than the size of any single correction.

## The fix: lower `LEADER_THREATENED_MARGIN`
Changed from **1.3 to 1.05**: a leader only needs to be 5% ahead of second
place, not 30%, before the table can organize against them. This keeps the
corrective mechanic engaged continuously instead of only firing once a
lead has already become dramatic.

| Configuration | Winner | Margin |
|---|---|---|
| Bot baseline, margin 1.3 (old) | Socialite 100% | 4.6 pts (1.1%) |
| Bot baseline, margin 1.05 (new) | Socialite 100% | 55.1 pts (13.6%) |
| + mistakes, margin 1.3, no fix | Aggressor 72.7% | -- |
| + mistakes, margin 1.05, no other fix | **Socialite 66.9%** | -- |
| + mistakes, margin 1.05 + raid fatigue | **Socialite 85.9%** | 11.1% |

Lowering the margin alone, with no other mitigation, already reverses the
mistakes-driven fragility from Part 3 (Aggressor 72.7% → Socialite 66.9%).
Combined with raid fatigue, Socialite wins 85.9% of games, Aggressor drops
to 13.3%, a real, wide, reproducible margin instead of a coin flip, and
Aggressor still wins often enough to remain a real strategy, not
eliminated outright.

A sanity check worth recording: at very small margins (tested down to
1.05, and 1.3 for comparison) game outcomes were identical across every
random seed tested, for *both* the old and new margin. This isn't new
determinism introduced by the fix, it's how this six-archetype,
no-mistakes bot pod has always behaved, fixed percentage-split archetypes
leave little for the untested traits (grudge/bandwagon/declare bias) to
actually swing once mistakes are off. Confirmed by checking the original,
already-published margin=1.3 baseline shows the same property.

## Retesting Part 6's four mechanics against the widened foundation
With the wider margin and raid fatigue as the baseline instead of the
fragile 1.1% one:

| Mechanic | Before (margin 1.3) | After (margin 1.05 + fatigue) |
|---|---|---|
| Idle cash erosion | Clean | **Clean, slightly better** (90.1% vs 85.9% no-tax) |
| Progressive income tax | Broke it (Aggressor 100%) | **Clean** (Socialite 86.6%, barely moved) |
| Long/short stocks | Broke it (Aggressor 100%) | Still breaks it, less severely (Aggressor 57.9%) |
| Peer-to-peer lending | Broke it (Aggressor 99.8%) | Still breaks it (Socialite falls to 53.9%) |

Two of four are now validated clean on a robust foundation. The other two
still have the specific, already-diagnosed problems from Part 6 (long/short
stocks' archetype-exposure asymmetry, peer loans' victim-cushioning
effect), those need their own targeted fixes, the wider margin didn't
paper over either root cause, it just stopped masking which mechanics are
actually fine.

## Recommended numbers (Part 7)

| Parameter | Old value | New value | Why |
|---|---|---|---|
| `LEADER_THREATENED_MARGIN` | 1.3 | **1.05** | The old value only produced a 1.1% win margin, not a validated fix, just a narrow coin flip. The new value produces a wide, reproducible margin and survives the mistakes-driven fragility with no other mitigation needed |

## What Part 7 doesn't cover
- Fixes for long/short stocks and peer-to-peer lending, both still broken,
  root causes already known (see Part 6), not yet applied.
- Whether `LEADER_THREATENED_MARGIN=1.05` needs retuning once Power Cards
  or the Hidden Raider role are simulated, both add mechanics this number
  hasn't been tested against.
- Player counts other than 6, this margin was only retuned against the
  six-archetype pod Part 2 validated against.
