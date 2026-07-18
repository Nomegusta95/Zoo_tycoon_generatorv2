from core.utils import resource_path
import os
import random
from collections import Counter
from datetime import datetime

from scoring.project_rewards import get_project_reward
from core.engine import generate_full_game
from data.data_loader import VALID_PACKS
from data.seed_store import load_saved_seeds, save_seed_entry, delete_seed_entry
from gui.theme_data import BADGE_MAP, PACK_LABELS, FILTERS, GROUP_ORDER, GROUP_TITLES, average_badge_color

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, simpledialog
from PIL import Image


TITLE_WRAP_WIDTH = 172
TITLE_MAX_LINES = 3

# Animal name column width in a project card row (card width minus the
# icon column and grid padding) - names wrap instead of silently
# overflowing/getting clipped past the card's fixed boundary.
ANIMAL_NAME_WRAP_WIDTH = 180

# Lock toggle button colors, as (light_mode, dark_mode) pairs.
LOCK_FILL_LOCKED = ("#3aa65a", "#2f6b3a")
LOCK_FILL_UNLOCKED = ("#9a9a9a", "#4a4a4a")


def fit_multi_line(text, font_obj, max_width, max_lines):
    """Let the label wrap across up to max_lines lines (rendering is
    handled by the widget's own wraplength) and only truncate with an
    ellipsis if the text is so long it wouldn't fit even at max_lines -
    keeps the fixed-height project card predictable for outlier long
    names instead of letting them grow the card unbounded. Line count is
    estimated via pixel width / max_width (ceil), measured against the
    ACTUAL font object the label renders with (not a freshly-built
    tkinter.font.Font) since CTkFont applies customtkinter's display
    scaling."""

    def estimated_lines(s):
        return max(1, -(-font_obj.measure(s) // max_width))

    if estimated_lines(text) <= max_lines:
        return text

    while text and estimated_lines(text + "…") > max_lines:
        if " " in text:
            text = text.rsplit(" ", 1)[0]
        else:
            text = text[:-1]
    return (text + "…") if text else "…"


class Tooltip:
    """Hover tooltip for a widget - CTk has no built-in one. Uses a plain
    tk.Toplevel/Label (not CTk) since a small transient popup doesn't need
    CTk's light/dark theming machinery - fixed dark-on-light colors read
    fine in either app appearance mode."""

    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        widget.bind("<Enter>", self._show)
        widget.bind("<Leave>", self._hide)

    def _show(self, event=None):
        if self.tip_window or not self.text:
            return
        x = self.widget.winfo_rootx()
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tk.Label(
            tw, text=self.text, justify="left",
            background="#2b2b2b", foreground="#f0f0f0",
            relief="solid", borderwidth=1,
            font=("Arial", 10), padx=8, pady=6, wraplength=280
        ).pack()

    def _hide(self, event=None):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None


# --- HELPERS ---

def group_animals(game_animals):
    lvl0 = []
    lvl1 = []
    lvl2 = []
    lvl3 = []
    special = []
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

        # An animal can belong to more than one habitat/group (e.g. Puma
        # spans several habitats, Sea otter is both predator and aquatic),
        # so it's counted once per habitat/group it actually belongs to.
        for h in a.get("habitats", []):
            habitat_counts[h] += 1

        for g in a.get("groups", []):
            group_counts[g] += 1

    return lvl0, lvl1, lvl2, lvl3, special, habitat_counts, group_counts


# Tier badge colors, as (light_mode, dark_mode) pairs so the badges stay
# readable when the theme toggle switches modes. "predefined" = mandatory
# projects, "basic" = fallback (e.g. failed-project placeholders).
TIER_STYLES = {
    "easy": {"bg": ("#d7f0e2", "#1f4a33"), "fg": ("#1f6b45", "#8fe3b3"), "label": "Easy"},
    "medium": {"bg": ("#faecc8", "#4a3a12"), "fg": ("#8a5a00", "#f2c766"), "label": "Medium"},
    "hard": {"bg": ("#fbdada", "#4a1f1f"), "fg": ("#8a1f1f", "#f29a9a"), "label": "Hard"},
    "predefined": {"bg": ("#e8e0fb", "#2f2350"), "fg": ("#4a2f8a", "#c6aef2"), "label": "Mandatory"},
    "basic": {"bg": ("#e5e5e5", "#333333"), "fg": ("#444444", "#cccccc"), "label": "Basic"},
}

# Other (light_mode, dark_mode) color pairs used across the sidebar.
ROW_BORDER_DEFAULT = ("#d0d0d0", "#444444")
ROW_FILL_DEFAULT = ("#eaeaea", "#2b2b2b")
# "pool" required state (blue) - guaranteed somewhere in the ~35-animal
# pool, but not necessarily in any specific project.
ROW_BORDER_SELECTED = ("#1f6fd6", "#3399ff")
ROW_FILL_SELECTED = ("#3a7ebf", "#1f538d")
# "forced" required state (green) - a second click on an already-required
# row escalates it to this: guaranteed a dedicated project, not just pool
# membership. See gui.app.ZooApp.required_state.
ROW_BORDER_FORCED = ("#1f8f4a", "#2fd97a")
ROW_FILL_FORCED = ("#2f8f5a", "#1f6b3a")
CHIP_FILL = ("#3a7ebf", "#1f538d")
CHIP_FILL_FORCED = ("#2f8f5a", "#1f6b3a")
CHIP_REMOVE_HOVER = ("#cfe0f2", "#16375c")
DIVIDER_COLOR = ("#d0d0d0", "#444444")
REWARD_FIRST = {"bg": ("#faecc8", "#4a3a12"), "fg": ("#8a5a00", "#f2c766")}

# Project card border - default (1px, theme default color) vs. a symbiosis
# project (all animals share a habitat, group, AND tag in common - see
# core.project_naming.is_symbiosis_project), which gets a thicker gold
# frame instead.
CARD_BORDER_WIDTH_DEFAULT = 1
CARD_BORDER_WIDTH_SYMBIOSIS = 3
CARD_BORDER_COLOR_SYMBIOSIS = ("#c9a227", "#e0b93a")
REWARD_SECOND = {"bg": ("#e5e5e5", "#3a3a3a"), "fg": ("#444444", "#d4d8dc")}

# Card background is tinted toward its badge's average color, blended
# against the theme's real default card fill (captured once, like the
# border default) - CTk/Tkinter fills are solid, not alpha-transparent,
# so (unlike the Streamlit version's simple rgba overlay) this has to
# precompute an actual blended hex color for each of light/dark mode.
CARD_TINT_OPACITY = 0.22

PROJECT_GRID_COLUMNS = 3

# FILTERS, GROUP_ORDER, GROUP_TITLES, PACK_LABELS, BADGE_MAP: see
# gui/theme_data.py (shared with streamlit_app.py). Labels in FILTERS are
# kept short on purpose - CTkSegmentedButton doesn't wrap or ellipsize, so
# anything longer gets visually clipped inside a narrow sidebar (this is
# exactly what happened with "Level 1"/"Cospecies").


# --- GUI APP ---

class ZooApp:

    def __init__(self, root, animals, predefined):
        self.root = root
        self.animals = animals
        self.animals_by_name = {a["name"]: a for a in animals}
        self.predefined = predefined
        self.root.title("Zoo Generator")

        self.badge_map = BADGE_MAP
        self.image_cache = {}
        self.badge_color_cache = {}

        # name -> "pool" (guaranteed somewhere in the generated pool) or
        # "forced" (guaranteed its own dedicated project). Clicking an
        # unrequired row moves it to "pool"; clicking an already-"pool"
        # row escalates it to "forced"; clicking a "forced" row clears it
        # entirely - see _cycle_animal_required_state.
        self.required_state = {}

        # name -> row frame, so a chip removal or a row click can both
        # keep the selection highlight in sync
        self.animal_rows = {}
        # name -> checkmark label, updated alongside animal_rows' border
        # (see _apply_row_selection_style)
        self.animal_checkmarks = {}
        # filter_key -> {"title", "container", "header", "inner", "state", "rows"}
        self.groups = {}
        self.current_filter = "all"

        # Project locking - slot_index -> project dict for locked cards.
        # current_projects mirrors what's shown on each card right now (or
        # None before the first generate) so the lock button knows what to
        # pin. last_game_animals/last_lookup are the pool a locked project
        # was drawn from - reused instead of resampling so a locked card's
        # animals stay consistent with what's shown elsewhere in the game.
        self.locked_projects = {}
        self.current_projects = [None] * 5
        self.last_game_animals = None
        self.last_lookup = None

        # The random.seed() value behind the currently-shown game - shown
        # in the seed bar and what "Save Seed" persists.
        self.current_seed = None

        # pack -> BooleanVar, all default-checked (base game + both
        # expansions included by default).
        self.pack_vars = {pack: tk.BooleanVar(value=True) for pack in VALID_PACKS}

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self.refresh_animal_list())

        # Shared font object for project titles - used both to render the
        # label AND to measure text in fit_single_line(), so truncation
        # is measured against the exact font (and scaling) actually used.
        self.title_font = ctk.CTkFont(family="Arial", size=14, weight="bold")

        self._build_layout()

    # -----------------------------------------------------------
    # LAYOUT
    # -----------------------------------------------------------

    def _build_layout(self):
        top_bar = ctk.CTkFrame(self.root, corner_radius=0, height=56)
        top_bar.pack(side="top", fill="x")
        top_bar.pack_propagate(False)

        ctk.CTkLabel(
            top_bar,
            text="Zoo Generator",
            font=("Arial", 18, "bold")
        ).pack(side="left", padx=16)

        ctk.CTkButton(
            top_bar,
            text="Generate Game",
            command=self.generate,
            width=160,
            height=34
        ).pack(side="right", padx=16)

        self.include_predefined_var = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            top_bar,
            text="Include predefined projects",
            variable=self.include_predefined_var
        ).pack(side="right", padx=(0, 16))

        mode_help_icon = ctk.CTkLabel(
            top_bar, text="ⓘ", font=("Arial", 14, "bold"),
            text_color="gray60", width=18
        )
        mode_help_icon.pack(side="right", padx=(0, 4))
        Tooltip(
            mode_help_icon,
            "Freeform: fast & varied. Only 3-4 of the 6 habitats appear "
            "each game, and there's no minimum number of species per "
            "habitat or group.\n\n"
            "Restrictive: rulebook-accurate. Doesn't force every habitat "
            "or group to appear - but whichever ones DO show up are "
            "properly represented: at least 3 species for any active "
            "habitat, at least 2 for any active group. No thin, "
            "one-animal token representation."
        )

        # Freeform = today's behavior (random 3-4 of 6 habitats, no
        # per-habitat/per-group floors). Restrictive = same random 3-4
        # habitat pick, but whichever habitats/groups end up present are
        # topped up to the rulebook's 3+ species/habitat and 2+
        # species/group floors - not forced to include every one, just
        # never left "broken" (a thin partial count). Enforced by
        # core.generator's targeted pool builder instead of a plain
        # random sample.
        self.generation_mode_toggle = ctk.CTkSegmentedButton(
            top_bar,
            values=["Freeform", "Restrictive"],
        )
        self.generation_mode_toggle.set("Freeform")
        self.generation_mode_toggle.pack(side="right", padx=(0, 16))

        self.theme_toggle = ctk.CTkSegmentedButton(
            top_bar,
            values=["Dark", "Light"],
            command=self._on_theme_changed
        )
        self.theme_toggle.set("Dark" if ctk.get_appearance_mode() == "Dark" else "Light")
        self.theme_toggle.pack(side="right", padx=(0, 12))

        self._build_seed_bar()

        body = ctk.CTkFrame(self.root, fg_color="transparent")
        body.pack(side="top", fill="both", expand=True)

        self._build_sidebar(body)
        self._build_main_area(body)

    def _build_seed_bar(self):
        seed_bar = ctk.CTkFrame(self.root, corner_radius=0, height=40)
        seed_bar.pack(side="top", fill="x")
        seed_bar.pack_propagate(False)

        # Toggle stays outside the collapsible part - collapsing seed_controls
        # must never hide the only control that can bring it back.
        self.seed_toggle = ctk.CTkButton(
            seed_bar, text="◀ Seed", width=70, height=26,
            command=self._toggle_seed_bar
        )
        self.seed_toggle.pack(side="left", padx=(16, 8))

        self.seed_controls = ctk.CTkFrame(seed_bar, fg_color="transparent")
        self.seed_controls.pack(side="left", fill="x", expand=True)

        self.seed_display_var = tk.StringVar(value="-")
        seed_display = ctk.CTkEntry(
            self.seed_controls, textvariable=self.seed_display_var, width=110
        )
        seed_display.configure(state="readonly")
        seed_display.pack(side="left", padx=(0, 8))

        self.seed_input_var = tk.StringVar()
        ctk.CTkEntry(
            self.seed_controls, textvariable=self.seed_input_var,
            placeholder_text="Enter a seed...", width=110
        ).pack(side="left", padx=(0, 4))

        ctk.CTkButton(
            self.seed_controls, text="Use Seed", width=90, height=26,
            command=self._use_typed_seed
        ).pack(side="left", padx=(0, 16))

        ctk.CTkButton(
            self.seed_controls, text="Save Seed...", width=100, height=26,
            command=self._save_current_seed
        ).pack(side="left", padx=(0, 4))

        ctk.CTkButton(
            self.seed_controls, text="Load Seed...", width=100, height=26,
            command=self._open_load_seed_window
        ).pack(side="left")

    def _toggle_seed_bar(self):
        if self.seed_controls.winfo_ismapped():
            self.seed_controls.pack_forget()
            self.seed_toggle.configure(text="▶ Seed")
        else:
            self.seed_controls.pack(side="left", fill="x", expand=True)
            self.seed_toggle.configure(text="◀ Seed")

    def _toggle_sidebar(self):
        if self.sidebar_content.winfo_ismapped():
            self.sidebar_content.pack_forget()
            self.sidebar_toggle.configure(text="▶")
        else:
            self.sidebar_content.pack(side="left", fill="y", padx=(6, 0))
            self.sidebar_toggle.configure(text="◀")

    def _toggle_summary(self):
        if self.summary_content.winfo_ismapped():
            self.summary_content.pack_forget()
            self.summary_toggle.configure(text="▶ Animal Pool")
        else:
            self.summary_content.pack(fill="both", expand=True, padx=12, pady=8)
            self.summary_toggle.configure(text="▼ Animal Pool")

    def _on_theme_changed(self, value):
        ctk.set_appearance_mode(value.lower())

    def _build_sidebar(self, parent):
        sidebar_wrapper = ctk.CTkFrame(parent, fg_color="transparent")
        sidebar_wrapper.pack(side="left", fill="y", padx=(10, 5), pady=10)

        # Toggle stays outside the collapsible sidebar frame - collapsing
        # it must never hide the only control that can bring it back.
        self.sidebar_toggle = ctk.CTkButton(
            sidebar_wrapper, text="◀", width=20, height=40,
            command=self._toggle_sidebar
        )
        self.sidebar_toggle.pack(side="left", fill="y")

        sidebar = ctk.CTkFrame(sidebar_wrapper, width=320)
        sidebar.pack(side="left", fill="y", padx=(6, 0))
        sidebar.pack_propagate(False)
        self.sidebar_content = sidebar

        ctk.CTkLabel(
            sidebar,
            text="Packs",
            font=("Arial", 13, "bold")
        ).pack(anchor="w", padx=10, pady=(10, 4))

        packs_row = ctk.CTkFrame(sidebar, fg_color="transparent")
        packs_row.pack(anchor="w", padx=10, pady=(0, 8))

        for pack in VALID_PACKS:
            ctk.CTkCheckBox(
                packs_row,
                text=PACK_LABELS.get(pack, pack),
                variable=self.pack_vars[pack],
                command=self._on_pack_changed,
                font=("Arial", 11)
            ).pack(anchor="w", pady=2)

        ctk.CTkFrame(sidebar, height=1, fg_color=DIVIDER_COLOR).pack(
            fill="x", padx=10, pady=(0, 8)
        )

        required_header_row = ctk.CTkFrame(sidebar, fg_color="transparent")
        required_header_row.pack(fill="x", padx=10, pady=(10, 4))

        ctk.CTkLabel(
            required_header_row,
            text="Select animals (required)",
            font=("Arial", 13, "bold")
        ).pack(side="left")

        required_help_icon = ctk.CTkLabel(
            required_header_row, text="ⓘ", font=("Arial", 14, "bold"),
            text_color="gray60", width=18
        )
        required_help_icon.pack(side="left", padx=(4, 0))
        Tooltip(
            required_help_icon,
            "Click an animal once to require it - guaranteed somewhere "
            "in the generated pool, but not necessarily in any project.\n\n"
            "Click it again to force it - guaranteed its own dedicated "
            "project, not just pool membership.\n\n"
            "Click a third time to clear it."
        )

        ctk.CTkEntry(
            sidebar,
            placeholder_text="Search animals...",
            textvariable=self.search_var
        ).pack(fill="x", padx=10, pady=(0, 6))

        self.filter_bar = ctk.CTkSegmentedButton(
            sidebar,
            values=[label for label, _key in FILTERS],
            font=ctk.CTkFont(size=11),
            command=self._on_filter_changed
        )
        self.filter_bar.set("All")
        self.filter_bar.pack(fill="x", padx=10, pady=(0, 8))

        # Reserve the bottom "Required" panel space BEFORE packing the
        # expanding scrollable list (pack fills top->bottom, bottom->up,
        # so bottom-side widgets must be packed first to reserve space).
        self.required_chips = ctk.CTkFrame(sidebar, fg_color="transparent")
        self.required_chips.pack(side="bottom", fill="x", padx=10, pady=(0, 10))

        ctk.CTkFrame(sidebar, height=1, fg_color=DIVIDER_COLOR).pack(
            side="bottom", fill="x", padx=10, pady=(4, 0)
        )

        required_header = ctk.CTkFrame(sidebar, fg_color="transparent")
        required_header.pack(side="bottom", fill="x", padx=10, pady=(6, 2))

        ctk.CTkLabel(
            required_header, text="Required", font=("Arial", 12, "bold")
        ).pack(side="left")

        self.required_count_label = ctk.CTkLabel(
            required_header, text="(0)", text_color="gray60"
        )
        self.required_count_label.pack(side="left", padx=(4, 0))

        self.scroll_frame = ctk.CTkScrollableFrame(sidebar)
        self.scroll_frame.pack(side="top", fill="both", expand=True, padx=5, pady=(0, 6))

        lvl1 = sorted([a for a in self.animals if a["type"] == "main" and a["level"] == 1], key=lambda x: x["name"])
        lvl2 = sorted([a for a in self.animals if a["type"] == "main" and a["level"] == 2], key=lambda x: x["name"])
        lvl3 = sorted([a for a in self.animals if a["type"] == "main" and a["level"] == 3], key=lambda x: x["name"])
        cospecies = sorted([a for a in self.animals if a["type"] == "cospecies"], key=lambda x: x["name"])

        self._insert_group("level1", lvl1)
        self._insert_group("level2", lvl2)
        self._insert_group("level3", lvl3)
        self._insert_group("cospecies", cospecies)

        self._refresh_required_chips()
        self.refresh_animal_list()

    def _build_main_area(self, parent):
        right_container = ctk.CTkFrame(parent, fg_color="transparent")
        right_container.pack(side="right", fill="both", expand=True, padx=(5, 10), pady=10)

        # Reserve the bottom summary bar first, then let the project
        # grid fill the remaining space above it. No fixed height here:
        # each category wraps to as many lines as it needs instead of
        # overflowing the window edge on one long row.
        self.summary_frame = ctk.CTkFrame(right_container)
        self.summary_frame.pack(side="bottom", fill="x", pady=(10, 0))

        summary_header = ctk.CTkFrame(self.summary_frame, fg_color="transparent")
        summary_header.pack(fill="x", padx=12, pady=(6, 0))

        # Toggle stays outside the collapsible content frame - collapsing
        # summary_content must never hide the only control that can bring
        # it back.
        self.summary_toggle = ctk.CTkButton(
            summary_header, text="▼ Animal Pool", anchor="w",
            fg_color="transparent", text_color=("gray10", "gray90"),
            hover_color=("#d0d0d0", "#3a3a3a"),
            font=("Arial", 12, "bold"), height=24,
            command=self._toggle_summary
        )
        self.summary_toggle.pack(side="left")

        self.summary_content = ctk.CTkFrame(self.summary_frame, fg_color="transparent")
        self.summary_content.pack(fill="both", expand=True, padx=12, pady=8)
        self.summary_content.bind("<Configure>", self._on_summary_resize)

        self._summary_value_labels = []

        ctk.CTkLabel(
            self.summary_content,
            text="Generate a game to see the animal pool here.",
            text_color="gray60"
        ).pack(anchor="w")

        self.projects_scroll = ctk.CTkScrollableFrame(right_container)
        self.projects_scroll.pack(side="top", fill="both", expand=True)

        for col in range(PROJECT_GRID_COLUMNS):
            self.projects_scroll.grid_columnconfigure(col, weight=1)

        self.project_frames = []
        self.project_containers = []
        self.project_tier_badges = []
        self.project_lock_buttons = []

        for i in range(5):
            row, col = divmod(i, PROJECT_GRID_COLUMNS)

            # Fixed width AND height - every card is the same footprint
            # regardless of whether a project has 3, 4, or 5 animals, so
            # the grid stays aligned instead of each card sizing to its
            # own content. Height includes room for a title wrapped up to
            # TITLE_MAX_LINES lines (see fit_multi_line).
            frame = ctk.CTkFrame(
                self.projects_scroll,
                corner_radius=12,
                border_width=1,
                width=320,
                height=510
            )
            frame.grid(row=row, column=col, padx=8, pady=8, sticky="n")
            # pack_propagate, not grid_propagate - frame's own children
            # (header, container below) are added with .pack(), and
            # grid_propagate only governs auto-sizing from grid-managed
            # children, so it was a no-op here and the card would still
            # shrink/grow to fit its content despite the fixed width/height
            # passed to the constructor above.
            frame.pack_propagate(False)

            # Captured once so a symbiosis card's gold border (see
            # _apply_card_border) can be reverted back to the real theme
            # default later, instead of hardcoding a guessed default color.
            # fg_color similarly backs the badge-color card tint (see
            # _apply_card_fill) - resolved to RGB once too, since CTk's
            # default fill is a named Tk color ("gray92" etc.), not hex,
            # and blending needs actual numbers.
            if i == 0:
                self._card_border_color_default = frame.cget("border_color")
                self._card_fill_color_default = frame.cget("fg_color")
                self._card_fill_rgb_default = tuple(
                    self._resolve_tk_color_to_rgb(c) for c in self._card_fill_color_default
                )

            header = ctk.CTkFrame(frame, fg_color="transparent")
            header.pack(fill="x", padx=10, pady=(10, 0))

            # Badge is packed BEFORE the title so it always claims its
            # fixed width first - packing title (expand=True) first let
            # long titles squeeze the badge down and clip its text.
            # anchor="n" keeps it pinned to the top when a wrapped
            # multi-line title makes the header row taller than the badge.
            tier_badge = ctk.CTkLabel(
                header,
                text="",
                corner_radius=8,
                font=("Arial", 10, "bold"),
                width=82,
                height=20
            )
            tier_badge.pack(side="right", padx=(6, 0), anchor="n")

            # Locking a card pins its current project so the next Generate
            # only (re)fills the unlocked cards, reusing the same pool -
            # see _toggle_lock().
            lock_button = ctk.CTkButton(
                header,
                text="\U0001F513",
                width=28,
                height=20,
                corner_radius=6,
                fg_color=LOCK_FILL_UNLOCKED,
                hover_color=LOCK_FILL_UNLOCKED,
                font=("Arial", 11),
                command=lambda i=i: self._toggle_lock(i)
            )
            lock_button.pack(side="right", padx=(6, 0), anchor="n")

            # Wraps up to TITLE_MAX_LINES lines instead of clipping to a
            # single line, so the full project name is readable - text is
            # pre-fitted in generate() via fit_multi_line() (see that
            # function for why).
            title = ctk.CTkLabel(
                header,
                text=f"Project {i + 1}",
                font=self.title_font,
                anchor="nw",
                justify="left",
                wraplength=TITLE_WRAP_WIDTH
            )
            title.pack(side="left", fill="x", expand=True, anchor="n")

            container = ctk.CTkFrame(frame, fg_color="transparent")
            container.pack(fill="both", expand=True, padx=10, pady=10)

            self.project_frames.append((frame, title))
            self.project_containers.append(container)
            self.project_tier_badges.append(tier_badge)
            self.project_lock_buttons.append(lock_button)

    # -----------------------------------------------------------
    # ANIMAL SIDEBAR: groups, search, filter
    # -----------------------------------------------------------

    def _insert_group(self, filter_key, group):
        title = GROUP_TITLES[filter_key]

        container = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")

        header = ctk.CTkLabel(
            container,
            text=f"▶ {title} ({len(group)})",
            anchor="w",
            font=("Arial", 13, "bold")
        )
        header.pack(fill="x")

        inner = ctk.CTkFrame(container, fg_color="transparent")

        state = {"user_expanded": False}

        def toggle(event=None):
            state["user_expanded"] = not state["user_expanded"]
            self.refresh_animal_list()

        header.bind("<Button-1>", toggle)

        rows = []
        for a in group:
            row = self._add_animal_row(inner, a)
            rows.append((a, row))

        self.groups[filter_key] = {
            "title": title,
            "container": container,
            "header": header,
            "inner": inner,
            "state": state,
            "rows": rows,
        }

    def _add_animal_row(self, parent, animal):
        name = animal["name"]

        frame = ctk.CTkFrame(
            parent,
            corner_radius=8,
            border_width=2,
            border_color=ROW_BORDER_DEFAULT,
            fg_color=ROW_FILL_DEFAULT
        )

        icon = self.load_icon(name)

        label = ctk.CTkLabel(
            frame,
            image=icon,
            text=name,
            compound="left",
            anchor="w",
            font=("Arial", 12)
        )
        label.pack(side="left", fill="x", expand=True, padx=(10, 4), pady=6)

        # Blank when unselected, a checkmark glyph when required - see
        # _apply_row_selection_style, the single place both this and
        # _load_seed_entry go through to keep the border/fill highlight
        # and this checkmark from drifting out of sync with each other.
        checkmark = ctk.CTkLabel(
            frame, text="", font=("Arial", 14, "bold"),
            text_color=ROW_BORDER_SELECTED, width=18
        )
        checkmark.pack(side="right", padx=(0, 10), pady=6)

        def toggle(event=None):
            self._cycle_animal_required_state(name)

        frame.bind("<Button-1>", toggle)
        label.bind("<Button-1>", toggle)
        checkmark.bind("<Button-1>", toggle)

        self.animal_rows[name] = frame
        self.animal_checkmarks[name] = checkmark
        return frame

    def _on_filter_changed(self, value):
        label_to_key = dict(FILTERS)
        self.current_filter = label_to_key.get(value, "all")
        self.refresh_animal_list()

    def _active_packs(self):
        return {pack for pack, var in self.pack_vars.items() if var.get()}

    def _on_pack_changed(self):
        # An animal required from a pack that just got unchecked would
        # otherwise sit in the Required list looking selected while
        # silently never being considered during generation (it's no
        # longer in the pool at all) - drop it instead of leaving that
        # mismatch between what's shown and what's used.
        active = self._active_packs()
        for name in list(self.required_state):
            a = self.animals_by_name.get(name)
            if a and a["pack"] not in active:
                self._set_animal_required_state(name, None)

        self.refresh_animal_list()

    def refresh_animal_list(self):
        search = self.search_var.get().strip().lower()
        active_filter = self.current_filter
        active_packs = self._active_packs()
        force_open = bool(search) or active_filter != "all"

        for key in GROUP_ORDER:
            g = self.groups[key]
            is_candidate = active_filter in ("all", "special", key)

            visible_rows = []
            for animal, row in g["rows"]:
                row.pack_forget()

                if not is_candidate:
                    continue
                if animal["pack"] not in active_packs:
                    continue
                if search and search not in animal["name"].lower():
                    continue
                if active_filter == "special" and not animal.get("special"):
                    continue

                visible_rows.append(row)

            for row in visible_rows:
                row.pack(fill="x", pady=2, padx=2)

            g["container"].pack_forget()
            g["inner"].pack_forget()

            if not visible_rows:
                continue

            g["container"].pack(fill="x", pady=3)

            if force_open or g["state"]["user_expanded"]:
                g["inner"].pack(fill="x")
                g["header"].configure(text=f"▼ {g['title']} ({len(visible_rows)})")
            else:
                g["header"].configure(text=f"▶ {g['title']} ({len(visible_rows)})")

    # -----------------------------------------------------------
    # REQUIRED ANIMALS PANEL
    # -----------------------------------------------------------

    def _apply_row_selection_style(self, name, state):
        """Single place that styles an animal row for its required
        state (None/"pool"/"forced") - both the border/fill highlight
        and the checkmark glyph, so the two things can't drift out of
        sync with each other. Used by both _set_animal_required_state (a
        row/chip click) and _load_seed_entry (restoring a saved seed's
        required list)."""
        frame = self.animal_rows.get(name)
        if frame:
            if state == "forced":
                frame.configure(border_width=3, border_color=ROW_BORDER_FORCED, fg_color=ROW_FILL_FORCED)
            elif state == "pool":
                frame.configure(border_width=3, border_color=ROW_BORDER_SELECTED, fg_color=ROW_FILL_SELECTED)
            else:
                frame.configure(border_width=2, border_color=ROW_BORDER_DEFAULT, fg_color=ROW_FILL_DEFAULT)

        checkmark = self.animal_checkmarks.get(name)
        if checkmark:
            if state == "forced":
                checkmark.configure(text="✓✓", text_color=ROW_BORDER_FORCED)
            elif state == "pool":
                checkmark.configure(text="✓", text_color=ROW_BORDER_SELECTED)
            else:
                checkmark.configure(text="")

    def _set_animal_required_state(self, name, state):
        """state: None (not required), "pool" (guaranteed in the pool
        only), or "forced" (guaranteed its own dedicated project)."""
        if state is None:
            self.required_state.pop(name, None)
        else:
            self.required_state[name] = state

        self._apply_row_selection_style(name, state)
        self._refresh_required_chips()

    def _cycle_animal_required_state(self, name):
        """A row click cycles: not required -> pool -> forced -> not
        required. Escalating to "forced" is the explicit second click
        the user asked for - a plain single click only guarantees pool
        membership, matching generate_full_game's `required` vs `forced`
        distinction (see core/engine.py)."""
        current = self.required_state.get(name)
        if current is None:
            self._set_animal_required_state(name, "pool")
        elif current == "pool":
            self._set_animal_required_state(name, "forced")
        else:
            self._set_animal_required_state(name, None)

    def _refresh_required_chips(self):
        for widget in self.required_chips.winfo_children():
            widget.destroy()

        self.required_count_label.configure(text=f"({len(self.required_state)})")

        if not self.required_state:
            ctk.CTkLabel(
                self.required_chips,
                text="Click an animal to require it (pool only); click again to force it into its own project.",
                text_color="gray60",
                font=("Arial", 11),
                wraplength=260,
                justify="left"
            ).pack(anchor="w")
            return

        for name in sorted(self.required_state):
            forced = self.required_state[name] == "forced"
            chip = ctk.CTkFrame(
                self.required_chips, corner_radius=8,
                fg_color=CHIP_FILL_FORCED if forced else CHIP_FILL
            )
            chip.pack(fill="x", pady=2)

            label_text = f"✓✓ {name}" if forced else name
            ctk.CTkLabel(
                chip, text=label_text, font=("Arial", 11), text_color="white", anchor="w"
            ).pack(side="left", fill="x", expand=True, padx=(8, 2), pady=4)

            ctk.CTkButton(
                chip, text="×", width=20, height=20, corner_radius=10,
                fg_color="transparent", hover_color=CHIP_REMOVE_HOVER,
                command=lambda n=name: self._set_animal_required_state(n, None)
            ).pack(side="right", padx=4, pady=2)

    # -----------------------------------------------------------
    # IMAGES
    # -----------------------------------------------------------

    def load_icon(self, name, variant="normal"):
        key = f"{name.lower().replace(' ', '_')}_{variant}"

        if key not in self.image_cache:
            try:
                path = resource_path(
                    os.path.join(
                        "assets", "images", "animals",
                        f"{name.lower().replace(' ', '_')}.png"
                    )
                )

                img = Image.open(path).convert("RGBA")

                # Preserve aspect ratio instead of forcing a hard 50x50
                # resize - source art isn't all square, so a hard resize
                # stretched/squished a lot of the icons.
                img.thumbnail((50, 50))
                canvas = Image.new("RGBA", (50, 50), (0, 0, 0, 0))
                canvas.paste(img, ((50 - img.width) // 2, (50 - img.height) // 2), img)
                img = canvas

                if variant == "alt":
                    alpha = img.split()[3]
                    alpha = alpha.point(lambda p: int(p * 0.65))
                    img.putalpha(alpha)

                self.image_cache[key] = ctk.CTkImage(
                    light_image=img, dark_image=img, size=(50, 50)
                )

            except Exception as e:
                print("ICON ERROR:", name, e)

                # Solid, fully-opaque placeholder so a missing icon is
                # still visible (and obviously a placeholder) rather than
                # silently invisible.
                img = Image.new("RGBA", (50, 50), (180, 180, 180, 255))
                self.image_cache[key] = ctk.CTkImage(
                    light_image=img, dark_image=img, size=(50, 50)
                )

        return self.image_cache[key]

    def load_badge(self, theme):
        if not theme:
            return None

        theme_clean = theme.strip().lower()
        key = f"badge_{theme_clean}"

        if key not in self.image_cache:
            try:
                filename = self.badge_map.get(theme_clean)

                if not filename:
                    print("NO BADGE:", theme_clean)
                    return None

                path = resource_path(
                    os.path.join("assets", "images", "badges", filename)
                )
                img = Image.open(path).convert("RGBA")
                img.thumbnail((70, 70))

                canvas = Image.new("RGBA", (70, 70), (0, 0, 0, 0))
                canvas.paste(img, ((70 - img.width) // 2, (70 - img.height) // 2), img)

                # CTkImage (not ImageTk.PhotoImage) - CTkLabel needs this
                # to scale correctly on HighDPI displays, and raw
                # PhotoImage was triggering a UserWarning about it.
                self.image_cache[key] = ctk.CTkImage(
                    light_image=canvas, dark_image=canvas, size=(70, 70)
                )

            except Exception as e:
                print("BADGE ERROR:", e)
                return None

        return self.image_cache[key]

    def _badge_path(self, theme):
        if not theme:
            return None
        filename = self.badge_map.get(theme.strip().lower())
        if not filename:
            return None
        return resource_path(os.path.join("assets", "images", "badges", filename))

    def _badge_avg_color(self, theme):
        key = (theme or "").strip().lower()
        if key not in self.badge_color_cache:
            path = self._badge_path(theme)
            self.badge_color_cache[key] = average_badge_color(path) if path else None
        return self.badge_color_cache[key]

    # -----------------------------------------------------------
    # PROJECT CARDS
    # -----------------------------------------------------------

    def _apply_tier_badge(self, index, tier):
        style = TIER_STYLES.get(tier, TIER_STYLES["basic"])
        badge = self.project_tier_badges[index]
        badge.configure(text=style["label"], fg_color=style["bg"], text_color=style["fg"])

    def _resolve_tk_color_to_rgb(self, color):
        r16, g16, b16 = self.root.winfo_rgb(color)
        return (r16 // 256, g16 // 256, b16 // 256)

    def _blend_rgb_to_hex(self, base_rgb, tint_rgb, opacity):
        r = int(tint_rgb[0] * opacity + base_rgb[0] * (1 - opacity))
        g = int(tint_rgb[1] * opacity + base_rgb[1] * (1 - opacity))
        b = int(tint_rgb[2] * opacity + base_rgb[2] * (1 - opacity))
        return f"#{r:02x}{g:02x}{b:02x}"

    def _apply_card_fill(self, index, project):
        """Tints the card's background toward its badge's average color,
        blended against the real theme default (see _card_fill_rgb_default)
        for both light and dark mode - CTk fills are solid, not
        alpha-transparent, so this precomputes an actual blended hex
        rather than layering a translucent overlay (contrast the
        Streamlit version's simpler rgba() approach)."""
        frame, _title = self.project_frames[index]

        if project and project.get("symbiosis") and project.get("symbiosis_badges"):
            theme_values = [value for _dim, value in project["symbiosis_badges"]]
        else:
            theme_values = [project.get("theme")] if project else []

        colors = [c for c in (self._badge_avg_color(v) for v in theme_values) if c]

        if not colors:
            frame.configure(fg_color=self._card_fill_color_default)
            return

        avg = tuple(sum(c[i] for c in colors) // len(colors) for i in range(3))
        light_base, dark_base = self._card_fill_rgb_default
        light_hex = self._blend_rgb_to_hex(light_base, avg, CARD_TINT_OPACITY)
        dark_hex = self._blend_rgb_to_hex(dark_base, avg, CARD_TINT_OPACITY)
        frame.configure(fg_color=(light_hex, dark_hex))

    def _apply_card_border(self, index, symbiosis):
        frame, _title = self.project_frames[index]
        if symbiosis:
            frame.configure(border_width=CARD_BORDER_WIDTH_SYMBIOSIS, border_color=CARD_BORDER_COLOR_SYMBIOSIS)
        else:
            frame.configure(border_width=CARD_BORDER_WIDTH_DEFAULT, border_color=self._card_border_color_default)

    def _apply_lock_button(self, index):
        button = self.project_lock_buttons[index]
        if index in self.locked_projects:
            button.configure(text="\U0001F512", fg_color=LOCK_FILL_LOCKED, hover_color=LOCK_FILL_LOCKED)
        else:
            button.configure(text="\U0001F513", fg_color=LOCK_FILL_UNLOCKED, hover_color=LOCK_FILL_UNLOCKED)

    def _toggle_lock(self, index):
        project = self.current_projects[index]
        if not project:
            return  # nothing generated for this card yet - nothing to lock

        if index in self.locked_projects:
            del self.locked_projects[index]
        else:
            self.locked_projects[index] = project

        self._apply_lock_button(index)

    def render_project(self, container, project, lookup):
        for widget in container.winfo_children():
            widget.destroy()

        reward = get_project_reward(project, lookup)

        info_row = ctk.CTkFrame(container, fg_color="transparent")
        info_row.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(
            info_row,
            text=f"1st  {reward['first']}",
            font=("Arial", 11, "bold"),
            text_color=REWARD_FIRST["fg"],
            fg_color=REWARD_FIRST["bg"],
            corner_radius=6,
            width=54,
            height=22
        ).pack(side="left", padx=(0, 6))

        ctk.CTkLabel(
            info_row,
            text=f"2nd  {reward['second']}",
            font=("Arial", 11, "bold"),
            text_color=REWARD_SECOND["fg"],
            fg_color=REWARD_SECOND["bg"],
            corner_radius=6,
            width=54,
            height=22
        ).pack(side="left")

        theme = project.get("theme")
        symbiosis_badges = project.get("symbiosis_badges") if project.get("symbiosis") else None

        if symbiosis_badges:
            # All 3 shared dimensions (habitat, group, tag) get their own
            # badge side by side, instead of just the project's own
            # generation theme - see core.project_naming.symbiosis_badge_traits.
            badge_frame = ctk.CTkFrame(container, fg_color="transparent")
            badge_frame.pack(pady=(0, 8))

            icons_row = ctk.CTkFrame(badge_frame, fg_color="transparent")
            icons_row.pack()

            label_parts = []
            icon_images = []
            for _dim, value in symbiosis_badges:
                icon = self.load_badge(value)
                if not icon:
                    continue
                icon_label = ctk.CTkLabel(icons_row, image=icon, text="")
                icon_label.image = icon
                icon_label.pack(side="left", padx=4)
                icon_images.append(icon)
                label_parts.append(value.upper())
            icons_row.images = icon_images

            if label_parts:
                ctk.CTkLabel(
                    badge_frame, text=" · ".join(label_parts), font=("Arial", 12, "bold"),
                    text_color=("#1a1a1a", "#f0f0f0")
                ).pack()
        else:
            badge = self.load_badge(theme)

            if badge:
                badge_frame = ctk.CTkFrame(container, fg_color="transparent")
                badge_frame.pack(pady=(0, 8))

                badge_label = ctk.CTkLabel(badge_frame, image=badge, text="")
                badge_label.image = badge
                badge_label.pack()

                ctk.CTkLabel(
                    badge_frame, text=theme.upper(), font=("Arial", 13, "bold"),
                    text_color=("#1a1a1a", "#f0f0f0")
                ).pack()

        # Divider - keeps name/badge/points visually separate from the
        # animal list below, inside the same card.
        ctk.CTkFrame(container, height=1, fg_color=DIVIDER_COLOR).pack(fill="x", pady=(4, 10))

        rows_frame = ctk.CTkFrame(container, fg_color="transparent")
        rows_frame.pack(fill="both", expand=True)

        rows_frame.grid_columnconfigure(0, weight=0)
        rows_frame.grid_columnconfigure(1, weight=1)

        for i, entry in enumerate(project.get("animals", [])):
            parts = entry.split(" OR ")

            if len(parts) == 1:
                # No OR - skip the wrapper frames and grid the icon/text
                # labels directly. This is the vast majority of rows
                # (~93% of rows across real games have no OR) and it cuts
                # 2 CTkFrame creations per row - CTkFrame's custom
                # rounded-rect canvas drawing was, by far, the biggest
                # cost in re-rendering all 5 project cards on every
                # "Generate Game" click (profiled: ~700ms/click, almost
                # entirely in widget creation/destruction, not in the
                # actual game-generation logic which takes ~4ms).
                name = parts[0].strip()
                tokens = name.split()

                if tokens and tokens[-1].isdigit():
                    multiplier = tokens[-1]
                    name = " ".join(tokens[:-1])
                else:
                    multiplier = None

                icon = self.load_icon(name, "normal")

                icon_label = ctk.CTkLabel(rows_frame, image=icon, text="")
                icon_label.image = icon
                icon_label.grid(row=i, column=0, sticky="w", padx=(0, 5), pady=3)

                text = name
                if multiplier:
                    text += f" x{multiplier}"

                ctk.CTkLabel(
                    rows_frame, text=text, font=("Arial", 10),
                    wraplength=ANIMAL_NAME_WRAP_WIDTH, justify="left", anchor="w"
                ).grid(row=i, column=1, sticky="w", padx=5, pady=3)
                continue

            icon_cell = ctk.CTkFrame(rows_frame, fg_color="transparent")
            icon_cell.grid(row=i, column=0, sticky="w", padx=(0, 5), pady=3)

            images = []
            texts = []

            for j, part in enumerate(parts):
                name = part.strip()
                tokens = name.split()

                if tokens and tokens[-1].isdigit():
                    multiplier = tokens[-1]
                    name = " ".join(tokens[:-1])
                else:
                    multiplier = None

                variant = "normal" if j == 0 else "alt"
                icon = self.load_icon(name, variant)
                images.append(icon)

                ctk.CTkLabel(icon_cell, image=icon, text="").pack(
                    side="left", padx=(1 if j else 0, 2)
                )

                text = name
                if multiplier:
                    text += f" x{multiplier}"
                texts.append(text)

            icon_cell.images = images

            # One wrapped label for the whole "A OR B" phrase instead of
            # separate packed sub-labels per option - those don't wrap as
            # a cohesive unit (each piece wraps on its own, breaking the
            # row's alignment). The icons already carry the primary/alt
            # distinction via their opacity, so losing the alt option's
            # separate gray text color here isn't a real loss.
            ctk.CTkLabel(
                rows_frame, text=" OR ".join(texts), font=("Arial", 10),
                wraplength=ANIMAL_NAME_WRAP_WIDTH, justify="left", anchor="w"
            ).grid(row=i, column=1, sticky="w", padx=5, pady=3)

    # -----------------------------------------------------------
    # SUMMARY BAR
    # -----------------------------------------------------------

    def _on_summary_resize(self, event=None):
        width = event.width if event else self.summary_content.winfo_width()
        wrap = max(width - 90, 100)
        for lbl in self._summary_value_labels:
            lbl.configure(wraplength=wrap)

    def render_summary(self, game_animals):
        for widget in self.summary_content.winfo_children():
            widget.destroy()
        self._summary_value_labels = []

        lvl0, lvl1, lvl2, lvl3, special, habitat_counts, group_counts = group_animals(game_animals)

        def format_counts(counts):
            return [f"{name.title()} ({count})" for name, count in sorted(counts.items())]

        groups = [
            ("Habitats", format_counts(habitat_counts)),
            ("Groups", format_counts(group_counts)),
            ("Lvl 1", lvl1),
            ("Lvl 2", lvl2),
            ("Lvl 3", lvl3),
            ("Cospecies", lvl0),
            ("Special", special),
        ]

        # Each category gets its own row and wraps within the available
        # width instead of one long row overflowing past the window edge.
        for title, items in groups:
            if not items:
                continue

            row = ctk.CTkFrame(self.summary_content, fg_color="transparent")
            row.pack(fill="x", anchor="w", pady=1)

            ctk.CTkLabel(
                row, text=f"{title}:", font=("Arial", 11, "bold"),
                text_color="gray60", width=70, anchor="nw"
            ).pack(side="left", anchor="n")

            value_label = ctk.CTkLabel(
                row, text=", ".join(items), font=("Arial", 11),
                anchor="w", justify="left"
            )
            value_label.pack(side="left", fill="x", expand=True, anchor="n")
            self._summary_value_labels.append(value_label)

        self._on_summary_resize()

    # -----------------------------------------------------------
    # GENERATE
    # -----------------------------------------------------------

    def generate(self):
        # Fresh random seed every plain "Generate Game" click - explicit
        # rather than left to whatever state Python's global random
        # happens to be in, so it can be shown/saved/replayed later.
        self._run_generation(random.randint(0, 2**31 - 1))

    def _use_typed_seed(self):
        text = self.seed_input_var.get().strip()
        if not text:
            return
        try:
            seed = int(text)
        except ValueError:
            messagebox.showerror("Error", "Seed must be a whole number.")
            return
        self._run_generation(seed)

    def _run_generation(self, seed):
        required = list(self.required_state)
        forced = [name for name, state in self.required_state.items() if state == "forced"]
        predefined = self.predefined if self.include_predefined_var.get() else []

        active_packs = self._active_packs()
        if not active_packs:
            messagebox.showerror("Error", "No packs selected - check at least one pack.")
            return

        animals = [a for a in self.animals if a["pack"] in active_packs]

        # A locked project's animals only make sense against the pool they
        # were drawn from, so reuse the last pool instead of resampling a
        # new one while anything is locked - unlock everything to force a
        # fresh pool (and ignore pack/required changes in the meantime).
        if self.locked_projects and self.last_game_animals is not None:
            pool_kwargs = {"game_animals": self.last_game_animals, "lookup": self.last_lookup}
        else:
            pool_kwargs = {}

        random.seed(seed)

        mode = self.generation_mode_toggle.get().lower()

        try:
            game, game_animals, lookup = generate_full_game(
                animals, required, predefined,
                locked_projects=self.locked_projects,
                mode=mode,
                forced=forced,
                **pool_kwargs
            )
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return

        self.current_seed = seed
        self.seed_display_var.set(str(seed))
        self.current_projects = game
        self.last_game_animals = game_animals
        self.last_lookup = lookup

        for i, p in enumerate(game):
            frame, title = self.project_frames[i]
            container = self.project_containers[i]

            full_title = f"Project {i + 1}: {p.get('name', 'Unnamed')}"
            title.configure(text=fit_multi_line(full_title, self.title_font, TITLE_WRAP_WIDTH, TITLE_MAX_LINES))
            self._apply_tier_badge(i, p.get("tier"))
            self._apply_lock_button(i)
            self._apply_card_border(i, p.get("symbiosis", False))
            self._apply_card_fill(i, p)
            self.render_project(container, p, lookup)

        self.render_summary(game_animals)

    # -----------------------------------------------------------
    # SAVE / LOAD SEEDS
    # -----------------------------------------------------------

    def _save_current_seed(self):
        if self.current_seed is None:
            messagebox.showerror("Error", "Generate a game first before saving its seed.")
            return

        name = simpledialog.askstring("Save Seed", "Name for this seed:", parent=self.root)
        if not name:
            return

        entry = {
            "name": name,
            "seed": self.current_seed,
            "active_packs": sorted(self._active_packs()),
            "required_animals": sorted(self.required_state),
            "forced_animals": sorted(n for n, s in self.required_state.items() if s == "forced"),
            "include_predefined": self.include_predefined_var.get(),
            "saved_at": datetime.now().isoformat(timespec="seconds"),
        }
        save_seed_entry(entry)
        messagebox.showinfo("Saved", f'Seed "{name}" saved.')

    def _open_load_seed_window(self):
        entries = load_saved_seeds()

        win = ctk.CTkToplevel(self.root)
        win.title("Load Saved Seed")
        win.geometry("440x420")
        win.transient(self.root)

        if not entries:
            ctk.CTkLabel(
                win, text="No saved seeds yet.", text_color="gray60"
            ).pack(pady=20)
            return

        scroll = ctk.CTkScrollableFrame(win)
        scroll.pack(fill="both", expand=True, padx=10, pady=10)

        for entry in sorted(entries, key=lambda e: e.get("saved_at", ""), reverse=True):
            row = ctk.CTkFrame(scroll, fg_color="transparent")
            row.pack(fill="x", pady=4)

            info = ctk.CTkFrame(row, fg_color="transparent")
            info.pack(side="left", fill="x", expand=True)

            ctk.CTkLabel(
                info, text=entry.get("name", "Unnamed"),
                font=("Arial", 12, "bold"), anchor="w"
            ).pack(anchor="w")

            packs = ", ".join(entry.get("active_packs", []))
            ctk.CTkLabel(
                info, text=f"seed {entry.get('seed')} - packs: {packs}",
                font=("Arial", 10), text_color="gray60", anchor="w"
            ).pack(anchor="w")

            ctk.CTkButton(
                row, text="Delete", width=60, height=24,
                fg_color="#8a2f2f", hover_color="#6b2323",
                command=lambda e=entry, w=win: self._delete_seed_entry(e, w)
            ).pack(side="right")

            ctk.CTkButton(
                row, text="Load", width=60, height=24,
                command=lambda e=entry, w=win: self._load_seed_entry(e, w)
            ).pack(side="right", padx=(0, 4))

    def _load_seed_entry(self, entry, window):
        window.destroy()

        active = set(entry.get("active_packs", []))
        for pack, var in self.pack_vars.items():
            var.set(pack in active)

        # "forced_animals" doesn't exist in seeds saved before the
        # pool-vs-forced distinction was added - absent means none of
        # them were forced, not that the key is missing/broken.
        forced_names = set(entry.get("forced_animals", []))
        self.required_state = {
            n: ("forced" if n in forced_names else "pool")
            for n in entry.get("required_animals", [])
            if n in self.animals_by_name
        }
        for name in self.animal_rows:
            self._apply_row_selection_style(name, self.required_state.get(name))
        self._refresh_required_chips()
        self.refresh_animal_list()

        self.include_predefined_var.set(entry.get("include_predefined", True))

        # Loading a saved seed replays a whole specific game - locks (and
        # the pool they'd otherwise pin) don't make sense layered on top.
        self.locked_projects = {}
        self.last_game_animals = None
        self.last_lookup = None
        for i in range(5):
            self._apply_lock_button(i)

        self._run_generation(entry["seed"])

    def _delete_seed_entry(self, entry, window):
        delete_seed_entry(entry.get("name", ""))
        window.destroy()
        self._open_load_seed_window()
