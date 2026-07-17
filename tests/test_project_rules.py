from core.project_rules import (
    can_use_animal_global,
    can_add_lvl3,
    can_add_special,
    is_valid_or_pair,
    has_similarity,
    can_apply_or,
    matches_theme,
    matches_special_theme,
    is_within_difficulty_range,
    tier_for_difficulty,
    RANGES,
    MAX_LVL3_PER_PROJECT,
    MAX_SPECIAL_PER_PROJECT,
    MAX_OR_PER_PROJECT,
    MAX_MULTIPLIER_PER_PROJECT,
    OR_CHANCE,
    SECOND_OR_CHANCE,
    MULTIPLIER_CHANCE,
    SECOND_MULTIPLIER_CHANCE,
)


def make_animal(name="Animal", type_="main", level=1, special=False,
                 habitats=None, groups=None, tags=None, size=None):
    return {
        "name": name,
        "type": type_,
        "level": level,
        "special": special,
        "habitats": habitats or set(),
        "groups": groups or set(),
        "tags": tags or set(),
        "size": size,
    }


# --- can_use_animal_global ---

def test_special_animal_capped_at_one_use():
    a = make_animal(special=True)
    assert can_use_animal_global(a, 0) is True
    assert can_use_animal_global(a, 1) is False


def test_level3_animal_capped_at_one_use():
    a = make_animal(level=3)
    assert can_use_animal_global(a, 0) is True
    assert can_use_animal_global(a, 1) is False


def test_regular_animal_capped_at_two_uses():
    a = make_animal(level=1)
    assert can_use_animal_global(a, 0) is True
    assert can_use_animal_global(a, 1) is True
    assert can_use_animal_global(a, 2) is False


def test_can_add_lvl3_respects_max_per_project():
    assert can_add_lvl3(MAX_LVL3_PER_PROJECT - 1) is True
    assert can_add_lvl3(MAX_LVL3_PER_PROJECT) is False


def test_can_add_special_respects_max_per_project():
    assert can_add_special(MAX_SPECIAL_PER_PROJECT - 1) is True
    assert can_add_special(MAX_SPECIAL_PER_PROJECT) is False


# --- is_valid_or_pair ---

def test_or_pair_rejects_mismatched_type():
    base = make_animal(type_="main")
    alt = make_animal(type_="cospecies")
    assert is_valid_or_pair(base, alt) is False


def test_or_pair_rejects_lvl3_main():
    base = make_animal(type_="main", level=3)
    alt = make_animal(type_="main", level=1)
    assert is_valid_or_pair(base, alt) is False


def test_or_pair_rejects_special_main():
    base = make_animal(type_="main", special=True)
    alt = make_animal(type_="main", level=1)
    assert is_valid_or_pair(base, alt) is False


def test_or_pair_accepts_similar_mains():
    base = make_animal(type_="main", level=1)
    alt = make_animal(type_="main", level=2)
    assert is_valid_or_pair(base, alt) is True


def test_or_pair_cospecies_requires_matching_size():
    base = make_animal(type_="cospecies", size="small")
    alt_same = make_animal(type_="cospecies", size="small")
    alt_diff = make_animal(type_="cospecies", size="large")
    assert is_valid_or_pair(base, alt_same) is True
    assert is_valid_or_pair(base, alt_diff) is False


# --- has_similarity ---

def test_has_similarity_true_when_groups_overlap():
    base = make_animal(groups={"predator"})
    alt = make_animal(groups={"predator", "bird"})
    assert has_similarity(base, alt) is True


def test_has_similarity_true_when_tags_overlap():
    base = make_animal(tags={"carnivore"})
    alt = make_animal(tags={"carnivore"})
    assert has_similarity(base, alt) is True


def test_has_similarity_false_when_nothing_shared():
    base = make_animal(groups={"predator"}, tags={"carnivore"})
    alt = make_animal(groups={"ungulate"}, tags={"herbivore"})
    assert has_similarity(base, alt) is False


# --- can_apply_or (deterministic branches only - the "how often" part is
# randomized and not worth asserting on without a live run) ---

