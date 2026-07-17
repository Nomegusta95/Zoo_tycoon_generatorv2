from data_loader import load_animals
import math
from collections import Counter


# --- REAL TILE COST ---
def animal_real_cost(a):
    tiles_needed = math.ceil(a["min_individual"] / a["tile"])
    wt = a.get("water_type", "none")

    if wt == "water":
        return tiles_needed + a.get("min_free_tiles", 0)

    if wt == "semi":
        return tiles_needed * a["tile_cost"] + a.get("water_tiles_needed", 0)

    return tiles_needed * a["tile_cost"]


# --- NEW ANIMAL COST (FINAL SYSTEM) ---
def animal_cost(a):

    # --- COSPECIES ---
    if a["type"] == "cospecies":
        return 1 if a.get("size") == "small" else 2

    # --- REAL TILE COST ---
    tiles = math.ceil(a["min_individual"] / a["tile"])
    base = tiles * a["tile_cost"]

    # --- WATER ADJUSTMENTS ---
    if a.get("water_type") == "water":
        base += a.get("min_free_tiles", 0)

    elif a.get("water_type") == "semi":
        base += a.get("water_tiles_needed", 0)

    cost = int(0.7*base)  # ← NO NORMALIZATION

    # --- LEVEL IMPACT ---
    if a["level"] == 2:
        cost += 2
    elif a["level"] == 3:
        cost += 6

    # --- SPECIAL ---
    if a.get("special"):
        cost += 7

    return cost


# --- ANALYSIS ---
def analyze_animals(animals):

    results = []

    for a in animals:
        if a["type"] != "main":
            continue

        real = animal_real_cost(a)
        cost = animal_cost(a)

        results.append((a["name"], real, cost, a["level"], a.get("special", False)))

    # --- SORT BY COST ---
    results.sort(key=lambda x: x[2])

    # --- PRINT TABLE ---
    print("\n=== ANIMAL COST TABLE ===")
    print(f"{'Name':30} {'RealCost':10} {'Cost':6} {'Lvl':4} {'Special':7}")
    print("-" * 65)

    for name, real, cost, lvl, special in results:
        print(f"{name:30} {real:<10} {cost:<6} {lvl:<4} {str(special):<7}")

    # --- DISTRIBUTION ---
    dist = Counter(cost for _, _, cost, _, _ in results)

    print("\n=== COST DISTRIBUTION ===")
    for k in sorted(dist):
        print(f"Cost {k}: {dist[k]} animals")

    # --- EXTREMES ---
    print("\n=== EASIEST ===")
    for r in results[:5]:
        print(r)

    print("\n=== HARDEST ===")
    for r in results[-5:]:
        print(r)


# --- RUN ---
if __name__ == "__main__":
    animals = load_animals("animals.xlsx")
    analyze_animals(animals)