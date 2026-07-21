import random
from core.project_naming import generate_project_name, is_symbiosis_project, symbiosis_badge_traits, SYMBIOSIS_CHANCE
from scoring.project_cost import expand_entry
from scoring.project_rewards import get_project_reward
from core.utils import (
    normalize_entry as normalize_name,
    extract_animal_names as extract_names,
    sort_project_animals,
)
from core.project_rules import (
    can_use_animal_global,
    can_add_lvl3,
    can_add_special,
    can_apply_or,
    is_valid_or_pair,
    has_similarity,
    can_use_multiplier,
    can_have_multiplier,
    generate_multiplier_values,
    should_apply_multiplier,
    is_valid_project,
    update_usage,
    tier_for_difficulty,
    MAX_OR_PER_PROJECT,
    MAX_MULTIPLIER_PER_PROJECT,
    matches_theme,
    matches_special_theme
)

# -------------------------
# 🔧 SHARED HELPERS
# -------------------------
# normalize_name / extract_names now come from core.utils (single
# implementation, previously duplicated here). Difficulty scoring now
# comes from scoring.project_rewards.compute_difficulty - previously this
# file had its own compute_simple_difficulty with completely different,
# uncalibrated weights (e.g. +8 for a lvl3 animal, +15 for special) that
# disagreed with the difficulty/reward shown to the player.


# -------------------------
# OR CANDIDATES (UNCHANGED)
# -------------------------

def find_or_candidates(a, animals, theme_type, theme):
    candidates = []

    for x in animals:
        if x["name"] == a["name"]:
            continue

        if not matches_theme(x, theme_type, theme):
            continue

        if not is_valid_or_pair(a, x):
            continue

        if not has_similarity(a, x):
            continue

        candidates.append(x["name"])

    return candidates


# -------------------------
# MAIN GENERATOR
# -------------------------

