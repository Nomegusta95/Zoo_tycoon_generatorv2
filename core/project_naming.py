# project_naming.py

import random
from scoring.project_cost import expand_entry
def normalize_tag(value):
    return value.strip().lower()

def normalize_biome(value):
    value = value.strip().lower()

    value = value.replace("dry dessert", "desert")
    value = value.replace("drydessert", "desert")

    return value
def normalize_group(value):
    value = value.strip().lower()

    # take primary group only
    if ";" in value:
        value = value.split(";")[0]

    return value

BIOME_BASE = {
    "savannah": [
        "Golden Plains",
        "Savannah Expanse",
        "Sunburnt Grasslands",
        "Endless Savanna",
        "Amber Plains",
        "Dryland Horizon",
        "Great Grazing Fields",
        "Savanna Heartlands",
        "Wild Grass Expanse",
        "Dustwind Plains"
    ],

    "jungle": [
        "Emerald Jungle",
        "Tropical Wilds",
        "Dense Rainforest",
        "Verdant Canopy",
        "Jungle Depths",
        "Green Labyrinth",
        "Overgrown Wilds",
        "Canopy Realm",
        "Primal Jungle",
        "Living Rainforest"
    ],

    "tundra": [
        "Frozen Expanse",
        "Icy Frontier",
        "Arctic Wastes",
        "Glacial Plains",
        "Frostbound Lands",
        "Permafrost Expanse",
        "Northern Wilds",
        "Icewind Tundra",
        "Snowbound Frontier",
        "Frozen Barrens"
    ],

    "mountain": [
        "Highland Peaks",
        "Rocky Highlands",
        "Mountain Stronghold",
        "Craggy Heights",
        "Alpine Wilds",
        "Stonebound Peaks",
        "Skyreach Mountains",
        "Rugged Highlands",
        "Cliffside Realm",
        "Granite Heights"
    ],

    "water": [
        "Open Waters",
        "Ocean Realm",
        "Blue Expanse",
        "Endless Sea",
        "Marine Domain",
        "Deepwater Frontier",
        "Crystal Waters",
        "Oceanic Wilds",
        "Tidal Expanse",
        "Great Blue"
    ],

    "desert": [
        "Endless Sands",
        "Desert Expanse",
        "Arid Wastes",
        "Sunscorched Dunes",
        "Golden Desert",
        "Dryland Expanse",
        "Burning Sands",
        "Dune Sea",
        "Harsh Desertlands",
        "Scorched Horizon"
    ],
}

GROUP_BASE = {
    "predator": [
        "Predator Grounds",
        "Hunters' Domain",
        "Apex Territory",
        "Carnivore Stronghold",
        "Stalkers' Realm",
        "Dominion of Hunters",
        "Savage Domain",
        "Predatory Frontier",
        "Alpha Territory",
        "Fangs of the Wild"
    ],

    "ungulate": [
        "Grazing Lands",
        "Herd Plains",
        "Migratory Fields",
        "Grazers' Domain",
        "Great Herdlands",
        "Open Grazing Territory",
        "Roaming Herd Grounds",
        "Pasture Expanse",
        "Grassland Collective",
        "Herd Migration Zone"
    ],

    "bird": [
        "Aerial Realm",
        "Sky Dominion",
        "Wings of the Sky",
        "Avian Territory",
        "Flock Skies",
        "Skyborne Domain",
        "Open Sky Realm",
        "Flight Territory",
        "Windswept Skies",
        "Avian Collective"
    ],

    "primate": [
        "Canopy Society",
        "Jungle Kin",
        "Primate Collective",
        "Treebound Dominion",
        "Forest Kinship",
        "Canopy Network",
        "Primate Territory",
        "Climbing Collective",
        "Tribal Canopy",
        "Branchland Society"
    ],

    "reptile": [
        "Scaled Dominion",
        "Cold-Blooded Realm",
        "Reptilian Territory",
        "Scaled Stronghold",
        "Ancient Scale Domain",
        "Reptile Frontier",
        "Silent Scale Lands",
        "Cold-Blooded Domain",
        "Reptilian Collective",
        "Scalebound Territory"
    ],

    "aquatic": [
        "Aquatic Realm",
        "Life Beneath Waves",
        "Marine Domain",
        "Oceanic Collective",
        "Deepwater Territory",
        "Aquatic Frontier",
        "Submerged Realm",
        "Tidebound Domain",
        "Waterborne Life",
        "Aquatic Expanse"
    ],

    "marsupial": [
        "Outback Colonies",
        "Pouchland",
        "Marsupial Territory",
        "Outback Domain",
        "Pouchkin Collective",
        "Hopper Grounds",
        "Marsupial Frontier",
        "Outback Kinship",
        "Pouchbound Lands",
        "Colonial Outback"
    ],

    "fish": [
        "Shoaling Waters",
        "Finned Domain",
        "Current Runners",
        "Reef Shoal",
        "Silver Current",
        "Deepwater Shoal",
        "School of the Deep",
        "Tidal Current Collective",
        "Fin and Scale Territory",
        "Drifting Shoal"
    ],
}

