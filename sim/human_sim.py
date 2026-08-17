"""
Human-shaped extension of power_simulation.py.

power_simulation.py validated that the rules have no free exploits, using six
fixed, non-adaptive bots that never make a mistake and never react
emotionally to what just happened to them. That is a real gap: it proves the
math is sound, not that a table of actual people would have a good time.

This module does not replace that simulation, it adds a layer real humans
bring that a purely rational archetype does not:
  - mistakes (misclicks, distraction, just winging it, modeled as reverting
    to last round's habitual split rather than a fresh random one)
  - grudges (retaliating against whoever hit you, not whoever is optimal)
  - bandwagoning (piling on a weak target harder once others already are)
  - a Casual archetype standing in for a first-time or half-attentive player
  - disengagement tracking: how many rounds does a beaten-down player spend
    with nothing meaningful to do, which is the actual mechanism behind the
    "eliminated players get bored" review finding
  - raid fatigue: a repeat successful attacker's future attacks get weaker,
    mirroring the reputation tax already validated for Joint Ventures

It also sweeps player count (3 to 8), which the original simulation never
varied, to test whether the round structure holds up outside the
six-player pod it was originally tuned on (see BALANCE_TESTING.md Part 16,
17: it does, once `roster_for` samples a fair archetype mix instead of a
fixed prefix).

A "fear after being hit" trait (playing scared and safe for a while after a
takeover) took four attempts (`apply_fear_hesitation`). The first three
(divert new investment to Real Estate, divert proportionally from company
and cash, freeze into cash) each handed the affected player a defense
boost they didn't pay for, or, for Aggressor specifically, fed straight
into the one resource that archetype already wants to hoard. The fourth
doesn't redirect anywhere: it just deploys less of a hit player's new
investment for a couple of rounds, leaving the rest as plain, unenhanced
idle cash, and exempts Aggressor/Leverager outright rather than hoping
they don't benefit. Clean in testing, see BALANCE_TESTING.md Part 19.

Run directly to print a summary and write CSVs next to this file.
"""

import csv
import random
import statistics

from power_simulation import (
    ARCHETYPES,
    BANKRUPTCY_LIQUIDATION_PCT,
    BUILDING_ROUNDS,
    COMPANY_INCOME_RATE,
    DEFENDER_TIE_BONUS,
    JV_DRAIN_BONUS,
    JV_GROWTH,
    LOAN_INTEREST_BASE,
    LOAN_RISK_PREMIUM,
    POST_ATTACK_SHIELD_ROUNDS,
    REAL_ESTATE_INCOME_RATE,
    REP_TAX_THRESHOLD,
    TAKEOVER_CAPTURE_PCT,
    TOTAL_ROUNDS,
    Player,
    allocate,
    defense_power_of,
)

INDUSTRIES = [
    "Healthcare",
    "Technology",
    "Pharma",
    "Energy",
    "Financial Services",
    "Consumer Retail",
    "Agriculture",
    "Manufacturing",
    "Media & Entertainment",
    "Property",
]

# (scenario text, {industry: tier}); unlisted industries stay flat. Tiers are
# resolved to an actual rolled number at draw time (see draw_scenario), not a
# fixed percentage: the same scenario doesn't pay out the same number twice,
# only the same rough character (a strong move stays strong, a mild one stays
# mild), matching GDD.md Section 5A's table exactly.
SCENARIOS = [
    (
        "A major regional conflict breaks out",
        {
            "Energy": "++",
            "Manufacturing": "+",
            "Pharma": "+",
            "Agriculture": "-",
            "Consumer Retail": "-",
            "Gold": "+",
        },
    ),
    (
        "A breakthrough vaccine is announced",
        {"Pharma": "++", "Healthcare": "+", "Media & Entertainment": "+"},
    ),
    (
        "Interest rates are cut sharply",
        {"Property": "++", "Consumer Retail": "+", "Technology": "+", "Gold": "+"},
    ),
    (
        "A major tech company reports a data breach",
        {"Technology": "--", "Financial Services": "-"},
    ),
    ("A bumper harvest season", {"Agriculture": "+", "Consumer Retail": "+"}),
    (
        "A severe drought hits key farming regions",
        {"Agriculture": "--", "Consumer Retail": "-", "Gold": "+"},
    ),
    (
        "A new blockbuster streaming platform launches",
        {"Media & Entertainment": "++", "Technology": "+"},
    ),
    (
        "Oil prices crash on oversupply",
        {
            "Energy": "--",
            "Manufacturing": "+",
            "Consumer Retail": "+",
            "Agriculture": "+",
            "Gold": "+",
        },
    ),
    (
        "A recession is officially declared",
        {
            "Consumer Retail": "--",
            "Financial Services": "--",
            "Technology": "-",
            "Property": "-",
            "Gold": "++",
        },
    ),
    (
        "A landmark trade deal is signed",
        {
            "Manufacturing": "++",
            "Agriculture": "+",
            "Technology": "+",
            "Consumer Retail": "+",
            "Gold": "-",
        },
    ),
    (
        "Consumer confidence hits a record high",
        {
            "Consumer Retail": "++",
            "Media & Entertainment": "+",
            "Property": "+",
            "Gold": "-",
        },
    ),
    (
        "A cybersecurity crisis hits financial institutions",
        {"Financial Services": "--", "Technology": "-", "Gold": "+"},
    ),
    (
        "Housing demand surges in major cities",
        {"Property": "++", "Financial Services": "+"},
    ),
    (
        "Global supply chains face major disruption",
        {
            "Manufacturing": "--",
            "Consumer Retail": "-",
            "Technology": "-",
            "Agriculture": "-",
            "Gold": "+",
        },
    ),
    (
        "A wave of mergers sweeps the healthcare industry",
        {"Healthcare": "+", "Pharma": "+", "Financial Services": "+"},
    ),
    (
        "Renewable energy investment surges",
        {"Energy": "+", "Manufacturing": "+", "Technology": "+"},
    ),
    (
        "A major retailer files for bankruptcy",
        {
            "Consumer Retail": "--",
            "Property": "-",
            "Financial Services": "-",
            "Gold": "+",
        },
    ),
    (
        "Streaming and gaming demand hits an all-time high",
        {"Media & Entertainment": "++", "Technology": "+"},
    ),
    (
        "A wave of automation disrupts manufacturing jobs",
        {"Manufacturing": "+", "Technology": "+", "Consumer Retail": "-"},
    ),
    ("A quiet, uneventful year in the markets", {}),
]

# A tier is a character, not a number: "++" always means "a strong positive
# move," but the exact size is rolled fresh from this range every time, so
# the same scenario never pays out identically twice. Ceilings are set wide
# on purpose, real crises and booms aren't a neat, memorizable +8%, they can
# occasionally run much hotter than the typical case without going to an
# absurd extreme.
SCENARIO_TIER_RANGES = {
    "++": (0.04, 0.20),
    "+": (0.01, 0.08),
    "-": (-0.08, -0.01),
    "--": (-0.20, -0.04),
}

# Gold's tiers are deliberately smaller and asymmetric (no "--"): it's a
# hedge, its whole job is losing less than everything else in a downturn,
# not swinging as violently as the industry it's a hedge against.
GOLD_TIER_RANGES = {
    "++": (0.03, 0.15),
    "+": (0.01, 0.06),
    "-": (-0.04, -0.01),
}

INDUSTRY_EVENTS_ENABLED = False  # set per-run


def assign_industries(players, rng):
    """Each player is assigned an industry, standing in for the real
    onboarding choice (GDD.md Section 5A). Repeats are fine, industries
    aren't a scarce resource players compete over.
    """
    if not INDUSTRY_EVENTS_ENABLED:
        return
    for p in players:
        p.industry = rng.choice(INDUSTRIES)


def draw_scenario(rng):
    """Picks this round's scenario, then rolls each named industry's tier
    into an actual number for this specific round. The tier (how strong,
    which direction) is fixed by the scenario text, since that's the part
    a player can genuinely read and reason about, "a recession is bad for
    Consumer Retail" is always true. The exact size is not fixed, rolled
    fresh from SCENARIO_TIER_RANGES/GOLD_TIER_RANGES every time, so the
    same scenario never pays out the identical number twice and there is
    nothing to memorize beyond direction and rough magnitude.
    """
    text, tiers = rng.choice(SCENARIOS)
    deltas = {}
    for industry, tier in tiers.items():
        ranges = GOLD_TIER_RANGES if industry == "Gold" else SCENARIO_TIER_RANGES
        lo, hi = ranges[tier]
        deltas[industry] = rng.uniform(lo, hi)
    return text, deltas


GOLD_BASE_RANGE = (
    0.005,
    0.035,
)  # ordinary-year jitter, centered near 2%, never a fixed number
GOLD_ALLOCATION_RATE = 0.15  # fraction of new cash a hedging archetype redirects into Gold instead of growth assets
GOLD_ENABLED = False  # set per-run
REAL_ESTATE_SCENARIO_DAMPENER = (
    0.5  # RE feels the Property scenario delta at half strength, stays the safer asset
)


def gold_growth_rate(scenario_deltas, rng):
    """Gold's real-world behavior isn't "another random industry," it's a
    flight-to-safety hedge: low in ordinary years, a real spike
    specifically during crisis scenarios (war, recession, a financial
    system shock), and a mild pullback during broad optimism, when money
    chases growth assets instead. The whole point of holding it is doing
    relatively better exactly when Company income and the Market are
    doing worse, see the "Gold" deltas on individual SCENARIOS entries.

    Even the ordinary-year case isn't a flat 2%: real gold prices drift on
    their own with no news at all, so the base itself is rolled from
    GOLD_BASE_RANGE every round, not a constant.
    """
    base = rng.uniform(*GOLD_BASE_RANGE)
    if not scenario_deltas:
        return base
    return base + scenario_deltas.get("Gold", 0.0)


ATTACK_FAIL_LOSS_PCT = 0.5
LEADER_THREATENED_MARGIN = 1.05  # was 1.3; see BALANCE_TESTING.md Part 7 for why
DISENGAGED_CASH_THRESHOLD = 3.0
DISENGAGED_COMPANY_THRESHOLD = 20.0
STOCK_INCOME_RATE_FALLBACK = (
    0.08  # power_simulation.py's old flat rate, used when long/short is off
)
LONG_SHORT_STOCKS_ENABLED = (
    False  # set per-run; breaks the validated baseline as of Part 6, not fixed yet
)
COUNTER_ATTACK_CAPTURE_PCT = (
    TAKEOVER_CAPTURE_PCT  # set per-run; see __main__ for the sweep that picked this
)


class HumanPlayer(Player):
    """A Player with individual quirks layered on top of an archetype.

    Traits are randomized per game so a "Turtle" in one trial is not the
    identical Turtle in the next, the same way two cautious friends do not
    play identically cautiously.
    """

    def __init__(self, idx, archetype, rng):
        super().__init__(idx, archetype)
        self.grudge_bias = rng.uniform(0.0, 0.6)
        self.mistake_rate = rng.uniform(0.03, 0.25)
        self.bandwagon_bias = rng.uniform(0.0, 0.4)
        # Operator leans into Power Cards by design (see operator_allocation): a
        # naturally higher declare_bias range, not a second special-cased probability system
        self.declare_bias = (
            rng.uniform(0.6, 0.95) if archetype == "Operator" else rng.uniform(0.2, 0.8)
        )
        self.last_attacker_idx = None
        self.dead_rounds = 0
        self.broke_rounds = (
            0  # rounds broke regardless of backing, the pre-fix baseline for comparison
        )
        self.pact_posture = {}  # ally_idx -> True (declared, visible) / False (covert, hidden)
        self.last_shares = (
            0.4,
            0.1,
            0.5,
        )  # company, real_estate, cash defaults before any history
        self.raid_count = 0  # successful takeovers landed this game, as an attacker
        self.backing_idx = (
            None  # fallback: who this Board Observer roots for if never recruited
        )
        self.co_founder_of = (
            None  # idx of the living player's company this player actively co-runs
        )
        self.co_founder_equity = (
            0.0  # this co-founder's live phantom-equity stake in the host's Company
        )
        self.ever_raided = (
            False  # has this player ever been successfully taken over, this game
        )
        self.stock_meta = {}  # target_idx -> {"principal", "direction", "entry_power"}
        self.receivables = {}  # borrower_idx -> amount still owed to this player on a peer loan
        self.peer_debt = {}  # lender_idx -> amount this player still owes on a peer loan
        self.round_profit = (
            0.0  # this round's total earnings, every source, the income tax base
        )
        self.is_raider = False  # secretly a Raider: wins if raider_target_idx fails, not by own Power
        self.raider_target_idx = None
        self.industry = None  # set by assign_industries when INDUSTRY_EVENTS_ENABLED
        self.industry_positions = {}  # industry_name -> {"principal", "direction"}
        self.bank_deposit = 0.0  # cash parked with the Bank, earning BANK_DEPOSIT_RATE, exempt from erosion
        self.gold = 0.0  # a flight-to-safety hedge, see gold_growth_rate; illiquid, not in collect_payment yet
        self.jv_pots = {}  # ally_idx -> shared dict (mirrored on both sides) {"value", "contributed_each", "industry"}
        self.pending_pact_break = None  # ally_idx a declared pact break was initiated against, resolves next round
        self.pact_break_count = 0  # declared pact breaks this player has initiated; a second one costs Power
        self.power_card = None  # the Power Card type this player actually holds, set by assign_power_cards
        self.power_card_action_used = (
            False  # this player's own card action, once-per-game
        )
        self.power_card_has_bluffed = (
            False  # at most one bluffed claim per game, see resolve_power_card_claims
        )
        self.hesitant_until_round = 0  # round number a Post-Hit Hesitation window (see apply_fear_hesitation) ends
        self.power_card_block_used = (
            False  # this player's own card block, once-per-game, see try_guardian_block
        )
        self.banker_waiver_pending = False  # next interest accrual uses the flat base rate, see resolve_power_card_claims
        self.analyst_perception_shock = 0.0  # a multiplier on this player's visible defense for the rest of this round only

    def is_broke(self):
        """Has next to nothing left to allocate, the raw financial condition,
        independent of whether they've found something else to do about it.
        """
        return self.bankrupt or (
            self.cash < DISENGAGED_CASH_THRESHOLD
            and self.company < DISENGAGED_COMPANY_THRESHOLD
        )

    def is_disengaged(self):
        """Broke, not co-running a company, and without even a backing pick.

        Co-founder is the real fix: an ongoing, repeated decision every
        round, not a one-time label. Backing is the fallback when nobody's
        recruited you, better than nothing but not a substitute.
        """
        return (
            self.is_broke() and self.backing_idx is None and self.co_founder_of is None
        )

    def total_power(self):
        """Adds peer-lending receivables as an asset and peer debt as a
        liability on top of the base calculation, a receivable is real
        value (illiquid until repaid or defaulted on), a peer debt is a
        real obligation, same as Bank debt.
        """
        jv_share = sum(pot["value"] / 2 for pot in self.jv_pots.values())
        return (
            super().total_power()
            + self.bank_deposit
            + self.gold
            + jv_share
            + self.co_founder_equity
            + sum(self.receivables.values())
            - sum(self.peer_debt.values())
        )


