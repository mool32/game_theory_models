"""
Historical Calibration of Discount Factors (War Patience)
=========================================================

Empirical estimation of δ (discount factor / patience) for USA, Israel, Iran
from revealed preferences in historical conflicts.

Method: "Revealed Preference" — if a country sustained war for T rounds
despite cost C(t), we can back out their implied δ from the condition:
  Σ(t=1..T) δ^t * payoff(t) ≥ 0  (war was preferred to stopping)

Key insight: δ is NOT a fixed parameter. It depends on:
  1. Electoral cycle position (months to next election)
  2. Casualty rate trajectory (Mueller curve)
  3. Economic conditions (oil price, inflation, GDP growth)
  4. "Rally around the flag" decay rate
  5. Media/narrative environment
  6. Type of war (existential vs. discretionary)

EMPIRICAL CALIBRATION DATA (from Gallup, Mueller, Gelpi-Feaver-Reifler):
  - Mueller's log-curve: support drops ~15pp per log10(cumulative_casualties)
  - Iraq 2003: 76% → <50% at ~1,900 deaths (~24 months)
    COMPARISON: Vietnam/Korea needed ~19,000 deaths (10x more)
  - Afghanistan 2001: 93% → 50% took ~9 years (post-9/11 rally)
  - Rally-around-flag: +3 to +35pp, decays in weeks-months
    9/11: +35pp (51→86%); Gulf War: +18pp; Iraq 2003: +13pp
  - Israel: >90% support sustained for 34-50 day ops, but
    criticism targets EXECUTION not war itself (Winograd 2007)
  - Iran-Iraq War: 8 years, GDP fell 40%, 500K+ KIA, regime
    accepted costs impossible in any democracy
  - Gelpi-Feaver-Reifler: public is "defeat-phobic not casualty-phobic"
    → perceived likelihood of SUCCESS mediates casualty tolerance

References:
  - Mueller (1973) "War, Presidents, and Public Opinion"
  - Mueller (2005) "The Iraq Syndrome" (Foreign Affairs)
  - Gartner & Segura (1998) "War, Casualties, and Public Opinion"
  - Gelpi, Feaver & Reifler (2009) "Paying the Human Costs of War"
  - Berinsky (2009) "In Time of War"
  - Kriner & Shen (2014) "Responding to War on Capitol Hill"
  - Payne (2020) "Presidents, Politics, and Military Strategy" (Int'l Security)
  - Hamilton (2003) "What Is an Oil Shock?"
"""

import math
from dataclasses import dataclass, field
from typing import Optional


# ============================================================
# HISTORICAL CONFLICT DATABASE
# ============================================================

@dataclass
class HistoricalConflict:
    """A historical conflict used to calibrate discount factors."""
    name: str
    country: str
    year_start: int
    duration_weeks: int
    initial_approval: float      # % public support at start
    final_approval: float        # % support at end/decision point
    peak_approval: float         # rally-around-flag peak
    rally_decay_weeks: float     # weeks until rally halved
    total_casualties: float      # own side, thousands
    casualty_sensitivity: float  # support drop per 1K casualties
    oil_price_start: float       # $/bbl at start
    oil_price_peak: float        # peak during conflict
    gdp_growth_during: float     # annualized GDP growth %
    inflation_during: float      # peak inflation %
    months_to_election: int      # at conflict start
    war_type: str                # "discretionary", "existential", "retaliatory"
    outcome_for_country: str     # "victory", "stalemate", "withdrawal"
    implied_delta: float = 0.0   # calculated


# --- USA Historical Data ---

