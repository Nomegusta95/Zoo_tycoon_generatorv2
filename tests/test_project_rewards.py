from scoring.project_rewards import (
    compute_difficulty,
    get_project_reward,
    SLOT_WEIGHTS,
    SPECIAL_WEIGHT,
    SIZE_BONUS_PER_SLOT,
    OR_DISCOUNT,
    MULTIPLIER_VALUE_BASELINE,
    MULTIPLIER_VALUE_BONUS_PER_UNIT,
    COSPECIES_SMALL_DISCOUNT,
    MIN_DIFFICULTY,
    DIFFICULTY_FLOOR,
)


def make_animal(name, type_="main", level=1, special=False, size=None):
    return {"name": name, "type": type_, "level": level, "special": special, "size": size}


def make_lookup(*animals):
    return {a["name"]: a for a in animals}


# --- hierarchy: cospecies < lvl1 < lvl2 < lvl3 < special ---

def test_slot_weight_hierarchy_is_strictly_increasing():
    cospecies = make_animal("Cospecies", type_="cospecies")
    lvl1 = make_animal("Lvl1", level=1)
    lvl2 = make_animal("Lvl2", level=2)
    lvl3 = make_animal("Lvl3", level=3)
    special = make_animal("Special", level=1, special=True)

    lookup = make_lookup(cospecies, lvl1, lvl2, lvl3, special)

    # Use a fixed 3-slot project (no size bonus kicks in) and swap only the
    # first slot so each project isolates the weight of a single animal.
    filler = [make_animal("Filler1"), make_animal("Filler2")]
    for f in filler:
        lookup[f["name"]] = f
    filler_names = [f["name"] for f in filler]

    def difficulty_for(animal):
        entries = [animal["name"]] + filler_names
        return compute_difficulty(entries, lookup)

    d_cospecies = difficulty_for(cospecies)
    d_lvl1 = difficulty_for(lvl1)
    d_lvl2 = difficulty_for(lvl2)
    d_lvl3 = difficulty_for(lvl3)
    d_special = difficulty_for(special)

    assert d_cospecies < d_lvl1 < d_lvl2 < d_lvl3 < d_special


def test_special_stacks_with_level_weight():
    # A level-1 special animal should weigh SLOT_WEIGHTS[1] + SPECIAL_WEIGHT,
    # not SPECIAL_WEIGHT alone.
    special = make_animal("Special", level=1, special=True)
    other = make_animal("Other", level=1)
    lookup = make_lookup(special, other)

    d_special = compute_difficulty(["Special", "Other", "Other"], lookup)
    d_plain = compute_difficulty(["Other", "Other", "Other"], lookup)

    assert d_special - d_plain == SPECIAL_WEIGHT


# --- more animals is harder ---

def test_more_animals_increases_difficulty_by_expected_gap():
    a = make_animal("A", level=1)
    lookup = make_lookup(a)

    d3 = compute_difficulty(["A", "A", "A"], lookup)
    d5 = compute_difficulty(["A", "A", "A", "A", "A"], lookup)

    expected_gap = 2 * SLOT_WEIGHTS[1] + 2 * SIZE_BONUS_PER_SLOT
    assert d5 - d3 == expected_gap


# --- OR discount ---

def test_or_entry_reduces_difficulty_by_or_discount():
    a = make_animal("A", level=1)
    b = make_animal("B", level=1)
    lookup = make_lookup(a, b)

    without_or = compute_difficulty(["A", "A", "A"], lookup)
    with_or = compute_difficulty(["A OR B", "A", "A"], lookup)

    assert without_or - with_or == OR_DISCOUNT


# --- multiplier bonus (scales with value, not a flat presence bonus) ---

def test_low_multiplier_value_adds_no_bonus():
    # A low multiplier (e.g. x2) is barely a harder ask than the plain
    # animal, so it should add nothing - only values above
    # MULTIPLIER_VALUE_BASELINE contribute.
    a = make_animal("A", level=1)
    lookup = make_lookup(a)

    no_multiplier = compute_difficulty(["A", "A", "A"], lookup)
    low_multiplier = compute_difficulty(["A 2", "A", "A"], lookup)

    assert low_multiplier == no_multiplier


