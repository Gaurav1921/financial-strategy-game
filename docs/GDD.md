# Hostile Ledger - Game Design Doc

## 1. Pitch
A web-based financial strategy game for a small group of friends (**3 to
8**, simulation-tested: an earlier pass found 3-4 players broke down
because of a biased test roster, not the player count itself, once that
bias was fixed, 3-4 read comparably to every other supported count, and 8
was validated once two new archetypes existed so a larger table wasn't
just padded with duplicate first-timers; see BALANCE_TESTING.md Part 17.
9-10 aren't supported yet, the same roster problem reappears there without
a genuine 9th archetype) playing together in one sitting - start to
finish in under an hour, like a
board game night, not a slow mobile game you check in on for weeks. Everyone
builds a company and grows their **Power** - a combined score built from
cash, real estate, stock positions, and captured rivals, not just a single
number. The biggest plays (taking over a rival) usually need allies to pull
off, some of your allies might secretly want you to fail, and every claim
anyone makes can be bluffed. Money, power, and trust are all live risks at
the same time.

## 2. Format: Live Mode first, Season Mode later
Originally designed as a slow, async, check-in-once-a-day "season" (2–3
weeks, matchmade with strangers) - that model doesn't fit the actual use
case (a group of friends who want to sit down and play one full game
together right now), and it wasn't producing a genuinely "hooked" feeling
since nothing happens live. **Live Mode is the build target**: one host
creates a room, friends join with a link, the whole game plays out in a
single sitting. Season Mode (persistent, async, matchmade with strangers)
is a plausible future enhancement once Live Mode is proven fun, not
something to build now.

**Competitive note:** Fusebox Games is shipping an officially licensed
*The Traitors* mobile app in 2026 (hidden traitors, roundtable banishment,
TV IP). A pure "hidden traitor + vote people off" game competes directly
with that. Our differentiation is the financial-strategy layer underneath -
Power, multiple asset classes, real takeovers - which a narrative party
game won't have.

## 3. The core resource: Power
Not just net worth. **Power = Cash + Real Estate value + Stock holdings +
Captured value (from successful takeovers) − Debt (from loans) + a small
bonus per active alliance.** Two players with the same raw dollar total can
have very different Power depending on how diversified and allied they are
- this is deliberate: it's what makes "am I actually strong enough to
attack/defend" a real question with more than one right answer, and it's
what makes a genuinely powerful solo player able to take on an allied
group (see Section 6) instead of alliances being a hard requirement.

## 4. The two phases of a game
Split into two phases, closing a loophole a friend flagged directly: if
attacks were allowed from round one, whoever forms alliances fastest could
immediately gang up on solo/slower players before anyone's had a fair
chance to build up.

- **Building Phase** (4 to 6 rounds, **length hidden, rolled secretly at
  the start of the game, never announced**): **no attacks allowed at
  all.** Only growing your company, investing, and quietly forming
  alliances. Everyone gets equal time to build a position. The length is
  hidden on purpose: with Company income (10%/round) beating Real Estate
  (5%/round) and no combat to defend against yet, a known, fixed Building
  Phase length reduces the whole first third of the game to one
  memorizable formula, "max Company until round N, then pivot to
  defense," a repeat player solves once and never has to think about
  again (caught directly, see BALANCE_TESTING.md Part 10). Hiding the
  length turns "when do I start defending" into a real read on the
  table's warning signs instead of a lookup table, without resorting to
  random luck, which would fight the game's financial-strategy identity.
  Simulation-tested balance-neutral to slightly positive; whether it
  actually stops a human from finding a dominant pattern after repeat
  plays can't be tested by bots at all, that's a human-playtesting
  question like everything else still open in Section 9.
- **Conflict Phase** (rest of the game): takeovers unlock. By now the game
  is about who built the strongest position, not who allied first.
- **Final Round**: deliberately different (see Section 8.5) - the
  guaranteed climax where season-long trust either pays off or gets cashed
  in.

**To be explicit**: only *attacks* are phase-gated. Every other money
move, growing your company, buying or selling Real Estate, the Market,
loans, Joint Ventures, stays available in every single round of the game,
Building Phase included. The Building Phase doesn't pause the economy, it
only pauses combat.

Simulation-tested: this structure measurably works (see BALANCE_TESTING.md
Part 2) - it doesn't fully solve the "one aggressive player snowballs
unopposed" risk on its own (Section 9 covers this honestly), but it clearly
helps.

**What actually happens in one round.** A round is a year, and every round
runs the same eight steps, whether it's Building or Conflict:
1. **Income** - Company, Real Estate, and any stock positions pay out
   based on what you held *last* round.
2. **Allocate** - everyone secretly decides where this round's income
   goes: Company, Real Estate, the Market, paying down a loan, or holding
   cash. The core simultaneous decision, every round.
3. **Alliances** - propose or accept new Joint Ventures; existing ones
   resolve (hold or drain).
4. **Loans** - borrow if you want to, Bank capacity permitting; any peer
   loans between allies settle.
5. **Combat** (Conflict Phase only) - takeovers and "gang up on the
   leader" counter-attacks resolve.
6. **The Market re-prices** - stock positions revalue against what just
   happened to the companies they're tied to, including a takeover that
   just landed.
7. **Taxes and upkeep** - income tax on everything earned this round
   combined, Real Estate liquidation if anyone chose it, inflation on idle
   cash.
8. Round ends, move to the next.

Building Phase skips step 5 only, everything else runs identically every
round. Power Card plays and Declare/Audit challenges slot into steps 2 and
5, wherever the claim is actually made. Matches `sim/human_sim.py`'s
`simulate_game` loop exactly.

## 5. The six ways to make money
Every round, you choose how to spread your money across six different
options - not just "grow one number." This is the actual financial-strategy
part of the game.

1. **Your Own Company** - the baseline. Generates income each round
   proportional to its size (10%/round). Growing it is always safe, if slow.