def generate_project(animals, usage, lookup=None, usable=None):

    # lookup/usable can be precomputed once by the caller (e.g. when this
    # is called many times per game) instead of rebuilt on every attempt.
    if lookup is None:
        lookup = {a["name"]: a for a in animals}
    if usable is None:
        usable = [a for a in animals if a["type"] in ("main", "cospecies")]

    # --- THEME ---
    theme_type = random.choice(["habitat", "group", "tag"])

    all_themes = set()
    for a in usable:
        all_themes.update(a.get(theme_type + "s", []))

    if not all_themes:
        return None

    # sorted(), not list() - set iteration order depends on Python's
    # per-process string hash randomization, so the same random.seed()
    # would pick a different theme (and everything downstream of it) on
    # every fresh run despite the "same" seed.
    theme = random.choice(sorted(all_themes))

    candidates = [
        a for a in usable
        if matches_theme(a, theme_type, theme)
    ]

    if len(candidates) < 3:
        return None

    random.shuffle(candidates)

    project = []
    used = set()

    lvl3_count = 0
    special_count = 0

    target_size = random.choice([3, 4, 5])

    # -------------------------
    # BUILD BASE
    # -------------------------
    for a in candidates:

        if not matches_special_theme(a, theme_type, theme, target_size):
            continue

        if len(project) >= target_size:
            break

        name = a["name"]

        if name in used:
            continue

        if not can_use_animal_global(a, usage.get(name, 0)):
            continue

        if a["level"] == 3 and not can_add_lvl3(lvl3_count):
            continue

        if a.get("special") and not can_add_special(special_count):
            continue

        project.append(name)
        used.add(name)

        if a["level"] == 3:
            lvl3_count += 1

        if a.get("special"):
            special_count += 1

    if len(project) < 3:
        return None

    main_count = sum(
        1 for name in project
        if lookup.get(name, {}).get("type") == "main"
    )

    if main_count < 2:
        return None

    # -------------------------
    # OR (flat frequency - see OR_CHANCE/SECOND_OR_CHANCE. Rolled without
    # regard to the project's difficulty so far: OR/multiplier choices are
    # what should determine the final difficulty, not react to a
    # difficulty computed before they're applied - see FINAL below.)
    # -------------------------
    attempts = 0
    while attempts < 5:

        or_count = sum(1 for e in project if " OR " in e)
        if or_count >= MAX_OR_PER_PROJECT:
            break

        # Rolled ONCE per pass, not once per candidate entry below - OR_CHANCE
        # is meant to be "chance this project gets its Nth OR", not "chance
        # per entry", which would silently compound across every eligible
        # entry tried and make the configured percentages meaningless.
        if not can_apply_or(project):
            break

        applied = False

        for i, entry in enumerate(project):

            if " OR " in entry:
                continue

            base_name = normalize_name(entry)
            a = lookup.get(base_name)

            if not a:
                continue

            if a["level"] == 3 or a.get("special"):
                continue

            or_candidates = find_or_candidates(a, usable, theme_type, theme)

            if not or_candidates:
                continue

            alt = random.choice(or_candidates)

            if alt in extract_names(project):
                continue

            alt_a = lookup.get(alt)

            if not can_use_animal_global(alt_a, usage.get(alt, 0)):
                continue

            if not matches_special_theme(alt_a, theme_type, theme, target_size):
                continue

            project[i] = f"{base_name} OR {alt}"
            applied = True
            break

        if not applied:
            break

        attempts += 1

    # -------------------------
    # MULTIPLIER (flat frequency, up to MAX_MULTIPLIER_PER_PROJECT - see
    # MULTIPLIER_CHANCE/SECOND_MULTIPLIER_CHANCE and the OR note above)
    # -------------------------
    # (slot_index, side_index) pairs already multiplied - side_index is
    # always 0 for a plain entry, but 0 or 1 for an OR pair, since either
    # option can carry its own multiplier independently of the other (e.g.
    # "Lion 2 OR Zebra 4", not just the base option).
    multiplied_slots = set()

    # Snapshotted once, before any multiplier is applied - a multiplier
    # only appends a number to an entry's name (e.g. "Zebra" -> "Zebra 4"),
    # it never changes how many entries are main vs. cospecies, so this
    # doesn't need (and shouldn't use) a live recount each pass.
    main_species_count = sum(
        1 for name in project
        if lookup.get(name.split(" OR ")[0], {}).get("type") == "main"
    )

    while len(multiplied_slots) < MAX_MULTIPLIER_PER_PROJECT and can_use_multiplier(project, lookup):

        if not should_apply_multiplier(len(multiplied_slots), main_species_count):
            break

        weighted_candidates = []

        for i, entry in enumerate(project):
            for side, name in enumerate(entry.split(" OR ")):
                if (i, side) in multiplied_slots:
                    continue

                a = lookup.get(name)
                if not a:
                    continue

                if a["type"] != "main":
                    continue

                if a.get("special"):
                    continue

                if a["level"] not in (1, 2):
                    continue

                if not can_have_multiplier(a):
                    continue

                weight = 5 if a["level"] == 1 else 2
                weighted_candidates.extend([(i, side, name, a)] * int(weight * 10))

        if not weighted_candidates:
            break

        i, side, name, a = random.choice(weighted_candidates)
        value = random.choice(generate_multiplier_values(a))
        parts = project[i].split(" OR ")
        parts[side] = f"{name} {value}"
        project[i] = " OR ".join(parts)
        multiplied_slots.add((i, side))

    project = sort_project_animals(project, lookup)

    # -------------------------
    # FINAL
    # -------------------------
    difficulty = get_project_reward({"animals": project}, lookup)["first"]
    tier = tier_for_difficulty(difficulty)

    # Reject projects whose difficulty doesn't actually fall in range for
    # their tier (e.g. multiplier/OR stacking pushed a "hard" project past
    # RANGES["hard"][1]). Caller treats None as a failed attempt and retries.
    if not is_valid_project(project, difficulty, tier):
        return None

    # Usage is only committed once a project is fully accepted - a
    # rejected attempt must not burn a special/lvl3 animal's one-time
    # global usage slot (see can_use_animal_global).
    update_usage(project, usage, expand_entry)

    # Eligible (all 3 trait dimensions align) doesn't mean it actually
    # becomes a symbiosis project - only SYMBIOSIS_CHANCE of eligible
    # projects get the treatment, the rest present as normal despite
    # qualifying. Rolled once here so naming/badges/frame all agree.
    symbiosis_eligible = is_symbiosis_project(project, lookup)
    symbiosis = symbiosis_eligible and random.random() < SYMBIOSIS_CHANCE

    return {
        "name": generate_project_name(project, theme_type, theme, lookup, difficulty, is_symbiosis=symbiosis),
        "animals": project,
        "theme": theme,
        "theme_type": theme_type,
        "difficulty": difficulty,
        "tier": tier,
        "symbiosis": symbiosis,
        "symbiosis_badges": symbiosis_badge_traits(project, theme_type, theme, lookup) if symbiosis else None
    }

