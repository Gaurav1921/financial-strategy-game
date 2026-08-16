# Gameplay Guide (Live Mode, up to 7 players)

This is the practical companion to `GDD.md`. The GDD explains *why* each
mechanic exists and how it was validated; this doc explains what a player
actually sees and does, round by round, starting from Round 1 with a full
table of 7. Numbers here match the simulation constants in
`sim/power_simulation.py`, the source of truth for anything not yet built
in `backend/`.

## 1. Setup

Every player starts identical. No classes, no asymmetric starting kits.

| Resource | Starting value |
|---|---|
| Cash | 20 |
| Company value | 80 |
| Real Estate | 0 |
| Stock positions | none |
| Debt | 0 |
| **Total Power** | **100** |

The only hidden asymmetry is the **Builder / Raider split** (Section 8.2):
a minority of the table are secretly Raiders. Everyone still starts with
the same 100 Power; the split only affects what counts as a personal win
later, not Round 1 resources or options.

The game runs **15 rounds**:
- **Rounds 1-5: Building Phase.** No takeovers. Every other option is open.
- **Rounds 6-14: Conflict Phase.** Takeovers unlock.
- **Round 15: Final Round.** Distinct rules, see Section 7.

## 2. The round loop

Every round, every player does the same four steps, and everyone's moves
lock in secretly, then resolve together. You never see an attack coming
in the same round it happens.

1. **Income** - your existing assets pay out: Company at 10%/round, Real
   Estate at 5%/round, any stock positions at 8%/round (diluted, tracks
   the target's growth). This happens automatically, no decision needed.
2. **Allocate** - decide what to do with the cash you now have on hand.
   This is the real decision point each round (Section 3).
3. **Joint Venture resolution** - any JV you're in either holds (compounds
   further) or gets drained, by you or your partner.
4. **Takeovers** - Conflict Phase only. Declare an attack, or don't.

Everyone locks in moves before anything resolves. Plan defensively based
on what you can already see (who's rich and undefended, who's been
allying), not on what happens this round.

## 3. Your options, every round

These six are always available except where noted. You split your cash
across as many of these as you want each round; nothing forces an
all-in choice.

### Grow Your Own Company
Reinvest into your own company. 10%/round, no risk, always available.
This is the baseline everyone can fall back on.

### Real Estate (the safe asset)
Buy in at a ~3% closing cost. Real Estate pays a lower 5%/round, but it
is the one asset that **cannot be touched by a takeover** and counts far
more toward your defense than cash does. Liquidating it back to cash
costs a 15% haircut, so it's a real commitment both ways, not a free
parking spot.

Use it to bank a defensive floor, or as an emergency valve if you're
short on cash. Both directions cost you something on purpose.

### The Market (stocks)
Take a long or short position in *any* other player's company. No
partnership or consent needed. Long if you think they're building well,
short if you think they're about to get taken over or overleveraged.
Positions pay out at 8%/round, tracking the target's actual growth.

### Loans
Borrow from **the Bank**, a finite shared pool (100 capital per seat at
the table, so 700 total at 7 players). Base interest is 8%/round, plus a
risk premium of 35% per unit of leverage, so the more you borrow relative
to your total Power, the worse your rate gets. Overleverage and you can
go **bankrupt**: creditors seize 85% of your holdings, the remaining debt
is discharged, and you stay in the game diminished rather than out
entirely.

The Bank is shared. If several players lean on credit in the same
stretch of rounds, later borrowers get worse terms or get shut out. Watch
what the table is doing, not just your own balance.

### Joint Ventures (JVs)
Pool cash with one ally (two allies max) for a return neither of you
would get solo, at 12%/round while both sides hold. Either side can drain
it early and keep 65% of the pot, leaving the other 35%. Two proven
drains and you lose access to easy JV/idle income and get worse terms on
anything you still manage to form, publicly, so reputation is visible to
the whole table.

A JV slot and a Defense Pact (Section 5) share the same relationship: an
ally covers both at once, and the two-ally cap applies to the combined
relationship, not to JVs and Pacts separately.

### Takeovers
Attempt to take a rival's whole company. **Only available in the
Conflict Phase (Round 6 onward).** See Section 6.

## 4. Round 1, concretely (7 players)

Nobody has takeovers available yet, so a first round is purely economic.
A typical player, starting from 20 cash / 80 company / 100 Power, is
choosing among:

- Reinvest all 20 into the company (safe, slow, no exposure).
- Split it: some into the company, some into Real Estate to start
  building a defensive floor early, before anyone needs one.
