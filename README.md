# Zoo Tycoon Generator v2

## Structure

- `main.py` — entry point (launches the CustomTkinter GUI)
- `core/` — generation engine: `engine.py`, `generator.py`, `project_generator.py`, `predefined_projects.py`, `project_naming.py`, `project_rules.py`, `best_project.py`, `utils.py`
- `scoring/` — cost/difficulty/reward logic: `animal_cost.py`, `project_cost.py`, `project_scoring.py`, `project_rewards.py`
- `data/` — data loading + source spreadsheets: `data_loader.py`, `predefined_loader.py`, `Animals.xlsx`, `Predefined projects.xlsx`
- `gui/` — GUI app: `app.py`
- `simulation/` — simulation/analysis scripts: `simulator.py`, `analysis.py`, `start.py`
- `analysis/` — generated analysis output (`animal_usage.xlsx`, `theme_usage.xlsx`, `animal_theme_heatmap.xlsx`, `simulation_results.xlsx`)
- `legacy/` — pre-refactor scripts kept for reference only, not imported by anything active (see below)
- `dist/` / `build/` — PyInstaller build output (gitignored, regenerate via PyInstaller, don't edit by hand)

## Legacy files

These predate the `core/`/`scoring/`/`data/` split and are no longer imported by `main.py` or any active module. They've been archived to `legacy/` rather than deleted, in case old logic is worth referencing:

- `gui_NEw.py` — superseded by `gui/app.py`
- `unlock_requirement_debugger.py` — only used by `gui_NEw.py`
- `analyze_animals.py` — superseded by `scoring/animal_cost.py`
- `difficulty.py` — superseded by `scoring/project_scoring.py`
- `test.py`, `debug.py`, `vezba.py` — ad-hoc scratch scripts
- `projects.py` — empty file

## Pending manual cleanup

Some of this cleanup requires deleting/moving files, which wasn't possible via the tools available when this pass was done. If you still see these, run:

```
mkdir legacy
move gui_NEw.py legacy\
move unlock_requirement_debugger.py legacy\
move analyze_animals.py legacy\
move difficulty.py legacy\
move test.py legacy\
move debug.py legacy\
move vezba.py legacy\
del projects.py
move simulation_results.xlsx analysis\
rmdir /s /q __pycache__
del "~$Animals.xlsx"
del "~$Zivotinje.xlsx"
```

(PowerShell equivalents: `Move-Item`, `Remove-Item -Recurse -Force`.)
