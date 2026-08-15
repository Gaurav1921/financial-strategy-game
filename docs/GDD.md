# [Working Title: "Consortium"] — Game Design Doc

## 1. Pitch
A web-based financial strategy game for a small group of friends (up to 7)
playing together in one sitting — start to finish in under an hour, like a
board game night, not a slow mobile game you check in on for weeks. Everyone
builds a company and grows their **Power** — a combined score built from
cash, real estate, stock positions, and captured rivals, not just a single
number. The biggest plays (taking over a rival) usually need allies to pull
off, some of your allies might secretly want you to fail, and every claim
anyone makes can be bluffed. Money, power, and trust are all live risks at
the same time.

## 2. Format: Live Mode first, Season Mode later
Originally designed as a slow, async, check-in-once-a-day "season" (2–3
weeks, matchmade with strangers) — that model doesn't fit the actual use
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
with that. Our differentiation is the financial-strategy layer underneath —
Power, multiple asset classes, real takeovers — which a narrative party
game won't have.

## 3. The core resource: Power
Not just net worth. **Power = Cash + Real Estate value + Stock holdings +
Captured value (from successful takeovers) − Debt (from loans) + a small
bonus per active alliance.** Two players with the same raw dollar total can
have very different Power depending on how diversified and allied they are
— this is deliberate: it's what makes "am I actually strong enough to
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
- **Final Round**: deliberately different (see Section 8.5) — the
  guaranteed climax where season-long trust either pays off or gets cashed
  in.

Simulation-tested: this structure measurably works (see BALANCE_TESTING.md
Part 2) — it doesn't fully solve the "one aggressive player snowballs
unopposed" risk on its own (Section 9 covers this honestly), but it clearly
helps.

## 5. The six ways to make money
Every round, you choose how to spread your money across six different
options — not just "grow one number." This is the actual financial-strategy
part of the game.

1. **Your Own Company** — the baseline. Generates income each round
   proportional to its size (10%/round). Growing it is always safe, if slow.
2. **Real Estate / Safe Assets** — lower income (5%/round) but this is
   *the* protected asset class: it counts far more toward your defense than
   cash does (see Section 6). The deliberate "safe harbor" choice.
3. **The Market** — buy a stake in *any* player's company. Believe in
   someone → profit if they grow. Think they're about to fall → bet against
   them instead. No partnership or consent needed, just a read on where
   things are headed.
4. **Loans** — borrow to invest bigger than your savings allow. Interest
   rises the more leveraged you get (not a flat rate — flat-rate loans were
   simulation-tested and turned out to be a risk-free exploit, see
   BALANCE_TESTING.md Part 2, Finding 2). Overleverage enough and you can go
   bankrupt: creditors seize ~85% of your holdings and the remaining debt is
   discharged — diminished but still in the game (see Section 8.4).
5. **Joint Ventures** — team up with an ally, pool money for a return
   neither gets solo, but they can drain it early and keep the majority
   (65/35 split, simulation-tested — see BALANCE_TESTING.md Part 1).
   Reputation has real teeth: two proven betrayals and you lose access to
   easy income and get worse terms on anything you still manage to form.
6. **Takeovers** — go after a rival's whole company (see Section 6).

## 6. Combat: attacking and defending
- **When can you attack?** Everyone's Power is visible. You can attempt a
  takeover any time in the Conflict Phase where your attack power (your
  liquid money, plus any allies backing you) exceeds the target's defense
  (their Real Estate + a portion of their cash + any allies defending them).
- **Do you need allies to attack?** Not always — **it's a Power
  comparison, not an ally requirement.** A rich-enough solo player can take
  on an allied group if their total Power genuinely exceeds the group's
  combined defense; allies are the easiest way to add power, not a
  mandatory gate. (This was a real gap in an earlier draft — corrected
  after being challenged on it directly.)
- **How do you defend?** Two ways: park money in Real Estate (which is
  built to actually protect you — simulation-tested, see Section 5.2/#2),
  or spend directly on security that round at the cost of growth. Allies
  can also rally to defend you, using the same "support" concept that lets
  people gang up to attack.
- **Defender's edge:** in a close fight, the defender wins (defense counts
  at a 1.05x bonus when compared) — borrowed from Risk's dice rules, where
  attacking only makes sense with a real edge, not just parity.
- **You can't see an attack coming that exact round** — everyone locks in
  moves secretly and they resolve together. What you *can* do is read the
  warning signs beforehand (who's rich and undefended, who's been forming
  alliances) and defend proactively.
- **Post-Attack Shield:** after being successfully taken over, you're
  immune to further takeovers for 2 rounds. Without this, simulation
  testing showed a single attacker will just repeatedly farm the same
  undefended victim for the rest of the game (see BALANCE_TESTING.md Part
  2, Finding 4) — exactly the "veterans farm new players" complaint our
  own market research flagged as the top churn cause in this genre.
- **Anyone can gang up on a runaway leader**, not just dedicated
  attackers — simulation-confirmed (BALANCE_TESTING.md Part 2, Finding 5):
  without this, one aggressive player wins unopposed every time; with it,
  the winning strategy flips to whoever's well-allied, and the top-two gap
  shrinks by 97%. This only works if relative Power is clearly visible to
  everyone at the table — that's a UI requirement, not just a rules one.
