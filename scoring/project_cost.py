# project_cost.py

from scoring.animal_cost import animal_cost


def expand_entry(entry):
    """Splits an entry into individual animal-name uses, one per
    multiplier count, for BOTH sides of an OR pair independently - e.g.
    "Lion 2 OR Zebra 4" -> ["Lion", "Lion", "Zebra", "Zebra", "Zebra",
    "Zebra"]. Either option can carry its own multiplier (or none), so
    each side is parsed on its own rather than assuming only the first
    option (or only a non-OR entry) can have one."""
    result = []
    for part in entry.split(" OR "):
        tokens = part.split()
        if tokens and tokens[-1].isdigit():
            name = " ".join(tokens[:-1])
            count = int(tokens[-1])
            result.extend([name] * count)
        else:
            result.append(part)
    return result


def parse_entry(entry, lookup):
    if " OR " in entry:
        return entry.split(" OR ")

    parts = entry.split()

    if parts[-1].isdigit():
        name = " ".join(parts[:-1])
        count = int(parts[-1])

        tile = lookup[name]["tile"]
        base = count // tile

        return [name] * base

    return [entry]


# project_cost.py

def compute_project_difficulty(project, lookup):

    base_count = len(project)  # number of slots (NOT expanded)

    total_quality = 0
    has_lvl3 = False
    has_special = False

    for entry in project:

        values = parse_entry(entry, lookup)

        # OR → take easier option
        if " OR " in entry:
            chosen = min(values, key=lambda v: lookup[v]["tile_cost"])
            a = lookup[chosen]
        else:
            a = lookup[values[0]]

        # --- QUALITY ---
        quality = 0

        if a["level"] == 2:
            quality += 1
        elif a["level"] == 3:
            quality += 3
            has_lvl3 = True

        if a.get("special"):
            quality += 4
            has_special = True

        total_quality += quality

    # --- BASE DIFFICULTY FROM SIZE ---
    size_score = base_count * 3

    # --- QUALITY CONTRIBUTION ---
    quality_score = total_quality / base_count

    # --- STRUCTURE MODIFIERS ---
    lvl3_bonus = 3 if has_lvl3 else 0
    special_bonus = 4 if has_special else 0

    difficulty = size_score + quality_score + lvl3_bonus + special_bonus

    return max(int(round(difficulty)), 1)