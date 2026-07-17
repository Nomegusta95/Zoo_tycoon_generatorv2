# animal_cost.py

import math


def animal_real_cost(a):
    tiles_needed = math.ceil(a["min_individual"] / a["tile"])
    wt = a.get("water_type", "none")

    if wt == "water":
        return tiles_needed + a.get("min_free_tiles", 0)

    if wt == "semi":
        return tiles_needed * a["tile_cost"] + a.get("water_tiles_needed", 0)

    return tiles_needed * a["tile_cost"]


def animal_cost(a):

    if a["type"] == "cospecies":
        return 1 if a.get("size") == "small" else 2

    tiles = math.ceil(a["min_individual"] / a["tile"])
    base = tiles * a["tile_cost"]

    if a.get("water_type") == "water":
        base += a.get("min_free_tiles", 0)
    elif a.get("water_type") == "semi":
        base += a.get("water_tiles_needed", 0)

    cost = int(0.7 * base)

    if a["level"] == 2:
        cost += 2
    elif a["level"] == 3:
        cost += 5

    if a.get("special"):
        cost += 6

    return cost