import pandas as pd
import pytest

from data.data_loader import load_animals
from data.predefined_loader import load_predefined_projects


# --- load_animals ---

def test_load_animals_missing_file_raises(tmp_path):
    missing = tmp_path / "does_not_exist.xlsx"
    with pytest.raises(FileNotFoundError):
        load_animals(str(missing))


def test_load_animals_missing_required_column_raises(tmp_path):
    path = tmp_path / "animals.xlsx"
    # Missing "tile_cost", which is required.
    df = pd.DataFrame([{"name": "Lion", "type": "main", "level": 1, "tile": 1}])
    df.to_excel(path, index=False)

    with pytest.raises(ValueError, match="tile_cost"):
        load_animals(str(path))


def test_load_animals_blank_name_raises(tmp_path):
    path = tmp_path / "animals.xlsx"
    df = pd.DataFrame([{
        "name": "",
        "type": "main",
        "level": 1,
        "tile": 1,
        "tile_cost": 100,
        "pack": "base",
    }])
    df.to_excel(path, index=False)

    with pytest.raises(ValueError, match="'name' is empty"):
        load_animals(str(path))


def test_load_animals_invalid_pack_raises(tmp_path):
    path = tmp_path / "animals.xlsx"
    df = pd.DataFrame([{
        "name": "Lion",
        "type": "main",
        "level": 1,
        "tile": 1,
        "tile_cost": 100,
        "pack": "komodo",
    }])
    df.to_excel(path, index=False)

    with pytest.raises(ValueError, match="'pack'"):
        load_animals(str(path))


def test_load_animals_happy_path_applies_defaults(tmp_path):
    path = tmp_path / "animals.xlsx"
    df = pd.DataFrame([{
        "name": "Lion",
        "type": "main",
        "level": 2,
        "tile": 3,
        "tile_cost": 500,
        "pack": "shores",
        "biome": "Savannah;Dry Dessert",
        "group": "Predator",
        "tags": "Carnivore",
        "special": True,
    }])
    df.to_excel(path, index=False)

    animals = load_animals(str(path))

    assert len(animals) == 1
    a = animals[0]
    assert a["name"] == "Lion"
    assert a["level"] == 2
    assert a["pack"] == "shores"
    assert a["habitats"] == {"savannah", "desert"}  # "dry dessert" normalized
    assert a["groups"] == {"predator"}
    assert a["tags"] == {"carnivore"}
    assert a["special"] is True
    # Columns not present in the sheet fall back to their documented defaults.
    assert a["min_individual"] == 1
    assert a["water_type"] == "none"
    assert a["unlock_group"] is None
    assert a["unlock_count"] == 0


# --- load_predefined_projects ---

def test_load_predefined_projects_missing_file_raises(tmp_path):
    missing = tmp_path / "does_not_exist.xlsx"
    with pytest.raises(FileNotFoundError):
        load_predefined_projects(str(missing))


def test_load_predefined_projects_missing_required_column_raises(tmp_path):
    path = tmp_path / "projects.xlsx"
    df = pd.DataFrame([{"name": "Savage Land"}])  # missing "animals"
    df.to_excel(path, index=False)

    with pytest.raises(ValueError, match="animals"):
        load_predefined_projects(str(path))


def test_load_predefined_projects_blank_animals_raises(tmp_path):
    path = tmp_path / "projects.xlsx"
    df = pd.DataFrame([{"name": "Savage Land", "animals": ""}])
    df.to_excel(path, index=False)

    with pytest.raises(ValueError, match="'animals' is empty"):
        load_predefined_projects(str(path))


def test_load_predefined_projects_happy_path_splits_animals_and_or(tmp_path):
    path = tmp_path / "projects.xlsx"
    df = pd.DataFrame([{
        "name": "Savage Land",
        "animals": "Lion;Zebra OR Warthog;Giraffe",
        "theme": "savannah",
        "theme_type": "habitat",
        "mandatory": "true",
    }])
    df.to_excel(path, index=False)

    projects = load_predefined_projects(str(path))

    assert len(projects) == 1
    p = projects[0]
    assert p["name"] == "Savage Land"
    assert p["animals"] == ["Lion", "Zebra OR Warthog", "Giraffe"]
    assert p["theme"] == "savannah"
    assert p["theme_type"] == "habitat"
    assert p["mandatory"] is True