def generate_income_human(p, bank, stats, players, rng, scenario_deltas=None):
    """Same as power_simulation.generate_income (company/Real Estate income,
    debt interest, bankruptcy check), minus the flat stock income term.

    Stocks no longer pay a flat diluted dividend, they gain or lose value
    with the target's actual performance instead (see
    `revalue_stock_positions`), a real market position, not an annuity.
    Duplicates a few lines from the original rather than threading a flag
    through it, the alternative made the shared function harder to read for
    a small save in duplication.

    Income tax is NOT applied here: a "round" is a year (per direct
    instruction), and real income tax is assessed once a year on every
    source of profit combined, not withheld separately per income stream.
    This just adds passive income to `round_profit`, the actual tax
    happens once at the end of the round in `apply_income_tax`, after
    captures and Joint Venture proceeds have also been added to it.

    `scenario_deltas`, when INDUSTRY_EVENTS_ENABLED, is this round's drawn
    scenario's effect on Company income if the player's industry is one of
    the ones it names, the direct fix for the Building Phase reducing to
    "always max Company," a real scenario-reading skill instead of a
    solved formula, see BALANCE_TESTING.md Part 12. Real Estate feels the
    same scenario's "Property" delta too, but dampened to half strength
    (REAL_ESTATE_SCENARIO_DAMPENER): it should be touched by the same
    world events as everything else, just more mildly, staying the safer,
    defense-weighted asset rather than a second copy of Company income.

    Gold, when GOLD_ENABLED, is not a dividend-paying asset like Company
    or Real Estate, it's a store of value that appreciates or depreciates
    in place (see `gold_growth_rate`), so its gain is added to the
    holding itself, not paid out as cash.
    """
    company_rate = COMPANY_INCOME_RATE
    if INDUSTRY_EVENTS_ENABLED and scenario_deltas and p.industry in scenario_deltas:
        company_rate += scenario_deltas[p.industry]
    company_income = p.company * company_rate

    re_rate = REAL_ESTATE_INCOME_RATE
    if INDUSTRY_EVENTS_ENABLED and scenario_deltas and "Property" in scenario_deltas:
        re_rate += scenario_deltas["Property"] * REAL_ESTATE_SCENARIO_DAMPENER
    income = company_income + p.real_estate * re_rate
    if not LONG_SHORT_STOCKS_ENABLED:
        income += sum(p.stocks.values()) * STOCK_INCOME_RATE_FALLBACK
    p.round_profit += income
    p.cash += income

    if GOLD_ENABLED:
        gold_gain = p.gold * gold_growth_rate(scenario_deltas, rng)
        p.gold = max(0.0, p.gold + gold_gain)
        p.round_profit += gold_gain

    if p.debt > 0 and not p.bankrupt:
        if p.banker_waiver_pending:
            # Banker's Easy Terms and Standstill (GDD.md Section 8.1) both
            # collapse to the same mechanical effect here: the leverage risk
            # premium is waived for one interest accrual, deliberately
            # applying to the round after the claim (income resolves before
            # a round's Power Card claims do), not the same round, the same
            # "takes effect next" shape the Defense Pact breakup penalty
            # already uses (Section 7).
            rate = LOAN_INTEREST_BASE
            p.banker_waiver_pending = False
        else:
            pre_debt_power = (
                p.cash + p.company + p.real_estate + sum(p.stocks.values()) + p.captured
            )
            leverage_ratio = p.debt / max(1.0, pre_debt_power)
            rate = LOAN_INTEREST_BASE + LOAN_RISK_PREMIUM * leverage_ratio
        p.debt *= 1 + rate

    if p.total_power() < 0 and not p.bankrupt:
        p.bankrupt = True
        p.cash *= 1 - BANKRUPTCY_LIQUIDATION_PCT
        p.company *= 1 - BANKRUPTCY_LIQUIDATION_PCT
        p.real_estate *= 1 - BANKRUPTCY_LIQUIDATION_PCT
        p.gold *= 1 - BANKRUPTCY_LIQUIDATION_PCT
        for k in p.stocks:
            p.stocks[k] *= 1 - BANKRUPTCY_LIQUIDATION_PCT
        p.debt = 0.0
        for lender_idx in list(p.peer_debt.keys()):
            p.peer_debt[lender_idx] = 0.0  # discharged, same as Bank debt


def track_new_stock_investment(p, players, stocks_before, rng):
    """After allocate() runs, any stock position that grew gets a
    long/short direction and an entry Power reference.

    Direction is a simple, defensible heuristic since bots don't have
    beliefs: go long on a target who's currently at or above the investor's
    own Power (betting on continued strength), short a target who's below
    (betting a struggling company keeps struggling), real short-selling
    logic, not a coin flip. Topping up an existing position resets its
    entry reference, a weighted-average cost basis would be more accurate
    but adds real complexity for a marginal gain here.
    """
    for target_idx, new_value in p.stocks.items():
        added = new_value - stocks_before.get(target_idx, 0.0)
        if added <= 0:
            continue
        target = players[target_idx]
        direction = "long" if target.total_power() >= p.total_power() else "short"
        p.stock_meta[target_idx] = {
            "principal": new_value,
            "direction": direction,
            "entry_power": max(1.0, target.total_power()),
        }


def revalue_stock_positions(players):
    """Marks every stock position to the target's actual Power change since
    entry: long gains when they grow (including from a successful
    takeover's captured value), loses when they shrink or get taken over, a
    real correlated risk. Short is the mirror image. Replaces the old flat
    8%/round income, which paid out the same whether the target was
    thriving or had just been raided.
    """
    if not LONG_SHORT_STOCKS_ENABLED:
        return
    for p in players:
        for target_idx, meta in list(p.stock_meta.items()):
            target = players[target_idx]
            pct_change = (target.total_power() - meta["entry_power"]) / meta[
                "entry_power"
            ]
            if meta["direction"] == "short":
                pct_change = -pct_change
            p.stocks[target_idx] = max(0.0, meta["principal"] * (1 + pct_change))


def track_new_industry_investment(p, rng):
    """Redirects whatever `allocate()` just invested in a specific rival
    into an Industry position instead, when INDUSTRY_EVENTS_ENABLED: the
    Market is industries now, not people (GDD.md Section 5A). Picks a
    random industry, long or short with equal odds, since bots don't have
    real convictions about which sector is due for a swing, a real human
    would actually read the scenario text first.

    Reuses `p.stocks` (keyed by industry name instead of a player index in
    this mode) so `total_power()` picks the value up without another
    override, `industry_positions` tracks direction and principal
    separately, same pattern as `stock_meta` for the player-targeted mode.
    """
    if not INDUSTRY_EVENTS_ENABLED:
        return
    for target_idx in list(p.stocks.keys()):
        if not isinstance(target_idx, int):
            continue  # already an industry position, not a fresh player-target one
        added = p.stocks.pop(target_idx)
        if added <= 0:
            continue
        industry = rng.choice(INDUSTRIES)
        direction = rng.choice(("long", "short"))
        existing = p.industry_positions.get(
            industry, {"principal": 0.0, "direction": direction}
        )
        existing["principal"] += added
        existing["direction"] = direction
        p.industry_positions[industry] = existing
        p.stocks[industry] = existing["principal"]


def revalue_industry_positions(players, scenario_deltas):
    """Marks every Industry position to that round's scenario: long gains
    when the sector is up, loses when it's down, short is the mirror
    image. Same "real correlated risk, not a flat annuity" logic as
    `revalue_stock_positions`, just against a sector event instead of one
    rival's fortunes.
    """
    if not INDUSTRY_EVENTS_ENABLED:
        return
    for p in players:
        for industry, meta in p.industry_positions.items():
            delta = scenario_deltas.get(industry, 0.0) if scenario_deltas else 0.0
            if meta["direction"] == "short":
                delta = -delta
            meta["principal"] = max(0.0, meta["principal"] * (1 + delta))
            p.stocks[industry] = meta["principal"]


def autopilot_allocation(p, rng):
    """A distracted or misclicking round: repeat last round's habitual split
    rather than reconsidering from scratch. A real person who isn't paying
    close attention defaults to what they did last time, they don't roll
    dice on a fresh random allocation, so this is a closer model of a
    mistake than pure randomness would be.
    """
    cash_available = p.cash
    company_share, re_share, cash_share = p.last_shares
    p.company += cash_available * company_share
    p.real_estate += cash_available * re_share
    p.cash = cash_available * cash_share


def record_shares(p, cash_available, company_before, re_before):
    """Remembers this round's actual company/real-estate/cash split so a
    future mistake round can fall back to it via autopilot_allocation.
    """
    if cash_available <= 0:
        return
    company_share = max(0.0, (p.company - company_before) / cash_available)
    re_share = max(0.0, (p.real_estate - re_before) / cash_available)
    cash_share = max(0.0, p.cash / cash_available)
    total = company_share + re_share + cash_share
    if total > 0:
        p.last_shares = (company_share / total, re_share / total, cash_share / total)


def casual_allocation(p, players, rng):
    """A first-time or half-attentive player: mild company bias, otherwise near-random."""
    cash_available = p.cash
    company_share = rng.uniform(0.35, 0.55)
    re_share = rng.uniform(0.0, 0.25)
    remaining = max(0.0, 1.0 - company_share - re_share)
    stock_share = remaining * rng.uniform(0.0, 0.6)
    cash_share = remaining - stock_share
    p.company += cash_available * company_share
    p.real_estate += cash_available * re_share
    if stock_share > 0:
        target = rng.choice([q for q in players if q.idx != p.idx])
        p.stocks[target.idx] = (
            p.stocks.get(target.idx, 0) + cash_available * stock_share
        )
    p.cash = cash_available * cash_share


def speculator_allocation(p, players, rng):
    """Nobody in the original 6-archetype roster treats the Market as a
    primary strategy, everyone else only dabbles in it as a side
    allocation on top of company/Real Estate growth. The Speculator tests
    what a dedicated, concentrated Market bettor actually looks like: heavy
    Market exposure, minimal company or Real Estate growth, no better
    read on which way a sector moves than anyone else (bots don't have
    real convictions), just far more of their capital riding on the
    outcome either way.
    """
    cash_available = p.cash
    p.company += cash_available * 0.15
    p.real_estate += cash_available * 0.10
    target = rng.choice([q for q in players if q.idx != p.idx])
    p.stocks[target.idx] = p.stocks.get(target.idx, 0) + cash_available * 0.60
    p.cash = cash_available * 0.15


def prepper_allocation(p, players, rng):
    """Turtle already plays defense-first through Real Estate specifically.
    The Prepper tests a different flavor of caution: opt out of growth
    almost entirely, keep a modest Real Estate floor, and leave the rest as
    spare cash. Deliberately does nothing special with that spare cash
    itself, `apply_gold_hedge` (extended below to include this archetype)
    and `manage_bank_deposits`'s automatic sweep both already exist and
    both already do exactly the job a hoarding archetype needs, reusing
    them costs nothing and avoids a second, redundant hedging path.
    """
    cash_available = p.cash
    p.company += cash_available * 0.10
    p.real_estate += cash_available * 0.25
    p.cash = cash_available * 0.65


def operator_allocation(p, players, rng):
    """Tests a player who leans hard into Power Cards (Section 8.1) rather
    than a concentrated financial position, behaviorally simple everywhere
    else (a balanced, Diversifier-like split), but given a naturally
    higher `declare_bias` at deal time (see HumanPlayer.__init__), so claim
    and Audit chances (`_power_card_claim_chance`, `_power_card_audit_chance`)
    run well above the table average without a second, special-cased
    probability system. Keeps a larger cash reserve than most archetypes:
    both claiming and Auditing cost real cash (Section 8.3).
    """
    cash_available = p.cash
    p.company += cash_available * 0.30
    p.real_estate += cash_available * 0.25
    target = rng.choice([q for q in players if q.idx != p.idx])
    p.stocks[target.idx] = p.stocks.get(target.idx, 0) + cash_available * 0.20
    p.cash = cash_available * 0.25


def momentum_allocation(p, players, rng, scenario_deltas):
    """Chases whichever asset class read stronger this round, a real,
    distinct behavioral pattern ("the hot hand") no existing archetype
    models: everyone else plays a fixed split regardless of what the
    scenario just did. Falls back to an even-ish default split without
    Industries active, there's no signal to chase without a scenario
    delta to compare.
    """
    cash_available = p.cash
    company_lean, re_lean = 0.45, 0.25
    if scenario_deltas:
        company_delta = scenario_deltas.get(p.industry, 0.0) if p.industry else 0.0
        re_delta = scenario_deltas.get("Property", 0.0) * REAL_ESTATE_SCENARIO_DAMPENER
        if re_delta > company_delta:
            company_lean, re_lean = 0.25, 0.45
    p.company += cash_available * company_lean
    p.real_estate += cash_available * re_lean
    p.cash = cash_available * (1.0 - company_lean - re_lean)