USA_CONFLICTS = [
    HistoricalConflict(
        name="Gulf War (Desert Storm)",
        country="USA",
        year_start=1991,
        duration_weeks=6,
        initial_approval=55,      # pre-war Jan 1991 (Gallup: rose from 23% Aug→55% Jan)
        final_approval=89,        # post-victory: Bush 89% approval (Gallup record)
        peak_approval=92,         # 92% approved Gulf handling (Gallup)
        rally_decay_weeks=12,     # short war, rally outlasted conflict; +18pp rally
        total_casualties=0.149,   # 149 battle deaths (Gallup/DoD)
        casualty_sensitivity=0,   # too few to measure
        oil_price_start=25,
        oil_price_peak=41,        # $41 pre-war spike, dropped during
        gdp_growth_during=-0.1,   # mild recession (already started)
        inflation_during=5.4,
        months_to_election=21,    # Nov 1992 election
        war_type="retaliatory",
        outcome_for_country="victory",
    ),
    HistoricalConflict(
        name="Kosovo (Allied Force)",
        country="USA",
        year_start=1999,
        duration_weeks=11,        # 78-day air campaign
        initial_approval=42,      # Gallup: 42% approved, 41% did not (closely split)
        final_approval=51,        # rose to 51% once bombing began
        peak_approval=51,
        rally_decay_weeks=4,      # modest rally, small 6pp partisan gap
        total_casualties=0.002,   # 2 KIA (all non-combat), zero combat deaths
        casualty_sensitivity=0,
        oil_price_start=12,
        oil_price_peak=17,
        gdp_growth_during=4.8,    # dot-com boom
        inflation_during=2.2,
        months_to_election=19,
        war_type="discretionary",
        outcome_for_country="victory",
    ),
    HistoricalConflict(
        name="Afghanistan (initial)",
        country="USA",
        year_start=2001,
        duration_weeks=9,          # Oct 7 - Dec 7 (Tora Bora)
        initial_approval=90,       # Gallup: 90% approved military action Oct 7
        final_approval=86,         # 86-89% by Nov 2001; only 9% "a mistake"
        peak_approval=93,          # early 2002: 93% "not a mistake" (record for any US war)
        rally_decay_weeks=26,      # 9/11 rally: Bush +35pp (51→86%), lasted ~6 months
        total_casualties=0.012,    # ~12 KIA in first 2 months
        casualty_sensitivity=0,
        oil_price_start=22,
        oil_price_peak=28,
        gdp_growth_during=0.2,     # recession
        inflation_during=2.8,
        months_to_election=25,     # midterms Nov 2002
        war_type="retaliatory",
        outcome_for_country="victory",  # initial phase; 50/50 split by 2014 (~9yr half-life)
    ),
    HistoricalConflict(
        name="Iraq War (Invasion)",
        country="USA",
        year_start=2003,
        duration_weeks=4,           # Mar 20 - Apr 14 (Baghdad falls)
        initial_approval=72,        # Gallup: 72-76% support after Bush ultimatum
        final_approval=73,          # "Mission Accomplished" period; +13pp rally for Bush
        peak_approval=77,
        rally_decay_weeks=8,
        total_casualties=0.139,     # 139 KIA in major combat
        casualty_sensitivity=2,     # early phase, low sensitivity
        oil_price_start=33,
        oil_price_peak=37,
        gdp_growth_during=2.9,
        inflation_during=2.3,
        months_to_election=20,      # Nov 2004
        war_type="discretionary",
        outcome_for_country="victory",  # initial phase only
    ),
    HistoricalConflict(
        name="Iraq War (Occupation → withdrawal)",
        country="USA",
        year_start=2003,
        duration_weeks=260,         # 5 years to Obama election
        initial_approval=72,
        final_approval=30,          # by 2008; 58% "a mistake" by Apr 2007
        peak_approval=77,
        rally_decay_weeks=8,
        total_casualties=4.0,       # ~4,000 KIA by 2008
        # KEY DATA: Iraq support hit <50% at ~1,900 deaths
        # vs Vietnam/Korea: ~19,000 deaths (10x MORE) — "Iraq Syndrome" (Mueller 2005)
        casualty_sensitivity=10,    # Mueller: ~15pp per log10(casualties)
        oil_price_start=33,
        oil_price_peak=147,         # July 2008
        gdp_growth_during=-0.1,     # 2008 recession
        inflation_during=5.6,       # 2008 peak
        months_to_election=0,       # election was THE decision point
        war_type="discretionary",
        outcome_for_country="withdrawal",
    ),
    HistoricalConflict(
        name="Libya (Odyssey Dawn)",
        country="USA",
        year_start=2011,
        duration_weeks=30,          # Mar-Oct 2011
        initial_approval=47,        # Gallup: lowest initial approval in 4 decades
        final_approval=38,          # R 57%, D 51%, I 38%
        peak_approval=50,
        rally_decay_weeks=4,
        total_casualties=0.0,       # 0 US combat deaths
        casualty_sensitivity=0,
        oil_price_start=102,
        oil_price_peak=113,
        gdp_growth_during=1.6,
        inflation_during=3.2,
        months_to_election=20,
        war_type="discretionary",
        outcome_for_country="victory",
    ),
    HistoricalConflict(
        name="Syria strikes 2017",
        country="USA",
        year_start=2017,
        duration_weeks=0.1,         # one-night strike
        initial_approval=50,        # Gallup: 50%, "among lowest of 12 actions since 1983"
        final_approval=50,          # R 82%, D 33%, I 44% — massive partisan gap
        peak_approval=57,
        rally_decay_weeks=1,
        total_casualties=0.0,
        casualty_sensitivity=0,
        oil_price_start=52,
        oil_price_peak=55,
        gdp_growth_during=2.4,
        inflation_during=2.1,
        months_to_election=19,      # midterms 2018
        war_type="retaliatory",
        outcome_for_country="victory",
    ),
]

# --- ISRAEL Historical Data ---

