#!/usr/bin/env python3
"""
Analytical toolkit for the game theory conflict model v5.1.

Provides tools to understand outcome distributions, find tipping points,
run sensitivity sweeps, and perform conditional analysis.

Usage:
    python analyze_distributions.py                    # full analysis
    python analyze_distributions.py sensitivity        # sensitivity sweeps only
    python analyze_distributions.py conditional         # conditional analysis only
    python analyze_distributions.py tipping            # tipping point search
    python analyze_distributions.py trajectories       # trajectory clustering
"""

import sys
import json
import random
import math
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

from game_theory_conflict_model import (
    SimulationConfig, run_simulation, monte_carlo,
)


# ============================================================
# 1. RAW SIMULATION COLLECTOR
# ============================================================

def collect_simulations(n: int, overrides: Optional[dict] = None) -> list[dict]:
    """Run n simulations and return full result dicts (without history for memory)."""
    base = SimulationConfig()
    if overrides:
        for k, v in overrides.items():
            if hasattr(base, k):
                setattr(base, k, v)

    results = []
    for i in range(n):
        cfg_dict = {f.name: getattr(base, f.name)
                    for f in base.__dataclass_fields__.values()}
        cfg_dict["seed"] = i
        cfg = SimulationConfig(**cfg_dict)
        r = run_simulation(cfg)
        # Drop history to save memory
        r.pop("history", None)
        results.append(r)
    return results


# ============================================================
# 2. DISTRIBUTION STATISTICS
# ============================================================

def percentile(values: list[float], p: float) -> float:
    """Calculate p-th percentile (0-100)."""
    s = sorted(values)
    k = (len(s) - 1) * p / 100
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return s[int(k)]
    return s[f] * (c - k) + s[c] * (k - f)


