import os
from collections import defaultdict, Counter

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns


def analyze_simulation(results, output_dir):

    os.makedirs(output_dir, exist_ok=True)

    # -------------------------
    # BASIC DATA
    # -------------------------
    first_rewards = results["first_rewards"]
    second_rewards = results["second_rewards"]
    animals = results["animals"]
    themes = results["themes"]

    # -------------------------
    # 1. REWARD DISTRIBUTION
    # -------------------------
    plt.figure()
    plt.hist(first_rewards, bins=10)
    plt.title("First Reward Distribution")
    plt.xlabel("Reward")
    plt.ylabel("Frequency")
    plt.savefig(os.path.join(output_dir, "first_reward_hist.png"))
    plt.close()

    plt.figure()
    plt.hist(second_rewards, bins=10)
    plt.title("Second Reward Distribution")
    plt.xlabel("Reward")
    plt.ylabel("Frequency")
    plt.savefig(os.path.join(output_dir, "second_reward_hist.png"))
    plt.close()

    # -------------------------
    # 2. TOP ANIMALS
    # -------------------------
    df_animals = pd.DataFrame(
        list(animals.items()),
        columns=["animal", "count"]
    ).sort_values("count", ascending=False)

    df_animals.to_excel(os.path.join(output_dir, "animal_usage.xlsx"), index=False)

    plt.figure(figsize=(10, 5))
    df_animals.head(15).plot(kind="bar", x="animal", y="count")
    plt.title("Top 15 Most Used Animals")
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "top_animals.png"))
    plt.close()

    # -------------------------
    # 3. THEMES
    # -------------------------
    df_themes = pd.DataFrame(
        list(themes.items()),
        columns=["theme", "count"]
    ).sort_values("count", ascending=False)

    df_themes.to_excel(os.path.join(output_dir, "theme_usage.xlsx"), index=False)

    plt.figure()
    df_themes.plot(kind="bar", x="theme", y="count")
    plt.title("Theme Distribution")
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "themes.png"))
    plt.close()

    # -------------------------
    # 4. HEATMAP (Animal x Theme)
    # -------------------------
    animal_theme = results.get("animal_theme")

    if animal_theme:
        df_heat = pd.DataFrame(animal_theme).fillna(0)

        plt.figure(figsize=(12, 8))
        sns.heatmap(df_heat, cmap="viridis")
        plt.title("Animal vs Theme Heatmap")
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, "animal_theme_heatmap.png"))
        plt.close()

        df_heat.to_excel(os.path.join(output_dir, "animal_theme_heatmap.xlsx"))

    # -------------------------
    # 5. SIZE VS REWARD
    # -------------------------
    sizes = results.get("sizes", [])
    if sizes:
        plt.figure()
        plt.scatter(sizes, first_rewards)
        plt.xlabel("Project Size")
        plt.ylabel("First Reward")
        plt.title("Reward vs Project Size")
        plt.savefig(os.path.join(output_dir, "reward_vs_size.png"))
        plt.close()

    # -------------------------
    # 6. SUMMARY REPORT
    # -------------------------
    print("\n--- SIMULATION REPORT ---")

    print("Total projects:", results["total_projects"])

    if first_rewards:
        print("Avg first reward:", round(sum(first_rewards) / len(first_rewards), 2))

    if second_rewards:
        print("Avg second reward:", round(sum(second_rewards) / len(second_rewards), 2))

    print("\nTop 5 animals:")
    for a, c in df_animals.head(5).values:
        print(f"{a}: {c}")

    print("\nTop themes:")
    for t, c in df_themes.head(5).values:
        print(f"{t}: {c}")

    print("\nAnalysis saved to:", output_dir)