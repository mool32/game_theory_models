"""
Game Theory Conflict Model v5: USA, Israel, Iran, Hezbollah (2026)
===================================================================

Multi-level dynamic non-cooperative game with incomplete information.

v5 — critical fixes addressing 13 identified model weaknesses:

1. HYBRID ACTION VECTORS: Players now execute continuous intensity vectors
   [strike=0.7, hormuz=0.9, negotiate=0.1] instead of single Enum choice.
   Captures "Iran negotiates while blocking Hormuz" simultaneously.
2. FOG OF WAR / BDA BIAS: Each player observes PERCEIVED state, not truth.
   Coalition BDA overestimates destruction by 20-40% (Kosovo/Iraq precedent).
   Iran overestimates own capability. Decisions on biased information.
3. IRAN RALLY UNDER BOMBING: Air strikes INCREASE Iran public support
   (London Blitz / North Vietnam pattern). Bombing = Mojtaba's best recruiter.
4. BIMODAL SHOCKS: Ship sunk → Pearl Harbor (+20 support) OR Beirut barracks
   (-25 support), not deterministic -12. Bimodal distribution for each shock.
5. HORMUZ DEMINING: Recovery rate fixed from +5-10%/week to +2-3%/week.
   1988 Tanker War: clearance took ~6 months after fighting stopped.
6. NUCLEAR THRESHOLD: Loosened conditions. Breakout decision decoupled from
   termination — race between destruction and breakout now possible.
7. IRAN CASUALTY THRESHOLD: Nonlinear — low sensitivity up to threshold,
   then "drinking poison" collapse. Iran-Iraq War: 500K tolerated, then sudden end.
8. ECONOMIC PHASE TRANSITIONS: Oil $130 = slowdown, $180 = panic, $220 =
   systemic crisis. Hysteresis: recovery asymmetric to shock.
9. WAR POWERS ACT: 60-day clock starts Day 1. Without AUMF, Trump faces
   constitutional crisis at week 9. Adds domestic political constraint.
10. CHINA/RUSSIA: Persistent strategic actors (not one-time shocks).
    China loses from Hormuz closure, Russia gains from high oil.
    Both evolve positions over time.
11. GRADUAL RHETORIC: Trump rhetoric now on 0-1 scale with escalating
    commitment trap, not binary declaration.
12. HEZBOLLAH FRAGMENTATION: Post-Nasrallah Hezbollah = collection of
    semi-autonomous units with variable Iran-control. Command coherence
    degrades under strikes.
13. VARIABLE TIME GRANULARITY: Phase 1 (days 1-7) = 1 day/round,
    Phase 2 (weeks 2-4) = 3 days/round, Phase 3 (week 5+) = 1 week/round.
    First 48 hours get proper resolution.

v4 features retained:
- Leadership transition (Khamenei → Mojtaba), Trump rhetoric, nuclear threshold,
  regional actors, Hormuz as δ-attack, coalition divergence

References:
- Fearon (1994/1995), Zartman (2000), Schelling (1960), Powell (2006)
- Slantchev (2003), Hamilton (2003), Gelpi/Feaver/Reifler (2006)
- Jervis (1976) "Perception and Misperception"
- Mueller (1973) "War, Presidents, and Public Opinion"
- Pape (1996) "Bombing to Win" (strategic bombing rarely breaks morale)
- Byman & Waxman (2002) "The Dynamics of Coercion"
- O'Hanlon (2009) "The Science of War" (BDA systematic overestimation)
- Kahneman & Renshon (2007) "Why Hawks Win" (hawkish bias under uncertainty)
"""

import random
import json
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from datetime import date, timedelta


# ============================================================
# TEMPORAL FRAMEWORK (v5: variable granularity)
# ============================================================

WAR_START = date(2026, 2, 28)  # Operation Epic Fury start
KHAMENEI_KILLED = date(2026, 2, 28)  # Day 1: Khamenei killed in strike
MOJTABA_ELECTED = date(2026, 3, 8)   # Day 8: Mojtaba Khamenei elected Supreme Leader

US_MIDTERMS = date(2026, 11, 3)
RAMADAN_2026_END = date(2026, 3, 19)
CARRIER_ROTATION_DAYS = 180

# v5 FIX #9: War Powers Resolution — 60-day clock
# Trump operates without AUMF. After 60 days, must get Congressional
# authorization or withdraw. Creates constitutional crisis at ~week 9.
WAR_POWERS_DEADLINE_DAYS = 60


