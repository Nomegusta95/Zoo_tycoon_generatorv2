# card_export.py
#
# Renders a single project as a print-ready PNG matching the real board
# game's physical project card (4cm x 6.5cm) - shared between the desktop
# app and the web app so both produce byte-identical output from the same
# layout code. Pillow-only (no tkinter/streamlit), same pattern as
# gui/theme_data.py.
#
# The left-column badges (leaf icon, two reward number squares) and the
# card background/border are measured directly from a clean reference
# photo of a real blank card (assets/images/template/project.png, 4cm x
# 6.5cm) - see REWARD_SQUARE_1/2 below, in that photo's ORIGINAL
# 2670x4428 pixel space (the file on disk has since been downsampled to
# ~1350px wide to shrink the repo - _s() below still scales from 2670,
# since that's the space the measurements themselves were taken in, and
# template.resize() maps whatever the file's current resolution is onto
# CARD_WIDTH_PX/CARD_HEIGHT_PX regardless). The badge-illustration and
# animal-row areas aren't present on the blank template (they vary per
# project on a real card), so those are original layout choices matched
# to the same color palette and proportions rather than measured.

import os

from PIL import Image, ImageDraw, ImageFont

from gui.theme_data import BADGE_MAP, LEVEL3_ANIMAL_BADGES, project_level3_badge_values
from scoring.project_cost import expand_entry

# --- PHYSICAL SIZE ---
# 4cm x 6.5cm, at the reference template photo's own aspect ratio
# (2670:4428) rather than a separately-computed one - the template's
# measured badge positions are only correct if the final canvas preserves
# the exact proportions they were measured in.
CARD_WIDTH_PX = 900
CARD_HEIGHT_PX = round(CARD_WIDTH_PX * 4428 / 2670)

_SCALE = CARD_WIDTH_PX / 2670


def _s(value):
    """Scales a measurement taken in the 2670px-wide reference template
    to the actual render canvas size."""
    return round(value * _SCALE)


TEMPLATE_PATH_PARTS = ("assets", "images", "template", "project.png")
FONT_REGULAR_PATH_PARTS = ("assets", "fonts", "DejaVuSans.ttf")
FONT_BOLD_PATH_PARTS = ("assets", "fonts", "DejaVuSans-Bold.ttf")
BADGE_DIR_PARTS = ("assets", "images", "badges")
ANIMAL_ICON_DIR_PARTS = ("assets", "images", "animals")

# --- MEASURED (from the clean reference template) ---
REWARD_SQUARE_1 = (182, 726, 626, 1167)   # 1st place reward number
REWARD_SQUARE_2 = (182, 1333, 626, 1774)  # 2nd place reward number (left-aligned with square 1)

# --- DESIGNED (not on the blank template - matched to its palette/proportions) ---
BADGE_ICON_BOX = (750, 120, 2550, 1100)    # area for the theme badge icon(s)
NAME_BOX = (700, 1150, 2590, 1460)         # project name banner below the badge icon
DIVIDER_Y = 1850                           # below REWARD_SQUARE_2's measured bottom (1774)
ROW_START_Y = 1950
ROW_HEIGHT = 480                           # 5 rows max: 1950 + 5*480 = 4350, within the 4428-tall card
ROW_ICON_SIZE = 360
ROW_TEXT_X = 960                           # nudged right of LEFT_MARGIN+2*ROW_ICON_SIZE so an OR row's two icons never crowd the text
ROW_TEXT_RIGHT_MARGIN = 90
LEFT_MARGIN = 178

TEXT_BROWN = (60, 45, 34)  # animal names, divider
TEXT_WHITE = (255, 255, 255)
TEXT_BLACK = (0, 0, 0)  # project name, multiplier numbers, "OR"
SYMBIOSIS_BORDER_COLOR = (201, 162, 39)  # matches CARD_BORDER_COLOR_SYMBIOSIS in gui/app.py


def _asset_path(base_dir, path_parts):
    return os.path.join(base_dir, *path_parts)


# Keyed by base_dir - decoding the 4.8MB template photo and resizing it
# down is by far the most expensive part of a render (~400ms, profiled),
# and it's identical every time for a given base_dir, so it's only ever
# done once per process instead of on every single card rendered.
_TEMPLATE_CACHE = {}
_FONT_CACHE = {}


def _get_base_card(base_dir):
    if base_dir not in _TEMPLATE_CACHE:
        template = Image.open(_asset_path(base_dir, TEMPLATE_PATH_PARTS)).convert("RGBA")
        _TEMPLATE_CACHE[base_dir] = template.resize((CARD_WIDTH_PX, CARD_HEIGHT_PX), Image.LANCZOS)
    return _TEMPLATE_CACHE[base_dir].copy()


def _load_font(base_dir, bold, size):
    key = (base_dir, bold, size)
    if key not in _FONT_CACHE:
        parts = FONT_BOLD_PATH_PARTS if bold else FONT_REGULAR_PATH_PARTS
        _FONT_CACHE[key] = ImageFont.truetype(_asset_path(base_dir, parts), size)
    return _FONT_CACHE[key]