TAG_BASE = {

    # --- MOVEMENT ---
    "flying": [
        "Sky Dominion",
        "Aerial Expansion",
        "Wings of the Sky",
        "Skyborne Initiative",
        "Flight Ascendancy",
        "Aerial Supremacy",
        "Open Skies Program",
        "Windborne Expansion"
    ],

    "swimming": [
        "Aquatic Expansion",
        "Oceanic Life",
        "Submerged Initiative",
        "Tideborne Growth",
        "Marine Expansion",
        "Deepwater Program",
        "Current Dominance",
        "Aquatic Proliferation"
    ],

    "ground": [
        "Terrestrial Expansion",
        "Land Dominance",
        "Ground Control",
        "Surface Expansion",
        "Earthbound Initiative",
        "Landfront Expansion",
        "Terra Dominion",
        "Continental Spread"
    ],

    "climbing": [
        "Canopy Expansion",
        "Vertical Dominion",
        "Climbing Initiative",
        "Arboreal Expansion",
        "Canopy Network",
        "Treebound Growth",
        "Vertical Territory",
        "Branchland Expansion"
    ],

    # --- SOCIAL ---
    "herd": [
        "Great Migration",
        "Herd Convergence",
        "Mass Movement",
        "Herd Expansion",
        "Migration Initiative",
        "Collective Grazing",
        "Roaming Herds",
        "Unified Migration"
    ],

    "pack": [
        "Pack Tactics",
        "Coordinated Hunt",
        "Pack Dominance",
        "Alpha Strategy",
        "Hunting Collective",
        "Pack Expansion",
        "Cooperative Predation",
        "Pack Initiative"
    ],

    "solitary": [
        "Silent Territories",
        "Lone Domain",
        "Isolated Expansion",
        "Solitary Control",
        "Independent Survival",
        "Loner's Program",
        "Territorial Isolation",
        "Shadow Domain"
    ],

    # --- STATUS ---
    "endangered": [
        "Last Sanctuary",
        "Fragile Existence",
        "Critical Survival",
        "Extinction Watch",
        "Recovery Initiative",
        "Final Refuge",
        "Preservation Program",
        "Endangered Protection"
    ],

    # --- ENVIRONMENT ---
    "cold": [
        "Frozen Survival",
        "Icy Adaptation",
        "Cold Resistance",
        "Frostbound Expansion",
        "Polar Adaptation",
        "Cryo Survival",
        "Glacial Expansion",
        "Winter Dominance"
    ],

    "tropical": [
        "Tropical Proliferation",
        "Jungle Growth",
        "Equatorial Expansion",
        "Rainforest Surge",
        "Humid Expansion",
        "Tropical Dominance",
        "Green Zone Growth",
        "Canopy Expansion Program"
    ],

    "arid": [
        "Desert Survival",
        "Harsh Existence",
        "Arid Adaptation",
        "Drought Resistance",
        "Dryland Expansion",
        "Heat Survival",
        "Desert Dominance",
        "Scarcity Adaptation"
    ],

    "temperate": [
        "Temperate Expansion",
        "Balanced Ecosystem",
        "Seasonal Stability",
        "Moderate Growth",
        "Temperate Adaptation",
        "Stable Expansion",
        "Climate Balance",
        "Ecosystem Harmony"
    ],

    "wetland": [
        "Wetland Expansion",
        "Marsh Ecosystem",
        "Floodplain Growth",
        "Swamp Expansion",
        "Wetland Adaptation",
        "Delta Expansion",
        "Shallow Water Ecosystem",
        "Marshland Initiative"
    ],

    "ocean": [
        "Oceanic Expansion",
        "Deep Sea Domain",
        "Marine Dominance",
        "Ocean Expansion",
        "Pelagic Growth",
        "Deepwater Initiative",
        "Oceanic Territory",
        "Sea Expansion Program"
    ],

    # --- DIET ---
    "carnivore": [
        "Predator Dominance",
        "Hunters' Expansion",
        "Carnivore Supremacy",
        "Predatory Growth",
        "Apex Expansion",
        "Hunting Dominance",
        "Meat Chain Control",
        "Predator Initiative"
    ],

    "herbivore": [
        "Grazing Expansion",
        "Herbivore Proliferation",
        "Plant-Based Growth",
        "Grazing Dominance",
        "Herbivore Expansion",
        "Vegetation Cycle",
        "Green Chain Expansion",
        "Foraging Initiative"
    ],

    "omnivore": [
        "Adaptive Expansion",
        "Dietary Flexibility",
        "Omnivore Growth",
        "Balanced Feeding",
        "Flexible Survival",
        "Adaptive Feeding",
        "Generalist Expansion",
        "Mixed Diet Dominance"
    ],

    # --- REGIONS ---
    "africa": [
        "African Expanse",
        "Heart of Africa",
        "Savanna Core",
        "African Wildlands",
        "Central Africa Initiative",
        "African Expansion",
        "Equatorial Africa",
        "Southern Wilds"
    ],

    "asia": [
        "Asian Wilderness",
        "Eastern Expanse",
        "Asian Frontier",
        "Oriental Wilds",
        "Asian Expansion",
        "Eastern Habitat",
        "Continental Asia",
        "Far East Initiative"
    ],

    "europe": [
        "European Frontier",
        "Old World Habitat",
        "European Expansion",
        "Western Wilds",
        "Continental Europe",
        "European Ecosystem",
        "Old Continent Program",
        "Northern Europe Zone"
    ],

    "north america": [
        "Northern Frontier",
        "American Wilderness",
        "Northland Expansion",
        "Continental North",
        "Northern Wilds",
        "North America Initiative",
        "Frontier Expansion",
        "American Habitat"
    ],

    "south america": [
        "Amazonian Realm",
        "South Wilds",
        "Southern Expansion",
        "Amazon Expansion",
        "Southland Ecosystem",
        "Tropical South",
        "South America Initiative",
        "Rainforest Core"
    ],

    "australia": [
        "Outback Expansion",
        "Australian Wilds",
        "Outback Frontier",
        "Southern Expanse",
        "Australian Ecosystem",
        "Outback Initiative",
        "Dryland Australia",
        "Island Expansion"
    ],

    "arctic": [
        "Arctic Survival",
        "Frozen North",
        "Polar Expansion",
        "Arctic Frontier",
        "North Pole Ecosystem",
        "Icebound Expansion",
        "Polar Initiative",
        "Extreme Cold Zone"
    ],

    # --- EGG-LAYING ---
    "egg-laying": [
        "Egg Preservation",
        "Nesting Initiative",
        "Brood Expansion",
        "Hatchery Program",
        "Incubation Protocol",
        "Nesting Grounds",
        "Life from the Shell"
    ],

    # --- FRIENDLY ---
    "friendly": [
        "Harmony Initiative",
        "Companion Program",
        "Peaceful Encounters",
        "Kindred Spirits",
        "Social Harmony",
        "Friendly Relations",
        "Animal Ambassadors"
    ],

    # --- TINY ---
    "tiny": [
        "Small Wonders",
        "Miniature Marvels",
        "Pocket Wildlife",
        "Tiny Treasures",
        "Microfauna Initiative",
        "Little Legends",
        "Hidden Gems",
        "Small but Mighty"
    ],

    # --- VENOMOUS ---
    "venomous": [
        "Venom Research",
        "Toxic Frontiers",
        "Deadly Adaptations",
        "Poison Protocol",
        "Venom Mastery",
        "Toxic Evolution",
        "Nature's Arsenal",
        "Lethal Precision"
    ],

    # --- NOCTURNAL ---
    "nocturnal": [
        "Moonlit Initiative",
        "Nightfall Expansion",
        "Twilight Dominion",
        "Shadow Ecology",
        "Midnight Adaptation",
        "Lunar Activity",
        "Nightwatch Program",
        "Darkness Ascendancy"
    ],

    # --- LARGE ---
    "large": [
        "Titan Initiative",
        "Giants of Nature",
        "Colossal Expansion",
        "Megafauna Project",
        "Titanic Growth",
        "Grand Species Program",
        "Monumental Wildlife",
        "Great Beasts Initiative"
    ],

    # --- MIGRATORY ---
    "migratory": [
        "Great Migration",
        "Seasonal Journeys",
        "Migration Corridors",
        "Endless Horizons",
        "Nomadic Expansion",
        "Journey Beyond",
        "Pathfinder Initiative",
        "Crosswinds Program"
    ],

    # --- BURROWING ---
    "burrowing": [
        "Underground Network",
        "Hidden Burrows",
        "Subterranean Expansion",
        "Earthworks Initiative",
        "Tunnel Systems",
        "Below the Surface",
        "Excavation Program",
        "Underground Dominion"
    ],

    # --- ANCIENT ---
    "ancient": [
        "Living Relics",
        "Ancient Lineages",
        "Prehistoric Legacy",
        "Primeval Origins",
        "Echoes of Time",
        "Legacy of Ages",
        "Forgotten Kingdoms",
        "Timeless Survivors"
    ],

    # --- HORNED ---
    "horned": [
        "Crowned Beasts",
        "Antler Ascendancy",
        "Horned Dominion",
        "Majestic Antlers",
        "Royal Rack Initiative",
        "Cervid Legacy",
        "Antlered Majesty",
        "Nature's Crown"
    ],
}

