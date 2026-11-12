"""The look, in one place: the Board look the owner chose on 2026-11-12.

Every colour, font and text size the drawing uses is read from here, so the look can never drift
between pages or between agents: white pages lying sideways, ink-dark rules, one blue for the normal
path, amber for a question, red only for a real stop, and one font family, Alexandria, for English and
Arabic alike. Whose name, logo and website appear is not the look: that is brand.py and
assets/brand.json.

All text measuring goes through `width`, so a word is always measured exactly as it will be drawn.
"""

import functools
import os

from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont, TTFontFile

from . import language, script

SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ASSETS = os.path.join(SKILL_ROOT, "assets")

# Colours
WHITE = HexColor("#FFFFFF")
INK = HexColor("#0F1629")          # main words, the rules of the board, the cover's ground
INK_SOFT = HexColor("#586077")     # second lines, quieter text, the other paths
LINE = HexColor("#D9DEE8")         # hairlines
ACCENT = HexColor("#2B4BFF")       # the normal path, step numbers
LANE_TINT = HexColor("#EEF2FF")    # every other lane
STRIP = HexColor("#F6F7FA")        # the "what comes out" strip under the lanes
CHIP_BG = HexColor("#EEF1F7")
AMBER = HexColor("#B26A00")        # a question
AMBER_FILL = HexColor("#FFF4DB")
RED = HexColor("#E03131")          # only for a real stop
COVER_BLUE = HexColor("#4D68FF")   # the path on the dark cover
COVER_BLUE_SOFT = HexColor("#7C93FF")
COVER_SOFT = HexColor("#B9C2D8")   # quiet words on the dark cover
ACTOR_COLOURS = [ACCENT, INK, HexColor("#E0872A"), HexColor("#8A93A8"), HexColor("#0C9A8A"),
                 HexColor("#B0408F"), HexColor("#6B8E23"), HexColor("#7A5CF0")]

# Fonts (static cuts of Alexandria, SIL Open Font License, see assets/fonts/OFL-Alexandria.txt).
# One family draws Latin and Arabic, so both always match in weight.
REGULAR = "Alexandria-Regular"
MEDIUM = "Alexandria-Medium"
SEMIBOLD = "Alexandria-SemiBold"
BOLD = "Alexandria-Bold"
EXTRABOLD = "Alexandria-ExtraBold"
_FONTS = (REGULAR, MEDIUM, SEMIBOLD, BOLD, EXTRABOLD)
MARK_WIDTH = 0.2      # a vowel mark is about a fifth of the text size wide; used to centre it on its letter
_cmap = None


def register_fonts():
    """Makes the house fonts available to measuring and drawing. Safe to call twice."""
    global _cmap
    registered = pdfmetrics.getRegisteredFontNames()
    for name in _FONTS:
        if name not in registered:
            pdfmetrics.registerFont(TTFont(name, os.path.join(ASSETS, "fonts", name + ".ttf")))
    if _cmap is None:
        _cmap = TTFontFile(os.path.join(ASSETS, "fonts", REGULAR + ".ttf")).charToGlyph


def missing_characters(text, code=language.DEFAULT):
    """Characters the font cannot draw in that language (they would print as empty boxes)."""
    register_fonts()
    cannot_join = set()
    if language.load(code)["direction"] == "rtl":
        cannot_join = set(script.unsupported(text))
    return sorted({ch for ch in text if not ch.isspace() and (ch in cannot_join or ord(ch) not in _cmap)})


@functools.lru_cache(maxsize=8192)
def _segments(pieces):
    text = "".join(piece for piece, _ in pieces)
    owner = [k for k, (piece, _) in enumerate(pieces) for _ in piece]
    found = []
    for ch, index in script.visual(text):
        k = owner[index]
        font = pieces[k][1]
        mark = script.is_mark(ch)
        if found and not mark and not found[-1][3] and found[-1][1:3] == (font, k):
            found[-1] = (found[-1][0] + ch, font, k, False)
        else:
            found.append((ch, font, k, mark))
    return tuple(found)


def segments(pieces):
    """Right-to-left text cut into the stretches that are drawn one after another, left to right.

    `pieces` is [(text, font), ...] in reading order: one line, where each piece may have its own font.
    Returns [(text, font, which piece it came from, is it a mark)]. A mark is alone in its stretch and
    comes just before the letter it sits on.
    """
    return _segments(tuple(pieces))


def width(text, font, size):
    if not language.rtl():
        return pdfmetrics.stringWidth(text, font, size)
    return sum(pdfmetrics.stringWidth(part, face, size) for part, face, _, _ in segments([(text, font)]))


# Text styles on the board: (font, size, line height)
STEP_TITLE = (BOLD, 9.6, 12.2)
STEP_DETAIL = (REGULAR, 8.4, 11.0)
FLAG = (SEMIBOLD, 8.0, 10.2)         # "Starts when: ..." above a box, and a start, stop or end on its own
LANE_LABEL = (BOLD, 10.4, 13.0)
ANSWER = (BOLD, 7.2)                 # a decision's answer, in its small pill
BADGE = (BOLD, 8.2)
STRIP_NUMBER = (EXTRABOLD, 11.5)
STRIP_TEXT = (REGULAR, 8.2, 10.8)