def distribution_stats(values: list[float]) -> dict:
    """Full distribution statistics for a list of values."""
    n = len(values)
    if n == 0:
        return {}
    s = sorted(values)
    mean = sum(s) / n
    variance = sum((x - mean) ** 2 for x in s) / n
    std = math.sqrt(variance)
    return {
        "mean": round(mean, 2),
        "median": round(s[n // 2], 2),
        "std": round(std, 2),
        "min": round(s[0], 2),
        "max": round(s[-1], 2),
        "p5": round(percentile(s, 5), 2),
        "p25": round(percentile(s, 25), 2),
        "p75": round(percentile(s, 75), 2),
        "p95": round(percentile(s, 95), 2),
    }


def print_distribution(name: str, values: list[float], unit: str = ""):
    """Pretty-print distribution statistics with histogram."""
    stats = distribution_stats(values)
    if not stats:
        print(f"  {name}: no data")
        return

    print(f"\n  {name}:")
    print(f"    mean={stats['mean']}{unit}  median={stats['median']}{unit}  "
          f"std={stats['std']}{unit}")
    print(f"    range=[{stats['min']}, {stats['max']}]  "
          f"90% CI=[{stats['p5']}, {stats['p95']}]")

    # ASCII histogram
    n_bins = 20
    lo, hi = stats['min'], stats['max']
    if hi == lo:
        return
    bin_width = (hi - lo) / n_bins
    bins = [0] * n_bins
    for v in values:
        idx = min(int((v - lo) / bin_width), n_bins - 1)
        bins[idx] += 1
    max_count = max(bins)
    if max_count == 0:
        return
    bar_width = 40
    print(f"    {'':>8s} ", end="")
    for i in range(n_bins):
        h = int(bins[i] / max_count * 8)
        chars = " ▁▂▃▄▅▆▇█"
        print(chars[h], end="")
    print()
    print(f"    {lo:>8.1f}{' ' * (n_bins - len(f'{hi:.1f}'))}{hi:.1f}")


# ============================================================
# 3. SENSITIVITY ANALYSIS
# ============================================================

def sensitivity_sweep(
    param_name: str,
    values: list,
    n_sims: int = 200,
    base_overrides: Optional[dict] = None,
) -> dict:
    """Sweep a single parameter across values, track outcome distributions.

    Returns dict mapping param value → outcome distribution + key metrics.
    """
    results = {}
    for val in values:
        overrides = dict(base_overrides or {})
        overrides[param_name] = val
        mc = monte_carlo(n_sims, overrides)
        results[val] = {
            "outcomes": mc["outcome_distribution"],
            "avg_rounds": mc["avg_rounds"],
            "avg_oil": mc["avg_final_oil_price"],
            "nuclear_breakout_%": round(mc["nuclear_breakout_rate"] * 100, 1),
            "avg_iran_cas_k": mc["avg_iran_casualties_k"],
            "avg_usa_cas_k": mc["avg_usa_casualties_k"],
            "economics": mc["economics"],
        }
    return results


def print_sensitivity(param_name: str, sweep_results: dict):
    """Pretty-print sensitivity sweep results as a table."""
    print(f"\n{'=' * 80}")
    print(f"  SENSITIVITY: {param_name}")
    print(f"{'=' * 80}")

    # Header
    outcomes_all = set()
    for v in sweep_results.values():
        outcomes_all.update(v["outcomes"].keys())
    outcomes_sorted = sorted(outcomes_all)

    header = f"  {'Value':>10s} "
    for o in outcomes_sorted:
        short = o.replace("coalition_", "c_").replace("iran_", "i_")
        header += f" {short:>12s}"
    header += f" {'Rounds':>7s} {'Oil$':>6s} {'Nuke%':>6s} {'IRcas':>6s}"
    print(header)
    print("  " + "-" * (len(header) - 2))

    for param_val, data in sorted(sweep_results.items()):
        line = f"  {str(param_val):>10s} "
        for o in outcomes_sorted:
            pct = data["outcomes"].get(o, 0)
            line += f" {pct:>11.1f}%"
        line += f" {data['avg_rounds']:>7.1f}"
        line += f" {data['avg_oil']:>6.0f}"
        line += f" {data['nuclear_breakout_%']:>5.1f}%"
        line += f" {data['avg_iran_cas_k']:>6.2f}"
        print(line)


def run_sensitivity_analysis(n_sims: int = 200):
    """Run sensitivity sweeps on key parameters."""
    print("\n" + "=" * 80)
    print("  SENSITIVITY ANALYSIS")
    print("  Sweeping key parameters to find what drives outcomes")
    print("=" * 80)

    # 1. USA discount factor (patience)
    sweep = sensitivity_sweep(
        "usa_discount",
        [0.70, 0.75, 0.78, 0.82, 0.85, 0.88, 0.93],
        n_sims,
        {"iran_is_revolutionary": True},
    )
    print_sensitivity("usa_discount (Trump patience)", sweep)

    # 2. Iran discount factor
    sweep = sensitivity_sweep(
        "iran_discount",
        [0.85, 0.90, 0.93, 0.95, 0.97, 0.99],
        n_sims,
        {"iran_is_revolutionary": True},
    )
    print_sensitivity("iran_discount (Iran patience)", sweep)

    # 3. Starting oil price
    sweep = sensitivity_sweep(
        "initial_oil_price",
        [75, 85, 95, 105, 115, 130],
        n_sims,
        {"iran_is_revolutionary": True},
    )
    print_sensitivity("initial_oil_price", sweep)

    # 4. Nuclear facilities surviving (what if strikes already happened)
    sweep = sensitivity_sweep(
        "iran_nuclear_facilities_pct",
        [100, 80, 60, 40, 20],
        n_sims,
        {"iran_is_revolutionary": True},
    )
    print_sensitivity("iran_nuclear_facilities_pct (strike damage)", sweep)

    # 5. Coalition belief about Iran type
    sweep = sensitivity_sweep(
        "coalition_belief_iran_rational",
        [0.2, 0.35, 0.5, 0.65, 0.8],
        n_sims,
        {"iran_is_revolutionary": True},
    )
    print_sensitivity("coalition_belief_iran_rational (intel accuracy)", sweep)


# ============================================================
# 4. CONDITIONAL ANALYSIS
# ============================================================

def conditional_analysis(n_sims: int = 500):
    """Analyze outcomes conditional on specific events occurring."""
    print("\n" + "=" * 80)
    print("  CONDITIONAL ANALYSIS")
    print("  'Given X happened, what's the outcome distribution?'")
    print("=" * 80)

    # Collect raw results
    print("\n  Collecting simulations...")
    results = collect_simulations(n_sims, {"iran_is_revolutionary": True})

    # Partition by events
    conditions = {
        "nuclear_breakout": lambda r: any(
            "NUCLEAR_BREAKOUT" in str(e) for e in r.get("v4_events", [])),
        "hormuz_blockaded": lambda r: r.get("hormuz_flow_pct", 100) < 80,
        "usa_recession": lambda r: r.get("usa_recession_risk", 0) > 0.5,
        "trump_trapped": lambda r: r.get("mission_accomplished_trap", False),
        "mojtaba_consolidated": lambda r: r.get("iran_leader_consolidated", False),
        "hezbollah_collapsed": lambda r: (
            r.get("final_hezbollah_military", 100) < 15),
        "war_powers_activated": lambda r: r.get("war_powers_active", False),
        "long_war_15plus": lambda r: r.get("rounds_played", 0) >= 15,
        "short_war_under_8": lambda r: r.get("rounds_played", 0) < 8,
        "oil_above_180": lambda r: r.get("final_oil_price", 0) > 180,
        "china_mediates": lambda r: r.get("china_mediation_interest", 0) > 0.5,
    }

    for cond_name, cond_fn in conditions.items():
        matching = [r for r in results if cond_fn(r)]
        not_matching = [r for r in results if not cond_fn(r)]

        if len(matching) < 3:
            print(f"\n  {cond_name}: too few cases ({len(matching)}/{len(results)})")
            continue

        # Outcome distribution
        outcomes_yes = defaultdict(int)
        outcomes_no = defaultdict(int)
        for r in matching:
            outcomes_yes[r["outcome"]] += 1
        for r in not_matching:
            outcomes_no[r["outcome"]] += 1

        print(f"\n  {cond_name}: {len(matching)}/{len(results)} sims "
              f"({len(matching)/len(results)*100:.1f}%)")
        print(f"  {'Outcome':<30s} {'Given YES':>10s} {'Given NO':>10s} {'Delta':>8s}")
        print(f"  {'-'*62}")

        all_outcomes = sorted(set(list(outcomes_yes.keys()) + list(outcomes_no.keys())))
        for o in all_outcomes:
            pct_yes = outcomes_yes.get(o, 0) / len(matching) * 100
            pct_no = outcomes_no.get(o, 0) / max(1, len(not_matching)) * 100
            delta = pct_yes - pct_no
            sign = "+" if delta > 0 else ""
            print(f"  {o:<30s} {pct_yes:>9.1f}% {pct_no:>9.1f}% {sign}{delta:>6.1f}%")

        # Key metrics conditional comparison
        metrics = [
            ("avg_rounds", "rounds_played"),
            ("avg_oil", "final_oil_price"),
            ("avg_iran_mil", "final_iran_military"),
            ("avg_usa_cas_k", "total_usa_casualties_k"),
        ]
        metrics_line = "    "
        for label, key in metrics:
            vals_yes = [r.get(key, 0) for r in matching]
            vals_no = [r.get(key, 0) for r in not_matching]
            avg_yes = sum(vals_yes) / len(vals_yes) if vals_yes else 0
            avg_no = sum(vals_no) / len(vals_no) if vals_no else 0
            metrics_line += f"{label}={avg_yes:.1f} (vs {avg_no:.1f})  "
        print(metrics_line)


# ============================================================
# 5. TIPPING POINT FINDER
# ============================================================

def find_tipping_point(
    param_name: str,
    low: float,
    high: float,
    target_outcome: str,
    target_pct: float = 50.0,
    n_sims: int = 200,
    base_overrides: Optional[dict] = None,
    tolerance: float = 2.0,
    max_iterations: int = 8,
) -> dict:
    """Binary search for parameter value where target_outcome crosses target_pct.

    Returns the parameter value where the outcome probability is closest
    to target_pct (e.g., "at what usa_discount does Iran strategic victory
    exceed 50%?").
    """
    history = []

    for iteration in range(max_iterations):
        mid = (low + high) / 2
        overrides = dict(base_overrides or {})
        overrides[param_name] = mid
        mc = monte_carlo(n_sims, overrides)
        actual_pct = mc["outcome_distribution"].get(target_outcome, 0)

        history.append({
            "iteration": iteration,
            "value": round(mid, 4),
            "outcome_pct": actual_pct,
        })

        if abs(actual_pct - target_pct) < tolerance:
            break

        # Determine which direction to search
        # Higher param value → need to check if outcome increases or decreases
        if actual_pct < target_pct:
            # Need more of target outcome — depends on param direction
            # For usa_discount: lower patience → more iran_strategic_victory
            # We can't know the direction, so use test-based approach
            low = mid
        else:
            high = mid

    return {
        "param": param_name,
        "target_outcome": target_outcome,
        "target_pct": target_pct,
        "found_value": round(mid, 4),
        "found_pct": actual_pct,
        "history": history,
    }


def run_tipping_points(n_sims: int = 200):
    """Find critical tipping points for major parameters."""
    print("\n" + "=" * 80)
    print("  TIPPING POINT ANALYSIS")
    print("  Finding parameter values where outcomes flip")
    print("=" * 80)

    searches = [
        {
            "param": "usa_discount",
            "low": 0.65, "high": 0.95,
            "target": "iran_strategic_victory",
            "target_pct": 40.0,
            "base": {"iran_is_revolutionary": True},
            "desc": "At what USA patience does Iran strategic victory reach 40%?",
        },
        {
            "param": "iran_discount",
            "low": 0.80, "high": 0.99,
            "target": "coalition_limited_victory",
            "target_pct": 85.0,
            "base": {"iran_is_revolutionary": True},
            "desc": "At what Iran patience does coalition limited victory reach 85%?",
        },
        {
            "param": "initial_oil_price",
            "low": 60, "high": 140,
            "target": "iran_strategic_victory",
            "target_pct": 35.0,
            "base": {"iran_is_revolutionary": True},
            "desc": "At what starting oil price does Iran strategic victory reach 35%?",
        },
    ]

    for s in searches:
        print(f"\n  Q: {s['desc']}")
        result = find_tipping_point(
            s["param"], s["low"], s["high"],
            s["target"], s["target_pct"],
            n_sims, s["base"],
        )
        print(f"  A: {s['param']} = {result['found_value']} "
              f"→ {s['target']} = {result['found_pct']}%")
        print(f"     Search history: ", end="")
        for h in result["history"]:
            print(f"[{h['value']:.3f}→{h['outcome_pct']:.1f}%] ", end="")
        print()


# ============================================================
# 6. TRAJECTORY ANALYSIS
# ============================================================

def trajectory_analysis(n_sims: int = 200):
    """Analyze full simulation trajectories to find archetypes."""
    print("\n" + "=" * 80)
    print("  TRAJECTORY ANALYSIS")
    print("  Classifying war paths into archetypes")
    print("=" * 80)

    # Need full history for this
    base = SimulationConfig(iran_is_revolutionary=True)

    # Classify trajectories
    archetypes = defaultdict(list)

    for i in range(n_sims):
        cfg_dict = {f.name: getattr(base, f.name)
                    for f in base.__dataclass_fields__.values()}
        cfg_dict["seed"] = i
        cfg = SimulationConfig(**cfg_dict)
        r = run_simulation(cfg)

        # Classify based on pattern
        outcome = r["outcome"]
        rounds = r["rounds_played"]
        nuclear = any("NUCLEAR_BREAKOUT" in str(e) for e in r.get("v4_events", []))
        hormuz = r.get("hormuz_flow_pct", 100) < 80
        max_oil = max(h.oil_price for h in r["history"]) if r["history"] else 85
        trapped = r.get("mission_accomplished_trap", False)

        # Determine archetype
        if outcome == "coalition_decisive_victory" and rounds < 8:
            archetype = "SWIFT_KNOCKOUT"
        elif outcome == "coalition_limited_victory" and not nuclear and max_oil < 150:
            archetype = "MANAGED_DEGRADATION"
        elif outcome == "coalition_limited_victory" and max_oil > 150:
            archetype = "PYRRHIC_VICTORY"
        elif outcome == "coalition_limited_victory" and nuclear:
            archetype = "NUCLEAR_SHADOW_WIN"
        elif outcome == "iran_strategic_victory" and hormuz:
            archetype = "HORMUZ_EXHAUSTION"
        elif outcome == "iran_strategic_victory" and trapped:
            archetype = "TRUMP_TRAP"
        elif outcome == "iran_strategic_victory":
            archetype = "ATTRITION_VICTORY"
        elif outcome == "negotiated_settlement":
            archetype = "DIPLOMATIC_EXIT"
        elif outcome == "frozen_conflict":
            archetype = "FROZEN"
        else:
            archetype = "OTHER"

        archetypes[archetype].append({
            "seed": i,
            "outcome": outcome,
            "rounds": rounds,
            "max_oil": max_oil,
            "final_oil": r["final_oil_price"],
            "nuclear": nuclear,
            "hormuz_blocked": hormuz,
            "iran_mil_final": r["final_iran_military"],
            "usa_cas_k": r["total_usa_casualties_k"],
            "iran_cas_k": r["total_iran_casualties_k"],
        })

    # Print archetypes
    total = sum(len(v) for v in archetypes.values())
    for archetype, sims in sorted(archetypes.items(), key=lambda x: -len(x[1])):
        pct = len(sims) / total * 100
        avg_rounds = sum(s["rounds"] for s in sims) / len(sims)
        avg_oil = sum(s["max_oil"] for s in sims) / len(sims)
        avg_iran_cas = sum(s["iran_cas_k"] for s in sims) / len(sims)
        avg_usa_cas = sum(s["usa_cas_k"] for s in sims) / len(sims)
        nuke_pct = sum(1 for s in sims if s["nuclear"]) / len(sims) * 100

        print(f"\n  {archetype} ({len(sims)} sims, {pct:.1f}%)")
        print(f"    avg_rounds={avg_rounds:.1f}  max_oil=${avg_oil:.0f}  "
              f"nuke={nuke_pct:.0f}%")
        print(f"    iran_cas={avg_iran_cas:.2f}K  usa_cas={avg_usa_cas:.2f}K")

        # Show example seeds
        examples = sims[:3]
        for ex in examples:
            print(f"    seed={ex['seed']}: {ex['rounds']}r, "
                  f"oil=${ex['final_oil']:.0f}, "
                  f"iran_mil={ex['iran_mil_final']:.0f}"
                  + (" [NUCLEAR]" if ex["nuclear"] else ""))


# ============================================================
# 7. FULL DISTRIBUTION REPORT
# ============================================================

def full_distribution_report(n_sims: int = 500):
    """Generate comprehensive distribution report for all key variables."""
    print("\n" + "=" * 80)
    print(f"  FULL DISTRIBUTION REPORT (n={n_sims}, revolutionary Iran)")
    print("=" * 80)

    results = collect_simulations(n_sims, {"iran_is_revolutionary": True})

    # Outcome distribution
    outcomes = defaultdict(int)
    for r in results:
        outcomes[r["outcome"]] += 1

    print("\n  OUTCOME DISTRIBUTION:")
    for o, count in sorted(outcomes.items(), key=lambda x: -x[1]):
        pct = count / len(results) * 100
        bar = "█" * int(pct / 2)
        print(f"    {o:<30s} {pct:>5.1f}% {bar}")

    # Key variable distributions
    print_distribution("War duration (rounds)",
                       [r["rounds_played"] for r in results], " rounds")
    print_distribution("Final oil price",
                       [r["final_oil_price"] for r in results], "$")
    print_distribution("Iran final military",
                       [r["final_iran_military"] for r in results])
    print_distribution("Iran casualties (K)",
                       [r["total_iran_casualties_k"] for r in results], "K")
    print_distribution("USA casualties (K)",
                       [r["total_usa_casualties_k"] for r in results], "K")
    print_distribution("Israel casualties (K)",
                       [r["total_israel_casualties_k"] for r in results], "K")
    print_distribution("USA inflation",
                       [r["usa_inflation"] for r in results], "%")
    print_distribution("USA GDP index",
                       [r["usa_gdp_index"] for r in results])
    print_distribution("USA recession risk",
                       [r["usa_recession_risk"] for r in results])
    print_distribution("SPR remaining (M bbl)",
                       [r["spr_remaining_mb"] for r in results], "M")
    print_distribution("Nuclear threat level",
                       [r.get("nuclear_threat_level", 0) for r in results])
    print_distribution("Hezbollah coherence",
                       [r.get("hez_coherence", 0.6) for r in results])
    print_distribution("China mediation interest",
                       [r.get("china_mediation_interest", 0) for r in results])
    print_distribution("Russia oil windfall ($B)",
                       [r.get("russia_oil_windfall_b", 0) for r in results], "B")

    # Correlation analysis
    print("\n\n  KEY CORRELATIONS (what drives what):")
    pairs = [
        ("rounds_played", "final_oil_price", "Duration → Oil"),
        ("rounds_played", "total_usa_casualties_k", "Duration → USA casualties"),
        ("final_oil_price", "usa_recession_risk", "Oil → Recession risk"),
        ("total_iran_casualties_k", "final_iran_military", "Iran cas → Iran mil"),
    ]
    for key_a, key_b, label in pairs:
        vals_a = [r.get(key_a, 0) for r in results]
        vals_b = [r.get(key_b, 0) for r in results]
        corr = _pearson(vals_a, vals_b)
        strength = "strong" if abs(corr) > 0.7 else "moderate" if abs(corr) > 0.4 else "weak"
        print(f"    {label:<35s} r={corr:+.3f} ({strength})")


def _pearson(x: list[float], y: list[float]) -> float:
    """Pearson correlation coefficient."""
    n = len(x)
    if n < 2:
        return 0.0
    mx = sum(x) / n
    my = sum(y) / n
    sx = math.sqrt(sum((xi - mx)**2 for xi in x) / n)
    sy = math.sqrt(sum((yi - my)**2 for yi in y) / n)
    if sx == 0 or sy == 0:
        return 0.0
    cov = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y)) / n
    return round(cov / (sx * sy), 4)