def apply_gold_hedge(p, rng):
    """A simple, defensible default for who bothers hedging: Turtle
    (already defense-first) and Diversifier (already spreads across
    everything) redirect a modest slice of their remaining cash into
    Gold instead of chasing more growth. Aggressor, SoloGrinder,
    Leverager, and Socialite are all playing some form of "concentrate
    and grow," they have no reason to bother with a low-yield hedge.
    """
    if not GOLD_ENABLED or p.archetype not in ("Turtle", "Diversifier", "Prepper"):
        return
    if p.cash <= DISENGAGED_CASH_THRESHOLD:
        return
    nudge = p.cash * GOLD_ALLOCATION_RATE
    p.cash -= nudge
    p.gold += nudge


FEAR_ENABLED = False  # set per-run
FEAR_ROUNDS = 2  # rounds of hesitation after being successfully hit by a takeover or counter-attack
FEAR_DEPLOYMENT_FRACTION = 0.6  # fraction of a hesitant player's new investment that still deploys; the rest sits as plain cash
# Aggressor and Leverager already keep a lot of cash liquid on purpose, that's their whole
# strategy. A fourth attempt at "fear" arming them further would reproduce the exact failure
# Part 3 Finding 6 already found and dropped (freezing into cash fed Aggressor's own base plan).
FEAR_EXEMPT_ARCHETYPES = ("Aggressor", "Leverager")


def apply_fear_hesitation(p, current_round, company_before, re_before, stocks_before):
    """A player who was just successfully hit plays it safe for a couple of
    rounds, a fourth attempt at a mechanic dropped three times before
    (BALANCE_TESTING.md Part 3, Finding 6). Every previous version
    redirected new investment into a specific bucket, into Real Estate
    (a free defense boost, since Real Estate is weighted far more heavily
    than cash, 0.9x vs 0.3x), or into cash specifically (which fed
    Aggressor's own already-liquid base strategy instead of penalizing it).
    This version doesn't redirect anywhere: it just deploys less of this
    round's new investment, full stop, and the clawed-back portion sits as
    ordinary idle cash, weakly weighted in defense, exposed to idle cash
    erosion if that's active, and not specially useful to any archetype's
    identity, a real, unenhanced opportunity cost rather than a disguised
    reward. Exempts the two archetypes (see FEAR_EXEMPT_ARCHETYPES) whose
    base strategy already keeps a lot of cash on hand on purpose, the
    specific trap every earlier attempt fell into for them.
    """
    if not FEAR_ENABLED or p.archetype in FEAR_EXEMPT_ARCHETYPES:
        return
    if p.hesitant_until_round < current_round:
        return
    clawback = 1.0 - FEAR_DEPLOYMENT_FRACTION
    company_added = max(0.0, p.company - company_before)
    re_added = max(0.0, p.real_estate - re_before)
    p.company -= company_added * clawback
    p.real_estate -= re_added * clawback
    p.cash += (company_added + re_added) * clawback
    for target_idx, value in list(p.stocks.items()):
        added = max(0.0, value - stocks_before.get(target_idx, 0.0))
        if added <= 0:
            continue
        p.stocks[target_idx] -= added * clawback
        p.cash += added * clawback


def allocate_human(p, players, rng, current_round=1, scenario_deltas=None):
    """Wraps the rational archetype allocation with mistakes."""
    cash_available = p.cash
    if rng.random() < p.mistake_rate:
        autopilot_allocation(p, rng)
        return

    company_before, re_before = p.company, p.real_estate
    stocks_before = dict(p.stocks)
    if p.archetype == "Casual":
        casual_allocation(p, players, rng)
    elif p.archetype == "Speculator":
        speculator_allocation(p, players, rng)
    elif p.archetype == "Prepper":
        prepper_allocation(p, players, rng)
    elif p.archetype == "Operator":
        operator_allocation(p, players, rng)
    elif p.archetype == "Momentum":
        momentum_allocation(p, players, rng, scenario_deltas)
    else:
        allocate(p, players, rng)
    if INDUSTRY_EVENTS_ENABLED:
        # replaces the player-targeted Market entirely (GDD.md Section 5A),
        # not layered alongside it: mixing the two left stale stock_meta
        # entries able to silently re-create player-keyed positions after
        # they'd already been redirected to an industry
        track_new_industry_investment(p, rng)
    else:
        track_new_stock_investment(p, players, stocks_before, rng)
    apply_real_estate_purchase_cost(p, re_before)
    apply_gold_hedge(p, rng)
    apply_fear_hesitation(p, current_round, company_before, re_before, stocks_before)

    record_shares(p, cash_available, company_before, re_before)


def set_pact_posture(p, partner, rng):
    """Decides, once, whether a new Defense Pact is declared (visibly boosts
    the target's defense number, deters attacks, exposes the alliance) or
    covert (invisible to attackers beforehand, a real reinforcement only at
    resolution). Reuses each player's declare_bias trait rather than a fixed
    per-archetype rule, since real people vary in how much they want the
    deterrence versus the surprise.
    """
    declared = rng.random() < (p.declare_bias + partner.declare_bias) / 2
    p.pact_posture[partner.idx] = declared
    partner.pact_posture[p.idx] = declared


MAX_ALLIES = 2  # set per-run; see BALANCE_TESTING.md Part 8 for why this number


def try_form_jv_human(p, players, rng):
    if p.archetype == "Casual":
        if len(p.allies) >= min(1, MAX_ALLIES) and rng.random() < 0.7:
            return
        candidates = [q for q in players if q.idx != p.idx and q.idx not in p.allies]
        if len(p.allies) < MAX_ALLIES and candidates and rng.random() < 0.3:
            partner = rng.choice(candidates)
            p.allies.add(partner.idx)
            partner.allies.add(p.idx)
            set_pact_posture(p, partner, rng)
        return

    if p.archetype not in ("Socialite", "Diversifier"):
        return
    if len(p.allies) >= MAX_ALLIES:
        return
    candidates = [
        q
        for q in players
        if q.idx != p.idx
        and q.idx not in p.allies
        and q.drain_count < REP_TAX_THRESHOLD
    ]
    if not candidates:
        return
    partner = rng.choice(candidates)
    if p.cash > 10 and partner.archetype in (
        "Socialite",
        "Diversifier",
        "Turtle",
        "Casual",
        "Prepper",
    ):
        p.allies.add(partner.idx)
        partner.allies.add(p.idx)
        set_pact_posture(p, partner, rng)


JV_CONTRIBUTION_UNIT = 10.0  # fixed amount each partner puts in to seed a JV; top-ups grow from here, see JV_TOPUP_RATE
JV_TOPUP_RATE = 0.2  # a later top-up is 20% of the poorer partner's current cash, floored at the seed amount
JV_TOPUP_CASH_BUFFER = (
    15.0  # a partner skips a top-up if it would cut them below this much spare cash
)
REPUTATION_PENALTY_PCT = 0.15  # a visible Power hit the instant a second betrayal is confirmed, not a hidden tax


def apply_reputation_penalty(p, stats):
    """ "Reputation" was never a real, trackable metric, a review of this
    session's own explanations caught that directly: there was no visible
    number anywhere a player could check, just repeated hand-waving. Fixed
    by making it not a separate metric at all. A JV drain is a public
    event at the table, the pot visibly moving between two named players,
    not private math, so everyone already saw it happen once. A second
    confirmed betrayal (REP_TAX_THRESHOLD) costs the drainer immediately
    and visibly: a real chunk of their own current wealth, docked on the
    spot, right there in Power, the one number this whole design already
    commits to being the only thing anyone tracks. No separate reputation
    score to display, no hidden counter to explain, the consequence IS
    Power, the same way the betrayal itself already was.

    Fires exactly once, the round `drain_count` crosses the threshold, not
    every round after: a second betrayal costs you, a fifth doesn't cost
    you again on top of that.
    """
    if p.drain_count != REP_TAX_THRESHOLD:
        return
    penalty = collect_payment(p, p.total_power() * REPUTATION_PENALTY_PCT)
    stats["reputation_penalties_paid"] += penalty


def resolve_jvs_human(players, rng, is_final_round, stats, scenario_deltas=None):
    """A Joint Venture is a shared position in one Industry, not a
    separate side bet with its own guaranteed rate. On formation it's
    assigned an Industry (a real player's deliberate pick at the table,
    a random one for these bots, since they don't have beliefs), and the
    pot moves with that Industry's actual scenario delta every round,
    exactly the same number that moves Company income and a solo Market
    position, no extra multiplier stacked on top. If Healthcare is down
    8% this round, a Healthcare JV is down 8%, full stop.

    That means a JV's expected return is *identical* to just investing in
    that Industry solo. The entire reason to form one instead is what a
    solo position can't offer: two partners can pool more capital than
    either affords alone, and either one can drain the shared pot early
    and keep the majority, a real trust problem a solo position never has.
    That's the actual profit motive behind a backstab: the drainer walks
    away with 65% of a pot they only funded half of, real, immediate
    upside for betraying the norm of an even split, at the cost of ending
    the partnership and, on a second confirmed betrayal, a real, visible
    hit to their own Power (`apply_reputation_penalty`), not a vague
    "reputation" score, an actual cost that shows up in the one metric
    everyone at the table already watches.

    The pot persists across rounds instead of forcibly resolving every
    round: seeded once on formation with a fixed, simple stake, then
    optionally topped up each round both partners can spare it. A top-up
    is not locked at the original seed amount forever: it's 20% of
    whichever partner has less cash that round, floored at the seed
    amount, so top-ups naturally grow larger as both partners get richer
    over the game, not a fixed number repeated every time.
    """
    for p in players:
        for ally_idx in list(p.allies):
            if ally_idx < p.idx:
                continue
            q = players[ally_idx]

            pot_entry = p.jv_pots.get(ally_idx)
            if pot_entry is None:
                if p.cash < JV_CONTRIBUTION_UNIT or q.cash < JV_CONTRIBUTION_UNIT:
                    continue
                industry = rng.choice(INDUSTRIES) if INDUSTRY_EVENTS_ENABLED else None
                pot_entry = {
                    "value": JV_CONTRIBUTION_UNIT * 2,
                    "contributed_each": JV_CONTRIBUTION_UNIT,
                    "industry": industry,
                }
                p.cash -= JV_CONTRIBUTION_UNIT
                q.cash -= JV_CONTRIBUTION_UNIT
                p.jv_pots[ally_idx] = pot_entry
                q.jv_pots[p.idx] = pot_entry
            else:
                topup = max(JV_CONTRIBUTION_UNIT, min(p.cash, q.cash) * JV_TOPUP_RATE)
                if (
                    p.cash - topup >= JV_TOPUP_CASH_BUFFER
                    and q.cash - topup >= JV_TOPUP_CASH_BUFFER
                ):
                    pot_entry["value"] += topup * 2
                    pot_entry["contributed_each"] += topup
                    p.cash -= topup
                    q.cash -= topup

            if (
                INDUSTRY_EVENTS_ENABLED
                and scenario_deltas
                and pot_entry["industry"] in scenario_deltas
            ):
                pot_entry["value"] *= 1 + scenario_deltas[pot_entry["industry"]]
            elif not INDUSTRY_EVENTS_ENABLED:
                pot_entry["value"] *= 1 + JV_GROWTH
            pot_entry["value"] = max(0.0, pot_entry["value"])
            pot = pot_entry["value"]

            p_sabotage = p.is_raider and p.raider_target_idx == q.idx
            q_sabotage = q.is_raider and q.raider_target_idx == p.idx
            p_drains = (
                (p.archetype == "Aggressor" and rng.random() < 0.3)
                or (is_final_round and rng.random() < 0.4)
                or (p_sabotage and rng.random() < 0.6)
            )
            q_drains = (
                (q.archetype == "Aggressor" and rng.random() < 0.3)
                or (is_final_round and rng.random() < 0.4)
                or (q_sabotage and rng.random() < 0.6)
            )

            if not p_drains and not q_drains:
                continue  # nobody cashes out, the pot carries into next round unchanged

            if p_drains and not q_drains:
                p_payout, q_payout = JV_DRAIN_BONUS * pot, (1 - JV_DRAIN_BONUS) * pot
                p.drain_count += 1
                q.last_attacker_idx = p.idx
            elif q_drains and not p_drains:
                q_payout, p_payout = JV_DRAIN_BONUS * pot, (1 - JV_DRAIN_BONUS) * pot
                q.drain_count += 1
                p.last_attacker_idx = q.idx
            else:
                p_payout = q_payout = 0.4 * pot
                p.drain_count += 1
                q.drain_count += 1

            p.cash += p_payout
            q.cash += q_payout
            p.round_profit += p_payout - pot_entry["contributed_each"]
            q.round_profit += q_payout - pot_entry["contributed_each"]
            del p.jv_pots[ally_idx]
            del q.jv_pots[p.idx]
            apply_reputation_penalty(p, stats)
            apply_reputation_penalty(q, stats)


PACT_BREAK_ENABLED = False  # set per-run
PACT_BREAK_PENALTY_PCT = REPUTATION_PENALTY_PCT  # same visible-Power-hit principle as a second JV betrayal, GDD.md Section 7
RAIDER_PACT_WITHHOLD_CHANCE = (
    0.5  # per round in the Conflict Phase, once allied with their own target
)


