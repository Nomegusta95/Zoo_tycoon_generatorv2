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
