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

# Easy's upper bound was lowered from 5 to 4 (medium's floor raised to
# match) - after the cospecies-discount rework, raw difficulty values
# skew noticeably lower than before (a simulated 1000-project sample had
# roughly 63% landing "easy"). Moving the single boundary value (5) out
# of "easy" and into "medium" shifted that split to roughly 44% easy /
# 51% medium, with hard's share untouched.
RANGES = {
    "easy": (3, 4),
    "medium": (5, 8),
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
MAX_MULTIPLIER_PER_PROJECT = 3


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

# Flat chance, not keyed by the project's tier-so-far - OR/multiplier
# choices are what should determine a project's difficulty, not the other
# way around, so they're rolled independently of it. Set to what used to
# be the "medium" tier's rate (the middle case) rather than picking new
# numbers from scratch.
OR_CHANCE = 0.35
SECOND_OR_CHANCE = 0.12


def can_apply_or(project):
    """
    Controls OR appearance frequency:
    - flat chance, independent of the project's difficulty so far
    - 2nd OR is rarer than the 1st
    """

    or_count = sum(1 for e in project if " OR " in e)

    # --- HARD LIMIT ---
    if or_count >= MAX_OR_PER_PROJECT:
        return False

    # --- PROBABILITY CONTROL ---
    if or_count == 0:
        return random.random() < OR_CHANCE
    elif or_count == 1:
        return random.random() < SECOND_OR_CHANCE

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


# Flat chance a multiplier is added at all - not keyed by tier, same
# reasoning as OR_CHANCE above: OR/multiplier choices should determine
# difficulty, not react to a difficulty computed before they're applied.
# Each successive multiplier (up to MAX_MULTIPLIER_PER_PROJECT) is rarer
# than the last - mirrors SECOND_OR_CHANCE.
MULTIPLIER_CHANCE = 0.40
SECOND_MULTIPLIER_CHANCE = 0.12
THIRD_MULTIPLIER_CHANCE = 0.04


# A project with this many main (non-cospecies) species or fewer needs a
# multiplier more often to carry its own difficulty on their own merits -
# below that, cospecies are doing too much of the work (they're easier to
# come by than main species). Bumped well above the flat 1st-multiplier
# rate (MULTIPLIER_CHANCE) rather than guaranteed outright.
LOW_MAIN_SPECIES_THRESHOLD = 3
LOW_MAIN_SPECIES_MULTIPLIER_CHANCE = 0.70


def should_apply_multiplier(existing_count=0, main_species_count=None):
    if existing_count == 0 and main_species_count is not None and main_species_count <= LOW_MAIN_SPECIES_THRESHOLD:
        return random.random() < LOW_MAIN_SPECIES_MULTIPLIER_CHANCE
    chances = (MULTIPLIER_CHANCE, SECOND_MULTIPLIER_CHANCE, THIRD_MULTIPLIER_CHANCE)
    chance = chances[existing_count] if existing_count < len(chances) else 0
    return random.random() < chance


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


