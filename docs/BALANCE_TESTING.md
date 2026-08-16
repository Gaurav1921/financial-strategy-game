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

## Addendum: real estate liquidation as a tactical attack-funding move
Requested and built: a challenger who's short on attack power to join a
pile-on can sell Real Estate to fund it (`liquidate_real_estate_for_attack`,
`TACTICAL_LIQUIDATION_ENABLED`). Tested at both the old margin (1.3, where
a leader has more time to build a real defense) and the new one (1.05):
**it never actually triggers**, 0 times across 300 test games at either
setting. Traced directly: by the time a challenger (almost always
Socialite) is considered, their attack power already comfortably exceeds
the leader's defense in every observed case (e.g. 25.8 vs 7.1, 44.3 vs
7.7), because the anti-snowball fix (at either margin) catches leaders
before their defense has time to grow into something a solvent challenger
couldn't already beat with cash alone. This isn't a bug, it's a real
consequence of Part 7's fix actually working: a well-functioning
correction mechanism means challengers rarely find themselves genuinely
short. The mechanic is built, off by default, and would need either a much
weaker anti-snowball setting or a much richer leader archetype to ever
actually exercise it, neither of which describes the currently recommended
configuration.

## Addendum: buying Real Estate wasn't free, and now it is on purpose
A review caught a real asymmetry: selling Real Estate (above) takes a real
15% haircut, but buying it was completely frictionless, an accident of
build order (the sell-side mechanic existed first), not a decision.
Added a small buy-side closing cost (`REAL_ESTATE_PURCHASE_COST`, ~3%) and
tested it against the current recommended configuration (margin 1.05, raid
fatigue 0.5):

| Configuration | Result |
|---|---|
| Bot baseline, cost off | Socialite 100%, gap 13.6% |
| Bot baseline, cost on | Socialite 100%, gap 13.0% (negligible) |
| + mistakes, cost off | Socialite 85.9% |
| + mistakes, cost on | **Socialite 90.6%** |

Clean, no downside, and modestly helps the mistakes-driven fragility, a
small, symmetric friction on both entering and exiting Real Estate seems to
discourage exactly the kind of low-cost flip-flopping into cash that made
the fragility possible in the first place. Off by default, same as idle
cash erosion and the income tax, a depth addition, not a required fix.

---

# Part 8 - How many allies can one player have at once

## Why this exists
A direct question caught something that was never actually a game rule:
`try_form_jv_human` capped a player at 2 simultaneous allies, but that cap
existed only as bot-tuning, never promoted to an actual documented rule or
tested for whether it matters to balance. Worth checking directly, since a
well-connected leader stacking unlimited Defense Pact support could
threaten the anti-snowball fix Part 7 just validated: defense includes
`ally.cash * 0.3` per ally, uncapped, that scales without bound.

## Method
`MAX_ALLIES` swept from 2 to unlimited (100), against both the clean
rational-bot baseline and the mistakes-driven fragility, with the current
recommended configuration (margin 1.05, raid fatigue 0.5).

## Result
| `MAX_ALLIES` | Bot baseline | + mistakes |
|---|---|---|
| 2 | Socialite 100%, gap 13.6% | Socialite 85.9% |
| 3 | Socialite 100%, gap 13.6% | Socialite 82.5% |
| 4-100 | Socialite 100%, gap 13.6% | Socialite 82.5% (identical to 3) |

Raising the cap from 2 to 3 costs a small amount of margin under realistic
play (85.9% → 82.5%), then flattens out completely, no further change all
the way to unlimited. That plateau is a pod limitation, not proof
uncapped alliances are safe: only 2-3 of the six archetypes (Socialite,
Diversifier, Casual) actively seek alliances at all in this bot model, the
rest never try. A real table, where any of 6-7 human players might want to
ally, especially a popular or well-negotiated leader, is a materially
bigger risk than this test can demonstrate. The cap matters more in
practice than in this specific simulation.

