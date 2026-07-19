# theme_data.py
#
# Pure presentation data shared between the desktop GUI (gui/app.py,
# CustomTkinter) and the web GUI (streamlit_app.py, Streamlit) - no
# tkinter/customtkinter/streamlit import here, so either frontend can pull
# from this one place without dragging in the other's dependencies.

# theme/group/tag value -> badge image filename under assets/images/badges/
BADGE_MAP = {
    "savannah": "savannah.png",
    "africa": "africa.png",
    "jungle": "jungle.png",
    "desert": "desert.png",
    "mountain": "mountain.png",
    "marsupial": "marsupial.png",
    "bird": "bird.png",
    "primate": "primate.png",
    "ungulate": "ungulate.png",
    "predator": "predator.png",
    "aquatic": "aquatic.png",
    "fish": "fish.png",
    "reptile": "reptile.png",
    "water": "water.png",
    "australia": "australia.png",
    "europe": "europe.png",
    "asia": "asia.png",
    "north america": "north_america.png",
    "south america": "south_america.png",
    "arctic": "arctic.png",
    "carnivore": "carnivore.png",
    "herbivore": "herbivore.png",
    "omnivore": "omnivore.png",
    "herd": "herd.png",
    "pack": "herd.png",
    "solitary": "solitary.png",
    "arid": "arid.png",
    "tropical": "tropical.png",
    "temperate": "temperate.png",
    "cold": "cold.png",
    "wetland": "wetland.png",
    "ocean": "ocean.png",
    "ground": "ground.png",
    "flying": "flying.png",
    "swimming": "swimming.png",
    "climbing": "climbing.png",
    "tundra": "tundra.png",
    "endangered": "endangered.png",
    "tiny": "tiny.png",
    "egg-laying": "egg-laying.png",
    "venomous": "venomous.png",
    "friendly": "friendly.png",
    "nocturnal": "nocturnal.png",
    "migratory": "migratory.png",
    "burrowing": "burrowing.png",
    "ancient": "ancient.png",
    "horned": "horned.png",
    "large": "large.png",
}

# level-3 animal name (lowercase) -> its own badge image filename under
# assets/images/badges/ - level-3s are the game's rarest species, so any
# project that contains one gets that animal's own badge in place of the
# usual theme/symbiosis badge(s).
LEVEL3_ANIMAL_BADGES = {
    "arabian oryx": "arabian_oryx.png",
    "bearded vulture": "bearded_vulture.png",
    "black-footed ferret": "black-footed_ferret.png",
    "bornean orangutan": "bornean_orangutan.png",
    "golden lion tamarin": "golden_lion_tamarin.png",
    "green sea turtle": "green_sea_turtle.png",
    "madagascar pochard": "madagascar_pochard.png",
    "northern bald ibis": "northern_bald_ibis.png",
    "przewalski's horse": "przewalskis_horse.png",
    "tasmanian devil": "tasmanian_devil.png",
    "zebra shark": "zebra_shark.png",
}


def project_level3_badge_values(project, lookup):
    """Distinct level-3 animal names (original casing, sorted) this
    project contains - each is looked up in LEVEL3_ANIMAL_BADGES the same
    way a theme value is looked up in BADGE_MAP, by whichever frontend is
    rendering the badge row."""
    from core.utils import extract_animal_names

    names = extract_animal_names(project.get("animals", []))
    return sorted(n for n in names if lookup.get(n, {}).get("level") == 3)


PACK_LABELS = {
    "base": "Base game",
    "shores": "New Shores",
    "additional": "Additional Species",
}

# (display label, internal filter key) - used by the animal-picker filter
FILTERS = [
    ("All", "all"),
    ("Lvl1", "level1"),
    ("Lvl2", "level2"),
    ("Lvl3", "level3"),
    ("CoSp", "cospecies"),
    ("Spec", "special"),
]

GROUP_ORDER = ["level1", "level2", "level3", "cospecies"]
GROUP_TITLES = {
    "level1": "Level 1",
    "level2": "Level 2",
    "level3": "Level 3",
    "cospecies": "Cospecies",
}

TIER_LABELS = {
    "easy": "Easy",
    "medium": "Medium",
    "hard": "Hard",
    "predefined": "Mandatory",
    "basic": "Basic",
}


def average_badge_color(path):
    """Average RGB (0-255 ints) of the non-transparent pixels in a badge
    image at the given path - used to tint a project card's background
    to roughly match its badge. Returns None if the image can't be read
    or is fully transparent. Pillow-only (no tkinter/streamlit), so both
    frontends can call this with their own resolved badge file path."""
    from PIL import Image

    try:
        img = Image.open(path).convert("RGBA")
    except Exception:
        return None

    r_total = g_total = b_total = count = 0
    for r, g, b, a in img.getdata():
        if a < 16:
            continue
        r_total += r
        g_total += g
        b_total += b
        count += 1

    if count == 0:
        return None
    return (r_total // count, g_total // count, b_total // count)