TAG_BASED_NAMES = {
    "wetland": [
        "Wetland Sanctuary",
        "Marshland Refuge",
        "Echoes of the Marsh"
    ],
    "ocean": [
        "Ocean Realm",
        "Depths of the Sea",
        "Tides of Life"
    ],
    "flying": [
        "Wings of the Wind",
        "Skyborne Migration",
        "Flight of the Wilds"
    ],
    "herd": [
        "Great Migration",
        "Roaming Herd",
        "Gathering of Giants"
    ],
    "pack": [
        "Pack Territory",
        "Coordinated Hunt",
        "Predator Pact"
    ],
    "solitary": [
        "Lone Predator",
        "Silent Territory",
        "Isolated Domain"
    ],
}
GROUP_BIOME_NAMES = {
    ("bird", "water"): [
        "Flock of the Wetlands",
        "Wings of the Marsh",
        "Seabird Haven",
    ],
    ("bird", "tundra"): [
        "Arctic Migration",
        "Wings of the Frozen Sky",
    ],
    ("bird", "savannah"): [
        "Sky of the Golden Plains",
        "Savannah Flock",
    ],
    ("predator", "savannah"): [
        "Hunters of the Golden Plains",
        "Savannah Hunt",
    ],
    ("predator", "jungle"): [
        "Jungle Ambush",
        "Hunters of the Canopy",
    ],
    ("ungulate", "savannah"): [
        "Great Migration",
        "Herd of the Plains",
    ],
    ("ungulate", "steppe"): [
        "Steppe Migration",
        "Roaming Herd",
    ],
    ("aquatic", "water"): [
        "Tides of Life",
        "Realm of the Reef",
        "Ocean Drifters",
    ],
}