2. **Real Estate / Safe Assets** - lower income (5%/round) but this is
   *the* asset that actually keeps you safe: it counts far more toward
   your defense than cash does (see Section 6), so it's what actually
   stops an attack from succeeding in the first place. It's no longer
   automatically untouched *if* an attack does succeed (Section 6's
   "what happens if a takeover succeeds" now draws from total wealth,
   Real Estate included, as a last resort after cash and Company), so
   think of it as "the asset that makes you hard to beat," not "the
   asset nothing can ever touch." The deliberate "safe harbor" choice,
   just not an absolute one anymore.
   **Where it comes from**: you're buying into the open market, diversified
   property, not one specific listing you're competing with other players
   for. No scarcity minigame, no "someone else got there first", the same
   abstraction "The Market" below already uses for stocks: you're accessing
   an outside financial system, not drawing down a shared pool at the
   table.
   **Buying and selling both cost something.** A review caught that selling
   Real Estate (below) had a real 15% cost but buying it was completely
   free, an asymmetry nobody had actually decided on, it just fell out of
   the sell-side mechanic being designed first. Fixed: buying now also
   takes a small closing cost (~3%), real but far cheaper than a distress
   sale, so Real Estate is a genuine commitment on both ends, not a free
   in/costly out lever. Simulation-tested clean, no balance impact, and
   modestly *helps* the anti-snowball margin under realistic play (85.9%→
   90.6%, see BALANCE_TESTING.md Part 7).
   **Liquidating it voluntarily**: converting some of it back to cash on
   your own terms, any time, takes the same 15% haircut (real transaction
   friction, not full market value) that a forced capture would.
   Simulation-tested
   two ways: as a rescue valve for a player low on cash, and as a deliberate
   move to fund joining a pile-on against a runaway leader. The tactical
   version never actually triggered in testing (0 times across 300 games,
   see BALANCE_TESTING.md Part 7's addendum): a well-functioning anti-
   snowball fix catches leaders before their defense grows large enough
   that a solvent challenger would ever need the extra cash. Not a dead
   end, just evidence the correction mechanic is doing its job.
3. **The Market** - **redesigned around Industries, not individual
   rivals** (see the full writeup below, right after this list). You
   invest in a *sector*, not a specific player's company, and read
   round-by-round scenario text to decide where the money's headed.
   Replaces the earlier "long/short a specific rival" design entirely.
4. **Loans** - borrow to invest bigger than your savings allow. Interest
   rises the more leveraged you get (not a flat rate - flat-rate loans were
   simulation-tested and turned out to be a risk-free exploit, see
   BALANCE_TESTING.md Part 2, Finding 2). Overleverage enough and you can go
   bankrupt: creditors seize ~85% of your holdings and the remaining debt is
   discharged - diminished but still in the game (see Section 8.4).
   **The money has to come from somewhere.** Loans are drawn from **the
   Bank**, which has real, finite capital, not an infinite tap; if enough
   players lean on credit at once, the Bank's capacity tightens and later
   borrowers get worse terms or can't borrow at all, a real credit crunch,
   not just a rule on paper. **Player-to-player lending** (a living player
   lends directly to another at a rate above the Bank's, in exchange for
   real counterparty risk, the lender eats it if the borrower defaults) is
   designed but not yet simulated - see BALANCE_TESTING.md Part 5.
   **The Bank also pays interest on deposits**, not just charging on
   loans: park Cash above a small working-cash floor with the Bank and
   earn a modest, safe 4%/round, deliberately below every active option
   (Company, Real Estate, a Joint Venture, even the Bank's own cheapest
   loan rate), so it beats doing nothing without ever being smarter than
   actually investing. Built directly to answer why idle cash should have
   any legitimate use besides eroding to inflation (step 7 above) or being
   spent outright - simulation-tested, see BALANCE_TESTING.md Part 12.
5. **Joint Ventures** - team up with an ally on a shared position in one
   Industry, pool money for a return neither gets solo, but either partner
   can drain it early and keep the majority (65/35 split, simulation-
   tested - see BALANCE_TESTING.md Part 1). Its growth is exactly that
   Industry's scenario delta, the same number moving Company income and a
   solo Market bet, no separate guaranteed rate and no extra risk
   multiplier stacked on top, so a JV's expected return is identical to
   investing in that Industry alone. What forming one actually buys you is
   scale (pool more than either partner could bet solo) and real
   betrayal risk (see Section 7's full walkthrough, worked numeric
   example, and BALANCE_TESTING.md Part 12).
   **"Reputation" isn't a hidden score, it's just what everyone already
   saw happen.** A JV drain is a public event, the pot visibly moving
   between two named players, not private math, so a second proven
   betrayal costs you twice, openly: other players simply remember and
   stop offering you new JVs (no separate score to track, they were in
   the room), and it costs you directly in the one number the whole table
   already watches, a real, visible Power hit the instant the second
   betrayal is confirmed (see Section 7).
   **Two allies at a time, max.** Not a limit anyone had actually decided
   on, it fell out of how the bots were tuned, until it got questioned
   directly. A JV partnership and a Defense Pact currently share the same
   relationship (allying with someone covers both at once, not two
   separate slots), and the cap applies to that combined relationship.
   Simulation-tested up to unlimited: the six-archetype pod plateaus at a
   cap of 3 or higher with no further change (only 2-3 archetypes actively
   seek alliances there at all), so a real table, where every human player
   might want to ally, is likely a bigger risk than this bot test can show.
   2 is the validated, recommended cap. See BALANCE_TESTING.md Part 8.
6. **Takeovers** - go after a rival's whole company (see Section 6).
7. **Gold** - a flight-to-safety hedge, not tied to any one Industry. Low
   and flat in ordinary years, a real gain specifically during crisis
   scenarios (war, recession, a financial shock), a mild pullback during
   broad optimism (see Section 5A). Not a growth strategy, a defensive one:
   simulated as something only cautious, diversifying players bother with,
   everyone else is chasing bigger returns elsewhere and has no reason to.
   **Not yet part of the liquidation cascade** (Section 5.4's cash-then-
   Company-then-Real-Estate order doesn't draw on Gold yet if someone owes
   more than that covers), a known scope gap, not a design decision.

## 5A. Industries and Market Events

A full redesign of The Market, decided directly: instead of betting for or
against one specific rival's company, players invest in **Industries**,
and a round-by-round event system moves those industries up or down based
on logical, readable cause and effect, not random noise.

**Onboarding.** Every player picks a company name, an icon, and **one
Industry** for their company, alongside the existing name/logo
customization (Section 8.6). Ten industries, fixed:

**Healthcare, Technology, Pharma, Energy, Financial Services, Consumer
Retail, Agriculture, Manufacturing, Media & Entertainment, Property.**

("Property," not "Real Estate": that name is already the defensive asset
class, Section 5.2, using it twice would be genuinely confusing at the
table.) With 3-8 players and 10 industries, most industries have zero or
one player in them, a few might overlap, that's fine, industries aren't a
scarce resource players compete over.

**The Market itself**: instead of taking a stake in one named rival, you
put money into an **Industry**, long (betting it rises) or short (betting
it falls). It pays out based on that industry's movement each round, not
any individual company's fortunes.

**Scenario events, one per round.** Each round, one scenario is drawn and
shown to the whole table as plain text (no numbers), with a **logical**,
not random, effect on each of the ten industries, most scenarios move only
a few industries and leave the rest flat. A player's own Company income
that round is affected too, if their company is in an affected industry,
on top of whatever Market bets anyone placed on that sector. This is the
main answer to a separate problem raised this session (the Building Phase
reducing to a solved formula, Section 4): reading a scenario correctly is
real financial-literacy skill, not a dice roll, and it's genuinely
unpredictable round to round, so it can't be memorized the way a fixed
income-rate comparison could.

A first working set of scenarios (not exhaustive, more can be added
without touching the mechanic itself):

| Scenario | Industries affected | Gold |
|---|---|---|
| "A major regional conflict breaks out" | Energy ↑↑, Manufacturing ↑, Pharma ↑, Agriculture ↓, Consumer Retail ↓ | ↑ |
| "A breakthrough vaccine is announced" | Pharma ↑↑, Healthcare ↑, Media & Entertainment ↑ | - |
| "Interest rates are cut sharply" | Property ↑↑, Consumer Retail ↑, Technology ↑ | ↑ |
| "A major tech company reports a data breach" | Technology ↓↓, Financial Services ↓ | - |
| "A bumper harvest season" | Agriculture ↑, Consumer Retail ↑ | - |
| "A severe drought hits key farming regions" | Agriculture ↓↓, Consumer Retail ↓ | slight ↑ |
| "A new blockbuster streaming platform launches" | Media & Entertainment ↑↑, Technology ↑ | - |
| "Oil prices crash on oversupply" | Energy ↓↓, Manufacturing ↑, Consumer Retail ↑, Agriculture ↑ | slight ↑ |
| "A recession is officially declared" | Consumer Retail ↓↓, Financial Services ↓↓, Technology ↓, Property ↓ | ↑↑ |
| "A landmark trade deal is signed" | Manufacturing ↑↑, Agriculture ↑, Technology ↑, Consumer Retail ↑ | slight ↓ |
| "Consumer confidence hits a record high" | Consumer Retail ↑↑, Media & Entertainment ↑, Property ↑ | slight ↓ |
| "A cybersecurity crisis hits financial institutions" | Financial Services ↓↓, Technology ↓ | ↑ |
| "Housing demand surges in major cities" | Property ↑↑, Financial Services ↑ | - |
| "Global supply chains face major disruption" | Manufacturing ↓↓, Consumer Retail ↓, Technology ↓, Agriculture ↓ | ↑ |
| "A wave of mergers sweeps the healthcare industry" | Healthcare ↑, Pharma ↑, Financial Services ↑ | - |
| "Renewable energy investment surges" | Energy ↑, Manufacturing ↑, Technology ↑ | - |
| "A major retailer files for bankruptcy" | Consumer Retail ↓↓, Property ↓, Financial Services ↓ | slight ↑ |
| "Streaming and gaming demand hits an all-time high" | Media & Entertainment ↑↑, Technology ↑ | - |
| "A wave of automation disrupts manufacturing jobs" | Manufacturing ↑, Technology ↑, Consumer Retail ↓ | - |
| "A quiet, uneventful year in the markets" | everything flat | - |

**None of these are fixed percentages.** `↑↑` / `↓↓` and `↑` / `↓` are
*characters*, not numbers, a strong move always means "roughly the same
shape of strong," not "exactly 8%, every single time." The actual size is
rolled fresh each time that scenario lands: a strong move (`↑↑`/`↓↓`)
comes out anywhere from 4% to 20% in that direction, a moderate one
(`↑`/`↓`) anywhere from 1% to 8%. The ceiling is set wide on purpose, a
real crisis or boom can occasionally run far hotter than the typical case,
the same way a real recession isn't always exactly as bad as the last one.
Unlisted industries stay flat that round. Real Estate reacts to the
Property row too, at half strength (see below), inheriting whatever number
Property actually rolled that round, not a separately-rolled number of its
own. Built and simulation-tested, see `BALANCE_TESTING.md` Part 12 and 13,
this was a genuine pivot away from the long/short-on-a-rival mechanic
validated earlier (Parts 6, 7, and 9), not an addition alongside it, those
specific numbers no longer apply, this replaced them.

**Real Estate and Gold both react to the same scenario system, not just
Company income.** Two direct answers to "why should Company income be the
only thing that isn't a flat guaranteed number":
- **Real Estate** feels that round's Property delta too, at half strength
  (whatever Property actually rolled that round, halved, not a separately
  rolled number). Real Estate stays the calmer, defense-weighted asset on
  purpose, it's not meant to be Company's twin, but it isn't fully
  insulated from the world either.
- **Gold** is a new, separate asset class: a flight-to-safety hedge, not
  another Industry a company can belong to. It grows around a low ~2%/round
  in ordinary years, itself rolled fresh each round rather than sitting at
  an exact 2% every time (a value-preserver, not a growth engine, real
  gold doesn't pay a dividend, and drifts a little on its own even with no
  news), and gets a real kicker specifically during crisis-flavored
  scenarios, war, recession, a financial-system shock, the "Gold" column
  above, while genuinely upbeat scenarios (a trade deal, a consumer-
  confidence high) pull it slightly negative, money chasing growth assets
  instead. That's the actual point of holding it: it does
  relatively better exactly when Company income and the Market are doing
  worse, the same real-world logic that makes gold a hedge and not just
  an eleventh industry. Simulation-tested balance-neutral, see
  BALANCE_TESTING.md Part 12.

Directly answers the exact complaint that prompted it: a player who always
reinvests 90% of new cash into Company for the whole Building Phase (the
"solved formula") used to land on the *exact same* final Company value
every single game (155.74, zero variance, 500 trials). With Industries on,
the same fixed strategy now lands anywhere from 129.89 to 183.74 depending
purely on which scenarios got drawn, a real spread the player doesn't
control just by playing "correctly." Full-game balance holds up too, still
clean by this file's standing bar with Industries active alongside Joint
Ventures and Bank deposits (Part 12): Socialite still wins most games, no
archetype crosses 50%, and for the first time in this project's testing
history a third archetype (Diversifier) takes a real share of wins (7.2%),
evidence Industries opens a genuine new path to winning rather than just
adding noise.

One property worth naming honestly: the twenty scenarios above aren't
perfectly symmetric (35 individual industry effects are positive, summing
to +1.72, versus 21 negative, summing to -1.16), so Company income and
anything tied to it (Joint Ventures, below) run slightly above a neutral
average over many rounds. This mirrors real economic history, expansions
outnumber contractions, and isn't treated as a bug, but a future balance
pass could tighten it if games start trending too far upward across many
rounds.

## 5B. Every income and cost source, exact rates

Asked directly: every rate in the game, in one place, instead of scattered
across Section 5's prose. **Not flat where it looks flat.** The general
rule this whole redesign follows: the *safer* an option is, the *lower and
flatter* its rate; anything that can actually lose money gets its rate
tied to the same scenario system instead of a fixed number, so nobody can
solve the game by memorizing a table of guaranteed percentages.

**Income and growth, from safest to riskiest:**

Only Bank deposit interest is a genuinely fixed number, on purpose: it's
the one deliberately risk-free option, the same way a real bank account
doesn't pay a variable rate. Everywhere else below, the tier (how strong,
which direction) is fixed by the scenario, but the exact size is rolled
fresh from a range every round, never the same number twice, see Section
5A's tier ranges for the actual `(min, max)` on each.

