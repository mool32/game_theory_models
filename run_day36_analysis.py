#!/usr/bin/env python3
"""Run Day-36 warm-start analysis: 500 Monte Carlo simulations from real-world state."""

import json
import sys
from collections import defaultdict

from game_theory_conflict_model import (
    SimulationConfig, run_simulation, run_simulation_from_state,
    monte_carlo, monte_carlo_warm_start, DAY_36_STATE, WarmStartState,
)


def run_analysis():
    print("=" * 60)
    print("DAY-36 WARM START ANALYSIS")
    print("Starting from real-world state: April 5, 2026")
    print("=" * 60)

    # 1. Monte Carlo: 500 runs from Day 36, revolutionary Iran
    print("\n[1/4] Monte Carlo: 500 runs, revolutionary Iran...", flush=True)
    mc_rev = monte_carlo_warm_start(
        n_simulations=500,
        warm_state=DAY_36_STATE,
        config_overrides={"iran_is_revolutionary": True},
    )
    print(f"  Outcomes: {mc_rev['outcome_distribution']}")
    print(f"  Avg additional rounds: {mc_rev['avg_additional_rounds']}")
    print(f"  Avg total days: {mc_rev['avg_total_days']}")
    print(f"  Median total days: {mc_rev['median_total_days']}")
    print(f"  Avg final oil: ${mc_rev['avg_final_oil_price']}")
    print(f"  Nuclear breakout rate: {mc_rev['nuclear_breakout_rate']*100:.1f}%")
    print(f"  Avg USA casualties: {mc_rev['avg_usa_casualties_k']}k")
    print(f"  Avg Iran casualties: {mc_rev['avg_iran_casualties_k']}k")

    # 2. Monte Carlo: 500 runs, rational Iran (comparison)
    print("\n[2/4] Monte Carlo: 500 runs, rational Iran...", flush=True)
    mc_rat = monte_carlo_warm_start(
        n_simulations=500,
        warm_state=DAY_36_STATE,
        config_overrides={"iran_is_revolutionary": False},
    )
    print(f"  Outcomes: {mc_rat['outcome_distribution']}")
    print(f"  Avg total days: {mc_rat['avg_total_days']}")

    # 3. What-if scenarios from Day 36
    print("\n[3/4] What-if scenarios from Day 36...", flush=True)
    scenarios = {
        "Base (Day 36)": {"iran_is_revolutionary": True},
        "Rational Iran": {"iran_is_revolutionary": False},
        "Impatient Trump (δ=0.75)": {"iran_is_revolutionary": True, "usa_discount": 0.75},
        "Patient Trump (δ=0.88)": {"iran_is_revolutionary": True, "usa_discount": 0.88},
        "Nuclear sites all destroyed": {
            "iran_is_revolutionary": True,
            "iran_nuclear_facilities_pct": 5,
        },
        "No more shocks": {"iran_is_revolutionary": True, "enable_shocks": False},
    }

    whatif = {}
    for name, overrides in scenarios.items():
        mc = monte_carlo_warm_start(300, DAY_36_STATE, overrides)
        coalition = sum(v for k, v in mc["outcome_distribution"].items()
                       if "coalition" in k)
        iran_win = mc["outcome_distribution"].get("iran_strategic_victory", 0)
        whatif[name] = {
            "coalition_pct": round(coalition, 1),
            "iran_pct": round(iran_win, 1),
            "other_pct": round(100 - coalition - iran_win, 1),
            "avg_total_days": mc["avg_total_days"],
            "avg_oil": mc["avg_final_oil_price"],
            "nuclear": round(mc["nuclear_breakout_rate"] * 100, 1),
            "usa_cas": mc["avg_usa_casualties_k"],
            "iran_cas": mc["avg_iran_casualties_k"],
            "avg_recession_risk": mc["avg_usa_recession_risk"],
        }
        print(f"  {name}: coalition={whatif[name]['coalition_pct']}% iran={whatif[name]['iran_pct']}% days={whatif[name]['avg_total_days']}")

    # 4. Sample timelines for visualization
    print("\n[4/4] Generating sample timelines...", flush=True)
    timelines = {}
    for seed in [42, 7, 23, 88]:
        config = SimulationConfig(seed=seed, iran_is_revolutionary=True)
        result = run_simulation_from_state(DAY_36_STATE, config)
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
        timelines[str(seed)] = {
            "outcome": result["outcome"],
            "total_days": result["days_elapsed"],
            "rounds": timeline,
        }
        print(f"  Seed {seed}: {result['outcome']} in {result['days_elapsed']} days")

    # 5. Compare with original cold-start model
    print("\n[Bonus] Original cold-start for comparison...", flush=True)
    mc_cold = monte_carlo(500, {"iran_is_revolutionary": True})

    # Save everything
    output = {
        "day36_revolutionary": mc_rev,
        "day36_rational": mc_rat,
        "day36_whatif": whatif,
        "day36_timelines": timelines,
        "cold_start_comparison": {
            "outcomes": mc_cold["outcome_distribution"],
            "avg_rounds": mc_cold["avg_rounds"],
            "avg_oil": mc_cold["avg_final_oil_price"],
            "nuclear": round(mc_cold["nuclear_breakout_rate"] * 100, 1),
        },
        "model_vs_reality": {
            "war_start": "2026-02-28",
            "analysis_date": "2026-04-05",
            "days_elapsed": 36,
            "model_got_right": [
                "Hormuz blockade (predicted 78% probability, happened Day 3)",
                "Mojtaba Khamenei succession dynamics",
                "Trump rhetoric escalation pattern (\"war almost over\" Day 14)",
                "No ceasefire in first month (model: 5-8% probability)",
                "IRGC principal-agent conflict with Mojtaba",
                "Mission Accomplished trap dynamics",
            ],
            "model_got_wrong": [
                "War duration (predicted avg 19 days, reality 36+ and counting)",
                "Oil price (predicted $136 avg, reality $105 with adaptation)",
                "Regional escalation scope (7 countries struck directly, not just proxies)",
            ],
            "recalibrations_applied": [
                "Oil: SPR +50%, OPEC x2, speculation decay faster, market adaptation factor",
                "Duration: raised termination thresholds (Iran harder to knock out)",
                "Regional: direct strikes on 7 countries (Bahrain, Jordan, Kuwait, Qatar, Saudi, UAE, Cyprus)",
                "Warm start from Day 36 real-world state",
            ],
        },
    }

    with open("day36_analysis.json", "w") as f:
        json.dump(output, f, ensure_ascii=False, indent=1)

    print("\n" + "=" * 60)
    print("RESULTS SAVED to day36_analysis.json")
    print("=" * 60)

    # Print summary comparison
    print("\n--- MODEL VS REALITY COMPARISON ---")
    print(f"Cold start (original):  avg {mc_cold['avg_rounds']} rounds, oil ${mc_cold['avg_final_oil_price']}")
    print(f"Day-36 warm start:      avg {mc_rev['avg_total_days']} total days, oil ${mc_rev['avg_final_oil_price']}")
    print(f"Nuclear breakout rate:  cold={mc_cold['nuclear_breakout_rate']*100:.1f}%  warm={mc_rev['nuclear_breakout_rate']*100:.1f}%")
    print()
    print("--- DAY 36 FORWARD PROJECTION ---")
    for k, v in mc_rev["outcome_distribution"].items():
        print(f"  {k}: {v}%")


if __name__ == "__main__":
    run_analysis()
