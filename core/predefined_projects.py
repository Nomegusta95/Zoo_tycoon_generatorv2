# NOTE: predefined projects are actually loaded via
# data.predefined_loader.load_predefined_projects (this module previously
# had its own duplicate, unused copy of that loader — removed).

from collections import Counter

from core.utils import normalize_entry, sort_project_animals
from core.project_naming import extract_biomes, extract_groups
from scoring.project_rewards import compute_difficulty


def _derive_theme(animals_entries, lookup):
    """Predefined projects (real board-game locations like "Serengeti")
    don't have a natural single habitat/group/tag theme the way a
    procedurally-generated project does, and the source spreadsheet
    leaves theme/theme_type blank for every one of them - derive a real
    theme from the project's own animals (their most common shared
    habitat, or group if no habitat is shared) instead of falling back
    to a made-up "Mixed" value that has no matching badge image and
    silently rendered no badge at all."""
    habitats = Counter(extract_biomes(animals_entries, lookup))
    if habitats:
        return habitats.most_common(1)[0][0], "habitat"

    groups = Counter(extract_groups(animals_entries, lookup))
    if groups:
        return groups.most_common(1)[0][0], "group"

    return "Mixed", "group"


def normalize_name(entry):
    return normalize_entry(entry.strip()).lower()


def is_project_valid(project, game_animals):

    pool_names = {a["name"].strip().lower() for a in game_animals}

    for entry in project["animals"]:

        parts = entry.split(" OR ")

        valid_option = False

        for p in parts:
            name = normalize_name(p)

            if name in pool_names:
                valid_option = True
                break

        if not valid_option:
            return False

    return True

def build_predefined_projects(game_animals, lookup, predefined):


    mandatory_projects = []
    optional_projects = []

    for p in predefined:

        if not is_project_valid(p, game_animals):
            continue

        difficulty = compute_difficulty(p["animals"], lookup)

        theme, theme_type = p["theme"], p["theme_type"]
        if not theme:
            theme, theme_type = _derive_theme(p["animals"], lookup)

        project_obj = {
            "name": p["name"],
            "animals": sort_project_animals(p["animals"], lookup),
            "theme": theme,
            "theme_type": theme_type,
            "difficulty": difficulty,
            "tier": "predefined",
            "source": "predefined"
        }

        if p.get("mandatory"):
            mandatory_projects.append(project_obj)
        else:
            optional_projects.append(project_obj)

    return mandatory_projects, optional_projects

