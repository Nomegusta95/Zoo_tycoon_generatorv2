import random

# --- CONSTANTS ---
# The physical board differs between base-game-only and expansion play -
# New Shores adds a board slot that raises the level-2 requirement from 9
# to 10 - so the per-level pool size isn't a single fixed constant, it
# depends on whether an expansion pack is in play.
LEVEL_COUNTS_BASE_ONLY = {
    "level_0": 12,
    "level_1": 9,
    "level_2": 9,
    "level_3": 5
}
LEVEL_COUNTS_WITH_EXPANSION = {
    "level_0": 12,
    "level_1": 9,
    "level_2": 10,
    "level_3": 5
}
# Default/backwards-compatible name - the with-expansion board, since that
# covers the common case (base + at least one expansion).
LEVEL_COUNTS = LEVEL_COUNTS_WITH_EXPANSION

# Rulebook, "restrictive" mode only: every habitat needs at least this
# many species present, and every group needs at least this many. Not
# enforced in "freeform" mode at all.
RESTRICTIVE_MIN_PER_HABITAT = 3
RESTRICTIVE_MIN_PER_GROUP = 2

MAX_RETRIES = 100


def level_counts_for(animals):
    """Picks the right board's per-level pool size depending on whether
    any expansion-pack animal is present in the pool being generated from."""
    has_expansion = any(a.get("pack") in ("shores", "additional") for a in animals)
    return LEVEL_COUNTS_WITH_EXPANSION if has_expansion else LEVEL_COUNTS_BASE_ONLY


def matches_unlock_group(animal, req_group):
    if not req_group:
        return True
    req_groups = req_group.split(";")
    animal_groups = animal.get("groups", [])
    return any(group in animal_groups for group in req_groups)


def count_matches_in_pool(pool, req_group):
    return sum(1 for animal in pool if matches_unlock_group(animal, req_group))


def check_required_special(required_animals):
    """Ensure only one special animal is required."""
    required_special = [animal for animal in required_animals if animal.get("special")]
    if len(required_special) > 1:
        raise ValueError("Only one special animal can be required")


def check_required_level_counts(required_animals, level_counts=None):
    """Ensure no level has more required animals than a generated pool has
    room for - otherwise the random.sample() calls below end up with a
    negative sample size and raise a ValueError that gives the user no
    indication of what actually went wrong."""
    level_counts = level_counts or LEVEL_COUNTS
    for level in range(4):
        cap = level_counts[f"level_{level}"]
        count = sum(1 for a in required_animals if a["level"] == level)
        if count > cap:
            raise ValueError(
                f"Too many required level {level} animals selected ({count}) "
                f"- a generated pool only has room for {cap}."
            )


def validate_level_counts(selected, level_counts=None):
    """Validate if the selected animals meet the required level numbers."""
    level_counts = level_counts or LEVEL_COUNTS
    counts = {
        "level_0": sum(1 for a in selected if a["level"] == 0),
        "level_1": sum(1 for a in selected if a["level"] == 1),
        "level_2": sum(1 for a in selected if a["level"] == 2),
        "level_3": sum(1 for a in selected if a["level"] == 3)
    }
    return all(counts[level] == level_counts[level] for level in level_counts)


def validate_habitat_floors(selected, habitats):
    """A habitat is fine at zero (simply not in play this game) or at the
    floor or above - a "broken" partial count (1 or 2) is what's invalid."""
    for h in habitats:
        count = sum(1 for a in selected if h in a.get("habitats", []))
        if 0 < count < RESTRICTIVE_MIN_PER_HABITAT:
            return False
    return True


def validate_group_floors(selected, groups):
    """Same idea as validate_habitat_floors: zero is fine, floor-or-above
    is fine, a lone 1 (or any partial count under the floor) is not."""
    for g in groups:
        count = sum(1 for a in selected if g in a.get("groups", []))
        if 0 < count < RESTRICTIVE_MIN_PER_GROUP:
            return False
    return True


