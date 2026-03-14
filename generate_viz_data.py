#!/usr/bin/env python3
"""Generate pre-computed data for the interactive visualization."""

import json
import sys
from collections import defaultdict

from game_theory_conflict_model import (
    SimulationConfig, run_simulation, monte_carlo,
)


def generate_viz_data():
    print("Generating visualization data...", flush=True)

    data = {}

    # 1. Single detailed simulation for timeline
    print("  [1/5] Single simulation timeline...", flush=True)
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
    print("  [2/5] USA patience sensitivity...", flush=True)
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
    print("  [3/5] Oil price sensitivity...", flush=True)
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
    print("  [4/5] Trajectory archetypes...", flush=True)
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
            arch = "Быстрый нокаут"
        elif outcome == "coalition_limited_victory" and not nuclear and max_oil < 150:
            arch = "Управляемая деградация"
        elif outcome == "coalition_limited_victory" and max_oil >= 150:
            arch = "Пиррова победа"
        elif outcome == "coalition_limited_victory" and nuclear:
            arch = "Ядерная тень"
        elif outcome == "iran_strategic_victory" and hormuz:
            arch = "Ормузское истощение"
        elif outcome == "iran_strategic_victory" and rounds < 5:
            arch = "Быстрый отход США"
        elif outcome == "iran_strategic_victory":
            arch = "Война на истощение"
        elif outcome == "negotiated_settlement":
            arch = "Дипломатический выход"
        elif outcome == "frozen_conflict":
            arch = "Замороженный конфликт"
        else:
            arch = "Прочее"

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

    # 5. What-if scenarios
    print("  [5/5] What-if scenarios...", flush=True)
    scenarios = {
        "Базовый сценарий": {"iran_is_revolutionary": True},
        "Рациональный Иран": {"iran_is_revolutionary": False},
        "Трамп нетерпелив": {"iran_is_revolutionary": True, "usa_discount": 0.75},
        "Трамп как Буш": {"iran_is_revolutionary": True, "usa_discount": 0.90},
        "Нефть уже $110": {"iran_is_revolutionary": True, "initial_oil_price": 110},
        "Ядерные объекты разбиты на 50%": {
            "iran_is_revolutionary": True, "iran_nuclear_facilities_pct": 50},
        "Без случайных шоков": {"iran_is_revolutionary": True, "enable_shocks": False},
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

    # Write output
    with open("viz_data.json", "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)

    print("Done! Written to viz_data.json", flush=True)


if __name__ == "__main__":
    generate_viz_data()