def _sever_alliance(p, q, stats):
    """Ends the one shared relationship an alliance is (GDD.md Section 9
    decided to keep the Joint Venture and Defense Pact merged, not split
    into two independent caps: Part 8's validated MAX_ALLIES=2 was tuned
    against this exact merged model, and splitting it needs a real
    re-architecture and a full retest neither open item ever justified on
    its own). Any live JV pot between them splits evenly: this is a
    no-fault severance, not a betrayal, so it never touches drain_count or
    the reputation penalty a real drain carries.
    """
    p.allies.discard(q.idx)
    q.allies.discard(p.idx)
    p.pact_posture.pop(q.idx, None)
    q.pact_posture.pop(p.idx, None)
    pot_entry = p.jv_pots.pop(q.idx, None)
    q.jv_pots.pop(p.idx, None)
    if pot_entry is not None:
        half = pot_entry["value"] / 2.0
        p.cash += half
        q.cash += half


def initiate_pact_break(p, q, stats):
    """Either partner can walk away from the shared alliance whenever they
    want (GDD.md Section 7). A covert pact costs nothing and ends
    immediately, nobody outside it knew it existed. A *declared* pact is
    deferred to the start of next round instead of ending instantly, so it
    can't be declared to inflate a defense number for one attack and
    un-declared the moment that attack resolves, and mirrors the JV
    betrayal's two-strike pattern: a first declared break costs the
    initiator nothing beyond the relationship itself, a second costs them a
    real, visible Power hit, the same principle already validated for a
    proven JV drain (Part 1, Part 14).
    """
    if not p.pact_posture.get(q.idx, False):
        _sever_alliance(p, q, stats)
        stats["covert_pact_breaks"] += 1
        return
    p.pending_pact_break = q.idx
    stats["declared_pact_breaks"] += 1


def finalize_pending_pact_breaks(players, stats):
    """Runs at the very start of each round, so a declared break initiated
    last round takes effect now, never the same round it was initiated.
    """
    for p in players:
        if p.pending_pact_break is None:
            continue
        q_idx = p.pending_pact_break
        p.pending_pact_break = None
        if q_idx not in p.allies:
            continue  # already gone, e.g. the other side broke it first
        q = players[q_idx]
        p.pact_break_count += 1
        _sever_alliance(p, q, stats)
        if p.pact_break_count == REP_TAX_THRESHOLD:
            penalty = collect_payment(p, p.total_power() * PACT_BREAK_PENALTY_PCT)
            stats["pact_break_penalties_paid"] += penalty


def consider_raider_pact_break(players, rng, is_building, stats):
    """Answers a question GDD.md Section 8.2 named but never modeled: should
    a Raider withhold Defense Pact support from their own secretly-assigned
    target? Passive under-defending has no separate representation in this
    model, defense is derived live from the ally/pact_posture relationship,
    there's no "nominally allied but secretly not helping" state, so the
    Raider's actual move is severing the relationship outright rather than
    keep propping up the very target they're trying to see fail. Skipped
    during the Building Phase: there's no defense to withhold before
    attacks exist at all.
    """
    if is_building or not PACT_BREAK_ENABLED:
        return
    for p in players:
        if not p.is_raider or p.raider_target_idx is None:
            continue
        if p.raider_target_idx not in p.allies or p.pending_pact_break is not None:
            continue
        if rng.random() < RAIDER_PACT_WITHHOLD_CHANCE:
            initiate_pact_break(p, players[p.raider_target_idx], stats)


POWER_CARDS_ENABLED = False  # set per-run
POWER_CARD_TYPES = [
    "Financier",
    "Marauder",
    "Guardian",
    "Broker",
    "Banker",
    "Insider",
    "Analyst",
]
AUDIT_COST = 5.0  # GDD.md Section 8.3: flat, not scaled to wealth, a real cost against a 20-cash starting stake
AUDIT_LIE_PENALTY_PCT = 0.15  # a caught lie costs this fraction of the liar's current Power, same figure as Section 5/7
POWER_CARD_CLAIM_CHANCE = (
    0.15  # per round, chance a player with an unused real card action attempts it
)
POWER_CARD_BLUFF_CHANCE = (
    0.05  # per round, chance a player attempts one bluffed claim this game
)
POWER_CARD_AUDIT_CHANCE = (
    0.25  # per claim, chance a random other living player audits it
)
# Five of seven cards now have a modeled, numeric effect (BALANCE_TESTING.md Parts 18, 21):
# Financier, Marauder, and Broker have clean, unconditional numbers. Banker's two halves
# (Easy Terms, Standstill) collapse to one mechanical effect, waiving the leverage risk
# premium on the player's next interest accrual, since both describe the same underlying
# benefit (cheaper debt) from different angles. Analyst's Report shifts the target's visible
# defense for the rest of the round, a real, if reinterpreted, take on "a perception shock,
# not real wealth" (the original text specified Company value, which nothing in this game's
# combat math actually reads, defense is Real Estate and cash only, see defense_power_visible).
# Guardian's block is modeled too, but reactively, at the moment an attack would land, not
# through this claim pipeline, see try_guardian_block. Still unmodeled: Analyst's Expose and
# Insider's Tip-Off, both a pure information payoff a fixed-behavior bot has no way to act on.
POWER_CARD_MODELED_ACTIONS = ("Financier", "Marauder", "Broker", "Banker", "Analyst")
ANALYST_PERCEPTION_SHOCK_PCT = 0.15  # matches the JV reputation penalty and Audit lying penalty, GDD.md Section 8.1


def assign_power_cards(players, rng):
    """Deals each player one of the 7 card types, no duplicates, up to 7
    players. Above 7 (GDD.md Section 1's range now runs to 10, past the
    original 7-card design), extra seats each get one more randomly
    repeated type: a real, named simplification, not a rules gap nobody
    noticed, a full 8th-through-10th card set is a real design task of its
    own, not a side effect of a player-count sweep. Every seat gets a real
    card either way, never left unassigned.
    """
    if not POWER_CARDS_ENABLED:
        return
    types = list(POWER_CARD_TYPES)
    n = len(players)
    if n <= len(types):
        dealt = rng.sample(types, n)
    else:
        dealt = types + [rng.choice(types) for _ in range(n - len(types))]
        rng.shuffle(dealt)
    for p, card in zip(players, dealt):
        p.power_card = card


def _resolve_power_card_action(
    claimed_card, claimant, players, rng, is_building, stats
):
    """Applies the Power/cash effect of a successfully resolved claim (a
    true claim, or a bluff nobody audited), for the three cards with a
    clean, unconditional numeric effect (see POWER_CARD_MODELED_ACTIONS).
    Returns False if the claimed card has no modeled action, or the phase
    doesn't allow it (Marauder is an attack, Conflict Phase only, matching
    every other attack in this game).
    """
    if claimed_card == "Financier":
        claimant.cash += claimant.company * 0.20
        return True
    if claimed_card == "Marauder":
        if is_building:
            return False
        candidates = [q for q in players if q.idx != claimant.idx and not q.bankrupt]
        if not candidates:
            return False
        target = max(candidates, key=lambda q: q.cash + q.company)
        if try_guardian_block(target, stats):
            return True  # the claim still resolves, the capture just doesn't
        captured = collect_payment(target, 0.10 * target.total_power())
        claimant.cash += captured
        return True
    if claimed_card == "Broker":
        if is_building:
            return False
        candidates = [q for q in players if q.idx != claimant.idx and q.cash > 0]
        if not candidates:
            return False
        target = max(candidates, key=lambda q: q.cash)
        skimmed = min(target.cash, target.cash * 0.08)
        target.cash -= skimmed
        claimant.cash += skimmed
        return True
    if claimed_card == "Banker":
        claimant.banker_waiver_pending = True
        return True
    if claimed_card == "Analyst":
        candidates = [q for q in players if q.idx != claimant.idx and not q.bankrupt]
        if not candidates:
            return False
        target = rng.choice(candidates)
        # bots don't have a read on a specific target worth shrinking or
        # inflating, so the direction is a coin flip, a real player would
        # choose deliberately (deter an attacker, or paint someone as an
        # easier mark than they are)
        direction = rng.choice((1.0, -1.0))
        target.analyst_perception_shock += direction * ANALYST_PERCEPTION_SHOCK_PCT
        return True
    return False


def try_guardian_block(target, stats):
    """Guardian's block (GDD.md Section 8.1) is reactive by design, it only
    matters at the exact moment an attack would otherwise land, which
    doesn't fit `resolve_power_card_claims`'s proactive claim/audit
    pipeline, so it's checked directly inside combat resolution instead.
    Only a genuine Guardian cardholder can use it in this pass, bluffing a
    block (claiming Guardian to save yourself, risking an audit mid-attack)
    is real texture for a future pass, not modeled here.
    """
    if not POWER_CARDS_ENABLED or target.power_card != "Guardian":
        return False
    if target.power_card_block_used:
        return False
    target.power_card_block_used = True
    stats["power_card_guardian_blocks"] += 1
    return True


def _power_card_claim_chance(p, base):
    """Individual variation on top of the flat base rate, reusing
    `declare_bias` (0.2-0.8, already governs how readily a player declares
    a Defense Pact, Section 7) rather than inventing a second trait: a
    player already modeled as bolder about public claims is bolder about
    Power Card claims too. Real per-player variation, not real strategic
    timing, see resolve_power_card_claims' docstring.
    """
    return base * (p.declare_bias / 0.5)


def _power_card_audit_chance(auditor, claimant, base):
    """A grudge (already used for attack targeting, `pick_target`) makes a
    player more likely to Audit someone who's hit them before, a real,
    if simple, "I don't trust them specifically" signal, reusing
    `grudge_bias` (0.0-0.6) rather than a flat, identical suspicion level
    for every claim regardless of history.
    """
    if auditor.grudge_bias > 0 and auditor.last_attacker_idx == claimant.idx:
        return min(1.0, base + auditor.grudge_bias * 0.3)
    return base


def resolve_power_card_claims(players, rng, is_building, stats):
    """A first simulation pass, matching the scope this file's other
    first-pass mechanics (Hidden Raider, Part 9) were given: real
    claim/bluff/audit dynamics and their real cost, not a fully faithful
    implementation of all 7 cards' distinct flavor. Each card action is a
    Declaration (GDD.md Section 8.1): any player can Audit it at
    `AUDIT_COST`, a failed Audit (the claim was true) refunds the auditor
    from the claimant, a caught lie costs the claimant `AUDIT_LIE_PENALTY_PCT`
    of their current Power and voids the claimed effect entirely, the exact
    asymmetry Section 8.3 specifies. Claim, bluff, and audit chances scale
    per-player off existing traits (`declare_bias`, `grudge_bias`) instead
    of an identical flat rate for everyone, real individual variation, still
    not real strategic bluffing (no timing based on pot size or reading who
    suspects them specifically), that's a separate, larger piece of work.
    Guardian's block is handled separately, reactively, in combat
    resolution (`try_guardian_block`), not through this claim pipeline.
    """
    if not POWER_CARDS_ENABLED:
        return
    for p in players:
        if p.bankrupt:
            continue
        claimed_card = None
        is_bluff = False
        if not p.power_card_action_used and rng.random() < _power_card_claim_chance(
            p, POWER_CARD_CLAIM_CHANCE
        ):
            claimed_card = p.power_card
        elif not p.power_card_has_bluffed and rng.random() < _power_card_claim_chance(
            p, POWER_CARD_BLUFF_CHANCE
        ):
            claimed_card = rng.choice(
                [c for c in POWER_CARD_TYPES if c != p.power_card]
            )
            is_bluff = True

        if claimed_card is None:
            continue

        auditors = [q for q in players if q.idx != p.idx and not q.bankrupt]
        auditor = None
        if auditors:
            auditor = rng.choice(auditors)
            audit_chance = _power_card_audit_chance(auditor, p, POWER_CARD_AUDIT_CHANCE)
            audited = rng.random() < audit_chance
            if not audited:
                auditor = None
        else:
            audited = False

        if audited:
            auditor.cash -= AUDIT_COST
            if is_bluff:
                penalty = collect_payment(p, p.total_power() * AUDIT_LIE_PENALTY_PCT)
                auditor.cash += min(AUDIT_COST, penalty)
                stats["power_card_lies_caught"] += 1
                stats["power_card_lie_penalties_paid"] += penalty
                p.power_card_has_bluffed = True
                continue  # a caught claim never resolves, true or false
            p.cash += AUDIT_COST  # a failed audit rewards the truthful claimant
            stats["power_card_failed_audits"] += 1

        resolved = _resolve_power_card_action(
            claimed_card, p, players, rng, is_building, stats
        )
        if claimed_card == p.power_card and not is_bluff:
            p.power_card_action_used = True
        if is_bluff:
            p.power_card_has_bluffed = True
        stats["power_card_claims"] += 1
        if resolved:
            stats["power_card_effects_resolved"] += 1


ALLIANCE_VISIBILITY_ENABLED = True


def defense_power_visible(target, players):
    """What an attacker can actually see before committing: own assets plus
    only the Defense Pacts that partner declared. Covert allies are real
    defenders at resolution but invisible here, on purpose, this is the
    mechanic that lets a target look weaker than they are. An Analyst's
    Report (GDD.md Section 8.1), when active, shifts this specifically,
    not the target's real Power, a one-round perception shock rather than
    an attack on their actual wealth, see `clear_analyst_shocks`.
    """
    if not ALLIANCE_VISIBILITY_ENABLED:
        return defense_power_of(target, players)
    dp = target.real_estate * 0.9 + target.cash * 0.3
    for ally_idx in target.allies:
        if target.pact_posture.get(ally_idx, False):
            dp += players[ally_idx].cash * 0.3
    dp *= 1.0 + target.analyst_perception_shock
    return dp * DEFENDER_TIE_BONUS


def clear_analyst_shocks(players):
    """An Analyst's Report only lasts the round it was declared in
    (GDD.md Section 8.1). Called once, after combat resolves each round.
    """
    for p in players:
        p.analyst_perception_shock = 0.0


