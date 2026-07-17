# project_rules.py

# This file encodes ALL rules from project_generator.py
# WITHOUT simplification. It is a direct rule representation.
import random

# --- USAGE RULES ---
MAX_PROJECTS_WITH_LVL3 = 2


def can_use_lvl3_project(current_count):
    return current_count < MAX_PROJECTS_WITH_LVL3

def has_multiplier(project):
    # Either side of an OR pair can carry its own multiplier, so check
    # every OR-split option's last token, not just the whole entry's.
    return any(
        part.split() and part.split()[-1].isdigit()
        for e in project
        for part in e.split(" OR ")
    )

def can_use_animal_global(a, used_count):
    """
    Rules:
    - Special animals: max 1 use
    - Level 3 animals: max 1 use
    - Others: max 2 uses
    """
    if a.get("special"):
        return used_count < 1

    if a["level"] == 3:
        return used_count < 1

    return used_count < 2


# --- PROJECT SIZE RULES ---

MIN_PROJECT_SIZE = 3
MAX_PROJECT_SIZE_OPTIONS = [3, 4, 5]


def is_valid_project_size(project):
    return len(project) >= MIN_PROJECT_SIZE


# --- DIFFICULTY RULES ---

RANGES = {
    "easy": (3, 5),
    "medium": (6, 8),
    "hard": (9, 11)
}


def is_within_difficulty_range(difficulty, tier):
    min_target, max_target = RANGES[tier]
    return min_target <= difficulty <= max_target


def is_below_max_difficulty(difficulty, tier):
    _, max_target = RANGES[tier]
    return difficulty <= max_target


def tier_for_difficulty(difficulty):
    """Single source of truth for turning a difficulty number into a
    tier name, derived from RANGES instead of a separately hardcoded
    set of cutoffs living elsewhere."""
    if difficulty <= RANGES["easy"][1]:
        return "easy"
    if difficulty <= RANGES["medium"][1]:
        return "medium"
    return "hard"


# --- THEME RULES ---

def matches_theme(a, theme_type, theme):
    if theme_type == "habitat":
        return theme in a.get("habitats", [])
    if theme_type == "group":
        return theme in a.get("groups", [])
    if theme_type == "tag":
        return theme in a.get("tags", [])
    return False


def valid_themes(pool, min_size=3):
    return {k: v for k, v in pool.items() if len(v) >= min_size}


# --- STRUCTURE LIMITS ---

MAX_LVL3_PER_PROJECT = 1
MAX_SPECIAL_PER_PROJECT = 1
MAX_OR_PER_PROJECT = 2
MAX_MULTIPLIER_PER_PROJECT = 2


def can_add_lvl3(current_count):
    return current_count < MAX_LVL3_PER_PROJECT


def can_add_special(current_count):
    return current_count < MAX_SPECIAL_PER_PROJECT


# --- DIFFICULTY-AWARE SELECTION RULES ---

def passes_difficulty_gap_rules(animal_cost, gap):
    """
    gap = min_target - current_difficulty
    """
    # Too easy → require stronger animals
    if gap > 2:
        if animal_cost < 2:
            return False

    if gap < 1:
        if animal_cost > 4:
            return False

    return True


# --- OR RULES ---

# OR discounts difficulty (see OR_DISCOUNT in scoring/project_rewards.py),
# so an easy project doesn't need it and a hard project benefits from the
# fallback it gives the player - the opposite trend from
# MULTIPLIER_CHANCE, which is more common on easy tiers because a
# multiplier adds difficulty instead. Keyed by the project's tier at the
# time each OR is considered (not a fixed absolute-difficulty threshold),
# so the frequency trend holds regardless of where RANGES happens to put
# each tier's band.
OR_CHANCE = {
    "easy": 0.05,
    "medium": 0.35,
    "hard": 0.55,
}
SECOND_OR_CHANCE = {
    "easy": 0.02,
    "medium": 0.12,
    "hard": 0.25,
}


def can_apply_or(project, difficulty):
    """
    Controls OR appearance frequency:
    - chance scales with tier (rare on easy, common on hard)
    - 2nd OR is rarer than the 1st, at every tier
    """

    or_count = sum(1 for e in project if " OR " in e)

    # --- HARD LIMIT ---
    if or_count >= MAX_OR_PER_PROJECT:
        return False

    tier = tier_for_difficulty(difficulty)

    # --- PROBABILITY CONTROL ---
    if or_count == 0:
        return random.random() < OR_CHANCE.get(tier, 0)
    elif or_count == 1:
        return random.random() < SECOND_OR_CHANCE.get(tier, 0)

    return False

