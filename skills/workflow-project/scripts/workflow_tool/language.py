"""The language the PDF is written in: its fixed words, its month names and its reading direction.

Each language is one small file, `assets/languages/<code>.json`. The workflow file picks one with
`"language"` in its project; English is the default. Adding a left-to-right language is adding a file.
"""

import json
import os

FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                      "assets", "languages")
DEFAULT = "en"
_loaded = {}
_current = DEFAULT      # ponytail: one language per run of the tool; pass it along if one run ever draws two


def available():
    """The language codes that have a file, for example ["ar", "en"]."""
    return sorted(name[:-5] for name in os.listdir(FOLDER) if name.endswith(".json"))


def load(code):
    """One language file: {"name", "direction", "months", "words"}."""
    if code not in _loaded:
        with open(os.path.join(FOLDER, code + ".json"), encoding="utf-8") as handle:
            _loaded[code] = json.load(handle)
    return _loaded[code]


def use(code):
    """Sets the language every page is drawn in from now on."""
    global _current
    load(code)
    _current = code


def current():
    return _current


def rtl():
    """True when the current language reads right to left, so the whole page is mirrored."""
    return load(_current)["direction"] == "rtl"


def t(key, **values):
    """One of the PDF's fixed sentences in the current language, with its blanks filled in."""
    text = load(_current)["words"][key]
    return text.format(**values) if values else text


def month(number):
    return load(_current)["months"][number - 1]