# --- SYMBIOSIS ---
# A project where every animal shares a common habitat AND a common group
# AND a common tag simultaneously - not just the project's own generation
# theme lining up, but all 3 trait dimensions overlapping at once. Rare
# enough (~1 in 6 generated projects) to warrant its own name treatment
# and a golden card frame in the GUI.
SYMBIOSIS_MIN_DIMENSIONS = 3

# Even a project that structurally qualifies (see is_symbiosis_project)
# only actually becomes a symbiosis project this often - the other
# (1 - SYMBIOSIS_CHANCE) of the time it's presented as a normal project
# (normal name, single theme badge, normal frame) despite being eligible.
SYMBIOSIS_CHANCE = 0.3

SYMBIOSIS_SUFFIXES = [
    "Symbiosis",
    "Convergence",
    "Harmony",
    "Unity",
    "Confluence",
    "Synergy",
    "Concord",
    "Equilibrium",
]


def _animal_trait_set(a):
    """(dimension, value) pairs for one animal - habitats/groups/tags are
    already normalized lowercase sets on the loaded animal dict (see
    data/data_loader.py), so no re-normalization is needed here."""
    traits = set()
    for h in a.get("habitats", []):
        traits.add(("habitat", h))
    for g in a.get("groups", []):
        traits.add(("group", g))
    for t in a.get("tags", []):
        traits.add(("tag", t))
    return traits


