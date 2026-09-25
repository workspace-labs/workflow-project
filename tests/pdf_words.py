"""Where every word really landed in a finished PDF, read back with poppler's `pdftotext -bbox`.

An independent check for review findings F02 and F03: it measures the drawn page, not the tool's own
text measurements. Tests that need it are skipped where pdftotext is not installed.
"""

import re
import shutil
import subprocess

AVAILABLE = shutil.which("pdftotext") is not None
_PAGE = re.compile(r'<page width="([\d.]+)" height="([\d.]+)">(.*?)</page>', re.S)
# signed: a word that starts left of or above the page has a negative position, and must not be skipped
_WORD = re.compile(r'<word xMin="(-?[\d.]+)" yMin="(-?[\d.]+)" xMax="(-?[\d.]+)" yMax="(-?[\d.]+)">(.*?)</word>')


def pages(pdf):
    """[(width, height, [(x0, y0, x1, y1, text), ...]), ...] for every page."""
    html = subprocess.run(["pdftotext", "-bbox", pdf, "-"], capture_output=True, text=True, check=True).stdout
    found = []
    for width, height, body in _PAGE.findall(html):
        words = [(float(a), float(b), float(c), float(d), t) for a, b, c, d, t in _WORD.findall(body)]
        found.append((float(width), float(height), words))
    return found


def problems(pdf, edge=10.0, share=0.25):
    """Words outside the page (closer than `edge` to it) and pairs of words that overlap by more than
    `share` of the smaller word. Returns plain lines; empty means every word sits clear."""
    lines = []
    for number, (width, height, words) in enumerate(pages(pdf), 1):
        for x0, y0, x1, y1, text in words:
            if x0 < edge or y0 < edge or x1 > width - edge or y1 > height - edge:
                lines.append("page %d: %r runs off the page (%.0f..%.0f)" % (number, text, x0, x1))
        for i, a in enumerate(words):
            for b in words[i + 1:]:
                w = min(a[2], b[2]) - max(a[0], b[0])
                h = min(a[3], b[3]) - max(a[1], b[1])
                if w <= 0 or h <= 0:
                    continue
                smaller = min((a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1]))
                if smaller > 0 and w * h / smaller > share:
                    lines.append("page %d: %r overlaps %r" % (number, a[4], b[4]))
    return lines
