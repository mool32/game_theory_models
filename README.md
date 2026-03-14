# USA vs Iran: Game Theory Conflict Model

A multi-player game-theoretic simulation of a hypothetical US-Iran military conflict (2026). The model implements a 4-player repeated non-cooperative game with incomplete information, stochastic shocks, oil price dynamics, nuclear escalation logic, and economic phase transitions.

**Version:** v5.1
**Live demo:** [mool32.github.io/game_theory_models](https://mool32.github.io/game_theory_models/)
**Method:** 500 Monte Carlo simulations, variable-granularity rounds, approximate Nash equilibrium via best-response dynamics
**Stack:** Pure Python (stdlib), no ML — classical game theory. Vanilla HTML/CSS/JS visualization.

> **Disclaimer:** This is an exploratory game-theoretic model, not a forecast. Real conflicts involve thousands of variables no model can capture. The probabilities reflect the model's internal logic, not objective likelihoods. Useful for understanding *dynamics* and *sensitivity*, not for prediction.

---

## Table of Contents

- [Overview](#overview)
- [Theoretical Foundation](#theoretical-foundation)
- [Players and Strategies](#players-and-strategies)
- [Discount Factors (Historical Calibration)](#discount-factors-historical-calibration)
- [Temporal Framework](#temporal-framework)
- [Model Subsystems (13 Mechanisms)](#model-subsystems-13-mechanisms)
  - [1. Hybrid Action Vectors](#1-hybrid-action-vectors)
  - [2. Fog of War / BDA Bias](#2-fog-of-war--bda-bias)
  - [3. Iran Rally Under Bombing](#3-iran-rally-under-bombing)
  - [4. Bimodal Shocks](#4-bimodal-shocks)
  - [5. Hormuz Demining](#5-hormuz-demining)
  - [6. Nuclear Threshold](#6-nuclear-threshold)
  - [7. Iran Casualty Threshold](#7-iran-casualty-threshold-nonlinear)
  - [8. Economic Phase Transitions](#8-economic-phase-transitions)
  - [9. War Powers Act](#9-war-powers-act)
  - [10. China/Russia as Persistent Actors](#10-chinarussia-as-persistent-actors)
  - [11. Gradual Trump Rhetoric](#11-gradual-trump-rhetoric)
  - [12. Hezbollah Fragmentation](#12-hezbollah-fragmentation)
  - [13. Variable Time Granularity](#13-variable-time-granularity)
- [Economic Subsystem](#economic-subsystem)
  - [Oil Market Model](#oil-market-model)
  - [Structured Economics](#structured-economics)
  - [Hormuz as a Delta-Attack](#hormuz-as-a-delta-attack)
- [Decision Mechanics](#decision-mechanics)
  - [Strategy Selection](#strategy-selection)
  - [Coalition Coordination Subgame](#coalition-coordination-subgame)
  - [Bayesian Belief Updates](#bayesian-belief-updates)
- [Payoff Functions](#payoff-functions)
- [Termination Conditions](#termination-conditions)
- [Iran Leadership Transition](#iran-leadership-transition)
- [Simulation Results (500 Runs)](#simulation-results-500-runs)
  - [Base Scenario](#base-scenario)
  - [Outcome Archetypes](#outcome-archetypes)
  - [Sensitivity: Trump Patience](#sensitivity-trump-patience)
  - [Sensitivity: Starting Oil Price](#sensitivity-starting-oil-price)
  - [What-If Scenarios](#what-if-scenarios)
- [Key Findings](#key-findings)
- [Limitations](#limitations)
- [Project Structure](#project-structure)
- [Usage](#usage)

---

## Overview

The model simulates a military conflict starting February 28, 2026, with 4 players making strategic decisions each round. Each simulation runs round-by-round until a termination condition is met. 500 Monte Carlo runs are aggregated into probabilistic outcome distributions.

The core loop:
1. Each player selects a strategy by maximizing expected discounted payoff (best-response to beliefs about opponents)
2. USA-Israel coordinate via a coalition bargaining subgame
3. Round effects are applied (military damage, casualties, oil price changes, economic cascades)
4. Stochastic shocks are rolled (bimodal outcomes)
5. Subsystems update (leadership, rhetoric, nuclear status, regional actors, fog of war, great powers, Hezbollah fragmentation)
6. Bayesian beliefs are updated based on observed actions
7. Termination conditions are checked

---

## Theoretical Foundation

The model draws on a substantial body of conflict theory and game theory literature:

| Author | Work | Concept Used |
|---|---|---|
| Fearon (1994/1995) | Rationalist Explanations for War | Information asymmetry, commitment problem |
| Schelling (1960) | The Strategy of Conflict | Escalation ladder, credible commitment |
| Powell (2006) | War as a Commitment Problem | Nuclear threshold, inability to credibly commit |
| Zartman (2000) | Ripeness Theory | "Hurting stalemate" as precondition for negotiation |
| Pape (1996) | Bombing to Win | Strategic bombing rarely breaks morale (rally effect) |
| Mueller (1973) | War, Presidents, and Public Opinion | Public support dynamics for wars |
| Gelpi, Feaver, Reifler (2006) | Casualty Sensitivity | Tolerance for casualties depends on framing |
| Hamilton (2003) | Oil Price Shocks | Economics of oil supply disruptions |
| O'Hanlon (2009) | The Science of War | Systematic BDA overestimation |
| Jervis (1976) | Perception and Misperception | Cognitive biases in conflict decisions |
| Kahneman & Renshon (2007) | Why Hawks Win | Hawkish bias under uncertainty |
| Slantchev (2003) | The Principle of Convergence | Bargaining during war |
| Byman & Waxman (2002) | The Dynamics of Coercion | Coercive diplomacy limitations |

---

## Players and Strategies

| Player | Role | Available Strategies | Initial State |
|---|---|---|---|
| **USA** | Coalition leader | Air Strikes, Ground Operation, Standoff Only, Declare Victory, Negotiate | Military 100, Support 55, delta=0.82 |
| **Israel** | Coalition junior partner | Joint Strikes, Independent Ops, Defensive Posture, Push for Talks | Military 85, Support 72, delta=0.85 |
| **Iran** | Adversary | Retaliate, Proxy Escalation, Attrition, Negotiate, Hormuz Blockade | Military 65, Support 78, delta=0.95 |
| **Hezbollah** | Semi-autonomous proxy | Full Barrage, Calibrated Strikes, Hold Fire, Independent Ceasefire | Military 55, Missiles 85, delta=0.85 |

---

## Discount Factors (Historical Calibration)

The discount factor (delta) is the key parameter governing a player's "patience" — how much they value future gains vs present costs. Lower delta = more impatient, wants quick results.

**Trump 2026 (delta=0.82, range 0.77-0.87):**
Calibrated against historical analogs:
- Iraq invasion: delta~0.76 (impatient)
- Gulf War: delta~0.85 (moderate)
- Afghanistan: delta~0.90 (patient, post-9/11 rally)
- Adjustments: election proximity (-0.04), war fatigue (-0.024), social media acceleration (-0.006)
- Source: `calibrate_patience.py` using Gallup/Mueller empirical support decay data

**Israel 2026 (delta=0.85, range 0.82-0.88):**
- Lebanon 2006: delta~0.72 (short war, low tolerance)
- Protective Edge 2014: delta~0.81
- Gaza 2023: delta~0.99 (existential framing after Oct 7)
- Key insight: existential framing adds +0.10 (Gelpi-Feaver-Reifler)

**Iran rational (delta=0.95):**
Authoritarian regime, no elections, survival mode. Can absorb costs that democracies cannot.

**Iran revolutionary (delta=0.97):**
Iran-Iraq War precedent: 8 years, 500K KIA, GDP -40% — and they continued.

**Hezbollah (delta=0.85):**
Proxy actor, dependent on Iran, Lebanon's fragile domestic politics limits tolerance.

---

## Temporal Framework

Variable time granularity (v5 FIX #13):

| Phase | Days | Resolution | Rounds |
|---|---|---|---|
| Phase 1 | Days 1-7 | 1 day/round | 7 rounds |
| Phase 2 | Days 8-28 | 3 days/round | 7 rounds |
| Phase 3 | Day 29+ | 7 days/round | Unlimited |

The first 48 hours get 2 rounds of resolution. Maximum ~40 rounds (up to November 2026 midterms).

Key calendar events:
- **Day 1 (Feb 28):** Khamenei killed in initial strike
- **Day 8 (Mar 8):** Mojtaba Khamenei elected Supreme Leader
- **Day 60:** War Powers Act deadline (no AUMF)
- **Nov 3, 2026:** US midterm elections
- **Ramadan 2026:** Feb 17 — Mar 19 (affects attrition narrative)

---

## Model Subsystems (13 Mechanisms)

### 1. Hybrid Action Vectors

Instead of a single Enum strategy, each player executes a **continuous intensity vector**: `{strike: 0.7, hormuz: 0.9, negotiate: 0.1}`. This captures situations like "Iran blockades Hormuz AND negotiates simultaneously." Intensity 0.1-1.0 maps to effect scale 0.5-1.2x. Secondary actions in the vector also produce proportional effects.

Example: Ground operation at intensity 0.8 includes air strikes at 0.5 and standoff at 0.15 — because real militaries don't do one thing at a time.

### 2. Fog of War / BDA Bias

Coalition overestimates damage dealt by 20-40% (O'Hanlon 2009). Historical precedent:
- **Kosovo 1999:** NATO claimed 120 tanks destroyed, actual count was 14
- **Iraq 2003:** Similar pattern of BDA overestimation

Implementation:
- `coalition_bda_bias = 1.3` — coalition thinks it destroyed 30% more than reality
- `iran_capability_bluff = 1.2` — Iran claims 20% more capability than actual
- `intel_noise = 0.15` — standard deviation as fraction of true value
- All decisions are made on **perceived**, not actual state

### 3. Iran Rally Under Bombing

Pape (1996): strategic bombing INCREASES morale rather than breaking it.

Historical patterns:
- **London Blitz 1940-41:** British morale increased
- **Germany 1943-44:** Production increased despite strategic bombing
- **North Vietnam 1965-72:** Rolling Thunder strengthened the regime
- **Iran-Iraq War:** Iraqi bombing of Iranian cities rallied the population

Implementation:
- Weeks 1-4: rally +1.0 to +3.0 per round (strong early rally)
- Weeks 4-12: moderate +0.0 to +1.5
- Week 12+: fatigue sets in, -0.5 to +0.5
- Revolutionary regime gets 1.3x multiplier
- Massive casualties (>3K/round) can eventually overcome the rally effect

### 4. Bimodal Shocks

Every stochastic shock has TWO possible outcomes — "Pearl Harbor vs Beirut Barracks." The same event can rally a nation or break its will.

**9 shock types:**

| Shock | Prob/Round | Path A (Rally) | Path B (Retreat) |
|---|---|---|---|
| US Ship Sunk | 4% | 40%: Pearl Harbor effect (+20 support, AUMF passes) | 60%: Beirut barracks ("why are we there?", -25 support) |
| Iran Nuclear Test | 2% | 80%: Justifies war, massive rally | 20%: Panic, "war made it worse" |
| Iran Leadership Killed | 3% | 50%: Command chaos, morale drops | 50%: Martyrdom rally, hardliners empowered |
| Hormuz Tanker Disaster | 5% | 30%: "Iran must be stopped" | 70%: Oil spikes, "end this war" |
| Hezbollah Arsenal Destroyed | 3% | 85%: Major capability blow | 15%: Secondary explosions in civilian area |
| Israeli City Mass Casualty | 3% | 60%: Society rallies, demands total victory | 40%: Panic, evacuation, government blamed |
| Iranian Civilian Massacre | 4% | 25%: Muted reaction | 75%: International condemnation, US protests |
| US Domestic Crisis | 4% | 50%: Minor distraction | 50%: War becomes secondary priority |
| Iraqi Militia Attacks US Base | 6% | 50%: "Proxies must be stopped" | 50%: "Another quagmire" |

Shock probabilities increase slightly each round: `adjusted_p = base_p * (1 + round * 0.02)`.

### 5. Hormuz Demining

Post-blockade Hormuz recovery: +0.5-1.5%/round (not +5-10% as in earlier versions). Historical calibration: 1988 Tanker War — mine clearance took approximately 6 months after fighting stopped. Even without active blockade, mines remain and insurance markets are slow to react.

### 6. Nuclear Threshold

"Use-it-or-lose-it" logic (Powell 2006): when conventional military capacity drops below 20%, nuclear breakout probability starts rising. The breakout decision is **decoupled** from conflict termination — creating a race between coalition facility destruction and Iran's decision to break out.

Four status levels: `Latent -> Breakout Capable -> Tested -> Deployed`

Breakout probability increases from multiple pressure sources:
- Military capacity <20%: `military_pressure * 0.025`
- Infrastructure <25%: `+0.015`
- Facility urgency >50% destroyed: `facility_urgency * 0.02`
- Must still have >10% facilities surviving to attempt breakout

### 7. Iran Casualty Threshold (Nonlinear)

Not linear: low sensitivity up to threshold, then sudden collapse.

| Casualties | Sensitivity | Description |
|---|---|---|
| < threshold * 0.5 | 1.0x | Regime barely notices |
| < threshold | 1.0-3.0x | Growing discomfort |
| > threshold | 3.0 + excess * 1.5 | "Drinking poison" — accelerating collapse |

Threshold: 15K for revolutionary regime, 8K for rational. Calibrated against Iran-Iraq War: 500K casualties tolerated for 8 years, then sudden end.

### 8. Economic Phase Transitions

Nonlinear economic damage from oil price:

| Oil Price | Regime | Damage Multiplier | Description |
|---|---|---|---|
| $85-130 | Linear slowdown | 1.0x | Hamilton (2003) standard model |
| $130-180 | Accelerating | 1.0-3.0x | Panic, hoarding, speculation |
| $180-220 | Systemic crisis | 3.0-5.0x | Margin calls, bank stress, supply chains break |
| $220+ | Financial crisis | 5.0x+ | 2008-like cascading failures |

**Hysteresis:** GDP drops fast from oil shock but recovers slowly. Mild recession = 0.5x recovery rate. Deep recession (GDP <93) = 0.25x recovery rate. Asymmetric by design — economies break fast and heal slow.

### 9. War Powers Act

60-day clock: without AUMF (Authorization for Use of Military Force), Trump faces a constitutional crisis at approximately week 9.

- Day 0-44: no pressure (0.0)
- Day 45-60: linear ramp to 1.0
- Day 60+: sustained at 1.0 (constitutional challenge)

### 10. China/Russia as Persistent Actors

Not one-time shocks but evolving strategic actors:

**China:**
- Loses from Hormuz closure (60% of oil imports transit the Strait)
- Mediation interest grows with accumulated oil pain
- Diplomatic pressure on USA increases over time
- Backs off if Iran is clearly losing (military <20%)

**Russia:**
- Gains from high oil prices (oil windfall accumulates)
- Intelligence support to Iran (satellite imagery): baseline 0.3, grows with oil windfall
- Blocks UN resolutions (probability 0.8)
- Reduces support if Iran approaching collapse (don't back a loser)

### 11. Gradual Trump Rhetoric

Scale 0-1 instead of binary "declared victory / didn't":

| Intensity | Example Rhetoric |
|---|---|
| 0.0-0.3 | "Going very well, tremendous progress" |
| 0.3-0.5 | "We're winning bigly, almost done" |
| 0.5-0.7 | "War is essentially over, just cleanup" |
| 0.7-1.0 | "Mission accomplished, bringing troops home" |

**Mission Accomplished Trap** (Bush precedent, May 1 2003): each victory claim creates future liability. Gap between rhetoric and reality erodes credibility and triggers support collapse. Decisions are based on **perceived** state (BDA-biased), not reality — Trump believes his own briefings.

Key mechanics:
- Rhetoric driven by Trump's `confidence_level` (based on biased BDA)
- Cumulative rhetoric "debt" — each claim creates future liability
- Credibility erodes when rhetoric exceeds reality by >0.2
- Commitment trap active when `rhetoric > 0.5` and `credibility < 0.7`

### 12. Hezbollah Fragmentation

Post-Nasrallah Hezbollah = fragmented command structure:

| Parameter | Initial | Description |
|---|---|---|
| `command_coherence` | 0.6 | 1.0 = unified, 0.0 = fully fragmented (already degraded from 2024-25 strikes) |
| `iran_control` | 0.5 | How much Tehran directs operations |
| `local_commanders` | 5 | Surviving semi-autonomous unit commanders |

Dynamics:
- Israeli strikes degrade coherence (-0.02 to -0.06 per round)
- Commander kills: 5% chance per round, each kill removes -0.05 coherence
- Low coherence (<0.3): 30% chance of spontaneous local ceasefires
- Effective combat power = `coherence * 0.6 + iran_control * 0.4` (min 0.3)
- Military capacity <30% forces coherence below `military/50`

### 13. Variable Time Granularity

See [Temporal Framework](#temporal-framework). Round weight scales payoff effects proportionally — a weekly round has 7x the effect of a daily round.

---

## Economic Subsystem

### Oil Market Model

Detailed simulation of global oil market:

| Component | Value | Source |
|---|---|---|
| Hormuz throughput | ~21M bbl/day (21% of global consumption) | EIA data |
| Blockade impact | 60-90% flow reduction depending on severity | — |
| SPR (Strategic Petroleum Reserve) | 400M barrels, release up to 1M bbl/day when oil >$110 | US DOE |
| OPEC spare capacity | 3-4M bbl/day, ramps up at ~15%/round of target | — |
| Shipping reroute | Cape of Good Hope: +10 days, +$1M/tanker insurance | — |
| Price elasticity | ~$8-12 per M bbl/day disrupted | Hamilton (2003) |
| Speculation premium | Up to $20 initially, decays over time | — |
| Seasonality | Winter +$5, summer -$2 | — |
| Hard bounds | $60-$300 per barrel | — |

Price formula: `target = pre_war + disruption_premium + shipping_premium + seasonal + speculation + mean_reversion`, then `price += (target - price) * friction_factor`.

### Structured Economics

Each player has a structured `EconomicState` with:

| Indicator | Description |
|---|---|
| GDP Index | 100 = pre-war baseline |
| Inflation Rate | Annual %, lagged effects from oil |
| War Spending | % of GDP (USA: $900M/day air, $2B+/day ground) |
| Trade Disruption | 0-100 scale |
| Budget Deficit Extra | Additional deficit from war costs |
| Unemployment Delta | Change from baseline, lagged from GDP |

**Lagged cascade effects:**
1. Oil price -> gas pump prices (immediate)
2. Oil price -> broader inflation (1-round lag)
3. Inflation -> GDP decline (2-round lag)
4. GDP decline -> unemployment (3-round lag)

**Player-specific dynamics:**
- **USA:** Net oil producer (moderate benefit from high prices via shale), but consumers hurt more than producers gain. War costs: ~$900M/day for air campaign, $2B+ for ground operations.
- **Israel:** 100% oil importer — extremely price-sensitive. Reservist mobilization = tech sector productivity loss.
- **Iran:** Hormuz blockade also cuts Iran's own exports (~$200M/day lost). Economy already constrained by sanctions (starting inflation 35%).

### Hormuz as a Delta-Attack

Key v4 innovation: Hormuz blockade is NOT just economic damage — it's a **direct attack on Trump's discount factor**. Every stuck tanker = gas prices in Ohio and Pennsylvania.

| Oil Price | Delta Reduction | Description |
|---|---|---|
| $100 | -0.01 | Noticeable |
| $130 | -0.03 | Painful |
| $150 | -0.05 | Severe |
| $200+ | -0.10 | Political crisis |

Amplified by:
- Inflation above 5%: `1.0 + (inflation - 5) * 0.1` multiplier
- Midterm proximity (<20 weeks): `1.0 + (20 - weeks) * 0.05` multiplier

This means Iran's optimal strategy is not military — it's economic warfare through Hormuz.

---

## Decision Mechanics

### Strategy Selection

Each player maximizes expected discounted payoff via **best-response dynamics** (approximate Nash equilibrium):

1. For each possible strategy, calculate Expected Value
2. `EV = SUM(weight * payoff)` across all possible opponent strategy combinations
3. Opponent weights determined by Bayesian beliefs about opponent type
4. Gaussian noise added (bounded rationality, `sigma = 0.5-0.8`)
5. Hard overrides applied (panic thresholds, support collapse)

Hard overrides examples:
- USA: `pain > 55` AND `support < 25` -> Negotiate
- USA: `Iran military < 12` AND `Iran infra < 15` -> Declare Victory
- USA: Midterm pressure > 0.7 AND support < 35 -> Declare Victory
- Iran: Even revolutionaries surrender when `pain > 85`, `military < 8`, `missiles < 5`
- Hezbollah: Near destruction (`military < 15` or `missiles < 10`) -> Ceasefire

### Coalition Coordination Subgame

USA-Israel bargaining game within each round:

**USA leverage:** weapons supply, diplomatic cover, intelligence sharing
**Israel leverage:** urgency (existential threat), higher pain tolerance, audience cost

Key dynamics:
- **Divergence** grows after week 4: `gap += 0.1 * (round - 4)`, plus `0.15` if USA support <40
- **Mission Accomplished forcing:** If Trump's rhetoric trap is active, his rhetoric forces exit even if strategically suboptimal
- **Closing window:** Israel knows US exit is coming and acts preemptively — accelerates independent operations while US still provides cover
- **Netanyahu races the clock:** When `round > 6` AND `USA support < 45` AND `Israel military > 50`, Israel shifts to independent ops

Four coordination outcomes:
1. **Aligned:** Both want the same thing, no friction
2. **USA exit / Israel fight:** Tension, Israel either drags USA in or goes independent
3. **USA fight / Israel tired:** USA pushes Israel to continue via audience cost
4. **Regional constraint:** Reduced base access from regional actors forces standoff-only operations

### Bayesian Belief Updates

Coalition and Iran update beliefs about opponent type (rational vs revolutionary):

| Observed Action | Likelihood Rational | Likelihood Revolutionary |
|---|---|---|
| Negotiate, Push for Talks, Ceasefire | 0.85 | 0.15 |
| Hold Fire, Defensive Posture | 0.60 | 0.40 |
| Neutral actions | 0.50 | 0.50 |
| Escalation (proxy, ground, barrage, hormuz) | 0.10-0.20 | 0.80-0.90 |

Escalation **under high pain** is a very strong revolutionary signal — the likelihood ratio shifts further based on `pain / 60.0`.

---

## Payoff Functions

### USA Payoff

| Component | Effect | Notes |
|---|---|---|
| Air strikes | +3.0 (degrading with own capacity loss) | Core value |
| Ground operation | -2.0 (additional -1.5 in summer heat) | Political cost |
| Standoff only | +2.0 | Low risk |
| Declare victory (Iran mil <30%) | +1.0 | Rational exit |
| Declare victory (Iran mil >=30%) | -3.0 | Premature |
| Iran resistance (retaliate/proxy) | -2.0 | Cost of ongoing conflict |
| Hormuz blockade | -4.0 | Economic crisis |
| Oil >$100 | -(oil - 100) * 0.04 | Linear damage |
| Oil >$150 | -(oil - 150) * 0.08 | Accelerating |
| Oil >$200 | -(oil - 200) * 0.12 | Crisis |
| Inflation >5% | -(inflation - 5) * 0.8 | Voter pain |
| GDP decline | -(100 - gdp) * 0.5 | Recession signal |
| War spending | -spending * 3.0 | Budget pressure |
| SPR depletion (<200M bbl) | -(200 - spr) * 0.01 | Strategic reserve anxiety |
| US casualties | -casualties_K * 10.0 | High sensitivity |
| Mission Accomplished trap | -(1 - credibility) * 3.0 | Can't continue after declaring "almost over" |
| Nuclear threat + declare victory | -threat * 8.0 | Can't leave with nuclear risk |
| All components | * delta^round | Time discounting |

### Israel Payoff

| Component | Effect |
|---|---|
| USA striking | +3.0 |
| Joint strikes | +2.5 |
| Independent ops | +2.0 |
| Hezbollah full barrage | -6.0 (plus displaced penalty) |
| Oil >$100 | -(oil - 100) * 0.06 (1.5x vs USA: 100% importer) |
| War spending | -spending * 4.0 |
| Casualties | -casualties_K * 6.0 |
| USA withdrawing | -4.0 (abandonment fear) |

### Iran Payoff

| Component | Effect |
|---|---|
| Retaliate | +2.0 |
| Proxy escalation | +2.5 |
| Hormuz blockade | +delta_damage * 40 (capped at 6.0) minus self-damage |
| Oil >$150 | +(oil - 150) * 0.02 |
| USA recession risk >0.3 | +recession_risk * 3.0 |
| US casualties >0.1K | +us_casualties * 5.0 (political win) |
| Own casualties | -casualties * sensitivity (nonlinear, see threshold model) |
| USA ground operation | -4.0 |
| Negotiate (Mojtaba pre-consolidation) | -audience_cost * 0.5 minus negotiate_penalty (up to -9.0) |
| Nuclear threat >0.3 | +threat * 2.0 (deterrence value) |
| Leadership delta bonus | effective_delta = delta + bonus (Mojtaba paradox) |

### Hezbollah Payoff

| Component | Effect |
|---|---|
| Calibrated strikes | +2.0 (optimal balance of loyalty and preservation) |
| Arsenal preservation | +(missile_stock / 100) * 3.0, modulated by strategy |
| Israel striking Hezbollah | -3.0 |
| Coordination with Iran | +1.5 (when both fighting) |
| Near destruction + ceasefire | +4.0 (survival = rational) |
| Lebanese domestic backlash | -2.0 (when casualties >0.5K or infra <50%) |
| Iran negotiating + full barrage | -2.0 (fighting without patron) |

---

## Termination Conditions

| Outcome | Conditions |
|---|---|
| **Coalition Decisive Victory** | Iran military <5% AND infrastructure <10% AND missiles <5% |
| **Coalition Limited Victory** | USA declares victory AND Iran military <25% AND infrastructure <30% |
| **Iran Strategic Victory** | USA support <15%, OR economy <15%, OR (recession >70% AND GDP <93), OR USA declares victory while Iran military >=45% |
| **Negotiated Settlement** | Both sides choose negotiate/ceasefire/declare victory, OR Israel forced out (support <15%, casualties >0.8K, pushing for talks) |
| **Frozen Conflict** | USA pain >45 AND Iran pain >55, neither side negotiating |

---

## Iran Leadership Transition

The model simulates the Khamenei -> Mojtaba transition with explicit dynamics:

**Day 1 (Feb 28, 2026): Khamenei killed in strike**
- Legitimacy drops to 0.3 (IRGC holds power, no formal leader)
- Public support -8 (shock)
- Military capacity -5 (command disruption)
- **Paradox:** delta INCREASES by +0.02 (rally effect: "we must resist")

**Day 8 (Mar 8): Mojtaba Khamenei elected Supreme Leader**
- Legitimacy = 0.4 (son of Khamenei, but unproven)
- Public support +5 (continuity relief)
- Audience cost +8: Mojtaba CANNOT negotiate now
- Negotiate penalty: up to -9.0 (negotiating = regime weakness = collapse risk)
- Delta bonus: +0.03 (must prove himself = more patient)

**~15 weeks: Consolidation complete (legitimacy >0.7)**
- Mojtaba can finally consider negotiation
- Legitimacy grows at +0.04/week if regime demonstrates resolve

**Key insight:** Killing Khamenei INCREASED Iran's delta temporarily. The new leader must be tougher than his predecessor to establish legitimacy. This is the paradox of decapitation strikes.

---

## Simulation Results (500 Runs)

### Base Scenario

| Metric | Value |
|---|---|
| Coalition victory | 72.6% |
| Iran strategic victory | 27.0% |
| Negotiated settlement | 0.4% |
| Average duration | 11.2 rounds |
| Average oil price | $136.3 |
| Nuclear risk | 21.0% |
| US casualties | 0.24K |
| Iran casualties | 2.37K |
| Recession probability | 16% |

### Outcome Archetypes

| Archetype | % | Description |
|---|---|---|
| **Pyrrhic Victory** | 46.0% | Coalition wins but oil >$150, heavy economic cost, long war. The most common outcome. |
| **Managed Degradation** | 19.2% | Clean coalition win: Iran military degrades, oil stays ~$83, no Hormuz crisis. ~10 rounds. |
| **Quick US Withdrawal** | 13.6% | US withdraws early (~3 rounds) due to political pressure. Iran declares strategic victory despite taking damage. |
| **Hormuz Exhaustion** | 12.4% | Iran blocks the Strait, oil spikes to ~$177. Coalition wins militarily but economic pain triggers withdrawal. |
| **Nuclear Shadow** | 5.8% | Coalition wins, but Iran achieves nuclear breakout. Tactical victory, strategic uncertainty. |
| **Attrition War** | 1.0% | Long grinding conflict. Both sides exhausted. Iran survives long enough for US domestic pressure to force withdrawal. |
| **Diplomatic Exit** | 0.2% | Rare: external mediation (China?) enables face-saving deal. |

### Sensitivity: Trump Patience

| Delta | Coalition Win | Iran Win | Avg Rounds | Avg Oil | Nuclear | Recession |
|---|---|---|---|---|---|---|
| 0.70 (impatient) | 67.3% | 32.7% | 10.2 | $130 | 17.3% | 12% |
| 0.75 | 68.7% | 31.0% | 10.7 | $132 | 21.0% | 13% |
| 0.78 | 70.7% | 29.0% | 10.9 | $134 | 22.7% | 14% |
| **0.82 (baseline)** | **72.6%** | **27.0%** | **11.2** | **$136** | **21.0%** | **16%** |
| 0.85 | 75.7% | 24.0% | 11.5 | $138 | 22.3% | 18% |
| 0.88 | 76.4% | 23.7% | 11.5 | $139 | 23.0% | 18% |
| 0.93 (Bush-like) | 81.0% | 19.0% | 11.9 | $139 | 22.3% | 18% |

**Takeaway:** +0.11 delta gives +14% coalition chances, but raises oil by $9 and recession risk from 12% to 18%. Patience buys victory but at economic cost.

### Sensitivity: Starting Oil Price

| Oil Start | Coalition Win | Iran Win | Avg Oil | Recession |
|---|---|---|---|---|
| $75 | 75.7% | 24.3% | $131 | 11% |
| **$85 (baseline)** | **72.6%** | **27.0%** | **$136** | **16%** |
| $95 | 69.7% | 30.3% | $145 | 24% |
| $105 | 68.3% | 31.7% | $155 | 35% |
| $115 | 60.3% | 39.7% | $169 | 48% |
| $130 | 41.7% | 58.3% | $198 | 66% |

**Takeaway:** Oil price is the single most powerful lever. At $130 start, Iran wins 58% of the time. Hormuz blockade becomes devastating when oil is already expensive.

### What-If Scenarios

| Scenario | Coalition | Iran | Key Insight |
|---|---|---|---|
| Base | 72.6% | 27.0% | — |
| Rational Iran | 80.7% | 19.3% | Rational Iran capitulates faster |
| Impatient Trump (delta=0.75) | 68.7% | 31.0% | Early withdrawal |
| Trump like Bush (delta=0.93) | 80.3% | 19.7% | Long war, more casualties |
| Oil already $110 | 64.6% | 35.3% | Iran's economic warfare leverage |
| Nuclear sites 50% pre-destroyed | 73.7% | 26.0% | Nuclear risk drops: 21% -> 2.3% |
| No random shocks | 82.0% | 17.7% | Shocks are the primary source of variance |

---

## Key Findings

1. **Coalition wins ~73% of scenarios** but the most common outcome (46%) is a "Pyrrhic victory" with oil >$150 and significant economic damage.

2. **Oil price is the single biggest lever.** Starting at $130 instead of $85 flips the odds: Iran wins 58% vs 27%. Iran's strategy of blocking the Strait of Hormuz becomes devastating when oil is already expensive.

3. **Trump's patience matters significantly.** An impatient Trump (delta=0.70, quick withdrawal) gives Iran a ~33% chance. A patient "Bush-like" commitment (delta=0.93) drops Iran's chances to ~19% — but at the cost of higher oil prices and greater recession risk.

4. **Nuclear breakout paradoxically helps the coalition.** When Iran approaches nuclear capability, it triggers escalation that accelerates Iran's military destruction. But it creates long-term instability.

5. **Short wars favor Iran.** If the war ends in <8 rounds, Iran wins 100% of the time — because the only reason for a short war is US withdrawal.

6. **"Managed degradation" (clean win) happens only 19% of the time.** In most scenarios, even winning is expensive.

7. **Stochastic shocks are the primary source of variance.** Without shocks, coalition wins 82%. With them, 73%. Each shock is bimodal — the same event can rally or break a nation.

---

## Limitations

The model does **NOT** capture:
- Full-spectrum diplomacy
- Intelligence operations (HUMINT, SIGINT beyond BDA)
- Cyber warfare
- Internal regime politics (IRGC factions, reform movement)
- Direct Chinese/Russian military involvement (only economic/diplomatic effects)
- Humanitarian costs and refugee dynamics beyond displacement counts
- Long-term occupation dynamics
- Media warfare and information operations
- Terrain and weather effects beyond summer heat penalty
- Supply chain logistics detail
- Domestic US congressional dynamics beyond War Powers clock
- Allied partner operations (UK, France, etc.)

---

## Project Structure

| File | Purpose |
|---|---|
| `game_theory_conflict_model.py` | Core model: ~2700 lines of Python. 4-player repeated game with approximate Nash equilibrium, stochastic shocks, oil dynamics, nuclear escalation, fog of war, economic phase transitions, and 13 subsystems. |
| `calibrate_patience.py` | Historical calibration of discount factors using Gallup/Mueller empirical support decay data |
| `analyze_war_duration.py` | War duration analysis across simulation runs |
| `analyze_distributions.py` | Outcome distribution analysis toolkit |
| `generate_viz_data.py` | Generate visualization data from model runs |
| `viz_data.json` | Pre-computed visualization data for the dashboard |
| `index.html` | Interactive visualization: single-page app with embedded data, all CSS/JS in one file |

---

## Usage

```bash
# Install dependencies
pip install numpy scipy

# Run the model (prints simulation results)
python game_theory_conflict_model.py

# Regenerate visualization data
python generate_viz_data.py

# View the dashboard
open index.html
```

To customize a simulation:

```python
from game_theory_conflict_model import SimulationConfig, run_simulation

config = SimulationConfig(
    max_rounds=40,
    iran_is_revolutionary=True,
    initial_oil_price=110.0,
    usa_discount=0.78,        # impatient Trump
    israel_discount=0.85,
    iran_discount=0.95,
    enable_shocks=True,
    enable_fog_of_war=True,
    enable_great_powers=True,
    coalition_bda_bias=1.3,    # 30% BDA overestimation
    seed=42,                   # for reproducibility
)

result = run_simulation(config)
print(f"Outcome: {result['outcome']}")
print(f"Rounds: {len(result['history'])}")
print(f"Final oil: ${result['history'][-1].oil_price:.0f}")
```