def _select_pool_with_floors(candidates, level_counts, required_animals, habitats, groups):
    """Restrictive-mode pool builder. Generation is NOT forced to include
    every habitat/group - it's free to end up with however many naturally
    fit. What it guarantees is that whichever ones DO end up present are
    properly represented: for each habitat/group, it tries to top up a
    thin one (1-2 for a habitat, 1 for a group) to its floor, and simply
    leaves it wherever it lands if there isn't enough supply to do that -
    it does not force inclusion, and a habitat/group can end up at 0. The
    caller re-validates the result (validate_habitat_floors/
    validate_group_floors, which treat 0 as valid) and retries with a
    fresh attempt if something still ended up "broken" (a partial count
    under the floor) - e.g. because a required animal pinned one there.
    """
    level_target = {
        0: level_counts["level_0"], 1: level_counts["level_1"],
        2: level_counts["level_2"], 3: level_counts["level_3"],
    }

    selected = list(required_animals)
    selected_names = {a["name"] for a in selected}

    for a in required_animals:
        level_target[a["level"]] -= 1
    if any(v < 0 for v in level_target.values()):
        return None

    pool = [a for a in candidates if a["name"] not in selected_names]
    random.shuffle(pool)

    def can_take(a):
        return level_target.get(a["level"], 0) > 0 and a["name"] not in selected_names

    def commit(a):
        selected.append(a)
        selected_names.add(a["name"])
        level_target[a["level"]] -= 1

    def current_count(attr, key):
        return sum(1 for a in selected if key in a.get(attr, []))

    def top_up(attr, key, floor):
        while current_count(attr, key) < floor:
            candidate = next((a for a in pool if key in a.get(attr, []) and can_take(a)), None)
            if candidate is None:
                return  # not enough supply - leave it as-is; validated (and retried if needed) by the caller
            commit(candidate)

    for h in habitats:
        top_up("habitats", h, RESTRICTIVE_MIN_PER_HABITAT)

    for g in groups:
        top_up("groups", g, RESTRICTIVE_MIN_PER_GROUP)

    # Fill whatever's left of each level's budget at random. This has no
    # habitat/group awareness, so it can occasionally leave something
    # thin - validate_habitat_floors/validate_group_floors catch that.
    for level, remaining in level_target.items():
        if remaining <= 0:
            continue
        eligible = [a for a in pool if a["level"] == level and can_take(a)]
        if len(eligible) < remaining:
            return None
        for a in random.sample(eligible, remaining):
            commit(a)

    return selected


def enforce_pool_requirements(selected_animals, allowed_animals, protected_names=None):
    """protected_names (e.g. user-required animals) are never swapped out
    to make room for someone else's unlock_group requirement - without
    this, a required animal could silently vanish from the pool despite
    the caller explicitly asking for it."""
    protected_names = protected_names or set()
    selected_animals = selected_animals[:]
    for animal in selected_animals:
        req_group = animal.get("unlock_group")
        req_count = animal.get("unlock_count", 0)

        if not req_group or count_matches_in_pool(selected_animals, req_group) >= req_count:
            continue

        needed = req_count - count_matches_in_pool(selected_animals, req_group)
        candidates = [
            candidate for candidate in allowed_animals
            if matches_unlock_group(candidate, req_group) and candidate not in selected_animals
        ]
        random.shuffle(candidates)
        added_animals = candidates[:needed]

        if len(added_animals) < needed:
            return None  # Cannot satisfy requirements; fail early

        for new_animal in added_animals:
            for i, old_animal in enumerate(selected_animals):
                if (
                    old_animal["name"] != animal["name"]
                    and old_animal["name"] not in protected_names
                    and old_animal["level"] == new_animal["level"]
                ):
                    selected_animals[i] = new_animal
                    break
            else:
                # No same-level, non-protected animal available to swap
                # out without breaking LEVEL_COUNTS. Fail this attempt
                # instead of swapping in a mismatched level (select_game_pool
                # retries).
                return None

    # A later swap can silently break an earlier animal's already-verified
    # requirement when two requirements have overlapping groups (e.g.
    # "aquatic;reptile" and "aquatic;fish" both accept an "aquatic"
    # animal) - swapping in a same-group animal to satisfy one can end up
    # displacing the exact animal that was covering the other. Re-check
    # every requirement now that all swapping is done, instead of shipping
    # a pool that violates one it was supposed to guarantee.
    for animal in selected_animals:
        req_group = animal.get("unlock_group")
        req_count = animal.get("unlock_count", 0)
        if req_group and count_matches_in_pool(selected_animals, req_group) < req_count:
            return None

    return selected_animals