| Source | Rate | Real risk? |
|---|---|---|
| Bank deposit interest | 4%/round, flat, the one genuinely fixed number in this table | None. The explicit safe floor, deliberately below every option below it. |
| Real Estate income | ~5%/round base, +/- half of whatever that round's Property roll came out to | Low. Stays the calm, defense-weighted asset on purpose. |
| Gold | rolled each round from a low band centered near 2% even in ordinary years, plus a real kicker rolled from a wider range during named crisis/boom scenarios (see Section 5A) | Low, and countercyclical, its whole job is doing better exactly when everything else is doing worse. |
| Company income | 10%/round base, +/- a rolled value for the player's own Industry (a moderate tier rolls 1-8%, a strong one rolls 4-20%, 0 if unaffected that round) | Real, and occasionally severe: a strong negative roll can push a round's income negative, not just lower. |
| Market (an Industry position, long or short) | No base rate. The rolled scenario delta for that Industry, long gains what it gains, short is the exact mirror | Real, full exposure, no floor. Without Industries on, falls back to a flat 8%/round (`STOCK_INCOME_RATE_FALLBACK`), the old, pre-redesign number, kept only so the mechanic still functions with Industries off. |
| Joint Venture | Same as a Market position in its assigned Industry, no separate rate. Without Industries on, falls back to a flat 12%/round (`JV_GROWTH`) | Real, identical to a solo Market bet in that Industry, plus betrayal risk on top (Section 7). |

**Interest and borrowing costs:**

| Source | Rate | Notes |
|---|---|---|
| Bank loan | 8% base + 35% x your leverage ratio (debt / total wealth) | Rises the more overleveraged you already are, not flat, see Section 5 item 4. |
| Peer-to-peer loan | 20%/round, flat | Well above the Bank's typical 8-20%, the real premium for unsecured credit from another player, not an institution. |

**Taxes (all currently experimental, feature-flagged, not in the base
ruleset yet, see BALANCE_TESTING.md Parts 6, 9, 12):**

| Tax | Structure |
|---|---|
| Income tax | Marginal slabs on total profit earned that round (every source combined): 0% up to 5, 5% from 5-15, 10% from 15-30, 15% from 30-50, 20% above 50. Modeled on India's actual income tax structure. |
| Net worth tax | Marginal slabs on total Power: 0% up to 100, 5% from 100-200, 10% from 200-300, 20% from 300-400, 30% above 400. |
| Idle cash erosion | 3%/round on Cash held above 10 (a protected working-cash floor), representing inflation on money that isn't invested anywhere. Deposited cash (above) is exempt, it isn't idle. |

**Transaction friction:**

| Action | Cost |
|---|---|
| Buying Real Estate | 97 cents on the dollar, a 3% purchase cost |
| Liquidating Real Estate | 85 cents on the dollar, a 15% haircut for selling in a hurry |
| Bankruptcy | Creditors seize 85% of everything (Cash, Company, Real Estate, Gold, Market and JV positions), the remaining 15% and your debt are both discharged |

**Combat percentages** (Section 6):

| Mechanic | Rate |
|---|---|
| Takeover / counter-attack capture | 25% of the target's *total* wealth, cash first, then Company, then Real Estate |
| Failed attack penalty | Attacker loses 50% of what they staked, split evenly between the defender and the Bank |
| JV drain split | 65/35 to the drainer if only one side drains, 40/40 (20% lost to friction) if both drain the same round, 50/50 if neither drains |
| Second proven JV betrayal | An immediate, visible ~15% hit to the drainer's own total Power, docked the instant a second drain is confirmed (across any of their JVs); a first drain costs nothing beyond the relationship itself |
| "Gang up on the leader" trigger | Any player whose total Power exceeds 1.05x the second-place player's becomes a valid counter-attack target |

## 6. Combat: attacking and defending