def test_high_multiplier_value_adds_proportional_bonus():
    # A high multiplier (e.g. x11) is a real ask and should meaningfully
    # raise difficulty, proportional to how far above the baseline it is.
    a = make_animal("A", level=1)
    lookup = make_lookup(a)

    no_multiplier = compute_difficulty(["A", "A", "A"], lookup)
    high_multiplier = compute_difficulty(["A 11", "A", "A"], lookup)

    expected_bonus = (11 - MULTIPLIER_VALUE_BASELINE) * MULTIPLIER_VALUE_BONUS_PER_UNIT
    assert high_multiplier - no_multiplier == expected_bonus
    assert expected_bonus >= 1  # "a point or two" for a high value like x11


def test_multiplier_bonus_sums_across_multiple_multiplied_slots():
    # Two multiplied slots should each contribute their own bonus, not be
    # capped at a single flat bonus for the whole project.
    a = make_animal("A", level=1)
    lookup = make_lookup(a)

    no_multiplier = compute_difficulty(["A", "A", "A"], lookup)
    one_multiplier = compute_difficulty(["A 11", "A", "A"], lookup)
    two_multipliers = compute_difficulty(["A 11", "A 11", "A"], lookup)

    per_slot_bonus = one_multiplier - no_multiplier
    assert two_multipliers - no_multiplier == 2 * per_slot_bonus


def test_or_alt_side_multiplier_also_counts():
    # Either side of an OR pair can carry its own multiplier.
    a = make_animal("A", level=1)
    b = make_animal("B", level=1)
    lookup = make_lookup(a, b)

    no_multiplier = compute_difficulty(["A OR B", "A", "A"], lookup)
    alt_multiplied = compute_difficulty(["A OR B 11", "A", "A"], lookup)

    expected_bonus = (11 - MULTIPLIER_VALUE_BASELINE) * MULTIPLIER_VALUE_BONUS_PER_UNIT
    assert alt_multiplied - no_multiplier == expected_bonus


# --- cospecies discount (per-animal "size", not a project-wide count) ---

def test_small_cospecies_gets_the_discount():
    # Swapping one main slot for a SMALL cospecies should cost less than
    # SLOT_WEIGHTS["cospecies"] alone would suggest, once the discount is
    # netted against it.
    main = make_animal("Main", level=1)
    cospecies = make_animal("Cospecies", type_="cospecies", size="small")
    lookup = make_lookup(main, cospecies)

    all_main = compute_difficulty(["Main", "Main", "Main"], lookup)
    one_cospecies = compute_difficulty(["Main", "Main", "Cospecies"], lookup)

    actual_swap_cost = one_cospecies - all_main
    expected_swap_cost = (SLOT_WEIGHTS["cospecies"] - COSPECIES_SMALL_DISCOUNT) - SLOT_WEIGHTS[1]
    assert round(actual_swap_cost, 10) == round(expected_swap_cost, 10)


def test_big_cospecies_gets_no_discount():
    # A BIG cospecies costs exactly SLOT_WEIGHTS["cospecies"] - no
    # discount at all, unlike a small one.
    main = make_animal("Main", level=1)
    cospecies = make_animal("Cospecies", type_="cospecies", size="big")
    lookup = make_lookup(main, cospecies)

    all_main = compute_difficulty(["Main", "Main", "Main"], lookup)
    one_cospecies = compute_difficulty(["Main", "Main", "Cospecies"], lookup)

    actual_swap_cost = one_cospecies - all_main
    expected_swap_cost = SLOT_WEIGHTS["cospecies"] - SLOT_WEIGHTS[1]
    assert round(actual_swap_cost, 10) == round(expected_swap_cost, 10)


