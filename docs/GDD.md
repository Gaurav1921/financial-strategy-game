# [Working Title: "Consortium"] - Game Design Doc

## 1. Pitch
A web-based financial strategy game for a small group of friends (**5 to
7**, simulation-tested: at 3 to 4 players the fixed round structure locks
the outcome in almost immediately, only one archetype ever wins, see
BALANCE_TESTING.md Part 3) playing together in one sitting - start to
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

- **Building Phase** (first third of the game): **no attacks allowed at
  all.** Only growing your company, investing, and quietly forming
  alliances. Everyone gets equal time to build a position.
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
   *the* protected asset class: it counts far more toward your defense than
   cash does (see Section 6). The deliberate "safe harbor" choice.
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
   **Liquidating it**: nothing else can touch your Real Estate, but you can
   choose to, converting some of it back to cash at any time takes the 15%
   haircut (real transaction friction, not full market value), the price of
   turning safety back into flexibility on your own terms. Simulation-tested
   two ways: as a rescue valve for a player low on cash, and as a deliberate
   move to fund joining a pile-on against a runaway leader. The tactical
   version never actually triggered in testing (0 times across 300 games,
   see BALANCE_TESTING.md Part 7's addendum): a well-functioning anti-
   snowball fix catches leaders before their defense grows large enough
   that a solvent challenger would ever need the extra cash. Not a dead
   end, just evidence the correction mechanic is doing its job.
3. **The Market** - buy a stake in *any* player's company. Believe in
   someone → profit if they grow. Think they're about to fall → bet against
   them instead. No partnership or consent needed, just a read on where
   things are headed.
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
5. **Joint Ventures** - team up with an ally, pool money for a return
   neither gets solo, but they can drain it early and keep the majority
   (65/35 split, simulation-tested - see BALANCE_TESTING.md Part 1).
   Reputation has real teeth: two proven betrayals and you lose access to
   easy income and get worse terms on anything you still manage to form.
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

## 6. Combat: attacking and defending
- **When can you attack?** Everyone's Power is visible. You can attempt a
  takeover any time in the Conflict Phase where your attack power (your
  liquid money, plus any allies backing you) exceeds the target's defense
  (their Real Estate + a portion of their cash + any allies defending them).
- **Do you need allies to attack?** Not always - **it's a Power
  comparison, not an ally requirement.** A rich-enough solo player can take
  on an allied group if their total Power genuinely exceeds the group's
  combined defense; allies are the easiest way to add power, not a
  mandatory gate. (This was a real gap in an earlier draft - corrected
  after being challenged on it directly.)
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
  target's liquid (cash + company) value. Real Estate is untouched - it's
  protected by design, not just by the defense math.

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
- **A Joint Venture pools a separate, distinct pot**, only the specific
  amount each partner contributed (10 each by default), which grows
  together while both hold. That pot exists apart from either partner's
  individual Cash the whole time it's active. When it resolves, whatever
  the pot is worth gets split and paid back into each partner's *own* Cash.

**The backstab process, step by step** (Section 5's 65/35 split, in full):
1. Two players agree to a JV, each puts in a fixed stake (10 each) into the
   shared pot. That stake leaves their own Cash the moment they commit.
2. Each round the JV stays open, the pot grows (12%/round) while it isn't
   touched.
3. Each round, both partners privately decide, same simultaneous-secret-move
   timing as everything else (Section 4's step 2): keep holding, or drain.
4. **If one drains while the other holds**: the JV ends immediately. The
   drainer's Cash goes up by 65% of the current pot; the partner who kept
   holding gets the remaining 35%, added to their own Cash. That's the
   whole betrayal, a single round's resolution, not a process that plays
   out over time.
5. **If both drain the same round**: a smaller, even split (40% each)
   instead, neither one gets the full drainer's cut.
6. **If both keep holding to the JV's natural end** (or the game ends):
   even 50/50 split.
7. A drain is recorded (`drain_count`). Two proven drains triggers the
   reputation tax: no more easy idle income, and worse growth rates on any
   JV that player still manages to form (Section 5, BALANCE_TESTING.md
   Part 1).

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
  existed, so there's no reputation to spend.
- **Ending a declared pact** costs a reputation mark, the same "publicly
  broken your word" cost as a Joint Venture drain, and takes effect at the
  *start of next round*, not immediately. You can't declare a pact to prop
  up a defense number for one attack and un-declare it the instant that
  attack resolves. Two broken declared pacts (mirroring the JV reputation
  tax's threshold) means the same tax: no easy income, worse terms on
  anything you still manage to form.
This means switching who you back is always possible, real allegiance
shifts are part of the game, but doing it loudly and often costs you the
same way backstabbing a Joint Venture partner does. Not yet simulated.

## 8. Bluffing, hidden roles, and personal stakes

### 8.1 Power Cards - Coup's mechanic, reused for finance
Your colleague's idea, and it fits neatly on top of what's already
designed. Like Coup, each player secretly holds a Power Card granting one
special move or block; you can bluff about which one you have; anyone can
challenge your claim. **This reuses the existing Declare/Audit system**
rather than needing a whole new mechanic - claiming a Power Card *is* a
Declaration, challenging it *is* an Audit. Rough set of 7, one per possible
player:
- **The Financier** - bonus income / blocks someone else's basic income move
- **The Raider** - a direct hit on a rival's company, smaller than a full takeover
- **The Guardian** - blocks a Raider's attack
- **The Broker** - skims cash from a rival / blocks being skimmed from
- **The Banker** - better loan terms / blocks someone calling in a loan against you
- **The Insider** - peek at a hidden thing (a rival's holdings, a rumor's truth)
- **The Analyst** (**locked in** as the 7th card) - manipulate the Market:
  force a rival's stock position to be revealed, or issue a public
  "report" that moves how much a target's company is perceived to be worth
  for one round / blocks another player's Analyst move against you or your
  holdings. The Market (Section 5.3) is the one core money mechanic none
  of the other six cards touch at all, everything else clusters around
  income, takeovers, loans, and information. Alternatives considered but
  not chosen: **The Regulator** (freeze or partially seize a rival's Real
  Estate for a round) and **The Fixer** (clears reputation marks / drain
  count). The Analyst is the strongest fit for making Power Cards
  reinforce the financial side of the game rather than adding another
  combat lever. Note the name collision worth fixing before this ships:
  **The Raider** (a Power Card, above) and the **Hidden Raider** role
  (Section 8.2) use the same word for two unrelated things, real confusion
  risk at a live table ("wait, the card or the role?").

Not yet simulated - bluffing behavior is hard to model meaningfully without
simulating the bluffing itself, which is a separate piece of work (see
BALANCE_TESTING.md Part 2, "what this doesn't cover"). `sim/human_sim.py`'s
trait framework makes this more tractable than when it was first deferred,
still real, unstarted work.

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

**Still open**: reveal timing (never, end of game, or a player-triggered
reveal), whether Raiders should also withhold Defense Pact support from
their target (not yet modeled), and whether the 14.9% success rate is the
right target or needs tuning once reveal timing and Power Cards are
layered in.

### 8.3 Declarations & Audits
Any claim (a trade offer, a tip, a statement of your own holdings, a Power
Card claim) can be audited by another player at a resource cost. Being
caught lying is penalized harder than a failed audit.

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

**Co-Founder: an even better fix, added after review pushed back.**
Picking a name to root for isn't actually an action, correctly called out
directly: "still they just sit in the game, it's not like they can do
anything." Fair. **Co-Founder** replaces backing as the preferred outcome:
a broke player can be recruited by a living player to actively co-run
their company. As co-founder, every remaining round, they redirect a real
slice of the host's fresh income toward Real Estate (a genuine, repeated,
risk-management decision, not a one-time label), and in exchange the host
gets a modest income bonus (+5% Company income) for having them aboard, a
real reason to want a co-founder, not a favor with nothing in it for
either side. One co-founder per host. Backing is now the fallback only for
whoever isn't recruited.
Simulation-validated: `AvgDeadRoundsPerPlayer` still drops to 0 at every
player count tested. Host recruitment is deliberately **random among
eligible hosts, not "richest available"**: an early version preferring the
richest host quietly fed the income bonus to whoever was already leading,
cutting Socialite's win rate from 85.9% to 75.5%, the same
snowball-reinforcing pattern this whole project kept finding elsewhere.
With random host selection, the cost is much smaller and honestly
reportable: 85.9% → 83.2%.

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
- ~~Power Cards' 7th card - still undecided~~ **resolved**: The Analyst is
  locked in (Section 8.1). Power Cards as a whole are still unsimulated.
- ~~Raider/Builder ratio and reveal timing~~ **ratio simulated**: roughly 1
  Raider per 5-6 players, 14.9% Raider success rate, no measurable effect
  on Builder balance (see Section 8.2). **Reveal timing is still open.**
- **Onboarding**: teaching Power (not just cash), the two phases, allies
  not being mandatory, and the final round being different - a lot to land
  in one sitting with a first-time group. Probably needs a guided first
  few rounds rather than a rules dump.
- **Round count and Building Phase length don't scale with player count.**
  `sim/human_sim.py`'s player-count sweep found the fixed 15-round
  structure is fine at 6 to 7 players but breaks down below that: at 3 to 4
  players the eventual winner is locked in by round 2 or 3 of 15, meaning
  most of a small-group game plays out as a foregone conclusion. Needs a
  player-count-scaled round count, not yet designed.
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
- **Defense Pact breakup has no defined cost.** Declaring or ending an
  alliance mid-game isn't addressed anywhere in Sections 6-7: can a player
  freely flip allegiance round to round with no consequence? Currently
  undefined. Proposed fix, not yet simulated: ending a covert pact is free
  (nobody knew anyway); ending a *declared* pact costs a reputation mark
  and takes effect starting the following round, not the same round,
  mirroring the JV reputation tax's 2-strike pattern.
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
- 5 to 7 players, one sitting, ~45–60 minutes. Not "up to 7": 3 to 4
  players is a structurally different, currently-broken game (Section 1).
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