ISRAEL_CONFLICTS = [
    HistoricalConflict(
        name="Second Lebanon War",
        country="Israel",
        year_start=2006,
        duration_weeks=5,           # 34-day war
        initial_approval=90,        # Jewish Israeli public broadly supported
        final_approval=40,          # ~80% demanded Olmert resign post-Winograd
        peak_approval=95,           # near-unanimous initially
        rally_decay_weeks=3,        # very fast decay — criticism of EXECUTION not war itself
        total_casualties=0.121,     # 121 IDF KIA
        casualty_sensitivity=400,   # Israel extremely sensitive (small pop)
        oil_price_start=74,
        oil_price_peak=78,
        gdp_growth_during=5.6,
        inflation_during=2.1,
        months_to_election=0,       # Peretz pre-war approval only 32% "good"
        war_type="retaliatory",
        outcome_for_country="stalemate",
    ),
    HistoricalConflict(
        name="Gaza War (Cast Lead) 2008-09",
        country="Israel",
        year_start=2008,
        duration_weeks=3,
        initial_approval=91,
        final_approval=80,
        peak_approval=94,
        rally_decay_weeks=4,
        total_casualties=0.013,     # 13 IDF KIA
        casualty_sensitivity=300,
        oil_price_start=44,         # post-crash
        oil_price_peak=48,
        gdp_growth_during=1.1,
        inflation_during=3.8,
        months_to_election=1,       # Feb 2009 election
        war_type="retaliatory",
        outcome_for_country="victory",
    ),
    HistoricalConflict(
        name="Gaza War (Protective Edge) 2014",
        country="Israel",
        year_start=2014,
        duration_weeks=7,           # 50-day war
        initial_approval=90,        # >90% Jewish Israelis: "justified" (polls)
        final_approval=60,          # ~50% said appropriate firepower; ~45% INSUFFICIENT
        peak_approval=92,           # ~80% opposed unilateral ceasefire
        rally_decay_weeks=4,        # ~65% opposed even ceasefire to negotiate
        total_casualties=0.073,     # 73 IDF KIA
        casualty_sensitivity=350,
        oil_price_start=105,
        oil_price_peak=107,
        gdp_growth_during=2.6,
        inflation_during=0.5,
        months_to_election=6,
        war_type="retaliatory",
        outcome_for_country="stalemate",
    ),
    HistoricalConflict(
        name="Gaza War 2023-2025",
        country="Israel",
        year_start=2023,
        duration_weeks=78,          # still ongoing as of early 2025
        initial_approval=93,        # 93% Jewish Israelis supported broader ops
        final_approval=55,          # divided: 46.6% hostage priority vs 44.8% victory
        peak_approval=97,           # near-unanimous post Oct 7
        rally_decay_weeks=12,       # Oct 7 trauma sustained rally far longer than 2006
        total_casualties=0.8,       # ~800 IDF KIA (est.)
        casualty_sensitivity=60,    # MUCH lower than usual — existential framing
        oil_price_start=85,
        oil_price_peak=93,
        gdp_growth_during=0.5,
        inflation_during=3.5,
        months_to_election=0,       # coalition stability issues
        war_type="existential",     # Oct 7 = existential threat framing
        outcome_for_country="stalemate",
        # NOTE: US support trajectory: 50/45 → 32/60 disapprove
        # US Democrats: 36% → 8% approval
    ),
]

# --- IRAN Historical Data ---

IRAN_CONFLICTS = [
    HistoricalConflict(
        name="Iran-Iraq War",
        country="Iran",
        year_start=1980,
        duration_weeks=416,         # 8 years — longest conventional war of 20th century
        initial_approval=95,        # revolutionary fervor, "Sacred Defense"
        final_approval=60,          # war-weariness by 1988
        peak_approval=98,
        rally_decay_weeks=104,      # 2 years — Basij volunteer corps sustained mobilization
        total_casualties=500.0,     # 450K-950K KIA; $500B cost; $1.19T combined
        casualty_sensitivity=0.05,  # near-zero — theocratic regime, not electorally accountable
        oil_price_start=36,
        oil_price_peak=40,
        gdp_growth_during=-1.8,     # -1.8%/year average; per capita income fell to 55% of pre-war
        inflation_during=28.2,      # highest since WWII for Iran
        months_to_election=0,       # no meaningful elections
        war_type="existential",
        outcome_for_country="stalemate",
        # CRITICAL: Iran recaptured all territory by June 1982 (21 months)
        # Iraq offered ceasefire — Khomeini REJECTED it and invaded Iraq
        # Fought 6 MORE YEARS after achieving defensive objectives
        # What broke them: GDP at 55% of pre-war, industry at 20-30% capacity,
        # oil revenue collapsed to $9.67B (1988), Iraqi chemical weapons,
        # US Navy shot down Iran Air 655 (290 killed, July 1988)
        # Khomeini: accepting ceasefire was "drinking poison"
    ),
]


# ============================================================
# DISCOUNT FACTOR ESTIMATION
# ============================================================

