import os
from openpyxl import load_workbook

# Columns the rest of the app assumes exist and are non-empty for every
# animal - everything else (water_type, unlock_group, etc.) already has a
# safe default below if missing.
REQUIRED_ANIMAL_COLUMNS = ["name", "type", "level", "tile", "tile_cost", "pack"]

# base = base game, shores = New Shores expansion, additional = Additional
# Species expansion. Used both to validate the 'pack' column here and to
# build the pack-selection checkboxes in the GUI.
VALID_PACKS = ["base", "shores", "additional"]


def _read_rows(path):
    """Yields (excel_row_number, {column_name: cell_value}) for each data
    row - every row dict has every header column as a key (even when the
    cell itself is blank, i.e. None), matching how a pandas row exposes
    every DataFrame column via `in`/`.get()` regardless of blank cells."""
    wb = load_workbook(path, read_only=True, data_only=True)
    ws = wb.active

    rows = ws.iter_rows(values_only=True)
    header = [str(c).strip() if c is not None else "" for c in next(rows)]

    for excel_row, values in enumerate(rows, start=2):
        yield excel_row, dict(zip(header, values))


def load_animals(path):
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Animals file not found: {path}\n"
            "Check that the file exists at that path."
        )

    try:
        rows = list(_read_rows(path))
    except Exception as e:
        raise ValueError(f"Could not read animals file '{path}': {e}") from e

    columns = list(rows[0][1].keys()) if rows else []

    missing = [c for c in REQUIRED_ANIMAL_COLUMNS if c not in columns]
    if missing:
        raise ValueError(
            f"Animals file '{path}' is missing required column(s): "
            f"{', '.join(missing)}.\n"
            f"Columns found: {', '.join(str(c) for c in columns)}"
        )

    animals = []

    for excel_row, row in rows:

        # A blank cell reads back as None here - without this check a
        # blank name/type cell silently becomes an animal named "None"
        # instead of failing loudly.
        if row.get("name") is None or not str(row["name"]).strip():
            raise ValueError(f"Animals file '{path}', row {excel_row}: 'name' is empty.")

        if row.get("type") is None or not str(row["type"]).strip():
            raise ValueError(
                f"Animals file '{path}', row {excel_row} ('{row['name']}'): 'type' is empty."
            )

        pack = str(row["pack"]).strip().lower() if row.get("pack") is not None else ""
        if pack not in VALID_PACKS:
            raise ValueError(
                f"Animals file '{path}', row {excel_row} ('{row['name']}'): "
                f"'pack' is '{pack or '<empty>'}', expected one of {VALID_PACKS}."
            )

        # --- NORMALIZE BIOME ---
        raw_biome = str(row.get("biome") or "").lower()

        raw_biome = raw_biome.replace("dry dessert", "desert")
        raw_biome = raw_biome.replace("drydessert", "desert")  # safety

        habitats = set(
            x.strip()
            for x in raw_biome.split(";")
            if x.strip()
        )

        # --- GROUPS ---
        raw_group = str(row.get("group") or "").lower()

        groups = set(
            x.strip()
            for x in raw_group.split(";")
            if x.strip()
        )

        # --- TAGS ---
        raw_tags = str(row.get("tags") or "").lower()

        tags = set(
            x.strip()
            for x in raw_tags.split(";")
            if x.strip()
        )

        animals.append({
            "name": str(row["name"]).strip(),
            "type": str(row["type"]).strip(),
            "pack": pack,

            "level": int(row["level"]) if row.get("level") is not None else 0,

            # Used by is_valid_or_pair to keep cospecies OR pairs the same
            # size (e.g. a small OR shouldn't pair with a big one).
            "size": str(row["size"]).strip().lower() if row.get("size") is not None else None,

            "habitats": habitats,
            "groups": groups,
            "tags": tags,

            # --- CORE ---
            "tile": int(row["tile"]) if row.get("tile") is not None else 1,
            "tile_cost": int(row["tile_cost"]) if row.get("tile_cost") is not None else 0,
            "min_individual": int(row["min_individual"]) if row.get("min_individual") is not None else 1,

            # --- WATER SYSTEM ---
            "water_type": str(row.get("water_type") or "none").strip().lower(),
            "min_free_tiles": int(row["min_free_tiles"]) if row.get("min_free_tiles") is not None else 0,
            "water_tiles_needed": int(row["water_tiles_needed"]) if row.get("water_tiles_needed") is not None else 0,

            # --- REQUIREMENTS ---
            "unlock_group": str(row["unlock_group"]).strip().lower()
            if row.get("unlock_group") is not None else None,

            "unlock_count": int(row["unlock_count"])
            if row.get("unlock_count") is not None else 0,

            # --- FLAGS ---
            "special": bool(row["special"]) if row.get("special") is not None else False,
        })

    return animals