## Recommendation
**Keep `MAX_ALLIES = 2`**, the validated number with the widest margin.
JV partnerships and Defense Pacts currently share the same relationship
(one allying-with-someone slot covers both), not two independent caps,
that's a modeling simplification worth revisiting if the two mechanics
ever need to diverge (e.g. a player who wants a Defense Pact with someone
they'd never form a Joint Venture with).

## What Part 8 doesn't cover
- Whether JVs and Defense Pacts should have independent caps rather than
  sharing one relationship.
- Real human alliance-seeking behavior, this is still bots, and the
  specific limitation here (only some archetypes ally at all) likely
  understates how much a cap matters at a real table.

---

# Part 9 - Co-Founder, Hidden Raider, and fixing the last two broken mechanics

## Why this exists
A single round of direct questions caught a real flaw (Board Observer
backing wasn't actually an action), asked why the Hidden Raider role still
hadn't been simulated after two full review cycles, and asked for the two
broken financial mechanics from Part 6/7 to actually get fixed instead of
staying diagnosed-but-not-applied. All three addressed here.

## Board Observer, redesigned again: Co-Founder
Backing (Part 4) fixed the dead-rounds metric but, correctly called out
directly, didn't actually give a broke player anything to *do*, picking a
name to root for isn't an action. **Co-Founder** replaces it as the
preferred outcome: a broke player can be recruited by a living player to
actively co-run their company. Every remaining round, they redirect a real
slice of the host's fresh income toward Real Estate (`CO_FOUNDER_RE_NUDGE`,
10%), a genuine, repeated decision, not a one-time label. In exchange the
host gets a modest income bonus (`CO_FOUNDER_INCOME_BONUS`, +5% Company
income) for having them aboard, a real reason to want a co-founder. One
co-founder per host. Backing remains the fallback for anyone not recruited.

**First version had a real bug**: host recruitment preferred whoever
currently held the most Power ("the richest available host"). That quietly
handed the income bonus to whoever was already winning, the exact
snowball-reinforcing pattern this whole project kept finding and fixing
elsewhere, and cut Socialite's win rate from 85.9% to 75.5%. Fixed:
recruitment is random among eligible hosts. With that fix, the cost drops
to a small, honestly-reportable 85.9% → 83.2%. Dead rounds still hit zero
at every player count tested either way, the mechanism (an immediate,
one-time recruitment decision) doesn't depend on which host gets picked.

## Hidden Raider: first simulation pass
Roughly 1 Raider per 5-6 players (`RAIDER_RATIO`), needs at least 4 players
(moot now that Section 1 sets the range at 5-7). Each Raider is secretly
assigned one target. Sabotage, two vectors:
- **Targeting**: takeover and counter-attack target selection prefers the
  Raider's assigned mark over the usual richest-beatable choice, when
  actually within reach (`pick_target`).
- **Joint Venture drains**: a Raider allied with their target via JV drains
  against them at 60% probability per round, well above the ordinary
  Aggressor-only 30% baseline.

Win condition: the target ends the game bankrupt, or below half the
table's average Power (`raider_succeeded`).

**Result** (six-player pod, realistic mistakes + raid fatigue active,
1500 trials): Builder-side win distribution barely moves with Raiders
active (Socialite 73.3% → 74.8%), the core Power game isn't destabilized
by a hidden saboteur in the mix. Raiders hit their own win condition in
**14.9%** of games (224/1500), a real, achievable rate, neither trivial nor
hopeless. A first, defensible data point, not a fully tuned number.

**Not yet modeled**: whether a Raider should also withhold Defense Pact
support from their own target (currently they'd still defend them
passively if allied), and reveal timing (never, end-of-game, or
player-triggered).

## Peer-to-peer lending: the real fix took two attempts
Part 6/7 diagnosed the problem as "rescuing Aggressor's own recent
victims." Testing the fix showed that diagnosis was incomplete:

1. **Exclude anyone still inside their Post-Attack Shield.** Cut
   Aggressor's win rate from 99.8% to 88.9%, real progress, not a fix.
2. **Exclude anyone ever raided this game, at all** (not just inside the
   shield window). **Made no difference whatsoever, still 88.9%.** Tracing
   actual cash flows settled it: the borrower was never the real
   mechanism. Only Socialite (the one archetype that both forms alliances
   and keeps spare cash) ever lends in this pod, and giving away 30% of
   their own cash every time directly drained the exact war chest their
   win condition depends on for counter-attacks, regardless of who
   received it.
3. **Cap the lending fraction.** Swept `PEER_LOAN_LEND_FRACTION` from 30%
   down: 30% and 20% both still broke the baseline (88.9% and 99.8%
   respectively, non-monotonic, consistent with other threshold sweeps
   this project has hit), 10% and below came back clean.

| Fraction | Bot baseline | Verdict |
|---|---|---|
| 30% (original) | Aggressor 88.9% | Broken |
| 20% | Aggressor 99.8% | Broken (worse) |
| **10% (fixed)** | **Socialite 100%** | Clean |
| 5% | Socialite 100% | Clean |

At 10%, under the harder mistakes + raid fatigue scenario: Socialite 71.7%,
Aggressor 26.9%, a real cost (down from 85.9% with peer lending off
entirely) but Socialite stays solidly dominant, not flipped. Both fixes
(shield/ever-raided exclusion, 10% cap) are kept in the final version, the
exclusion is still the thematically correct rule (you don't lend to
someone mid-raid-recovery), even though the cap turned out to be the fix
that actually mattered numerically.

## Long/short stocks: clean under realistic play, still shaky on the artificial baseline
Retested against the full current configuration (widened margin, raid
fatigue, income tax, idle cash erosion, real estate purchase cost, fixed
peer lending, co-founder, all active together, the combination Part 7
flagged as never having been tested as a whole):

| Configuration | Long/short off | Long/short on |
|---|---|---|
| + mistakes (realistic play) | Socialite 78.9% | **Socialite 82.7%** |
| Clean bot baseline (zero mistakes) | Socialite 100% | Aggressor 78.7% |

Under realistic play, the scenario this whole `human_sim.py` harness
exists to approximate, long/short stocks is clean, slightly better than
without it. On the artificial zero-mistake baseline, it still breaks
things. Given Part 7 already found that baseline is close to fully
deterministic (identical results across every seed once mistakes are off),
and the entire point of this harness is testing against realistic
imperfection rather than that narrow artificial case, this is reported as
a genuine, if incomplete, improvement rather than a full fix.

## Player count: the data doesn't support "4 to 7"
Asked directly to confirm a 4-7 player range. Checked the actual sweep
(current settings) before agreeing:

| Players | Locked in by | Winner variety |
|---|---|---|
| 3 | round 1.3 of 15 | 1 archetype ever wins |
| 4 | round 1.9 of 15 | 1 archetype ever wins |
| 5 | round 9.5 of 15 | 3 archetypes win |
| 6 | round 10.5 of 15 | 3 archetypes win |
| 7 | round 10.9 of 15 | 4 archetypes win |

4 players shows the identical failure mode as 3, locked in almost
immediately with only one archetype ever able to win. The real breakpoint
is between 4 and 5, not 3 and 4. GDD.md now states **5 to 7 players**, not
4 to 7, in Sections 1 and 10.

## What Part 9 doesn't cover
- Whether a Raider should withhold passive Defense Pact support from their
  target (see Hidden Raider section above).
- Hidden Raider reveal timing.
- A working fix for long/short stocks on the artificial zero-mistake
  baseline specifically, only validated as clean under realistic play.
- A player-count-scaled round structure for a hypothetical 3-4 player mode,
  which is now explicitly out of scope rather than a bug to fix.

---

# Part 10 - The Building Phase was a solved formula

## Why this exists
Caught directly: with Company income at 10%/round and Real Estate at
5%/round, and no attacks possible until the Conflict Phase, Real Estate's
one advantage (defense weight) is worth exactly zero for the entire
Building Phase. A purely rational solo player has no reason to ever touch
it before round 6. Since the Building Phase length is fixed at 5 rounds
and stated as a rule everyone knows, even the "when do I start pivoting to
defense" question has a single calculable answer. The whole first third of
the game reduces to "max Company until round N, then pivot," a formula a
repeat player solves once and never has to think about again. Not a
balance bug, a design gap: no luck, no real decision, once you've done the
math.

## The fix: hide the Building Phase length, don't add luck
Random dice/luck would fight the game's financial-strategy identity.
Hidden information doesn't: the actual length is unknowable to players in
advance, the same way a real market doesn't announce the exact day a
downturn starts. `VARIABLE_BUILDING_PHASE_ENABLED` rolls the length once
per game, secretly, from `BUILDING_PHASE_RANGE` (4-6 rounds inclusive,
never revealed to players). "When do I start defending" becomes a real
read on warning signs (who's already building Real Estate, who looks
aggressive) instead of a lookup table.

## Result
Tested against the mistakes + raid fatigue configuration, fixed 5-round
Building Phase vs. randomized 4-6:

| Configuration | Top archetype | Gap |
|---|---|---|
| Fixed Building Phase = 5 | Socialite 85.9% | 11.1% |
| Variable Building Phase = 4-6 | Socialite 89.0% | 8.7% |

Balance-neutral to slightly positive, no regression.

## The honest limit of this test
This confirms the mechanic doesn't break anything numerically. It does
**not**, and structurally cannot, confirm the actual claim it's meant to
address: that hiding the length stops a real human from finding and
memorizing a dominant strategy after a handful of games. Bots don't learn
or adapt across separate games, they run the same fixed archetype logic
every trial regardless of what happened last time. Whether this genuinely
keeps the Building Phase interesting on a group's fifth game night is a
human-playtesting question, the same limitation that applies to
everything in this file.

## What Part 10 doesn't cover
- Whether 4-6 rounds is the right range, or whether it should scale with
  the eventual player-count-aware round structure (Section 9's still-open
  item).
- A "warning" mechanic (e.g. a signal the round before Conflict Phase
  actually opens) that would make the hidden length a readable risk
  instead of a total blind spot, mentioned as a design idea, not built.
- Whether diminishing returns on Company reinvestment (a second, additive
  fix for the same "solved formula" problem, not yet tried) would help on
  top of this.

---

# Part 11 - Total-wealth capture, defender rewards, and Power-only visibility

## Why this exists
Two direct changes to the takeover mechanic, requested outright: captures
should draw from a target's *total* wealth, not just liquid cash + Company
(forcing Real Estate liquidation if needed), and a failed attack's lost
stake should reward the defender and the Bank instead of vanishing. Both
built and tested. A separate, related conversation about what players can
actually see landed on Power-only visibility, replacing an earlier,
now-superseded "show the full breakdown" design from Part 9's
neighborhood, see GDD.md Section 6 for the final version and the reasoning
that got there.

## Total-wealth capture
`TOTAL_WEALTH_CAPTURE_ENABLED`: a successful takeover now owes
`TAKEOVER_CAPTURE_PCT * target.total_power()` (or
`COUNTER_ATTACK_CAPTURE_PCT` for a counter-attack), collected cash first,
then Company, then Real Estate at the standard 15% liquidation haircut if
the rest isn't enough (`collect_payment`, shared with the tax-collection
cascades already in place). Real Estate is no longer automatically
untouched, it's just usually the last thing drawn on.