def _text_size(draw, text, font):
    box = draw.textbbox((0, 0), text, font=font)
    return box[2] - box[0], box[3] - box[1]


def _fit_font(draw, text, base_dir, bold, max_width, max_size, min_size=18):
    """Largest font size (within [min_size, max_size]) that fits text
    within max_width on one line."""
    size = max_size
    while size > min_size:
        font = _load_font(base_dir, bold, size)
        w, _h = _text_size(draw, text, font)
        if w <= max_width:
            return font
        size -= 2
    return _load_font(base_dir, bold, min_size)


def _wrap_text(draw, text, font, max_width):
    words = text.split()
    lines = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        w, _h = _text_size(draw, candidate, font)
        if w <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _fit_font_wrapped(draw, text, base_dir, bold, max_width, max_size, max_lines=2, min_size=18):
    """Largest font size (within [min_size, max_size]) whose word-wrapped
    layout fits within max_lines lines of max_width - unlike _fit_font,
    which only ever considers one line and so shrinks a long entry (e.g.
    a multi-word OR pair) all the way down to fit, this lets it drop to a
    second line instead and stay bigger."""
    size = max_size
    while size > min_size:
        font = _load_font(base_dir, bold, size)
        lines = _wrap_text(draw, text, font, max_width)
        if len(lines) <= max_lines:
            return font, lines
        size -= 2
    font = _load_font(base_dir, bold, min_size)
    return font, _wrap_text(draw, text, font, max_width)


