# Gameplay Guide (Live Mode, 3 to 10 players)

This is the practical companion to `GDD.md`. The GDD explains *why* each
mechanic exists and how it was validated; this doc explains what a player
actually sees and does, round by round, starting from Round 1. Numbers
here match the current simulation constants in `sim/human_sim.py` and
`sim/power_simulation.py`, the source of truth for anything not yet built
in `backend/`. The game's working title is **Hostile Ledger**.

**Player count: 3 to 10.** An earlier version of this game excluded 3-4
players entirely, based on a test that turned out to be measuring a biased
archetype sample as much as the player count itself (BALANCE_TESTING.md
Part 17). With that fixed, 3-4 read comparably to every other supported
count. Four new archetypes let 9-10 read clean too (Part 22).

## 1. Setup

Every player starts identical. No classes, no asymmetric starting kits.

| Resource | Starting value |
|---|---|
| Cash | 20 |
| Company value | 80 |
| Real Estate | 0 |
| Gold | 0 |
| Market (Industry) positions | none |
| Debt | 0 |
| **Total Power** | **100** |

Every player also picks a **company name, an icon, and one Industry**
(Section 3) as part of setup, alongside the starting resources above.

The only hidden asymmetry is the **Builder / Raider split** (Section 8):
a minority of the table are secretly Raiders. Everyone still starts with
the same 100 Power; the split only affects what counts as a personal win
later, not Round 1 resources or options.

