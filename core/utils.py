import sys
import os

def normalize_entry(entry: str) -> str:
    tokens = entry.split()
    if tokens and tokens[-1].isdigit():
        tokens = tokens[:-1]
    return " ".join(tokens)


def extract_animal_names(entries):
    names = set()

    for entry in entries:
        parts = entry.split(" OR ")
        for p in parts:
            names.add(normalize_entry(p))

    return names


def split_or(entry):
    return entry.split(" OR ")


def _animal_sort_rank(entry, lookup):
    """main level 1/2/3 first (in that order), cospecies last. OR options
    are guaranteed the same type (see is_valid_or_pair), so the first
    option is representative of the whole slot. An entry missing from
    lookup sorts last rather than raising, to fail visibly-but-safely."""
    base = split_or(entry)[0]
    a = lookup.get(normalize_entry(base))
    if not a:
        return 99
    if a["type"] != "main":
        return 4
    return a.get("level", 0)


def sort_project_animals(entries, lookup):
    """Order a project's animal entries: level 1, level 2, level 3, then
    cospecies last - purely a display concern, doesn't affect difficulty,
    naming, or usage tracking, all of which are already order-independent."""
    return sorted(entries, key=lambda e: _animal_sort_rank(e, lookup))



def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)