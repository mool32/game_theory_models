"""
Analyze what conditions produce wars of different durations:
3 weeks (blitz), 9 weeks (typical), 12 weeks, 15+ weeks (quagmire).
"""

import random
import json
from collections import defaultdict
from game_theory_conflict_model import (
    SimulationConfig, run_simulation,
)


def analyze_duration_factors(n=5000):
    """Run n simulations across varied parameters, bucket by duration."""

    # Parameter grid to sample from
    param_ranges = {
        "usa_discount": [0.70, 0.78, 0.83, 0.88, 0.92],
        "iran_discount": [0.85, 0.90, 0.93, 0.96],
        "iran_is_revolutionary": [False, True],
        "initial_oil_price": [75, 85, 100, 110],
        "enable_shocks": [True, False],
    }

    # Duration buckets
    buckets = {
        "ultra_short (1-3 wk)": lambda r: r <= 3,
        "short (4-6 wk)": lambda r: 4 <= r <= 6,
        "typical (7-9 wk)": lambda r: 7 <= r <= 9,
        "extended (10-12 wk)": lambda r: 10 <= r <= 12,
        "long (13-15 wk)": lambda r: 13 <= r <= 15,
        "quagmire (16+ wk)": lambda r: r >= 16,
    }

    bucket_data = {k: [] for k in buckets}

    for i in range(n):
        # Sample parameters
        ud = random.choice(param_ranges["usa_discount"])
        idr = random.choice(param_ranges["iran_discount"])
        rev = random.choice(param_ranges["iran_is_revolutionary"])
        oil = random.choice(param_ranges["initial_oil_price"])
        shocks = random.choice(param_ranges["enable_shocks"])

        cfg = SimulationConfig(
            seed=i,
            usa_discount=ud,
            iran_discount=idr,
            iran_is_revolutionary=rev,
            initial_oil_price=oil,
            enable_shocks=shocks,
            max_rounds=40,
        )

        result = run_simulation(cfg)

        record = {
            "seed": i,
            "rounds": result["rounds_played"],
            "outcome": result["outcome"],
            "final_date": result["final_date"],
            "oil_price": result["final_oil_price"],
            "hormuz_flow": result["hormuz_flow_pct"],
            "usa_inflation": result["usa_inflation"],
            "usa_gdp": result["usa_gdp_index"],
            "usa_recession_risk": result["usa_recession_risk"],
            "usa_war_cost": result["usa_war_cost_pct_gdp"],
            "oil_shock_weeks": result["oil_shock_weeks"],
            "spr_remaining": result["spr_remaining_mb"],
            "iran_military": result["final_iran_military"],
            "iran_casualties_k": result["total_iran_casualties_k"],
            "usa_casualties_k": result["total_usa_casualties_k"],
            "israel_casualties_k": result["total_israel_casualties_k"],
            "red_lines": result["red_lines_crossed"],
            "shocks": result["all_shocks"],
            # Input parameters
            "p_usa_discount": ud,
            "p_iran_discount": idr,
            "p_revolutionary": rev,
            "p_initial_oil": oil,
            "p_shocks": shocks,
        }

        for bname, bfn in buckets.items():
            if bfn(result["rounds_played"]):
                bucket_data[bname].append(record)
                break

    # --- Analysis ---
    print("=" * 90)
    print("WAR DURATION ANALYSIS: What makes wars short vs. long?")
    print(f"  (n={n} simulations, varied parameters)")
    print("=" * 90)

    for bname, records in bucket_data.items():
        if not records:
            print(f"\n{'='*70}")
            print(f"  {bname}: 0 cases (0.0%)")
            continue

        pct = len(records) / n * 100
        print(f"\n{'='*70}")
        print(f"  {bname}: {len(records)} cases ({pct:.1f}%)")
        print(f"{'='*70}")

        # Average conditions
        avg = lambda key: sum(r[key] for r in records) / len(records)
        count = lambda key, val: sum(1 for r in records if r[key] == val) / len(records) * 100

        # Outcomes
        outcomes = defaultdict(int)
        for r in records:
            outcomes[r["outcome"]] += 1
        print(f"\n  Outcomes:")
        for o, c in sorted(outcomes.items(), key=lambda x: -x[1]):
            print(f"    {o}: {c/len(records)*100:.1f}%")

        print(f"\n  Avg conditions at war's end:")
        print(f"    Oil price:        ${avg('oil_price'):.1f}")
        print(f"    Hormuz flow:      {avg('hormuz_flow'):.1f}%")
        print(f"    USA inflation:    {avg('usa_inflation'):.1f}%")
        print(f"    USA GDP index:    {avg('usa_gdp'):.1f}")
        print(f"    USA recession R:  {avg('usa_recession_risk'):.2f}")
        print(f"    USA war cost %GDP:{avg('usa_war_cost'):.2f}%")
        print(f"    Oil shock weeks:  {avg('oil_shock_weeks'):.1f}")
        print(f"    SPR remaining:    {avg('spr_remaining'):.1f}M bbl")
        print(f"    Iran military:    {avg('iran_military'):.1f}")
        print(f"    Casualties (K):   USA={avg('usa_casualties_k'):.2f}  "
              f"Israel={avg('israel_casualties_k'):.2f}  Iran={avg('iran_casualties_k'):.2f}")

        print(f"\n  Input parameter profile:")
        print(f"    USA discount (patience): {avg('p_usa_discount'):.2f}  "
              f"(low=impatient, high=patient)")
        print(f"    Iran discount (patience): {avg('p_iran_discount'):.2f}")
        print(f"    Revolutionary Iran:  {count('p_revolutionary', True):.0f}%")
        print(f"    Initial oil price:   ${avg('p_initial_oil'):.0f}")
        print(f"    Shocks enabled:      {count('p_shocks', True):.0f}%")

        # Red lines
        rl_counts = defaultdict(int)
        for r in records:
            for rl in r["red_lines"]:
                rl_counts[rl] += 1
        if rl_counts:
            print(f"\n  Red lines crossed (% of cases):")
            for rl, c in sorted(rl_counts.items(), key=lambda x: -x[1]):
                print(f"    {rl}: {c/len(records)*100:.0f}%")

        # Shocks
        sh_counts = defaultdict(int)
        for r in records:
            for sh in r["shocks"]:
                sh_counts[sh] += 1
        if sh_counts:
            print(f"\n  Shocks triggered (% of cases):")
            for sh, c in sorted(sh_counts.items(), key=lambda x: -x[1])[:5]:
                print(f"    {sh}: {c/len(records)*100:.0f}%")

        # Show 2 representative examples
        print(f"\n  Example trajectories:")
        examples = records[:2]
        for ex in examples:
            print(f"    Seed {ex['seed']}: {ex['rounds']}wk → {ex['outcome']} | "
                  f"Oil ${ex['oil_price']:.0f} | IRmil={ex['iran_military']:.0f} | "
                  f"USAcas={ex['usa_casualties_k']:.2f}K | "
                  f"d_usa={ex['p_usa_discount']:.2f} d_iran={ex['p_iran_discount']:.2f} "
                  f"rev={ex['p_revolutionary']}")

    # --- Duration histogram ---
    print(f"\n\n{'='*70}")
    print("DURATION HISTOGRAM (all simulations)")
    print(f"{'='*70}")
    dur_hist = defaultdict(int)
    for bname, records in bucket_data.items():
        for r in records:
            dur_hist[r["rounds"]] += 1
    for wk in sorted(dur_hist.keys()):
        bar = "#" * (dur_hist[wk] * 60 // n)
        print(f"  {wk:2d} wk: {dur_hist[wk]:4d} ({dur_hist[wk]/n*100:5.1f}%) {bar}")

    # --- What SPECIFICALLY causes 3-week wars? ---
    print(f"\n\n{'='*70}")
    print("DEEP DIVE: What causes ultra-short wars (≤3 weeks)?")
    print(f"{'='*70}")
    short = bucket_data.get("ultra_short (1-3 wk)", [])
    if short:
        for r in short[:5]:
            print(f"\n  Seed {r['seed']}:")
            print(f"    Config: d_usa={r['p_usa_discount']:.2f} d_iran={r['p_iran_discount']:.2f} "
                  f"rev={r['p_revolutionary']} oil=${r['p_initial_oil']} shocks={r['p_shocks']}")
            print(f"    Result: {r['rounds']}wk → {r['outcome']} | Oil ${r['oil_price']:.0f}")
            print(f"    Iran mil={r['iran_military']:.0f} | USA cas={r['usa_casualties_k']:.2f}K")
            print(f"    Red lines: {r['red_lines']}")
            print(f"    Shocks: {r['shocks']}")

    # --- What causes 15+ week wars? ---
    print(f"\n\n{'='*70}")
    print("DEEP DIVE: What causes long wars (13+ weeks)?")
    print(f"{'='*70}")
    long_wars = bucket_data.get("long (13-15 wk)", []) + bucket_data.get("quagmire (16+ wk)", [])
    if long_wars:
        for r in long_wars[:5]:
            print(f"\n  Seed {r['seed']}:")
            print(f"    Config: d_usa={r['p_usa_discount']:.2f} d_iran={r['p_iran_discount']:.2f} "
                  f"rev={r['p_revolutionary']} oil=${r['p_initial_oil']} shocks={r['p_shocks']}")
            print(f"    Result: {r['rounds']}wk → {r['outcome']} | Oil ${r['oil_price']:.0f}")
            print(f"    Econ: inflation={r['usa_inflation']:.1f}% GDP={r['usa_gdp']:.1f} "
                  f"recession_r={r['usa_recession_risk']:.2f} war_cost={r['usa_war_cost']:.2f}%GDP")
            print(f"    SPR={r['spr_remaining']:.0f}M bbl | oil_shock_wk={r['oil_shock_weeks']}")
            print(f"    Casualties: USA={r['usa_casualties_k']:.2f}K Iran={r['iran_casualties_k']:.2f}K")
            print(f"    Red lines: {r['red_lines']}")
    else:
        print("  No long wars found — model resolves too quickly.")
        print("  This itself is a finding: current parameters don't produce quagmires.")


if __name__ == "__main__":
    analyze_duration_factors(5000)