**What everyone can actually see.** Asked directly, and it went through
two drafts. First draft: show every player's full breakdown (Cash,
Company, Real Estate, stocks, Debt) at all times, reasoning that the
anti-snowball mechanic depends on players reading "who's rich and
undefended," and Power alone doesn't tell you that (someone with high
Power from a big company could have almost no liquid cash, someone with
modest Power but all cash could be genuinely dangerous, and a Power-only
leaderboard can't distinguish them). Correctly rejected: an accurate
number, or even an accurate bucketed rating, is just as conclusive as the
real thing, it removes the actual decision instead of restoring it, "if
you already know how good their defense is, attacking anyway is just
stupidity."

**Settled design: only Power is shown, exactly, always. Nothing else is
visible by default.** Everything else, cash, Company, Real Estate,
stocks, Debt, exact defense or attack capability, is genuinely unknown
unless it passes through Declare/Audit (Section 8.3):
- **Declarations are always about your own position.** You can claim
  something about your own holdings to deter or bluff, the same way Coup
  works, you don't get to declare things about someone else.
- **Any player can Audit any Declaration**, not just whoever it directly
  threatens, at a resource cost, revealing the truth. Caught lying is
  penalized harder than a failed Audit (already established).
- Declared Defense Pacts stay the one exception that's automatically
  public (Section 7), since the whole point of declaring one is the
  deterrent value; covert ones stay hidden until a fight actually happens.

This makes "who's rich and undefended" a real question you have to spend
a resource to answer, not a leaderboard lookup, seeing two rivals' cash
piles (by choosing to Audit them) and correctly reading "we're both
exposed, let's team up" is the game working as intended.

**Honest tradeoff**: every win-margin number in `BALANCE_TESTING.md`
comes from bots with perfect information, they read exact defense values
directly rather than spending an Audit to learn them. Real play, with
only Power visible by default, makes the "gang up on a leader" mechanic
genuinely harder than the bots demonstrate, real players need to actually
invest in Audits to approach what the bots get for free. Not a flaw, real
texture, but the validated margins describe a more-informed table than
the live game will actually have.

- **Attack power is your cash only** (a portion of it), plus allies
  backing you, **not your Company, Real Estate, or stock holdings.** Those
  grow your Power but don't arm you; only liquid cash does.
- **Defense is Real Estate (heavily) plus a portion of cash**, plus allies
  defending you, **also not Company or stocks.**
- **When can you attack?** Any time in the Conflict Phase where your
  attack power exceeds the target's defense, both derived values above,
  not a direct comparison of total Power.
- **Do you need allies to attack?** Not always - **it's an attack-power
  vs. defense comparison, not an ally requirement.** A rich-enough solo
  player (in liquid cash specifically) can take on an allied group if
  their attack power genuinely exceeds the group's combined defense;
  allies are the easiest way to add power, not a mandatory gate. (This was
  a real gap in an earlier draft - corrected after being challenged on it
  directly.)
- **How do you defend?** Two ways: park money in Real Estate (which is
  built to actually protect you - simulation-tested, see Section 5.2/#2),
  or spend directly on security that round at the cost of growth. Allies
  can also rally to defend you, using the same "support" concept that lets
  people gang up to attack.
- **Defender's edge:** in a close fight, the defender wins (defense counts
  at a 1.05x bonus when compared) - borrowed from Risk's dice rules, where
  attacking only makes sense with a real edge, not just parity.
- **You can't see an attack coming that exact round** - everyone locks in
  moves secretly and they resolve together. What you *can* do is read the
  warning signs beforehand (who's rich and undefended, who's been forming
  alliances) and defend proactively.
- **Post-Attack Shield:** after being successfully taken over, you're
  immune to further takeovers for 2 rounds. Without this, simulation
  testing showed a single attacker will just repeatedly farm the same
  undefended victim for the rest of the game (see BALANCE_TESTING.md Part
  2, Finding 4) - exactly the "veterans farm new players" complaint our
  own market research flagged as the top churn cause in this genre.
- **Anyone can gang up on a runaway leader**, not just dedicated
  attackers - simulation-confirmed (BALANCE_TESTING.md Part 2, Finding 5):
  without this, one aggressive player wins unopposed every time; with it,
  the winning strategy flips to whoever's well-allied, and the top-two gap
  shrinks by 97%. This only works if relative Power is clearly visible to
  everyone at the table - that's a UI requirement, not just a rules one.
- **What happens if a takeover succeeds:** the attacker captures 25% of the
  target's **total wealth**, not just liquid cash + company. Changed from
  the original "Real Estate untouched" design, per direct instruction: the
  target pays from cash first, then Company, then Real Estate (at the
  standard 15% liquidation haircut, Section 5.2) if the rest isn't enough.
  Real Estate is still the best defense you can build, it still counts
  far more than cash toward whether an attack succeeds at all, but it's no
  longer 100% immune to what happens *after* an attack lands. Simulation-
  tested: this strengthens the anti-snowball margin further (85.9% →
  90.0%, gap 11.1% → 21.3%, see BALANCE_TESTING.md Part 11), because a
  bigger single hit against a Real-Estate-heavy target also makes whoever
  landed it look like a bigger threat sooner, triggering the "gang up"
  correction faster.
- **What happens if a takeover fails:** the attacker still loses 50% of
  what they committed, same as before, but that loss no longer just
  vanishes. Half goes to the defender who successfully protected
  themselves, a real reward for defending, not just an absence of loss;
  half goes to the Bank (Section 5.4). If the attacker doesn't have enough
  cash to cover it, the same cash-then-Company-then-Real-Estate cascade
  applies to them too. Built and tested, but honestly: these bots use
  perfect information and never actually fail an attack they attempt
  (0 failures across 2,700+ attempts tested), so this mechanic can't be
  balance-validated by bot simulation at all, it only matters once real
  players are deciding under the reduced visibility above, where
  miscalculating is actually possible.

## 7. Defense Pacts - alliances that protect, not just profit

**What actually happens to each player's Power when an alliance ends.**
Asked directly and worth answering precisely, since Joint Ventures and
Defense Pacts work completely differently here:

- **Your individual Power components** (Cash, Company, Real Estate, Stocks,
  Captured value, Debt) are **never merged, pooled, or shared**, by either
  alliance type, ever. They stay 100% your own the entire game.
- **A Defense Pact pools nothing.** It's a promise, not a transaction: an
  ally's cash counts toward *your defense calculation* while the pact is
  active (Section 6), a temporary borrowed weight in one formula, not a
  transfer of anything. When the pact ends, that weight just stops being
  added. No asset ever changed hands, so there's nothing to distribute.
- **A Joint Venture is a shared position in one Industry, not a separate
  bet with its own guaranteed rate.** On formation the two partners pick
  (or, for these bots, get randomly assigned) one Industry for the
  venture, and the pot moves with that Industry's real scenario delta
  every round, exactly the same number that moves a solo Market position
  or a Company in that Industry. If Healthcare is down 8% that round, a
  Healthcare JV is down 8%. Full stop, no separate multiplier, no
  guaranteed floor.
- **That means a JV's expected return is identical to just investing in
  that Industry solo.** The entire reason to form one instead is what a
  solo position can't offer: two partners can pool more money into one
  Industry bet than either could alone, and either one can drain the
  shared pot early and keep the majority, a real trust problem a solo
  bet never has.
- **The pot persists across rounds, it doesn't reset every round.** It's
  seeded once with both partners' opening stake, and grows or shrinks in
  place each round after that with the Industry's movement. Either
  partner can add another equal top-up on top in a later round if both
  can spare it, compounding the position further; if they can't spare it,
  the pot just keeps existing and moving on whatever's already in it.
  Nothing pays out, and nobody has to decide anything, until someone
  actually drains it.

**The backstab process, step by step, with real numbers** (Section 5's
65/35 split, in full):
1. Two players agree to a JV and it's assigned an Industry, say
   Healthcare. Each puts in 10, the pot opens at **20**.
2. Round 2: nobody drains, both can afford to top up. A top-up isn't
   locked at the original 10 forever, it's 20% of whichever partner has
   less Cash that round, floored at 10, so it naturally grows larger as
   both partners get richer over the game. Healthcare has a flat year
   this round (rolled delta near 0%). Pot stays close to **40**.
