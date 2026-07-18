# Difficulty weight per animal slot. Reflects the hierarchy:
# cospecies < level 1 < level 2 < level 3 < special. SPECIAL_WEIGHT stacks
# on top of the animal's own level weight (a special is still whatever
# level it is, plus extra for being special) rather than replacing it.
#
# Calibrated against 10 real predefined-project reward cards from the
# original board game (see conversation history / project memory) - the
# level 2/3 and special weights were originally much higher and badly
# overscored small special-heavy projects (e.g. Polar Park), while
# SIZE_BONUS_PER_SLOT was too weak and OR_DISCOUNT too strong, badly
# underscoring larger OR-heavy projects (e.g. Serengeti). This set gets
# 6/10 real cards exact and the rest within 1 point.
SLOT_WEIGHTS = {
    "cospecies": 0.6,
    1: 1.0,
    2: 1.5,
    3: 1.75,
}
SPECIAL_WEIGHT = 2.75

# A project containing a level-3 animal gets this on top of that animal's
# own SLOT_WEIGHTS[3] entry - a level-3 species is the rarest non-special
# tier, and a project built around one should read as noticeably harder
# than the same project would with a level-2 in its place, not just
# +0.25 harder. MAX_LVL3_PER_PROJECT is 1, so this is a flat per-project
# bump rather than something that needs to scale with a count.
LVL3_PROJECT_BONUS = 1.5

# More MAIN animals is harder on its own, beyond what summing slot
# weights already implies - each main slot past the minimum size of 3
# adds a bit more. Cospecies count toward this too, but only partially
# (COSPECIES_SIZE_BONUS_RATE) - a project padded out with cheap cospecies
# still shouldn't read as "bigger and harder" the way adding more main
# species does, but scoping this to main slots alone (rate 0) pulled
# difficulty down too broadly across generated games in practice, since
# cospecies are common in a generated pool - most projects include at
# least one, so almost everything lost some of its size bonus. Softened
# to a partial rate instead of an outright exclusion.
SIZE_BONUS_PER_SLOT = 1.5
COSPECIES_SIZE_BONUS_RATE = 0.3

# The real cards show no evidence that an OR slot makes a project easier
# (a Jaguar OR Puma project scores the same as an equivalent single-name
# project) - so this no longer discounts difficulty at all.
OR_DISCOUNT = 0.0

# A multiplier makes a slot harder to fulfill in proportion to its value -
# "Zebra 2" barely matters, "Zebra 11" is a real ask. Values at or below
# the baseline contribute nothing; every unit above it adds
# MULTIPLIER_VALUE_BONUS_PER_UNIT. Summed across every multiplied option
# in the project (either side of an OR pair can carry its own value).
MULTIPLIER_VALUE_BASELINE = 3
MULTIPLIER_VALUE_BONUS_PER_UNIT = 0.25

# Cospecies are easier to come by than main species, so a "small" one
# (see the "size" field on the animal, from data/Animals.xlsx) gets this
# knocked off on top of its own (lower) SLOT_WEIGHTS entry above - it's
# a minor, easy-to-spot filler. A "big" cospecies (e.g. West caucasian
# tur, Great hornbill) does NOT get this discount at all - despite being
# cospecies-tier, it's a substantial enough animal that padding a project
# out with it shouldn't make that project easier. This is a per-animal
# rule (each cospecies' own size), not a per-project cospecies-count rule.
COSPECIES_SMALL_DISCOUNT = 0.3

MIN_DIFFICULTY = 3
DIFFICULTY_FLOOR = 0.5


def _slot_weight(animal):
    if not animal:
        return 0
    if animal["type"] != "main":
        return SLOT_WEIGHTS["cospecies"]
    weight = SLOT_WEIGHTS.get(animal["level"], SLOT_WEIGHTS["cospecies"])
    if animal.get("special"):
        weight += SPECIAL_WEIGHT
    return weight


def compute_difficulty(entries, lookup):
    """Single source of truth for project difficulty. Used both for the
    difficulty/reward shown to the player and internally during
    generation (e.g. deciding when an OR is allowed) - previously those
    two things used different, uncalibrated formulas that disagreed with
    each other."""

    total = 0.0
    or_count = 0
    main_count = 0
    cospecies_count = 0
    has_lvl3 = False

    for entry in entries:
        parts = entry.split(" OR ")
        if len(parts) > 1:
            or_count += 1

        # Either side of an OR pair can carry its own multiplier (e.g.
        # "Lion 2 OR Zebra 4"), so every option's value is scored, not
        # just the first.
        for p in parts:
            p_tokens = p.split()
            if p_tokens and p_tokens[-1].isdigit():
                value = int(p_tokens[-1])
                total += max(0, value - MULTIPLIER_VALUE_BASELINE) * MULTIPLIER_VALUE_BONUS_PER_UNIT

        # For an OR slot, both options are already constrained to be
        # similar in tier (same type, neither lvl3/special) - the first
        # option is representative enough for weighting purposes.
        tokens = parts[0].split()

        if tokens and tokens[-1].isdigit():
            tokens = tokens[:-1]

        name = " ".join(tokens)
        animal = lookup.get(name)
        total += _slot_weight(animal)

        if animal:
            if animal["type"] != "main":
                cospecies_count += 1
                if animal.get("size") == "small":
                    total -= COSPECIES_SMALL_DISCOUNT
            else:
                main_count += 1
                if animal["level"] == 3:
                    has_lvl3 = True

    effective_size_count = main_count + COSPECIES_SIZE_BONUS_RATE * cospecies_count
    total += SIZE_BONUS_PER_SLOT * max(0, effective_size_count - 3)
    total -= OR_DISCOUNT * or_count

    if has_lvl3:
        total += LVL3_PROJECT_BONUS

    return max(total, DIFFICULTY_FLOOR)


def get_project_reward(project, lookup):
    difficulty = compute_difficulty(project["animals"], lookup)
    first = max(MIN_DIFFICULTY, round(difficulty))

    # --- SECOND REWARD (NON-LINEAR) ---
    if first <= 5:
        second = 2
    elif first <= 7:
        second = 3
    elif first <= 9:
        second = 4
    elif first <= 11:
        second = 5
    elif first <= 13:
        second = 6
    else:
        second = 7

    return {
        "first": first,
        "second": second
    }