def pick_target(attacker, beatable, players, rng):
    """Richest-beatable-target by default, grudge-driven when the trait
    fires, a secret Raider's assigned target takes priority over both when
    it's actually within reach: a saboteur cares about their real mission
    more than an ordinary grudge.
    """
    if attacker.is_raider and attacker.raider_target_idx is not None:
        raider_target = next(
            (q for q in beatable if q.idx == attacker.raider_target_idx), None
        )
        if raider_target is not None:
            return raider_target
    if (
        attacker.grudge_bias > 0
        and attacker.last_attacker_idx is not None
        and rng.random() < attacker.grudge_bias
    ):
        grudge_target = next(
            (q for q in beatable if q.idx == attacker.last_attacker_idx), None
        )
        if grudge_target is not None:
            return grudge_target
    return max(beatable, key=lambda q: q.cash + q.company)


def mark_hit(target, attacker, current_round):
    target.shielded_until_round = current_round + POST_ATTACK_SHIELD_ROUNDS
    target.last_attacker_idx = attacker.idx
    target.ever_raided = True
    if FEAR_ENABLED:
        target.hesitant_until_round = current_round + FEAR_ROUNDS


def attempt_takeovers_human(players, rng, current_round, stats, bank):
    attackers = [
        p
        for p in players
        if p.archetype in ("Aggressor", "Leverager") and p.cash > 15 and not p.bankrupt
    ]
    for attacker in attackers:
        candidates = [
            q
            for q in players
            if q.idx != attacker.idx and current_round > q.shielded_until_round
        ]
        if not candidates:
            continue

        support = 0.0
        if attacker.archetype != "SoloGrinder":
            for ally_idx in attacker.allies:
                support += players[ally_idx].cash * 0.3
        attack_power = (attacker.cash * 0.5 + support) * fatigue_multiplier(attacker)

        # attackers can only act on what's declared, covert allies are
        # invisible until an attack is actually attempted
        beatable = [
            q for q in candidates if attack_power > defense_power_visible(q, players)
        ]
        if not beatable:
            continue
        target = pick_target(attacker, beatable, players, rng)

        true_defense = defense_power_of(target, players)
        stake = attacker.cash * 0.5
        stats["attempts"] += 1
        if attack_power > true_defense and try_guardian_block(target, stats):
            penalize_failed_attacker(
                attacker, target, bank, stats, stake * ATTACK_FAIL_LOSS_PCT
            )
            stats["ambushes"] += 1
        elif attack_power > true_defense:
            captured = capture_from_target(target, TAKEOVER_CAPTURE_PCT)
            mark_hit(target, attacker, current_round)
            apply_golden_parachute(target, captured, players, stats)
            apply_windfall_tax(attacker, captured, players, stats)
            attacker.round_profit += (
                captured  # counts toward this year's income tax too
            )
            attacker.cash -= stake * 0.2
            attacker.raid_count += 1
            stats["successes"] += 1
        else:
            penalize_failed_attacker(
                attacker, target, bank, stats, stake * ATTACK_FAIL_LOSS_PCT
            )
            stats["ambushes"] += 1


def attempt_counter_attacks_human(
    players, rng, current_round, already_joined_this_round, stats, bank
):
    """Anyone can dogpile a runaway leader; bandwagon-biased players commit harder
    once someone else has already gone after the same target this round.

    A leader who kept their Defense Pacts covert can look weaker than they
    really are, this is the case that matters most for validating the
    declare-to-reinforce fix: does hiding behind an undeclared alliance let a
    runaway leader dodge the anti-snowball mechanic the whole design depends on?
    """
    ranked = sorted(players, key=lambda p: p.total_power(), reverse=True)
    leader = ranked[0]
    if len(ranked) < 2:
        return
    second_power = max(1.0, ranked[1].total_power())
    if leader.total_power() < second_power * LEADER_THREATENED_MARGIN:
        return
    if current_round <= leader.shielded_until_round:
        return

    already_hit = leader.idx in already_joined_this_round
    challengers = [
        p
        for p in players
        if p.idx != leader.idx
        and p.archetype not in ("Aggressor", "Leverager")
        and p.cash > 10
        and not p.bankrupt
    ]
    leader_visible_defense = defense_power_visible(leader, players)
    for challenger in challengers:
        if leader.bankrupt:
            return  # already brought down this round, nothing left to pile onto
        support = sum(players[a].cash * 0.3 for a in challenger.allies)
        bandwagon_boost = challenger.bandwagon_bias if already_hit else 0.0
        mobilize_rate = 0.15 + bandwagon_boost * 0.15
        mobilized = challenger.cash * 0.4 + challenger.company * mobilize_rate
        attack_power = mobilized + support
        if attack_power <= leader_visible_defense:
            # not enough to join the pile-on: sell some Real Estate to try
            # to close the gap, a real tactical trade, safety for offense,
            # right now. Testing showed a narrow "only if very close"
            # trigger almost never fires with these bots' deterministic
            # cash allocation (they're either clearly capable or clearly
            # not), so this tries liquidating whenever short, not just
            # when the gap is small, capped by TACTICAL_LIQUIDATION_CAP so
            # it isn't an unconditional fire sale
            shortfall = min(
                leader_visible_defense - attack_power,
                challenger.real_estate * TACTICAL_LIQUIDATION_CAP * 0.4,
            )
            liquidate_real_estate_for_attack(challenger, shortfall)
            mobilized = challenger.cash * 0.4 + challenger.company * mobilize_rate
            attack_power = mobilized + support
        if attack_power <= leader_visible_defense:
            continue  # looks unbeatable from here, a real challenger wouldn't even try
        # true defense is recomputed each time, a leader weakened by an
        # earlier hit this same round is a softer target for the next
        # challenger, a coalition finishes the job in one round instead of
        # needing several separate rounds to grind them down
        true_defense = defense_power_of(leader, players)
        stats["counter_attempts"] += 1
        if attack_power > true_defense and try_guardian_block(leader, stats):
            penalize_failed_attacker(
                challenger,
                leader,
                bank,
                stats,
                mobilized * ATTACK_FAIL_LOSS_PCT * 0.3,
                fallback_attr="company",
            )
            stats["counter_ambushes"] += 1
        elif attack_power > true_defense:
            # a coordinated pile-on hits harder than a lone opportunist's
            # raid, not the same amount: Finding 5's original fix capped
            # the runaway snowball but left the corrective mechanic barely
            # winning on average (405.9 vs 401.3, a 1.1% margin, see
            # BALANCE_TESTING.md Part 6), this gives the "gang up on the
            # leader" mechanic real teeth instead of just parity
            captured = capture_from_target(leader, COUNTER_ATTACK_CAPTURE_PCT)
            mark_hit(leader, challenger, current_round)
            apply_golden_parachute(leader, captured, players, stats)
            challenger.captured += captured
            # unlike the old windfall tax (exempted here, see
            # apply_windfall_tax's docstring for why), the unified income
            # tax applies uniformly, per direct instruction: real income
            # tax doesn't carve out exemptions for who earned the money, it
            # taxes everything earned that year, the same way for everyone
            challenger.round_profit += captured
            challenger.company -= mobilized * 0.2
            already_joined_this_round.add(leader.idx)
            already_hit = True
            stats["counter_successes"] += 1
        else:
            penalize_failed_attacker(
                challenger,
                leader,
                bank,
                stats,
                mobilized * ATTACK_FAIL_LOSS_PCT * 0.3,
                fallback_attr="company",
            )
            stats["counter_ambushes"] += 1
            stats["leader_dodged_via_covert"] += 1


RAIDER_ENABLED = False  # set per-run
RAIDER_RATIO = (
    1 / 5.5
)  # roughly 1 Raider per 5-6 players, a real minority, not half the table


def assign_raiders(players, rng):
    """A minority of players are secretly Raiders: their real win condition
    is that one assigned target fails (bankrupt, or well below the table
    average) by game end, invisible to everyone playing to maximize their
    own Power. Needs at least 4 players for even one Raider to make sense
    (GDD.md's stated range).
    """
    if not RAIDER_ENABLED or len(players) < 4:
        return
    n_raiders = max(1, round(len(players) * RAIDER_RATIO))
    raider_pool = rng.sample(players, min(n_raiders, len(players)))
    for raider in raider_pool:
        others = [q for q in players if q.idx != raider.idx]
        target = rng.choice(others)
        raider.is_raider = True
        raider.raider_target_idx = target.idx


def raider_succeeded(raider, players):
    """A Raider's real win: their target ended the game failed, either
    bankrupt outright or well below the table's average Power, a company
    that quietly withered isn't "failed" by accident, it's still a win for
    the Raider who steered it there.
    """
    if raider.raider_target_idx is None:
        return False
    target = players[raider.raider_target_idx]
    if target.bankrupt:
        return True
    avg_power = sum(p.total_power() for p in players) / len(players)
    return target.total_power() < avg_power * 0.5


EXTENDED_ARCHETYPES = (
    ARCHETYPES
    + [
        "Speculator",
        "Prepper",
        "Operator",
        "Momentum",
    ]
)  # the 6 originals plus four built for 8-10 player pods (BALANCE_TESTING.md Parts 17, 22)


def roster_for(n, rng):
    """Builds an archetype roster for n players. Up to 6, the original
    pod. At 7, Casual fills the extra seat, matching every player-count
    sweep this file has run historically. Above 7, four more genuinely
    distinct identities (Speculator, Prepper, Operator, Momentum, see
    their allocation functions above) fill seats 8 through 10, so a
    larger table isn't just padded with duplicate first-timers: 9 and 10
    players no longer need a single repeated Casual at all.
    """
    base = list(ARCHETYPES)
    if n <= len(base):
        # A random n-of-6 subset, not a fixed prefix: the old `base[:n]`
        # meant every 3-player game got the identical ["Diversifier",
        # "Turtle", "Aggressor"] with no Socialite at all, and every
        # 4-player game got the identical four with no SoloGrinder or
        # Leverager, ever. That's not a fair read of what an arbitrary
        # small table looks like, it's always the same narrow slice.
        return rng.sample(base, n)
    if n == len(base) + 1:
        return base + ["Casual"]
    extended = EXTENDED_ARCHETYPES + ["Casual"] * max(0, n - len(EXTENDED_ARCHETYPES))
    return extended[:n]


RAID_FATIGUE_PENALTY = 0.5  # attack power lost per prior successful raid this game, see __main__ for the sweep that picked this


def fatigue_multiplier(p):
    """Each successful takeover an attacker has already landed this game
    makes their next one harder, representing rivals pricing in a known
    predator (better security spend, wary partners) rather than treating
    every raid as a fresh, unpunished opportunity.

    Mirrors the reputation tax already validated for Joint Ventures in Part
    1 (two proven drains cost you easy income and worse terms), applied to
    the takeover side instead. Tried first as a flat tax on whoever
    currently held the lead, that punished Socialite and Turtle far more
    than Aggressor, since Aggressor keeps most income as untaxed liquid
    cash. This targets the repeat behavior directly instead of a proxy for
    it.
    """
    if RAID_FATIGUE_PENALTY <= 0:
        return 1.0
    return max(0.25, 1.0 - RAID_FATIGUE_PENALTY * p.raid_count)


CO_FOUNDER_ENABLED = False  # set per-run
CO_FOUNDER_RE_NUDGE = 0.10  # fraction of the host's cash the co-founder redirects to Real Estate each round
CO_FOUNDER_EQUITY_RATE = 0.07  # co-founder's live phantom-equity share of the host's Company; see __main__ sweep
CO_FOUNDER_BUYOUT_PREMIUM = (
    1.2  # a host buying the co-founder out pays 20% over the equity's current value
)
CO_FOUNDER_BUYOUT_CASH_MULTIPLE = 1.2  # a host only offers a buyout once cash comfortably clears the cost; see __main__ sweep
CO_FOUNDER_PARACHUTE_PCT = (
    0.20  # co-founder's cut of captured value if their host gets taken over
)


def assign_co_founders(players, rng):
    """A newly-broke player can be recruited as a co-founder by a solvent
    host without one already, a real ongoing role instead of a one-time
    label pick, caught in review: "who do I back" wasn't actually giving a
    broke player anything to do, they still just sat there. What the host
    gains for taking one on isn't a free income bonus (a first version did
    that, and it created a real perverse incentive: profiting directly
    from a player losing, exactly backwards for what this fix was meant
    to solve). What the host actually gets is real, unpaid help managing
    risk (`apply_co_founder_influence`'s Real Estate steering), at the
    cost of giving up equity. What the co-founder gets is the actual hook:
    a real, growing stake (`co_founder_equity`) in someone else's success,
    a path back to being a solvent, independent player again if the host
    ever buys them out, and a payout of their own if the host gets taken
    over instead (see `apply_golden_parachute`), not just a favor with
    nothing in it for them.
    """
    if not CO_FOUNDER_ENABLED:
        return
    hosts_taken = {q.co_founder_of for q in players if q.co_founder_of is not None}
    for p in players:
        if not p.is_broke() or p.co_founder_of is not None:
            continue
        candidates = [
            q
            for q in players
            if q.idx != p.idx and not q.is_broke() and q.idx not in hosts_taken
        ]
        if candidates:
            # deliberately random, not "richest available": preferring the
            # richest host would concentrate co-founder equity in whoever's
            # already leading, the exact snowball-reinforcing pattern this
            # session kept finding and fixing in other mechanics
            host = rng.choice(candidates)
            p.co_founder_of = host.idx
            hosts_taken.add(host.idx)


