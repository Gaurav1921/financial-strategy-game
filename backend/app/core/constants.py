"""Every tunable rate and table the round engine uses, in one place.

Ported from `sim/human_sim.py` and `sim/power_simulation.py`, the simulations
that validated these exact numbers (see `docs/BALANCE_TESTING.md`), and
cross-checked against `docs/GDD.md` Section 5B's rate table. `sim/` stays the
source of truth for anything this file's values ever appear to disagree with.

Two mechanics documented in GDD.md Section 5B's "Taxes" table (marginal
income tax and net-worth tax) are intentionally not implemented here: both
are explicitly flagged experimental and "not in the base ruleset yet," and
default off (`INCOME_TAX_ENABLED = False`, `NET_WORTH_TAX_ENABLED = False`)
in the simulation itself. Idle cash erosion, in the same table, is treated as
part of the base ruleset here: GDD.md Section 5 item 4 justifies the Bank's
deposit interest by it directly, and GAMEPLAY.md's round loop narrates it as
something that just happens, not an opt-in.
"""

from dataclasses import dataclass, field
from enum import StrEnum


class Industry(StrEnum):
    """The ten fixed Industries every company and Market position belongs to."""

    HEALTHCARE = "Healthcare"
    TECHNOLOGY = "Technology"
    PHARMA = "Pharma"
    ENERGY = "Energy"
    FINANCIAL_SERVICES = "Financial Services"
    CONSUMER_RETAIL = "Consumer Retail"
    AGRICULTURE = "Agriculture"
    MANUFACTURING = "Manufacturing"
    MEDIA_ENTERTAINMENT = "Media & Entertainment"
    PROPERTY = "Property"


@dataclass(frozen=True)
class Scenario:
    """One round-event card: flavor text plus its tiered effect per Industry.

    A tier ("++", "+", "-", "--") names direction and rough strength only.
    The actual size is rolled fresh from `SCENARIO_TIER_RANGES` /
    `GOLD_TIER_RANGES` every time the scenario is drawn (see
    `round_engine.draw_scenario`), so the same scenario never pays out an
    identical number twice.
    """

    text: str
    industry_tiers: dict[Industry, str] = field(default_factory=dict)
    gold_tier: str | None = None


# Player starting position, identical for everyone (GAMEPLAY.md Section 1).
STARTING_CASH = 20.0
STARTING_COMPANY = 80.0

# Round structure.
TOTAL_ROUNDS = 15
BUILDING_PHASE_RANGE = (4, 6)  # inclusive; rolled once per game, never revealed
MIN_PLAYERS = 3
MAX_PLAYERS = 10
ROUND_TIMER_SECONDS = 180  # 3 minutes (GAMEPLAY.md Section 2); ends early once everyone's ready
RESULT_DISPLAY_SECONDS = 8  # minimum pause on the result screen before the next round opens

# Income and growth rates (GDD.md Section 5B).
COMPANY_INCOME_RATE = 0.10
REAL_ESTATE_INCOME_RATE = 0.05
REAL_ESTATE_SCENARIO_DAMPENER = 0.5  # Real Estate feels the Property roll at half strength
GOLD_BASE_RANGE = (0.005, 0.035)  # ordinary-year jitter, centered near 2%

# A tier is a character, not a number: the exact size is rolled fresh from
# these ranges every time that scenario lands.
SCENARIO_TIER_RANGES = {
    "++": (0.04, 0.20),
    "+": (0.01, 0.08),
    "-": (-0.08, -0.01),
    "--": (-0.20, -0.04),
}
# Gold's tiers are smaller and asymmetric (no "--"): a hedge's job is losing
# less than everything else in a downturn, not swinging as violently as the
# industry it's hedging against.
GOLD_TIER_RANGES = {
    "++": (0.03, 0.15),
    "+": (0.01, 0.06),
    "-": (-0.04, -0.01),
}

# Borrowing and deposits.
LOAN_INTEREST_BASE = 0.08
LOAN_RISK_PREMIUM = 0.35  # extra interest per unit of leverage ratio (debt / power)
BANK_POOL_PER_PLAYER = 100.0  # matches one player's starting capital (20 cash + 80 company)
BANK_DEPOSIT_RATE = 0.04
BANK_DEPOSIT_BUFFER = 10.0  # same working-cash floor idle cash erosion protects

# Transaction friction.
REAL_ESTATE_PURCHASE_COST = 0.97  # buying costs 3%
REAL_ESTATE_LIQUIDATION_HAIRCUT = 0.85  # voluntary/forced selling costs 15%
GOLD_LIQUIDATION_HAIRCUT = 0.95  # Gold is the deliberately liquid hedge, only 5%
BANKRUPTCY_LIQUIDATION_PCT = 0.85

