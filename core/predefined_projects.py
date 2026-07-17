# NOTE: predefined projects are actually loaded via
# data.predefined_loader.load_predefined_projects (this module previously
# had its own duplicate, unused copy of that loader — removed).

from core.utils import normalize_entry, sort_project_animals
from scoring.project_rewards import compute_difficulty


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

        project_obj = {
            "name": p["name"],
            "animals": sort_project_animals(p["animals"], lookup),
            "theme": p["theme"] or "Mixed",
            "theme_type": p["theme_type"] or "group",
            "difficulty": difficulty,
            "tier": "predefined",
            "source": "predefined"
        }

        if p.get("mandatory"):
            mandatory_projects.append(project_obj)
        else:
            optional_projects.append(project_obj)

    return mandatory_projects, optional_projects