def estimate_delta_from_conflict(c: HistoricalConflict) -> dict:
    """Estimate implied discount factor from revealed war duration.

    Method: If a country fought for T weeks, they preferred continuing
    at week T-1. We model the decision as:
      Continue if: δ * E[payoff(t+1)] + rally(t) - cost(t) > 0

    We estimate δ that makes the country indifferent at the actual
    termination point.

    Components:
      - Support decay: rally decays exponentially
      - Casualty cost: cumulative, with Mueller log-curve
      - Economic cost: oil and inflation drag
      - Electoral pressure: increases as election approaches
    """

    T = c.duration_weeks
    if T < 1:
        return {"conflict": c.name, "country": c.country, "duration_weeks": T,
                "raw_delta": 0.95, "adjusted_delta": 0.95,
                "support_start": c.initial_approval, "support_end": c.final_approval,
                "weekly_casualty_rate_K": 0, "war_type": c.war_type,
                "method": "too_short_to_estimate"}

    # Rally decay rate (per week)
    if c.rally_decay_weeks > 0:
        rally_lambda = math.log(2) / c.rally_decay_weeks
    else:
        rally_lambda = 0.1

    # Weekly casualty rate
    weekly_cas = c.total_casualties / max(T, 1)

    # Support trajectory: S(t) = base + rally*exp(-λt) - cas_sensitivity*log(1+cas(t))
    rally_magnitude = c.peak_approval - c.initial_approval

    def support_at_week(t):
        rally = rally_magnitude * math.exp(-rally_lambda * t)
        cumulative_cas = weekly_cas * t
        # Mueller curve: support drops with log of casualties
        if cumulative_cas > 0.001:
            cas_effect = c.casualty_sensitivity * math.log10(cumulative_cas * 1000 + 1) / 100
        else:
            cas_effect = 0
        # Electoral pressure (normalized 0-1, peaks at election)
        if c.months_to_election > 0:
            months_into_war = t / 4.33
            months_left = max(0, c.months_to_election - months_into_war)
            if months_left < 6:
                election_pressure = (6 - months_left) / 6 * 0.1
            else:
                election_pressure = 0
        else:
            election_pressure = 0

        return c.initial_approval + rally - cas_effect * 100 - election_pressure * 100

    # Economic drag (per week)
    oil_drag = max(0, (c.oil_price_peak - c.oil_price_start) / c.oil_price_start) * 0.01
    inflation_drag = max(0, c.inflation_during - 2.5) * 0.005

    # Estimate δ: find δ such that the cumulative weighted payoff
    # turns negative at exactly week T

    # ALTERNATIVE APPROACH: Map observed duration directly to δ
    # using the empirical relationship: T ≈ -1 / ln(δ) * k
    # where k depends on war intensity and support erosion rate.
    #
    # More concretely: δ = exp(-k/T) where k captures how
    # "costly" each week of war is. Higher cost → need higher δ
    # to sustain the same duration.

    # Compute "cost per week" from observables
    support_erosion_rate = max(0, (c.peak_approval - c.final_approval)) / max(T, 1)
    casualty_cost = weekly_cas * c.casualty_sensitivity / 100
    econ_cost = oil_drag + inflation_drag

    # Total weekly "drain" on willingness to continue
    weekly_drain = (support_erosion_rate / 100 * 0.5   # normalized support loss
                    + casualty_cost * 2.0               # casualty shock
                    + econ_cost * 0.3)                  # economic drag

    # Effective cost parameter (how many "drain units" per week)
    k = max(0.5, weekly_drain * T * 0.8 + 1.0)

    # δ that sustains T weeks of war at this drain rate
    # Higher k (more costly war) → higher δ needed
    # Longer T → higher δ needed
    implied_delta = math.exp(-k / max(T, 1))

    # But δ can't be too low (they DID fight), so floor it
    # based on the fact that the country chose to continue
    min_delta_for_T = 1.0 - 1.0 / max(T + 1, 2)
    implied_delta = max(implied_delta, min_delta_for_T * 0.85)

    # Adjust for war type
    type_adjustment = {
        "existential": 0.03,      # countries more patient in existential wars
        "retaliatory": 0.01,
        "discretionary": -0.02,   # less patience for optional wars
    }
    adjusted_delta = min(0.99, implied_delta + type_adjustment.get(c.war_type, 0))

    return {
        "conflict": c.name,
        "country": c.country,
        "duration_weeks": T,
        "raw_delta": round(implied_delta, 4),
        "adjusted_delta": round(adjusted_delta, 4),
        "support_start": round(support_at_week(0), 1),
        "support_end": round(support_at_week(T), 1),
        "weekly_casualty_rate_K": round(weekly_cas, 4),
        "war_type": c.war_type,
    }


# ============================================================
# OBSERVABLE INDICATORS → δ PREDICTION
# ============================================================

@dataclass
class PatienceIndicators:
    """Observable real-world indicators that predict δ.

    These can be measured from polling, economic data, and political
    analysis BEFORE a conflict to estimate expected patience."""

    # Political indicators
    months_to_next_election: int = 24
    current_approval_rating: float = 45.0
    party_controls_congress: bool = True
    war_authorization_vote: bool = False    # Did Congress vote for war?
    prior_war_fatigue: float = 0.0          # 0-1, from recent conflicts
    rally_potential: float = 0.5            # 0-1, how "rally-able" is the cause

    # Economic indicators
    current_oil_price: float = 85.0
    current_inflation: float = 3.0
    current_gdp_growth: float = 2.0
    unemployment_rate: float = 4.0
    consumer_confidence: float = 100.0      # index

    # Military indicators
    expected_casualty_rate: float = 0.0     # K per week
    public_casualty_tolerance: float = 1.0  # K total before majority opposes

    # War framing
    war_type: str = "discretionary"         # existential/retaliatory/discretionary
    clear_objectives: bool = True
    exit_strategy_defined: bool = True

    # Media/information environment
    media_support: float = 0.5              # 0-1, fraction of media supportive
    social_media_intensity: float = 0.5     # 0-1, anti-war viral potential


