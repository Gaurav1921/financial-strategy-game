# [Working Title: "Consortium"] — Game Design Doc

## 1. Pitch
A web-based strategy game where you build a company inside a small, closed
pod of real rivals (6–10 players). The biggest plays in the game — hostile
takeovers, cornering a market — are **mathematically impossible to pull off
alone**, so alliances aren't optional flavor, they're required to be
ambitious. But some of the players you need are secretly incentivized to
see you fail, alliances involve real pooled assets that can be drained, and
every claim anyone makes can be bluffed. You find out who was lying when it's
already too late to matter.

## 2. Why This Version Instead of v2 ("informal alliances, betrayal always
possible")
The earlier draft said alliances "can be broken any time" but gave no
mechanical reason to ally in the first place — if betrayal is free and
available at will, the rational move in a one-shot trust decision is never
to cooperate, and the whole system collapses into "nobody trusts anybody,"
which is boring, not tense. Games that actually get betrayal right
(Diplomacy, EVE Online, Secret Hitler/Avalon, Sheriff of Nottingham, Blood
on the Clocktower) all make **cooperation mechanically necessary** and
**betrayal mechanically costly** — not just narratively costly. This
version borrows the specific mechanisms that do that (see Section 4),
recombined around a finance/business theme rather than copied wholesale
from any one of them.

**Competitive note:** Fusebox Games is shipping an officially licensed
*The Traitors* mobile app in 2026 (hidden traitors, roundtable banishment,
TV IP). If our game leans purely on "hidden traitor + vote people off" we
compete directly with a licensed, marketed product. Our differentiation has
to be the economic/build layer underneath the social-deduction layer —
joint ventures, market plays, combined-power moves — which a narrative party
game like that won't have.

## 3. Core Loop (per round, e.g. daily)
1. **Review** — see what happened last round: market moves, audit results,
   who proposed/broke a joint venture, any exposed lies.
2. **Plan** — secretly choose actions:
   - **Invest** — grow your own company (safe, baseline play).
   - **Propose a Syndicate Move** — a big play (hostile takeover, cornering
     a resource) that only resolves if enough *other* players commit
     support to it this round too (see 4.1). You need people, not just
     money.
   - **Form/Contribute to a Joint Venture** — pool real assets with allies
     into a shared pot that pays out more than solo investment, but any
     party with access can drain it early (see 4.2).
   - **Declare** — state something as fact (a trade offer, a tip, a claim
     about your own position). Others may **Audit** it at a cost (see 4.4).
   - **Defend** — reduce your exposure to takeovers/audits this round, at
     the cost of growth.
3. **Lock in** — all players submit in secret within the round window.
4. **Resolve** — actions play out together; results (including who
   supported whom, who drained a joint venture, who got caught lying) are
   revealed to the pod.
5. **Repeat** for most of the season; the season's final round is a
   deliberately different, high-stakes phase (see 4.6).

## 4. What Makes Alliances Real (the mechanical answers)

### 4.1 Syndicate Moves — cooperation is mandatory, not optional
Modeled on Diplomacy's support-order math: a takeover or market-cornering
attempt's success is a function of the initiator's stake **plus the number
of other players who committed support to it this round**. Below a
threshold, it simply fails — no amount of solo investment substitutes for
having allies. This is the mechanical reason you need people, independent
of whether you trust them.

### 4.2 Joint Ventures — trust becomes a real, drainable stake
Modeled on EVE Online's alliance treasuries. Two or more players can form a
Joint Venture: assets contributed compound into a return neither could get
solo. But anyone with standing access can withdraw early, taking a bonus
cut and leaving partners with the loss — a real, quantified betrayal, not a
reputation label. The bigger and longer a Joint Venture runs, the more
there is to protect *and* the more there is to steal — mirroring why EVE's
biggest betrayals only happen after years of real trust-building.

**Numbers (simulation-tested, see BALANCE_TESTING.md):** a drainer keeps
**65%** of the current pot, the partner gets the remaining 35%; a held JV
compounds at **12% per round**. At those settings, patient/honest play
consistently beats blind draining across a full season — but only *with*
the reputation tax below. Without it, blind backstabbing wins outright at
these numbers, so the tax isn't optional flavor, it's load-bearing:

**Reputation tax:** once a player has been caught draining **2 or more
times** (public, matches the pod-visible reputation already in the design),
they lose access to easy/idle income, and any JV they still manage to form
runs at a **5-percentage-point reduced growth rate** (partners who deal
with a known offender anyway protect themselves by under-investing). This
is what actually makes reputation cost something, rather than just being a
label players can shrug off.

### 4.3 Hidden Roles — some allies structurally can't stay loyal
Modeled on Secret Hitler/Avalon. A minority of players are secretly
**Raiders** (their win condition requires certain companies to fail —
think activist short-sellers), invisible to the majority **Builders**
(standard growth win condition). You're never just wondering "will they
choose greed" — you're wondering whether an ally is even capable of staying
loyal to you, which is a sharper, more anxious uncertainty than flat
"anyone might betray anytime."