3. Round 3: Healthcare gets a strong scenario, "A breakthrough vaccine is
   announced," and the roll comes out +6% this time, not a fixed number,
   a fresh roll every time this scenario lands. Neither tops up this round
   (one partner's short on cash). Pot: 40 x 1.06 = **42.4**.
4. Round 4: another strong Healthcare scenario lands, rolling +3% this
   time. Pot: 42.4 x 1.03 = **43.7**. **This is the moment a backstab
   actually pays**: one partner privately decides to drain instead of
   letting it ride. They get 65% of 43.7 = **28.4** straight into their
   own Cash. The partner who didn't drain gets the remaining 35% =
   **15.3**. Compare that 15.3 to what an even split would have paid
   (21.85 each): the drainer walked away with 28.4 for two rounds of 10
   each (20 contributed), a real, immediate profit on top of what an
   honest split would have paid them, at the cost of the partnership.
5. **Why would someone actually do this, concretely**: the profit motive
   is exactly that 28.4-vs-21.85 gap, real money, right now, no waiting.
   It's most tempting after a run of good scenarios has grown the pot
   large (a bigger pot means a bigger absolute gap between 65% and an
   honest 50%), and most tempting for a player who needs cash *this*
   round, to fund an attack, cover a tax bill, or shore up defense before
   Conflict Phase opens, over a player who's comfortable letting the
   position keep compounding. It is never forced, and a Turtle-style
   cautious player who values the ongoing relationship over one big
   payday has every reason to never drain at all.
6. **If both drain the same round**: a smaller, even split (40% each)
   instead, neither one gets the full drainer's cut, the two betrayals
   partly cancel each other out.
7. **If neither drains**: nothing pays out, the pot simply carries into
   next round, still moving with Healthcare, still growable with another
   top-up.
8. **A drain is recorded (`drain_count`) and ends that JV, in full view of
   the table.** This isn't a private update, the pot visibly moving from
   the shared position into the drainer's own Cash is exactly the kind of
   thing everyone at the table sees happen, "reputation" doesn't need a
   separate score anywhere, players simply remember who did this to whom.
   A **second** proven betrayal (across any of a player's JVs, not just
   one) costs the drainer directly and visibly: an immediate Power hit,
   right then, roughly 15% of their current total wealth, docked on the
   spot (BALANCE_TESTING.md Part 1, Part 12). Not a hidden counter,
   not a quiet tax on future opportunities nobody can check, an actual
   drop in the one number this whole game already commits to being the
   only thing anyone tracks. The partner drained on, and everyone else
   watching, has every reason to stop offering that player new JVs,
   nothing in the rules forces them to, they simply know better now.

Beyond Joint Ventures (which are financial), you can form a **Defense
Pact**: a promise that if your partner is attacked, you help defend them.
Borrowed from Civilization's alliance mechanics. Gives alliances a
protective dimension, not just a money-making one.

**Declare to reinforce.** A review flagged a real contradiction: Section 6
requires visible Power (including ally backing) so the table can gang up on
a leader, but that seemed to force every alliance into the open, leaving no
room for the secret, bluffable commitments the game's Coup DNA depends on.
Fixed by reusing the existing Declare/Audit system on the Pact itself:
- **Declared**: you publicly commit to the pact. It visibly adds to your
  partner's defense number, a real deterrent, but everyone now knows you're
  allied.
- **Covert**: you stay off the record. It doesn't count toward your
  partner's visible defense, so an attacker can be lured into a fight that
  looks winnable and isn't, but if it's ever audited and found to be a
  bluffed commitment with nothing behind it, that's penalized harder than a
  failed audit, same as any other false Declaration.
Simulation-tested (`sim/human_sim.py`, see BALANCE_TESTING.md Part 3): with
roughly half of all pacts going covert, this reproduces the validated
Finding 5 numbers exactly in the rational-play case. It doesn't reopen the
anti-snowball fix on its own.

**Ending a Pact.** Either side can walk away from a Defense Pact whenever
they want, allies aren't locked in forever, but flip-flopping isn't free
for a pact that was ever public:
- **Ending a covert pact** costs nothing. Nobody outside the pact knew it
  existed, so there's nothing publicly broken.
- **Ending a declared pact** costs you, the same "publicly broken your
  word" cost as a Joint Venture drain, and takes effect at the *start of
  next round*, not immediately. You can't declare a pact to prop up a
  defense number for one attack and un-declare it the instant that attack
  resolves. **Built and simulation-tested** (BALANCE_TESTING.md Part 15):
  a first declared break costs nothing beyond the relationship itself, a
  second costs a real, visible ~15% Power hit, docked on the spot, the
  same principle and the same size as the JV reputation fix (Section 5,
  Section 7), not a hidden "reputation" score nobody can see.
This means switching who you back is always possible, real allegiance
shifts are part of the game, but doing it loudly and often costs you the
same way backstabbing a Joint Venture partner does. Simulation-tested
clean: Socialite stays the dominant winner and the anti-snowball margin
holds in the same band it was already in, with or without the mechanic
active (BALANCE_TESTING.md Part 15).

## 8. Bluffing, hidden roles, and personal stakes

### 8.1 Power Cards - Coup's mechanic, reused for finance
Your colleague's idea, and it fits neatly on top of what's already
designed. Like Coup, each player secretly holds one Power Card granting one
special action and one special block; you can bluff about which one you
have; anyone can challenge your claim. **This reuses the existing
Declare/Audit system** rather than needing a whole new mechanic, claiming a
Power Card *is* a Declaration, challenging it *is* an Audit, at the exact
costs and penalties Section 8.3 now defines.

**The naming collision flagged in the last pass is fixed**: the Power Card
formerly called "The Raider" is renamed **The Marauder** below. "The
Raider" (a card) and the **Hidden Raider** role (Section 8.2) used the same
word for two unrelated things, real confusion risk at a live table ("wait,
the card or the role?"), and the fix costs nothing since the card's
mechanics were never attached to the name.

**Deal and lifecycle.** At game start, each player is secretly dealt one
of the 7 card types below, no duplicates: with 5 or 6 players, one or two
of the 7 types simply aren't in play that game, the same "not every
Industry has a player in it" logic Section 5A already uses for a resource
that doesn't need to be scarce. **Each card's action and its block are
each usable exactly once per game**, independently, most cards get one
real moment for each. This is a real, one-time swing, not a repeatable
income stream: 15 rounds is long enough that unlimited-use abilities would
have to be priced far weaker to stay balanced, and this game already has a
pattern for rare, high-impact, once-ish events (a takeover, a JV drain, the
Defense Pact breakup penalty's second strike) that Power Cards fit into
more naturally than a repeatable one would. **A claim that repeats a move
already legitimately used this game is automatically a lie if the claimant
truly held that card**, real texture for a sharp Audit read ("you already
did that this game") that costs nothing to add since it falls straight out
of the one-per-game rule.

**Phase gating matches Section 4's existing rule exactly**: a Power Card
move that takes value from another player without their consent is an
attack, and is Conflict Phase only, same as a takeover. A move that only
touches the user's own position, or only reveals information, is available
in every round, Building Phase included, the same "only attacks are
phase-gated" principle Section 4 already states for the rest of the game.

The 7 cards:

- **The Financier** (income)
  - *Action, Capital Raise* (any round): add 20% of your current Company
    value straight to your own Cash, a one-time financing round. Doesn't
    touch anyone else, so it's legal in the Building Phase.
  - *Block, Freeze* (any round, named target, an attack): zero a named
    target's Company and Real Estate income for this round only.
- **The Marauder** (renamed from "The Raider")
  - *Action, Smash and Grab* (Conflict Phase only, an attack): capture 10%
    of a named target's total wealth straight to your own Cash, the same
    cash-then-Company-then-Real-Estate cascade a takeover uses (Section 6),
    deliberately smaller than a takeover's 25% and not a full takeover:
    it doesn't trigger a Post-Attack Shield and doesn't count as a
    "runaway leader" strike either way. If blocked by a Guardian, it fails
    exactly like a failed takeover attempt (Section 6): the Marauder loses
    50% of the intended capture, split between the target and the Bank.
- **The Guardian** — one job, no action of its own
  - *Block, Bodyguard* (Conflict Phase only): fully negate one attack
    against your own company, whether it's a takeover, a counter-attack, or
    a Marauder's Smash and Grab. The attacker still pays the normal failed-
    attack penalty. Matches Section 6's "Declarations are always about your
    own position" rule: a Guardian can only protect themselves, not an ally.
- **The Broker** (cash)
  - *Action, Skim* (Conflict Phase only, an attack): take 8% of a named
    target's current Cash directly, a pickpocket, not a raid, smaller than
    the Marauder's already-smaller-than-a-takeover hit.
  - *Block, Vault* (any round): fully negate one Skim attempt against you.
    The failed Broker forfeits half the attempted skim to the Bank, the
    same shape as a failed attack at a proportionally smaller scale.
- **The Banker** (loans)
  - *Action, Easy Terms* (any round): take a Bank loan this round at the
    flat 8% base rate with no leverage risk premium added (Section 5B's
    normal 8% + 35% x leverage formula is waived for this one loan), still
    limited by the Bank's actual available pool.
  - *Block, Standstill* (any round): for one round, your existing debt is
    charged interest at the flat 8% base only (your leverage premium is
    waived) and you can't be denied a loan due to a Bank capacity
    shortfall. A deliberate reframing of the original "blocks someone
    calling in a loan against you" idea: peer-loan recall isn't a modeled
    mechanic (Section 5 item 4), so Standstill is scoped to shield against
    exactly the leverage-driven costs the Loans system already charges,
    not a mechanic that doesn't exist yet.
- **The Insider** (information) — one job, no block
  - *Action, Tip-Off* (any round, named target): privately learn that
    target's true Cash, Company, Real Estate, Gold, and Debt (their full
    hidden breakdown, Section 6), without them being told they were looked
    at. The Declaration ("I'm claiming to be the Insider") is public and
    auditable as always; the *result* of a successful, un-audited peek
    stays private unless the Insider later chooses to leak it (Section
    8.4). No block exists for this card on purpose, matching the original
    design: information asymmetry is the whole point, there's no
    defending against being looked at, only against being told about it.
- **The Analyst** (**locked in** as the 7th card, Section 5.3's Market)
  - *Action, Expose or Report, pick one* (any round, named target, uses
    the card's single action-use either way): **Expose** forces a named
    target's Market (Industry) positions to be revealed to the whole
    table, publicly. **Report** issues a public "report" that shifts how
    the target's Company is perceived for one round: their *apparent*
    Company value, for attack-power and defense calculations only, not
    their real Power, moves +/-15% (the Analyst's choice of direction), the
    same figure the JV reputation penalty and the Audit lying penalty
    already use, a real, one-round perception shock, not their actual
    wealth.
  - *Block, Countermeasure* (any round): fully negate an Expose or Report
    aimed at you.

Alternatives considered but not chosen for the 7th card slot: **The
Regulator** (freeze or partially seize a rival's Real Estate for a round)
and **The Fixer** (resets `drain_count`, wiping a player's proven-betrayal
record clean). The Analyst remains the strongest fit: the Market is the
one core money mechanic none of the other six cards touch at all,
everything else already clusters around income, takeovers, loans, and
information.

**Not yet simulated.** Every number above was chosen to sit inside this
game's existing vocabulary of percentages (a takeover's 25%, a JV drain's
65/35, a reputation-style penalty's 15%) rather than invented fresh, and
every action/block pairing was checked against Section 6 and Section 4's
existing rules (self-only Declarations, phase-gating) rather than granting
a new exception. None of it has a simulated win-rate or balance read yet:
bluffing behavior is hard to model meaningfully without simulating the
bluffing itself, a separate piece of work (see BALANCE_TESTING.md Part 2,
"what this doesn't cover"). `sim/human_sim.py`'s trait framework (declared
vs. covert posture, `declare_bias`) makes this more tractable than when it
was first deferred, still real, unstarted work: a first pass would need
each archetype to have a plain probability of claiming a card it doesn't
hold and a plain probability of Auditing a suspicious claim, not real
strategic bluffing, the same honesty caveat every other mechanic in this
file already carries about the gap between fixed bots and adaptive humans.

### 8.2 Hidden Raider role
A minority of players are secretly **Raiders** - their win condition
requires certain companies to fail (activist short-sellers), invisible to
the majority **Builders** (standard Power-maximizing win condition). You're
never just wondering "will they choose greed" - you're wondering whether an
ally is even capable of staying loyal.

**First simulation pass, done.** Roughly 1 Raider per 5-6 players (a real
minority, needs at least 4 players to make sense, which is now moot given
Section 1's 5-7 player range), each secretly assigned one target. A Raider
sabotages two ways: takeover/counter-attack targeting prefers their
assigned mark over the usual richest-beatable choice, and if allied with
their target via a Joint Venture, they drain it against them far more
often (60% vs the ordinary Aggressor-only 30%). Win condition: the target
ends the game bankrupt, or below half the table's average Power.

Results (`sim/human_sim.py`, six-player pod, realistic mistakes + raid
fatigue active): adding Raiders left Builder-side win rates essentially
unchanged (Socialite 73.3% → 74.8% without vs with), the core Power game
isn't destabilized by a hidden saboteur in the mix. Raiders themselves hit
their secret win condition in **14.9%** of games, a real, achievable rate
that isn't trivial and isn't hopeless either, a first, defensible data
point, not a fully tuned number.

**Resolved**: whether Raiders should also withhold Defense Pact support
from their target. Passive under-defending has no separate representation
in the model, so a Raider allied with their own target now has a real
chance each round, once the Conflict Phase opens, to sever the pact
outright instead, using the Defense Pact breakup mechanic below (Section
7, BALANCE_TESTING.md Part 15). Raider success rate moved within a small,
inconsistent band (15.0-17.3%) with the sabotage vector active, noise at
this sample size, not a clear signal either way.

**Still open**: reveal timing (never, end of game, or a player-triggered
reveal), and whether the 14.9% success rate is the right target or needs
tuning once reveal timing and Power Cards are layered in.

### 8.3 Declarations & Audits
Any claim (a trade offer, a tip, a statement of your own holdings, a Power
Card claim) can be audited by another player at a resource cost. Being
caught lying is penalized harder than a failed audit. **Exact numbers,
given real ones didn't exist anywhere before this pass:**

- **Auditing costs a flat 5 cash**, paid by the auditor the moment they
  declare an Audit, regardless of what it finds. Flat, not scaled to
  wealth, on purpose: it should stay a real, felt cost against a starting
  stake of 20 cash without becoming irrelevant pocket change once a table's
  cash piles grow into the hundreds, the same reasoning a fixed Bank
  deposit rate (Section 5B) already uses for the one number in this game
  that's deliberately not scenario-driven.
- **A failed Audit** (the Declaration was true) costs the auditor their 5
  cash, paid straight to the player they audited, a real reward for having
  told the truth, the same "defending pays" principle a successful defense
  against a takeover already carries (Section 6).
- **A caught lie** costs the liar a real, visible ~15% of their current
  total Power, docked on the spot through the same collection cascade used
  everywhere else in this game (cash, then Company, then Real Estate),
  with the auditor's 5 cash refunded out of that penalty first. Reusing
  the exact figure the JV reputation penalty and the Defense Pact breakup
  penalty already use (Section 5, Section 7) rather than inventing a
  separate number: this is the same currency (a visible Power hit) doing
  the same job (make a specific broken trust cost something real) for a
  third mechanic in a row.

This is deliberately asymmetric in the direction Section 8.3's original
draft already promised ("caught lying is penalized harder than a failed
audit"): a failed Audit costs a flat 5, a caught lie costs a percentage of
total wealth that grows with the game and is meant to sting far more than
5 cash by the time it matters. Not yet simulated: what this does to how
often a rational bot actually chooses to Audit, since every other
percentage-based penalty in this file (JV, Defense Pact) has already been
tested and this one hasn't.

### 8.4 Ghost/Observer status
A bankrupted or fully-taken-over company doesn't vanish. Its founder
becomes a **Board Observer**, and gets a vote in the final round, same as
before.

**Backing, not just leaking.** A review flagged that "leak one piece of
information" is too thin to fill up to two-thirds of a Conflict Phase in a
live, one-sitting session, and simulation confirmed it: a heavily-farmed
player could spend up to 7 of 15 rounds with nothing meaningful to do (see
BALANCE_TESTING.md Part 3, `AvgBrokeRoundsPerPlayer`). Fixed by giving a
Board Observer a real choice instead of a one-time move: the moment you go
broke, you pick one living player to **back**.

This is deliberately **not a financial stake**. A first draft gave the
backer a 15% cut of the backed player's future captures, and that was
wrong: you're not trying to win anymore once you're a Board Observer, your
own Power isn't coming back in any way that matters, so growing it via a
cut does nothing for you, it just taxes the living player you back for no
return, there's no real answer to "why would I give up 15% of what I just
earned to someone who's out of the game." Corrected: backing is social and
informational, no cash or Power changes hands. You can still leak one piece
of information about anyone at any point, and your backing choice is what
your final-round vote is actually for, if the top two players finish
within a hair of each other, whichever one more Board Observers were
backing wins the tie.

**Co-Founder: an even better fix, added after review pushed back, then
rebuilt again once the reward structure was called out as backwards.**
Picking a name to root for isn't actually an action, correctly called out
directly: "still they just sit in the game, it's not like they can do
anything." Fair. **Co-Founder** replaces backing as the preferred outcome:
a broke player can be recruited by a living player to actively co-run
their company. As co-founder, every remaining round, they redirect a real
slice of the host's cash toward Real Estate (a genuine, repeated,
risk-management decision, not a one-time label). One co-founder per host.
Backing is now the fallback only for whoever isn't recruited.

**The first version's reward was backwards, and got called out
directly: "why extra income, then everyone would want someone to die and
take them on the team."** Right. Paying the *host* a flat income bonus for
recruiting a broke player is profiting directly from someone else's loss,
exactly the wrong incentive, and it gave the co-founder nothing of their
own to actually care about beyond "something to do." Rebuilt around a
real, tracked stake instead of a bonus:
- **The host's income bonus is gone.** Their only reason to take on a
  co-founder now is the real, ongoing Real Estate risk-management help,
  paid for with real equity dilution, not a free bonus.
- **The co-founder gets a real, growing equity stake** (7% of the host's
  Company, marked to its current value every single round, not a static
  number) that visibly counts toward their own standing in the game. This
  is the actual hook: a genuine number they're watching move, tied to a
  real decision every round, "is my host playing well, should I keep
  steering them toward safety."
- **A real comeback, not a permanent sidelined role.** Once the host can
  comfortably afford it, they can buy the co-founder out entirely, a real
  cash payout that frees the co-founder to rebuild independently or be
  recruited elsewhere. Simulated: this happens in **48% of games**, close
  to a coin flip, real and worth hoping for without being guaranteed
  (BALANCE_TESTING.md Part 12).
- **A golden parachute if the host gets taken over instead.** The
  co-founder gets 20% of whatever an attacker captures, paid straight to
  their own cash, and is freed to be recruited again. Direct answer to
  "would I even want to attach myself to someone who might get raided":
  yes, because even that downside pays you something real, unlike an
  organic bankruptcy, where there's no acquirer to pay a severance from
  and the equity is just gone. Fires in **23.6% of games**.

Simulation-validated: `AvgDeadRoundsPerPlayer` still drops to effectively
0 (0.030) at every player count tested. Host recruitment is deliberately
**random among eligible hosts, not "richest available"**: an early version
preferring the richest host quietly fed the (now-removed) income bonus to
whoever was already leading, cutting Socialite's win rate from 85.9% to
75.5%, the same snowball-reinforcing pattern this whole project kept
finding elsewhere. With random host selection and the rebuilt equity
structure, full-game balance stays clean: 84.2% → 83.2%.

### 8.5 The Final Round
Deliberately different from the rest of the game. Game theory says rational
players defect in a known final round (the "shadow of the future"
disappears) - rather than fight that, the last round is an explicit
different phase (a final vote/tally) marketed as the climax. Confirmed in
the earlier Joint Venture simulation: the strongest honest strategy wasn't
"always honest," it was "honest all game, then take the expected defection
in the final round" - worth telling players outright rather than letting
them learn it the hard way.

### 8.6 Personal touch
Players name and customize their own company (name, logo/color). Cheap to
build, makes losses sting more and wins feel more like *yours* - especially
for a group of friends playing together.

## 9. Open risks (named honestly, not yet solved)
- ~~Industries and Market Events (Section 5A) are designed but not built
  or simulated~~ **resolved**: built and simulation-tested (Section 5A,
  BALANCE_TESTING.md Part 12). Directly fixes the Building Phase "solved
  formula" complaint: the always-max-Company strategy used to land on the
  exact same final value every game (zero variance across 500 trials),
  now spreads across a 54-point range depending on which scenarios get
  drawn. Full-game balance holds with Industries active alongside the
  redesigned Joint Ventures and new Bank deposits below, and a third
  archetype (Diversifier) wins for the first time in this project's
  testing history.
- ~~Joint Ventures were a fixed 5-cash, guaranteed ~12%, no real risk~~
  **resolved**: a JV is now a shared position in one Industry, its growth
  is exactly that Industry's real scenario delta, the same number moving
  Company income, no separate guaranteed rate, no extra risk multiplier.
  A JV can lose money now, expected return is identical to investing in
  that Industry solo, the only edge it offers is pooling more capital
  than either partner could alone, at the cost of real betrayal risk. The
  pot also persists and compounds across rounds instead of resolving
  every single round. See Section 5 item 5, Section 7's full worked
  numeric example, and BALANCE_TESTING.md Part 12.
- ~~Idle cash erosion had no legitimate escape hatch besides spending
  everything~~ **resolved**: the Bank now pays interest on deposits
  (Section 5 item 4), a safe, modest, taxed return that beats erosion
  without ever beating actual investment. See BALANCE_TESTING.md Part 12.
- ~~Power Cards' 7th card - still undecided~~ **resolved**: The Analyst is
  locked in (Section 8.1). **All 7 cards now have exact, numbered mechanics**
  (action and block for each, phase-gating, the once-per-game lifecycle,
  and the naming collision with the Hidden Raider role fixed by renaming
  "The Raider" card to The Marauder), reusing Section 8.3's now-quantified
  Declare/Audit costs and this game's existing percentage vocabulary rather
  than inventing new numbers. **Still genuinely open**: none of it has a
  simulated win-rate or balance read yet, this pass was design only, no
  code. That first simulation pass is the next real step, not a rules
  question anymore.
- ~~Raider/Builder ratio and reveal timing~~ **ratio simulated**: roughly 1
  Raider per 5-6 players, 14.9% Raider success rate, no measurable effect
  on Builder balance (see Section 8.2). **Reveal timing is still open.**
- **Onboarding**: teaching Power (not just cash), the two phases, allies
  not being mandatory, and the final round being different - a lot to land
  in one sitting with a first-time group. Probably needs a guided first
  few rounds rather than a rules dump.
- ~~Round count doesn't scale with player count, and the anti-snowball
  margin has only ever been validated against the six-player pod~~
  **partially resolved**: every mechanic added since Part 7's margin fix
  (Industries, Gold, Bank deposits, Co-Founder, the JV rebuild, the Defense
  Pact breakup mechanic) had only ever been tested at n=6. Run together,
  for the first time, across the full 5-7 range: all three player counts
  now hold up (healthy archetype variety, Socialite dominant but never
  runaway, near-zero dead rounds), confirming the officially supported
  range on its own terms, not just extrapolated from the six-player result.
  See BALANCE_TESTING.md Part 16.

  **Superseded by Part 17** (see below and Section 1): the "different,
  not-yet-clean problem" this paragraph originally described (Socialite
  crossing 50% at 4 players, Aggressor winning outright at 3) turned out to
  be a roster-sampling bug, not a property of small player counts. Fixed,
  and the range is now **3 to 8**, not 5 to 7.

  **Traced and mostly resolved** (BALANCE_TESTING.md Part 17): that
  dominance problem turned out to be a roster-composition bug, not a real
  property of small player counts. `roster_for` had been handing every
  3-player game the *identical* `[Diversifier, Turtle, Aggressor]` roster
  and every 4-player game the identical four, Socialite never appeared at
  all in a 3-player game, SoloGrinder and Leverager never appeared at 3 or
  4, in this file's entire testing history. Fixed to a genuine random
  sample of the 6 archetypes. With that fixed: no archetype crosses 50% at
  either 3 or 4 players, Socialite leads at both (consistent with every
  other player count), and winner variety improves. (Building Phase
  *length* is hidden and randomized per game, see above, a related but
  separate fix for a different problem, "the Building Phase is a solved
  formula," not this one.)

  **What's still a real, open product decision, not a numbers question
  anymore**: whether to actually lower the officially supported minimum
  below 5. The evidence that excluded 3-4 players in the first place was
  measuring a biased roster as much as the player count itself, and with
  that bias fixed, 3-4 now look comparable to 5-7 on every metric this file
  tracks (lock round, win-rate variety, no single-archetype dominance).
  That's real, positive evidence, not proof a human table of 3-4 has a
  good time, the same bots-aren't-playtesting caveat every finding in this
  file carries. Two new archetypes (**The Speculator**, a concentrated
  Market bettor, and **The Prepper**, a Gold/Bank-deposit hoarder, both
  reusing existing mechanics rather than new plumbing) were also built and
  tested for the *maximum* end: **8 players reads clean**, directly
  comparable to 7 on every metric; 9-10 are not yet clean, both still lean
  on duplicate Casual bots to fill the table rather than genuinely distinct
  archetypes.
- ~~Ordinary human inconsistency weakens the anti-snowball fix more than
  expected~~ **resolved**: Finding 5's fix only ever won by a 1.1% margin
  (405.9 vs 401.3 Power), a coin flip dressed up as a validated result,
  which is why realistic imperfection could flip it so easily. Fixed at
  the root: the "how far ahead is a runaway leader" threshold that
  triggers the gang-up mechanic was lowered from 1.3x to 1.05x, keeping the
  correction engaged continuously instead of only firing once a lead is
  already dramatic. Combined with raid fatigue, Socialite wins 85.9% of
  games even under the mistakes fragility (Aggressor down to 13.3%, still
  a viable if underdog strategy, not eliminated). See BALANCE_TESTING.md
  Part 7.
- **A "fear after being hit" reaction was deliberately not modeled.**
  Multiple attempts to simulate a player playing scared and defensive for a
  few rounds after a takeover all backfired in archetype-specific ways
  (see BALANCE_TESTING.md Part 3). Real psychological reaction to being
  attacked is probably a real design factor, but needs a dedicated,
  archetype-aware modeling pass, not a bolt-on trait.
- ~~What an eliminated player does for the rest of a live session~~
  **resolved**: Board Observers can now be recruited as a Co-Founder,
  redirecting a real slice of the host's income every round in exchange for
  a modest income bonus to the host (Section 8.4), simulation-validated to
  zero out dead rounds with negligible balance cost. See BALANCE_TESTING.md
  Part 9.
- ~~Defense Pact breakup has no defined cost~~ **resolved**: ending a
  covert pact is free (nobody knew anyway); ending a *declared* pact costs
  nothing on the first break, then a real, visible ~15% Power hit on the
  second, and takes effect starting the following round, not the same
  round, mirroring the JV reputation fix's 2-strike pattern exactly
  (Section 5, Section 7). Built and simulation-tested clean: Socialite
  stays dominant and the anti-snowball margin holds in the same band with
  or without it active. See BALANCE_TESTING.md Part 15.
- ~~Should a Joint Venture partner automatically be a Defense Pact
  partner?~~ **decided**: keep them merged, one relationship, one cap
  (option (a) below), "we're in business together, we've got each other's
  backs." Splitting them into two independent relationships (option (b):
  a purely financial partner who owes you nothing in a fight, and a
  separate combat ally who isn't necessarily pooling money with you) would
  need a real re-architecture and a full retest of Part 8's validated
  `MAX_ALLIES=2`, and nothing in this file's testing history has shown a
  concrete reason to make that trade. See BALANCE_TESTING.md Part 15.
- ~~Two of four financial-depth mechanics are now validated, two still need
  fixes~~ **all four now validated**: real long/short stock positions, a
  progressive income tax (assessed once a round on every source of profit
  combined, company/Real Estate income, capture proceeds, and Joint
  Venture proceeds together, matching how income tax actually works), idle
  cash erosion, and peer-to-peer lending (all in `sim/human_sim.py`).
  Against the original 1.1%-margin baseline, three of the four broke it;
  against the widened margin, idle cash erosion and the income tax came
  back clean immediately (the income tax fix also directly answers "why
  does Aggressor barely pay it": the first version only taxed passive
  company/Real Estate income, which Aggressor barely generates, the
  corrected version taxes all profit including raid proceeds, and
  Aggressor now pays the highest effective rate of any archetype, 7.2% vs
  3-5% for everyone else). **Peer-to-peer lending** needed two rounds of
  fixing: the real mechanism wasn't "rescuing Aggressor's victims" as first
  diagnosed, it was Socialite (the only archetype that both allies and
  keeps spare cash) giving away 30% of their own war chest every time they
  lent, undermining their own counter-attack capability; capping the loan
  at 10% of the lender's cash fixed it. **Long/short stocks** is clean
  under realistic play (with the other three mechanics active) but still
  breaks the artificial zero-mistake bot baseline, a narrower, honestly
  reported result rather than a full fix. See BALANCE_TESTING.md Part 9.
  Real estate can now also be voluntarily
  liquidated for cash (at a 15% haircut) when a player is low on liquidity,
  the direct answer to "Real Estate can't be touched by an attacker, so
  what's a player's own way to convert it to cash when they need to."

## 10. MVP Scope (Live Mode)

### In scope (v1)
- 3 to 8 players, one sitting, ~45-60 minutes, with room lengths scaling
  loosely at the extremes (a 3-player game locks in a leader earlier, an
  8-player game runs a bit longer). 9-10 aren't in scope yet: both still
  rely on duplicate Casual bots in testing rather than genuinely distinct
  archetypes (Section 1, BALANCE_TESTING.md Part 17).
- Building Phase + Conflict Phase structure.
- All six money mechanics (Company, Real Estate, Market, Loans, Joint
  Ventures, Takeovers) - simulation-tested numbers from Section 5/6.
- Defense Pacts, Post-Attack Shield, Ghost/Observer status.
- Hidden Raider/Builder split (simplest version: fixed ratio).
- Company naming/customization.
- Final Round as a distinct phase.
- A clearly visible relative-Power display (e.g. a live leaderboard) -
  simulation-confirmed as a requirement, not a nice-to-have: the
  "gang up on a runaway leader" dynamic that keeps the game balanced only
  works if everyone can actually see who's pulling ahead.

### Deferred to v2+
- Power Cards (needs its own design/testing pass, reuses Declare/Audit so
  the plumbing is shared, but the 7-card balance is unproven).
- Season Mode (persistent, async, matchmade with strangers).
- Cosmetics, cross-game progression, monetization systems.

## 11. Platform & Tech
- **Target platform:** web (browser-based).
- **Client:** React + Vite (already scaffolded in `frontend/`).
- **Backend:** Python + FastAPI (already scaffolded in `backend/`).
- **Live Mode implication:** since a game is a single synchronous sitting
  (not async daily rounds), the backend needs real-time sync between
  connected players in the same room - WebSockets (FastAPI supports these
  natively), not a scheduled daily job. This is a meaningful shift from the
  original async/Season architecture and should be designed in from the
  start rather than retrofitted.
- **Round resolution logic** (Power calculation, takeover resolution, JV
  payouts) is the most important code in the game and should be
  unit-testable independent of the API/WebSocket layer - the simulations
  in `sim/` already validate this logic in Python, so the resolution
  engine can reuse the same language and much of the same logic tested
  there.
- No database-heavy persistence needed for MVP (a game lives and dies
  within one room's session) - simplifies the backend considerably
  compared to the original Season Mode plan.

## 12. Monetization (placeholder, unchanged in principle)
- Likely "one person unlocks the game, friends join free" (Jackbox-style)
  rather than per-player purchases - fits a friend-group one-sitting game
  much better than trying to monetize each participant individually.
- No pay-to-win: Takeovers, Joint Ventures, and Power Cards only stay
  meaningful if outcomes can't be bought.