def apply_co_founder_influence(players, stats):
    """The co-founder's actual, repeated job: steering some of the host's
    cash toward Real Estate, a real risk-management voice a solo founder
    doesn't have. In exchange, their equity stake is marked to the host's
    current Company value every round, a real number they're actually
    watching grow (or shrink) alongside the host's fortunes, not a static
    label. Once the host can comfortably afford it, they can buy the
    co-founder out entirely: the co-founder gets a genuine cash return and
    is free again, either to be recruited elsewhere or to start rebuilding
    independently with real capital in hand, a real comeback path instead
    of a permanent sidelined role.
    """
    if not CO_FOUNDER_ENABLED:
        return
    for p in players:
        if p.co_founder_of is None:
            continue
        host = players[p.co_founder_of]
        if host.bankrupt or host.cash <= 0:
            p.co_founder_of = (
                None  # the company they co-ran folded, their equity is worthless
            )
            p.co_founder_equity = 0.0
            continue

        nudge = min(host.cash * CO_FOUNDER_RE_NUDGE, host.cash)
        host.cash -= nudge
        host.real_estate += nudge
        stats["co_founder_re_nudged"] += nudge

        p.co_founder_equity = host.company * CO_FOUNDER_EQUITY_RATE
        buyout_cost = p.co_founder_equity * CO_FOUNDER_BUYOUT_PREMIUM
        if host.cash > buyout_cost * CO_FOUNDER_BUYOUT_CASH_MULTIPLE:
            host.cash -= buyout_cost
            p.cash += buyout_cost
            p.round_profit += buyout_cost
            p.co_founder_of = None
            p.co_founder_equity = 0.0
            stats["co_founder_buyouts"] += 1
            stats["co_founder_buyout_volume"] += buyout_cost


def apply_golden_parachute(target, captured, players, stats):
    """If a player with an active co-founder gets successfully taken over,
    the co-founder's equity doesn't just evaporate the way it would in an
    organic bankruptcy, someone else profited directly from the host's
    fall, so the co-founder gets a real severance cut of exactly what was
    captured, real cash, immediately, and is freed to be recruited again.
    The direct answer to "why would a co-founder want to attach themselves
    to someone who might get raided": because even the downside case pays
    them something, it isn't a total loss the way it is for the attacker's
    victim.
    """
    if not CO_FOUNDER_ENABLED:
        return
    for p in players:
        if p.co_founder_of == target.idx:
            payout = captured * CO_FOUNDER_PARACHUTE_PCT
            p.cash += payout
            p.round_profit += payout
            p.co_founder_of = None
            p.co_founder_equity = 0.0
            stats["co_founder_parachutes_paid"] += payout


def assign_ghost_backing(players, rng):
    """The fallback for a broke player nobody has recruited as a
    co-founder: pick a living player to back.

    Deliberately not a financial stake: no cut, no transfer, nothing taken
    from the living player they back. It's a social/informational choice
    with a real, if smaller, payoff, see `determine_winner`'s tiebreak.
    Prefers an existing ally if one is still solvent, otherwise backs
    whoever currently holds the most Power, the same "who looks likely to
    keep winning" read a real spectator would make.
    """
    for p in players:
        if not p.is_broke() or p.backing_idx is not None or p.co_founder_of is not None:
            continue
        allied_candidates = [players[a] for a in p.allies if not players[a].is_broke()]
        if allied_candidates:
            p.backing_idx = rng.choice(allied_candidates).idx
        else:
            solvent = [q for q in players if q.idx != p.idx and not q.is_broke()]
            if solvent:
                p.backing_idx = max(solvent, key=lambda q: q.total_power()).idx


WIN_TIE_EPSILON = (
    0.5  # power difference this small counts as a tie for the Board Observer vote
)


def determine_winner(players):
    """Highest total Power wins, ties broken by Board Observer votes.

    This is the only place a Board Observer's backing choice touches the
    outcome: it's a tiebreaker for the final-round vote GDD.md Section 8.4
    already promised, not an ongoing financial mechanic.
    """
    ranked = sorted(players, key=lambda p: p.total_power(), reverse=True)
    if (
        len(ranked) < 2
        or ranked[0].total_power() - ranked[1].total_power() > WIN_TIE_EPSILON
    ):
        return ranked[0]
    tied = [
        p
        for p in ranked
        if ranked[0].total_power() - p.total_power() <= WIN_TIE_EPSILON
    ]
    votes = {p.idx: 0 for p in tied}
    for ghost in players:
        if ghost.backing_idx in votes:
            votes[ghost.backing_idx] += 1
    return max(tied, key=lambda p: votes[p.idx])


BANK_POOL_PER_PLAYER = (
    100.0  # matches one player's starting capital (20 cash + 80 company)
)


class Bank:
    """The actual source of every loan, and the sink for windfall tax revenue.

    Without this, `allocate()`'s Leverager branch materializes loan cash out
    of nothing, no source, no sink, which breaks conservation: cash a player
    borrows has to come from somewhere finite, the way it does from a real
    bank's balance sheet, and other players lending directly (not yet
    modeled here) would be a second, costlier source instead of an infinite
    one.

    Pool scales with player count (one starting capital's worth per seat at
    the table), a defensible starting point, not a validated one: this
    six-archetype pod only ever has one Leverager borrowing at a time, so it
    understates how tight credit would get in a real game where several
    human players might all lean on loans at once, especially late-game.
    Needs retesting once borrowing isn't restricted to a single archetype.
    """

    def __init__(self, pool):
        self.pool = pool


def enforce_bank_capacity(p, debt_before, bank, stats):
    """Caps how much of a round's loan the Bank can actually fund.

    Leverager's own allocate() logic already decided how big a loan to take
    and spent it (added to company/cash); this reconciles that against the
    Bank's remaining pool after the fact, clawing back the unfunded portion
    proportionally from wherever it went (Leverager splits new cash 70%
    company / 30% cash) if the Bank can't cover the full amount, a real
    credit crunch, not just a rule on paper.
    """
    loan_taken = p.debt - debt_before
    if loan_taken <= 0:
        return
    if loan_taken <= bank.pool:
        bank.pool -= loan_taken
        return
    shortfall = loan_taken - max(0.0, bank.pool)
    p.debt -= shortfall
    p.company -= shortfall * 0.7
    p.cash -= shortfall * 0.3
    bank.pool = 0.0
    stats["bank_loans_denied"] += 1
    stats["bank_shortfall_total"] += shortfall


WINDFALL_TAX_BRACKETS = [
    (150.0, 0.0),
    (300.0, 0.15),
    (450.0, 0.25),
    (float("inf"), 0.35),
]
WINDFALL_TAX_ENABLED = (
    False  # set per-run; see __main__ for the comparison against raid fatigue
)


def windfall_tax_rate(power_after_capture):
    for threshold, rate in WINDFALL_TAX_BRACKETS:
        if power_after_capture <= threshold:
            return rate
    return WINDFALL_TAX_BRACKETS[-1][1]


def apply_windfall_tax(attacker, gross_captured, players, stats):
    """A progressive capital-gains-style tax on a successful takeover's
    proceeds, scaled by the attacker's own resulting wealth bracket, not by
    who's "the leader" (that comparison-based approach backfired badly, see
    BALANCE_TESTING.md Part 3, Finding 4).

    First version routed the tax into the Bank's pool, which made things
    worse (Aggressor's win rate went from 72.7% to 99.9%), because the pool
    is never actually stressed, so the tax just deleted value from the game
    with no offsetting benefit, and it hit Socialite's counter-attack
    captures exactly as hard as Aggressor's raids, weakening the one
    mechanism that checks a runaway leader more than the problem itself.
    Real progressive taxation redistributes, it doesn't vanish: this splits
    the tax evenly across every other living player instead, an explicit
    "the table benefits when someone cashes in big" transfer.
    """
    if not WINDFALL_TAX_ENABLED:
        attacker.captured += gross_captured
        return
    rate = windfall_tax_rate(attacker.total_power() + gross_captured)
    tax = gross_captured * rate
    attacker.captured += gross_captured - tax
    stats["windfall_tax_collected"] += tax
    recipients = [q for q in players if q.idx != attacker.idx and not q.is_broke()]
    if recipients and tax > 0:
        share = tax / len(recipients)
        for q in recipients:
            q.cash += share


# Marginal slabs on total Power, scaled from Indian income tax's actual
# structure (0 / 5 / 10 / 15 / 20 / 30%) down to this game's Power range.
# Unlike WINDFALL_TAX_BRACKETS above, this is properly marginal: only the
# slice of Power inside each band is taxed at that band's rate, not the
# whole amount at whichever band you land in.
NET_WORTH_TAX_BRACKETS = [
    (100.0, 0.00),
    (200.0, 0.05),
    (300.0, 0.10),
    (400.0, 0.20),
    (float("inf"), 0.30),
]
NET_WORTH_TAX_ENABLED = False  # set per-run; see __main__ for the comparison


def marginal_tax(power, brackets):
    """Real slab-style tax: each slice of `power` is taxed at its own
    bracket's rate, a person earning just past a threshold only pays the
    higher rate on the sliver above it, not their entire income.
    """
    tax = 0.0
    lower = 0.0
    for threshold, rate in brackets:
        if power <= lower:
            break
        taxable = min(power, threshold) - lower
        tax += taxable * rate
        lower = threshold
    return tax


def collect_net_worth_tax(p):
    """Charges one player's marginal tax bill, in cash first, forcing a
    proportional liquidation of company and Real Estate if cash alone can't
    cover it, the real-world "asset rich, cash poor" problem a wealth tax
    actually creates. Returns how much was actually collected.
    """
    if p.is_broke():
        return 0.0
    tax = marginal_tax(p.total_power(), NET_WORTH_TAX_BRACKETS)
    if tax <= 0:
        return 0.0
    if p.cash >= tax:
        p.cash -= tax
        return tax
    remainder = tax - p.cash
    collected = p.cash
    p.cash = 0.0
    liquidatable = p.company + p.real_estate
    if liquidatable > 0:
        forced_fraction = min(1.0, remainder / liquidatable)
        p.company -= p.company * forced_fraction
        p.real_estate -= p.real_estate * forced_fraction
        collected += min(remainder, liquidatable)
    return collected


def apply_net_worth_tax(players, stats):
    """Taxes every living player's total Power each round and splits the
    proceeds evenly among them, explicit wealth redistribution, not a
    one-time event tax. Applies to everyone based on current wealth, not
    just to attackers after a raid, so it can't reproduce the windfall
    tax's failure mode of cushioning a raid's own victim specifically.
    """
    if not NET_WORTH_TAX_ENABLED:
        return
    total_collected = sum(collect_net_worth_tax(p) for p in players)
    stats["net_worth_tax_collected"] += total_collected
    recipients = [p for p in players if not p.is_broke()]
    if recipients and total_collected > 0:
        share = total_collected / len(recipients)
        for p in recipients:
            p.cash += share


# Marginal slabs on a player's TOTAL profit for the round (a round is a
# year, per direct instruction): passive company/Real Estate income,
# capture proceeds from a successful raid or counter-attack, and Joint
# Venture proceeds, all combined, the same as a real income tax return
# covers every income source together, not one stream at a time.
INCOME_TAX_BRACKETS = [
    (5.0, 0.00),
    (15.0, 0.05),
    (30.0, 0.10),
    (50.0, 0.15),
    (float("inf"), 0.20),
]
INCOME_TAX_ENABLED = False  # set per-run

REAL_ESTATE_LIQUIDATION_HAIRCUT = (
    0.85  # selling in a hurry doesn't fetch full market value
)
REAL_ESTATE_PURCHASE_COST = (
    0.97  # buying isn't free either, just cheaper friction than a distress sale
)
REAL_ESTATE_PURCHASE_COST_ENABLED = False  # set per-run


def apply_real_estate_purchase_cost(p, re_before):
    """Buying Real Estate has real closing costs too, smaller than the 15%
    distress-sale haircut, but not zero. Without this, buying was fully
    frictionless while selling wasn't, an asymmetry nobody had actually
    decided on, it just fell out of the sell-side mechanic being built
    first. This makes entering and exiting the position both cost
    something, so Real Estate is a real long-term commitment on both ends,
    not a one-way-free, one-way-costly lever.
    """
    if not REAL_ESTATE_PURCHASE_COST_ENABLED:
        return
    added = p.real_estate - re_before
    if added > 0:
        p.real_estate = re_before + added * REAL_ESTATE_PURCHASE_COST


def liquidate_real_estate(p, cash_needed):
    """Sells off Real Estate to raise cash, at a haircut for a forced or
    urgent sale, real estate is otherwise the one asset nothing can touch
    (GDD.md Section 6), this is the one legitimate way a player gives up
    some of that safety for liquidity, whether by choice or because a tax
    bill demands it. Returns how much cash was actually raised.
    """
    if p.real_estate <= 0 or cash_needed <= 0:
        return 0.0
    re_to_sell = min(p.real_estate, cash_needed / REAL_ESTATE_LIQUIDATION_HAIRCUT)
    p.real_estate -= re_to_sell
    raised = re_to_sell * REAL_ESTATE_LIQUIDATION_HAIRCUT
    p.cash += raised
    return raised


GOLD_LIQUIDATION_HAIRCUT = (
    0.95  # Gold is deliberately the *liquid* hedge (GDD.md Section 5), forced
)
# liquidation costs far less friction than Real Estate's 15%, the illiquid asset by design


def liquidate_gold(p, cash_needed):
    """Sells off Gold to raise cash, a much smaller haircut than Real
    Estate's: Gold's entire identity is being the flight-to-safety asset
    that's easy to convert back to cash in a crunch, a real distress sale
    of illiquid property is not the same transaction as selling bullion.
    Returns how much cash was actually raised.
    """
    if p.gold <= 0 or cash_needed <= 0:
        return 0.0
    gold_to_sell = min(p.gold, cash_needed / GOLD_LIQUIDATION_HAIRCUT)
    p.gold -= gold_to_sell
    raised = gold_to_sell * GOLD_LIQUIDATION_HAIRCUT
    p.cash += raised
    return raised


