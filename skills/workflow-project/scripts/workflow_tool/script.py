"""Arabic text, ready to draw: letters joined, and the line put in the order it sits on the page.

reportlab draws a string left to right, one glyph per character, and joins nothing. So this file does
the two jobs a text engine would do, with nothing but the Unicode tables Python ships with:

  1. joining: every Arabic letter is swapped for its start, middle, end or alone shape (and lam + alef
     for their one combined shape), taken from Unicode's own "presentation forms" (a letter standing alone stays the plain letter);
  2. ordering: Arabic runs right to left, while a number or a run of Latin words inside it keeps its
     own left-to-right order.

It knows nothing about fonts, pages or reportlab.
"""

import unicodedata

_SHAPES = ("isolated", "final", "initial", "medial")
_FORMS = {}        # one letter, or lam + alef  ->  {"isolated": ch, "final": ch, ...}
for _code in range(0xFE70, 0xFEFD):
    _parts = unicodedata.decomposition(chr(_code)).split()
    if not _parts or _parts[0][1:-1] not in _SHAPES:
        continue
    _letters = "".join(chr(int(p, 16)) for p in _parts[1:])
    if " " in _letters or "ـ" in _letters:        # spacing forms of the vowel marks: not letters
        continue
    _FORMS.setdefault(_letters, {})[_parts[0][1:-1]] = chr(_code)
_FORMS["ـ"] = dict.fromkeys(_SHAPES, "ـ")    # tatweel joins on both sides and never changes

_MIRRORED = {"(": ")", ")": "(", "[": "]", "]": "[", "{": "}", "}": "{", "<": ">", ">": "<",
             "«": "»", "»": "«"}
_BETWEEN_DIGITS = ".,:/-٫٬"


def is_arabic(ch):
    """True for a character the Arabic font draws (letters, marks, Arabic digits and punctuation)."""
    return "؀" <= ch <= "ۿ" or "ﭐ" <= ch <= "ﻼ"


def is_mark(ch):
    """True for a vowel mark or shadda: it sits on its letter and takes no room of its own."""
    return unicodedata.combining(ch) != 0


def has_arabic(text):
    return any(is_arabic(ch) for ch in text)


def unsupported(text):
    """Arabic-script letters this file cannot join (Persian or Urdu letters, for example)."""
    return sorted({ch for ch in text if "؀" <= ch <= "ۿ" and unicodedata.category(ch) == "Lo"
                   and ch not in _FORMS})


class _Unit(object):
    """One letter as drawn (already in its joined shape), the marks on it, and where it came from."""

    def __init__(self, text, index):
        self.text = text
        self.marks = []            # [(mark, its place in the original text)]
        self.index = index
        self.kind = ""             # "R" Arabic, "L" Latin, "N" number, "" not yet decided


def _units(text):
    """The text as joined letters, still in reading order."""
    units, i = [], 0
    while i < len(text):
        ch = text[i]
        if is_mark(ch) and units and units[-1].text in _FORMS:
            units[-1].marks.append((ch, i))
        elif text[i:i + 2] in _FORMS:
            units.append(_Unit(text[i:i + 2], i))
            i += 1
        else:
            units.append(_Unit(ch, i))
        i += 1

    def forms(k):
        return _FORMS.get(units[k].text, {}) if 0 <= k < len(units) else {}

    shapes = []
    for k in range(len(units)):
        mine = forms(k)
        if not mine:
            shapes.append(None)
            continue
        before = "initial" in forms(k - 1) and "final" in mine     # the letter before reaches forward
        after = "initial" in mine and "final" in forms(k + 1)      # this one reaches the next
        shapes.append("medial" if before and after else "final" if before else "initial" if after else "isolated")
    for unit, shape in zip(units, shapes):
        if shape:
            if shape == "isolated" and len(unit.text) == 1:
                continue        # an alone letter is the plain letter: every Arabic font has it
            unit.text = _FORMS[unit.text].get(shape) or (unit.text if len(unit.text) == 1 else _FORMS[unit.text]["isolated"])
    return units


def _decide(units, source):
    """Marks every unit Arabic (R), Latin (L) or number (N); what lies between takes its neighbours' side."""
    for k, unit in enumerate(units):
        kind = unicodedata.bidirectional(source[unit.index])
        if kind in ("R", "AL"):
            unit.kind = "R"
        elif kind == "L":
            unit.kind = "L"
        elif kind in ("EN", "AN"):
            unit.kind = "N"
    for k in range(1, len(units) - 1):          # 1.0, 10:30, 2026-10-02 stay one number
        if not units[k].kind and units[k].text in _BETWEEN_DIGITS and units[k - 1].kind == units[k + 1].kind == "N":
            units[k].kind = "N"
    strong = "R"
    for unit in units:                          # a number after a Latin word belongs to it ("Part 2")
        if unit.kind in ("R", "L"):
            strong = unit.kind
        elif unit.kind == "N" and strong == "L":
            unit.kind = "L"
    k = 0
    while k < len(units):                       # spaces and punctuation: Latin only between two Latin sides
        if units[k].kind:
            k += 1
            continue
        end = k
        while end < len(units) and not units[end].kind:
            end += 1
        left = units[k - 1].kind if k else "R"
        right = units[end].kind if end < len(units) else "R"
        for unit in units[k:end]:
            unit.kind = "L" if left == right == "L" else "R"
        k = end


def visual(text):
    """The text as it is drawn, left to right, in a right-to-left line.

    Returns [(character, its place in the original text)]. A mark comes just before the letter it
    sits on, so whoever draws it knows which letter that is.
    """
    units = _units(text)
    _decide(units, text)
    out, k = [], len(units)
    while k > 0:
        end = k
        k -= 1
        if units[k].kind == "R":
            unit = units[k]
            out += unit.marks
            out.append((_MIRRORED.get(unit.text, unit.text), unit.index))
            continue
        while k > 0 and units[k - 1].kind != "R":
            k -= 1
        for unit in units[k:end]:               # Latin words and numbers keep their own order
            out.append((unit.text, unit.index))
            out += unit.marks
    return out
