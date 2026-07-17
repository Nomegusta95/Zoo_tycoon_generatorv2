# best_project.py

from core.project_generator import generate_project
import random
from core.utils import extract_animal_names


def extract_theme(project):
    return project.get("theme")


# --- SIMILARITY ---

def extract_names(project):
    return extract_animal_names(project["animals"])


def project_similarity(p1, p2):
    s1 = extract_names(p1)
    s2 = extract_names(p2)

    if not s1 or not s2:
        return 0

    return len(s1 & s2) / len(s1 | s2)


# --- SIMPLE SELECTION ---

def generate_best_project(
    animals,
    usage,
    previous_projects=None,
    attempts=20,
    required_animals=None
):

    candidates = []

    # Build once and reuse across every attempt instead of rebuilding
    # inside generate_project on each call.
    lookup = {a["name"]: a for a in animals}
    usable = [a for a in animals if a["type"] in ("main", "cospecies")]

    for _ in range(attempts):

        p = generate_project(animals, usage.copy(), lookup=lookup, usable=usable)

        if not p:
            continue

        # --- avoid similar animals
        if previous_projects:
            if any(project_similarity(p, prev) > 0.6 for prev in previous_projects):
                continue

        # --- 🚫 NEW: avoid same theme
        if previous_projects:
            p_theme = extract_theme(p)

            if any(extract_theme(prev) == p_theme for prev in previous_projects):
                continue

        candidates.append(p)

    if not candidates:
        # fallback
        for _ in range(5):
            p = generate_project(animals, usage.copy(), lookup=lookup, usable=usable)
            if p:
                return p
        return None

    # -----------------------------
    # 🔥 SCORING (ANY required = strong bias)
    # -----------------------------
    scored = []

    required_set = set(required_animals or [])

    for p in candidates:

        names = extract_names(p)

        # --- how many required animals are included
        required_hits = len(names & required_set)

        # --- PRIMARY RULE:
        # any required animal → big bonus
        has_required = required_hits > 0

        # --- score logic
        score = 0

        if has_required:
            score += 5  # strong boost (presence matters most)

        # small extra reward if multiple appear (but not dominant)
        score += required_hits * 1

        # --- size bonus (very small)
        score += len(names) * 0.1

        scored.append((score, p))

    # sort best → worst
    scored.sort(key=lambda x: x[0], reverse=True)

    best_score = scored[0][0]

    # keep top tier to avoid repetition
    top = [p for s, p in scored if s >= best_score - 1]

    return random.choice(top)