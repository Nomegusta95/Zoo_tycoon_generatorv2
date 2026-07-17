import random

from core.generator import (
    matches_unlock_group,
    count_matches_in_pool,
    validate_level_counts,
    enforce_pool_requirements,
    LEVEL_COUNTS,
)


def make_animal(name, level=0, groups=None, unlock_group=None, unlock_count=0,
                 special=False, type_="main"):
    return {
        "name": name,
        "level": level,
        "type": type_,
        "groups": groups or set(),
        "unlock_group": unlock_group,
        "unlock_count": unlock_count,
        "special": special,
    }


# --- matches_unlock_group / count_matches_in_pool ---

def test_matches_unlock_group_true_when_no_requirement():
    a = make_animal("A")
    assert matches_unlock_group(a, None) is True
    assert matches_unlock_group(a, "") is True


def test_matches_unlock_group_checks_any_of_multiple_groups():
    a = make_animal("A", groups={"bird"})
    assert matches_unlock_group(a, "predator;bird") is True
    assert matches_unlock_group(a, "predator;reptile") is False


def test_count_matches_in_pool():
    pool = [
        make_animal("A", groups={"predator"}),
        make_animal("B", groups={"bird"}),
        make_animal("C", groups={"predator", "bird"}),
    ]
    assert count_matches_in_pool(pool, "predator") == 2
    assert count_matches_in_pool(pool, "reptile") == 0


# --- validate_level_counts ---

def _build_full_pool():
    pool = []
    for level, count in [(0, LEVEL_COUNTS["level_0"]),
                          (1, LEVEL_COUNTS["level_1"]),
                          (2, LEVEL_COUNTS["level_2"]),
                          (3, LEVEL_COUNTS["level_3"])]:
        for i in range(count):
            pool.append(make_animal(f"L{level}_{i}", level=level))
    return pool


def test_validate_level_counts_true_for_correct_pool():
    assert validate_level_counts(_build_full_pool()) is True


def test_validate_level_counts_false_when_one_level_short():
    pool = _build_full_pool()
    pool.pop()  # remove one level_3 animal
    assert validate_level_counts(pool) is False


# --- enforce_pool_requirements ---

def test_enforce_pool_requirements_noop_when_already_satisfied():
    needer = make_animal("Needer", level=1, unlock_group="predator", unlock_count=1)
    predator = make_animal("Predator", level=1, groups={"predator"})
    selected = [needer, predator]

    result = enforce_pool_requirements(selected, selected)

    assert result == [needer, predator]


def test_enforce_pool_requirements_returns_none_when_no_candidates():
    needer = make_animal("Needer", level=1, unlock_group="unicorn", unlock_count=1)
    filler = make_animal("Filler", level=1)
    selected = [needer, filler]

    result = enforce_pool_requirements(selected, selected)

    assert result is None


def test_enforce_pool_requirements_swaps_in_matching_candidate():
    needer = make_animal("Needer", level=1, unlock_group="special_group", unlock_count=1)
    filler = make_animal("Filler", level=1)
    candidate = make_animal("Candidate", level=1, groups={"special_group"})

    selected = [needer, filler]
    allowed = [needer, filler, candidate]

    random.seed(42)
    result = enforce_pool_requirements(selected, allowed)

    # Filler gets swapped out for Candidate (same level, so LEVEL_COUNTS
    # stays balanced); Needer's requirement is now satisfied.
    assert result == [needer, candidate]
    assert count_matches_in_pool(result, "special_group") >= needer["unlock_count"]