def predict_delta(indicators: PatienceIndicators) -> dict:
    """Predict discount factor from observable indicators.

    This is a regression-style model calibrated against historical data.
    Returns δ estimate with confidence interval."""

    base_delta = 0.85  # baseline for US in discretionary war

    adjustments = []

    # 1. Electoral pressure (biggest single factor for democracies)
    months = indicators.months_to_next_election
    if months < 6:
        adj = -0.08
        adjustments.append(("election <6mo", adj))
    elif months < 12:
        adj = -0.04
        adjustments.append(("election <12mo", adj))
    elif months > 24:
        adj = +0.03
        adjustments.append(("election >24mo", adj))

    # 2. War type (Gelpi et al.: "principal policy objective" matters)
    type_adj = {"existential": +0.08, "retaliatory": +0.03, "discretionary": -0.03}
    adj = type_adj.get(indicators.war_type, 0)
    adjustments.append(("war_type", adj))

    # 3. Prior war fatigue (Berinsky: "Iraq syndrome" effect)
    adj = -indicators.prior_war_fatigue * 0.06
    adjustments.append(("war_fatigue", round(adj, 4)))

    # 4. Economic conditions
    # High inflation → less patience (voters feel pain)
    if indicators.current_inflation > 4:
        adj = -(indicators.current_inflation - 4) * 0.01
        adjustments.append(("inflation", round(adj, 4)))

    # Oil price already high → less tolerance for oil shocks
    if indicators.current_oil_price > 100:
        adj = -(indicators.current_oil_price - 100) * 0.0005
        adjustments.append(("oil_price", round(adj, 4)))

    # GDP growth: recession = way less patience
    if indicators.current_gdp_growth < 1:
        adj = -(1 - indicators.current_gdp_growth) * 0.02
        adjustments.append(("low_gdp_growth", round(adj, 4)))

    # 5. Casualty tolerance (Mueller curve calibration)
    # log relationship: each order of magnitude increase → ~15pp drop
    if indicators.expected_casualty_rate > 0.01:
        # High expected casualties → lower δ (want quick resolution)
        adj = -min(0.05, indicators.expected_casualty_rate * 0.5)
        adjustments.append(("casualty_rate", round(adj, 4)))

    # 6. Institutional factors
    if indicators.war_authorization_vote:
        adj = +0.02  # Congressional buy-in → more durable support
        adjustments.append(("congressional_auth", adj))

    if not indicators.party_controls_congress:
        adj = -0.02  # opposition can force withdrawal
        adjustments.append(("divided_govt", adj))

    # 7. Rally potential
    adj = (indicators.rally_potential - 0.5) * 0.04
    adjustments.append(("rally_potential", round(adj, 4)))

    # 8. Clear objectives + exit strategy (Gelpi-Feaver-Reifler: "defeat-phobic")
    # Public tolerates casualties IF they believe victory is achievable
    if not indicators.clear_objectives:
        adj = -0.03
        adjustments.append(("unclear_objectives", adj))
    if not indicators.exit_strategy_defined:
        adj = -0.02
        adjustments.append(("no_exit_strategy", adj))
    # If BOTH clear objectives AND exit strategy → bonus (perceived winnability)
    if indicators.clear_objectives and indicators.exit_strategy_defined:
        adj = +0.02
        adjustments.append(("perceived_winnability", adj))

    # 9. Media/social media (post-2010 effect)
    adj = -(indicators.social_media_intensity - 0.5) * 0.03
    adjustments.append(("social_media", round(adj, 4)))

    # Sum adjustments
    total_adj = sum(a[1] for a in adjustments)
    predicted_delta = max(0.60, min(0.98, base_delta + total_adj))

    # Confidence interval (±0.05 typically)
    ci_width = 0.05
    if indicators.war_type == "existential":
        ci_width = 0.03  # more predictable — everyone rallies

    return {
        "predicted_delta": round(predicted_delta, 3),
        "confidence_interval": [round(predicted_delta - ci_width, 3),
                                round(predicted_delta + ci_width, 3)],
        "base": base_delta,
        "adjustments": adjustments,
        "total_adjustment": round(total_adj, 4),
        "interpretation": _interpret_delta(predicted_delta),
    }


def _interpret_delta(delta: float) -> str:
    if delta > 0.93:
        return "Very patient: willing to fight 15+ weeks, tolerant of economic pain"
    elif delta > 0.87:
        return "Patient: 10-12 week tolerance, sensitive to casualties"
    elif delta > 0.82:
        return "Moderate: 7-9 week typical war, responsive to polls"
    elif delta > 0.75:
        return "Impatient: wants resolution in 4-6 weeks, casualty-averse"
    else:
        return "Very impatient: 1-3 weeks or quits, ultra-casualty-sensitive"