# Combat (GDD.md Section 6 / 5B).
TAKEOVER_CAPTURE_PCT = 0.25  # a successful Hostile Bid or counter-attack takes this share
ATTACK_FAIL_LOSS_PCT = 0.5  # a failed attacker loses this share of what they staked
POST_ATTACK_SHIELD_ROUNDS = 2  # immunity after being successfully taken over
DEFENDER_TIE_BONUS = 1.05  # defense counts at this multiple when compared to attack power
LEADER_THREATENED_MARGIN = 1.05  # the leader becomes counter-attackable this far past 2nd place
RAID_FATIGUE_PENALTY = 0.5  # attack power lost per prior successful Hostile Bid this game
RAID_FATIGUE_FLOOR = 0.25  # a repeat attacker's power never drops below this fraction

# Attack/defense weights: how much of each asset counts, per unit.
ATTACKER_CASH_WEIGHT = 0.5
ALLY_SUPPORT_WEIGHT = 0.3  # an ally's cash, added to both the attacker's and defender's side
DEFENSE_CASH_WEIGHT = 0.3
DEFENSE_GOLD_WEIGHT = 0.6
DEFENSE_REAL_ESTATE_WEIGHT = 0.9
COUNTER_ATTACK_CASH_WEIGHT = 0.4
COUNTER_ATTACK_COMPANY_WEIGHT = 0.15
COUNTER_ATTACK_FAIL_DAMPENER = (
    0.3  # a failed counter-attack's penalty is smaller than a Hostile Bid's
)

# Alliances: Joint Ventures and Defense Pacts (GDD.md Section 5 item 5 / 7).
MAX_ALLIES = 2
JV_CONTRIBUTION_UNIT = 10.0  # each partner's seed stake, and the top-up floor
JV_TOPUP_RATE = 0.2  # a top-up is this fraction of the poorer partner's current cash
JV_TOPUP_CASH_BUFFER = 15.0  # a partner skips a top-up that would leave them below this
JV_DRAIN_BONUS = 0.65  # the drainer's share of the pot; the other partner gets the rest
JV_GROWTH_FALLBACK = 0.12  # flat rate if a JV's Industry can't be resolved (should not occur in v1)
REPUTATION_PENALTY_PCT = (
    0.15  # a second proven JV drain or declared-pact break costs this much Power
)
REP_TAX_THRESHOLD = 2  # the betrayal/break count that triggers the reputation penalty

# Declare/Audit (GDD.md Section 6 / 8.3, scoped to a direct "reveal true numbers" action for v1;
# the general claim/bluff/caught-lying layer needs a concretely specified claim format this
# project doesn't have yet, see the docstring on `conflict_engine.audit_player`).
AUDIT_COST = 5.0

# Hidden Raider (GDD.md Section 8.2).
RAIDER_RATIO = 1 / 5.5  # roughly 1 Raider per 5-6 players
MIN_PLAYERS_FOR_RAIDER = 4  # below this, a hidden-role minority doesn't make sense
RAIDER_TARGET_POWER_FRACTION = 0.5  # a Raider wins if their target ends below this share of average

# Board Observer / Co-Founder (GDD.md Section 8.4).
CO_FOUNDER_RE_NUDGE = 0.10  # fraction of the host's cash the co-founder redirects to Real Estate
CO_FOUNDER_EQUITY_RATE = 0.07  # co-founder's live equity share of the host's Company
CO_FOUNDER_BUYOUT_PREMIUM = 1.2  # a host buying the co-founder out pays 20% over equity's value
CO_FOUNDER_BUYOUT_CASH_MULTIPLE = 1.2  # cash the host needs on hand before a buyout is offered
CO_FOUNDER_PARACHUTE_PCT = 0.20  # co-founder's cut of captured value if their host gets taken over

# The Final Round (GDD.md Section 8.5).
WIN_TIE_EPSILON = 0.5  # a Power gap this small counts as a tie, broken by Board Observer backing

# Idle cash erosion (GDD.md Section 5 item 4 / 5B).
IDLE_CASH_EROSION_RATE = 0.03
IDLE_CASH_EROSION_THRESHOLD = 10.0  # protects a small working-cash floor

# Disengagement / bankruptcy-adjacent thresholds (used by Player.is_broke()).
DISENGAGED_CASH_THRESHOLD = 3.0
DISENGAGED_COMPANY_THRESHOLD = 20.0