| Configuration | Result |
|---|---|
| Off (original: liquid only) | Socialite 85.9%, gap 11.1% |
| **On (total wealth)** | **Socialite 90.0%, gap 21.3%** |

Strengthens the anti-snowball margin further, doesn't weaken it. Likely
mechanism: a bigger single hit against a Real-Estate-heavy target also
inflates whoever landed it (usually Aggressor) faster, tripping the
"gang up" correction (Part 7) sooner than the liquid-only version would.

## Defender reward on a failed attack
`DEFENDER_REWARD_ENABLED`: the attacker's lost stake (still 50% of what
they committed, unchanged) no longer vanishes. It's collected via the same
cascade (`penalize_failed_attacker`, cash then Company then Real Estate),
split evenly between the defender who successfully protected themselves
and the Bank.

**Result: no measurable difference, on or off, identical numbers.** Traced
directly: across 500 sample games, takeover attempts failed **0 times out
of 2,714**, counter-attack attempts failed **0 times out of 1,360**. These
bots use perfect information (true defense values, not an estimate) to
decide who's even worth attacking, so they never actually initiate a fight
they'd lose. The mechanic is correctly built, it's just structurally
untestable by this bot model, it only has anything to reward once players
are deciding under real uncertainty, which is exactly what Power-only
visibility (below) introduces and this bot pod still doesn't model.