def _draw_row_line(draw, x, y, line, font, base_color):
    """Draws one line word-by-word instead of as a single colored string -
    a multiplier count and the literal word "OR" always render in
    TEXT_BLACK (OR also underlined) regardless of the row's own brown/
    green scheme, which stays on every other word."""
    space_w = _text_size(draw, " ", font)[0]
    cur_x = x
    for word in line.split(" "):
        if not word:
            continue
        is_or = word == "OR"
        color = TEXT_BLACK if (word.isdigit() or is_or) else base_color
        draw.text((cur_x, y), word, font=font, fill=color)
        bbox = draw.textbbox((cur_x, y), word, font=font)
        if is_or:
            underline_y = bbox[3] + max(2, (bbox[3] - bbox[1]) // 12)
            draw.line(
                [(bbox[0], underline_y), (bbox[2], underline_y)],
                fill=TEXT_BLACK, width=max(3, (bbox[3] - bbox[1]) // 14)
            )
        cur_x += (bbox[2] - bbox[0]) + space_w


def _load_icon_rgba(path, box_size):
    try:
        img = Image.open(path).convert("RGBA")
    except Exception:
        img = Image.new("RGBA", (box_size, box_size), (0, 0, 0, 0))

    # img.thumbnail() only ever shrinks, never upscales - badge source art
    # (~140px) is much smaller than the printed badge area, so this needs
    # an explicit resize (either direction) rather than thumbnail().
    scale = box_size / max(img.width, img.height)
    new_size = (max(1, round(img.width * scale)), max(1, round(img.height * scale)))
    img = img.resize(new_size, Image.LANCZOS)

    canvas = Image.new("RGBA", (box_size, box_size), (0, 0, 0, 0))
    canvas.paste(img, ((box_size - img.width) // 2, (box_size - img.height) // 2), img)
    return canvas


def _paste_centered(base, overlay, box):
    x0, y0, x1, y1 = box
    bw, bh = x1 - x0, y1 - y0
    ox = x0 + (bw - overlay.width) // 2
    oy = y0 + (bh - overlay.height) // 2
    base.paste(overlay, (ox, oy), overlay)


def _format_row(entry):
    """One animal row's (icon_paths_with_variant, display_text) - text
    color is decided per-word when drawn (see _draw_row_line), not per
    row, so there's no is_or here."""
    parts = entry.split(" OR ")
    icons = []
    texts = []
    for j, part in enumerate(parts):
        tokens = part.strip().split()
        multiplier = None
        if tokens and tokens[-1].isdigit():
            multiplier = tokens[-1]
            tokens = tokens[:-1]
        name = " ".join(tokens)
        icons.append((name, "normal" if j == 0 else "alt"))
        # Matches the real card's own convention: quantity prefixes the
        # name ("9 MAGELLANIC PENGUINS") rather than an "xN" suffix.
        texts.append(f"{multiplier} {name}".upper() if multiplier else name.upper())
    display = " OR ".join(texts)
    return icons, display


def render_project_card(project, lookup, reward, base_dir):
    """Renders one project as a PIL.Image sized CARD_WIDTH_PX x
    CARD_HEIGHT_PX. base_dir: absolute path to the repo root (desktop:
    resource_path(""), streamlit: BASE_DIR) - both frontends resolve
    their own asset paths differently (PyInstaller extraction dir vs a
    plain relative path), so this takes the resolved root rather than
    importing either frontend's own path helper."""
    card = _get_base_card(base_dir)
    draw = ImageDraw.Draw(card)

    # --- REWARD NUMBERS ---
    for box, value in ((REWARD_SQUARE_1, reward["first"]), (REWARD_SQUARE_2, reward["second"])):
        x0, y0, x1, y1 = (_s(v) for v in box)
        text = str(value)
        font = _fit_font(draw, text, base_dir, True, x1 - x0 - _s(40), _s(280))
        tw, th = _text_size(draw, text, font)
        draw.text((x0 + (x1 - x0 - tw) // 2, y0 + (y1 - y0 - th) // 2 - _s(20)), text, font=font, fill=TEXT_WHITE)

    # --- THEME BADGE ICON(S) ---
    # A level-3 animal's own badge (see gui.theme_data.LEVEL3_ANIMAL_BADGES)
    # takes over the badge row entirely when the project contains one -
    # level-3s are the rarest species, so they get marquee treatment
    # instead of the usual theme/symbiosis category badge(s).
    symbiosis = project.get("symbiosis") and project.get("symbiosis_badges")
    theme_values = [v for _dim, v in project["symbiosis_badges"]] if symbiosis else [project.get("theme")]
    level3_values = project_level3_badge_values(project, lookup)
    badge_values = level3_values if level3_values else theme_values

    badge_box = tuple(_s(v) for v in BADGE_ICON_BOX)
    bw, bh = badge_box[2] - badge_box[0], badge_box[3] - badge_box[1]
    icon_size = min(bw, bh) if len(badge_values) == 1 else min(bw // len(badge_values), bh)
    icons = []
    for value in badge_values:
        key = (value or "").strip().lower()
        filename = BADGE_MAP.get(key) or LEVEL3_ANIMAL_BADGES.get(key)
        if not filename:
            continue
        path = _asset_path(base_dir, BADGE_DIR_PARTS + (filename,))
        icons.append(_load_icon_rgba(path, icon_size))
    if icons:
        total_w = sum(i.width for i in icons) + _s(20) * (len(icons) - 1)
        start_x = badge_box[0] + (bw - total_w) // 2
        y = badge_box[1] + (bh - icons[0].height) // 2
        for icon in icons:
            card.paste(icon, (start_x, y), icon)
            start_x += icon.width + _s(20)

    # --- PROJECT NAME ---
    name_box = tuple(_s(v) for v in NAME_BOX)
    nx0, ny0, nx1, ny1 = name_box
    name_text = (project.get("name") or "").upper()
    name_font, lines = _fit_font_wrapped(draw, name_text, base_dir, True, nx1 - nx0, _s(150), min_size=_s(60))
    lines = lines[:2]
    line_h = _text_size(draw, "Ag", name_font)[1] + _s(15)
    total_h = line_h * len(lines)
    ty = ny0 + max(0, (ny1 - ny0 - total_h) // 2)
    for line in lines:
        lw, _lh = _text_size(draw, line, name_font)
        draw.text((nx0 + (nx1 - nx0 - lw) // 2, ty), line, font=name_font, fill=TEXT_BLACK)
        ty += line_h

    # --- DIVIDER ---
    div_y = _s(DIVIDER_Y)
    draw.line([(_s(LEFT_MARGIN), div_y), (CARD_WIDTH_PX - _s(LEFT_MARGIN), div_y)], fill=TEXT_BROWN, width=_s(6))

    # --- ANIMAL ROWS ---
    row_y = _s(ROW_START_Y)
    row_h = _s(ROW_HEIGHT)
    icon_size = _s(ROW_ICON_SIZE)
    text_x = _s(ROW_TEXT_X)
    text_right = CARD_WIDTH_PX - _s(ROW_TEXT_RIGHT_MARGIN)
    row_font_size = _s(95)

    for entry in project.get("animals", []):
        icon_specs, display_text = _format_row(entry)

        icon_x = _s(LEFT_MARGIN)
        icon_y = row_y + (row_h - icon_size) // 2
        for name, variant in icon_specs:
            path = _asset_path(base_dir, ANIMAL_ICON_DIR_PARTS + (f"{name.lower().replace(' ', '_')}.png",))
            icon = _load_icon_rgba(path, icon_size)
            if variant == "alt":
                alpha = icon.split()[3].point(lambda p: int(p * 0.55))
                icon.putalpha(alpha)
            card.paste(icon, (icon_x, icon_y), icon)
            icon_x += icon_size + _s(15)

        font, text_lines = _fit_font_wrapped(
            draw, display_text, base_dir, True, text_right - text_x, row_font_size, min_size=_s(45)
        )
        line_h = _text_size(draw, "Ag", font)[1] + _s(12)
        ty = row_y + (row_h - line_h * len(text_lines)) // 2
        for line in text_lines:
            _draw_row_line(draw, text_x, ty, line, font, TEXT_BROWN)
            ty += line_h

        row_y += row_h

    # --- SYMBIOSIS BORDER --- (matches the gold card-frame both frontends use)
    if symbiosis:
        border_w = _s(30)
        inset = border_w // 2
        draw.rounded_rectangle(
            [inset, inset, CARD_WIDTH_PX - 1 - inset, CARD_HEIGHT_PX - 1 - inset],
            radius=_s(70), outline=SYMBIOSIS_BORDER_COLOR, width=border_w
        )

    return card.convert("RGB")