# Twenty-four example scenarios (GDD.md Section 5A), ported verbatim from
# sim/human_sim.py's SCENARIOS table.
SCENARIOS: list[Scenario] = [
    Scenario(
        "A major regional conflict breaks out",
        {
            Industry.ENERGY: "++",
            Industry.MANUFACTURING: "+",
            Industry.PHARMA: "+",
            Industry.AGRICULTURE: "-",
            Industry.CONSUMER_RETAIL: "-",
        },
        gold_tier="+",
    ),
    Scenario(
        "A breakthrough vaccine is announced",
        {
            Industry.PHARMA: "++",
            Industry.HEALTHCARE: "+",
            Industry.MEDIA_ENTERTAINMENT: "+",
        },
    ),
    Scenario(
        "Interest rates are cut sharply",
        {
            Industry.PROPERTY: "++",
            Industry.CONSUMER_RETAIL: "+",
            Industry.TECHNOLOGY: "+",
            Industry.FINANCIAL_SERVICES: "-",
        },
        gold_tier="+",
    ),
    Scenario(
        "A major tech company reports a data breach",
        {Industry.TECHNOLOGY: "--", Industry.FINANCIAL_SERVICES: "-"},
    ),
    Scenario(
        "A bumper harvest season",
        {Industry.AGRICULTURE: "+", Industry.CONSUMER_RETAIL: "+"},
    ),
    Scenario(
        "A severe drought hits key farming regions",
        {Industry.AGRICULTURE: "--", Industry.CONSUMER_RETAIL: "-"},
        gold_tier="+",
    ),
    Scenario(
        "A new blockbuster streaming platform launches",
        {Industry.MEDIA_ENTERTAINMENT: "++", Industry.TECHNOLOGY: "+"},
    ),
    Scenario(
        "Oil prices crash on oversupply",
        {
            Industry.ENERGY: "--",
            Industry.MANUFACTURING: "+",
            Industry.CONSUMER_RETAIL: "+",
            Industry.AGRICULTURE: "+",
        },
        gold_tier="+",
    ),
    Scenario(
        "A recession is officially declared",
        {
            Industry.CONSUMER_RETAIL: "--",
            Industry.FINANCIAL_SERVICES: "--",
            Industry.TECHNOLOGY: "-",
            Industry.PROPERTY: "-",
        },
        gold_tier="++",
    ),
    Scenario(
        "A landmark trade deal is signed",
        {
            Industry.MANUFACTURING: "++",
            Industry.AGRICULTURE: "+",
            Industry.TECHNOLOGY: "+",
            Industry.CONSUMER_RETAIL: "+",
        },
        gold_tier="-",
    ),
    Scenario(
        "Consumer confidence hits a record high",
        {
            Industry.CONSUMER_RETAIL: "++",
            Industry.MEDIA_ENTERTAINMENT: "+",
            Industry.PROPERTY: "+",
        },
        gold_tier="-",
    ),
    Scenario(
        "A cybersecurity crisis hits financial institutions",
        {Industry.FINANCIAL_SERVICES: "--", Industry.TECHNOLOGY: "-"},
        gold_tier="+",
    ),
    Scenario(
        "Housing demand surges in major cities",
        {Industry.PROPERTY: "++", Industry.FINANCIAL_SERVICES: "+"},
    ),
    Scenario(
        "Global supply chains face major disruption",
        {
            Industry.MANUFACTURING: "--",
            Industry.CONSUMER_RETAIL: "-",
            Industry.TECHNOLOGY: "-",
            Industry.AGRICULTURE: "-",
        },
        gold_tier="+",
    ),
    Scenario(
        "A wave of mergers sweeps the healthcare industry",
        {
            Industry.HEALTHCARE: "+",
            Industry.PHARMA: "+",
            Industry.FINANCIAL_SERVICES: "+",
        },
    ),
    Scenario(
        "Renewable energy investment surges",
        {Industry.ENERGY: "+", Industry.MANUFACTURING: "+", Industry.TECHNOLOGY: "+"},
    ),
    Scenario(
        "A major retailer files for bankruptcy",
        {
            Industry.CONSUMER_RETAIL: "--",
            Industry.PROPERTY: "-",
            Industry.FINANCIAL_SERVICES: "-",
        },
        gold_tier="+",
    ),
    Scenario(
        "Streaming and gaming demand hits an all-time high",
        {Industry.MEDIA_ENTERTAINMENT: "++", Industry.TECHNOLOGY: "+"},
    ),
    Scenario(
        "A wave of automation disrupts manufacturing jobs",
        {
            Industry.MANUFACTURING: "+",
            Industry.TECHNOLOGY: "+",
            Industry.CONSUMER_RETAIL: "-",
        },
    ),
    Scenario(
        "A wave of corporate bankruptcies hits over-leveraged firms",
        {
            Industry.FINANCIAL_SERVICES: "--",
            Industry.MANUFACTURING: "-",
            Industry.CONSUMER_RETAIL: "-",
        },
        gold_tier="++",
    ),
    Scenario(
        "Currency volatility rattles global markets",
        {
            Industry.FINANCIAL_SERVICES: "-",
            Industry.TECHNOLOGY: "-",
            Industry.MANUFACTURING: "-",
        },
        gold_tier="+",
    ),
    Scenario(
        "A prolonged labor strike disrupts key industries",
        {
            Industry.MANUFACTURING: "--",
            Industry.AGRICULTURE: "-",
            Industry.CONSUMER_RETAIL: "-",
        },
    ),
    Scenario(
        "Extreme weather disrupts supply chains",
        {
            Industry.AGRICULTURE: "--",
            Industry.ENERGY: "-",
            Industry.CONSUMER_RETAIL: "-",
        },
        gold_tier="+",
    ),
    Scenario("A quiet, uneventful year in the markets", {}),
]
