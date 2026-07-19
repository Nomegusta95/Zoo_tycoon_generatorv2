# streamlit_app.py
#
# Web (Streamlit Cloud) entry point - a separate frontend from the desktop
# app (main.py + gui/app.py, CustomTkinter). tkinter has no web-hostable
# build, so this is a full second UI, not a port - but it drives the exact
# same game logic (core/, data/, scoring/), so the two frontends can never
# disagree on how a game is generated or scored.
#
# Simplifications from the desktop app (documented where they matter,
# rather than silently diverging):
#   - Required-animal picker is one searchable multiselect instead of a
#     collapsible grouped/filtered list with icon rows - Streamlit's
#     multiselect already has built-in type-to-filter search, so the
#     grouped-list UI would mostly duplicate that for little benefit.
#   - Saved seeds live in this browser session's st.session_state (reset
#     on page reload) instead of a per-machine file, since a hosted
#     multi-user app has no single "this user's machine" to write to.
#     Download/Upload buttons are provided so a seed collection can still
#     be carried between sessions, which is the correct web-native
#     equivalent of the desktop's persistent JSON file.
#   - Dark/Light is Streamlit's own theme setting (top-right menu ->
#     Settings), not an in-app toggle - CSS below is written to work in
#     both.

import base64
import io
import os
import random
from collections import Counter
from datetime import datetime

import streamlit as st
import streamlit.components.v1 as components
from PIL import Image

from core.engine import generate_full_game
from core.card_export import render_project_card
from data.data_loader import load_animals, VALID_PACKS
from data.predefined_loader import load_predefined_projects
from scoring.project_rewards import get_project_reward
from gui.theme_data import BADGE_MAP, PACK_LABELS, GROUP_TITLES, TIER_LABELS, average_badge_color

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ANIMALS_PATH = os.path.join(BASE_DIR, "data", "Animals.xlsx")
PREDEFINED_PATH = os.path.join(BASE_DIR, "data", "Predefined projects.xlsx")

# Card background is a low-alpha overlay of the badge's average color,
# not a solid blended hex - an rgba overlay adapts automatically to
# Streamlit's light/dark theme (whatever's underneath shows through),
# unlike the desktop app which has to precompute a blended solid color
# since CTk/Tkinter widgets don't support alpha-transparent fills.
CARD_TINT_ALPHA = 0.18

TIER_COLORS = {
    "easy": ("#8fe3b3", "#123322"),
    "medium": ("#f2c766", "#3a2d0d"),
    "hard": ("#f29a9a", "#3a1616"),
    "predefined": ("#c6aef2", "#241a3a"),
    "basic": ("#cccccc", "#2b2b2b"),
}
SYMBIOSIS_BORDER = "#d4af37"
DEFAULT_BORDER = "rgba(128,128,128,0.4)"

# Board tab: physical-game player tokens. Order also sets the active-player
# picker's left-to-right order.
PLAYER_COLORS = {
    "red": "🔴",
    "blue": "🔵",
    "green": "🟢",
    "yellow": "🟡",
}


# -----------------------------------------------------------
# DATA LOADING (cached across reruns/sessions)
# -----------------------------------------------------------

@st.cache_data
def _load_animals():
    return load_animals(ANIMALS_PATH)


@st.cache_data
def _load_predefined():
    return load_predefined_projects(PREDEFINED_PATH)