### 4.4 Declarations & Audits — moment-to-moment bluffing texture
Modeled on Sheriff of Nottingham's declare/inspect loop. Any claim (a trade
offer, a tip about the market, a statement of your own holdings) can be
audited by another player at a resource cost. Being caught lying is
penalized harder than a failed audit, so both bluffing and accusing carry
real risk — this is what gives the game constant texture between the big
Syndicate Moves and Joint Venture betrayals.

### 4.5 Ghost/Observer status — eliminated players stay engaged
Modeled on Blood on the Clocktower's "ghost" mechanic. A bankrupted company
doesn't vanish — its founder becomes a **Board Observer** with limited
residual influence (can leak one true or false piece of information, gets
a vote in the season finale). Fixes social deduction's classic "eliminated
players disengage and quit" problem.

### 4.6 The Final Round — designed-for defection, not fought
Game theory is clear that rational players defect in a known final round of
a repeated Prisoner's Dilemma (the "shadow of the future" disappears).
Rather than fight that, the season's last round is an explicit different
phase — a final Syndicate vote/tally (Diplomacy-style final count, Traitors-
style roundtable) — marketed as the climax where all season-long trust
either pays off or gets cashed in. Mid-season cooperation is sustained by
*not* telling players exactly how long the shadow of the future is (season
length has some variance) until the final-round trigger fires.

**Confirmed in simulation:** the strongest-performing honest strategy in
testing wasn't "always honest" — it was "honest all season, then take the
expected defection in the final round." That gap was consistent enough
that onboarding should say the final round works differently outright,
rather than let players learn it the hard way and feel cheated the first
time (see BALANCE_TESTING.md, Finding 3).

## 5. MVP Scope

### In scope (v1)
- Pods of 6–8 players, matched by a simple skill/activity bracket.
- Core actions: Invest, Defend, Declare/Audit, and **one** Syndicate Move
  type (the takeover) — prove the combined-power mechanic before adding
  market-cornering.
- Joint Ventures with real pooled assets and early-withdrawal betrayal.
- Hidden Raider/Builder role split (simplest version: fixed ratio, revealed
  only at bankruptcy or season end).
- Ghost/Observer status on bankruptcy instead of full elimination.
- Season structure ending in a designed final round; leaderboard across
  seasons.

### Deferred to v2+
- Second Syndicate Move type (market cornering).
- Rumor/misinformation broadcast layer (a prediction-market-style "is this
  true" mechanic where the pod collectively prices claims) — interesting
  but adds real tuning complexity, build after the core loop is proven.
- Multiple industries, cosmetics, deeper economy, monetization systems.

This is a bigger build than the v2 draft — the payoff is that "why ally"
now has a real answer instead of an assumption. Small pods (6–8) and daily
async rounds keep the server logic within solo-dev reach.

## 6. Platform & Tech
- **Target platform:** web (browser-based), not a native mobile app —
  pivoted away from the earlier Flutter/Android plan because the mobile
  toolchain (Android Studio, SDK licensing, emulator setup) was a lot of
  install/ops overhead for a solo first project with no clear payoff yet.
  A web build removes the app-store gatekeeping entirely and ships to
  anyone with a browser; a mobile wrapper (PWA, or Capacitor around the
  same frontend) stays possible later without a rewrite if Play Store
  distribution still matters down the line.
- **Client:** React + Vite (already scaffolded in `frontend/`).
- **Backend:** Python + FastAPI (already scaffolded in `backend/`, currently
  just a `/health` stub). Round resolution (Syndicate Move thresholds,
  Joint Venture payouts, audit results) is the most important code in the
  game and should be unit-testable independent of the API layer — the
  balance-testing simulation in `sim/` already models this logic in Python,
  so the resolution engine can share the same language and largely the same
  logic as what's already validated there.
- **Data/rounds:** needs a persistence layer (players, pods, JV state) and
  a scheduled job for round resolution — a lightweight database
  (SQLite to start, Postgres if/when it needs to scale) plus a simple
  scheduler is enough for the MVP; no need for Firebase now that there's a
  real backend instead of a serverless-only plan.

## 7. Monetization (placeholder)
- Cosmetic-only (company branding, round-result flair) — Syndicate Moves,
  Joint Ventures, and audits only stay meaningful if outcomes can't be
  bought. This is also a deliberate contrast with the genre's
  pay-to-win reputation (Evony, etc. — see MARKET_RESEARCH.md).

## 8. Open Questions
- ~~Exact Joint Venture drain math~~ — **resolved via simulation**: 65%
  drain bonus, 12%/round growth, 2-strike reputation tax (–5pp growth,
  loss of idle income). See BALANCE_TESTING.md.
- Exact Syndicate Move support threshold — same rigor still owed here;
  not yet simulated.
- Raider/Builder ratio and reveal timing — too early and it kills tension,
  too late and it feels unfair. Not yet simulated; the JV tournament
  assumed a single shared win condition, so Raiders' effect on these
  numbers is still unknown.
- Season length variance — how much uncertainty in "when's the final round"
  is enough to sustain mid-season cooperation without feeling arbitrary?
- Onboarding: teaching "you need allies for the big plays, but they might
  be structurally against you," **and** that the final round is a
  deliberate exception where honesty stops being the strong play — three
  things to land without overwhelming a first-time player.