# ============================================================
# 8. WHAT-IF COMPARATOR
# ============================================================

def what_if_compare(n_sims: int = 300):
    """Compare specific what-if scenarios side by side."""
    print("\n" + "=" * 80)
    print("  WHAT-IF COMPARISON")
    print("  How do key assumptions change the war?")
    print("=" * 80)

    scenarios = {
        "Базовый (рев. Иран)": {"iran_is_revolutionary": True},
        "Рац. Иран": {"iran_is_revolutionary": False},
        "Трамп нетерпеливый (δ=0.75)": {
            "iran_is_revolutionary": True, "usa_discount": 0.75},
        "Трамп как Буш (δ=0.90)": {
            "iran_is_revolutionary": True, "usa_discount": 0.90},
        "Нефть уже $110": {
            "iran_is_revolutionary": True, "initial_oil_price": 110},
        "Ядерн. объекты на 50%": {
            "iran_is_revolutionary": True, "iran_nuclear_facilities_pct": 50},
        "Без шоков": {
            "iran_is_revolutionary": True, "enable_shocks": False},
        "Без тумана войны": {
            "iran_is_revolutionary": True, "enable_fog_of_war": False},
    }

    all_results = {}
    for name, overrides in scenarios.items():
        print(f"  Running: {name}...", flush=True)
        all_results[name] = monte_carlo(n_sims, overrides)

    # Print comparison table
    print(f"\n  {'Сценарий':<30s} {'Coalition%':>10s} {'Iran%':>8s} "
          f"{'Rounds':>7s} {'Oil$':>6s} {'Nuke%':>6s} {'USAcas':>7s}")
    print(f"  {'-'*76}")

    for name, mc in all_results.items():
        coalition = sum(v for k, v in mc["outcome_distribution"].items()
                       if "coalition" in k)
        iran = mc["outcome_distribution"].get("iran_strategic_victory", 0)
        print(f"  {name:<30s} {coalition:>9.1f}% {iran:>7.1f}% "
              f"{mc['avg_rounds']:>7.1f} {mc['avg_final_oil_price']:>5.0f}$ "
              f"{mc['nuclear_breakout_rate']*100:>5.1f}% "
              f"{mc['avg_usa_casualties_k']:>6.2f}K")


# ============================================================
# MAIN
# ============================================================

def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"

    if mode in ("all", "distributions", "dist"):
        full_distribution_report(500)

    if mode in ("all", "sensitivity", "sens"):
        run_sensitivity_analysis(200)

    if mode in ("all", "conditional", "cond"):
        conditional_analysis(500)

    if mode in ("all", "tipping", "tip"):
        run_tipping_points(200)

    if mode in ("all", "trajectories", "traj"):
        trajectory_analysis(300)

    if mode in ("all", "whatif", "compare"):
        what_if_compare(300)


if __name__ == "__main__":
    main()