The game runs **15 rounds**, split into three parts:
- **Building Phase**: no hostile bids. Every other option is open. **Its
  length is 4 to 6 rounds and is rolled secretly at the start of the
  game, never announced.** You genuinely don't know, round to round,
  whether attacks are about to unlock. This is deliberate: a fixed,
  known length turns the whole opening into a memorizable formula ("max
  Company until round N, then pivot to defense"), and a repeat player
  solves that once and never has to think about it again. Hiding the
  length forces you to read the table's actual warning signs instead.
- **Conflict Phase**: the rest of the game up to round 15. Hostile Bids
  unlock the round after the Building Phase ends.
- **Round 15, the Final Round**: deliberately different rules. See
  Section 7.

## 2. The round loop

Every round runs the same eight steps, Building or Conflict, and
everyone's moves lock in secretly before anything resolves. You never
see an attack coming in the same round it happens.

1. **Income** - Company, Real Estate, Gold, and any Market positions pay
   out based on what you held *last* round. Automatic, no decision needed.
2. **Allocate** - everyone secretly decides where this round's income
   goes: Company, Real Estate, Gold, the Market, a Bank deposit, paying
   down a loan, or just holding cash. The core simultaneous decision,
   every round.
3. **Alliances** - propose or accept new Joint Ventures; existing ones
   resolve (hold, top up, or get drained).
4. **Loans** - borrow if you want to, Bank capacity permitting; any
   outstanding peer-to-peer loans between allies settle.
5. **Combat** (Conflict Phase only, skipped entirely during the Building
   Phase) - hostile bids and "gang up on the leader" counter-attacks
   resolve.
6. **The Market re-prices** - Industry positions revalue against that
   round's scenario, including the knock-on effect of a hostile bid that
   just landed.
7. **Taxes and upkeep** - if enabled at your table: income tax on
   everything earned this round combined, Real Estate liquidation if
   anyone chose it, erosion on idle cash.
8. Round ends, move to the next.

Plan defensively based on what you can already see (Section 6 covers
exactly what that is), not on what happens this round.

## 3. Industries and the Market

The Market isn't a bet against a specific rival. Every player's company
belongs to one of ten fixed **Industries**: Healthcare, Technology,
Pharma, Energy, Financial Services, Consumer Retail, Agriculture,
Manufacturing, Media & Entertainment, and Property. ("Property," not
"Real Estate": Real Estate is the separate defensive asset class below,
same name would be confusing at the table.) With 3 to 10 players and 10
industries, most industries have zero or one player in them. That's
fine, industries aren't scarce.

**Every round, one scenario is drawn** and read out to the whole table as
plain text, for example "A major regional conflict breaks out" or "A
recession is officially declared." Each scenario has a logical,
readable effect on a handful of industries (never all ten), and leaves
the rest flat. This is real financial-literacy skill, not a dice roll:
you can reason about "a recession hurts Consumer Retail," and it's
genuinely unpredictable round to round, so it can't be memorized.
Twenty-four example scenarios exist today; more can be added without
touching the mechanic.

**What a scenario actually pays out is never a fixed number.** The
scenario text tells you the *direction and rough strength* (a strong move
or a mild one, up or down), and the *exact size* is rolled fresh every
time that scenario lands:
- A strong move (`++` / `--`): 4% to 20% in that direction.
- A mild move (`+` / `-`): 1% to 8% in that direction.

If your company's Industry is hit that round, your Company income moves
by that roll on top of its normal growth. You can also put money
directly into the Market: a long or short position in any Industry
(including your own), paying out on that same roll. Real Estate feels
the Property roll too, but only at half strength. Unaffected industries
just stay flat.

### Gold
A separate asset class, not tied to any Industry. Gold is a
flight-to-safety hedge: it drifts around a low 0.5% to 3.5% in an
ordinary round (a value-preserver, not a growth engine), gets a real
kicker during crisis-flavored scenarios (war, recession, a financial
shock), and pulls slightly negative during genuinely upbeat scenarios,
money chasing growth assets instead. Not a way to grow fast; a way to
lose less when everything else is losing.

## 4. Your options, every round

### Grow Your Own Company
Reinvest into your own company. 10%/round base, plus or minus whatever
your Industry rolled this round (0 if your Industry wasn't affected).
Always available, the baseline everyone can fall back on, but no longer
guaranteed-positive: a bad roll in your own Industry can make a round's
Company income negative.

### Real Estate (the defense-weighted asset)
Buy in at a 3% closing cost. Real Estate pays roughly 5%/round, adjusted
by half of whatever that round's Property scenario rolled. It's still
the asset that counts far more toward your **defense** than cash does
(Section 6), the deliberate safe-harbor choice, **but it is no longer
100% untouchable** if a hostile bid actually lands against you (see
Section 6's capture cascade). Liquidating it back to cash, on your own
terms, any time, costs a 15% haircut.

### Gold
Buy in with spare cash any round. Counts toward your **defense** too
(0.6x per unit, between cash's 0.3x and Real Estate's 0.9x), a real, if
smaller, defensive credit for a safe-haven asset, though not toward
attack power the way cash is. Also exists to smooth out your returns
across good and bad scenario rounds.

### The Market (Industry positions)
Take a long or short position in any of the ten Industries. Pays out on
that Industry's rolled scenario delta each round, same number that moves
Company income and Joint Ventures in that Industry. No guaranteed rate,
full exposure both directions.

### Loans
Borrow from **the Bank**, a finite shared pool (100 capital per seat, so
500 to 700 total depending on table size). Base interest is 8%/round
plus a 35%-per-unit-of-leverage risk premium, so the more you borrow
relative to your total wealth, the worse your rate gets. The Bank is
shared: if several players lean on credit in the same stretch, later
borrowers get worse terms or get shut out entirely.

**Peer-to-peer loans** are also possible: another player lends you cash
directly at a flat 20%/round, well above the Bank's typical 8-20%, real
compensation for the real risk they're taking on you as a counterparty.

Overleverage either way and you can go **bankrupt**: creditors seize 85%
of everything you have (Cash, Company, Real Estate, Gold, Market and JV
positions), the remaining 15% and your debt are both discharged. You
stay in the game, diminished, not eliminated.

**The Bank also pays interest on deposits.** Park cash above a small
working-cash floor (10) with the Bank and earn a flat, safe 4%/round,
deliberately below every active option. It beats letting cash sit idle
without ever being smarter than actually investing.

### Joint Ventures (JVs)
Team up with one ally (two allies max) on a **shared position in one
Industry**. It is not a separate bet with its own guaranteed rate: the
pot moves with that Industry's real scenario delta every round, exactly
the number that moves a solo Market position in the same Industry. A
JV's *expected* return is identical to just investing in that Industry
solo. What forming one actually buys you is scale (pooling more than
either partner could bet alone) and real betrayal risk.

**How it works, concretely:**
- Each partner seeds the pot with 10. It opens at 20.
- The pot persists and compounds across rounds; it doesn't reset every
  round. Either partner can top it up later, an amount equal to 20% of
  whichever partner currently has less cash (floored at the original 10,
  skipped if it would leave that partner below 15 spare cash).
- Each round, the pot moves with the assigned Industry's rolled delta,
  same as any Market position.
- Either partner can **drain** it at any time instead of letting it
  ride: the drainer keeps 65% of the current pot, the other partner gets
  35%. If both partners drain the same round, it's a smaller 40/40 split
  (20% lost to friction). If neither drains, nothing pays out and the
  pot just carries forward.
- **A drain is public.** Everyone at the table sees the pot move from the
  shared position into the drainer's own cash. There's no hidden
  reputation score to track, players simply remember. A **second**
  proven betrayal, across any of a player's JVs, costs them directly and
  visibly: an immediate ~15% hit to their own current total Power,
  docked the instant it's confirmed.

A JV partnership and a Defense Pact (Section 5) currently share the same
relationship: allying with someone covers both at once, and the two-ally
cap applies to that combined relationship, not to each separately.

### Hostile Bids
Attempt to capture a real share of a rival's wealth, not their whole
company, they keep it and come back behind a shield. **Only available
once the Building Phase ends** (round 5 to 7, depending on that game's
hidden roll). See Section 6.

## 5. Round 1, concretely

Nobody has hostile bids available yet (and won't for at least 4 more
rounds, though exactly how many is hidden), so early rounds are purely
economic. A typical player, starting from 20 cash / 80 company / 100
Power in their assigned Industry, is choosing among:

- Reinvest into the company, accepting whatever that round's scenario
  does to their Industry along with it.
- Split it: some into the company, some into Real Estate, to start
  building a defensive floor early, before anyone needs one, at a 3%
  buy-in cost.
- Take a small Market position in an Industry they read as likely to do
  well, based on that round's scenario text.
- Approach another player to form a Joint Venture in a shared Industry,
  pooling cash for a bigger combined bet than either gets solo.
- Borrow from the Bank, or deposit spare cash with it for a safe 4%,
  instead of letting it sit idle.
- Put a small amount into Gold as a hedge against a bad scenario roll
  later.
- Do nothing financially aggressive and instead start quietly forming a
  Defense Pact (Section 5) for later, since alliances can form well
  before attacks are possible.

There's no wrong opening move: the Building Phase exists specifically so
nobody can be punished for a slow start, and its hidden length means
there's no fixed round where "switch to defense now" is the objectively
correct move either. What matters early is reading the table (who's
aggressive, who's cautious, who's allying with whom, which scenarios have
landed so far) before the Conflict Phase makes that information
actionable.

## 6. What you can actually see, and combat

**Only Power is shown, exactly, always, for every player.** Nothing
else is visible by default: cash, Company value, Real Estate, Gold,
Market positions, debt, and exact attack or defense capability are all
genuinely unknown unless someone chooses to reveal them.

- **Declarations** let a player claim something about their *own*
  position (you can't declare things about someone else) to deter or
  bluff.
- **Any player can Audit any Declaration**, not just whoever it directly
  threatens, at a resource cost, revealing the truth. Being caught lying
  is penalized harder than a failed Audit.
- **Declared Defense Pacts** are the one exception that's automatically
  public, since the deterrent only works if it's visible. Covert ones
  stay hidden until a fight actually happens.

So "who's rich and undefended" is a real question you spend a resource
to answer, not a leaderboard lookup.

**Attack power is your cash only** (a portion of it), plus any allies
backing you. Company, Real Estate, and Market positions grow your Power
but don't arm you; only liquid cash does.

**Defense is Real Estate (heavily weighted) plus a portion of your cash**,
plus any allies defending you. Company and Market positions don't count
toward defense either.

- **When can you attack?** Once the Conflict Phase opens, any time your
  attack power exceeds a target's defense, both the derived values
  above, not a raw Power comparison.
- **Do you need allies to attack?** Not always. It's an attack-power vs.
  defense comparison, not an ally requirement. A player holding enough
  liquid cash solo can beat an allied group's combined defense if the
  numbers genuinely support it.
- **Defender's edge**: in a close fight, the defender wins ties. Defense
  counts at a 1.05x bonus when compared, so attacking only makes sense
  with a real edge, not just parity.
- **You can't see an attack coming that exact round.** Everyone locks in
  moves secretly and they resolve together. Read the warning signs ahead
  of time instead: who's rich and undefended, who's been forming
  alliances.

**On a successful hostile bid**, the attacker captures 25% of the target's
**total wealth**, not just liquid cash. The target pays cash first, then
Company, then Real Estate (at the standard 15% liquidation haircut) if
the rest isn't enough to cover it. Real Estate is still your best
defense, it still counts far more than cash toward whether an attack
succeeds in the first place, but it's no longer fully immune to what
happens *after* an attack lands.

**On a failed attack**, the attacker still loses 50% of what they
committed. That loss doesn't just vanish: half goes to the defender who
successfully protected themselves, a real reward for defending; half
goes to the Bank.

**Post-Attack Shield**: a player who was just successfully taken over is
immune to further hostile bids for 2 rounds. Nobody can just keep farming
the same undefended victim.

**Anyone can gang up on a runaway leader**, not just dedicated
attackers. Any player whose total Power exceeds 1.05x the second-place
player's becomes a valid counter-attack target for the whole table, and
since only Power is visible by default, spotting this requires everyone
to actually be watching the leaderboard.

## 7. Defense Pacts and the Final Round

Beyond Joint Ventures (financial), you can form a **Defense Pact**: a
promise that if your partner is attacked, you help defend them.

- **Declared**: public. Visibly adds to your partner's defense number, a
  real deterrent, but everyone now knows you're allied.
- **Covert**: off the record. Doesn't count toward your partner's
  visible defense, so an attacker can be lured into a fight that looks
  winnable and isn't, but if it's ever audited and found empty, that's
  penalized harder than a normal failed Audit.

Either side can walk away from a Defense Pact whenever they want. Ending
a covert one costs nothing, nobody outside it knew it existed. Ending a
declared one costs you the same kind of real, visible Power hit a second
proven JV betrayal does, and takes effect starting the *next* round, not
immediately, so a pact can't be declared to inflate a defense number for
one attack and un-declared the instant that attack resolves.

**Round 15, the Final Round, is deliberately different.** Rational play
in a known final round means allies holding Joint Ventures honestly all
game have a real incentive to drain rather than hold, since there's no
next round left to protect a reputation for. Expect it: the strongest
honest strategy across the whole game isn't "always honest," it's
"honest all game, then take the expected defection in the final round."

If a player has already been fully taken over or gone bankrupt earlier,
they don't just leave. A living player can recruit them as a
**Co-Founder**: every remaining round, the co-founder redirects a real
slice of the host's cash toward Real Estate, and in exchange earns a
real, growing equity stake (7% of the host's Company, marked to its
current value every round) that counts toward their own standing. The
host can later buy the co-founder out entirely for cash, freeing them to
rebuild or be recruited elsewhere. If the host instead gets taken over,
the co-founder gets a golden parachute: 20% of whatever the attacker
captured, paid straight to their own cash. Whoever isn't recruited falls
back to simply **backing** a living player, a purely social pick with no
cash or Power attached, but it's what their final-round vote is for: if
the top two players finish within a hair of each other, whichever one
had more backers wins the tie.

## 8. The Hidden Raider

A minority of the table (roughly 1 in every 5 to 6 players) are secretly
**Raiders**, invisible to the majority **Builders**. A Raider's win
condition is tied to a secretly assigned target ending the game
bankrupt or below half the table's average Power, not to their own
Power being highest. They pursue it two ways: preferring their assigned
target when choosing who to attack, and, if allied with that target via
a Joint Venture, draining it far more often than an ordinary betrayal
would. You're never just wondering whether an ally will choose greed,
you're wondering whether they're even capable of staying loyal to you at
all. Reveal timing (never, end of game, or player-triggered) is still
undecided.

## 9. Putting it together: building wealth vs. building defense

There's no single correct split. The options trade off against each
other on the same axis every round:

- **Company and Market** grow your Power fastest but leave you exposed:
  cash and Company value both count toward what an attacker can
  capture, and both swing with that round's scenario.
- **Real Estate** grows slower and isn't free to buy or sell, but it's
  the asset that actually keeps you hard to beat, weighted heavily in
  defense, even though it's no longer fully untouchable if an attack
  does land.
- **Gold** doesn't grow fast either direction; it exists to flatten out
  the swings a bad scenario roll can cause elsewhere.
- **Loans** let you do more of any of the above, at a cost that gets
  worse the more you lean on it, and real bankruptcy risk if you
  overextend. A Bank deposit is the flat, safe alternative to letting
  cash sit idle.
- **Joint Ventures** let you bet bigger in an Industry than you could
  solo, at the cost of a real, visible betrayal risk from your partner.

A player who stays fully liquid in Company and the Market grows fastest
on paper but is the easiest target once the Conflict Phase opens, and
the most exposed to a bad scenario roll. A player who moves heavily into
Real Estate and Gold early is harder to beat but grows slower and has
less capital to attack with later. Reading which posture fits a given
round, based on what phase you're in, what's just been revealed about
the table, and which scenario just landed, is the actual game.