def test_small_cospecies_heavy_project_scores_at_most_a_main_only_project():
    # The concrete case that motivated this rule: 2 main animals padded
    # out to 5 slots with 3 SMALL cospecies should score no higher than
    # the same 2 mains rounded out to 3 with one more main animal. This
    # guarantee is specific to small cospecies - a big one is deliberately
    # exempt from the discount that makes this hold (see
    # test_big_cospecies_is_not_guaranteed_cheaper_than_a_main_only_project).
    main1 = make_animal("Main1", level=1)
    main2 = make_animal("Main2", level=1)
    main3 = make_animal("Main3", level=1)
    cospecies = [make_animal(f"Cospecies{i}", type_="cospecies", size="small") for i in range(3)]
    lookup = make_lookup(main1, main2, main3, *cospecies)

    three_mains = compute_difficulty(["Main1", "Main2", "Main3"], lookup)
    five_with_three_cospecies = compute_difficulty(
        ["Main1", "Main2", "Cospecies0", "Cospecies1", "Cospecies2"], lookup
    )

    assert five_with_three_cospecies <= three_mains


def test_big_cospecies_is_not_guaranteed_cheaper_than_a_main_only_project():
    # The mirror case: with no discount at all, 3 BIG cospecies can (and
    # here does) score HIGHER than the equivalent main-only project -
    # this is the intended effect of "if cospecies is big there's no
    # penalty", not a regression of the small-cospecies guarantee above.
    main1 = make_animal("Main1", level=1)
    main2 = make_animal("Main2", level=1)
    main3 = make_animal("Main3", level=1)
    cospecies = [make_animal(f"Cospecies{i}", type_="cospecies", size="big") for i in range(3)]
    lookup = make_lookup(main1, main2, main3, *cospecies)

    three_mains = compute_difficulty(["Main1", "Main2", "Main3"], lookup)
    five_with_three_cospecies = compute_difficulty(
        ["Main1", "Main2", "Cospecies0", "Cospecies1", "Cospecies2"], lookup
    )

    assert five_with_three_cospecies > three_mains


# --- difficulty floor ---

def test_minimal_all_small_cospecies_project_reflects_the_discount():
    # 3 small-cospecies slots at SLOT_WEIGHTS["cospecies"] each, minus
    # the small-cospecies discount applied to all 3 - still comfortably
    # above DIFFICULTY_FLOOR for a realistic minimal (3-slot) project.
    a = make_animal("A", type_="cospecies", size="small")
    b = make_animal("B", type_="cospecies", size="small")
    lookup = make_lookup(a, b)

    entries = ["A OR B", "A OR B", "A"]
    difficulty = compute_difficulty(entries, lookup)

    raw = 3 * SLOT_WEIGHTS["cospecies"] - 3 * COSPECIES_SMALL_DISCOUNT
    assert raw > DIFFICULTY_FLOOR
    # round() rather than exact equality - the discount is subtracted
    # once per small cospecies in a loop, not as a single multiplication,
    # so the two sides can differ in the last float bit.
    assert round(difficulty, 10) == round(raw, 10)


def test_difficulty_floor_still_engages_for_a_pathologically_cheap_input():
    # Not a project the generator would ever actually produce (real
    # projects have MIN_PROJECT_SIZE >= 3 entries) - this exists purely to
    # confirm the floor itself still defends against a value that would
    # otherwise go at or below zero. An empty entry list is used instead
    # of a hand-picked "cheap" combination of entries, since which
    # combination of weights is cheap enough to go below the floor
    # depends on the current calibration of SLOT_WEIGHTS/OR_DISCOUNT/etc,
    # while zero entries sums to exactly 0 regardless of calibration.
    lookup = {}

    difficulty = compute_difficulty([], lookup)

    assert difficulty == DIFFICULTY_FLOOR


# --- get_project_reward ---

def test_get_project_reward_first_is_never_below_min_difficulty():
    a = make_animal("A", type_="cospecies")
    b = make_animal("B", type_="cospecies")
    lookup = make_lookup(a, b)

    reward = get_project_reward({"animals": ["A OR B", "A OR B", "A"]}, lookup)
    assert reward["first"] >= MIN_DIFFICULTY


def test_get_project_reward_second_scales_with_first():
    a = make_animal("A", level=1)
    lookup = make_lookup(a)

    small = get_project_reward({"animals": ["A", "A", "A"]}, lookup)
    large_entries = ["A"] * 8
    large = get_project_reward({"animals": large_entries}, lookup)

    assert large["first"] > small["first"]
    assert large["second"] >= small["second"]