def _shared_traits_by_dimension(project, lookup):
    """{"habitat": {shared habitat values}, "group": {...}, "tag": {...}}
    - every animal in the project (OR/multiplier entries expanded to each
    individual name) has at least one of each dimension's values, or that
    dimension's set is empty. Needs the per-animal trait INTERSECTION,
    which is why this doesn't reuse extract_tags/extract_groups/
    extract_biomes below (those flatten every animal's traits into one
    combined list for frequency counting, not an intersection)."""
    names = set()
    for entry in project:
        names.update(expand_entry(entry))

    trait_sets = [_animal_trait_set(lookup[n]) for n in names if n in lookup]

    result = {"habitat": set(), "group": set(), "tag": set()}
    if not trait_sets:
        return result

    for dim, value in set.intersection(*trait_sets):
        result[dim].add(value)
    return result


def is_symbiosis_project(project, lookup):
    """True if every animal shares at least one common habitat, one
    common group, AND one common tag - all 3 dimensions at once."""
    shared = _shared_traits_by_dimension(project, lookup)
    dimensions_with_overlap = sum(1 for values in shared.values() if values)
    return dimensions_with_overlap >= SYMBIOSIS_MIN_DIMENSIONS


def symbiosis_badge_traits(project, theme_type, theme, lookup):
    """One representative (dimension, value) per habitat/group/tag, for a
    project that already qualifies as symbiosis (see is_symbiosis_project)
    - always 3 entries, since qualifying guarantees all 3 dimensions have
    at least one shared value. The project's own generation theme is used
    verbatim for its matching dimension (already guaranteed to be one of
    the shared values there); the other two dimensions pick their first
    (alphabetically, for determinism) shared value."""
    shared = _shared_traits_by_dimension(project, lookup)

    badges = []
    for dim in ("habitat", "group", "tag"):
        if dim == theme_type:
            badges.append((dim, theme))
        elif shared[dim]:
            badges.append((dim, sorted(shared[dim])[0]))
    return badges


def build_core_identity(theme_type, theme):

    theme = (theme or "").lower()

    # -------------------------
    # HABITAT (STRICT)
    # -------------------------
    if theme_type == "habitat":
        if theme in BIOME_BASE:
            return random.choice(BIOME_BASE[theme])
        raise ValueError(f"[NAMING ERROR] Unknown habitat theme: {theme}")

    # -------------------------
    # GROUP (STRICT)
    # -------------------------
    if not theme:
        raise ValueError("Empty group theme detected")
    if theme_type == "group":
        if theme in GROUP_BASE:
            return random.choice(GROUP_BASE[theme])
        raise ValueError(f"[NAMING ERROR] Unknown group theme: {theme}")

    # -------------------------
    # TAG (STRICT)
    # -------------------------
    if theme_type == "tag":
        if theme in TAG_BASED_NAMES:
            return random.choice(TAG_BASED_NAMES[theme])

        if theme in TAG_BASE:
            return random.choice(TAG_BASE[theme])

        raise ValueError(f"[NAMING ERROR] Unknown tag theme: {theme}")

    raise ValueError(f"[NAMING ERROR] Invalid theme_type: {theme_type}")
def extract_tags(project, lookup):

    tags = []

    for entry in project:
        for name in expand_entry(entry):

            a = lookup.get(name)
            if not a:
                continue

            t = a.get("tags", "")

            if isinstance(t, str):
                parts = t.split(";")

                for x in parts:
                    tag = normalize_tag(x)
                    if tag:
                        tags.append(tag)

    return tags