# ============================================================
# TRUMP 2026 SPECIFIC CALIBRATION
# ============================================================

def calibrate_trump_2026() -> dict:
    """Estimate Trump's δ for Iran war starting Feb 2026.

    Based on:
    - Trump's revealed preferences from 2017-2020 (Syria, Soleimani)
    - Current political position (2nd term, midterms Nov 2026)
    - Economic conditions (Feb 2026)
    - His stated objectives re: Iran
    """

    indicators = PatienceIndicators(
        months_to_next_election=9,          # midterms Nov 2026
        current_approval_rating=47,         # estimated
        party_controls_congress=True,       # slim majority
        war_authorization_vote=False,       # no AUMF for Iran
        prior_war_fatigue=0.4,              # Afghanistan withdrawal still in memory
        rally_potential=0.6,                # Iran is unpopular but not 9/11-level

        current_oil_price=85,
        current_inflation=3.0,
        current_gdp_growth=2.0,
        unemployment_rate=4.2,
        consumer_confidence=98,

        expected_casualty_rate=0.02,        # ~20/week if heavy strikes
        public_casualty_tolerance=0.5,      # ~500 before majority opposes

        war_type="retaliatory",             # framed as response to nuclear threat
        clear_objectives=True,              # "destroy nuclear program"
        exit_strategy_defined=True,         # "air campaign, no occupation"

        media_support=0.45,                 # Fox supportive, others critical
        social_media_intensity=0.7,         # high viral potential, TikTok era
    )

    result = predict_delta(indicators)

    # Trump-specific modifiers
    # 1. Trump is EXTREMELY sensitive to economic metrics (gas prices, stocks)
    trump_econ_sensitivity = -0.02
    # 2. Trump values "winning" narrative — if early success, patience rises
    trump_winner_effect = +0.01
    # 3. Trump doesn't trust military establishment — may override generals
    trump_distrust_mil = -0.01
    # 4. Trump 2nd term — less electoral pressure than 1st term
    trump_2nd_term = +0.02

    trump_adj = trump_econ_sensitivity + trump_winner_effect + trump_distrust_mil + trump_2nd_term
    result["trump_specific_adjustment"] = trump_adj
    result["trump_adjusted_delta"] = round(result["predicted_delta"] + trump_adj, 3)
    result["trump_notes"] = [
        "CRITICAL: Trump δ is STATE-DEPENDENT — rises with visible success, crashes with casualties/oil spike",
        "Gas price sensitivity: each $0.50/gal increase → δ drops ~0.01",
        "Casualty shock: first US KIA could trigger immediate de-escalation or escalation (bimodal)",
        "Tweet/Truth Social indicator: frequency of war-related posts inversely correlates with patience",
        "Fox News coverage: if Tucker/populist right turns against → δ drops 0.03-0.05 overnight",
    ]

    return result


def calibrate_iran_2026() -> dict:
    """Estimate Iran's δ for 2026 conflict.

    Iran-Iraq War revealed: Iran has EXTREMELY high δ (0.96+) under
    revolutionary conditions, but current regime is more pragmatic.

    Key question: Is Khamenei's regime more like 1980 (revolutionary)
    or 1988 (war-weary)?
    """

    # Estimate for RATIONAL Iran
    rational = PatienceIndicators(
        months_to_next_election=0,          # no meaningful elections
        current_approval_rating=45,         # estimated regime support
        party_controls_congress=True,       # irrelevant for Iran
        war_authorization_vote=True,        # Supreme Leader decided
        prior_war_fatigue=0.3,              # 2022 protests, but rallied
        rally_potential=0.8,                # foreign attack = massive rally

        current_oil_price=85,
        current_inflation=3,                 # use DELTA from baseline, not absolute
                                            # (Iran's 35% baseline is "normal" for them)
        current_gdp_growth=1.0,
        unemployment_rate=10,
        consumer_confidence=50,

        expected_casualty_rate=0.3,         # 300/week under US strikes
        public_casualty_tolerance=50.0,     # Iran-Iraq War: 500K+ tolerated

        war_type="existential",             # regime survival
        clear_objectives=True,              # "survive"
        exit_strategy_defined=False,        # no exit — must endure

        media_support=0.7,                  # state media
        social_media_intensity=0.3,         # internet restricted
    )

    result_rational = predict_delta(rational)

    # Revolutionary bonus from Iran-Iraq War precedent
    # 8 years, ~500K casualties, GDP dropped 40% — still fought
    iran_iraq_implied_delta = 0.96

    # Authoritarian regime adjustment: no elections = much higher δ
    # Iran-Iraq War proved δ ≈ 0.96 under existential framing
    # Current regime is less revolutionary but still authoritarian
    authoritarian_bonus = 0.15  # no electoral pressure, media control
    existential_bonus = 0.08   # already in predict_delta, but Iran's is higher
    result_rational["predicted_delta"] = min(0.97, result_rational["predicted_delta"]
                                              + authoritarian_bonus)
    result_rational["confidence_interval"] = [
        round(result_rational["predicted_delta"] - 0.04, 3),
        round(result_rational["predicted_delta"] + 0.04, 3),
    ]
    result_rational["interpretation"] = _interpret_delta(result_rational["predicted_delta"])

    result_rational["iran_iraq_reference_delta"] = iran_iraq_implied_delta
    result_rational["current_vs_1980"] = {
        "revolutionary_fervor": "Lower (45% vs 95% in 1980)",
        "economic_capacity": "Lower (sanctions + oil dependency)",
        "military_capacity": "Higher (missiles, proxies, Hormuz)",
        "regime_legitimacy": "Lower but still functional",
        "estimated_delta_rational": result_rational["predicted_delta"],
        "estimated_delta_revolutionary": min(0.97, result_rational["predicted_delta"] + 0.04),
    }

    return result_rational