- **What happens if a takeover succeeds:** the attacker captures 25% of the
  target's liquid (cash + company) value. Real Estate is untouched — it's
  protected by design, not just by the defense math.

## 7. Defense Pacts — alliances that protect, not just profit
Beyond Joint Ventures (which are financial), you can form a **Defense
Pact**: a promise that if your partner is attacked, you help defend them.
Borrowed from Civilization's alliance mechanics. Gives alliances a
protective dimension, not just a money-making one.

## 8. Bluffing, hidden roles, and personal stakes

### 8.1 Power Cards — Coup's mechanic, reused for finance
Your colleague's idea, and it fits neatly on top of what's already
designed. Like Coup, each player secretly holds a Power Card granting one
special move or block; you can bluff about which one you have; anyone can
challenge your claim. **This reuses the existing Declare/Audit system**
rather than needing a whole new mechanic — claiming a Power Card *is* a
Declaration, challenging it *is* an Audit. Rough set of 7, one per possible
player:
- **The Financier** — bonus income / blocks someone else's basic income move
- **The Raider** — a direct hit on a rival's company, smaller than a full takeover
- **The Guardian** — blocks a Raider's attack
- **The Broker** — skims cash from a rival / blocks being skimmed from
- **The Banker** — better loan terms / blocks someone calling in a loan against you
- **The Insider** — peek at a hidden thing (a rival's holdings, a rumor's truth)
- one more — still open, see Section 9

Not yet simulated — bluffing behavior is hard to model meaningfully without
simulating the bluffing itself, which is a separate piece of work (see
BALANCE_TESTING.md Part 2, "what this doesn't cover").

### 8.2 Hidden Raider role
A minority of players are secretly **Raiders** — their win condition
requires certain companies to fail (activist short-sellers), invisible to
the majority **Builders** (standard Power-maximizing win condition). You're
never just wondering "will they choose greed" — you're wondering whether an
ally is even capable of staying loyal. Ratio and reveal timing still open
(Section 9).

### 8.3 Declarations & Audits
Any claim (a trade offer, a tip, a statement of your own holdings, a Power
Card claim) can be audited by another player at a resource cost. Being
caught lying is penalized harder than a failed audit.

### 8.4 Ghost/Observer status
A bankrupted or fully-taken-over company doesn't vanish. Its founder
becomes a **Board Observer**: limited residual influence (can leak one true
or false piece of information, gets a vote in the final round). Keeps
eliminated players engaged instead of just disengaging and quitting.

### 8.5 The Final Round
Deliberately different from the rest of the game. Game theory says rational
players defect in a known final round (the "shadow of the future"
disappears) — rather than fight that, the last round is an explicit
different phase (a final vote/tally) marketed as the climax. Confirmed in
the earlier Joint Venture simulation: the strongest honest strategy wasn't
"always honest," it was "honest all game, then take the expected defection
in the final round" — worth telling players outright rather than letting
them learn it the hard way.

### 8.6 Personal touch
Players name and customize their own company (name, logo/color). Cheap to
build, makes losses sting more and wins feel more like *yours* — especially
for a group of friends playing together.

## 9. Open risks (named honestly, not yet solved)
- **Power Cards' 7th card** — still undecided.
- **Raider/Builder ratio and reveal timing** — too early kills tension, too
  late feels unfair. Not yet simulated against the Power system.
- **Onboarding**: teaching Power (not just cash), the two phases, allies
  not being mandatory, and the final round being different — a lot to land
  in one sitting with a first-time group. Probably needs a guided first
  few rounds rather than a rules dump.

## 10. MVP Scope (Live Mode)

### In scope (v1)
- Up to 7 players, one sitting, ~45–60 minutes.
- Building Phase + Conflict Phase structure.
- All six money mechanics (Company, Real Estate, Market, Loans, Joint
  Ventures, Takeovers) — simulation-tested numbers from Section 5/6.
- Defense Pacts, Post-Attack Shield, Ghost/Observer status.
- Hidden Raider/Builder split (simplest version: fixed ratio).
- Company naming/customization.
- Final Round as a distinct phase.
- A clearly visible relative-Power display (e.g. a live leaderboard) —
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
  connected players in the same room — WebSockets (FastAPI supports these
  natively), not a scheduled daily job. This is a meaningful shift from the
  original async/Season architecture and should be designed in from the
  start rather than retrofitted.
- **Round resolution logic** (Power calculation, takeover resolution, JV
  payouts) is the most important code in the game and should be
  unit-testable independent of the API/WebSocket layer — the simulations
  in `sim/` already validate this logic in Python, so the resolution
  engine can reuse the same language and much of the same logic tested
  there.
- No database-heavy persistence needed for MVP (a game lives and dies
  within one room's session) — simplifies the backend considerably
  compared to the original Season Mode plan.

## 12. Monetization (placeholder, unchanged in principle)
- Likely "one person unlocks the game, friends join free" (Jackbox-style)
  rather than per-player purchases — fits a friend-group one-sitting game
  much better than trying to monetize each participant individually.
- No pay-to-win: Takeovers, Joint Ventures, and Power Cards only stay
  meaningful if outcomes can't be bought.