def matches_special_theme(a, theme_type, theme, project_size):
    """
    Special animals are restricted to their specific unlock_group for
    projects of MORE than 3 animals - e.g. Polar bear/Giant Panda
    (unlock_group="predator") only in predator-group-themed projects,
    Asian Elephant (unlock_group="ungulate") only in ungulate-group-themed
    ones. A habitat- or tag-themed 4-5 animal project is excluded
    entirely, not just unrestricted - this used to be the reverse (any
    non-group theme was silently allowed through).

    For a 3-animal project, no extra restriction applies - a special can
    appear via any theme it would normally qualify for, same as a
    non-special animal (e.g. Asian Elephant, tagged "herbivore", can be in
    a herbivore-themed 3-animal project).
    """

    if not a.get("special"):
        return True

    if project_size <= 3:
        return True

    unlock = a.get("unlock_group")

    if not unlock:
        return True

    if theme_type != "group":
        return False

    # unlock_group may contain multiple groups (e.g. "predator;bird")
    unlock_group = set(unlock.split(";"))

    return theme in unlock_group
def is_valid_or_pair(base, alt):

    """
    Rules:
    - Same type
    - If main:
        - neither lvl3
        - neither special
    - If cospecies:
        - size must match
    """
    if base["type"] != alt["type"]:
        return False

    if base["type"] == "main":
        if base["level"] == 3 or alt["level"] == 3:
            return False
        if base.get("special") or alt.get("special"):
            return False
    else:
        if base.get("size") != alt.get("size"):
            return False

    return True


def has_similarity(base, alt):
    shared = 0

    if set(base.get("groups", [])) & set(alt.get("groups", [])):
        shared += 1

    if set(base.get("tags", [])) & set(alt.get("tags", [])):
        shared += 1

    return shared > 0


# --- MULTIPLIER RULES ---

def can_use_multiplier(project, lookup):

    main_count = 0

    for entry in project:
        # OR options are guaranteed the same type (see is_valid_or_pair),
        # so the first option represents the whole slot - counting both
        # sides would double-count a slot that only ever resolves to one.
        name = entry.split(" OR ")[0]
        a = lookup.get(name)
        if not a:
            continue

        if a["type"] == "main":
            main_count += 1

    return main_count < 6


def can_have_multiplier(a):
    return a.get("tile", 1) >= 1


# Chance a multiplier is added at all, keyed by the project's tier
# *before* the multiplier bonus is factored in. Lower on harder tiers so
# multipliers read as a notable easy-project feature rather than a
# guaranteed stack on top of already-hard projects - the opposite trend
# from OR_CHANCE, since a multiplier adds difficulty instead of
# discounting it. A 2nd multiplier (up to MAX_MULTIPLIER_PER_PROJECT) is
# rarer than the 1st, at every tier - mirrors SECOND_OR_CHANCE.
MULTIPLIER_CHANCE = {
    "easy": 0.70,
    "medium": 0.40,
    "hard": 0.15,
}
SECOND_MULTIPLIER_CHANCE = {
    "easy": 0.25,
    "medium": 0.12,
    "hard": 0.05,
}


# A project needs at least this many main (non-cospecies) species to carry
# its own difficulty on their own merits - below that, cospecies are doing
# too much of the work (they're easier to come by than main species), so
# the first multiplier isn't left to chance, it's guaranteed.
MIN_MAIN_SPECIES_FOR_OPTIONAL_MULTIPLIER = 3


def should_apply_multiplier(tier, existing_count=0, main_species_count=None):
    if existing_count == 0 and main_species_count is not None and main_species_count < MIN_MAIN_SPECIES_FOR_OPTIONAL_MULTIPLIER:
        return True
    table = MULTIPLIER_CHANCE if existing_count == 0 else SECOND_MULTIPLIER_CHANCE
    return random.random() < table.get(tier, 0)


def generate_multiplier_values(a):
    tile = a.get("tile", 1)

    base_values = [2 * tile + i for i in range(tile)]
    triple = 3 * tile

    values = base_values + [triple]

    return list(set(values))


# --- FAILURE CONDITIONS ---

def is_valid_project(project, difficulty, tier):
    """
    Final validation:
    - size ≥ 3
    - difficulty within range
    """
    if len(project) < MIN_PROJECT_SIZE:
        return False

    if not is_within_difficulty_range(difficulty, tier):
        return False

    return True


# --- USAGE UPDATE RULE ---

def update_usage(project, usage, expand_entry):
    """
    After success:
    increment usage for all animals (including OR expansions)
    """
    for entry in project:
        for n in expand_entry(entry):
            usage[n] = usage.get(n, 0) + 1


