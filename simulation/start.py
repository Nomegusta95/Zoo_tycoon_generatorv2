import os
from data.data_loader import load_animals
from data.predefined_loader import load_predefined_projects
from simulation.simulator import run_simulation, export_simulation
from simulation.analysis import analyze_simulation

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

animals_path = os.path.join(BASE_DIR, "data", "Animals.xlsx")
predefined_path = os.path.join(BASE_DIR, "data", "Predefined projects.xlsx")

animals = load_animals(animals_path)
predefined = load_predefined_projects(predefined_path)

results = run_simulation(animals, predefined, runs=200)

output_path = os.path.join(BASE_DIR, "analysis", "simulation_results.xlsx")
export_simulation(results, path=output_path)

analyze_simulation(results, output_dir=os.path.join(BASE_DIR, "analysis"))