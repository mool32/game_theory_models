#!/usr/bin/env python3
"""Generate pre-computed data for the interactive visualization."""

import json
import sys
from collections import defaultdict

from game_theory_conflict_model import (
    SimulationConfig, run_simulation, run_simulation_from_state,
    monte_carlo, monte_carlo_warm_start, DAY_36_STATE,
)


def generate_viz_data():
    print("Generating visualization data...", flush=True)

    data = {}

    # 1. Single detailed simulation for timeline (cold start)
    print("  [1/7] Single simulation timeline...", flush=True)
    result = run_simulation(SimulationConfig(seed=42, iran_is_revolutionary=True))
    timeline = []
    for h in result["history"]:
        timeline.append({
            "round": h.round_num,
            "date": h.date,
            "usa": h.usa_strategy,
            "iran": h.iran_strategy,
            "israel": h.israel_strategy,
            "hez": h.hezbollah_strategy,
            "oil": h.oil_price,
            "hormuz": h.hormuz_flow_pct,
            "iran_mil": h.iran_military,
            "usa_cas": h.usa_casualties,
            "iran_cas": h.iran_casualties,
            "israel_cas": h.israel_casualties,
            "usa_support": h.usa_support,
            "iran_support": h.iran_support,
            "recession_risk": h.usa_recession_risk,
            "iran_missiles": h.iran_missiles,
            "hez_missiles": h.hez_missiles,
            "shocks": h.shocks,
        })
    data["timeline"] = {
        "outcome": result["outcome"],
        "rounds": timeline,
    }

    # 2. Sensitivity: USA patience slider (7 points)
    print("  [2/7] USA patience sensitivity...", flush=True)
    usa_patience = {}
    for d in [0.70, 0.75, 0.78, 0.82, 0.85, 0.88, 0.93]:
        mc = monte_carlo(300, {"iran_is_revolutionary": True, "usa_discount": d})
        usa_patience[str(d)] = {
            "outcomes": mc["outcome_distribution"],
            "avg_rounds": mc["avg_rounds"],
            "avg_oil": mc["avg_final_oil_price"],
            "nuclear": round(mc["nuclear_breakout_rate"] * 100, 1),
            "usa_cas": mc["avg_usa_casualties_k"],
            "iran_cas": mc["avg_iran_casualties_k"],
            "recession": mc["economics"]["avg_usa_recession_risk"],
        }
    data["sensitivity_usa_patience"] = usa_patience

    # 3. Sensitivity: Oil price (6 points)
    print("  [3/7] Oil price sensitivity...", flush=True)
    oil_sens = {}
    for p in [75, 85, 95, 105, 115, 130]:
        mc = monte_carlo(300, {"iran_is_revolutionary": True, "initial_oil_price": p})
        oil_sens[str(p)] = {
            "outcomes": mc["outcome_distribution"],
            "avg_rounds": mc["avg_rounds"],
            "avg_oil": mc["avg_final_oil_price"],
            "nuclear": round(mc["nuclear_breakout_rate"] * 100, 1),
            "usa_cas": mc["avg_usa_casualties_k"],
            "iran_cas": mc["avg_iran_casualties_k"],
            "recession": mc["economics"]["avg_usa_recession_risk"],
        }
    data["sensitivity_oil"] = oil_sens

    # 4. Trajectory archetypes (n=500)
    print("  [4/7] Trajectory archetypes...", flush=True)
    base = SimulationConfig(iran_is_revolutionary=True)
    archetype_counts = defaultdict(int)
    archetype_examples = defaultdict(list)
    n = 500

    for i in range(n):
        cfg_dict = {f.name: getattr(base, f.name)
                    for f in base.__dataclass_fields__.values()}
        cfg_dict["seed"] = i
        cfg = SimulationConfig(**cfg_dict)
        r = run_simulation(cfg)

        outcome = r["outcome"]
        rounds = r["rounds_played"]
        nuclear = any("NUCLEAR_BREAKOUT" in str(e) for e in r.get("v4_events", []))
        hormuz = r.get("hormuz_flow_pct", 100) < 80
        max_oil = max(h.oil_price for h in r["history"]) if r["history"] else 85

        if outcome == "coalition_decisive_victory" and rounds < 8:
            arch = "Quick Knockout"
        elif outcome == "coalition_limited_victory" and not nuclear and max_oil < 150:
            arch = "Managed Degradation"
        elif outcome == "coalition_limited_victory" and max_oil >= 150:
            arch = "Pyrrhic Victory"
        elif outcome == "coalition_limited_victory" and nuclear:
            arch = "Nuclear Shadow"
        elif outcome == "iran_strategic_victory" and hormuz:
            arch = "Hormuz Exhaustion"
        elif outcome == "iran_strategic_victory" and rounds < 5:
            arch = "Quick US Withdrawal"
        elif outcome == "iran_strategic_victory":
            arch = "Attrition War"
        elif outcome == "negotiated_settlement":
            arch = "Diplomatic Exit"
        elif outcome == "frozen_conflict":
            arch = "Frozen Conflict"
        else:
            arch = "Other"

        archetype_counts[arch] += 1
        if len(archetype_examples[arch]) < 1:
            archetype_examples[arch].append({
                "rounds": rounds,
                "oil": r["final_oil_price"],
                "max_oil": max_oil,
                "iran_mil": r["final_iran_military"],
                "usa_cas": r["total_usa_casualties_k"],
                "iran_cas": r["total_iran_casualties_k"],
                "nuclear": nuclear,
            })

    data["archetypes"] = {
        name: {
            "count": archetype_counts[name],
            "pct": round(archetype_counts[name] / n * 100, 1),
            "example": archetype_examples[name][0] if archetype_examples[name] else {},
        }
        for name in sorted(archetype_counts, key=lambda k: -archetype_counts[k])
    }

    # 5. What-if scenarios (cold start)
    print("  [5/7] What-if scenarios...", flush=True)
    scenarios = {
        "Base Scenario": {"iran_is_revolutionary": True},
        "Rational Iran": {"iran_is_revolutionary": False},
        "Impatient Trump": {"iran_is_revolutionary": True, "usa_discount": 0.75},
        "Trump like Bush": {"iran_is_revolutionary": True, "usa_discount": 0.90},
        "Oil already $110": {"iran_is_revolutionary": True, "initial_oil_price": 110},
        "Nuclear sites 50% destroyed": {
            "iran_is_revolutionary": True, "iran_nuclear_facilities_pct": 50},
        "No random shocks": {"iran_is_revolutionary": True, "enable_shocks": False},
    }
    whatif = {}
    for name, overrides in scenarios.items():
        mc = monte_carlo(300, overrides)
        coalition = sum(v for k, v in mc["outcome_distribution"].items()
                       if "coalition" in k)
        iran = mc["outcome_distribution"].get("iran_strategic_victory", 0)
        whatif[name] = {
            "coalition_pct": round(coalition, 1),
            "iran_pct": round(iran, 1),
            "other_pct": round(100 - coalition - iran, 1),
            "avg_rounds": mc["avg_rounds"],
            "avg_oil": mc["avg_final_oil_price"],
            "nuclear": round(mc["nuclear_breakout_rate"] * 100, 1),
            "usa_cas": mc["avg_usa_casualties_k"],
            "iran_cas": mc["avg_iran_casualties_k"],
            "recession": mc["economics"]["avg_usa_recession_risk"],
        }
    data["whatif"] = whatif

    # 6. v6: Day-36 warm start data
    print("  [6/7] Day-36 warm start projections (500 runs)...", flush=True)
    mc_warm = monte_carlo_warm_start(
        n_simulations=500,
        warm_state=DAY_36_STATE,
        config_overrides={"iran_is_revolutionary": True},
    )
    data["day36"] = {
        "outcomes": mc_warm["outcome_distribution"],
        "avg_total_days": mc_warm["avg_total_days"],
        "median_total_days": mc_warm["median_total_days"],
        "avg_oil": mc_warm["avg_final_oil_price"],
        "nuclear": round(mc_warm["nuclear_breakout_rate"] * 100, 1),
        "usa_cas": mc_warm["avg_usa_casualties_k"],
        "iran_cas": mc_warm["avg_iran_casualties_k"],
        "recession_risk": mc_warm["avg_usa_recession_risk"],
    }

    # Day-36 what-if scenarios
    day36_scenarios = {
        "Base (Day 36)": {"iran_is_revolutionary": True},
        "Rational Iran": {"iran_is_revolutionary": False},
        "Impatient Trump (δ=0.75)": {"iran_is_revolutionary": True, "usa_discount": 0.75},
        "Patient Trump (δ=0.88)": {"iran_is_revolutionary": True, "usa_discount": 0.88},
        "No more shocks": {"iran_is_revolutionary": True, "enable_shocks": False},
    }
    day36_whatif = {}
    for name, overrides in day36_scenarios.items():
        mc = monte_carlo_warm_start(300, DAY_36_STATE, overrides)
        coalition = sum(v for k, v in mc["outcome_distribution"].items()
                       if "coalition" in k)
        iran_win = mc["outcome_distribution"].get("iran_strategic_victory", 0)
        day36_whatif[name] = {
            "coalition_pct": round(coalition, 1),
            "iran_pct": round(iran_win, 1),
            "other_pct": round(100 - coalition - iran_win, 1),
            "avg_days": mc["avg_total_days"],
            "avg_oil": mc["avg_final_oil_price"],
            "nuclear": round(mc["nuclear_breakout_rate"] * 100, 1),
            "usa_cas": mc["avg_usa_casualties_k"],
            "iran_cas": mc["avg_iran_casualties_k"],
        }
    data["day36_whatif"] = day36_whatif

    # Day-36 sample timelines
    day36_timelines = {}
    for seed in [42, 7, 23, 88]:
        config = SimulationConfig(seed=seed, iran_is_revolutionary=True)
        result = run_simulation_from_state(DAY_36_STATE, config)
        tl = []
        for h in result["history"]:
            tl.append({
                "round": h.round_num,
                "date": h.date,
                "usa": h.usa_strategy,
                "iran": h.iran_strategy,
                "israel": h.israel_strategy,
                "hez": h.hezbollah_strategy,
                "oil": h.oil_price,
                "hormuz": h.hormuz_flow_pct,
                "iran_mil": h.iran_military,
                "usa_cas": h.usa_casualties,
                "iran_cas": h.iran_casualties,
                "israel_cas": h.israel_casualties,
                "usa_support": h.usa_support,
                "iran_support": h.iran_support,
                "recession_risk": h.usa_recession_risk,
                "iran_missiles": h.iran_missiles,
                "hez_missiles": h.hez_missiles,
                "shocks": h.shocks,
            })
        day36_timelines[str(seed)] = {
            "outcome": result["outcome"],
            "total_days": result["days_elapsed"],
            "rounds": tl,
        }
    data["day36_timelines"] = day36_timelines

    # 7. Model vs Reality comparison data
    print("  [7/7] Model vs Reality data...", flush=True)
    data["model_vs_reality"] = {
        "analysis_date": "2026-04-05",
        "days_elapsed": 36,
        "predictions_correct": [
            {"prediction": "Hormuz blockade", "detail": "Model: 78% probability. Reality: happened Day 3."},
            {"prediction": "Mojtaba succession", "detail": "Model: legitimacy crisis + cannot negotiate early. Reality: confirmed."},
            {"prediction": "Trump rhetoric trap", "detail": "Model: escalating claims → credibility loss. Reality: 'war almost over' Day 14."},
            {"prediction": "No early ceasefire", "detail": "Model: 5-8% probability in first month. Polymarket: 23-31%. Reality: no ceasefire."},
            {"prediction": "IRGC-Mojtaba tension", "detail": "Model: principal-agent problem. Reality: IRGC acting semi-independently."},
            {"prediction": "Mission Accomplished trap", "detail": "Model: if claims ≠ reality → credibility crash. Reality: developing."},
        ],
        "predictions_wrong": [
            {"prediction": "War duration", "model": "Avg 19 days", "reality": "36+ days and counting", "fix": "Raised termination thresholds"},
            {"prediction": "Oil price", "model": "Avg $136", "reality": "$105", "fix": "SPR +50%, OPEC x2, market adaptation"},
            {"prediction": "Regional scope", "model": "Proxy attacks only", "reality": "7 countries struck directly", "fix": "Added direct strikes on 7 countries"},
        ],
        "recalibrations": [
            "Oil model: SPR release +50%, OPEC ramp x2, faster speculation decay, market adaptation factor",
            "Duration: raised termination thresholds (Iran harder to knock out than assumed)",
            "Regional: direct Iranian missile strikes on Bahrain, Jordan, Kuwait, Qatar, Saudi Arabia, UAE, Cyprus",
            "Warm start from Day 36 real-world state",
        ],
    }

    # Write output
    with open("viz_data.json", "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)

    print("Done! Written to viz_data.json", flush=True)


if __name__ == "__main__":
    generate_viz_data()
