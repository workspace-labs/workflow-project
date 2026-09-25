"""The WorkSpace Labs look, in one place.

Every colour, font and text size the drawing uses is read from here, so the look can never
drift between pages or between agents. The values are the locked WorkSpace Labs video look
(light ground, Plus Jakarta Sans, one blue accent, red only for a real stop). Whose name, logo and
website appear is not the look: that is brand.py and assets/brand.json.
"""

import os

from reportlab.lib.colors import Color, HexColor
from reportlab.lib.fonts import addMapping
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont, TTFontFile

SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ASSETS = os.path.join(SKILL_ROOT, "assets")

# Colours
SPACE = HexColor("#F2F5FF")        # the pale ground (cover and last page)
INK = HexColor("#10182E")          # main words
INK_SOFT = HexColor("#4A5478")     # second lines, quieter text
INK_FAINT = HexColor("#8A93B2")    # footers, small labels
ACCENT = HexColor("#3E5BFF")       # one emphasis word, the normal path
GOLD = HexColor("#C4962E")         # decisions
RED = HexColor("#E03131")          # only for a real stop
WHITE = HexColor("#FFFFFF")
LINE = HexColor("#D6DCEF")
LINE_SOFT = HexColor("#E3E8F7")
BOX_STROKE = HexColor("#C9D1EA")
DECISION_FILL = HexColor("#FBF6EA")
LANE_TINT = HexColor("#FAFBFF")
CHIP_BG = HexColor("#EEF1FF")
CHIP_LINE = HexColor("#DDE3F8")
OTHER_PATH = HexColor("#9AA3C0")
TABLE_RULE = HexColor("#B9C1D9")
ZEBRA = HexColor("#F6F8FE")


def mix(base, tint, amount):
    """A solid colour that looks like `tint` laid over `base` at `amount` opacity."""
    return Color(
        base.red + (tint.red - base.red) * amount,
        base.green + (tint.green - base.green) * amount,
        base.blue + (tint.blue - base.blue) * amount,
    )


WASH_GOLD = mix(SPACE, GOLD, 0.10)
WASH_BLUE = mix(SPACE, ACCENT, 0.16)
GRID_LINE = mix(SPACE, HexColor("#283A78"), 0.05)
TAG_BG = mix(WHITE, ACCENT, 0.08)
TAG_LINE = mix(WHITE, ACCENT, 0.22)

# Fonts (static cuts of Plus Jakarta Sans, SIL Open Font License, see assets/fonts/OFL.txt)
REGULAR = "PJS-Regular"
MEDIUM = "PJS-Medium"
SEMIBOLD = "PJS-SemiBold"
BOLD = "PJS-Bold"
EXTRABOLD = "PJS-ExtraBold"
FAMILY = "PJS"
_FONT_FILES = {
    REGULAR: "PlusJakartaSans-Regular.ttf",
    MEDIUM: "PlusJakartaSans-Medium.ttf",
    SEMIBOLD: "PlusJakartaSans-SemiBold.ttf",
    BOLD: "PlusJakartaSans-Bold.ttf",
    EXTRABOLD: "PlusJakartaSans-ExtraBold.ttf",
}
_cmap = None


def register_fonts():
    """Makes the house fonts available to measuring and drawing. Safe to call twice."""
    global _cmap
    registered = pdfmetrics.getRegisteredFontNames()
    for name, filename in _FONT_FILES.items():
        if name not in registered:
            pdfmetrics.registerFont(TTFont(name, os.path.join(ASSETS, "fonts", filename)))
    addMapping(FAMILY, 0, 0, REGULAR)
    addMapping(FAMILY, 1, 0, BOLD)
    addMapping(FAMILY, 0, 1, REGULAR)
    addMapping(FAMILY, 1, 1, BOLD)
    if _cmap is None:
        _cmap = TTFontFile(os.path.join(ASSETS, "fonts", _FONT_FILES[REGULAR])).charToGlyph


def missing_characters(text):
    """Characters the house font cannot draw (they would print as empty boxes)."""
    register_fonts()
    return sorted({ch for ch in text if not ch.isspace() and ord(ch) not in _cmap})


def width(text, font, size):
    return pdfmetrics.stringWidth(text, font, size)


def tracked_width(text, font, size, tracking):
    """Width of letter-spaced text (small capital labels)."""
    return width(text, font, size) + tracking * max(len(text) - 1, 0)


def chip_lines(text, width_room, font=BOLD, size=6.2, tracking=0.7):
    """Splits a capital label into the lines it needs to fit the room (never cuts words off)."""
    words, lines, current = text.upper().split(), [], ""
    for word in words:
        candidate = word if not current else current + " " + word
        if tracked_width(candidate, font, size, tracking) <= width_room:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


# Text styles inside the swimlane: (font, size, line height)
STEP_TITLE = (BOLD, 8.4, 10.2)
STEP_DETAIL = (REGULAR, 7.2, 8.8)
DECISION_TEXT = (BOLD, 7.8, 9.2)
TERMINAL_TITLE = (SEMIBOLD, 7.4, 8.8)
TERMINAL_DETAIL = (REGULAR, 7.0, 8.4)
LANE_LABEL = (BOLD, 6.6)
BRANCH_LABEL = (BOLD, 7.2)
BADGE = (BOLD, 6.8)
