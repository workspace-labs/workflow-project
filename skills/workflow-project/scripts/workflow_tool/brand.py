"""Whose name, logo and website the PDF carries.

They live in one small file, `assets/brand.json` (WorkSpace Labs by default). Another user replaces that
file, and their logo beside it, to put their own brand on every workflow. The rest of the look is fixed.
"""

import json
import os

from reportlab.lib.utils import ImageReader

from . import theme
from .model import WorkflowError, describe_value

BRAND_FILE = os.path.join(theme.ASSETS, "brand.json")
_KEYS = {"name", "accent", "website", "logo"}


class Brand(object):
    def __init__(self, name, accent, website, logo):
        self.name = name          # shown beside the logo on every page, and as "Prepared by" by default
        self.accent = accent      # one word of the name drawn in blue, or "" for none
        self.website = website    # the last line of the end card, or "" for none
        self.logo = logo          # full path to the logo picture, or "" for none


def load(path=BRAND_FILE):
    """Reads and checks the brand file. Raises WorkflowError with plain sentences when it is wrong."""
    where = "The brand file (%s)" % path
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError) as err:
        raise WorkflowError(["%s could not be read: %s." % (where, err)])
    if not isinstance(data, dict):
        raise WorkflowError(['%s must be one JSON object with "name", "accent", "website" and "logo".' % where])

    problems = []
    for key in data:
        if key not in _KEYS:
            problems.append('%s has an unknown field "%s" (allowed: accent, logo, name, website).' % (where, key))

    name = _field(data, "name", 40, where, problems, required=True)
    words = name.split()
    if "accent" in data:
        accent = _field(data, "accent", 20, where, problems)
        if accent and accent not in words:
            problems.append('%s: "accent" must be one word of the name ("%s"), or "" for none.' % (where, name))
    else:
        accent = words[-1] if len(words) > 1 else ""
    website = _field(data, "website", 60, where, problems)
    logo_name = _field(data, "logo", 200, where, problems)
    logo = ""
    if logo_name:
        logo = os.path.join(os.path.dirname(os.path.abspath(path)), logo_name)
        try:
            ImageReader(logo).getSize()
        except Exception:
            problems.append('%s: the logo "%s" is not a picture beside the brand file. Put a PNG or JPEG '
                            'there, or set "logo" to "" for none.' % (where, logo_name))
    missing = sorted(set(ch for text in (name, website) for ch in theme.missing_characters(text)))
    if missing:
        problems.append("%s uses characters the house font cannot draw: %s." % (where, ", ".join(missing)))
    if problems:
        raise WorkflowError(problems)
    return Brand(name, accent, website, logo)


def _field(data, key, limit, where, problems, required=False):
    """One text field of the brand file. A wrong type or a too-long value is refused, never silently
    dropped (review finding F06); a missing optional field, or "", means none."""
    if key not in data:
        if required:
            problems.append('%s needs a "%s": your organisation\'s name, up to %d characters.' % (where, key, limit))
        return ""
    value = data[key]
    if not isinstance(value, str):
        problems.append('%s: "%s" must be text in quotes%s; it is %s.' % (
            where, key, "" if required else ', or "" for none', describe_value(value)))
        return ""
    value = " ".join(value.split())
    if required and not value:
        problems.append('%s needs a "%s": your organisation\'s name, up to %d characters.' % (where, key, limit))
    if len(value) > limit:
        problems.append('%s: "%s" is too long (%d characters; keep it to %d).' % (where, key, len(value), limit))
        return ""
    return value