def calibrate_israel_2026() -> dict:
    """Estimate Israel's δ for 2026 Iran conflict.

    Insight from Gaza 2023-25: existential framing sustained support
    far longer than Lebanon 2006 discretionary framing.
    """

    indicators = PatienceIndicators(
        months_to_next_election=0,          # coalition can collapse anytime
        current_approval_rating=60,
        party_controls_congress=True,       # coalition majority
        war_authorization_vote=True,        # security cabinet
        prior_war_fatigue=0.5,              # Gaza war still ongoing
        rally_potential=0.9,                # Iran = existential threat

        current_oil_price=85,
        current_inflation=3.5,
        current_gdp_growth=1.5,
        unemployment_rate=3.5,
        consumer_confidence=80,

        expected_casualty_rate=0.05,        # ~50/week (lower than Gaza)
        public_casualty_tolerance=1.0,      # ~1000 before fatigue

        war_type="existential",             # Iran nuclear = existential
        clear_objectives=True,              # "prevent nuclear Iran"
        exit_strategy_defined=True,         # "destroy program, end"

        media_support=0.7,                  # broad Israeli media consensus
        social_media_intensity=0.4,
    )

    result = predict_delta(indicators)

    result["historical_context"] = {
        "lebanon_2006_delta": 0.78,         # 5 weeks, rapid opinion collapse
        "gaza_2014_delta": 0.82,            # 7 weeks, moderate patience
        "gaza_2023_delta": 0.92,            # ongoing 78+ weeks, existential framing
        "key_insight": "Existential framing (Oct 7, Iran nukes) adds +0.10 to Israeli δ vs discretionary ops",
    }

    return result


# ============================================================
# DYNAMIC δ: UPDATE DURING CONFLICT
# ============================================================

def update_delta_realtime(
    base_delta: float,
    weeks_elapsed: int,
    cumulative_casualties_k: float,
    current_oil_price: float,
    current_inflation: float,
    current_approval: float,
    weeks_to_election: int,
    recent_shock: Optional[str] = None,
) -> float:
    """Update δ dynamically during a conflict based on incoming data.

    Real-world application: feed in weekly polling + economic data
    to get updated δ estimate.

    This is the key innovation: δ is NOT fixed. It evolves.
    """

    delta = base_delta

    # 1. Casualty accumulation (Mueller log-curve)
    if cumulative_casualties_k > 0.01:
        log_cas = math.log10(cumulative_casualties_k * 1000 + 1)
        delta -= log_cas * 0.01

    # 2. Oil price shock
    if current_oil_price > 120:
        delta -= (current_oil_price - 120) * 0.0003
    if current_oil_price > 180:
        delta -= (current_oil_price - 180) * 0.0008  # accelerating

    # 3. Inflation pain
    if current_inflation > 5:
        delta -= (current_inflation - 5) * 0.005

    # 4. Approval rating collapse
    if current_approval < 35:
        delta -= (35 - current_approval) * 0.002
    if current_approval < 25:
        delta -= (25 - current_approval) * 0.005  # panic zone

    # 5. Electoral deadline
    if weeks_to_election < 8:
        delta -= (8 - weeks_to_election) * 0.005
    if weeks_to_election < 4:
        delta -= 0.03  # crisis: must resolve NOW

    # 6. War fatigue (increases with time)
    fatigue = min(0.04, weeks_elapsed * 0.001)
    delta -= fatigue

    # 7. Shocks (can go either way)
    shock_effects = {
        "us_ship_sunk": -0.03,              # Pearl Harbor or Beirut barracks?
        "us_soldiers_killed": -0.04,        # massive drop
        "iran_nuclear_test": +0.02,         # re-justifies war
        "iran_leadership_killed": +0.02,    # victory narrative
        "oil_200": -0.05,                   # economic crisis
        "china_mediation": -0.01,           # diplomatic offramp
        "mass_civilian_casualties": -0.03,  # moral pressure
        "hostage_crisis": +0.03,            # can't leave now
    }
    if recent_shock and recent_shock in shock_effects:
        delta += shock_effects[recent_shock]

    return max(0.55, min(0.98, round(delta, 4)))


# ============================================================
# MAIN: Run all calibrations
# ============================================================