@st.cache_data(show_spinner=False)
def _icon_data_uri(name, variant="normal"):
    path = os.path.join(BASE_DIR, "assets", "images", "animals", f"{name.lower().replace(' ', '_')}.png")
    try:
        img = Image.open(path).convert("RGBA")
    except Exception:
        img = Image.new("RGBA", (50, 50), (180, 180, 180, 255))

    img.thumbnail((50, 50))
    canvas = Image.new("RGBA", (50, 50), (0, 0, 0, 0))
    canvas.paste(img, ((50 - img.width) // 2, (50 - img.height) // 2), img)

    if variant == "alt":
        alpha = canvas.split()[3]
        alpha = alpha.point(lambda p: int(p * 0.65))
        canvas.putalpha(alpha)

    return _pil_to_data_uri(canvas)


@st.cache_data(show_spinner=False)
def _badge_data_uri(theme):
    filename = BADGE_MAP.get((theme or "").strip().lower())
    if not filename:
        return None
    path = os.path.join(BASE_DIR, "assets", "images", "badges", filename)
    try:
        img = Image.open(path).convert("RGBA")
    except Exception:
        return None
    img.thumbnail((70, 70))
    canvas = Image.new("RGBA", (70, 70), (0, 0, 0, 0))
    canvas.paste(img, ((70 - img.width) // 2, (70 - img.height) // 2), img)
    return _pil_to_data_uri(canvas)


def _pil_to_data_uri(img):
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


@st.cache_data(show_spinner=False)
def _badge_avg_color(theme):
    filename = BADGE_MAP.get((theme or "").strip().lower())
    if not filename:
        return None
    path = os.path.join(BASE_DIR, "assets", "images", "badges", filename)
    return average_badge_color(path)


def _card_tint_style(theme_values):
    """rgba() background-color CSS for a card, averaged across 1
    (normal) or 3 (symbiosis) badge colors. Empty string (no tint) if
    none of the badges have a resolvable color."""
    colors = [c for c in (_badge_avg_color(v) for v in theme_values) if c]
    if not colors:
        return ""
    avg = tuple(sum(c[i] for c in colors) // len(colors) for i in range(3))
    return f"background-color: rgba({avg[0]}, {avg[1]}, {avg[2]}, {CARD_TINT_ALPHA});"


# -----------------------------------------------------------
# SESSION STATE
# -----------------------------------------------------------

def _init_state():
    defaults = {
        "current_projects": [None] * 5,
        "locked_projects": {},
        "last_game_animals": None,
        "last_lookup": None,
        "current_seed": None,
        "required_animals": set(),
        # Subset of required_animals guaranteed a dedicated project, not
        # just pool membership - see the "Force into a project"
        # multiselect in _render_sidebar and core.engine.generate_full_game's
        # required-vs-forced distinction.
        "forced_animals": set(),
        "active_packs": set(VALID_PACKS),
        "include_predefined": False,
        "generation_mode": "freeform",
        "saved_seeds": [],
        "active_player": "red",
        # project identity -> {"first": color|None, "second": color|None} -
        # who has "conquered" each reward slot on the Board tab. Keyed by
        # identity (not plain index) so a locked project keeps its claims
        # across a regeneration, the same way locked projects keep their
        # animals - see _project_identity.
        "conquered": {},
        # project identity -> rendered card PNG bytes, populated only when
        # the player taps "Generate Board" (see _render_board) - not
        # rendered automatically on every rerun, since a claim click reruns
        # the script and re-rendering all 5 print-quality cards on every
        # single tap would make the board sluggish for no benefit.
        "board_card_images": {},
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _project_identity(index, project):
    """Identifies "this exact project in this exact slot" - stable across
    a regeneration for a locked project (same name/animals), so its Board
    claims survive; a replaced project gets a new identity and its old
    claims become orphaned (pruned in _run_generation)."""
    return (index, project.get("name"), tuple(project.get("animals", [])))


# -----------------------------------------------------------
# GENERATION
# -----------------------------------------------------------

def _run_generation(seed, animals, predefined):
    active_packs = st.session_state.active_packs
    if not active_packs:
        st.error("No packs selected - check at least one pack.")
        return

    pool_animals = [a for a in animals if a["pack"] in active_packs]
    required = list(st.session_state.required_animals)
    forced = list(st.session_state.forced_animals)
    predefined_arg = predefined if st.session_state.include_predefined else []

    # A locked project's animals only make sense against the pool they
    # were drawn from, so reuse the last pool instead of resampling a new
    # one while anything is locked.
    if st.session_state.locked_projects and st.session_state.last_game_animals is not None:
        pool_kwargs = {
            "game_animals": st.session_state.last_game_animals,
            "lookup": st.session_state.last_lookup,
        }
    else:
        pool_kwargs = {}

    random.seed(seed)
    try:
        game, game_animals, lookup = generate_full_game(
            pool_animals, required, predefined_arg,
            locked_projects=st.session_state.locked_projects,
            mode=st.session_state.generation_mode,
            forced=forced,
            **pool_kwargs
        )
    except Exception as e:
        st.error(str(e))
        return

    st.session_state.current_seed = seed
    st.session_state.current_projects = game
    st.session_state.last_game_animals = game_animals
    st.session_state.last_lookup = lookup

    # Drop Board claims for any slot whose project changed (kept for a
    # locked slot, whose identity is unchanged) - otherwise orphaned
    # entries pile up in session state as a long session regenerates.
    live_ids = {_project_identity(i, p) for i, p in enumerate(game) if p}
    st.session_state.conquered = {
        k: v for k, v in st.session_state.conquered.items() if k in live_ids
    }
    st.session_state.board_card_images = {
        k: v for k, v in st.session_state.board_card_images.items() if k in live_ids
    }


# -----------------------------------------------------------
# RENDERING HELPERS
# -----------------------------------------------------------

def _format_entry_html(entry):
    """One animal-row's inner HTML (icon(s) + name(s), OR pairs combined,
    multiplier shown as 'x4') - mirrors gui/app.py's render_project."""
    parts = entry.split(" OR ")
    icons_html = []
    texts = []

    for j, part in enumerate(parts):
        tokens = part.strip().split()
        multiplier = None
        if tokens and tokens[-1].isdigit():
            multiplier = tokens[-1]
            tokens = tokens[:-1]
        name = " ".join(tokens)

        variant = "normal" if j == 0 else "alt"
        icons_html.append(f'<img class="zoo-icon" src="{_icon_data_uri(name, variant)}">')

        text = name
        if multiplier:
            text += f" x{multiplier}"
        texts.append(text)

    return "".join(icons_html), " OR ".join(texts)


def _group_animals(game_animals):
    lvl0, lvl1, lvl2, lvl3, special = [], [], [], [], []
    habitat_counts = Counter()
    group_counts = Counter()

    for a in game_animals:
        if a["type"] == "main":
            if a["level"] == 1:
                lvl1.append(a["name"])
            elif a["level"] == 2:
                lvl2.append(a["name"])
            elif a["level"] == 3:
                lvl3.append(a["name"])
        if a["type"] == "cospecies":
            lvl0.append(a["name"])
        if a.get("special"):
            special.append(a["name"])
        for h in a.get("habitats", []):
            habitat_counts[h] += 1
        for g in a.get("groups", []):
            group_counts[g] += 1

    return lvl0, lvl1, lvl2, lvl3, special, habitat_counts, group_counts


def _render_card(index, project, lookup):
    with st.container():
        lock_col, title_col, export_col = st.columns([1, 5, 1])
        with lock_col:
            is_locked = index in st.session_state.locked_projects
            if st.button("🔒" if is_locked else "🔓", key=f"lock_{index}", help="Lock/unlock this slot"):
                if not project:
                    st.toast("Nothing generated for this slot yet.")
                elif is_locked:
                    del st.session_state.locked_projects[index]
                else:
                    st.session_state.locked_projects[index] = project
                st.rerun()

        if not project:
            with title_col:
                st.markdown(f"**Project {index + 1}**")
                st.caption("Not generated yet.")
            return

        tier = project.get("tier")
        tier_bg, tier_fg_dark = TIER_COLORS.get(tier, TIER_COLORS["basic"])
        tier_label = TIER_LABELS.get(tier, tier or "-")

        with title_col:
            st.markdown(
                f'**Project {index + 1}: {project.get("name", "Unnamed")}** '
                f'<span class="tier-pill" style="background:{tier_bg}22;color:{tier_bg};border:1px solid {tier_bg}66;">{tier_label}</span>',
                unsafe_allow_html=True
            )

        reward = get_project_reward(project, lookup)

        with export_col:
            # st.button only returns True on the single rerun triggered by
            # the click itself, so the render below only ever runs once per
            # actual click - no eager per-rerun regeneration, and (unlike
            # st.download_button, whose data must be computed before the
            # button is even drawn) the browser download fires on this same
            # click instead of needing a second one.
            if st.button("🖼️", key=f"export_{index}", help="Download this project as a printable PNG card"):
                card_image = render_project_card(project, lookup, reward, base_dir=BASE_DIR)
                buf = io.BytesIO()
                card_image.save(buf, format="PNG")
                safe_name = "".join(c for c in project.get("name", "project") if c not in '<>:"/\\|?*')
                b64 = base64.b64encode(buf.getvalue()).decode()
                components.html(
                    f'<a id="dl" href="data:image/png;base64,{b64}" download="{safe_name}.png"></a>'
                    f'<script>document.getElementById("dl").click();</script>',
                    height=0,
                )

        symbiosis = project.get("symbiosis") and project.get("symbiosis_badges")
        border_color = SYMBIOSIS_BORDER if symbiosis else DEFAULT_BORDER
        border_width = "3px" if symbiosis else "1px"

        theme_values = (
            [value for _dim, value in project["symbiosis_badges"]] if symbiosis
            else [project.get("theme")]
        )
        tint_style = _card_tint_style(theme_values)

        badges_html = ""
        if symbiosis:
            imgs = []
            labels = []
            for _dim, value in project["symbiosis_badges"]:
                uri = _badge_data_uri(value)
                if not uri:
                    continue
                imgs.append(f'<img class="zoo-badge" src="{uri}">')
                labels.append(value.upper())
            if imgs:
                badges_html = (
                    f'<div class="badge-row">{"".join(imgs)}</div>'
                    f'<div class="badge-label">{" &middot; ".join(labels)}</div>'
                )
        else:
            uri = _badge_data_uri(project.get("theme"))
            if uri:
                badges_html = (
                    f'<div class="badge-row"><img class="zoo-badge" src="{uri}"></div>'
                    f'<div class="badge-label">{(project.get("theme") or "").upper()}</div>'
                )

        rows_html = []
        for entry in project.get("animals", []):
            icons_html, text = _format_entry_html(entry)
            rows_html.append(
                f'<div class="zoo-row"><span class="zoo-row-icons">{icons_html}</span>'
                f'<span class="zoo-row-text">{text}</span></div>'
            )

        card_html = f"""
        <div class="zoo-card" style="border-color:{border_color}; border-width:{border_width}; {tint_style}">
          <div class="reward-row">
            <span class="reward-pill reward-first">1st&nbsp;&nbsp;{reward['first']}</span>
            <span class="reward-pill reward-second">2nd&nbsp;&nbsp;{reward['second']}</span>
          </div>
          {badges_html}
          <hr class="zoo-divider">
          {''.join(rows_html)}
        </div>
        """
        st.markdown(card_html, unsafe_allow_html=True)


def _render_board(game, lookup):
    """Shared 'table screen' view: the currently generated projects with
    their 1st/2nd reward boxes as tap targets, so whoever's turn it is can
    mark it conquered in their color - the on-screen equivalent of placing
    a token on the physical card."""
    st.caption("Active player")
    player_cols = st.columns(len(PLAYER_COLORS))
    for col, (color, emoji) in zip(player_cols, PLAYER_COLORS.items()):
        with col:
            is_active = st.session_state.active_player == color
            label = f"{emoji} {color.capitalize()}" + (" ✓" if is_active else "")
            if st.button(label, key=f"active_player_{color}", use_container_width=True,
                         type="primary" if is_active else "secondary"):
                st.session_state.active_player = color
                st.rerun()

    st.divider()

    if not any(game):
        st.info("Generate a game first, then come back here to track who conquers what.")
        return

    if st.button("🖼️ Generate Board", help="Render each project as its printable card"):
        for index, project in enumerate(game):
            if not project:
                continue
            identity = _project_identity(index, project)
            if identity in st.session_state.board_card_images:
                continue
            reward = get_project_reward(project, lookup)
            card_image = render_project_card(project, lookup, reward, base_dir=BASE_DIR)
            buf = io.BytesIO()
            card_image.save(buf, format="PNG")
            st.session_state.board_card_images[identity] = buf.getvalue()

    for index, project in enumerate(game):
        if not project:
            continue
        identity = _project_identity(index, project)
        claims = st.session_state.conquered.get(identity, {})
        reward = get_project_reward(project, lookup)

        st.markdown(f"**Project {index + 1}: {project.get('name', 'Unnamed')}**")
        card_image = st.session_state.board_card_images.get(identity)
        if card_image:
            st.image(card_image, width=280)
        slot_cols = st.columns(2)
        for col, slot, label in ((slot_cols[0], "first", "1st"), (slot_cols[1], "second", "2nd")):
            with col:
                claimed_by = claims.get(slot)
                prefix = f"{PLAYER_COLORS[claimed_by]} " if claimed_by else ""
                if st.button(f"{prefix}{label}  {reward[slot]}", key=f"conquer_{index}_{slot}",
                             use_container_width=True):
                    entry = dict(st.session_state.conquered.get(identity, {}))
                    entry[slot] = None if claimed_by else st.session_state.active_player
                    st.session_state.conquered = {**st.session_state.conquered, identity: entry}
                    st.rerun()
        st.markdown("---")


def _inject_css():
    st.markdown("""
    <style>
    .zoo-card {
        border-style: solid;
        border-radius: 12px;
        padding: 12px 14px 14px 14px;
        margin-bottom: 8px;
    }
    .tier-pill {
        display: inline-block;
        font-size: 0.72rem;
        font-weight: 700;
        padding: 2px 8px;
        border-radius: 8px;
        vertical-align: middle;
    }
    .reward-row { margin-bottom: 8px; }
    .reward-pill {
        display: inline-block;
        font-size: 0.78rem;
        font-weight: 700;
        padding: 3px 10px;
        border-radius: 6px;
        margin-right: 6px;
    }
    .reward-first { background: #4a3a1244; color: #f2c766; }
    .reward-second { background: #3a3a3a44; color: #d4d8dc; }
    .badge-row { text-align: center; margin: 4px 0 2px 0; }
    .zoo-badge { width: 56px; height: 56px; margin: 0 3px; }
    .badge-label {
        text-align: center;
        font-weight: 700;
        font-size: 0.85rem;
        margin-bottom: 6px;
        letter-spacing: 0.02em;
    }
    .zoo-divider { border: none; border-top: 1px solid rgba(128,128,128,0.35); margin: 6px 0 10px 0; }
    .zoo-row { display: flex; align-items: center; gap: 8px; padding: 3px 0; }
    .zoo-row-icons { display: flex; flex-shrink: 0; }
    .zoo-icon { width: 32px; height: 32px; margin-right: 2px; }
    .zoo-row-text { font-size: 0.88rem; line-height: 1.2; }
    </style>
    """, unsafe_allow_html=True)


# -----------------------------------------------------------
# SIDEBAR
# -----------------------------------------------------------

def _render_sidebar(animals):
    st.sidebar.header("Packs")
    for pack in VALID_PACKS:
        checked = st.sidebar.checkbox(
            PACK_LABELS.get(pack, pack), value=pack in st.session_state.active_packs, key=f"pack_{pack}"
        )
        if checked:
            st.session_state.active_packs.add(pack)
        else:
            st.session_state.active_packs.discard(pack)

    # An animal required from a now-unchecked pack would otherwise sit in
    # the required set looking selected while silently not being in the
    # pool at all during generation.
    active = st.session_state.active_packs
    animals_by_name = {a["name"]: a for a in animals}
    st.session_state.required_animals = {
        n for n in st.session_state.required_animals
        if n in animals_by_name and animals_by_name[n]["pack"] in active
    }
    # forced_animals is always a subset of required_animals - dropping a
    # pack can shrink the latter, so re-clamp the former to match.
    st.session_state.forced_animals &= st.session_state.required_animals

    st.sidebar.divider()
    st.sidebar.header("Required animals")

    def _label(a):
        if a["type"] == "cospecies":
            group = "Cospecies"
        else:
            group = f"Lvl {a['level']}"
        star = " ★" if a.get("special") else ""
        return f"{a['name']} ({group}){star}"

    eligible = sorted(
        [a for a in animals if a["pack"] in active], key=lambda a: a["name"]
    )
    label_to_name = {_label(a): a["name"] for a in eligible}
    name_to_label = {v: k for k, v in label_to_name.items()}

    current_labels = [name_to_label[n] for n in st.session_state.required_animals if n in name_to_label]

    chosen_labels = st.sidebar.multiselect(
        "Search and select (type to filter) - guarantees a spot in the "
        "generated pool, not necessarily in a project",
        options=sorted(label_to_name.keys()),
        default=current_labels,
    )
    st.session_state.required_animals = {label_to_name[label] for label in chosen_labels}
    # forced_animals can only reference animals still required after the
    # multiselect above just ran.
    st.session_state.forced_animals &= st.session_state.required_animals

    # Second level: escalate a required animal to guarantee it a
    # dedicated project (see core.engine.generate_full_game's `forced`
    # param), not just pool membership - options are restricted to
    # whatever's currently required, since forcing implies requiring.
    force_options = sorted(
        name_to_label[n] for n in st.session_state.required_animals if n in name_to_label
    )
    current_forced_labels = [
        name_to_label[n] for n in st.session_state.forced_animals if n in name_to_label
    ]
    chosen_forced_labels = st.sidebar.multiselect(
        "Force into a project (guarantees a dedicated project, not just the pool)",
        options=force_options,
        default=[label for label in current_forced_labels if label in force_options],
    )
    st.session_state.forced_animals = {label_to_name[label] for label in chosen_forced_labels}


# -----------------------------------------------------------
# SEED BAR
# -----------------------------------------------------------

def _render_seed_bar(animals, predefined):
    with st.expander("Seed", expanded=False):
        st.text(f"Current seed: {st.session_state.current_seed if st.session_state.current_seed is not None else '-'}")

        col1, col2 = st.columns([2, 1])
        with col1:
            typed = st.text_input("Enter a seed", key="seed_input", label_visibility="collapsed", placeholder="Enter a seed...")
        with col2:
            if st.button("Use Seed", use_container_width=True):
                if typed.strip():
                    try:
                        _run_generation(int(typed.strip()), animals, predefined)
                    except ValueError:
                        st.error("Seed must be a whole number.")

        st.markdown("**Save current seed**")
        save_col1, save_col2 = st.columns([2, 1])
        with save_col1:
            seed_name = st.text_input("Name", key="seed_name_input", label_visibility="collapsed", placeholder="Name for this seed...")
        with save_col2:
            if st.button("Save Seed", use_container_width=True):
                if st.session_state.current_seed is None:
                    st.error("Generate a game first before saving its seed.")
                elif not seed_name.strip():
                    st.error("Enter a name for this seed.")
                else:
                    entry = {
                        "name": seed_name.strip(),
                        "seed": st.session_state.current_seed,
                        "active_packs": sorted(st.session_state.active_packs),
                        "required_animals": sorted(st.session_state.required_animals),
                        "forced_animals": sorted(st.session_state.forced_animals),
                        "include_predefined": st.session_state.include_predefined,
                        "saved_at": datetime.now().isoformat(timespec="seconds"),
                    }
                    st.session_state.saved_seeds = [
                        e for e in st.session_state.saved_seeds if e["name"] != entry["name"]
                    ] + [entry]
                    st.success(f'Seed "{entry["name"]}" saved for this session.')

        st.markdown("**Saved seeds (this session)**")
        if not st.session_state.saved_seeds:
            st.caption("No saved seeds yet.")
        else:
            for entry in sorted(st.session_state.saved_seeds, key=lambda e: e.get("saved_at", ""), reverse=True):
                c1, c2, c3 = st.columns([3, 1, 1])
                with c1:
                    st.caption(f'{entry["name"]} — seed {entry["seed"]} — packs: {", ".join(entry.get("active_packs", []))}')
                with c2:
                    if st.button("Load", key=f"load_seed_{entry['name']}"):
                        st.session_state.active_packs = set(entry.get("active_packs", []))
                        st.session_state.required_animals = set(entry.get("required_animals", []))
                        # Absent in seeds saved before the pool-vs-forced
                        # distinction existed - absent means none were
                        # forced, not that the key is missing/broken.
                        st.session_state.forced_animals = set(entry.get("forced_animals", []))
                        st.session_state.include_predefined = entry.get("include_predefined", True)
                        st.session_state.locked_projects = {}
                        st.session_state.last_game_animals = None
                        st.session_state.last_lookup = None
                        _run_generation(entry["seed"], animals, predefined)
                        st.rerun()
                with c3:
                    if st.button("Delete", key=f"delete_seed_{entry['name']}"):
                        st.session_state.saved_seeds = [
                            e for e in st.session_state.saved_seeds if e["name"] != entry["name"]
                        ]
                        st.rerun()

        st.divider()
        st.caption("Seeds above only last this browser session. Export/import to keep them across visits.")
        import json as _json
        export_data = _json.dumps(st.session_state.saved_seeds, indent=2).encode("utf-8")
        st.download_button("Export saved seeds", data=export_data, file_name="zoo_seeds.json", mime="application/json")
        uploaded = st.file_uploader("Import saved seeds", type="json", key="seed_import")
        if uploaded is not None:
            try:
                imported = _json.load(uploaded)
                names = {e["name"] for e in st.session_state.saved_seeds}
                for e in imported:
                    if e.get("name") not in names:
                        st.session_state.saved_seeds.append(e)
                st.success(f"Imported {len(imported)} seed(s).")
            except Exception as e:
                st.error(f"Could not read that file: {e}")


# -----------------------------------------------------------
# SUMMARY PANEL
# -----------------------------------------------------------

def _render_summary(game_animals):
    if not game_animals:
        return
    with st.expander("Animal Pool", expanded=False):
        lvl0, lvl1, lvl2, lvl3, special, habitat_counts, group_counts = _group_animals(game_animals)

        def fmt(counts):
            return ", ".join(f"{name.title()} ({count})" for name, count in sorted(counts.items()))

        rows = [
            ("Habitats", fmt(habitat_counts)),
            ("Groups", fmt(group_counts)),
            ("Lvl 1", ", ".join(lvl1)),
            ("Lvl 2", ", ".join(lvl2)),
            ("Lvl 3", ", ".join(lvl3)),
            ("Cospecies", ", ".join(lvl0)),
            ("Special", ", ".join(special)),
        ]
        for title, value in rows:
            if not value:
                continue
            st.markdown(f"**{title}:** {value}")


# -----------------------------------------------------------
# MAIN
# -----------------------------------------------------------

def main():
    st.set_page_config(page_title="Zoo Generator", layout="wide")
    _init_state()
    _inject_css()

    animals = _load_animals()
    predefined = _load_predefined()

    st.title("🦁 Zoo Generator")

    generator_tab, board_tab = st.tabs(["🎲 Generator", "🏆 Board"])

    game = st.session_state.current_projects
    lookup = st.session_state.last_lookup or {}

    with generator_tab:
        top1, top2, top3 = st.columns([2, 2, 3])
        with top1:
            if st.button("🎲 Generate Game", type="primary", use_container_width=True):
                _run_generation(random.randint(0, 2**31 - 1), animals, predefined)
        with top2:
            st.session_state.include_predefined = st.checkbox(
                "Include predefined projects", value=st.session_state.include_predefined,
                help="Include projects from the original board game"
            )
        with top3:
            st.session_state.generation_mode = st.radio(
                "Generation mode",
                options=["freeform", "restrictive"],
                format_func=lambda v: v.capitalize(),
                horizontal=True,
                index=0 if st.session_state.generation_mode == "freeform" else 1,
                help=(
                    "Freeform: fast & varied. Only 3-4 of the 6 habitats appear each game, "
                    "and there's no minimum number of species per habitat or group.\n\n"
                    "Restrictive: rulebook-accurate. Doesn't force every habitat or group to "
                    "appear - but whichever ones DO show up are properly represented: at least "
                    "3 species for any active habitat, at least 2 for any active group."
                ),
            )

        _render_seed_bar(animals, predefined)
        _render_sidebar(animals)

        st.divider()

        for row_start in range(0, 5, 3):
            cols = st.columns(3)
            for offset, col in enumerate(cols):
                index = row_start + offset
                if index >= 5:
                    break
                with col:
                    _render_card(index, game[index], lookup)

        _render_summary(st.session_state.last_game_animals)

    with board_tab:
        _render_board(game, lookup)


if __name__ == "__main__":
    main()
