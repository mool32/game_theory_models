# Game Theory Conflict Model

Game-theoretic analysis of coalition vs Iran conflict dynamics with interactive visualization.

## Structure

- `game_theory_conflict_model.py` — Core model: multi-level game with economic subsystem, temporal framework, phase transitions, and hysteresis
- `calibrate_patience.py` — Historical calibration of discount factors using Gallup/Mueller empirical data
- `analyze_war_duration.py` — War duration analysis
- `analyze_distributions.py` — Outcome distribution analysis toolkit
- `generate_viz_data.py` — Generate visualization data from model runs
- `viz_data.json` — Pre-computed visualization data
- `index.html` — Interactive visualization dashboard

## Visualization

Live demo: https://mool32.github.io/game_theory_models/

## Usage

```bash
pip install numpy scipy
python game_theory_conflict_model.py
```

To regenerate visualization data:
```bash
python generate_viz_data.py
```