def collect_payment(p, amount_needed):
    """Raises `amount_needed` in actual cash from a player: cash first, then
    Company, then Real Estate, then Gold, each at its own liquidation
    haircut if still short. Shared by every mechanic that forces a payment:
    a takeover capturing a share of total wealth (not just liquid
    holdings), a failed attacker's penalty, an Audit's lying penalty, and
    the Defense Pact breakup penalty. Returns how much was actually
    collected, capped by what the player has.
    """
    paid = min(p.cash, amount_needed)
    p.cash -= paid
    remaining = amount_needed - paid
    if remaining > 0 and p.company > 0:
        from_company = min(p.company, remaining)
        p.company -= from_company
        paid += from_company
        remaining -= from_company
    if remaining > 0 and p.real_estate > 0:
        raised = liquidate_real_estate(p, remaining)  # adds `raised` to p.cash
        take = min(raised, p.cash)
        p.cash -= take
        paid += take
        remaining -= take
    if remaining > 0 and p.gold > 0:
        raised = liquidate_gold(p, remaining)  # adds `raised` to p.cash
        take = min(raised, p.cash)
        p.cash -= take
        paid += take
    return paid


TOTAL_WEALTH_CAPTURE_ENABLED = False  # set per-run


def capture_from_target(target, capture_pct):
    """How much a successful takeover or counter-attack actually extracts
    from the target, at the given capture percentage (takeovers and
    counter-attacks use different rates, see TAKEOVER_CAPTURE_PCT and
    COUNTER_ATTACK_CAPTURE_PCT).

    Two modes. Original: capture_pct of liquid (cash + Company) value
    only, Real Estate untouched, the "safe harbor" design. New, per direct
    instruction: capture_pct of the target's *total* wealth, cash first,
    then Company, then Real Estate (at the standard liquidation haircut)
    if cash and Company together aren't enough. Real Estate stops being
    fully protected once a big enough capture demands it, a real change
    to a previously load-bearing design pillar, tested both ways.
    """
    if TOTAL_WEALTH_CAPTURE_ENABLED:
        owed = capture_pct * target.total_power()
        return collect_payment(target, owed)
    captured = capture_pct * (target.cash + target.company)
    target.cash = max(0.0, target.cash - captured * 0.5)
    target.company = max(0.0, target.company - captured * 0.5)
    return captured


DEFENDER_REWARD_ENABLED = False  # set per-run


def penalize_failed_attacker(
    attacker, target, bank, stats, penalty, fallback_attr="cash"
):
    """A failed attack still costs the attacker their committed stake,
    `penalty` is the pre-computed amount (callers use different formulas
    for a takeover attempt vs. a counter-attack pile-on attempt, and the
    original design docked a different resource for each: cash for a
    takeover, Company for a counter-attack, `fallback_attr` preserves that
    exactly when the new mechanic is off).

    Original: the lost stake just vanishes. New, per direct instruction:
    it's collected as real cash (liquidating the attacker's other assets
    if cash alone isn't enough) and split, half to the defender who just
    successfully protected themselves, a real reward for defending, not
    just an absence of loss, half to the Bank.
    """
    if not DEFENDER_REWARD_ENABLED:
        setattr(attacker, fallback_attr, getattr(attacker, fallback_attr) - penalty)
        return
    collected = collect_payment(attacker, penalty)
    target.cash += collected * 0.5
    bank.pool += collected * 0.5
    stats["defender_rewards_paid"] += collected * 0.5


TACTICAL_LIQUIDATION_ENABLED = False  # set per-run
TACTICAL_LIQUIDATION_CAP = (
    0.5  # sells at most half of Real Estate to fund a single pile-on attempt
)


def liquidate_real_estate_for_attack(p, power_shortfall):
    """A player who's close to being able to join a pile-on, but not quite,
    sells just enough Real Estate to close the gap, a deliberate mid-battle
    trade of safety for offense. Mobilized attack power is 40% of cash, so
    raising cash by X raises attack power by 0.4X, sized accordingly with a
    small margin so the sale is actually enough to tip the fight.
    """
    if not TACTICAL_LIQUIDATION_ENABLED or power_shortfall <= 0:
        return 0.0
    cash_needed = (power_shortfall / 0.4) * 1.05
    return liquidate_real_estate(p, cash_needed)


VOLUNTARY_LIQUIDATION_CASH_THRESHOLD = DISENGAGED_CASH_THRESHOLD
VOLUNTARY_LIQUIDATION_FRACTION = (
    0.20  # sells a slice, not everything, keeps some safety net
)
VOLUNTARY_LIQUIDATION_ENABLED = False  # set per-run


def consider_voluntary_liquidation(players, stats):
    """A player low on cash but sitting on Real Estate sells off a slice of
    it rather than going broke with a paper fortune they can't spend.

    This is the direct answer to "if Real Estate can't be touched by an
    attacker, what's a player's own way to turn it into cash when they need
    some": they choose to give up some of that safety themselves, at the
    same haircut a forced sale takes, real estate stops being a
    set-and-forget choice and becomes an active liquidity decision.
    """
    if not VOLUNTARY_LIQUIDATION_ENABLED:
        return
    for p in players:
        if (
            p.bankrupt
            or p.cash >= VOLUNTARY_LIQUIDATION_CASH_THRESHOLD
            or p.real_estate <= 0
        ):
            continue
        re_to_sell = p.real_estate * VOLUNTARY_LIQUIDATION_FRACTION
        p.real_estate -= re_to_sell
        raised = re_to_sell * REAL_ESTATE_LIQUIDATION_HAIRCUT
        p.cash += raised
        stats["voluntary_re_liquidations"] += 1
        stats["voluntary_re_liquidation_volume"] += raised


def apply_income_tax(p, bank, stats):
    """Taxes this round's total profit once, at the end of the round, after
    every income source has been added to `round_profit`, matching how
    real income tax is assessed once a year on everything earned together,
    not withheld separately per stream. That's also the direct fix for
    Aggressor barely paying anything under the first version of this tax:
    that version only taxed passive company/Real Estate income, which
    Aggressor generates almost none of, their actual income is raiding,
    and raiding wasn't in the tax base at all.

    Routes proceeds to the Bank, not to player redistribution: every
    redistribution-to-players design tried in this file backfired (see
    BALANCE_TESTING.md Part 5 and Part 6), the recipient-pool problem is
    structural, not specific to one tax base.
    """
    if not INCOME_TAX_ENABLED or p.round_profit <= 0:
        p.round_profit = 0.0
        return
    tax = marginal_tax(p.round_profit, INCOME_TAX_BRACKETS)
    p.round_profit = 0.0
    if tax <= 0:
        return
    if p.cash < tax:
        liquidate_real_estate(p, tax - p.cash)
    paid = min(tax, p.cash)
    p.cash -= paid
    bank.pool += paid
    stats["income_tax_collected"] += paid


IDLE_CASH_EROSION_RATE = 0.03  # 3%/round, real inflation eating idle purchasing power
IDLE_CASH_EROSION_THRESHOLD = 10.0  # protects small working balances from erosion
IDLE_CASH_EROSION_ENABLED = False  # set per-run


def erode_idle_cash(players, stats):
    """Cash sitting uninvested loses real value every round, it doesn't
    flow anywhere, inflation is a general price-level effect, not a
    transfer to anyone, same conservation logic as the windfall tax
    reaching a dead end when it tried to redistribute: this one simply
    doesn't redistribute, on purpose.

    Only `p.cash` erodes, not Company, Real Estate, stocks, or
    `p.bank_deposit`, because those are the assets that actually exist to
    beat inflation, that is the entire reason a real economy has
    investment instead of everyone holding currency. `bank_deposit` is
    exempt for the same reason a savings account is: it is not idle, it
    is earning BANK_DEPOSIT_RATE (see `apply_bank_deposit_interest`),
    which is the intended escape hatch from this mechanic. The threshold
    is not a special exemption for erosion specifically, it is a
    floor of minimal working cash no one should be taxed for holding,
    same idea as a tax-free personal allowance.
    """
    if not IDLE_CASH_EROSION_ENABLED:
        return
    for p in players:
        if p.cash > IDLE_CASH_EROSION_THRESHOLD:
            erosion = (p.cash - IDLE_CASH_EROSION_THRESHOLD) * IDLE_CASH_EROSION_RATE
            p.cash -= erosion
            stats["idle_cash_eroded"] += erosion


BANK_DEPOSIT_RATE = (
    0.04  # modest and safe: below the Bank's own loan rates and below active investing
)
BANK_DEPOSIT_BUFFER = (
    IDLE_CASH_EROSION_THRESHOLD  # same working-cash floor idle cash erosion protects
)
BANK_DEPOSIT_ENABLED = False  # set per-run


def manage_bank_deposits(players, stats):
    """The rational response to holding cash above the working buffer:
    park it with the Bank for a safe return instead of either letting it
    erode (if IDLE_CASH_EROSION_ENABLED) or just sitting there earning
    nothing. Draws back down automatically when cash runs short, a
    person dips into savings before reaching for a loan, not after.
    """
    if not BANK_DEPOSIT_ENABLED:
        return
    for p in players:
        if p.cash > BANK_DEPOSIT_BUFFER:
            deposit = p.cash - BANK_DEPOSIT_BUFFER
            p.cash -= deposit
            p.bank_deposit += deposit
        elif p.cash < BANK_DEPOSIT_BUFFER and p.bank_deposit > 0:
            withdrawal = min(p.bank_deposit, BANK_DEPOSIT_BUFFER - p.cash)
            p.bank_deposit -= withdrawal
            p.cash += withdrawal


def apply_bank_deposit_interest(p, stats):
    """Pays BANK_DEPOSIT_RATE on whatever is parked with the Bank, same
    round-by-round cadence as Company and Real Estate income, and, like
    those, counted in `round_profit` so it is taxed as income too, a
    deposit is a real income source, not a loophole.
    """
    if not BANK_DEPOSIT_ENABLED or p.bank_deposit <= 0:
        return
    interest = p.bank_deposit * BANK_DEPOSIT_RATE
    p.bank_deposit += interest
    p.round_profit += interest
    stats["bank_deposit_interest_paid"] += interest


PEER_LOAN_RATE = 0.20  # flat, well above the Bank's ~8-20%, the real premium for unsecured peer credit
PEER_LOAN_NEED_THRESHOLD = DISENGAGED_CASH_THRESHOLD * 3
PEER_LOAN_MIN_LENDER_CASH = 20.0
PEER_LOAN_LENDER_RESERVE = (
    15.0  # a lender keeps at least this much, enough to still act themselves
)
PEER_LOAN_LEND_FRACTION = (
    0.10  # was 0.3; see __main__ for the sweep, 0.2 and above still break balance
)
PEER_LOANS_ENABLED = False  # set per-run


def offer_peer_loans(players, rng, stats):
    """A solvent ally lends directly to a cash-strapped ally, at a real
    premium over Bank rates. First pass: no Declare/Audit posture yet
    (unlike Defense Pacts, see GDD.md Section 7), every peer loan is
    effectively covert for now, that's a natural extension once this core
    mechanic is validated, not built here.

    Two fixes layered on top of the original design, found in that order:
    1. Excludes anyone who's ever been successfully raided this game (a
       narrower "still inside the 2-round Post-Attack Shield" version was
       tried first and barely moved the needle, a victim is still poor the
       round the shield expires). Original problem: peer loans were mostly
       rescuing Aggressor's own recent victims, refilling their cash and
       letting Aggressor farm them again sooner than they'd have recovered
       unassisted.
    2. Caps how much of their own cash a lender gives away
       (`PEER_LOAN_LEND_FRACTION`, down from 30% to 10%). Fix 1 alone
       didn't change the outcome at all, tracing actual cash flows found
       the real mechanism was never about the borrower, it was the lender:
       only Socialite (the one archetype that both forms alliances and
       keeps spare cash) ever lends, and giving away 30% of their own cash
       every time directly drained the exact war chest their win condition
       depends on for counter-attacks. Lending shouldn't cost you your own
       ability to fight back. 20% and above still broke the baseline in
       testing; 10% and below hold clean.
    """
    if not PEER_LOANS_ENABLED:
        return
    for lender in players:
        if (
            lender.is_broke()
            or not lender.allies
            or lender.cash < PEER_LOAN_MIN_LENDER_CASH
        ):
            continue
        needy_allies = [
            players[a]
            for a in lender.allies
            if not players[a].bankrupt
            and players[a].cash < PEER_LOAN_NEED_THRESHOLD
            and not players[a].ever_raided
        ]
        if not needy_allies:
            continue
        borrower = rng.choice(needy_allies)
        lendable = max(0.0, lender.cash - PEER_LOAN_LENDER_RESERVE)
        loan = min(lender.cash * PEER_LOAN_LEND_FRACTION, lendable)
        if loan <= 0:
            continue
        lender.cash -= loan
        lender.receivables[borrower.idx] = (
            lender.receivables.get(borrower.idx, 0.0) + loan
        )
        borrower.cash += loan
        borrower.peer_debt[lender.idx] = borrower.peer_debt.get(lender.idx, 0.0) + loan
        stats["peer_loans_issued"] += 1
        stats["peer_loan_volume"] += loan


def service_peer_loans(players):
    """Grows every outstanding peer loan by its rate, mirrored on both the
    borrower's obligation and the lender's receivable, they're the same
    number by construction, this just keeps them in sync.
    """
    if not PEER_LOANS_ENABLED:
        return
    for borrower in players:
        for lender_idx in list(borrower.peer_debt.keys()):
            borrower.peer_debt[lender_idx] *= 1 + PEER_LOAN_RATE
            players[lender_idx].receivables[borrower.idx] = borrower.peer_debt[
                lender_idx
            ]


def settle_peer_defaults(players, stats):
    """A bankrupt borrower's peer debt is discharged, same as Bank debt,
    but unlike the Bank (which already absorbed its loss the moment it
    funded the loan), the lending player's receivable is written off right
    here, a real, personal loss landing on a specific named player, not an
    institution. This is deliberately not symmetric with Bank lending, a
    peer loan is a real bet on a specific person, not a balance-sheet line.
    """
    if not PEER_LOANS_ENABLED:
        return
    for borrower in players:
        if not borrower.bankrupt:
            continue
        for lender_idx, amount in list(borrower.peer_debt.items()):
            if amount > 0:
                stats["peer_loan_defaults"] += 1
                stats["peer_loan_losses"] += amount
            players[lender_idx].receivables[borrower.idx] = 0.0
            borrower.peer_debt[lender_idx] = 0.0