- Take a small stock position in a player you expect to grow fast.
- Approach another player to form a Joint Venture, pooling cash for a
  better combined return than either gets solo.
- Borrow from the Bank to invest bigger than 20 cash allows, accepting a
  worse rate the more leveraged you get.
- Do nothing financially aggressive and instead start quietly signaling
  or forming a Defense Pact (Section 5) for later, since alliances can
  form from Round 1 even though attacks can't happen yet.

There's no wrong opening move: the Building Phase exists specifically so
nobody can be punished for a slow start. What matters in Round 1 is
starting to read the table (who's aggressive, who's cautious, who's
allying with whom) before the Conflict Phase makes that information
actionable.

## 5. Building your defense

Two players with the same raw dollar total can have very different
Power, and the same is true of defense. Your defense number is:

**Real Estate + a portion of cash + any allies actively defending you.**

Ways to build it:
- **Park money in Real Estate.** The single most effective defensive
  move: it's protected from capture entirely and weighted heavily in the
  defense calculation.
- **Spend directly on security that round**, at the cost of growth that
  round. A short-term option when you see a threat coming.
- **Form a Defense Pact.** A promise that if you're attacked, your
  partner helps defend you. Two flavors:
  - **Declared**: public. Visibly adds to your defense number and
    deters attackers, but everyone at the table now knows you're allied.
  - **Covert**: off the record. Doesn't count toward your visible
    defense (so it can spring a surprise on an attacker who thought the
    fight looked winnable), but if it's ever audited and found empty,
    that's penalized harder than a normal failed audit.
- **Defender's edge**: in a close fight, you win ties. Defense counts at
  a 1.05x bonus when compared against an attacker's power, so attacking
  only makes sense with a real edge, not just parity.

Ending a Pact: a covert one costs nothing to walk away from. A declared
one costs a reputation mark and only takes effect starting *next* round,
so you can't publicly declare a pact to inflate your defense for one
attack and un-declare it the instant that attack resolves.

## 6. Attacking (Conflict Phase, Round 6 onward)

You can attempt a takeover on any player whose defense your attack power
(your liquid cash, plus any allies backing you) exceeds. It is a **Power
comparison, not an ally requirement**: a rich enough solo player can take
on an allied group if their total genuinely exceeds the group's combined
defense. Allies are the easiest way to add power, not a mandatory gate.

- **On success**: you capture 25% of the target's liquid (cash +
  company) value. Their Real Estate is completely untouched.
- **On failure**: you lose 50% of what you committed to the attack. This
  is a real cost, not a free roll, so declaring an attack you can't back
  up is a genuine risk.
- **Post-Attack Shield**: a player who was just successfully taken over
  is immune to further takeovers for 2 rounds. You can't just keep
  farming the same victim.
- **Anyone can gang up on a runaway leader**, not just dedicated
  attackers. Everyone's Power is visible on a live leaderboard specifically
  so the table can see who's pulling ahead and coordinate against them
  before one player snowballs unopposed.

## 7. The Final Round (Round 15)

Deliberately different from every round before it. Rational play in a
known final round means allies who were holding Joint Ventures honestly
all game have a real incentive to drain rather than hold, since there's
no next round to protect a reputation for. Expect it, don't be surprised
by it: the strongest honest strategy across the whole game isn't "always
honest," it's "honest all game, then take the expected defection in the
final round."

If a player has already been fully taken over or gone bankrupt earlier in
the game, they don't just leave: they become a **Board Observer** with
one choice, picking a living player to **back**. That backing is purely
social (no cash or Power changes hands), but it's what a Board Observer's
final-round vote is for: if the top two players finish within a hair of
each other, whichever one had more Board Observers backing them wins the
tie.

## 8. Putting it together: building wealth vs. building defense

There's no single correct split. The six options trade off against each
other on the same axis every round:

- **Company and Market** grow your Power fastest but leave you exposed
  (cash and company value both count toward what an attacker can
  capture).
- **Real Estate** grows slower but is the only thing a takeover can never
  touch, and it's what actually keeps you safe once the Conflict Phase
  opens.
- **Loans** let you do more of either, at the cost of interest that gets
  worse the more you lean on it, and real bankruptcy risk if you
  overextend.
- **Joint Ventures** boost your return past what you could get solo, but
  hand your partner a real chance to drain the pot and keep the majority.

A player who stays 100% liquid in Company and Market grows the fastest on
paper but is the easiest target the moment the Conflict Phase opens. A
player who moves heavily into Real Estate early is safe but grows slower
and has less capital to attack with later. Reading which posture fits a
given round, based on what phase you're in and what the table looks like,
is the actual game.