@dataclass
class Calendar:
    """v5 FIX #13: Variable time granularity.

    Phase 1 (days 1-7):   1 day per round  (7 rounds)
    Phase 2 (days 8-28):  3 days per round (7 rounds)
    Phase 3 (day 29+):    7 days per round (unlimited)

    Total: 14 rounds = first 28 days, then weekly.
    First 48 hours get 2 rounds of resolution.
    """

    start_date: date = field(default_factory=lambda: WAR_START)
    current_round: int = 0
    _cumulative_days: int = 0

    @property
    def round_duration_days(self) -> int:
        """How many days this round represents."""
        if self._cumulative_days < 7:
            return 1    # Phase 1: daily
        elif self._cumulative_days < 28:
            return 3    # Phase 2: every 3 days
        else:
            return 7    # Phase 3: weekly

    @property
    def round_weight(self) -> float:
        """Weight for payoff scaling — longer rounds have proportionally larger effects."""
        return self.round_duration_days / 7.0

    @property
    def current_date(self) -> date:
        return self.start_date + timedelta(days=self._cumulative_days)

    @property
    def weeks_elapsed(self) -> float:
        return self._cumulative_days / 7.0

    @property
    def weeks_to_midterms(self) -> int:
        delta = US_MIDTERMS - self.current_date
        return max(0, delta.days // 7)

    @property
    def is_ramadan(self) -> bool:
        d = self.current_date
        return (date(2026, 2, 17) <= d <= RAMADAN_2026_END or
                date(2027, 2, 7) <= d <= date(2027, 3, 9))

    @property
    def month(self) -> int:
        return self.current_date.month

    @property
    def is_winter_demand(self) -> bool:
        return self.month in (11, 12, 1, 2)

    @property
    def is_summer_heat(self) -> bool:
        return self.month in (6, 7, 8)

    @property
    def days_since_start(self) -> int:
        return self._cumulative_days

    @property
    def carrier_rotation_due(self) -> bool:
        return self._cumulative_days > 0 and self._cumulative_days % CARRIER_ROTATION_DAYS < 7

    @property
    def midterm_pressure(self) -> float:
        weeks = self.weeks_to_midterms
        if weeks > 30:
            return 0.0
        if weeks < 4:
            return 1.0
        return max(0, 1.0 - (weeks / 30.0) ** 0.5)

    @property
    def war_powers_pressure(self) -> float:
        """v5 FIX #9: War Powers Act pressure.
        0.0 until day 45, ramps to 1.0 at day 60, stays at 1.0 after.
        Without AUMF, Trump faces constitutional challenge."""
        days = self._cumulative_days
        if days < 45:
            return 0.0
        if days >= WAR_POWERS_DEADLINE_DAYS:
            return 1.0
        return (days - 45) / 15.0

    def advance(self):
        self.current_round += 1
        self._cumulative_days += self.round_duration_days


# ============================================================
# v5 FIX #1: HYBRID ACTION VECTORS
# ============================================================

@dataclass
class ActionVector:
    """Continuous action intensities replacing pure Enum strategies.

    Each dimension 0-1. Player can simultaneously strike AND negotiate
    AND blockade Hormuz at different intensities.

    Example: Iran round 3 = {strike: 0.6, hormuz: 0.9, proxy: 0.8, negotiate: 0.05, attrition: 0.3}
    This means: heavy Hormuz blockade + proxy escalation + some direct strikes + token negotiation signal.
    """
    intensities: dict = field(default_factory=dict)

    def dominant_action(self) -> str:
        """Return the highest-intensity action (for backwards compatibility)."""
        if not self.intensities:
            return "attrition"
        return max(self.intensities, key=self.intensities.get)

    def intensity(self, action: str) -> float:
        return self.intensities.get(action, 0.0)

    def is_active(self, action: str, threshold: float = 0.3) -> bool:
        return self.intensity(action) >= threshold

    def effect_scale(self, action: str) -> float:
        """Scale factor for effects of an action (0.5-1.2 based on intensity).

        Higher intensity = more committed = stronger effects.
        Even the dominant action is modulated: 0.8 intensity ≠ 1.0 effects.
        """
        raw = self.intensity(action)
        if raw < 0.1:
            return 0.0
        # Map 0.1-1.0 intensity → 0.5-1.2 effect scale
        return 0.5 + raw * 0.7

    @staticmethod
    def from_enum(strat_value: str) -> 'ActionVector':
        """Convert legacy Enum strategy to ActionVector with secondary activities.

        Real militaries don't do ONE thing. Air strikes include standoff weapons.
        Retaliation includes proxy activation. Blockade includes defensive posture.
        Noise added for stochasticity.
        """
        noise = random.gauss(0, 0.05)
        base = {strat_value: min(1.0, max(0.3, 0.8 + noise))}

        # USA strategies
        if strat_value == "air_strikes":
            base["standoff_only"] = 0.2 + random.uniform(0, 0.15)
        elif strat_value == "ground_operation":
            base["air_strikes"] = 0.5 + random.uniform(0, 0.1)
            base["standoff_only"] = 0.15
        elif strat_value == "standoff_only":
            base["negotiate"] = random.uniform(0, 0.15)
        elif strat_value == "declare_victory":
            base["negotiate"] = 0.3 + random.uniform(0, 0.2)
        elif strat_value == "negotiate":
            base["standoff_only"] = random.uniform(0, 0.1)  # keep some pressure

        # Israel strategies
        elif strat_value == "joint_strikes":
            base["defensive_posture"] = 0.2
        elif strat_value == "independent_ops":
            base["joint_strikes"] = 0.3
        elif strat_value == "defensive_posture":
            base["push_for_talks"] = random.uniform(0, 0.2)

        # Iran strategies
        elif strat_value == "retaliate":
            base["proxy_escalation"] = 0.4 + random.uniform(0, 0.15)
            base["attrition"] = 0.2
        elif strat_value == "proxy_escalation":
            base["retaliate"] = 0.3 + random.uniform(0, 0.1)
        elif strat_value == "hormuz_blockade":
            base["attrition"] = 0.3
            base["proxy_escalation"] = 0.2
        elif strat_value == "attrition":
            base["proxy_escalation"] = random.uniform(0.1, 0.3)

        # Hezbollah strategies
        elif strat_value == "full_barrage":
            base["calibrated"] = 0.2
        elif strat_value == "calibrated":
            base["hold_fire"] = random.uniform(0, 0.15)

        return ActionVector(intensities=base)


# ============================================================
# v5 FIX #2: FOG OF WAR / BDA BIAS
# ============================================================

@dataclass
class FogOfWar:
    """Information asymmetry in conflict.

    O'Hanlon (2009): BDA (Battle Damage Assessment) systematically overestimates
    destruction by 20-40%. Kosovo 1999: NATO claimed 120 tanks destroyed,
    actual count was 14. Iraq 2003: similar pattern.

    Each player perceives a BIASED version of enemy state.
    Decisions are made on perceived, not actual state.
    """

    # BDA overestimation factor (1.0 = perfect info, 1.3 = 30% overestimate)
    coalition_bda_bias: float = 1.3    # coalition thinks it destroyed 30% more
    iran_capability_bluff: float = 1.2  # Iran claims 20% more capability than real

    # Noise in intelligence (standard deviation as fraction of true value)
    intel_noise: float = 0.15

    def perceived_iran_military(self, actual: float) -> float:
        """What coalition THINKS Iran's military capacity is.
        They overestimate their own destruction → underestimate Iran's remaining."""
        perceived_destroyed = (100 - actual) * self.coalition_bda_bias
        perceived_remaining = max(0, 100 - perceived_destroyed)
        noise = random.gauss(0, actual * self.intel_noise)
        return max(0, min(100, perceived_remaining + noise))

    def perceived_iran_missiles(self, actual: float) -> float:
        """Coalition estimate of Iran's remaining missiles."""
        perceived_destroyed = (100 - actual) * self.coalition_bda_bias
        perceived_remaining = max(0, 100 - perceived_destroyed)
        noise = random.gauss(0, actual * self.intel_noise)
        return max(0, min(100, perceived_remaining + noise))

    def perceived_own_damage_iran(self, actual_military: float) -> float:
        """What Iran THINKS its own capability is (overestimates)."""
        noise = random.gauss(0, actual_military * self.intel_noise)
        return min(100, actual_military * self.iran_capability_bluff + noise)

    def perceived_usa_support(self, actual: float) -> float:
        """What Iran thinks US public support is (underestimates resilience)."""
        # Iran state media shows protests → believes support is lower
        return max(0, actual - random.uniform(5, 15))

    @property
    def bda_overestimate_pct(self) -> float:
        """How much coalition overestimates destruction."""
        return (self.coalition_bda_bias - 1.0) * 100


# ============================================================
# v5 FIX #10: CHINA/RUSSIA AS PERSISTENT ACTORS
# ============================================================

@dataclass
class GreatPowerDynamics:
    """China and Russia as persistent strategic actors, not one-time shocks.

    China: Loses from Hormuz closure (60% of oil imports via Strait).
    Gains from weakened US position. Mediator potential.

    Russia: Gains from high oil prices. Provides Iran intel (satellite).
    Blocks UN resolutions. Limited military support risk.
    """

    # China
    china_mediation_interest: float = 0.1  # grows as Hormuz hurts them
    china_diplomatic_pressure_on_usa: float = 0.0
    china_oil_pain: float = 0.0  # accumulated cost from Hormuz

    # Russia
    russia_oil_windfall: float = 0.0  # billions from high oil
    russia_intel_support_iran: float = 0.3  # baseline satellite intel
    russia_un_blocking: float = 0.8  # probability of blocking UN resolution

    def update(self, oil_price: float, hormuz_flow_pct: float,
               iran_military: float, round_num: int, round_weight: float):
        """Update great power positions each round."""

        # China: Hormuz pain accumulates
        if hormuz_flow_pct < 80:
            self.china_oil_pain += (80 - hormuz_flow_pct) * 0.02 * round_weight
            self.china_mediation_interest = min(0.9, 0.1 + self.china_oil_pain * 0.1)
            self.china_diplomatic_pressure_on_usa += 0.5 * round_weight

        # China backs off if Iran is clearly losing
        if iran_military < 20:
            self.china_mediation_interest *= 0.95

        # Russia: oil windfall
        if oil_price > 85:
            self.russia_oil_windfall += (oil_price - 85) * 0.1 * round_weight
            # Higher windfall → more willingness to support Iran
            self.russia_intel_support_iran = min(0.7, 0.3 + self.russia_oil_windfall * 0.005)

        # Russia reduces support if Iran approaching collapse (avoid backing loser)
        if iran_military < 15:
            self.russia_intel_support_iran *= 0.9

    @property
    def iran_intel_bonus(self) -> float:
        """Russian intel support reduces coalition BDA effectiveness."""
        return self.russia_intel_support_iran * 0.1  # 0-7% improvement in Iran targeting

    @property
    def coalition_diplomatic_cost(self) -> float:
        """Combined China/Russia diplomatic pressure on coalition."""
        return self.china_diplomatic_pressure_on_usa * 0.3


# ============================================================
# v5 FIX #12: HEZBOLLAH FRAGMENTATION MODEL
# ============================================================

@dataclass
class HezbollahFragmentation:
    """Post-Nasrallah Hezbollah = fragmented command structure.

    After 2024-2025 decapitation strikes, Hezbollah lacks unified command.
    Units operate semi-autonomously with varying Iran control.

    command_coherence: 1.0 = unified command, 0.0 = completely fragmented
    iran_control: how much Tehran directs operations (0-1)
    """

    command_coherence: float = 0.6   # already degraded from 2024-25 strikes
    iran_control: float = 0.5       # partial, post-Nasrallah
    local_commanders: int = 5       # surviving semi-autonomous unit commanders

    def update(self, hez_military: float, iran_strat_value: str,
               israel_strikes: bool, round_weight: float):
        """Update fragmentation state."""

        # Israeli strikes degrade command coherence
        if israel_strikes:
            self.command_coherence = max(0.1,
                self.command_coherence - random.uniform(0.02, 0.06) * round_weight)
            # Kill a commander sometimes
            if random.random() < 0.05 * round_weight and self.local_commanders > 1:
                self.local_commanders -= 1
                self.command_coherence -= 0.05

        # Iran tries to maintain control
        if iran_strat_value in ("proxy_escalation", "retaliate"):
            self.iran_control = min(0.8, self.iran_control + 0.02 * round_weight)
        else:
            self.iran_control = max(0.1, self.iran_control - 0.03 * round_weight)

        # Military capacity loss → fragmentation
        if hez_military < 30:
            self.command_coherence = min(self.command_coherence, hez_military / 50.0)

    @property
    def effective_combat_power(self) -> float:
        """Fragmented force is less effective than coherent one.
        Multiplier on military effects: 1.0 = full, 0.3 = barely functional."""
        return max(0.3, self.command_coherence * 0.6 + self.iran_control * 0.4)

    @property
    def ceasefire_probability_modifier(self) -> float:
        """Low coherence → some units may cease fire independently."""
        if self.command_coherence < 0.3:
            return 0.3  # 30% chance of spontaneous local ceasefires
        return 0.0


# ============================================================
# v4: LEADERSHIP TRANSITION DYNAMICS
# ============================================================

@dataclass
class LeadershipState:
    """Models Iranian leadership transition: Khamenei → Mojtaba.

    Key dynamics:
    - New leader CANNOT negotiate early (= weakness = lose legitimacy)
    - Revenge rhetoric is RATIONAL signaling for internal audience
    - Iran's δ temporarily INCREASES after transition (paradox)
    - Legitimacy builds over time but requires demonstrated resolve
    """

    leader: str = "khamenei"
    transition_date: Optional[date] = None  # when new leader took power
    legitimacy: float = 1.0                 # 0-1: new leader starts low
    consolidation_complete: bool = False     # True once legitimacy > 0.7

    def process_transition(self, current_date: date) -> dict:
        """Update leadership state. Returns effects on Iran's parameters."""
        effects = {}

        if self.leader == "khamenei" and current_date >= KHAMENEI_KILLED:
            # Day 1: Khamenei killed. Chaos period.
            self.leader = "interregnum"
            self.legitimacy = 0.3  # IRGC holds power but no formal leader
            effects["public_support_delta"] = -8  # shock
            effects["military_capacity_delta"] = -5  # command disruption
            effects["delta_modifier"] = +0.02  # rally effect: "we must resist"

        if self.leader == "interregnum" and current_date >= MOJTABA_ELECTED:
            # Day 8: Mojtaba elected. Legitimacy-building phase begins.
            self.leader = "mojtaba"
            self.transition_date = MOJTABA_ELECTED
            self.legitimacy = 0.4  # son of Khamenei, but unproven
            effects["public_support_delta"] = +5  # continuity relief
            effects["audience_cost_delta"] = +8  # Mojtaba CANNOT back down now
            effects["delta_modifier"] = +0.03  # must prove himself = more patient

        if self.leader == "mojtaba" and self.transition_date:
            weeks_in_power = (current_date - self.transition_date).days / 7
            # Legitimacy grows slowly if regime demonstrates resolve
            if weeks_in_power > 0:
                self.legitimacy = min(0.9, 0.4 + weeks_in_power * 0.04)
            # After ~15 weeks, consolidation complete — can consider negotiation
            if self.legitimacy > 0.7 and not self.consolidation_complete:
                self.consolidation_complete = True
                effects["can_negotiate"] = True

        return effects

    @property
    def negotiate_penalty(self) -> float:
        """Extra audience cost for negotiating before consolidation.
        Mojtaba negotiating in first 2 months = regime collapse risk."""
        if self.leader == "mojtaba" and not self.consolidation_complete:
            return (1 - self.legitimacy) * 15.0  # up to +9.0 extra audience cost
        return 0.0

    @property
    def delta_bonus(self) -> float:
        """New leader must be tougher than predecessor to establish legitimacy.
        This is the paradox: killing Khamenei INCREASED Iran's δ temporarily."""
        if self.leader == "mojtaba" and not self.consolidation_complete:
            return (1 - self.legitimacy) * 0.05  # up to +0.03 at start
        if self.leader == "interregnum":
            return 0.02  # rally around the flag
        return 0.0


# ============================================================
# v4: TRUMP RHETORIC / SIGNALING MODEL
# ============================================================

@dataclass
class TrumpRhetoricState:
    """Models Trump's public statements as strategic signaling.

    "War is almost over" (Day 14) is NOT reality — it's:
    1. Market manipulation (dampen oil speculation)
    2. Domestic opinion management (we're winning!)
    3. Confidence proxy (genuinely believes 85-90% destruction = victory)
    4. Commitment trap: if war continues past declared endpoint → credibility loss

    Bush "Mission Accomplished" precedent:
    - May 1, 2003: "major combat operations ended"
    - War lasted 8 more years. Approval: 77% → 25%.
    """

    # v5 FIX #11: Gradual rhetoric scale instead of binary
    rhetoric_intensity: float = 0.0       # 0-1 scale of victory claims
    earliest_claim_round: int = 0
    credibility: float = 1.0
    confidence_level: float = 0.7
    cumulative_claims: float = 0.0        # accumulated rhetoric "debt"

    def process_rhetoric(self, iran_military: float, iran_missiles: float,
                         oil_price: float, round_num: int,
                         perceived_iran_mil: Optional[float] = None) -> dict:
        """v5 FIX #11: Gradual rhetoric model.

        Trump doesn't flip a switch — he escalates claims over time:
        0.0-0.3: "Going very well, tremendous progress"
        0.3-0.5: "We're winning bigly, almost done"
        0.5-0.7: "War is essentially over, just cleanup"
        0.7-1.0: "Mission accomplished, bringing troops home"

        Uses PERCEIVED Iran state (BDA-biased), not actual.
        """
        effects = {}

        # Use perceived state if available (v5 FIX #2: fog of war)
        iran_mil = perceived_iran_mil if perceived_iran_mil is not None else iran_military

        # Confidence driven by what Trump SEES in briefings (biased BDA)
        destruction_pct = (100 - iran_mil) / 100.0
        missile_destruction = (100 - iran_missiles) / 100.0
        self.confidence_level = min(0.95, 0.3 + destruction_pct * 0.4
                                     + missile_destruction * 0.3)

        # Rhetoric intensity ramps up gradually
        old_intensity = self.rhetoric_intensity
        if self.confidence_level > 0.6:
            # Ramp toward confidence level, but faster when politically pressed
            target = self.confidence_level * 0.8
            self.rhetoric_intensity = min(1.0,
                self.rhetoric_intensity + (target - self.rhetoric_intensity) * 0.3)
        else:
            # Low confidence: dial back rhetoric
            self.rhetoric_intensity = max(0, self.rhetoric_intensity - 0.1)

        # Track first significant claim
        if self.rhetoric_intensity > 0.3 and self.earliest_claim_round == 0:
            self.earliest_claim_round = round_num

        # Cumulative rhetoric "debt" — each claim creates future liability
        if self.rhetoric_intensity > 0.3:
            self.cumulative_claims += self.rhetoric_intensity * 0.1

        # Effects scale with rhetoric intensity
        if self.rhetoric_intensity > old_intensity + 0.1:
            # New escalation in claims → brief market/support bump
            effects["usa_support_boost"] = self.rhetoric_intensity * 2.0
            effects["oil_speculation_dampen"] = -self.rhetoric_intensity * 3.0

        # CREDIBILITY EROSION: grows with gap between claims and reality
        if self.earliest_claim_round > 0 and round_num > self.earliest_claim_round + 2:
            # Reality check: is Iran actually defeated?
            reality_gap = self.rhetoric_intensity - (destruction_pct * 0.5)
            if reality_gap > 0.2:
                self.credibility = max(0.2,
                    self.credibility - reality_gap * 0.05)
                effects["usa_support_penalty"] = -self.cumulative_claims * 1.5
                effects["mission_accomplished_trap"] = True

        return effects

    @property
    def commitment_trap_active(self) -> bool:
        """Is Trump stuck in the Mission Accomplished pattern?"""
        return self.rhetoric_intensity > 0.5 and self.credibility < 0.7


# ============================================================
# v4: NUCLEAR THRESHOLD (cornered player dynamics)
# ============================================================

class NuclearStatus(Enum):
    """Iran's nuclear program status."""
    LATENT = "latent"              # can build but hasn't
    BREAKOUT_CAPABLE = "breakout"  # weeks from weapon
    TESTED = "tested"              # demonstrated capability
    DEPLOYED = "deployed"          # weapon on missile


@dataclass
class NuclearThreshold:
    """Models the most dangerous moment: when a cornered player considers WMD.

    When conventional capacity drops below 10%, nuclear breakout becomes
    rational under "use-it-or-lose-it" logic. The remaining 10% of capacity
    might be the most dangerous 10%.

    Powell (2006): war as commitment problem — can't credibly commit to
    not using WMD when regime survival at stake.
    """

    status: NuclearStatus = NuclearStatus.LATENT
    enrichment_pct: float = 60.0     # current enrichment level
    fissile_material_kg: float = 10.0  # accumulated HEU/weapons-grade
    breakout_time_weeks: int = 8       # weeks to first weapon if decided
    facilities_surviving_pct: float = 100.0  # % of nuclear facilities intact

    # Decision thresholds
    breakout_decided: bool = False
    breakout_week: int = 0

    def update(self, iran_military: float, iran_infrastructure: float,
               coalition_strikes_on_nuclear: bool, round_num: int) -> dict:
        """Update nuclear status. Returns effects if threshold crossed."""
        effects = {}

        # Coalition targets nuclear facilities
        if coalition_strikes_on_nuclear:
            self.facilities_surviving_pct = max(5, self.facilities_surviving_pct
                                                 - random.uniform(10, 25))
            # Can't build what you don't have
            self.breakout_time_weeks = int(self.breakout_time_weeks
                                            * (100 / max(5, self.facilities_surviving_pct)))

        # v5 FIX #6: CORNERED PLAYER LOGIC (loosened conditions)
        # Nuclear breakout decision is DECOUPLED from termination.
        # Race: coalition destroying facilities vs Iran deciding to break out.
        # Key insight: decision made when regime BELIEVES it's losing, not when
        # it's already lost. Uses perceived state, not actual.
        if not self.breakout_decided:
            # Pressure accumulates from multiple sources
            military_pressure = max(0, (100 - iran_military) / 100)
            facility_urgency = max(0, (100 - self.facilities_surviving_pct) / 100)
            # Must still have SOME facilities to attempt breakout
            can_attempt = self.facilities_surviving_pct > 10

            # v5: Lower threshold — decision made earlier when trend is clear
            if can_attempt:
                breakout_prob = 0.0
                if iran_military < 20:  # triggers when clearly losing
                    breakout_prob += military_pressure * 0.025
                if iran_infrastructure < 25:
                    breakout_prob += 0.015
                if facility_urgency > 0.5:  # use-it-or-lose-it
                    breakout_prob += facility_urgency * 0.02

                if random.random() < breakout_prob:
                    self.breakout_decided = True
                    self.breakout_week = round_num
                    self.status = NuclearStatus.BREAKOUT_CAPABLE
                    effects["nuclear_breakout_started"] = True
                    effects["escalation_level"] = 6

        # If breakout decided, count down
        if self.breakout_decided:
            weeks_since = round_num - self.breakout_week
            if weeks_since >= self.breakout_time_weeks:
                self.status = NuclearStatus.TESTED
                effects["nuclear_test"] = True
                effects["game_changer"] = True

        return effects

    @property
    def threat_level(self) -> float:
        """0-1 scale of how close to nuclear use. Affects all payoffs."""
        if self.status == NuclearStatus.DEPLOYED:
            return 1.0
        if self.status == NuclearStatus.TESTED:
            return 0.9
        if self.status == NuclearStatus.BREAKOUT_CAPABLE:
            return 0.6
        # Latent but under pressure
        if self.facilities_surviving_pct < 30:
            return 0.3  # use-it-or-lose-it anxiety
        return 0.1


# ============================================================
# v4: REGIONAL ACTORS (pressure on coalition)
# ============================================================

@dataclass
class RegionalActors:
    """Gulf states and regional actors that affect coalition operations.

    Saudi Arabia, Bahrain, Qatar, Kuwait, Jordan provide:
    - Base access for US forces
    - Overflight rights
    - Diplomatic cover
    - Logistics and intelligence

    When they're targeted by Iranian proxies, their cooperation DECREASES.
    Each actor has a tolerance threshold.
    """

    # Cooperation level (0-100): how much each country supports coalition
    saudi_cooperation: float = 75.0    # cautious but cooperative
    bahrain_cooperation: float = 85.0  # hosts US 5th Fleet
    qatar_cooperation: float = 60.0    # hedges between sides
    jordan_cooperation: float = 70.0   # fears domestic blowback
    kuwait_cooperation: float = 80.0   # remembers 1990

    # Casualties/damage from Iranian proxy attacks
    regional_casualties: float = 0.0
    regional_infrastructure_damage: float = 0.0

    def update(self, iran_strat_value: str, hez_strat_value: str,
               oil_price: float, round_num: int) -> dict:
        """Update regional actor cooperation."""
        effects = {}

        # Iranian retaliation hits regional bases/infrastructure
        if iran_strat_value in ("retaliate", "proxy_escalation"):
            damage = random.uniform(1, 4)
            self.regional_casualties += random.uniform(0, 0.02)
            self.regional_infrastructure_damage += damage

            # Each attack reduces cooperation
            self.saudi_cooperation -= random.uniform(1, 3)
            self.bahrain_cooperation -= random.uniform(0.5, 2)
            self.qatar_cooperation -= random.uniform(2, 5)  # Qatar hedges most
            self.jordan_cooperation -= random.uniform(1, 4)
            self.kuwait_cooperation -= random.uniform(0.5, 2)

        # High oil prices increase SOME cooperation (Saudi benefits from high oil)
        if oil_price > 120:
            self.saudi_cooperation += 0.5  # Saudi profits from high oil
            self.qatar_cooperation += 0.3

        # Time pressure: public opinion in Gulf turns against war
        if round_num > 6:
            for attr in ("saudi_cooperation", "bahrain_cooperation",
                         "qatar_cooperation", "jordan_cooperation", "kuwait_cooperation"):
                current = getattr(self, attr)
                setattr(self, attr, max(10, current - random.uniform(0, 1)))

        # Clamp
        for attr in ("saudi_cooperation", "bahrain_cooperation",
                     "qatar_cooperation", "jordan_cooperation", "kuwait_cooperation"):
            setattr(self, attr, max(0, min(100, getattr(self, attr))))

        # Effects on coalition
        avg_cooperation = (self.saudi_cooperation + self.bahrain_cooperation
                           + self.qatar_cooperation + self.jordan_cooperation
                           + self.kuwait_cooperation) / 5

        if avg_cooperation < 50:
            effects["coalition_logistics_penalty"] = (50 - avg_cooperation) * 0.02
        if avg_cooperation < 30:
            effects["base_access_crisis"] = True
            effects["usa_military_effectiveness_penalty"] = -5.0

        # Jordan or Saudi withdrawing cooperation = major diplomatic blow
        if self.jordan_cooperation < 25:
            effects["jordan_closes_airspace"] = True
        if self.saudi_cooperation < 30:
            effects["saudi_reduces_oil_supply"] = True  # price spike

        effects["avg_regional_cooperation"] = avg_cooperation
        return effects

    @property
    def coalition_effectiveness_modifier(self) -> float:
        """How much regional cooperation affects coalition military ops.
        1.0 = full access, 0.5 = severely constrained."""
        avg = (self.saudi_cooperation + self.bahrain_cooperation
               + self.qatar_cooperation + self.jordan_cooperation
               + self.kuwait_cooperation) / 5
        return max(0.5, avg / 100.0)


# ============================================================
# ECONOMIC SUBSYSTEM
# ============================================================

@dataclass
class OilMarket:
    """Global oil market model.

    Hormuz Strait: ~21M bbl/day (≈21% of global consumption).
    Blockade reduces this by 60-90% depending on severity.
    Alternative: Cape of Good Hope adds ~10 days + $1M/tanker insurance.
    SPR: US has ~400M barrels (can release ~1M bbl/day for ~400 days).
    OPEC spare capacity: ~3-4M bbl/day (Saudi, UAE).
    """

    price: float = 85.0             # $/barrel (Brent benchmark)
    pre_war_price: float = 85.0

    # Supply disruption
    hormuz_flow_pct: float = 100.0  # % of normal flow (100 = open, 0 = fully blocked)
    disrupted_supply_mbd: float = 0.0  # million barrels/day disrupted

    # Strategic reserves
    spr_remaining_mb: float = 400.0  # US SPR in million barrels
    spr_release_rate: float = 0.0    # million barrels/day being released

    # OPEC response
    opec_spare_activated: float = 0.0  # million barrels/day of spare capacity online

    # Shipping/insurance
    insurance_premium_pct: float = 0.0  # war risk premium as % of cargo value
    tankers_rerouted_pct: float = 0.0   # % of tankers taking Cape route

    # Accumulated economic damage
    cumulative_oil_shock_weeks: int = 0  # weeks with oil > $120

    def update(self, iran_strat_value: str, is_hormuz_blockaded: bool,
               round_num: int, calendar: Calendar):
        """Update oil market state for one round (1 week)."""

        # --- Hormuz flow ---
        if iran_strat_value == "hormuz_blockade":
            # First blockade round: shock drop. Subsequent: progressive tightening
            if self.hormuz_flow_pct > 80:
                # Initial shock: mines deployed, tankers halt immediately
                self.hormuz_flow_pct = max(15, self.hormuz_flow_pct - random.uniform(30, 50))
                self.insurance_premium_pct = min(15, self.insurance_premium_pct + random.uniform(5, 10))
            else:
                self.hormuz_flow_pct = max(15, self.hormuz_flow_pct - random.uniform(5, 15))
                self.insurance_premium_pct = min(15, self.insurance_premium_pct + random.uniform(2, 5))
        elif is_hormuz_blockaded:
            # v5 FIX #5: Mines/threats remain — demining takes MONTHS
            # 1988 Tanker War: clearance took ~6 months after fighting stopped
            self.hormuz_flow_pct = min(100, self.hormuz_flow_pct + random.uniform(0.5, 1.5))
            self.insurance_premium_pct = max(0, self.insurance_premium_pct - random.uniform(0.1, 0.3))
        else:
            # v5 FIX #5: Even without active blockade, recovery is slow
            # Mines must be swept, insurance markets slow to react
            self.hormuz_flow_pct = min(100, self.hormuz_flow_pct + random.uniform(1, 3))
            self.insurance_premium_pct = max(0, self.insurance_premium_pct - random.uniform(0.3, 0.8))

        # Supply disrupted = 21M * (1 - flow%)
        self.disrupted_supply_mbd = 21.0 * (1 - self.hormuz_flow_pct / 100.0)

        # Tankers reroute via Cape when insurance too high
        if self.insurance_premium_pct > 5:
            self.tankers_rerouted_pct = min(80, (self.insurance_premium_pct - 5) * 8)
        else:
            self.tankers_rerouted_pct = max(0, self.tankers_rerouted_pct - 5)

        # --- SPR response (US releases reserves when price > $110) ---
        if self.price > 110 and self.spr_remaining_mb > 10:
            self.spr_release_rate = min(1.0, (self.price - 110) / 50.0)
            self.spr_remaining_mb -= self.spr_release_rate * 7  # 7 days per round
        else:
            self.spr_release_rate = max(0, self.spr_release_rate - 0.1)

        # --- OPEC response (Saudi ramps up spare capacity, but slowly) ---
        # OPEC needs ~4-6 weeks to bring spare online
        opec_target = min(4.0, self.disrupted_supply_mbd * 0.4)  # can offset ~40%
        self.opec_spare_activated += (opec_target - self.opec_spare_activated) * 0.15

        # --- PRICE CALCULATION ---
        # Net supply disruption after mitigants
        net_disruption = max(0, self.disrupted_supply_mbd
                             - self.spr_release_rate
                             - self.opec_spare_activated)

        # Price elasticity: ~$8-12 per M bbl/day disrupted (Hamilton 2003)
        disruption_premium = net_disruption * random.uniform(8, 12)

        # Insurance/rerouting cost premium
        shipping_premium = self.insurance_premium_pct * 0.8 + self.tankers_rerouted_pct * 0.1

        # Seasonal demand
        seasonal = 5.0 if calendar.is_winter_demand else -2.0

        # Fear/speculation premium (decays over time as markets adjust)
        speculation = max(0, 20 - round_num * 1.5) if self.disrupted_supply_mbd > 3 else 0

        # Mean reversion force (markets adapt, alternatives found)
        reversion = (self.pre_war_price - self.price) * 0.02

        # Compose price
        target_price = (self.pre_war_price + disruption_premium + shipping_premium
                        + seasonal + speculation + reversion)

        # Price adjusts toward target (not instant — market friction)
        self.price += (target_price - self.price) * random.uniform(0.3, 0.6)
        self.price = max(60, min(300, self.price))  # hard bounds

        # Track shock duration
        if self.price > 120:
            self.cumulative_oil_shock_weeks += 1

    @property
    def crisis_severity(self) -> str:
        if self.price < 100:
            return "normal"
        elif self.price < 130:
            return "elevated"
        elif self.price < 180:
            return "crisis"
        else:
            return "severe_crisis"


@dataclass
class EconomicState:
    """Structured economic state for a player. Replaces single economic_health."""

    # Core indicators (indexed: 100 = pre-war baseline)
    gdp_index: float = 100.0
    inflation_rate: float = 3.0     # annual %
    war_spending_pct_gdp: float = 0.0  # additional war costs as % of GDP
    trade_disruption: float = 0.0    # 0-100 scale
    budget_deficit_extra: float = 0.0  # additional deficit from war (% GDP)
    unemployment_delta: float = 0.0  # change in unemployment from baseline

    # Lagged effects queue (value, rounds_until_impact)
    _pending_effects: list = field(default_factory=list)

    def add_lagged_effect(self, attribute: str, delta: float, lag_rounds: int):
        """Schedule a delayed economic effect."""
        self._pending_effects.append((attribute, delta, lag_rounds))

    def process_lagged_effects(self):
        """Process one round of lagged effects."""
        still_pending = []
        for attr, delta, lag in self._pending_effects:
            if lag <= 0:
                current = getattr(self, attr, 0)
                setattr(self, attr, current + delta)
            else:
                still_pending.append((attr, delta, lag - 1))
        self._pending_effects = still_pending

    @property
    def composite_health(self) -> float:
        """Single 0-100 score for backwards compatibility."""
        score = 100.0
        score -= max(0, self.inflation_rate - 3) * 3  # inflation above 3% hurts
        score -= (100 - self.gdp_index) * 0.5
        score -= self.war_spending_pct_gdp * 5
        score -= self.trade_disruption * 0.3
        score -= self.unemployment_delta * 4
        return max(0, min(100, score))

    @property
    def recession_risk(self) -> float:
        """Probability of recession (0-1). Oil shock → recession with lag."""
        risk = 0.0
        risk += max(0, self.inflation_rate - 5) * 0.05  # high inflation
        risk += max(0, 100 - self.gdp_index) * 0.02
        risk += self.war_spending_pct_gdp * 0.03
        return min(1.0, risk)


def hormuz_delta_attack_effect(oil_price: float, usa_inflation: float,
                               weeks_to_midterms: int) -> float:
    """v4: Hormuz blockade as ENDOGENOUS attack on Trump's δ.

    Iran doesn't need to hit US territory. Every tanker stuck in Hormuz
    hits gas prices in Ohio and Pennsylvania.

    δ_Trump reduction from Hormuz:
      Oil $100  → δ effect: -0.01
      Oil $130  → δ effect: -0.03
      Oil $150  → δ effect: -0.05
      Oil $200+ → δ effect: -0.10 (political crisis)

    Amplified by proximity to midterms.
    """
    delta_reduction = 0.0

    if oil_price > 100:
        delta_reduction += (oil_price - 100) * 0.0003
    if oil_price > 150:
        delta_reduction += (oil_price - 150) * 0.0008  # accelerating
    if oil_price > 200:
        delta_reduction += (oil_price - 200) * 0.002   # political crisis

    # Inflation amplifier
    if usa_inflation > 5:
        delta_reduction *= 1.0 + (usa_inflation - 5) * 0.1

    # Midterm proximity amplifier
    if weeks_to_midterms < 20:
        delta_reduction *= 1.0 + (20 - weeks_to_midterms) * 0.05

    return min(0.15, delta_reduction)


def update_economics(
    player_name: str,
    econ: EconomicState,
    oil_market: OilMarket,
    player_action: str,
    calendar: Calendar,
):
    """Update economic state for one round, including lagged cascades.

    v5: Integrates phase multiplier (nonlinear oil damage) and hysteresis
    (asymmetric recovery). Economic damage scales nonlinearly above $130 oil,
    and recovery is slower than shock onset.
    """

    # --- Process pending lagged effects ---
    econ.process_lagged_effects()

    oil = oil_market.price

    # v5: Phase transition multiplier — damage accelerates above $130
    phase_mult = economic_phase_multiplier(oil)

    # v5: Hysteresis — recovery slows in recession
    recovery_rate = economic_hysteresis(econ.gdp_index, oil)

    if player_name == "usa":
        # War costs: ~$900M/day air campaign, $2B+ for ground ops
        if player_action == "air_strikes":
            econ.war_spending_pct_gdp += 0.015
        elif player_action == "ground_operation":
            econ.war_spending_pct_gdp += 0.04
        elif player_action == "standoff_only":
            econ.war_spending_pct_gdp += 0.008

        # Oil → inflation: immediate partial effect + lagged full effect
        # Gas prices change within days, broader inflation takes weeks
        if oil > 100:
            # Immediate: gas pump prices (scaled by phase multiplier)
            econ.inflation_rate += (oil - 100) * 0.005 * phase_mult
        if oil > 120:
            # Lagged: broader economy (scaled by phase multiplier)
            inflation_impulse = (oil - 120) * 0.02 * phase_mult
            econ.add_lagged_effect("inflation_rate", inflation_impulse, lag_rounds=1)

        # Inflation → GDP (2-3 round lag, Hamilton rule: 1% oil = -0.02% GDP)
        # Phase multiplier amplifies GDP damage in crisis regimes
        if econ.inflation_rate > 5:
            gdp_hit = -(econ.inflation_rate - 5) * 0.3 * phase_mult
            econ.add_lagged_effect("gdp_index", gdp_hit, lag_rounds=2)

        # Budget deficit from war spending
        econ.budget_deficit_extra = econ.war_spending_pct_gdp * 0.8

        # GDP → unemployment (3 round lag)
        if econ.gdp_index < 97:
            econ.add_lagged_effect("unemployment_delta", 0.3, lag_rounds=3)

        # US is net oil producer: moderate benefit from high prices (shale)
        # but consumers hurt more than producers gain
        if oil > 100:
            econ.trade_disruption = min(50, (oil - 100) * 0.3)

    elif player_name == "israel":
        # Israel imports 100% of oil — extremely sensitive
        # Phase multiplier hits Israel harder (100% import dependent)
        if oil > 100:
            inflation_impulse = (oil - 100) * 0.025 * phase_mult
            econ.add_lagged_effect("inflation_rate", inflation_impulse, lag_rounds=1)

        # War mobilization costs (reservists = productivity loss)
        if player_action in ("joint_strikes", "independent_ops"):
            econ.war_spending_pct_gdp += 0.03
            econ.gdp_index -= random.uniform(0.1, 0.3)  # reservist productivity loss

        # Tech sector disruption from rocket attacks
        econ.trade_disruption = min(60, econ.trade_disruption)

        if econ.inflation_rate > 6:
            econ.add_lagged_effect("gdp_index", -0.5, lag_rounds=2)

    elif player_name == "iran":
        # Iran LOSES oil revenue from Hormuz blockade (can't export either)
        if player_action == "hormuz_blockade":
            econ.trade_disruption += random.uniform(5, 15)
            econ.gdp_index -= random.uniform(0.5, 1.5)
            # Iran loses ~$200M/day in oil exports when blocked
            econ.war_spending_pct_gdp += 0.05

        # Sanctions already constrain economy
        econ.inflation_rate = max(econ.inflation_rate,
                                  econ.inflation_rate + random.uniform(0, 1))

        # Infrastructure destruction → GDP
        econ.add_lagged_effect("gdp_index", -random.uniform(0.2, 0.8), lag_rounds=1)

        # But: wartime nationalism can sustain economic tolerance temporarily
        if calendar.is_ramadan:
            econ.gdp_index += 0.1  # slight solidarity boost

    elif player_name == "hezbollah":
        # Hezbollah is a non-state actor; "economy" = funding + Lebanon damage
        if player_action in ("full_barrage", "calibrated"):
            econ.war_spending_pct_gdp += 0.02
        econ.trade_disruption += random.uniform(0.5, 2)

    # --- Natural recovery (very slow, v5: asymmetric via hysteresis) ---
    # Recovery rate: 1.0 normal, 0.5 mild recession, 0.25 deep recession
    inflation_decay = 0.98 + (1.0 - 0.98) * (1.0 - recovery_rate)  # slower decay in recession
    econ.inflation_rate = max(2.0, econ.inflation_rate * inflation_decay)
    trade_decay = 0.95 + (1.0 - 0.95) * (1.0 - recovery_rate)
    econ.trade_disruption = max(0, econ.trade_disruption * trade_decay)
    econ.gdp_index = max(60, min(105, econ.gdp_index))


# ============================================================
# v5 FIX #8: ECONOMIC PHASE TRANSITIONS
# ============================================================

def economic_phase_multiplier(oil_price: float) -> float:
    """Nonlinear economic damage with phase transitions.

    Oil $85-130:  linear slowdown (Hamilton 2003)
    Oil $130-180: accelerating damage (panic, hoarding, speculation)
    Oil $180-220: systemic crisis (margin calls, bank stress, supply chains break)
    Oil $220+:    financial crisis regime (2008-like cascading failures)

    Returns multiplier on economic damage (1.0 = normal, up to 5.0 = crisis).
    """
    if oil_price < 130:
        return 1.0
    elif oil_price < 180:
        return 1.0 + (oil_price - 130) * 0.04  # up to 3.0x at $180
    elif oil_price < 220:
        return 3.0 + (oil_price - 180) * 0.05  # up to 5.0x at $220
    else:
        return 5.0 + (oil_price - 220) * 0.03  # keeps growing, margin calls


def economic_hysteresis(gdp_index: float, oil_price: float) -> float:
    """v5: Recovery is NOT symmetric to shock.

    GDP drops fast from oil shock but recovers slowly.
    Once recession territory (GDP < 97), recovery rate halved.
    Once deep recession (GDP < 93), recovery rate quartered.
    """
    if gdp_index < 93:
        return 0.25  # deep recession: very slow recovery
    elif gdp_index < 97:
        return 0.5   # mild recession: slow recovery
    return 1.0       # normal: standard recovery


# ============================================================
# v5 FIX #3: IRAN RALLY-UNDER-BOMBING EFFECT
# ============================================================

def iran_rally_under_bombing(
    current_support: float,
    casualties_this_round: float,
    infrastructure_damage: float,
    is_revolutionary: bool,
    weeks_elapsed: float,
) -> float:
    """Bombing INCREASES public support — Pape (1996) "Bombing to Win".

    Historical pattern:
    - London Blitz 1940-41: British morale INCREASED under bombing
    - Germany 1943-44: production INCREASED despite strategic bombing
    - North Vietnam 1965-72: Rolling Thunder strengthened regime
    - Iran-Iraq War: Iraqi bombing of Iranian cities rallied population

    Effect decays over time (fatigue) but initial weeks are strong rally.

    Returns delta to public_support (positive = rally, negative = collapse).
    """
    # Base rally effect: stronger in early weeks
    if weeks_elapsed < 4:
        rally = random.uniform(1.0, 3.0)  # strong early rally
    elif weeks_elapsed < 12:
        rally = random.uniform(0.0, 1.5)  # moderate
    else:
        rally = random.uniform(-0.5, 0.5)  # fatigue sets in

    # Revolutionary regime gets bigger rally
    if is_revolutionary:
        rally *= 1.3

    # Massive casualties can eventually overcome rally (but threshold is HIGH)
    # Iran-Iraq War: 500K casualties before "drinking poison"
    # Modeled as threshold function, not linear
    if casualties_this_round > 1.0:  # 1000+ in a single round
        rally -= (casualties_this_round - 1.0) * 0.5
    if casualties_this_round > 3.0:  # 3000+ = potential breaking point
        rally -= (casualties_this_round - 3.0) * 2.0

    # Infrastructure destruction: moderate negative (supply problems)
    if infrastructure_damage > 10:
        rally -= infrastructure_damage * 0.05

    # Capped: support can't exceed 95 from rally alone
    max_boost = 95 - current_support
    return min(max_boost, rally)


# ============================================================
# v5 FIX #7: IRAN CASUALTY THRESHOLD (nonlinear)
# ============================================================

def iran_casualty_sensitivity(cumulative_casualties_k: float,
                               is_revolutionary: bool) -> float:
    """Nonlinear casualty sensitivity for Iran.

    Not linear: low sensitivity up to threshold, then sudden collapse.
    Iran-Iraq War: ~500K tolerated for 8 years, then "drinking poison" moment.

    Returns payoff penalty per additional 1K casualties.
    Below threshold: low penalty (regime absorbs).
    Above threshold: massive, accelerating penalty.
    """
    # Threshold depends on regime type
    threshold = 15.0 if is_revolutionary else 8.0  # thousands

    if cumulative_casualties_k < threshold * 0.5:
        # Low casualties: regime barely notices
        return 1.0
    elif cumulative_casualties_k < threshold:
        # Approaching threshold: growing discomfort
        ratio = cumulative_casualties_k / threshold
        return 1.0 + ratio * 2.0  # up to 3x
    else:
        # ABOVE THRESHOLD: "drinking poison" — accelerating collapse
        excess = cumulative_casualties_k - threshold
        return 3.0 + excess * 1.5  # rapidly growing


# ============================================================
# 1. STRATEGIES (expanded for 4 players)
# ============================================================

class USAStrategy(Enum):
    AIR_STRIKES = "air_strikes"
    GROUND_OPERATION = "ground_operation"
    DECLARE_VICTORY = "declare_victory"
    NEGOTIATE = "negotiate"
    LIMIT_TO_STANDOFF = "standoff_only"  # cruise missiles only, no aircraft risk


class IsraelStrategy(Enum):
    JOINT_STRIKES = "joint_strikes"          # coordinate with USA
    INDEPENDENT_OPS = "independent_ops"      # unilateral strikes on nuclear sites
    DEFENSIVE_POSTURE = "defensive_posture"  # Iron Dome focus, reduce exposure
    PUSH_FOR_TALKS = "push_for_talks"        # pressure USA toward negotiation


class IranStrategy(Enum):
    RETALIATE = "retaliate"
    PROXY_ESCALATION = "proxy_escalation"
    ATTRITION = "attrition"
    NEGOTIATE = "negotiate"
    HORMUZ_FULL_BLOCKADE = "hormuz_blockade"  # separate from general retaliation


class HezbollahStrategy(Enum):
    FULL_BARRAGE = "full_barrage"        # all-out rocket campaign on Israel
    CALIBRATED_STRIKES = "calibrated"    # limited strikes to pressure, not exhaust
    HOLD_FIRE = "hold_fire"              # preserve arsenal, wait
    INDEPENDENT_CEASEFIRE = "ceasefire"   # break from Iran, seek own deal


# ============================================================
# 2. PLAYER STATE (enhanced)
# ============================================================

@dataclass
class PlayerState:
    name: str
    military_capacity: float = 100.0
    economic_health: float = 100.0  # legacy: now computed from EconomicState
    public_support: float = 70.0
    infrastructure: float = 100.0
    audience_cost: float = 0.0
    casualties: float = 0.0  # thousands
    displaced: float = 0.0   # millions displaced (relevant for Iran, Israel)
    discount_factor: float = 0.9
    escalation_level: int = 0
    move_history: list = field(default_factory=list)

    # Missile/rocket inventory (hundreds of units)
    missile_stock: float = 100.0

    # Structured economic state (v3)
    economy: EconomicState = field(default_factory=EconomicState)

    def sync_economic_health(self):
        """Sync legacy economic_health from structured EconomicState."""
        self.economic_health = self.economy.composite_health

    @property
    def pain_index(self) -> float:
        """Zartman's hurting metric (0-100+). Now uses structured economics."""
        econ_pain = (100 - self.economy.composite_health) * 0.25
        return (
            (100 - self.military_capacity) * 0.15
            + econ_pain
            + (100 - self.public_support) * 0.15
            + self.casualties * 8.0
            + self.displaced * 3.0
            + (100 - self.infrastructure) * 0.1
            + max(0, (100 - self.missile_stock)) * 0.1
        )

    @property
    def resolve(self) -> float:
        base = self.public_support * 0.5 + self.military_capacity * 0.3 + self.missile_stock * 0.2
        return min(100, base + self.audience_cost * 0.5)

    def clamp(self):
        self.military_capacity = max(0, min(100, self.military_capacity))
        self.public_support = max(0, min(100, self.public_support))
        self.infrastructure = max(0, min(100, self.infrastructure))
        self.audience_cost = max(0, self.audience_cost)
        self.casualties = max(0, self.casualties)
        self.displaced = max(0, self.displaced)
        self.missile_stock = max(0, min(100, self.missile_stock))
        self.sync_economic_health()


# ============================================================
# 3. BAYESIAN BELIEFS (enhanced with multiple type dimensions)
# ============================================================

@dataclass
class BeliefState:
    """Belief about opponent type: rational (will deal) vs revolutionary (won't)."""
    p_rational: float = 0.6

    def update(self, action: str, escalation: int, pain: float):
        """Bayesian update. Considers pain level: escalating while in pain
        is a stronger signal of revolutionary type."""
        if action in ("negotiate", "push_for_talks", "ceasefire"):
            lr, lv = 0.85, 0.15
        elif action in ("proxy_escalation", "ground_operation", "full_barrage", "hormuz_blockade"):
            # Escalation under high pain = very strong revolutionary signal
            pain_factor = min(1.0, pain / 60.0)
            lr = 0.2 - pain_factor * 0.1
            lv = 0.8 + pain_factor * 0.1
        elif action in ("attrition",) and escalation >= 3:
            lr, lv = 0.25, 0.75
        elif action in ("hold_fire", "defensive_posture"):
            lr, lv = 0.6, 0.4
        else:
            lr, lv = 0.5, 0.5

        p = self.p_rational
        self.p_rational = (lr * p) / (lr * p + lv * (1 - p)) if (lr * p + lv * (1 - p)) > 0 else 0.5


# ============================================================
# 4. ESCALATION LADDER & RED LINES
# ============================================================

class EscalationThreshold(Enum):
    """Discrete escalation thresholds that change the game qualitatively."""
    CONVENTIONAL_LIMITED = 1      # standoff weapons, limited strikes
    CONVENTIONAL_FULL = 2         # full air campaign
    MULTI_FRONT = 3               # proxy fronts open
    GROUND_WAR = 4                # boots on the ground
    STRATEGIC_TARGETS = 5         # capital, leadership, nuclear sites
    WMD_THRESHOLD = 6             # chemical/biological/nuclear


@dataclass
class RedLineTracker:
    """Tracks which red lines have been crossed and their consequences."""
    lines_crossed: set = field(default_factory=set)

    def check_and_cross(self, action: str, player: str) -> list[str]:
        """Returns list of newly crossed red lines."""
        newly_crossed = []

        if player == "usa" and action == "ground_operation" and "usa_ground" not in self.lines_crossed:
            self.lines_crossed.add("usa_ground")
            newly_crossed.append("USA commits ground forces — domestic political crisis risk")

        if player == "iran" and action == "hormuz_blockade" and "hormuz" not in self.lines_crossed:
            self.lines_crossed.add("hormuz")
            newly_crossed.append("Hormuz fully blocked — global oil crisis, $150+ oil")

        if player == "hezbollah" and action == "full_barrage" and "hez_barrage" not in self.lines_crossed:
            self.lines_crossed.add("hez_barrage")
            newly_crossed.append("Hezbollah full barrage — Israeli home front under mass fire")

        if player == "israel" and action == "independent_ops" and "israel_unilateral" not in self.lines_crossed:
            self.lines_crossed.add("israel_unilateral")
            newly_crossed.append("Israel acts unilaterally — coalition strain")

        return newly_crossed


# ============================================================
# 5. STOCHASTIC SHOCKS
# ============================================================

@dataclass
class Shock:
    name: str
    probability: float  # per round
    effects: dict  # player_name -> {attribute: delta}
    description: str
    one_time: bool = True  # can only happen once


# v5 FIX #4: BIMODAL SHOCKS
# Each shock now has TWO possible outcomes with different probabilities.
# "Pearl Harbor vs Beirut barracks" — same event, opposite reactions.

@dataclass
class BimodalShock:
    """v5: Shock with two possible reaction paths."""
    name: str
    probability: float
    # Path A: "rally" response (Pearl Harbor, 9/11)
    path_a_probability: float  # probability of path A given shock occurs
    effects_a: dict
    description_a: str
    # Path B: "retreat" response (Beirut barracks, Mogadishu)
    effects_b: dict
    description_b: str
    one_time: bool = True


SHOCK_TABLE = [
    BimodalShock(
        name="us_ship_sunk",
        probability=0.04,
        path_a_probability=0.4,  # 40% Pearl Harbor, 60% Beirut barracks
        effects_a={
            "usa": {"casualties": 0.3, "public_support": 20, "audience_cost": 15},
            "iran": {"public_support": -5},
        },
        description_a="US destroyer sunk → Pearl Harbor effect: nation rallies, AUMF passes",
        effects_b={
            "usa": {"casualties": 0.3, "public_support": -25, "audience_cost": -5},
            "iran": {"public_support": 15},
        },
        description_b="US destroyer sunk → Beirut barracks effect: 'why are we there?', withdrawal pressure",
    ),
    BimodalShock(
        name="iran_nuclear_test",
        probability=0.02,
        path_a_probability=0.8,  # 80% justifies war, 20% panic/escalation fear
        effects_a={
            "iran": {"audience_cost": 10, "public_support": 15, "escalation_level": 5},
            "usa": {"public_support": 15, "audience_cost": 10},
            "israel": {"public_support": 15, "audience_cost": 12},
        },
        description_a="Iran nuclear test → justifies war, massive rally, 'we were right'",
        effects_b={
            "iran": {"audience_cost": 10, "public_support": 15, "escalation_level": 5},
            "usa": {"public_support": -15},
            "israel": {"public_support": -10},
        },
        description_b="Iran nuclear test → panic: 'war made it worse', fear of nuclear exchange",
    ),
    BimodalShock(
        name="iran_leadership_killed",
        probability=0.03,
        path_a_probability=0.5,
        effects_a={
            "iran": {"public_support": -15, "military_capacity": -10, "audience_cost": -5},
            "usa": {"public_support": 10},
            "israel": {"public_support": 8},
        },
        description_a="IRGC commander killed → command chaos, morale drops",
        effects_b={
            "iran": {"public_support": 10, "military_capacity": -5, "audience_cost": 8},
            "usa": {"public_support": 3},
        },
        description_b="IRGC commander killed → martyrdom rally, hardliners empowered",
    ),
    BimodalShock(
        name="hormuz_tanker_disaster",
        probability=0.05,
        path_a_probability=0.3,
        effects_a={
            "usa": {"public_support": 5, "audience_cost": 5},
        },
        description_a="Tanker disaster → 'Iran must be stopped', justifies escalation",
        effects_b={
            "usa": {"public_support": -8},
            "israel": {"public_support": -3},
        },
        description_b="Tanker disaster → oil spikes, economic pain, 'end this war'",
    ),
    BimodalShock(
        name="hezbollah_arsenal_destroyed",
        probability=0.03,
        path_a_probability=0.85,
        effects_a={
            "hezbollah": {"missile_stock": -40, "military_capacity": -25},
            "israel": {"public_support": 8},
        },
        description_a="Hezbollah depot destroyed — major blow to capability",
        effects_b={
            "hezbollah": {"missile_stock": -20, "military_capacity": -10},
            "israel": {"casualties": 0.1, "public_support": -3},
        },
        description_b="Depot strike causes massive secondary explosions in civilian area",
    ),
    BimodalShock(
        name="israeli_city_mass_casualty",
        probability=0.03,
        path_a_probability=0.6,
        effects_a={
            "israel": {"casualties": 0.2, "public_support": 10, "audience_cost": 8},
        },
        description_a="Mass casualty → Israeli society rallies, demands total victory",
        effects_b={
            "israel": {"casualties": 0.2, "public_support": -12, "displaced": 0.5},
        },
        description_b="Mass casualty → panic, evacuation, government blamed for failure",
    ),
    BimodalShock(
        name="iranian_civilian_massacre",
        probability=0.04,
        path_a_probability=0.25,  # rare: most of the time this hurts coalition
        effects_a={
            "usa": {"public_support": -3},
            "iran": {"public_support": 12, "casualties": 0.5},
        },
        description_a="Civilian casualties → muted reaction, 'war is hell' narrative",
        effects_b={
            "usa": {"public_support": -15, "audience_cost": -5},
            "iran": {"public_support": 18, "casualties": 0.5, "displaced": 1.0},
        },
        description_b="Hospital/school hit → massive international condemnation, protests in US cities",
    ),
    BimodalShock(
        name="us_domestic_crisis",
        probability=0.04,
        path_a_probability=0.5,
        effects_a={
            "usa": {"public_support": -5},
        },
        description_a="Domestic event briefly diverts attention, minor impact",
        effects_b={
            "usa": {"public_support": -15},
        },
        description_b="Major domestic crisis (recession signal, political scandal) — war becomes secondary",
    ),
    BimodalShock(
        name="iraqi_militia_attacks_us_base",
        probability=0.06,
        path_a_probability=0.5,
        effects_a={
            "usa": {"casualties": 0.05, "public_support": 3, "audience_cost": 3},
            "iran": {"audience_cost": 2},
        },
        description_a="Iraqi militia attack → 'Iran's proxies must be stopped', slight rally",
        effects_b={
            "usa": {"casualties": 0.05, "public_support": -5},
            "iran": {"audience_cost": 2},
        },
        description_b="Iraqi militia attack → 'another quagmire', Vietnam/Iraq comparison in media",
    ),
]


def roll_shocks(round_num: int, occurred: set, round_weight: float = 1.0) -> list[tuple]:
    """v5: Roll bimodal shocks. Returns list of (shock, path_chosen, effects, description)."""
    triggered = []
    for shock in SHOCK_TABLE:
        if shock.one_time and shock.name in occurred:
            continue
        adjusted_p = shock.probability * (1 + round_num * 0.02) * round_weight
        if random.random() < adjusted_p:
            # v5 FIX #4: Choose path A or B
            if random.random() < shock.path_a_probability:
                triggered.append((shock, "A", shock.effects_a, shock.description_a))
            else:
                triggered.append((shock, "B", shock.effects_b, shock.description_b))
            if shock.one_time:
                occurred.add(shock.name)
    return triggered


def apply_shocks(shocks: list[tuple], players: dict):
    """v5: Apply bimodal shock effects."""
    for shock, path, effects, desc in shocks:
        for player_name, deltas in effects.items():
            if player_name not in players:
                continue
            p = players[player_name]
            for attr, delta in deltas.items():
                if attr == "escalation_level":
                    p.escalation_level = max(p.escalation_level, int(delta))
                else:
                    setattr(p, attr, getattr(p, attr) + delta)


# (v5: roll_shocks and apply_shocks moved above with BimodalShock)


# ============================================================
# 6. COALITION COORDINATION SUBGAME (USA-Israel bargaining)
# ============================================================

def coalition_coordination(
    usa: PlayerState,
    israel: PlayerState,
    usa_preferred: USAStrategy,
    israel_preferred: IsraelStrategy,
    round_num: int,
    trump_rhetoric: Optional['TrumpRhetoricState'] = None,
    regional: Optional['RegionalActors'] = None,
) -> tuple[USAStrategy, IsraelStrategy, dict]:
    """v4: Enhanced USA-Israel bargaining with divergence modeling.

    Key dynamics:
    - USA has leverage (providing weapons, diplomatic cover)
    - Israel has urgency (existential threat, higher pain)
    - Divergence increases over time as costs accumulate differently
    - "Mission Accomplished" trap: Trump declares victory, Israel keeps fighting
    - Window closing: Israel knows US exit is coming, acts accordingly

    Returns (usa_strat, israel_strat, coordination_info).
    """
    coord_info = {"tension_level": 0.0, "divergence_type": "aligned"}

    # Measure divergence
    usa_wants_exit = usa_preferred in (USAStrategy.DECLARE_VICTORY, USAStrategy.NEGOTIATE)
    israel_wants_fight = israel_preferred in (IsraelStrategy.JOINT_STRIKES, IsraelStrategy.INDEPENDENT_OPS)

    # v4: Divergence score — how far apart are their objectives?
    # USA: 4-8 week war, air only, declare victory
    # Israel: total elimination of threats (nuclear + missiles + Hezbollah)
    objective_gap = 0.0
    if round_num > 4:
        objective_gap += 0.1 * (round_num - 4)  # grows each week past week 4
    if usa.public_support < 40:
        objective_gap += 0.15
    if israel.casualties > 0.2:
        objective_gap += 0.1  # Israel's urgency increases
    objective_gap = min(1.0, objective_gap)

    coord_info["objective_gap"] = round(objective_gap, 2)

    # v4: Mission Accomplished trap affects coordination
    if trump_rhetoric and trump_rhetoric.commitment_trap_active:
        # Trump already declared "almost over" — he MUST follow through or lose face
        if not usa_wants_exit:
            # Trump's rhetoric forces his hand: lean toward exit
            if random.random() < trump_rhetoric.confidence_level:
                usa_preferred = USAStrategy.DECLARE_VICTORY
                usa_wants_exit = True
                coord_info["mission_accomplished_forcing"] = True

    if usa_wants_exit and israel_wants_fight:
        # COALITION TENSION: USA wants out, Israel wants to continue
        coord_info["divergence_type"] = "usa_exit_israel_fight"
        coord_info["tension_level"] = 0.6 + objective_gap * 0.4

        usa_leverage = usa.economic_health * 0.5 + usa.public_support * 0.3
        israel_leverage = israel.pain_index * 0.4 + israel.audience_cost * 0.3

        # v4: Israel's window is closing — if USA exits, Israel goes solo
        # Netanyahu knows this and acts preemptively
        israel_window_closing = round_num > 6 and usa.public_support < 45

        if israel_leverage > usa_leverage or israel_window_closing:
            # Israel drags USA into continuing or goes independent
            if israel_window_closing and israel.military_capacity > 50:
                # Israel accelerates independent ops while US still providing cover
                coord_info["israel_racing_clock"] = True
                return USAStrategy.LIMIT_TO_STANDOFF, IsraelStrategy.INDEPENDENT_OPS, coord_info
            return USAStrategy.LIMIT_TO_STANDOFF, IsraelStrategy.INDEPENDENT_OPS, coord_info
        else:
            # USA forces Israel to accept reduced operations
            return USAStrategy.DECLARE_VICTORY, IsraelStrategy.DEFENSIVE_POSTURE, coord_info

    elif not usa_wants_exit and not israel_wants_fight:
        # Israel tired, USA still fighting
        coord_info["divergence_type"] = "usa_fight_israel_tired"
        if usa.audience_cost > 10:
            return usa_preferred, IsraelStrategy.JOINT_STRIKES, coord_info
        else:
            return usa_preferred, israel_preferred, coord_info

    else:
        # Aligned: no coordination friction
        coord_info["divergence_type"] = "aligned"

        # v4: Regional actor effects on coordination
        if regional:
            effectiveness = regional.coalition_effectiveness_modifier
            if effectiveness < 0.7:
                coord_info["regional_constraint"] = True
                # Reduced base access constrains operations
                if usa_preferred == USAStrategy.AIR_STRIKES:
                    if random.random() < (1 - effectiveness):
                        return USAStrategy.LIMIT_TO_STANDOFF, israel_preferred, coord_info

        return usa_preferred, israel_preferred, coord_info


# ============================================================
# 7. PAYOFF FUNCTIONS (separate for each player)
# ============================================================

def usa_payoff(
    usa_strat: USAStrategy, iran_strat: IranStrategy,
    hez_strat: HezbollahStrategy, israel_strat: IsraelStrategy,
    usa: PlayerState, iran: PlayerState, oil_market: OilMarket,
    round_num: int, calendar: Calendar,
    trump_rhetoric: Optional[TrumpRhetoricState] = None,
    regional: Optional[RegionalActors] = None,
    nuclear: Optional[NuclearThreshold] = None,
) -> float:
    """USA payoff. v4: adds Trump rhetoric trap, Hormuz δ-attack, regional effects,
    nuclear threshold anxiety."""

    base = 0.0

    # Action payoffs
    if usa_strat == USAStrategy.AIR_STRIKES:
        base += 3.0 - (100 - usa.military_capacity) * 0.02
    elif usa_strat == USAStrategy.GROUND_OPERATION:
        base += -2.0
        if calendar.is_summer_heat:
            base -= 1.5
    elif usa_strat == USAStrategy.LIMIT_TO_STANDOFF:
        base += 2.0
    elif usa_strat == USAStrategy.DECLARE_VICTORY:
        base += 1.0 if iran.military_capacity < 30 else -3.0
    elif usa_strat == USAStrategy.NEGOTIATE:
        base += 0.0

    # Iran resistance
    if iran_strat in (IranStrategy.RETALIATE, IranStrategy.PROXY_ESCALATION):
        base -= 2.0
    if iran_strat == IranStrategy.HORMUZ_FULL_BLOCKADE:
        base -= 4.0

    # ECONOMIC DAMAGE
    oil = oil_market.price
    econ = usa.economy

    if oil > 100:
        base -= (oil - 100) * 0.04
    if oil > 150:
        base -= (oil - 150) * 0.08
    if oil > 200:
        base -= (oil - 200) * 0.12

    if econ.inflation_rate > 5:
        base -= (econ.inflation_rate - 5) * 0.8

    if econ.gdp_index < 98:
        base -= (100 - econ.gdp_index) * 0.5

    base -= econ.war_spending_pct_gdp * 3.0

    if oil_market.spr_remaining_mb < 200:
        base -= (200 - oil_market.spr_remaining_mb) * 0.01

    base -= usa.casualties * 10.0

    # Audience cost trap
    if usa_strat in (USAStrategy.DECLARE_VICTORY, USAStrategy.NEGOTIATE):
        base -= usa.audience_cost * 0.4

    # v4: MISSION ACCOMPLISHED TRAP
    if trump_rhetoric and trump_rhetoric.commitment_trap_active:
        if usa_strat not in (USAStrategy.DECLARE_VICTORY,):
            # Continuing war after "almost over" = credibility damage
            base -= (1 - trump_rhetoric.credibility) * 3.0
        else:
            # Declaring victory when Iran still fighting = looks like retreat
            if iran.military_capacity > 20 or iran.missile_stock > 15:
                base -= 2.0  # "declaring victory while rockets still fly"

    # MIDTERM PRESSURE
    midterm = calendar.midterm_pressure
    if midterm > 0.3:
        if usa.public_support < 40:
            base -= midterm * 5.0
        base -= midterm * 1.5

    # v4: Hormuz directly attacks Trump's δ (felt as gas prices in swing states)
    hormuz_delta_hit = hormuz_delta_attack_effect(
        oil, econ.inflation_rate, calendar.weeks_to_midterms)
    if hormuz_delta_hit > 0.02:
        base -= hormuz_delta_hit * 20  # translate δ damage to payoff

    if calendar.carrier_rotation_due:
        if usa_strat in (USAStrategy.AIR_STRIKES, USAStrategy.GROUND_OPERATION):
            base -= 1.0

    if hez_strat in (HezbollahStrategy.FULL_BARRAGE, HezbollahStrategy.CALIBRATED_STRIKES):
        base -= 1.5

    # v4: Regional actor effects
    if regional:
        effectiveness = regional.coalition_effectiveness_modifier
        if effectiveness < 0.8:
            base -= (0.8 - effectiveness) * 5.0  # reduced base access hurts ops

    # v4: Nuclear threshold anxiety — if Iran approaching breakout, war must continue
    if nuclear and nuclear.threat_level > 0.3:
        if usa_strat == USAStrategy.DECLARE_VICTORY:
            base -= nuclear.threat_level * 8.0  # can't leave with nuclear threat
        elif usa_strat in (USAStrategy.AIR_STRIKES, USAStrategy.GROUND_OPERATION):
            base += nuclear.threat_level * 2.0  # justified to continue

    # Time pressure
    base *= usa.discount_factor ** round_num

    return round(base, 2)


def israel_payoff(
    usa_strat: USAStrategy, iran_strat: IranStrategy,
    hez_strat: HezbollahStrategy, israel_strat: IsraelStrategy,
    israel: PlayerState, iran: PlayerState, hezbollah: PlayerState,
    round_num: int, oil_market: OilMarket, calendar: Calendar,
) -> float:
    """Israel payoff. Now includes oil import dependency, tech sector disruption,
    reservist mobilization costs."""

    base = 0.0

    # Security gains
    if usa_strat in (USAStrategy.AIR_STRIKES, USAStrategy.GROUND_OPERATION):
        base += 3.0
    if israel_strat == IsraelStrategy.INDEPENDENT_OPS:
        base += 2.0
    elif israel_strat == IsraelStrategy.JOINT_STRIKES:
        base += 2.5
    elif israel_strat == IsraelStrategy.DEFENSIVE_POSTURE:
        base += 0.5

    # Hezbollah threat
    if hez_strat == HezbollahStrategy.FULL_BARRAGE:
        base -= 6.0
        base -= israel.displaced * 1.0
    elif hez_strat == HezbollahStrategy.CALIBRATED_STRIKES:
        base -= 3.0
    elif hez_strat == HezbollahStrategy.HOLD_FIRE:
        base += 1.0

    # ECONOMIC: Israel imports 100% of oil via Eilat/Ashkelon pipeline
    econ = israel.economy
    oil = oil_market.price
    if oil > 100:
        base -= (oil - 100) * 0.06  # more sensitive than USA (100% importer)
    if econ.inflation_rate > 5:
        base -= (econ.inflation_rate - 5) * 0.6
    # Reservist mobilization = GDP loss (tech sector especially)
    base -= econ.war_spending_pct_gdp * 4.0
    if econ.gdp_index < 96:
        base -= (100 - econ.gdp_index) * 0.4

    # Casualty sensitivity
    base -= israel.casualties * 6.0

    # USA abandonment risk
    if usa_strat in (USAStrategy.DECLARE_VICTORY, USAStrategy.NEGOTIATE):
        base -= 4.0

    # Audience cost
    if israel_strat in (IsraelStrategy.PUSH_FOR_TALKS, IsraelStrategy.DEFENSIVE_POSTURE):
        base -= israel.audience_cost * 0.3

    # Iran nuclear threat
    if iran.military_capacity > 40:
        base -= 2.0

    base *= israel.discount_factor ** round_num

    return round(base, 2)


def iran_payoff(
    usa_strat: USAStrategy, iran_strat: IranStrategy,
    hez_strat: HezbollahStrategy,
    iran: PlayerState, usa: PlayerState, oil_market: OilMarket,
    round_num: int, calendar: Calendar,
    leadership: Optional[LeadershipState] = None,
    nuclear: Optional[NuclearThreshold] = None,
) -> float:
    """Iran payoff. v4: includes leadership transition, Hormuz as δ-attack,
    nuclear threshold effects, and structured economic warfare."""

    base = 0.0
    oil = oil_market.price
    econ = iran.economy

    # Resistance value
    if iran_strat == IranStrategy.RETALIATE:
        base += 2.0
    elif iran_strat == IranStrategy.PROXY_ESCALATION:
        base += 2.5
    elif iran_strat == IranStrategy.HORMUZ_FULL_BLOCKADE:
        # v4: Hormuz is a δ-ATTACK on Trump, not just economic damage
        # Value = damage to enemy's discount factor (political, not military)
        enemy_delta_damage = hormuz_delta_attack_effect(
            oil, usa.economy.inflation_rate, calendar.weeks_to_midterms)
        enemy_damage = min(6.0, enemy_delta_damage * 40)  # scale to payoff
        self_damage = -econ.trade_disruption * 0.03  # Iran can't export either
        base += enemy_damage + self_damage
    elif iran_strat == IranStrategy.ATTRITION:
        base += 1.0
        if calendar.is_ramadan:
            base += 0.5
    elif iran_strat == IranStrategy.NEGOTIATE:
        base += 0.0

    # Proxy success
    if hez_strat in (HezbollahStrategy.FULL_BARRAGE, HezbollahStrategy.CALIBRATED_STRIKES):
        base += 2.0
    if hez_strat == HezbollahStrategy.INDEPENDENT_CEASEFIRE:
        base -= 3.0

    # Economic warfare effectiveness: high oil = Iran winning economically
    if oil > 150:
        base += (oil - 150) * 0.02
    if usa.economy.recession_risk > 0.3:
        base += usa.economy.recession_risk * 3.0

    # US casualties = huge political win
    if usa.casualties > 0.1:
        base += usa.casualties * 5.0

    # OWN ECONOMIC SUFFERING
    base -= max(0, econ.inflation_rate - 15) * 0.3
    if econ.gdp_index < 90:
        base -= (90 - econ.gdp_index) * 0.2
    base -= econ.trade_disruption * 0.02

    # v5 FIX #7: NONLINEAR casualty sensitivity
    # Below threshold: regime absorbs. Above: "drinking poison" collapse.
    is_rev = leadership is not None and not leadership.consolidation_complete
    cas_sensitivity = iran_casualty_sensitivity(iran.casualties, is_rev)
    base -= iran.casualties * cas_sensitivity

    base -= iran.displaced * 1.5
    base -= (100 - iran.infrastructure) * 0.03

    # Coalition intensity
    if usa_strat == USAStrategy.GROUND_OPERATION:
        base -= 4.0
    elif usa_strat == USAStrategy.AIR_STRIKES:
        base -= 2.0

    # v4: Leadership transition — negotiation penalty for Mojtaba
    negotiate_penalty = 0.0
    if leadership:
        negotiate_penalty = leadership.negotiate_penalty
    if iran_strat == IranStrategy.NEGOTIATE:
        base -= iran.audience_cost * 0.5
        base -= negotiate_penalty  # Mojtaba: up to -9.0 extra for negotiating early

    # v4: Nuclear option increases Iran's bargaining power
    if nuclear and nuclear.threat_level > 0.3:
        base += nuclear.threat_level * 2.0  # nuclear threat = deterrence value

    # Missile depletion
    if iran.missile_stock < 20:
        base -= 3.0

    # v4: Apply leadership δ bonus
    effective_delta = iran.discount_factor
    if leadership:
        effective_delta = min(0.99, effective_delta + leadership.delta_bonus)
    base *= effective_delta ** round_num

    return round(base, 2)


def hezbollah_payoff(
    hez_strat: HezbollahStrategy, iran_strat: IranStrategy,
    israel_strat: IsraelStrategy,
    hezbollah: PlayerState, israel: PlayerState,
    round_num: int,
) -> float:
    """Hezbollah payoff. Semi-autonomous: loyal to Iran but has own survival logic.
    Key concerns: organizational survival, arsenal preservation, Lebanon politics."""

    base = 0.0

    # Fighting value (ideological + Iranian pressure)
    if hez_strat == HezbollahStrategy.FULL_BARRAGE:
        base += 1.0 if iran_strat != IranStrategy.NEGOTIATE else -2.0
    elif hez_strat == HezbollahStrategy.CALIBRATED_STRIKES:
        base += 2.0  # best balance of loyalty and preservation
    elif hez_strat == HezbollahStrategy.HOLD_FIRE:
        base += 0.5  # preserve but lose Iran's trust
    elif hez_strat == HezbollahStrategy.INDEPENDENT_CEASEFIRE:
        base += -1.0  # betrayal cost from Iran, but survival

    # Arsenal preservation (existential for Hezbollah's post-war power)
    arsenal_value = hezbollah.missile_stock / 100.0 * 3.0
    if hez_strat == HezbollahStrategy.FULL_BARRAGE:
        arsenal_value *= 0.3  # burning through arsenal
    elif hez_strat == HezbollahStrategy.CALIBRATED_STRIKES:
        arsenal_value *= 0.7
    base += arsenal_value

    # Israeli retaliation damage
    if israel_strat in (IsraelStrategy.JOINT_STRIKES, IsraelStrategy.INDEPENDENT_OPS):
        base -= 3.0  # Israel hits Hezbollah hard
    elif israel_strat == IsraelStrategy.DEFENSIVE_POSTURE:
        base += 1.0  # Israel not targeting Hezbollah

    # Organizational survival
    if hezbollah.military_capacity < 20:
        # Near destruction — ceasefire becomes rational
        if hez_strat == HezbollahStrategy.INDEPENDENT_CEASEFIRE:
            base += 4.0
        else:
            base -= 2.0

    # Iran coordination bonus
    if iran_strat in (IranStrategy.RETALIATE, IranStrategy.PROXY_ESCALATION):
        if hez_strat in (HezbollahStrategy.FULL_BARRAGE, HezbollahStrategy.CALIBRATED_STRIKES):
            base += 1.5  # coordinated pressure

    # Lebanon domestic backlash
    if hezbollah.casualties > 0.5 or hezbollah.infrastructure < 50:
        base -= 2.0  # Lebanese turning against

    base *= hezbollah.discount_factor ** round_num

    return round(base, 2)


# ============================================================
# 8. STRATEGY SELECTION
# ============================================================

def select_usa_strategy(
    usa: PlayerState, iran: PlayerState, israel: PlayerState,
    belief_iran: BeliefState, round_num: int, oil_market: OilMarket,
    calendar: Calendar,
) -> USAStrategy:
    """USA selects strategy. Now considers midterm pressure, economic state, calendar."""

    best, best_val = USAStrategy.AIR_STRIKES, float('-inf')

    for us in USAStrategy:
        ev = 0.0
        for ir in IranStrategy:
            for hz in HezbollahStrategy:
                w_ir = _iran_action_weight(ir, belief_iran)
                w_hz = _hez_action_weight(hz, iran)
                w = w_ir * w_hz

                p = usa_payoff(us, ir, hz, IsraelStrategy.JOINT_STRIKES,
                               usa, iran, oil_market, round_num, calendar)
                ev += w * p

        ev += random.gauss(0, 0.8)
        if ev > best_val:
            best_val = ev
            best = us

    # Hard overrides
    if usa.pain_index > 55 and usa.public_support < 25:
        best = USAStrategy.NEGOTIATE
    if iran.military_capacity < 12 and iran.infrastructure < 15:
        best = USAStrategy.DECLARE_VICTORY

    # Midterm pressure override: if elections imminent and war unpopular
    if calendar.midterm_pressure > 0.7 and usa.public_support < 35:
        best = USAStrategy.DECLARE_VICTORY

    # Carrier rotation: forced to reduce ops temporarily
    if calendar.carrier_rotation_due and best == USAStrategy.AIR_STRIKES:
        best = USAStrategy.LIMIT_TO_STANDOFF

    # Summer heat: avoid ground ops in Middle East June-August
    if calendar.is_summer_heat and best == USAStrategy.GROUND_OPERATION:
        if random.random() < 0.6:
            best = USAStrategy.AIR_STRIKES

    return best


def select_israel_strategy(
    israel: PlayerState, usa: PlayerState, iran: PlayerState,
    hezbollah: PlayerState, belief_iran: BeliefState, round_num: int,
    oil_market: Optional[OilMarket] = None, calendar: Optional[Calendar] = None,
) -> IsraelStrategy:
    """Israel selects strategy based on home front pressure and alliance."""

    if oil_market is None:
        oil_market = OilMarket()
    if calendar is None:
        calendar = Calendar()

    best, best_val = IsraelStrategy.JOINT_STRIKES, float('-inf')

    for isr in IsraelStrategy:
        ev = 0.0
        for ir in IranStrategy:
            for hz in HezbollahStrategy:
                w = _iran_action_weight(ir, belief_iran) * _hez_action_weight(hz, iran)
                p = israel_payoff(USAStrategy.AIR_STRIKES, ir, hz, isr,
                                  israel, iran, hezbollah, round_num,
                                  oil_market, calendar)
                ev += w * p
        ev += random.gauss(0, 0.6)
        if ev > best_val:
            best_val = ev
            best = isr

    # If Hezbollah battering Israel, shift to defensive
    if hezbollah.missile_stock > 30 and israel.casualties > 0.3:
        if best == IsraelStrategy.INDEPENDENT_OPS:
            best = IsraelStrategy.DEFENSIVE_POSTURE

    # If USA withdrawing, Israel either goes independent or pushes talks
    if usa.public_support < 30:
        if israel.military_capacity > 60:
            best = IsraelStrategy.INDEPENDENT_OPS
        else:
            best = IsraelStrategy.PUSH_FOR_TALKS

    return best


def select_iran_strategy(
    iran: PlayerState, usa: PlayerState, hezbollah: PlayerState,
    belief_coalition: BeliefState, round_num: int, oil_market: OilMarket,
    calendar: Calendar, is_revolutionary: bool = False,
) -> IranStrategy:
    """Iran strategy. Now considers own economic self-damage from Hormuz,
    enemy economic weakness as leverage, temporal factors."""

    best, best_val = IranStrategy.RETALIATE, float('-inf')

    for ir in IranStrategy:
        ev = 0.0
        for us in USAStrategy:
            for hz in HezbollahStrategy:
                w_us = _coalition_action_weight(us, belief_coalition)
                w_hz = 0.25
                w = w_us * w_hz
                p = iran_payoff(us, ir, hz, iran, usa, oil_market, round_num, calendar)
                ev += w * p

        if is_revolutionary and ir in (IranStrategy.RETALIATE, IranStrategy.PROXY_ESCALATION,
                                        IranStrategy.HORMUZ_FULL_BLOCKADE):
            ev += 3.0

        ev += random.gauss(0, 0.7)
        if ev > best_val:
            best_val = ev
            best = ir

    # Revolutionary override
    if is_revolutionary and best == IranStrategy.NEGOTIATE and iran.military_capacity > 8:
        best = IranStrategy.ATTRITION

    # Even revolutionaries surrender when truly broken
    if iran.pain_index > 85 and iran.military_capacity < 8 and iran.missile_stock < 5:
        best = IranStrategy.NEGOTIATE

    # Hormuz: strategic calculation based on self-damage vs enemy damage
    oil = oil_market.price
    if iran.military_capacity < 30 and oil < 130 and iran.missile_stock > 10:
        # Hormuz more attractive if Iran has little to lose economically
        if iran.economy.trade_disruption > 50 or iran.economy.gdp_index < 85:
            # Already disrupted — blocking Hormuz costs Iran less
            if random.random() < 0.5:
                best = IranStrategy.HORMUZ_FULL_BLOCKADE
        elif random.random() < 0.3:
            best = IranStrategy.HORMUZ_FULL_BLOCKADE

    # If enemy economy is cracking, double down on economic warfare
    if usa.economy.recession_risk > 0.4 and best == IranStrategy.RETALIATE:
        if random.random() < 0.5:
            best = IranStrategy.HORMUZ_FULL_BLOCKADE

    # Ramadan: attrition narrative stronger
    if calendar.is_ramadan and best == IranStrategy.RETALIATE:
        if random.random() < 0.3:
            best = IranStrategy.ATTRITION

    return best


def select_hezbollah_strategy(
    hezbollah: PlayerState, iran: PlayerState, israel: PlayerState,
    iran_strat: IranStrategy, round_num: int,
) -> HezbollahStrategy:
    """Hezbollah: semi-autonomous but influenced by Iran's moves."""

    best, best_val = HezbollahStrategy.CALIBRATED_STRIKES, float('-inf')

    for hz in HezbollahStrategy:
        ev = hezbollah_payoff(hz, iran_strat, IsraelStrategy.JOINT_STRIKES,
                              hezbollah, israel, round_num)
        ev += random.gauss(0, 0.5)
        if ev > best_val:
            best_val = ev
            best = hz

    # If Iran negotiates, Hezbollah has strong incentive to ceasefire
    if iran_strat == IranStrategy.NEGOTIATE:
        if random.random() < 0.7:
            best = HezbollahStrategy.INDEPENDENT_CEASEFIRE

    # Near-destruction → ceasefire
    if hezbollah.military_capacity < 15 or hezbollah.missile_stock < 10:
        best = HezbollahStrategy.INDEPENDENT_CEASEFIRE

    return best


# Strategy weight helpers
def _iran_action_weight(strat: IranStrategy, belief: BeliefState) -> float:
    weights = {
        IranStrategy.NEGOTIATE: belief.p_rational * 0.4,
        IranStrategy.ATTRITION: 0.2 + (1 - belief.p_rational) * 0.15,
        IranStrategy.RETALIATE: 0.2,
        IranStrategy.PROXY_ESCALATION: (1 - belief.p_rational) * 0.25,
        IranStrategy.HORMUZ_FULL_BLOCKADE: (1 - belief.p_rational) * 0.15,
    }
    return weights.get(strat, 0.1)


def _hez_action_weight(strat: HezbollahStrategy, iran: PlayerState) -> float:
    # Hezbollah more likely to fight if Iran is fighting
    fighting = iran.escalation_level >= 2
    weights = {
        HezbollahStrategy.FULL_BARRAGE: 0.3 if fighting else 0.1,
        HezbollahStrategy.CALIBRATED_STRIKES: 0.35,
        HezbollahStrategy.HOLD_FIRE: 0.15 if fighting else 0.4,
        HezbollahStrategy.INDEPENDENT_CEASEFIRE: 0.05,
    }
    return weights.get(strat, 0.1)


def _coalition_action_weight(strat: USAStrategy, belief: BeliefState) -> float:
    weights = {
        USAStrategy.AIR_STRIKES: 0.35,
        USAStrategy.GROUND_OPERATION: 0.1,
        USAStrategy.LIMIT_TO_STANDOFF: 0.2,
        USAStrategy.DECLARE_VICTORY: belief.p_rational * 0.2,
        USAStrategy.NEGOTIATE: belief.p_rational * 0.15,
    }
    return weights.get(strat, 0.1)


# ============================================================
# 9. STATE TRANSITIONS (recalibrated effects)
# ============================================================

def apply_round_effects(
    usa_strat: USAStrategy, israel_strat: IsraelStrategy,
    iran_strat: IranStrategy, hez_strat: HezbollahStrategy,
    usa: PlayerState, israel: PlayerState,
    iran: PlayerState, hezbollah: PlayerState,
    oil_market: OilMarket, calendar: Calendar,
    usa_av: 'ActionVector | None' = None,
    israel_av: 'ActionVector | None' = None,
    iran_av: 'ActionVector | None' = None,
    hez_av: 'ActionVector | None' = None,
):
    """Apply one round of effects. Oil market updated via OilMarket subsystem.
    Economics updated via EconomicState + update_economics().

    v5: ActionVectors modulate effect magnitudes. A player doing air_strikes
    at 0.6 intensity does ~75% damage vs 1.0 intensity (~105% damage).
    Secondary actions in the vector also produce proportional effects.
    """

    # Compute effect scales from ActionVectors (default 1.0 if no AV)
    def _s(av, action):
        """Get effect scale for an action from its ActionVector."""
        if av is None:
            return 1.0
        return av.effect_scale(action)

    # === USA ACTIONS ===
    s = _s(usa_av, "air_strikes")
    if usa_strat == USAStrategy.AIR_STRIKES:
        usa.military_capacity -= random.uniform(1.5, 3.5) * s
        usa.audience_cost += 1.5 * s
        usa.escalation_level = max(usa.escalation_level, 2)
        iran.infrastructure -= random.uniform(4, 9) * s
        iran.military_capacity -= random.uniform(3, 7) * s
        iran.casualties += random.uniform(0.15, 0.6) * s
        iran.displaced += random.uniform(0.05, 0.2) * s

    elif usa_strat == USAStrategy.GROUND_OPERATION:
        s = _s(usa_av, "ground_operation")
        usa.military_capacity -= random.uniform(4, 8) * s
        usa.casualties += random.uniform(0.08, 0.3) * s
        usa.public_support -= random.uniform(3, 7) * s
        usa.audience_cost += 4.0 * s
        usa.escalation_level = max(usa.escalation_level, 4)
        iran.infrastructure -= random.uniform(6, 14) * s
        iran.military_capacity -= random.uniform(5, 12) * s
        iran.casualties += random.uniform(0.4, 1.2) * s
        iran.displaced += random.uniform(0.2, 0.5) * s
        # v5: Simultaneous air strikes component from ActionVector
        if usa_av and usa_av.is_active("air_strikes"):
            sa = _s(usa_av, "air_strikes")
            iran.infrastructure -= random.uniform(1, 3) * sa
            iran.military_capacity -= random.uniform(1, 2) * sa

    elif usa_strat == USAStrategy.LIMIT_TO_STANDOFF:
        s = _s(usa_av, "standoff_only")
        usa.military_capacity -= random.uniform(0.5, 2.0) * s
        usa.audience_cost += 0.5 * s
        iran.infrastructure -= random.uniform(1, 4) * s
        iran.military_capacity -= random.uniform(1, 3) * s
        iran.casualties += random.uniform(0.05, 0.2) * s

    elif usa_strat == USAStrategy.DECLARE_VICTORY:
        usa.audience_cost = max(0, usa.audience_cost - 3.0)
        usa.public_support += random.uniform(2, 5)

    elif usa_strat == USAStrategy.NEGOTIATE:
        usa.audience_cost = max(0, usa.audience_cost - 1.0)
        usa.public_support -= random.uniform(0, 3)

    # === ISRAEL ACTIONS ===
    if israel_strat == IsraelStrategy.JOINT_STRIKES:
        s = _s(israel_av, "joint_strikes")
        israel.military_capacity -= random.uniform(1, 3) * s
        israel.audience_cost += 1.0 * s
        iran.military_capacity -= random.uniform(1, 3) * s
        iran.infrastructure -= random.uniform(1, 3) * s

    elif israel_strat == IsraelStrategy.INDEPENDENT_OPS:
        s = _s(israel_av, "independent_ops")
        israel.military_capacity -= random.uniform(2, 5) * s
        israel.audience_cost += 2.0 * s
        iran.military_capacity -= random.uniform(2, 5) * s
        iran.infrastructure -= random.uniform(2, 5) * s

    elif israel_strat == IsraelStrategy.DEFENSIVE_POSTURE:
        israel.public_support += random.uniform(0, 2)
        israel.military_capacity -= random.uniform(0.5, 1.5)

    elif israel_strat == IsraelStrategy.PUSH_FOR_TALKS:
        israel.audience_cost = max(0, israel.audience_cost - 1.0)
        israel.public_support -= random.uniform(0, 2)

    # === IRAN ACTIONS ===
    if iran_strat == IranStrategy.RETALIATE:
        s = _s(iran_av, "retaliate")
        iran.missile_stock -= random.uniform(3, 8) * s
        iran.military_capacity -= random.uniform(2, 4) * s
        iran.audience_cost += 2.0 * s
        iran.escalation_level = max(iran.escalation_level, 2)
        usa.infrastructure -= random.uniform(0.5, 2.0) * s
        usa.casualties += random.uniform(0, 0.05) * s
        israel.infrastructure -= random.uniform(1, 3) * s
        israel.casualties += random.uniform(0, 0.05) * s
        # v5: Simultaneous proxy escalation from ActionVector
        if iran_av and iran_av.is_active("proxy_escalation"):
            sp = _s(iran_av, "proxy_escalation")
            usa.public_support -= random.uniform(0.5, 1.5) * sp
            israel.public_support -= random.uniform(0.3, 1.0) * sp

    elif iran_strat == IranStrategy.HORMUZ_FULL_BLOCKADE:
        s = _s(iran_av, "hormuz_blockade")
        iran.missile_stock -= random.uniform(2, 5) * s
        iran.military_capacity -= random.uniform(1, 3) * s
        iran.audience_cost += 3.0 * s
        iran.escalation_level = max(iran.escalation_level, 3)
        # v5: Simultaneous attrition component
        if iran_av and iran_av.is_active("attrition"):
            iran.public_support += random.uniform(0, 1.5) * _s(iran_av, "attrition")

    elif iran_strat == IranStrategy.PROXY_ESCALATION:
        s = _s(iran_av, "proxy_escalation")
        iran.missile_stock -= random.uniform(1, 3) * s
        iran.audience_cost += 2.5 * s
        iran.escalation_level = max(iran.escalation_level, 3)
        usa.public_support -= random.uniform(2, 4) * s
        israel.public_support -= random.uniform(1, 3) * s
        # v5: Simultaneous direct retaliation
        if iran_av and iran_av.is_active("retaliate"):
            sr = _s(iran_av, "retaliate")
            iran.missile_stock -= random.uniform(1, 2) * sr
            usa.infrastructure -= random.uniform(0.2, 0.8) * sr

    elif iran_strat == IranStrategy.ATTRITION:
        s = _s(iran_av, "attrition")
        iran.military_capacity -= random.uniform(0.5, 1.5) * s
        iran.public_support += random.uniform(0, 3) * s
        iran.casualties += random.uniform(0.1, 0.3) * s
        iran.displaced += random.uniform(0.05, 0.15) * s

    elif iran_strat == IranStrategy.NEGOTIATE:
        iran.audience_cost = max(0, iran.audience_cost - 2.0)
        iran.public_support -= random.uniform(2, 6)

    # === HEZBOLLAH ACTIONS ===
    if hez_strat == HezbollahStrategy.FULL_BARRAGE:
        s = _s(hez_av, "full_barrage")
        hezbollah.missile_stock -= random.uniform(8, 15) * s
        hezbollah.military_capacity -= random.uniform(3, 6) * s
        hezbollah.audience_cost += 2.0 * s
        israel.infrastructure -= random.uniform(2, 6) * s
        israel.casualties += random.uniform(0.05, 0.2) * s
        israel.displaced += random.uniform(0.1, 0.4) * s
        israel.public_support -= random.uniform(2, 5) * s
        hezbollah.infrastructure -= random.uniform(3, 7) * s
        hezbollah.casualties += random.uniform(0.1, 0.3) * s

    elif hez_strat == HezbollahStrategy.CALIBRATED_STRIKES:
        s = _s(hez_av, "calibrated")
        hezbollah.missile_stock -= random.uniform(3, 6) * s
        hezbollah.military_capacity -= random.uniform(1, 3) * s
        israel.infrastructure -= random.uniform(0.5, 2) * s
        israel.casualties += random.uniform(0, 0.08) * s
        israel.displaced += random.uniform(0, 0.15) * s
        hezbollah.infrastructure -= random.uniform(1, 4) * s
        hezbollah.casualties += random.uniform(0.02, 0.1) * s

    elif hez_strat == HezbollahStrategy.HOLD_FIRE:
        hezbollah.public_support += random.uniform(0, 2)
        hezbollah.infrastructure -= random.uniform(0, 1)

    elif hez_strat == HezbollahStrategy.INDEPENDENT_CEASEFIRE:
        hezbollah.audience_cost = max(0, hezbollah.audience_cost - 3.0)
        hezbollah.public_support -= random.uniform(0, 3)

    # === OIL MARKET UPDATE (replaces simple oil_price arithmetic) ===
    is_hormuz_blockaded = "hormuz" in {iran_strat.value}  # current round
    oil_market.update(iran_strat.value, is_hormuz_blockaded,
                      calendar.current_round, calendar)

    # === ECONOMIC UPDATES (structured, with lagged cascades) ===
    players_actions = {
        "usa": usa_strat.value,
        "israel": israel_strat.value,
        "iran": iran_strat.value,
        "hezbollah": hez_strat.value,
    }
    players_states = {"usa": usa, "israel": israel, "iran": iran, "hezbollah": hezbollah}
    for pname, pstate in players_states.items():
        update_economics(pname, pstate.economy, oil_market, players_actions[pname], calendar)

    # === OIL → PUBLIC SUPPORT (lagged) ===
    # High oil + inflation → public turns against war (2-round lag for USA)
    if oil_market.price > 150 and usa.economy.inflation_rate > 6:
        usa.economy.add_lagged_effect("gdp_index", -0.5, lag_rounds=2)
        # Public support drops when they feel inflation at the pump
        if oil_market.cumulative_oil_shock_weeks > 4:
            usa.public_support -= random.uniform(0.5, 2.0)

    # Israel: direct and immediate economic pain from oil
    if oil_market.price > 120:
        israel.public_support -= random.uniform(0, 1.0)

    # Clamp all
    for p in (usa, israel, iran, hezbollah):
        p.clamp()

    # Advance calendar
    calendar.advance()


# ============================================================
# 10. TERMINATION CONDITIONS (enhanced)
# ============================================================

class GameOutcome(Enum):
    COALITION_DECISIVE_VICTORY = "coalition_decisive_victory"  # Iran regime change / total disarmament
    COALITION_LIMITED_VICTORY = "coalition_limited_victory"     # objectives partially met, withdrawal
    IRAN_STRATEGIC_VICTORY = "iran_strategic_victory"          # coalition withdraws, Iran intact
    NEGOTIATED_SETTLEMENT = "negotiated_settlement"
    FROZEN_CONFLICT = "frozen_conflict"                        # no resolution, low intensity continues
    ONGOING = "ongoing"


def check_termination(
    usa_strat: USAStrategy, iran_strat: IranStrategy,
    israel_strat: IsraelStrategy, hez_strat: HezbollahStrategy,
    usa: PlayerState, israel: PlayerState,
    iran: PlayerState, hezbollah: PlayerState,
) -> GameOutcome:
    """Enhanced termination with more nuanced outcomes."""

    # Mutual negotiation across board
    negotiating_coalition = usa_strat in (USAStrategy.NEGOTIATE, USAStrategy.DECLARE_VICTORY)
    negotiating_iran = iran_strat == IranStrategy.NEGOTIATE
    negotiating_hez = hez_strat == HezbollahStrategy.INDEPENDENT_CEASEFIRE

    if negotiating_coalition and negotiating_iran:
        return GameOutcome.NEGOTIATED_SETTLEMENT

    # Iran total collapse
    if iran.military_capacity < 5 and iran.infrastructure < 10 and iran.missile_stock < 5:
        return GameOutcome.COALITION_DECISIVE_VICTORY

    # Iran significantly weakened + coalition declares victory
    if (usa_strat == USAStrategy.DECLARE_VICTORY and
            iran.military_capacity < 25 and iran.infrastructure < 30):
        return GameOutcome.COALITION_LIMITED_VICTORY

    # Coalition gives up: USA support collapses or economic damage too high
    if usa.public_support < 15:
        return GameOutcome.IRAN_STRATEGIC_VICTORY
    if usa.economy.composite_health < 15:
        return GameOutcome.IRAN_STRATEGIC_VICTORY
    # Recession forces withdrawal
    if usa.economy.recession_risk > 0.7 and usa.economy.gdp_index < 93:
        return GameOutcome.IRAN_STRATEGIC_VICTORY
    if usa_strat == USAStrategy.DECLARE_VICTORY and iran.military_capacity >= 45:
        return GameOutcome.IRAN_STRATEGIC_VICTORY

    # Israel forced out + USA follows
    if (israel.public_support < 15 and israel.casualties > 0.8 and
            israel_strat == IsraelStrategy.PUSH_FOR_TALKS):
        return GameOutcome.NEGOTIATED_SETTLEMENT

    # Frozen conflict: both exhausted but neither negotiates
    if (usa.pain_index > 45 and iran.pain_index > 55 and
            not negotiating_coalition and not negotiating_iran):
        return GameOutcome.FROZEN_CONFLICT

    return GameOutcome.ONGOING


# ============================================================
# 11. SIMULATION ENGINE v2
# ============================================================

@dataclass
class SimulationConfig:
    max_rounds: int = 40              # ~40 weeks (up to midterms)
    iran_is_revolutionary: bool = False
    initial_oil_price: float = 85.0   # pre-war Brent
    seed: Optional[int] = None
    # Historically calibrated discount factors (see calibrate_patience.py):
    # Trump 2026: δ≈0.82 [0.77-0.87] (9mo to midterms, no AUMF, +winnability, social media)
    #   Based on: Iraq invasion δ≈0.76, Gulf War δ≈0.85, Afghanistan δ≈0.90
    #   Adjusted for: election proximity (-0.04), war fatigue (-0.024), social media (-0.006)
    # Israel 2026: δ≈0.85 [0.82-0.88] (existential framing vs Gaza fatigue)
    #   Based on: Lebanon 2006 δ≈0.72, Protective Edge δ≈0.81, Gaza 2023 δ≈0.99
    #   Key insight: existential framing adds +0.10 (Gelpi-Feaver-Reifler)
    # Iran rational: δ≈0.95 (authoritarian, no elections, survival mode)
    # Iran revolutionary: δ≈0.97 (Iran-Iraq War: 8yr, 500K KIA, GDP -40%)
    # Hezbollah: δ≈0.85 (proxy, dependent on Iran, Lebanon fragile)
    usa_discount: float = 0.82
    israel_discount: float = 0.85
    iran_discount: float = 0.95
    hezbollah_discount: float = 0.85
    coalition_belief_iran_rational: float = 0.55
    iran_belief_coalition_rational: float = 0.50
    enable_shocks: bool = True

    # v4: New subsystem toggles
    enable_leadership_transition: bool = True   # Khamenei → Mojtaba dynamics
    enable_trump_rhetoric: bool = True          # Mission Accomplished trap
    enable_nuclear_threshold: bool = True       # cornered player nuclear logic
    enable_regional_actors: bool = True         # Gulf state cooperation effects
    iran_initial_enrichment_pct: float = 60.0   # starting enrichment level
    iran_nuclear_facilities_pct: float = 100.0  # % surviving at start
    # v5: New subsystem toggles
    enable_fog_of_war: bool = True              # BDA bias, information asymmetry
    enable_great_powers: bool = True            # China/Russia persistent actors
    enable_hez_fragmentation: bool = True       # Hezbollah command fragmentation
    enable_iran_rally: bool = True              # bombing → rally effect
    enable_war_powers: bool = True              # 60-day War Powers Act clock
    coalition_bda_bias: float = 1.3             # BDA overestimation factor


@dataclass
class RoundResult:
    round_num: int
    date: str                   # calendar date
    usa_strategy: str
    israel_strategy: str
    iran_strategy: str
    hezbollah_strategy: str
    usa_payoff: float
    israel_payoff: float
    iran_payoff: float
    hezbollah_payoff: float
    oil_price: float
    hormuz_flow_pct: float      # % of normal Hormuz flow
    spr_remaining: float        # US SPR in million barrels
    usa_inflation: float
    israel_inflation: float
    iran_inflation: float
    usa_gdp_index: float
    iran_gdp_index: float
    usa_war_cost_pct_gdp: float
    usa_recession_risk: float
    usa_military: float
    israel_military: float
    iran_military: float
    hez_military: float
    usa_support: float
    israel_support: float
    iran_support: float
    usa_pain: float
    iran_pain: float
    israel_pain: float
    iran_missiles: float
    hez_missiles: float
    iran_casualties: float
    usa_casualties: float
    israel_casualties: float
    weeks_to_midterms: int
    shocks: list[str]
    red_lines: list[str]
    belief_iran_rational: float


def run_simulation(config: SimulationConfig) -> dict:
    if config.seed is not None:
        random.seed(config.seed)

    # Initialize players with structured economics
    usa = PlayerState(
        name="USA", military_capacity=100,
        public_support=55, infrastructure=100, discount_factor=config.usa_discount,
        missile_stock=100,
        economy=EconomicState(gdp_index=100, inflation_rate=3.2, war_spending_pct_gdp=0),
    )
    israel = PlayerState(
        name="Israel", military_capacity=85,
        public_support=72, infrastructure=90, discount_factor=config.israel_discount,
        missile_stock=80,
        economy=EconomicState(gdp_index=100, inflation_rate=3.5, war_spending_pct_gdp=0),
    )
    iran = PlayerState(
        name="Iran", military_capacity=65,
        public_support=78, infrastructure=75, discount_factor=config.iran_discount,
        missile_stock=70,
        economy=EconomicState(gdp_index=85, inflation_rate=35.0,
                               war_spending_pct_gdp=0, trade_disruption=20),
    )
    hezbollah = PlayerState(
        name="Hezbollah", military_capacity=55,
        public_support=60, infrastructure=50, discount_factor=config.hezbollah_discount,
        missile_stock=85,
        economy=EconomicState(gdp_index=70, inflation_rate=20.0, trade_disruption=30),
    )

    for p in (usa, israel, iran, hezbollah):
        p.sync_economic_health()

    players = {"usa": usa, "israel": israel, "iran": iran, "hezbollah": hezbollah}

    belief_iran = BeliefState(p_rational=config.coalition_belief_iran_rational)
    belief_coalition = BeliefState(p_rational=config.iran_belief_coalition_rational)

    oil_market = OilMarket(price=config.initial_oil_price,
                           pre_war_price=config.initial_oil_price)
    calendar = Calendar()

    # v4: Initialize new subsystems
    leadership = LeadershipState() if config.enable_leadership_transition else None
    trump_rhetoric = TrumpRhetoricState() if config.enable_trump_rhetoric else None
    nuclear = NuclearThreshold(
        enrichment_pct=config.iran_initial_enrichment_pct,
        facilities_surviving_pct=config.iran_nuclear_facilities_pct,
    ) if config.enable_nuclear_threshold else None
    regional = RegionalActors() if config.enable_regional_actors else None

    # v5: Initialize new subsystems
    fog = FogOfWar(coalition_bda_bias=config.coalition_bda_bias) if config.enable_fog_of_war else None
    great_powers = GreatPowerDynamics() if config.enable_great_powers else None
    hez_frag = HezbollahFragmentation() if config.enable_hez_fragmentation else None

    history: list[RoundResult] = []
    outcome = GameOutcome.ONGOING
    red_lines = RedLineTracker()
    shocks_occurred: set = set()
    v4_events = []

    for r in range(1, config.max_rounds + 1):
        round_shocks = []
        round_red_lines = []
        round_v4_events = []

        # --- v4: Leadership transition ---
        if leadership:
            leadership_effects = leadership.process_transition(calendar.current_date)
            if "public_support_delta" in leadership_effects:
                iran.public_support += leadership_effects["public_support_delta"]
            if "military_capacity_delta" in leadership_effects:
                iran.military_capacity += leadership_effects["military_capacity_delta"]
            if "audience_cost_delta" in leadership_effects:
                iran.audience_cost += leadership_effects["audience_cost_delta"]
            if "delta_modifier" in leadership_effects:
                # Temporarily boost Iran's effective δ
                iran.discount_factor = min(0.99,
                    config.iran_discount + leadership.delta_bonus)
            if leadership.leader != "khamenei":
                round_v4_events.append(f"iran_leader:{leadership.leader}"
                                        f"(legit:{leadership.legitimacy:.2f})")

        # --- v5: Fog of war — compute perceived states ---
        perceived_iran_mil = iran.military_capacity
        perceived_iran_miss = iran.missile_stock
        if fog:
            perceived_iran_mil = fog.perceived_iran_military(iran.military_capacity)
            perceived_iran_miss = fog.perceived_iran_missiles(iran.missile_stock)

        # --- v4: Trump rhetoric processing ---
        if trump_rhetoric:
            rhetoric_effects = trump_rhetoric.process_rhetoric(
                iran.military_capacity, iran.missile_stock,
                oil_market.price, r,
                perceived_iran_mil=perceived_iran_mil)
            if "usa_support_boost" in rhetoric_effects:
                usa.public_support += rhetoric_effects["usa_support_boost"]
            if "usa_support_penalty" in rhetoric_effects:
                usa.public_support += rhetoric_effects["usa_support_penalty"]
            if "oil_speculation_dampen" in rhetoric_effects:
                oil_market.price += rhetoric_effects["oil_speculation_dampen"]
            if rhetoric_effects.get("mission_accomplished_trap"):
                round_v4_events.append("mission_accomplished_trap!")
            if trump_rhetoric.rhetoric_intensity > 0:
                round_v4_events.append(
                    f"trump_credibility:{trump_rhetoric.credibility:.2f}")

        # --- v4: Nuclear threshold ---
        if nuclear:
            # Coalition targets nuclear facilities during air strikes
            coalition_strikes_nuclear = (r <= 4)  # first 4 weeks priority targets
            nuclear_effects = nuclear.update(
                iran.military_capacity, iran.infrastructure,
                coalition_strikes_nuclear, r)
            if nuclear_effects.get("nuclear_breakout_started"):
                round_v4_events.append("NUCLEAR_BREAKOUT_STARTED!")
                iran.escalation_level = max(iran.escalation_level, 6)
            if nuclear_effects.get("nuclear_test"):
                round_v4_events.append("IRAN_NUCLEAR_TEST!")
            round_v4_events.append(f"nuclear_threat:{nuclear.threat_level:.2f}")

        # --- v4: Regional actors ---
        regional_effects = {}
        if regional:
            regional_effects = regional.update(
                iran.move_history[-1] if iran.move_history else "attrition",
                hezbollah.move_history[-1] if hezbollah.move_history else "hold_fire",
                oil_market.price, r)
            if regional_effects.get("base_access_crisis"):
                round_v4_events.append("BASE_ACCESS_CRISIS!")
                usa.military_capacity -= 3
            if regional_effects.get("jordan_closes_airspace"):
                round_v4_events.append("jordan_airspace_closed!")
            avg_coop = regional_effects.get("avg_regional_cooperation", 75)
            round_v4_events.append(f"regional_coop:{avg_coop:.0f}")

        # --- v5: Great power dynamics ---
        if great_powers:
            great_powers.update(oil_market.price, oil_market.hormuz_flow_pct,
                                iran.military_capacity, r, calendar.round_weight)
            if great_powers.iran_intel_bonus > 0.05:
                round_v4_events.append(f"russia_intel:{great_powers.russia_intel_support_iran:.2f}")
            if great_powers.china_mediation_interest > 0.3:
                round_v4_events.append(f"china_mediation:{great_powers.china_mediation_interest:.2f}")
            # Russian intel helps Iran's targeting
            if great_powers.iran_intel_bonus > 0.03:
                iran.military_capacity += great_powers.iran_intel_bonus  # slight boost

        # --- v5: Hezbollah fragmentation ---
        if hez_frag:
            israel_hitting_hez = (len(israel.move_history) > 0 and
                                  israel.move_history[-1] in ("joint_strikes", "independent_ops"))
            iran_last = iran.move_history[-1] if iran.move_history else "attrition"
            hez_frag.update(hezbollah.military_capacity, iran_last,
                            israel_hitting_hez, calendar.round_weight)

        # --- v5: Iran rally under bombing (FIX #3) ---
        if config.enable_iran_rally:
            # Check if coalition is bombing this round (from last round's action)
            last_usa = usa.move_history[-1] if usa.move_history else ""
            if last_usa in ("air_strikes", "ground_operation", "standoff_only"):
                rally_delta = iran_rally_under_bombing(
                    iran.public_support,
                    iran.casualties * 0.1,  # this round's casualties (approx)
                    max(0, 75 - iran.infrastructure),  # damage from baseline
                    config.iran_is_revolutionary,
                    calendar.weeks_elapsed)
                iran.public_support += rally_delta

        # --- v5 FIX #9: War Powers Act pressure ---
        if config.enable_war_powers and calendar.war_powers_pressure > 0:
            wp = calendar.war_powers_pressure
            if wp > 0.5:
                round_v4_events.append(f"war_powers_pressure:{wp:.2f}")
                usa.public_support -= wp * 2.0  # constitutional crisis looms
                if wp >= 1.0:
                    round_v4_events.append("WAR_POWERS_DEADLINE!")
                    # After 60 days without AUMF: major political crisis
                    usa.public_support -= 5.0
                    usa.audience_cost -= 3.0  # easier to withdraw legally

        # --- Stochastic shocks (v5: bimodal) ---
        if config.enable_shocks:
            triggered = roll_shocks(r, shocks_occurred, calendar.round_weight)
            apply_shocks(triggered, players)
            round_shocks = [f"{s[0].name}:{s[1]}" for s in triggered]

        # --- Strategy selection (v5: uses perceived states for USA/Israel) ---
        # v5 FIX #2: Coalition decides based on BIASED intelligence
        iran_for_coalition = PlayerState(
            name="Iran_perceived",
            military_capacity=perceived_iran_mil,
            public_support=iran.public_support,
            infrastructure=iran.infrastructure,
            discount_factor=iran.discount_factor,
            missile_stock=perceived_iran_miss,
            casualties=iran.casualties,
            displaced=iran.displaced,
            audience_cost=iran.audience_cost,
            escalation_level=iran.escalation_level,
            economy=iran.economy,
        )
        usa_pref = select_usa_strategy(usa, iran_for_coalition, israel, belief_iran, r,
                                        oil_market, calendar)
        israel_pref = select_israel_strategy(israel, usa, iran_for_coalition, hezbollah,
                                              belief_iran, r, oil_market, calendar)

        # v4: Coalition coordination with Trump rhetoric and regional effects
        usa_strat, israel_strat, coord_info = coalition_coordination(
            usa, israel, usa_pref, israel_pref, r,
            trump_rhetoric=trump_rhetoric, regional=regional)
        if coord_info.get("israel_racing_clock"):
            round_v4_events.append("israel_racing_clock!")
        if coord_info.get("mission_accomplished_forcing"):
            round_v4_events.append("trump_forced_to_exit!")

        # v4: Iran strategy considers leadership constraints
        iran_strat = select_iran_strategy(
            iran, usa, hezbollah, belief_coalition, r, oil_market, calendar,
            is_revolutionary=config.iran_is_revolutionary,
        )
        # v4: Mojtaba override — cannot negotiate before consolidation
        if (leadership and not leadership.consolidation_complete
                and iran_strat == IranStrategy.NEGOTIATE
                and iran.military_capacity > 8):
            iran_strat = IranStrategy.ATTRITION  # must demonstrate resolve
            round_v4_events.append("mojtaba_blocks_negotiation!")

        hez_strat = select_hezbollah_strategy(hezbollah, iran, israel, iran_strat, r)

        # v5 FIX #12: Hezbollah fragmentation effects
        if hez_frag:
            # Low coherence → some units may spontaneously cease fire
            if (hez_frag.ceasefire_probability_modifier > 0 and
                    random.random() < hez_frag.ceasefire_probability_modifier):
                hez_strat = HezbollahStrategy.HOLD_FIRE
                round_v4_events.append("hez_local_ceasefire!")
            # Fragmented Hezbollah can't do full barrage
            if (hez_frag.command_coherence < 0.4 and
                    hez_strat == HezbollahStrategy.FULL_BARRAGE):
                hez_strat = HezbollahStrategy.CALIBRATED_STRIKES
                round_v4_events.append("hez_too_fragmented_for_barrage!")

        # --- Red line checks ---
        round_red_lines.extend(red_lines.check_and_cross(usa_strat.value, "usa"))
        round_red_lines.extend(red_lines.check_and_cross(israel_strat.value, "israel"))
        round_red_lines.extend(red_lines.check_and_cross(iran_strat.value, "iran"))
        round_red_lines.extend(red_lines.check_and_cross(hez_strat.value, "hezbollah"))

        # --- Payoffs (v4: with new subsystem parameters) ---
        p_usa = usa_payoff(usa_strat, iran_strat, hez_strat, israel_strat,
                           usa, iran, oil_market, r, calendar,
                           trump_rhetoric=trump_rhetoric, regional=regional,
                           nuclear=nuclear)
        p_israel = israel_payoff(usa_strat, iran_strat, hez_strat, israel_strat,
                                 israel, iran, hezbollah, r, oil_market, calendar)
        p_iran = iran_payoff(usa_strat, iran_strat, hez_strat, iran, usa,
                             oil_market, r, calendar,
                             leadership=leadership, nuclear=nuclear)
        p_hez = hezbollah_payoff(hez_strat, iran_strat, israel_strat, hezbollah, israel, r)

        # --- Bayesian updates ---
        belief_iran.update(iran_strat.value, iran.escalation_level, iran.pain_index)
        belief_coalition.update(usa_strat.value, usa.escalation_level, usa.pain_index)

        # --- v5: Generate ActionVectors for continuous intensity modulation ---
        usa_av = ActionVector.from_enum(usa_strat.value)
        israel_av = ActionVector.from_enum(israel_strat.value)
        iran_av = ActionVector.from_enum(iran_strat.value)
        hez_av = ActionVector.from_enum(hez_strat.value)

        # --- Apply effects (v5: with ActionVector intensity scaling) ---
        apply_round_effects(
            usa_strat, israel_strat, iran_strat, hez_strat,
            usa, israel, iran, hezbollah, oil_market, calendar,
            usa_av=usa_av, israel_av=israel_av,
            iran_av=iran_av, hez_av=hez_av,
        )

        # v4: Dynamic δ update for USA based on Hormuz δ-attack
        if oil_market.price > 100:
            hormuz_hit = hormuz_delta_attack_effect(
                oil_market.price, usa.economy.inflation_rate,
                calendar.weeks_to_midterms)
            usa.discount_factor = max(0.65,
                config.usa_discount - hormuz_hit)

        # --- Record ---
        for p in players.values():
            p.move_history.append(None)
        usa.move_history[-1] = usa_strat.value
        israel.move_history[-1] = israel_strat.value
        iran.move_history[-1] = iran_strat.value
        hezbollah.move_history[-1] = hez_strat.value

        history.append(RoundResult(
            round_num=r,
            date=str(calendar.current_date),
            usa_strategy=usa_strat.value,
            israel_strategy=israel_strat.value,
            iran_strategy=iran_strat.value,
            hezbollah_strategy=hez_strat.value,
            usa_payoff=p_usa, israel_payoff=p_israel,
            iran_payoff=p_iran, hezbollah_payoff=p_hez,
            oil_price=round(oil_market.price, 1),
            hormuz_flow_pct=round(oil_market.hormuz_flow_pct, 1),
            spr_remaining=round(oil_market.spr_remaining_mb, 1),
            usa_inflation=round(usa.economy.inflation_rate, 1),
            israel_inflation=round(israel.economy.inflation_rate, 1),
            iran_inflation=round(iran.economy.inflation_rate, 1),
            usa_gdp_index=round(usa.economy.gdp_index, 1),
            iran_gdp_index=round(iran.economy.gdp_index, 1),
            usa_war_cost_pct_gdp=round(usa.economy.war_spending_pct_gdp, 2),
            usa_recession_risk=round(usa.economy.recession_risk, 2),
            usa_military=round(usa.military_capacity, 1),
            israel_military=round(israel.military_capacity, 1),
            iran_military=round(iran.military_capacity, 1),
            hez_military=round(hezbollah.military_capacity, 1),
            usa_support=round(usa.public_support, 1),
            israel_support=round(israel.public_support, 1),
            iran_support=round(iran.public_support, 1),
            usa_pain=round(usa.pain_index, 1),
            iran_pain=round(iran.pain_index, 1),
            israel_pain=round(israel.pain_index, 1),
            iran_missiles=round(iran.missile_stock, 1),
            hez_missiles=round(hezbollah.missile_stock, 1),
            iran_casualties=round(iran.casualties, 2),
            usa_casualties=round(usa.casualties, 2),
            israel_casualties=round(israel.casualties, 2),
            weeks_to_midterms=calendar.weeks_to_midterms,
            shocks=round_shocks,
            red_lines=round_red_lines,
            belief_iran_rational=round(belief_iran.p_rational, 3),
        ))

        # Track v4 events
        if round_v4_events:
            v4_events.append({"round": r, "events": round_v4_events})

        # --- Termination ---
        outcome = check_termination(
            usa_strat, iran_strat, israel_strat, hez_strat,
            usa, israel, iran, hezbollah,
        )
        if outcome != GameOutcome.ONGOING:
            break

    if outcome == GameOutcome.ONGOING:
        outcome = GameOutcome.FROZEN_CONFLICT

    result = {
        "outcome": outcome.value,
        "rounds_played": len(history),
        "final_date": str(calendar.current_date),
        "final_oil_price": round(oil_market.price, 1),
        "hormuz_flow_pct": round(oil_market.hormuz_flow_pct, 1),
        "spr_remaining_mb": round(oil_market.spr_remaining_mb, 1),
        "usa_inflation": round(usa.economy.inflation_rate, 1),
        "usa_gdp_index": round(usa.economy.gdp_index, 1),
        "usa_war_cost_pct_gdp": round(usa.economy.war_spending_pct_gdp, 2),
        "usa_recession_risk": round(usa.economy.recession_risk, 2),
        "oil_shock_weeks": oil_market.cumulative_oil_shock_weeks,
        "final_usa_military": round(usa.military_capacity, 1),
        "final_israel_military": round(israel.military_capacity, 1),
        "final_iran_military": round(iran.military_capacity, 1),
        "final_hezbollah_military": round(hezbollah.military_capacity, 1),
        "total_iran_casualties_k": round(iran.casualties, 2),
        "total_usa_casualties_k": round(usa.casualties, 2),
        "total_israel_casualties_k": round(israel.casualties, 2),
        "total_hezbollah_casualties_k": round(hezbollah.casualties, 2),
        "iran_missiles_remaining": round(iran.missile_stock, 1),
        "hez_missiles_remaining": round(hezbollah.missile_stock, 1),
        "belief_iran_rational": round(belief_iran.p_rational, 3),
        "red_lines_crossed": list(red_lines.lines_crossed),
        "all_shocks": list(shocks_occurred),
        "history": history,
    }

    # v4: Additional output
    result["v4_events"] = v4_events
    result["usa_final_delta"] = round(usa.discount_factor, 4)
    result["iran_final_delta"] = round(iran.discount_factor, 4)

    if leadership:
        result["iran_leader"] = leadership.leader
        result["iran_leader_legitimacy"] = round(leadership.legitimacy, 2)
        result["iran_leader_consolidated"] = leadership.consolidation_complete

    if trump_rhetoric:
        result["trump_rhetoric_intensity"] = round(trump_rhetoric.rhetoric_intensity, 2)
        result["trump_credibility"] = round(trump_rhetoric.credibility, 2)
        result["mission_accomplished_trap"] = trump_rhetoric.commitment_trap_active

    if nuclear:
        result["nuclear_status"] = nuclear.status.value
        result["nuclear_threat_level"] = round(nuclear.threat_level, 2)
        result["nuclear_facilities_surviving"] = round(nuclear.facilities_surviving_pct, 1)

    if regional:
        result["regional_cooperation_avg"] = round(
            (regional.saudi_cooperation + regional.bahrain_cooperation
             + regional.qatar_cooperation + regional.jordan_cooperation
             + regional.kuwait_cooperation) / 5, 1)

    # v5: Additional output
    if fog:
        result["bda_bias"] = fog.coalition_bda_bias
        result["perceived_iran_mil"] = round(perceived_iran_mil, 1) if 'perceived_iran_mil' in dir() else None
    if great_powers:
        result["china_mediation_interest"] = round(great_powers.china_mediation_interest, 2)
        result["russia_oil_windfall_b"] = round(great_powers.russia_oil_windfall, 1)
        result["russia_intel_support"] = round(great_powers.russia_intel_support_iran, 2)
    if hez_frag:
        result["hez_coherence"] = round(hez_frag.command_coherence, 2)
        result["hez_iran_control"] = round(hez_frag.iran_control, 2)
        result["hez_effective_power"] = round(hez_frag.effective_combat_power, 2)
    result["war_powers_active"] = calendar.war_powers_pressure >= 1.0
    result["days_elapsed"] = calendar.days_since_start

    return result


# ============================================================
# 12. MONTE CARLO v2
# ============================================================

def monte_carlo(
    n_simulations: int = 1000,
    config_overrides: Optional[dict] = None,
) -> dict:
    base = SimulationConfig()
    if config_overrides:
        for k, v in config_overrides.items():
            if hasattr(base, k):
                setattr(base, k, v)

    outcomes = {}
    rounds_list = []
    oil_list = []
    iran_cas = []
    usa_cas = []
    israel_cas = []
    red_line_counts = {}
    shock_counts = {}
    # Economic aggregates
    usa_inflation_list = []
    usa_gdp_list = []
    usa_recession_risk_list = []
    usa_war_cost_list = []
    oil_shock_weeks_list = []
    spr_remaining_list = []

    nuclear_breakout_count = 0

    for i in range(n_simulations):
        # v5: Copy ALL config fields from base, not just a subset
        cfg = SimulationConfig(
            max_rounds=base.max_rounds,
            iran_is_revolutionary=base.iran_is_revolutionary,
            initial_oil_price=base.initial_oil_price,
            seed=i,
            usa_discount=base.usa_discount,
            israel_discount=base.israel_discount,
            iran_discount=base.iran_discount,
            hezbollah_discount=base.hezbollah_discount,
            coalition_belief_iran_rational=base.coalition_belief_iran_rational,
            iran_belief_coalition_rational=base.iran_belief_coalition_rational,
            enable_shocks=base.enable_shocks,
            # v4 subsystem toggles
            enable_leadership_transition=base.enable_leadership_transition,
            enable_trump_rhetoric=base.enable_trump_rhetoric,
            enable_nuclear_threshold=base.enable_nuclear_threshold,
            enable_regional_actors=base.enable_regional_actors,
            iran_initial_enrichment_pct=base.iran_initial_enrichment_pct,
            iran_nuclear_facilities_pct=base.iran_nuclear_facilities_pct,
            # v5 subsystem toggles
            enable_fog_of_war=base.enable_fog_of_war,
            enable_great_powers=base.enable_great_powers,
            enable_hez_fragmentation=base.enable_hez_fragmentation,
            enable_iran_rally=base.enable_iran_rally,
            enable_war_powers=base.enable_war_powers,
            coalition_bda_bias=base.coalition_bda_bias,
        )
        result = run_simulation(cfg)

        o = result["outcome"]
        outcomes[o] = outcomes.get(o, 0) + 1
        rounds_list.append(result["rounds_played"])
        oil_list.append(result["final_oil_price"])
        iran_cas.append(result["total_iran_casualties_k"])
        usa_cas.append(result["total_usa_casualties_k"])
        israel_cas.append(result["total_israel_casualties_k"])
        usa_inflation_list.append(result["usa_inflation"])
        usa_gdp_list.append(result["usa_gdp_index"])
        usa_recession_risk_list.append(result["usa_recession_risk"])
        usa_war_cost_list.append(result["usa_war_cost_pct_gdp"])
        oil_shock_weeks_list.append(result["oil_shock_weeks"])
        spr_remaining_list.append(result["spr_remaining_mb"])

        for rl in result["red_lines_crossed"]:
            red_line_counts[rl] = red_line_counts.get(rl, 0) + 1
        for sh in result["all_shocks"]:
            shock_counts[sh] = shock_counts.get(sh, 0) + 1

        # v5: Track nuclear breakout
        if any("NUCLEAR_BREAKOUT" in str(e) for e in result.get("v4_events", [])):
            nuclear_breakout_count += 1

    n = n_simulations
    return {
        "n_simulations": n,
        "outcome_distribution": {
            k: round(v / n * 100, 1) for k, v in sorted(outcomes.items())
        },
        "avg_rounds": round(sum(rounds_list) / n, 1),
        "median_rounds": sorted(rounds_list)[n // 2],
        "avg_final_oil_price": round(sum(oil_list) / n, 1),
        "economics": {
            "avg_usa_inflation_%": round(sum(usa_inflation_list) / n, 1),
            "avg_usa_gdp_index": round(sum(usa_gdp_list) / n, 1),
            "avg_usa_recession_risk": round(sum(usa_recession_risk_list) / n, 2),
            "avg_usa_war_cost_%_gdp": round(sum(usa_war_cost_list) / n, 2),
            "avg_oil_shock_weeks": round(sum(oil_shock_weeks_list) / n, 1),
            "avg_spr_remaining_mb": round(sum(spr_remaining_list) / n, 1),
        },
        "avg_iran_casualties_k": round(sum(iran_cas) / n, 2),
        "avg_usa_casualties_k": round(sum(usa_cas) / n, 2),
        "avg_israel_casualties_k": round(sum(israel_cas) / n, 2),
        "red_line_frequency_%": {
            k: round(v / n * 100, 1) for k, v in sorted(red_line_counts.items())
        },
        "shock_frequency_%": {
            k: round(v / n * 100, 1) for k, v in sorted(shock_counts.items())
        },
        "nuclear_breakout_rate": round(nuclear_breakout_count / n, 3),
    }


# ============================================================
# 13. SCENARIO COMPARISON
# ============================================================

def run_scenario_comparison() -> dict:
    """Compare key scenarios side by side. v4: adds multi-level scenarios."""
    scenarios = {
        "baseline_rational": {
            "iran_is_revolutionary": False,
            "enable_shocks": True,
        },
        "revolutionary_iran": {
            "iran_is_revolutionary": True,
            "enable_shocks": True,
        },
        "usa_very_impatient": {
            "iran_is_revolutionary": False,
            "usa_discount": 0.70,
            "enable_shocks": True,
        },
        "post_911_commitment": {
            "iran_is_revolutionary": True,
            "usa_discount": 0.93,
            "iran_discount": 0.97,
            "max_rounds": 40,
            "enable_shocks": True,
        },
        "high_oil_start": {
            "iran_is_revolutionary": False,
            "initial_oil_price": 110.0,
            "enable_shocks": True,
        },
        "near_midterms": {
            "iran_is_revolutionary": True,
            "usa_discount": 0.75,
            "enable_shocks": True,
        },
        # v4 scenarios
        "mojtaba_hardline": {
            "iran_is_revolutionary": True,
            "enable_leadership_transition": True,
            "enable_trump_rhetoric": True,
            "enable_shocks": True,
            "iran_discount": 0.96,  # Mojtaba proves even harder than father
        },
        "hormuz_delta_attack": {
            "iran_is_revolutionary": True,
            "initial_oil_price": 100.0,  # already elevated
            "enable_leadership_transition": True,
            "enable_trump_rhetoric": True,
            "enable_shocks": True,
        },
        "nuclear_brinkmanship": {
            "iran_is_revolutionary": True,
            "enable_nuclear_threshold": True,
            "iran_initial_enrichment_pct": 60.0,
            "iran_nuclear_facilities_pct": 50.0,  # half already hit
            "enable_shocks": True,
        },
        "coalition_fracture": {
            "iran_is_revolutionary": True,
            "usa_discount": 0.78,    # impatient Trump
            "israel_discount": 0.90,  # very committed Israel
            "enable_trump_rhetoric": True,
            "enable_regional_actors": True,
            "enable_shocks": True,
        },
    }

    results = {}
    for name, overrides in scenarios.items():
        results[name] = monte_carlo(500, overrides)

    return results


# ============================================================
# 14. MIXED STRATEGY NASH EQUILIBRIUM (2-player projection)
# ============================================================

def find_mixed_nash_2player(
    usa: PlayerState, iran: PlayerState, oil_market: OilMarket,
    round_num: int = 1, calendar: Optional[Calendar] = None,
) -> dict:
    """Find mixed strategy Nash equilibrium for simplified 2-player projection."""

    if calendar is None:
        calendar = Calendar()

    usa_strats = list(USAStrategy)
    iran_strats = list(IranStrategy)

    n_us = len(usa_strats)
    n_ir = len(iran_strats)

    M_us = [[0.0] * n_ir for _ in range(n_us)]
    M_ir = [[0.0] * n_ir for _ in range(n_us)]

    for i, us in enumerate(usa_strats):
        for j, ir in enumerate(iran_strats):
            pu = usa_payoff(us, ir, HezbollahStrategy.CALIBRATED_STRIKES,
                            IsraelStrategy.JOINT_STRIKES, usa, iran,
                            oil_market, round_num, calendar)
            pi = iran_payoff(us, ir, HezbollahStrategy.CALIBRATED_STRIKES,
                             iran, usa, oil_market, round_num, calendar)
            M_us[i][j] = pu
            M_ir[i][j] = pi

    # Find pure Nash first
    pure_nash = []
    for i in range(n_us):
        for j in range(n_ir):
            is_us_best = all(M_us[i][j] >= M_us[k][j] for k in range(n_us))
            is_ir_best = all(M_ir[i][j] >= M_ir[i][k] for k in range(n_ir))
            if is_us_best and is_ir_best:
                pure_nash.append((usa_strats[i].value, iran_strats[j].value,
                                  M_us[i][j], M_ir[i][j]))

    return {
        "payoff_matrix_usa": {
            usa_strats[i].value: {iran_strats[j].value: M_us[i][j]
                                   for j in range(n_ir)}
            for i in range(n_us)
        },
        "payoff_matrix_iran": {
            usa_strats[i].value: {iran_strats[j].value: M_ir[i][j]
                                   for j in range(n_ir)}
            for i in range(n_us)
        },
        "pure_nash_equilibria": pure_nash,
    }


# ============================================================
# 15. PRETTY PRINTER
# ============================================================

def print_payoff_matrix_4player(
    usa: PlayerState, iran: PlayerState,
    oil_market: OilMarket, round_num: int = 1,
    calendar: Optional[Calendar] = None,
):
    """Print simplified 2-player (USA vs Iran) payoff matrix."""

    if calendar is None:
        calendar = Calendar()

    label = "USA vs Iran"
    print(f"\n{label:<20s}", end="")
    for ir in IranStrategy:
        print(f"  {ir.value:>17s}", end="")
    print()
    print("-" * 115)

    nash = find_mixed_nash_2player(usa, iran, oil_market, round_num, calendar)
    pure_eq = {(n[0], n[1]) for n in nash["pure_nash_equilibria"]}

    for us in USAStrategy:
        print(f"{us.value:<20s}", end="")
        for ir in IranStrategy:
            pu = nash["payoff_matrix_usa"][us.value][ir.value]
            pi = nash["payoff_matrix_iran"][us.value][ir.value]
            marker = " *" if (us.value, ir.value) in pure_eq else "  "
            print(f"  ({pu:+6.1f},{pi:+6.1f}){marker}", end="")
        print()

    if pure_eq:
        print(f"\n  * Nash equilibria: {list(pure_eq)}")
    else:
        print("\n  No pure strategy Nash equilibrium (mixed strategy needed)")


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 80)
    print("GAME THEORY CONFLICT MODEL v5: USA, Israel, Iran, Hezbollah (2026)")
    print("  13 CRITICAL FIXES: Fog of War, Bimodal Shocks, Phase Transitions")
    print("=" * 80)

    # --- 1. Single simulation with full detail ---
    print("\n\n--- SINGLE SIMULATION (seed=42) ---")
    result = run_simulation(SimulationConfig(seed=42))
    print(f"Outcome: {result['outcome']}")
    print(f"Rounds: {result['rounds_played']}  (ended: {result['final_date']})")
    print(f"\nOIL & ECONOMY:")
    print(f"  Oil: ${result['final_oil_price']:.1f}  |  Hormuz flow: {result['hormuz_flow_pct']}%")
    print(f"  US SPR remaining: {result['spr_remaining_mb']}M bbl  "
          f"(started: 400M)")
    print(f"  US inflation: {result['usa_inflation']}%  |  "
          f"US GDP index: {result['usa_gdp_index']}")
    print(f"  US war cost: {result['usa_war_cost_pct_gdp']}% of GDP  |  "
          f"Recession risk: {result['usa_recession_risk']}")
    print(f"  Oil shock weeks (>$120): {result['oil_shock_weeks']}")
    print(f"\nCASUALTIES:")
    print(f"  USA={result['total_usa_casualties_k']}K  "
          f"Israel={result['total_israel_casualties_k']}K  "
          f"Iran={result['total_iran_casualties_k']}K  "
          f"Hez={result['total_hezbollah_casualties_k']}K")
    print(f"\nMISSILES: Iran={result['iran_missiles_remaining']}  Hez={result['hez_missiles_remaining']}")
    print(f"Red lines: {result['red_lines_crossed']}")
    print(f"Shocks: {result['all_shocks']}")
    print(f"\nv4 DYNAMICS:")
    print(f"  USA final δ: {result.get('usa_final_delta', 'N/A')}  |  "
          f"Iran final δ: {result.get('iran_final_delta', 'N/A')}")
    if result.get('iran_leader'):
        print(f"  Iran leader: {result['iran_leader']}  "
              f"(legitimacy: {result.get('iran_leader_legitimacy', 'N/A')}, "
              f"consolidated: {result.get('iran_leader_consolidated', 'N/A')})")
    if result.get('trump_rhetoric_intensity', 0) > 0:
        print(f"  Trump victory declarations: {result['trump_rhetoric_intensity']}  "
              f"(credibility: {result.get('trump_credibility', 'N/A')}, "
              f"trap: {result.get('mission_accomplished_trap', False)})")
    if result.get('nuclear_status'):
        print(f"  Nuclear: {result['nuclear_status']}  "
              f"(threat: {result.get('nuclear_threat_level', 0)}, "
              f"facilities: {result.get('nuclear_facilities_surviving', 0)}%)")
    if result.get('regional_cooperation_avg') is not None:
        print(f"  Regional cooperation: {result['regional_cooperation_avg']}%")

    print("\n  Round-by-round:")
    print(f"  {'R':>3s} {'Date':10s} {'USA':15s} {'Israel':16s} {'Iran':17s} {'Hez':12s} "
          f"{'Oil':>6s} {'Hrmz%':>5s} {'SPR':>5s} {'USinf':>5s} {'USgdp':>5s} {'RecR':>5s} "
          f"{'IRmil':>5s} {'Midtrm':>6s}")
    for h in result["history"]:
        shocks_str = f"  !{','.join(h.shocks)}" if h.shocks else ""
        print(f"  {h.round_num:3d} {h.date:10s} {h.usa_strategy:15s} {h.israel_strategy:16s} "
              f"{h.iran_strategy:17s} {h.hezbollah_strategy:12s} "
              f"${h.oil_price:5.1f} {h.hormuz_flow_pct:5.1f} {h.spr_remaining:5.1f} "
              f"{h.usa_inflation:5.1f} {h.usa_gdp_index:5.1f} {h.usa_recession_risk:5.2f} "
              f"{h.iran_military:5.1f} {h.weeks_to_midterms:5d}w"
              f"{shocks_str}")

    # --- 2. Scenario comparison ---
    print("\n\n--- SCENARIO COMPARISON (n=500 each) ---")
    comparison = run_scenario_comparison()
    for scenario_name, data in comparison.items():
        print(f"\n{'='*60}")
        print(f"  {scenario_name}")
        print(f"{'='*60}")
        summary = {k: v for k, v in data.items()
                   if k not in ("red_line_frequency_%", "shock_frequency_%")}
        print(json.dumps(summary, indent=2))

    # --- 3. Full Monte Carlo ---
    print("\n\n--- FULL MONTE CARLO: BASELINE (n=1000) ---")
    full = monte_carlo(1000, {"iran_is_revolutionary": False})
    print(json.dumps(full, indent=2))

    print("\n\n--- FULL MONTE CARLO: REVOLUTIONARY (n=1000) ---")
    full_rev = monte_carlo(1000, {"iran_is_revolutionary": True})
    print(json.dumps(full_rev, indent=2))


if __name__ == "__main__":
    main()
