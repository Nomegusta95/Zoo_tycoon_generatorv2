from core.generator import generate_game
from core.best_project import generate_best_project
from core.predefined_projects import build_predefined_projects
from scoring.project_rewards import get_project_reward
from scoring.project_cost import expand_entry
from core.project_rules import update_usage
from core.utils import extract_animal_names


def extract_names(project):
    return extract_animal_names(project["animals"])


def generate_full_game(animals, required, predefined, locked_projects=None, game_animals=None, lookup=None, mode="freeform"):
    """locked_projects: optional {slot_index: project_dict} - those slots
    are kept exactly as given and only the remaining slots are (re)filled.
    game_animals/lookup: optional pool to reuse instead of sampling a new
    one - required when locking anything, since a locked project's animals
    only make sense against the same pool they were drawn from.
    mode: "freeform" (today's behavior) or "restrictive" (every habitat
    active, plus per-habitat/per-group species floors) - only matters
    when actually building a fresh pool, not when reusing one."""

    locked_projects = locked_projects or {}

    if game_animals is None or lookup is None:
        game_pool, game_animals = generate_game(animals, required, mode=mode)
        lookup = {a["name"]: a for a in game_animals}

    usage = {}
    game = [None] * 5

    for idx, p in locked_projects.items():
        if 0 <= idx < 5:
            game[idx] = p
            update_usage(p["animals"], usage, expand_entry)

    # Predefined projects already sitting in a locked slot must not be
    # placed again in another slot - build_predefined_projects has no idea
    # about locks, so it'll happily offer the same one back.
    locked_predefined_names = {
        p.get("name") for p in game if p and p.get("source") == "predefined"
    }

    mandatory_projects, optional_projects = build_predefined_projects(
        game_animals,
        lookup,
        predefined
    )

    mandatory_projects.sort(key=lambda p: p["difficulty"], reverse=True)

    def empty_slots():
        return [i for i in range(5) if game[i] is None]

    # --- ADD MANDATORY ---
    for p in mandatory_projects:
        if not empty_slots():
            break

        if p.get("name") in locked_predefined_names:
            continue

        names = extract_names(p)

        if any(usage.get(name, 0) >= 2 for name in names):
            continue

        p["reward"] = get_project_reward(p, lookup)
        game[empty_slots()[0]] = p
        update_usage(p["animals"], usage, expand_entry)

    # --- GENERATE REST ---
    while empty_slots():

        previous_projects = [p for p in game if p is not None]

        p = generate_best_project(
            game_animals,
            usage,
            previous_projects=previous_projects,
            attempts=10,
            required_animals=required
        )

        if not p:
            break

        names = extract_names(p)

        if any(usage.get(name, 0) >= 2 for name in names):
            continue

        p["reward"] = get_project_reward(p, lookup)
        game[empty_slots()[0]] = p
        update_usage(p["animals"], usage, expand_entry)

    # fallback
    for i in empty_slots():
        game[i] = {
            "name": "Failed Project",
            "animals": [],
            "theme": "None",
            "theme_type": "none",
            "difficulty": 0
        }

    return game, game_animals, lookup