def extract_biomes(project, lookup):

    biomes = []

    for entry in project:
        for name in expand_entry(entry):

            a = lookup.get(name)
            if not a:
                continue

            h = a.get("habitats", [])

            if isinstance(h, str):
                h = h.split(";")

            for x in h:
                b = normalize_biome(x)
                if b:
                    biomes.append(b)

    return biomes


def extract_groups(project, lookup):

    groups = []

    for entry in project:
        for name in expand_entry(entry):

            a = lookup.get(name)
            if not a:
                continue

            g = a.get("groups", [])

            if isinstance(g, str):
                g = g.split(";")

            for x in g:
                g_norm = normalize_group(x)
                if g_norm:
                    groups.append(g_norm)

    return groups

def generate_project_name(project, theme_type, theme, lookup, difficulty, real_theme=None, is_symbiosis=False):

    # -----------------------------
    # SYMBIOSIS OVERRIDE
    # -----------------------------
    # Checked before the special/lvl3 overrides below - a 3-way trait
    # alignment across the whole project is a rarer, more structural
    # distinction than a single named animal being present, so it takes
    # priority for naming (and gets its own golden frame in the GUI - see
    # the "symbiosis" key the caller stores on the project dict).
    #
    # is_symbiosis is decided by the caller (project_generator.py), not
    # recomputed here - a project can structurally QUALIFY as symbiosis
    # (see is_symbiosis_project) without actually BECOMING one, since
    # only SYMBIOSIS_CHANCE of eligible projects get the treatment. The
    # caller rolls that once and passes the result in, so naming and the
    # "symbiosis"/"symbiosis_badges" dict keys (and the GUI's golden
    # frame) all agree on the same outcome instead of rolling separately.
    if is_symbiosis:
        core_identity = build_core_identity(theme_type, theme)
        suffix = random.choice(SYMBIOSIS_SUFFIXES)
        return f"{core_identity} {suffix}"


    # -----------------------------
    # ANALYZE PROJECT
    # -----------------------------
    has_or = any(" OR " in e for e in project)
    # Either side of an OR pair can carry its own multiplier, so check
    # every OR-split option's last token, not just the whole entry's.
    has_multiplier = any(
        part.split() and part.split()[-1].isdigit()
        for e in project
        for part in e.split(" OR ")
    )

    lvl3_animals = []
    special_animals = []

    for entry in project:
        for name in expand_entry(entry):
            if name not in lookup:
                continue

            a = lookup[name]

            if a["type"] != "main":
                continue

            if a["level"] == 3:
                lvl3_animals.append(name)

            if a.get("special"):
                special_animals.append(name)

    # -----------------------------
    # SPECIAL OVERRIDE
    # -----------------------------
    if special_animals:
        special = random.choice(special_animals)

        special_names = {
            "Panda": ["Bamboo Sanctuary", "Panda Preservation"],
            "Polar bear": ["Frozen Kingdom", "Arctic Guardian"],
            "Asian Elephant": ["Elephant Legacy", "Ancient Giants"]
        }

        if special in special_names:
            return random.choice(special_names[special])

    # -----------------------------
    # LEVEL 3 OVERRIDE
    # -----------------------------
    lvl3_names = {
        "Tasmanian Devil": [
            "Echoes of the Devil",
            "Tasmanian Nightfall",
            "Shadows of Tasmania",
            "Fury in the Dark",
            "Devil's Domain",
            "Nocturnal Menace",
            "Island of Screams"
        ],

        "Bearded vulture": [
            "Bones of the Sky",
            "Carrion Crown",
            "Sky Scavenger",
            "Wings of Decay",
            "Feast from Above",
            "Silent Bonebreaker",
            "Crown of the Highlands"
        ],

        "Golden Lion Tamarin": [
            "Golden Canopy Court",
            "Sunlit Grove",
            "Crown of the Jungle",
            "Forest Royalty",
            "Gilded Canopy",
            "Echoes of Gold",
            "Jungle Crownlands"
        ],

        "Bornean orangutan": [
            "Last Giants of Borneo",
            "Canopy of the Ancients",
            "Forest Elders",
            "Silent Giants",
            "Voices of the Canopy",
            "Ancient Tree Dwellers",
            "Borneo's Last Watchers"
        ],

        "Arabian oryx": [
            "White Ghosts of the Desert",
            "Endless Sand Runners",
            "Desert Spirits",
            "Phantoms of the Dunes",
            "Nomads of the Sands",
            "Mirage Walkers",
            "Desert Survivors"
        ],

        "Northern bald ibis": [
            "Relics of the Ancient Skies",
            "Forgotten Flock",
            "Echoes of Extinction",
            "Skyline Survivors",
            "Last of the Flock",
            "Ancient Wings Return",
            "Ghosts of the Sky"
        ],

        "Black-footed ferret": [
            "Prairie Shadows",
            "Burrowland Reclaimed",
            "Ghosts of the Prairie",
            "Silent Burrowers",
            "Return from the Dust",
            "Hidden Predators",
            "Underground Revival"
        ],

        "Zebra shark": [
            "Stripes Beneath the Waves",
            "Reef Phantom",
            "Shadows of the Reef",
            "Striped Depths",
            "Ocean Wanderer",
            "Silent Reef Hunter",
            "Patterns of the Deep"
        ],

        "Green sea turtle": [
            "Ancient Tides",
            "Guardians of the Current",
            "Ocean Travelers",
            "Endless Migration",
            "Tides of Time",
            "Sea of Ancients",
            "Currents of Survival"
        ],

        "Madagascar pochard": [
            "Echoes of the Wetlands",
            "Rare Duck",
            "Lost Waters",
            "Return of the Pochard",
            "Hidden Marsh Survivor",
            "Last of the Wetlands",
            "Vanishing Waters"
        ],

        "Przewalski's horse": [
            "Return to the Steppe",
            "Last Wild Herd",
            "Echoes of Freedom",
            "Steppe Reclaimed",
            "Untamed Return",
            "Wild Ancestors",
            "Herd of the Past"
        ]
    }

    if lvl3_animals:
        animal = random.choice(lvl3_animals)

        if animal in lvl3_names:
            return random.choice(lvl3_names[animal])

    # -----------------------------
    # DIFFICULTY → TONE
    # -----------------------------
    if difficulty <= 10:
        base_tones = ["Sanctuary", "Haven", "Reserve"]
    elif difficulty <= 14:
        base_tones = ["Territory", "Domain", "Frontier"]
    elif difficulty <= 20:
        base_tones = ["Dominion", "Stronghold"]
    else:
        base_tones = ["Supremacy", "Empire"]

    theme_tone_map = {
        "habitat": ["Expanse", "Sanctum", "Realm"],
        "group": ["Collective", "Assembly", "Order"],
        "tag": ["Initiative", "Directive", "Program"]
    }

    tone = random.choice(base_tones + theme_tone_map.get(theme_type, []))

    # -----------------------------
    # PREFIX (MECHANICS)
    # -----------------------------
    if special_animals:
        base_prefix = ["Sacred", "Mythic", "Legendary"]
    elif lvl3_animals:
        base_prefix = ["Apex", "Colossal", "Dominant"]
    elif has_multiplier:
        base_prefix = ["Proliferation", "Swarming", "Overgrowth"]
    elif has_or:
        base_prefix = ["Competing Species", "Shifting Balance", "Rival Territories"]
    else:
        base_prefix = ["Wild", "Natural", "Untamed"]

    theme_prefix_map = {
        "habitat": ["Primal", "Elemental", "Untamed"],
        "tag": ["Adaptive", "Strategic", "Evolving"]
    }

    prefix = random.choice(base_prefix + theme_prefix_map.get(theme_type, []))

    # -----------------------------
    # DATA EXTRACTION
    # -----------------------------
    tags = extract_tags(project, lookup)
    groups = extract_groups(project, lookup)
    biomes = extract_biomes(project, lookup)

    primary_group = max(set(groups), key=groups.count) if groups else None
    primary_biome = max(set(biomes), key=biomes.count) if biomes else None

    core_identity = build_core_identity(theme_type, theme)

    # -----------------------------
    # FINAL OUTPUT (STRICT THEME FIRST)
    # -----------------------------

    r = random.random()

    if r < 0.7:
        return core_identity

    elif r < 0.9:
        return f"{core_identity} {tone}"

    else:
        return f"{core_identity} – {prefix}"