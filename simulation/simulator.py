import random

import pandas as pd
from collections import defaultdict, Counter

from core.engine import generate_full_game


def run_simulation(animals, predefined, runs=100):

    theme_counter = Counter()
    animal_counter = Counter()
    first_rewards = []
    second_rewards = []

    animal_theme = defaultdict(lambda: defaultdict(int))
    sizes = []

    total_projects = 0

    for _ in range(runs):

        game, game_animals, lookup = generate_full_game(
            animals,
            required=[],
            predefined=predefined
        )

        for project in game:
            total_projects += 1

            sizes.append(len(project.get("animals", [])))

            # --- THEME ---
            theme = project.get("theme") or "none"
            theme_counter[theme] += 1

            # --- ANIMALS ---
            for entry in project.get("animals", []):
                parts = entry.split(" OR ")

                p = random.choice(parts)  # pick ONE

                tokens = p.split()
                if tokens and tokens[-1].isdigit():
                    tokens = tokens[:-1]

                name = " ".join(tokens)

                animal_counter[name] += 1
                animal_theme[name][theme] += 1

            # --- REWARDS ---
            reward = project.get("reward")
            if reward:
                first_rewards.append(reward["first"])
                second_rewards.append(reward["second"])

    return {
        "total_projects": total_projects,
        "themes": theme_counter,
        "animals": animal_counter,
        "first_rewards": first_rewards,
        "second_rewards": second_rewards,
        "animal_theme": animal_theme,
        "sizes": sizes,
    }


def export_simulation(results, path="simulation_results.xlsx"):

    # --- THEMES ---
    df_themes = pd.DataFrame([
        {"theme": k, "count": v}
        for k, v in results["themes"].items()
    ])

    # --- ANIMALS ---
    df_animals = pd.DataFrame([
        {"animal": k, "count": v}
        for k, v in results["animals"].items()
    ])

    # --- REWARDS ---
    df_rewards = pd.DataFrame({
        "first_reward": results["first_rewards"],
        "second_reward": results["second_rewards"]
    })

    # --- SUMMARY ---
    df_summary = pd.DataFrame([{
        "total_projects": results["total_projects"],
        "avg_first_reward": sum(results["first_rewards"]) / len(results["first_rewards"]) if results["first_rewards"] else 0,
        "avg_second_reward": sum(results["second_rewards"]) / len(results["second_rewards"]) if results["second_rewards"] else 0,
    }])

    # --- WRITE EXCEL ---
    with pd.ExcelWriter(path) as writer:
        df_summary.to_excel(writer, sheet_name="summary", index=False)
        df_themes.to_excel(writer, sheet_name="themes", index=False)
        df_animals.to_excel(writer, sheet_name="animals", index=False)
        df_rewards.to_excel(writer, sheet_name="rewards", index=False)

    print(f"Simulation exported to {path}")