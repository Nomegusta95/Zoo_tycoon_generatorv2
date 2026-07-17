from core.utils import normalize_entry, extract_animal_names, split_or


def test_normalize_entry_strips_trailing_multiplier():
    assert normalize_entry("Zebra 4") == "Zebra"


def test_normalize_entry_leaves_plain_name_alone():
    assert normalize_entry("Zebra") == "Zebra"


def test_normalize_entry_handles_multiword_names():
    assert normalize_entry("Giant Panda") == "Giant Panda"
    assert normalize_entry("Giant Panda 3") == "Giant Panda"


def test_extract_animal_names_expands_or_and_strips_multiplier():
    entries = ["Lion", "Zebra OR Warthog", "Giraffe 2"]
    assert extract_animal_names(entries) == {"Lion", "Zebra", "Warthog", "Giraffe"}


def test_split_or():
    assert split_or("Zebra OR Warthog") == ["Zebra", "Warthog"]
    assert split_or("Lion") == ["Lion"]