def select_game_pool(animals, required_animals=None, mode="freeform"):
    usable_animals = [a for a in animals if a["type"] in ("main", "cospecies")]
    required_animals = [a for a in usable_animals if required_animals and a["name"] in required_animals]

    level_counts = level_counts_for(animals)

    check_required_special(required_animals)
    check_required_level_counts(required_animals, level_counts)

    # sorted(), not list() - set iteration order depends on Python's
    # per-process string hash randomization, so random.sample() below
    # would pick different habitats on every fresh run despite the same
    # random.seed().
    all_habitats = sorted({habitat for animal in animals for habitat in animal.get("habitats", [])})
    all_groups = sorted({group for animal in animals for group in animal.get("groups", [])})

    for attempt in range(MAX_RETRIES):
        required_habitats = {h for a in required_animals for h in a.get("habitats", [])}

        # Same random "3 or 4 of 6" habitat pick as freeform, in both
        # modes - restrictive mode doesn't force which (or how many)
        # habitats are in play, only that whichever ones make the cut are
        # properly represented (see _select_pool_with_floors), not all 6
        # forced active.
        extra_habitats = random.sample(
            [h for h in all_habitats if h not in required_habitats],
            max(0, random.choice([3, 4]) - len(required_habitats))
        )
        allowed_habitats = required_habitats.union(extra_habitats)
        filtered = [a for a in usable_animals if set(a.get("habitats", [])) & allowed_habitats]

        level_pools = {level: [a for a in filtered if a["level"] == i] for i, level in enumerate(level_counts)}

        if not all(len(level_pools[level]) >= level_counts[level] for level in level_counts):
            continue

        if mode == "restrictive":
            selected_animals = _select_pool_with_floors(
                filtered, level_counts, required_animals, allowed_habitats, all_groups
            )
            if selected_animals is None:
                continue
        else:
            selected_animals = (
                random.sample(level_pools["level_0"], level_counts["level_0"]) +
                required_animals +
                random.sample(level_pools["level_1"],
                              max(0, level_counts["level_1"] - len([a for a in required_animals if a["level"] == 1]))) +
                random.sample(level_pools["level_2"],
                              max(0, level_counts["level_2"] - len([a for a in required_animals if a["level"] == 2]))) +
                random.sample(level_pools["level_3"],
                              max(0, level_counts["level_3"] - len([a for a in required_animals if a["level"] == 3])))
            )
            selected_animals = list({a["name"]: a for a in selected_animals}.values())

        selected_animals = enforce_pool_requirements(
            selected_animals, filtered, protected_names={a["name"] for a in required_animals}
        )

        if not selected_animals or not validate_level_counts(selected_animals, level_counts):
            continue

        # enforce_pool_requirements' swaps have no awareness of the
        # habitat/group floors - re-check after it runs rather than
        # trusting _select_pool_with_floors' guarantee still holds.
        if mode == "restrictive" and not (
            validate_habitat_floors(selected_animals, all_habitats)
            and validate_group_floors(selected_animals, all_groups)
        ):
            continue

        return selected_animals

    raise ValueError("Failed to generate valid pool after 100 attempts")


def generate_game(animals, required_animals=None, mode="freeform"):
    game_animals = select_game_pool(animals, required_animals, mode=mode)
    return None, game_animals