## Power-only visibility (superseding the "full breakdown" design)
A first pass at "what should players see" (see GDD.md Section 6's own
history) proposed showing every player's full asset breakdown, on the
reasoning that the anti-snowball mechanic needs players to read "who's
undefended" and Power alone can't tell them that. Correctly rejected in
conversation: an accurate number, or even an accurate bucketed rating,
removes the decision the same way full transparency does, "if you already
know their defense, attacking anyway is just stupidity." Landed on:
**only Power is shown, exactly; everything else is unknown unless it goes
through a Declaration (always self-referential, matching Coup) that any
player can Audit** (a cost, with lying penalized harder than a failed
Audit, already established in Section 8.3).

**Not simulated, and can't be with the current bot model**: every
win-margin number in this file assumes bots read exact defense values
directly. Modeling "an attacker only knows what's been Declared or
Audited" would require building a genuine hidden-information layer into
the bots (a real project, closer to the Power Cards / Declare-Audit
simulation work that's already deferred, see GDD.md Section 8.1). Until
that exists, treat every validated margin in this file as describing a
more-informed table than Power-only visibility will actually produce.

## What Part 11 doesn't cover
- Simulating Power-only visibility itself, needs a real hidden-information
  bot model, not built.
- Whether the defender-reward split (50/50 to defender/Bank) is the right
  ratio, untestable until failed attacks can actually happen in the sim.
- Retesting total-wealth capture at other player counts or in combination
  with all other mechanics from Parts 6-10 active simultaneously.