def test_can_apply_or_false_at_or_limit():
    project = ["A OR B", "C OR D"][:MAX_OR_PER_PROJECT]
    assert can_apply_or(project, RANGES["hard"][1]) is False


# --- OR_CHANCE / MULTIPLIER_CHANCE hierarchy ---
# OR discounts difficulty so it should get MORE common as tier goes up
# (easy doesn't need it); a multiplier adds difficulty so it should get
# LESS common as tier goes up (easy benefits most). Mirrors the
# strictly-increasing SLOT_WEIGHTS hierarchy in scoring/project_rewards.py.

def test_or_chance_increases_with_tier():
    assert OR_CHANCE["easy"] < OR_CHANCE["medium"] < OR_CHANCE["hard"]
    assert SECOND_OR_CHANCE["easy"] < SECOND_OR_CHANCE["medium"] < SECOND_OR_CHANCE["hard"]


def test_multiplier_chance_decreases_with_tier():
    assert MULTIPLIER_CHANCE["easy"] > MULTIPLIER_CHANCE["medium"] > MULTIPLIER_CHANCE["hard"]
    assert SECOND_MULTIPLIER_CHANCE["easy"] > SECOND_MULTIPLIER_CHANCE["medium"] > SECOND_MULTIPLIER_CHANCE["hard"]


def test_second_chance_always_rarer_than_first():
    for tier in ("easy", "medium", "hard"):
        assert SECOND_OR_CHANCE[tier] < OR_CHANCE[tier]
        assert SECOND_MULTIPLIER_CHANCE[tier] < MULTIPLIER_CHANCE[tier]


# --- matches_theme / matches_special_theme ---

def test_matches_theme_habitat():
    a = make_animal(habitats={"savannah"})
    assert matches_theme(a, "habitat", "savannah") is True
    assert matches_theme(a, "habitat", "jungle") is False


def test_matches_theme_group_and_tag():
    a = make_animal(groups={"predator"}, tags={"carnivore"})
    assert matches_theme(a, "group", "predator") is True
    assert matches_theme(a, "tag", "carnivore") is True


def test_matches_special_theme_true_for_non_special():
    a = make_animal(special=False)
    assert matches_special_theme(a, "group", "predator", 4) is True


def test_matches_special_theme_unrestricted_for_3_animal_projects():
    # No extra restriction at a project size of 3 - any theme it would
    # otherwise qualify for is fine, same as a non-special animal.
    a = make_animal(special=True)
    a["unlock_group"] = "predator"
    assert matches_special_theme(a, "habitat", "savannah", 3) is True
    assert matches_special_theme(a, "tag", "carnivore", 3) is True
    assert matches_special_theme(a, "group", "bird", 3) is True


def test_matches_special_theme_restricted_to_unlock_group_for_larger_projects():
    # For 4+ animals, only its own unlock_group as a *group* theme is
    # allowed - habitat/tag themes are excluded entirely (not just
    # unrestricted), and a mismatched group is excluded too.
    a = make_animal(special=True)
    a["unlock_group"] = "predator"
    assert matches_special_theme(a, "group", "predator", 4) is True
    assert matches_special_theme(a, "group", "bird", 4) is False
    assert matches_special_theme(a, "habitat", "savannah", 4) is False
    assert matches_special_theme(a, "tag", "carnivore", 5) is False


# --- difficulty range / tier helpers ---

def test_is_within_difficulty_range():
    lo, hi = RANGES["medium"]
    assert is_within_difficulty_range(lo, "medium") is True
    assert is_within_difficulty_range(hi, "medium") is True
    assert is_within_difficulty_range(hi + 1, "medium") is False


def test_tier_for_difficulty_matches_ranges_boundaries():
    assert tier_for_difficulty(RANGES["easy"][1]) == "easy"
    assert tier_for_difficulty(RANGES["easy"][1] + 0.01) == "medium"
    assert tier_for_difficulty(RANGES["medium"][1]) == "medium"
    assert tier_for_difficulty(RANGES["medium"][1] + 0.01) == "hard"