def new_stats():
    return {
        "attempts": 0,
        "successes": 0,
        "ambushes": 0,
        "counter_attempts": 0,
        "counter_successes": 0,
        "counter_ambushes": 0,
        "leader_dodged_via_covert": 0,
        "declared_pacts": 0,
        "covert_pacts": 0,
        "windfall_tax_collected": 0.0,
        "net_worth_tax_collected": 0.0,
        "income_tax_collected": 0.0,
        "idle_cash_eroded": 0.0,
        "bank_deposit_interest_paid": 0.0,
        "bank_loans_denied": 0,
        "bank_shortfall_total": 0.0,
        "bank_pool_end": 0.0,
        "peer_loans_issued": 0,
        "peer_loan_volume": 0.0,
        "peer_loan_defaults": 0,
        "peer_loan_losses": 0.0,
        "voluntary_re_liquidations": 0,
        "voluntary_re_liquidation_volume": 0.0,
        "co_founder_re_nudged": 0.0,
        "reputation_penalties_paid": 0.0,
        "declared_pact_breaks": 0,
        "covert_pact_breaks": 0,
        "pact_break_penalties_paid": 0.0,
        "co_founder_buyouts": 0,
        "co_founder_buyout_volume": 0.0,
        "co_founder_parachutes_paid": 0.0,
        "defender_rewards_paid": 0.0,
        "power_card_claims": 0,
        "power_card_effects_resolved": 0,
        "power_card_failed_audits": 0,
        "power_card_lies_caught": 0,
        "power_card_lie_penalties_paid": 0.0,
        "power_card_guardian_blocks": 0,
    }


VARIABLE_BUILDING_PHASE_ENABLED = False  # set per-run
BUILDING_PHASE_RANGE = (
    4,
    6,
)  # inclusive; length is rolled once per game and never revealed


def simulate_game(n_players, rng, total_rounds=TOTAL_ROUNDS, building_rounds=None):
    """`building_rounds=None` means "use the default", not "always 5":
    with `VARIABLE_BUILDING_PHASE_ENABLED`, the Building Phase length is
    hidden information, not a fixed, publicly-known number. With it fixed
    and known, a purely rational player has zero reason to ever touch Real
    Estate before the Conflict Phase (10% Company beats 5% Real Estate,
    and defense weight is worth nothing until combat is even possible), so
    the entire Building Phase reduces to a single memorizable formula
    ("max Company until round N, then pivot") a repeat player would just
    solve and stop thinking about. Randomizing the length, secretly, per
    game, turns "when do I start defending" into a real read under
    uncertainty instead of a lookup table. Tested balance-neutral to
    slightly positive (BALANCE_TESTING.md Part 10); whether it actually
    stops a human from finding a dominant pattern after repeat plays isn't
    something bots, which don't learn across games, can measure at all.
    """
    if building_rounds is None:
        if VARIABLE_BUILDING_PHASE_ENABLED:
            building_rounds = rng.randint(*BUILDING_PHASE_RANGE)
        else:
            building_rounds = BUILDING_ROUNDS
    archetypes = roster_for(n_players, rng)
    players = [HumanPlayer(i, archetypes[i], rng) for i in range(n_players)]
    assign_raiders(players, rng)
    assign_industries(players, rng)
    assign_power_cards(players, rng)
    leader_history = []
    stats = new_stats()
    bank = Bank(pool=BANK_POOL_PER_PLAYER * n_players)

    for rnd in range(1, total_rounds + 1):
        is_building = rnd <= building_rounds
        is_final = rnd == total_rounds
        _scenario_text, scenario_deltas = (
            draw_scenario(rng) if INDUSTRY_EVENTS_ENABLED else (None, None)
        )
        finalize_pending_pact_breaks(players, stats)

        for p in players:
            generate_income_human(p, bank, stats, players, rng, scenario_deltas)
            apply_bank_deposit_interest(p, stats)
        settle_peer_defaults(players, stats)
        for p in players:
            debt_before = p.debt
            allocate_human(p, players, rng, rnd, scenario_deltas)
            if p.archetype == "Leverager":
                enforce_bank_capacity(p, debt_before, bank, stats)
        for p in players:
            try_form_jv_human(p, players, rng)
        resolve_jvs_human(players, rng, is_final, stats, scenario_deltas)
        consider_raider_pact_break(players, rng, is_building, stats)
        resolve_power_card_claims(players, rng, is_building, stats)
        assign_co_founders(players, rng)
        apply_co_founder_influence(players, stats)
        assign_ghost_backing(players, rng)
        offer_peer_loans(players, rng, stats)
        service_peer_loans(players)

        if not is_building:
            already_joined_this_round = set()
            attempt_takeovers_human(players, rng, rnd, stats, bank)
            attempt_counter_attacks_human(
                players, rng, rnd, already_joined_this_round, stats, bank
            )
        clear_analyst_shocks(players)

        revalue_stock_positions(
            players
        )  # after combat, so long/short reacts to this round's raids
        revalue_industry_positions(players, scenario_deltas)
        for p in players:
            apply_income_tax(
                p, bank, stats
            )  # after captures/JV proceeds, the whole year's profit
        apply_net_worth_tax(players, stats)
        manage_bank_deposits(players, stats)
        erode_idle_cash(players, stats)
        consider_voluntary_liquidation(players, stats)

        for p in players:
            p.cash = max(0.0, p.cash)
            if p.is_broke():
                p.broke_rounds += 1
            if p.is_disengaged():
                p.dead_rounds += 1

        leader_history.append(max(players, key=lambda p: p.total_power()).idx)

    stats["bank_pool_end"] = bank.pool

    lock_round = total_rounds
    final_leader = leader_history[-1]
    for i in range(len(leader_history) - 1, -1, -1):
        if leader_history[i] != final_leader:
            lock_round = i + 2
            break
    else:
        lock_round = 1

    for p in players:
        for ally_idx in p.allies:
            if ally_idx < p.idx:
                continue
            if p.pact_posture.get(ally_idx, False):
                stats["declared_pacts"] += 1
            else:
                stats["covert_pacts"] += 1

    return players, lock_round, stats


def run_player_count_sweep(player_counts, num_trials, seed=11):
    rng = random.Random(seed)
    rows = []
    for n in player_counts:
        dead_rounds_all = []
        broke_rounds_all = []
        lock_rounds = []
        top_gap_pcts = []
        win_counts = {}
        for _ in range(num_trials):
            players, lock_round, _ = simulate_game(n, rng)
            lock_rounds.append(lock_round)
            powers = sorted((p.total_power() for p in players), reverse=True)
            top, second = powers[0], powers[1] if len(powers) > 1 else powers[0]
            top_gap_pcts.append(0.0 if top <= 0 else 100.0 * (top - second) / top)
            winner = determine_winner(players)
            win_counts[winner.archetype] = win_counts.get(winner.archetype, 0) + 1
            for p in players:
                dead_rounds_all.append(p.dead_rounds)
                broke_rounds_all.append(p.broke_rounds)

        rows.append(
            {
                "Players": n,
                "AvgBrokeRoundsPerPlayer": round(statistics.mean(broke_rounds_all), 2),
                "AvgDeadRoundsPerPlayer": round(statistics.mean(dead_rounds_all), 2),
                "MaxDeadRoundsSeen": max(dead_rounds_all),
                "AvgLockRound": round(statistics.mean(lock_rounds), 1),
                "AvgTopVsSecondGapPct": round(statistics.mean(top_gap_pcts), 1),
                "MostFrequentWinner": max(win_counts, key=win_counts.get),
                "WinnerVarietyCount": len(win_counts),
            }
        )
    return rows


def run_alliance_visibility_check(num_trials, seed=23):
    """Re-runs the six-archetype pod BALANCE_TESTING.md Part 2 Finding 5 was
    based on, now with declare-to-reinforce alliance visibility active, to
    check whether a runaway leader can dodge the anti-snowball fix by simply
    keeping their Defense Pacts covert.
    """
    rng = random.Random(seed)
    win_counts = {a: 0 for a in ARCHETYPES}
    total_power = {a: 0.0 for a in ARCHETYPES}
    agg = new_stats()
    top_gap_pcts = []

    for _ in range(num_trials):
        players, _, stats = simulate_game(6, rng)
        for key in agg:
            agg[key] += stats[key]
        powers = sorted((p.total_power() for p in players), reverse=True)
        top, second = powers[0], powers[1]
        top_gap_pcts.append(0.0 if top <= 0 else 100.0 * (top - second) / top)
        winner = determine_winner(players)
        win_counts[winner.archetype] += 1
        for p in players:
            total_power[p.archetype] += p.total_power()

    rows = []
    for a in ARCHETYPES:
        rows.append(
            {
                "Archetype": a,
                "WinRatePct": round(100.0 * win_counts[a] / num_trials, 1),
                "AvgPower": round(total_power[a] / num_trials, 1),
            }
        )

    ambush_rate = (
        round(100.0 * agg["ambushes"] / agg["attempts"], 1) if agg["attempts"] else 0.0
    )
    counter_ambush_rate = (
        round(100.0 * agg["counter_ambushes"] / agg["counter_attempts"], 1)
        if agg["counter_attempts"]
        else 0.0
    )
    summary = {
        "AvgTopVsSecondGapPct": round(statistics.mean(top_gap_pcts), 1),
        "AttackAmbushRatePct": ambush_rate,
        "CounterAttackAmbushRatePct": counter_ambush_rate,
        "LeaderDodgedViaCovertPerGame": round(
            agg["leader_dodged_via_covert"] / num_trials, 2
        ),
        "DeclaredPactsPerGame": round(agg["declared_pacts"] / num_trials, 2),
        "CovertPactsPerGame": round(agg["covert_pacts"] / num_trials, 2),
    }
    return rows, summary


def write_csv(rows, path):
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    player_counts = [3, 4, 5, 6, 7]
    num_trials = 1000

    rows = run_player_count_sweep(player_counts, num_trials)
    write_csv(rows, "d:/Game/sim/human_sim_results.csv")

    print(f"=== Player-count sweep ({num_trials} trials each, human-biased bots) ===")
    print(
        "AvgBrokeRounds = rounds with next to nothing left, before the Board Observer fix."
    )
    print(
        "AvgDeadRounds = same, but only counting rounds without a backing choice made yet."
    )
    header = (
        f"{'N':>3} {'AvgBroke':>9} {'AvgDead':>8} {'MaxDead':>8} {'AvgLockRound':>13} "
        f"{'AvgTop2Gap%':>12} {'TopWinner':>12} {'WinnerVariety':>14}"
    )
    print(header)
    for r in rows:
        print(
            f"{r['Players']:>3} {r['AvgBrokeRoundsPerPlayer']:>9} {r['AvgDeadRoundsPerPlayer']:>8} "
            f"{r['MaxDeadRoundsSeen']:>8} {r['AvgLockRound']:>13} {r['AvgTopVsSecondGapPct']:>12} "
            f"{r['MostFrequentWinner']:>12} {r['WinnerVarietyCount']:>14}"
        )

    av_rows, av_summary = run_alliance_visibility_check(2000)
    write_csv(av_rows, "d:/Game/sim/alliance_visibility_results.csv")

    print("\n=== Declare-to-reinforce check (2000 trials, six-archetype pod) ===")
    for r in sorted(av_rows, key=lambda r: -r["WinRatePct"]):
        print(
            f"{r['Archetype']:<12} win rate {r['WinRatePct']:>5}%   avg power {r['AvgPower']:>7}"
        )
    print(
        f"\nTop vs second place power gap: {av_summary['AvgTopVsSecondGapPct']}% "
        f"(BALANCE_TESTING.md Finding 5, post-fix baseline: 4.6%)"
    )
    print(
        f"Attacks that looked winnable but failed on hidden allies (ambush rate): "
        f"{av_summary['AttackAmbushRatePct']}%"
    )
    print(
        f"Counter-attacks on the leader that got ambushed by covert allies: "
        f"{av_summary['CounterAttackAmbushRatePct']}%"
    )
    print(
        f"Times per game a runaway leader dodged a counter-attack by staying covert: "
        f"{av_summary['LeaderDodgedViaCovertPerGame']}"
    )
    print(
        f"Declared pacts per game: {av_summary['DeclaredPactsPerGame']}   "
        f"Covert pacts per game: {av_summary['CovertPactsPerGame']}"
    )

    print(
        "\n=== Ordinary-mistakes fragility check (1500 trials, six-archetype pod) ==="
    )
    print("Rational bots vs. bots with autopilot mistakes active,")
    print("with and without the raid fatigue penalty that responds to it.")
    configs = [
        ("rational bots (no mistakes)", 0.0, 0.0),
        ("+ mistakes, no fatigue fix", None, 0.0),
        ("+ mistakes, with raid fatigue", None, RAID_FATIGUE_PENALTY),
    ]
    orig_init = HumanPlayer.__init__
    for label, mistake_override, fatigue in configs:
        if mistake_override is not None:

            def init(self, idx, archetype, rng, _rate=mistake_override):
                orig_init(self, idx, archetype, rng)
                self.mistake_rate = _rate

            HumanPlayer.__init__ = init
        else:
            HumanPlayer.__init__ = orig_init
        globals()["RAID_FATIGUE_PENALTY"] = fatigue
        rows, summary = run_alliance_visibility_check(1500, seed=23)
        ranked = sorted(rows, key=lambda r: -r["WinRatePct"])
        top = ranked[0]
        print(
            f"{label:<32} top: {top['Archetype']:<12} {top['WinRatePct']:>5}%   "
            f"gap {summary['AvgTopVsSecondGapPct']}%"
        )
    HumanPlayer.__init__ = orig_init
    globals()["RAID_FATIGUE_PENALTY"] = 0.5
