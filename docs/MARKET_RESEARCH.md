# Market Research — PvP Business/Alliance Strategy Game

## TL;DR
The concept we landed on (companies as players, alliances that can betray,
PvP sabotage) is **not a novel niche — it's the exact mechanical skeleton of
the biggest genre in mobile gaming right now: 4X strategy MMOs** (Rise of
Kingdoms, Whiteout Survival, Last War: Survival, Lords Mobile, Evony). That's
good news (proven demand, proven monetization) and bad news (we'd be
entering a genre dominated by studios with massive budgets). The path for a
solo/indie dev is **not** to out-build them — it's to fuse in something they
don't do well: real hidden-information bluffing (our COUP DNA) and
season-bound, low-grind pods instead of eternal grind servers.

## 1. Market size & proof of demand
- Strategy is the **#1 revenue-generating mobile genre**, generating ~$17.5B
  in IAP revenue, and strategy/4X was the *only* category with positive
  growth across revenue, downloads, **and** time-spent in 2025 even as the
  broader mobile market matured.
  [Business of Apps](https://www.businessofapps.com/data/strategy-games-market/),
  [Udonis top-grossing ranking](https://www.blog.udonis.co/mobile-marketing/mobile-games/top-grossing-mobile-games)
- **Rise of Kingdoms** alone is a ~$2B lifetime-revenue game built on:
  alliances, PvP, resource/base management, commanders/heroes, live events.
  Day-1/7/30 retention: 41% / 20% / 9% — near top-tier for the genre.
  [Udonis breakdown](https://www.blog.udonis.co/mobile-marketing/mobile-games/rise-of-kingdoms-monetization)
- Current chart leaders (**Last War: Survival**, **Whiteout Survival**,
  **Kingshot**) all pair a shared world map, alliances, and PvP territory
  conflict with a survival/zombie theme.
  [FinancialContent](https://www.financialcontent.com/article/worldnewswire-2026-6-15-last-war-vs-whiteout-survival-a-battle-of-strategy-and-survival)
- Whales (>$1,000/month) are disproportionately concentrated in strategy
  games; ~5% of players drive >50% of IAP revenue industry-wide.

**Implication:** the "alliances + betrayal + PvP" hook is validated at
massive scale — we're not guessing whether people want this.

## 2. What actually drives retention (not just theme)
- **Social infrastructure, not content, is the retention fabric.** "The
  social centers, cooperation, and alliances players build are the
  retention fabric of 4X games" — players stay for the people, not the next
  feature drop.
  [Google Play Console genre report via Medium](https://medium.com/googleplaydev/succeeding-in-4x-strategy-games-e90dcf6db3f9)
- **Progressive complexity wins.** Top performers (Last War, Whiteout
  Survival) intentionally start hyper-casual-simple and *ramp* complexity,
  because the genre suffers severe early (D1–D30) drop-off — but players who
  survive onboarding show strong D60+ loyalty.
  [NextBigGames deep dive](https://nextbiggames.com/2025/11/14/a-deep-dive-into-the-4x-gaming-genre/)
- **Variable/unpredictable rewards beat fixed ones.** The Hooked Model
  (Trigger → Action → Variable Reward → Investment) and broader reinforcement
  research both show unpredictable outcomes drive materially more habitual
  engagement than predictable ones.
  [Nir Eyal / Google Play Medium](https://medium.com/googleplaydev/optimize-app-retention-with-the-hooked-model-a0781f8e5d29),
  [Dopamine loops study](https://jcoma.com/index.php/JCM/article/view/352)
- **Betrayal is a proven, studied psychological hook, not just a hunch.**
  Academic work on the board game *Diplomacy* found betrayal is one of the
  most emotionally significant events in a match, is linguistically
  predictable (politeness shifts precede betrayal), and only works *because*
  the game forces real interdependence — nobody can win alone, so trust
  decisions are forced and meaningful.
  [Cornell/Leskovec paper: "Linguistic Harbingers of Betrayal"](https://arxiv.org/abs/1506.04744),
  [Schneier on Security summary](https://www.schneier.com/blog/archives/2015/08/detecting_betra.html)
- **Coup itself is proof of the smaller claim:** its addictiveness comes
  from a tiny ruleset where every action might be a bluff, resolved in
  ~10 minutes — depth from mind-games, not content volume.

**Implication:** our GDD's core loop (secret actions → resolve → visible
betrayal/reputation) is aligned with what the research says actually works.
The risk isn't the concept, it's execution: onboarding softness and reward
unpredictability need explicit design attention, not just the alliance
mechanic itself.

## 3. What players/critics actually complain about (pitfalls to avoid)
- **Heavy pay-to-win perception.** Evony and similar titles are repeatedly
  criticized for "investment-heavy time-killing mechanics" once the surface
  wears off, and for aggressive/deceptive marketing history.
  [TechCrunch on Evony's ad controversy](https://techcrunch.com/2009/07/24/evony-ad-campaign-where-breasts-trick-you-into-playing-a-civ-clone)
- **New players get farmed by veteran alliances.** Structural complaint
  across the genre — protection shields exist precisely because unshielded
  new players get crushed by established players, which is a known churn
  driver.
- **Enormous, indefinite time investment.** Construction queues, research
  trees, hero systems, and alliance duties all run in parallel and never
  really end — reviewers note this is what turns curiosity into burnout.
- **Genre-wide D1–D30 churn is worse than casual genres.** Confirmed by the
  same Google/industry sources cited above — this is the single biggest
  structural risk to reuse this genre's mechanics naively.
- **Competing head-on requires serious capital.** Industry guidance pegs 4X
  dev costs with 25–100% contingency on top of "significant upfront
  investment," and notes the market is increasingly dominated by
  well-funded Chinese studios with massive UA budgets.
  [NextBigGames](https://nextbiggames.com/2025/11/14/a-deep-dive-into-the-4x-gaming-genre/)

**Implication:** don't clone Rise of Kingdoms' scope. A solo dev competing
on production value or ad spend loses immediately.

## 4. Where the actual opportunity is for a solo/indie dev
Industry sources are explicit that this genre still has room for indies —
just not by out-scaling incumbents:
- **4X has a smaller, more loyal, more selective audience** than casual
  genres, which suits a personalized, community-first indie approach rather
  than mass UA spend.
- **Genre fusion is the proven indie path.** *Puzzles & Survivors* hit $1B
  lifetime revenue by fusing match-3 with 4X mechanics — an "underexplored
  combination" bet, not a better version of an existing game.
  [NextBigGames](https://nextbiggames.com/2025/11/14/a-deep-dive-into-the-4x-gaming-genre/)
- Nobody in the current top charts is fusing 4X-style alliance/PvP with
  **real hidden-information bluffing** (Coup/Diplomacy-style secret roles,
  false claims, detectable-but-not-certain betrayal). Alliances in Rise of
  Kingdoms/Whiteout Survival are cooperative infrastructure, not a bluffing
  layer — this is a legitimate white space, not just our own preference.
- **Season-bound small pods** (6–8 players, 2–3 week seasons) directly
  answer the genre's two worst complaints — "goes on forever" and "new
  players get farmed by veterans" — since nobody has multi-season seniority
  advantage and every player enters a fresh, closed group.

## 5. Recommendation
Keep the pivot from the last GDD revision, but sharpen the pitch to make
the differentiation explicit rather than incidental:

> **A season-based 4X-lite where the alliance layer is a real bluffing
> game, not just chat and shared buffs — closed pods, no whales grinding
> for years, betrayal you can see coming if you're paying attention.**

Concretely, this means the GDD's MVP should:
1. Keep pods small and seasonal (already planned) — this is now a validated
   answer to the genre's #1 and #2 complaints, not just a scope-management
   trick for solo dev.
2. Explicitly design the **onboarding ramp** (start dead simple, layer in
   sabotage/alliance mechanics over the first few rounds) — the research is
   clear this is where the genre bleeds players.
3. Make reward timing **variable, not fixed** (e.g. don't resolve everything
   on a predictable clock with predictable magnitude) — ties directly to
   the Hooked Model finding.
4. Treat the **detection/betrayal-signal design** as the single most
   important balance question (echoing GDD section 8) — it's the
   academically-validated core of the hook, so it deserves prototyping
   before anything else.
5. Avoid the incumbents' biggest reputation risk: keep monetization
   cosmetic/convenience-only (already planned) and say so in marketing —
   "fair PvP" is a real differentiator against Evony/Lords Mobile's
   reputation.

## 6. Cross-genre research: how other games actually make trust real
Round two of research went wider than the 4X genre, specifically to answer
"if players know allies can betray them, why would anyone ally at all?" —
a real design flaw in the v2 GDD, which said betrayal was "always possible"
without giving cooperation any mechanical necessity. Findings, by game:

- **EVE Online** — alliances hold real, shared, drainable treasuries and
  territory. The game's most legendary moments (a director draining a
  trillion-ISK war chest overnight, e.g. "The Judge" betrayal of Circle of
  Two in 2017) are legendary specifically because the trust was built up
  over years and the stakes were real and large — not because betrayal was
  cheap or constant.
  [Kotaku: biggest betrayal in EVE history](https://kotaku.com/how-eve-players-pulled-off-the-biggest-betrayal-in-its-1806168400),
  [Massively OP on the Judge heist](https://massivelyop.com/2017/09/12/eve-online-political-betrayal-results-in-record-breaking-theft/)
- **Diplomacy** — the actual mechanical reason you need allies: a unit
  cannot dislodge a defended territory alone; attack strength is 1 + the
  number of other players' units supporting you. You are *mathematically*
  unable to make the biggest moves solo, regardless of trust.
  [Windy City Weasels intro](https://windycityweasels.org/intro-to-diplomacy/)
- **Secret Hitler / The Resistance: Avalon** — a hidden minority (with a
  different win condition than the majority) creates real epistemic
  uncertainty about who *can* stay loyal, not just who *chooses* to.
  Secret Hitler was explicitly designed to fix Werewolf/Avalon's over-reliance
  on pure social reading by adding a genuine information puzzle.
  [Medium: Hidden Information in Secret Hitler](https://medium.com/@tommygents/hidden-information-in-secret-hitler-f71d0251ee82)
- **The Traitors (TV format)** — Fusebox Games/All3media are shipping an
  officially licensed *The Traitors: Interactive Game* mobile app in 2026
  (hidden traitors, roundtable banishment). Direct competitive signal: a
  pure "hidden traitor + vote off" mechanic without an economic layer
  underneath it will compete head-on with a marketed, TV-IP-backed product.
  [The Escapist announcement](https://www.escapistmagazine.com/news-the-traitors-mobile-game-announced-fusebox/)
- **Blood on the Clocktower** — widely regarded as the best-designed modern
  social deduction game. Its "ghost" mechanic keeps eliminated players
  engaged with limited residual influence instead of having them disengage
  entirely, solving social deduction's classic elimination problem.
  [Wargamer review](https://www.wargamer.com/blood-on-the-clocktower/review),
  [Mechanics of Magic critical play](https://mechanicsofmagic.com/2024/04/07/critical-player-blood-on-the-clocktower/)
- **Sheriff of Nottingham** — a tight declare/inspect loop (claim your bag's
  contents; the Sheriff can trust or pay to inspect; asymmetric penalties
  either way; bribery adds a negotiation layer) is a reusable small-scale
  template for constant, round-to-round bluffing rather than one big
  betrayal at the end.
  [Geeky Hobbies rules/review](https://www.geekyhobbies.com/sheriff-of-nottingham-board-game-review-and-rules/)
- **Kremlin / Junta / Corruption** — older political-intrigue board games
  with a reusable pattern: secretly build a stake, but you must **publicly
  declare** it to actually use its power — a good template for an
  insider-position mechanic where cashing in requires exposing yourself.
  [Kremlin rules overview](https://boardgameguys.com/kremlin/)
- **Game theory (iterated Prisoner's Dilemma)** — defection becomes the
  rational move in a *known* final round because the "shadow of the
  future" disappears; cooperation is sustained mid-game by uncertainty
  about how much future interaction remains. Rather than fight this, the
  design should make the final round a deliberate, marketed climax (as
  Diplomacy, Survivor, and The Traitors all do) while keeping season-length
  timing uncertain enough to sustain mid-game cooperation.
  [FasterCapital summary of the endgame effect](https://fastercapital.com/content/Iterated-Game--Playing-the-Long-Game--Iterated-Prisoner-s-Dilemma-Explained.html)
- **Prediction markets** — a "wisdom of crowds" mechanic (players
  collectively price whether a claim/rumor is true, price moves as they
  bet) is a plausible design for the deferred rumor/misinformation system,
  worth prototyping after the MVP loop is proven.

**Implication:** the redesigned GDD (see GDD.md v3, "Consortium") borrows
the *mechanisms*, not the themes, from these — Syndicate Moves (Diplomacy's
support math), Joint Ventures (EVE's drainable treasuries), Hidden Raider
roles (Secret Hitler's minority win-condition), Declarations & Audits
(Sheriff of Nottingham's claim/inspect loop), and Ghost/Observer status
(Blood on the Clocktower's elimination fix) — recombined around the
finance/business theme, which is not something any single one of these
games does.

## 7. Open follow-ups worth researching next
- Direct player sentiment (actual Reddit threads) on *why* people quit Rise
  of Kingdoms/Evony specifically — general web search surfaced industry
  analysis reliably but not raw Reddit threads; worth browsing
  r/RiseOfKingdoms, r/EvonyTKR, r/MobileGaming directly for verbatim
  complaints if we want quotes for design decisions.
- Look at *Kingshot* and *Puzzles & Survivors* specifically as the newest
  breakout hits — both are recent enough that there's more to learn about
  what's currently working.
- User acquisition cost benchmarks for strategy genre — affects whether
  organic/word-of-mouth growth (viable per the indie-niche argument above)
  is realistic for launch or whether some paid UA is unavoidable.