def main():
    print("=" * 80)
    print("HISTORICAL CALIBRATION OF DISCOUNT FACTORS (WAR PATIENCE)")
    print("=" * 80)

    # 1. Historical estimates
    print("\n\n--- HISTORICAL CONFLICT CALIBRATION ---")
    print(f"{'Conflict':<35s} {'Country':<8s} {'Weeks':>6s} {'Type':<14s} "
          f"{'Raw δ':>6s} {'Adj δ':>6s} {'Interpretation'}")
    print("-" * 115)

    all_conflicts = USA_CONFLICTS + ISRAEL_CONFLICTS + IRAN_CONFLICTS
    for c in all_conflicts:
        est = estimate_delta_from_conflict(c)
        interp = _interpret_delta(est["adjusted_delta"])[:45]
        print(f"{c.name:<35s} {c.country:<8s} {c.duration_weeks:6.1f} {c.war_type:<14s} "
              f"{est['raw_delta']:6.3f} {est['adjusted_delta']:6.3f} {interp}")

    # 2. Trump 2026 prediction
    print("\n\n--- TRUMP 2026 CALIBRATION ---")
    trump = calibrate_trump_2026()
    print(f"  Predicted δ (base):     {trump['predicted_delta']}")
    print(f"  Trump-adjusted δ:       {trump['trump_adjusted_delta']}")
    print(f"  Confidence interval:    {trump['confidence_interval']}")
    print(f"  Interpretation:         {trump['interpretation']}")
    print(f"\n  Adjustments:")
    for name, val in trump['adjustments']:
        print(f"    {name:<25s} {val:+.4f}")
    print(f"\n  Trump-specific notes:")
    for note in trump['trump_notes']:
        print(f"    - {note}")

    # 3. Iran 2026
    print("\n\n--- IRAN 2026 CALIBRATION ---")
    iran = calibrate_iran_2026()
    print(f"  Predicted δ (rational): {iran['predicted_delta']}")
    print(f"  Iran-Iraq War ref δ:    {iran['iran_iraq_reference_delta']}")
    print(f"  Current vs 1980:")
    for k, v in iran["current_vs_1980"].items():
        print(f"    {k}: {v}")

    # 4. Israel 2026
    print("\n\n--- ISRAEL 2026 CALIBRATION ---")
    israel = calibrate_israel_2026()
    print(f"  Predicted δ:            {israel['predicted_delta']}")
    print(f"  Confidence interval:    {israel['confidence_interval']}")
    print(f"  Historical context:")
    for k, v in israel["historical_context"].items():
        print(f"    {k}: {v}")

    # 5. Dynamic δ evolution example
    print("\n\n--- DYNAMIC δ EVOLUTION: TRUMP DURING 20-WEEK WAR ---")
    base = trump["trump_adjusted_delta"]
    print(f"  {'Week':>4s} {'Casualties':>10s} {'Oil':>6s} {'Inflation':>9s} "
          f"{'Approval':>8s} {'Midterms':>8s} {'Shock':<20s} {'δ':>6s}")
    print("-" * 85)

    scenarios = [
        (1,  0.01, 95,  3.2, 55, 35, None),
        (3,  0.03, 110, 3.5, 52, 33, None),
        (5,  0.08, 130, 4.2, 48, 31, "us_ship_sunk"),
        (7,  0.12, 145, 5.0, 42, 29, None),
        (9,  0.18, 160, 5.8, 38, 27, None),
        (11, 0.25, 155, 6.5, 35, 25, "iran_leadership_killed"),
        (13, 0.30, 150, 7.0, 33, 23, None),
        (15, 0.35, 170, 7.5, 30, 21, "oil_200"),
        (17, 0.42, 190, 8.5, 27, 19, "mass_civilian_casualties"),
        (20, 0.50, 180, 9.0, 25, 16, None),
    ]

    for wk, cas, oil, inf, apr, midterm, shock in scenarios:
        d = update_delta_realtime(base, wk, cas, oil, inf, apr, midterm, shock)
        shock_str = shock if shock else ""
        print(f"  {wk:4d} {cas:10.2f}K ${oil:5.0f} {inf:8.1f}% {apr:7.0f}% "
              f"{midterm:7d}w {shock_str:<20s} {d:6.3f}")

    # 6. What δ would need to be for different war durations
    print("\n\n--- δ THRESHOLDS BY WAR DURATION ---")
    print("  (minimum δ for USA to sustain war for N weeks)")
    print(f"  {'Duration':>10s} {'Required δ':>10s} {'Political meaning'}")
    print("-" * 60)
    duration_thresholds = [
        (3, 0.70, "Cosmetic strike only, no commitment"),
        (6, 0.78, "Limited campaign, accepts partial objectives"),
        (9, 0.83, "Standard air campaign to degradation"),
        (12, 0.87, "Sustained campaign with economic cost"),
        (15, 0.90, "Willing to accept recession risk"),
        (20, 0.93, "Post-9/11 level commitment"),
        (30, 0.96, "Existential — no price too high"),
    ]
    for dur, delta, meaning in duration_thresholds:
        print(f"  {dur:8d} wk {delta:10.2f}   {meaning}")


if __name__ == "__main__":
    main()
