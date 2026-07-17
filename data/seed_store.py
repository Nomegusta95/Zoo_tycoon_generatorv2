import os
import json

# Deliberately NOT using core.utils.resource_path or a __file__-relative
# path here - both resolve to PyInstaller's onefile temp extraction dir
# when running as the packaged .exe, which is wiped on exit. Saved seeds
# need to survive between launches, so they go in a real per-user,
# persistent location instead.
def _user_data_dir():
    base = os.getenv("APPDATA") or os.path.expanduser("~")
    path = os.path.join(base, "ZooGenerator")
    os.makedirs(path, exist_ok=True)
    return path


SAVED_SEEDS_PATH = os.path.join(_user_data_dir(), "saved_seeds.json")


def load_saved_seeds(path=SAVED_SEEDS_PATH):
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def save_seed_entry(entry, path=SAVED_SEEDS_PATH):
    entries = load_saved_seeds(path)
    entries = [e for e in entries if e["name"] != entry["name"]]  # overwrite same-name saves
    entries.append(entry)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2)


def delete_seed_entry(name, path=SAVED_SEEDS_PATH):
    entries = load_saved_seeds(path)
    entries = [e for e in entries if e["name"] != name]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2)
