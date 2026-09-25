"""Small drawing helpers shared by the diagram and the pages: tracked capitals, accent words,
chips, rounded arrows and the logo tile. They draw on a reportlab canvas (y grows upward)."""

from reportlab.lib.utils import ImageReader

from . import theme

_logos = {}


def draw_tracked(c, text, x, y, font, size, color, tracking, align="left"):
    """Letter-spaced text, used for small capital labels."""
    w = theme.tracked_width(text, font, size, tracking)
    if align == "centre":
        x -= w / 2.0
    elif align == "right":
        x -= w
    c.setFillColor(color)
    c.setFont(font, size)
    c.drawString(x, y, text, charSpace=tracking)
    return w


def accent_runs(text, accent):
    """Splits text into (words, is_accent) runs; only the first whole-word match is accented."""
    if not accent:
        return [(text, False)]
    words = text.split(" ")
    for i, word in enumerate(words):
        if word.strip(".,:;!?") == accent:
            before = " ".join(words[:i])
            after = " ".join(words[i + 1:])
            core = word.strip(".,:;!?")
            tail = word[len(core):] if word.startswith(core) else ""
            runs = []
            if before:
                runs.append((before + " ", False))
            runs.append((core, True))
            if tail or after:
                runs.append((tail + (" " + after if after else ""), False))
            return runs
    return [(text, False)]


def draw_accent_line(c, text, accent, x, y, font, size, color=None, align="left"):
    """One line of text with one word in the accent colour."""
    color = color or theme.INK
    runs = accent_runs(text, accent)
    total = sum(theme.width(t, font, size) for t, _ in runs)
    if align == "centre":
        x -= total / 2.0
    elif align == "right":
        x -= total
    c.setFont(font, size)
    for t, is_accent in runs:
        c.setFillColor(theme.ACCENT if is_accent else color)
        c.drawString(x, y, t)
        x += theme.width(t, font, size)
    return total


def rounded_path(c, points, radius=5.0, trim_end=0.0):
    """A right-angled line through points with softly rounded corners, trimmed at the end for an arrowhead."""
    pts = list(points)
    if trim_end and len(pts) >= 2:
        (x0, y0), (x1, y1) = pts[-2], pts[-1]
        length = abs(x1 - x0) + abs(y1 - y0)
        if length > trim_end:
            t = (length - trim_end) / length
            pts[-1] = (x0 + (x1 - x0) * t, y0 + (y1 - y0) * t)
    path = c.beginPath()
    path.moveTo(*pts[0])
    for i in range(1, len(pts) - 1):
        a, b, n = pts[i - 1], pts[i], pts[i + 1]
        r = min(radius, _dist(a, b) / 2.0, _dist(b, n) / 2.0)
        p1 = (b[0] - _sign(b[0] - a[0]) * r, b[1] - _sign(b[1] - a[1]) * r)
        p2 = (b[0] + _sign(n[0] - b[0]) * r, b[1] + _sign(n[1] - b[1]) * r)
        path.lineTo(*p1)
        path.curveTo(b[0], b[1], b[0], b[1], p2[0], p2[1])
    path.lineTo(*pts[-1])
    return path


def arrowhead(c, tip, before, color, length=5.6, half=2.7):
    """A filled triangle at `tip`, pointing away from `before`."""
    dx, dy = _sign(tip[0] - before[0]), _sign(tip[1] - before[1])
    bx, by = tip[0] - dx * length, tip[1] - dy * length
    path = c.beginPath()
    path.moveTo(*tip)
    path.lineTo(bx - dy * half, by + dx * half)
    path.lineTo(bx + dy * half, by - dx * half)
    path.close()
    c.setFillColor(color)
    c.drawPath(path, stroke=0, fill=1)


def draw_chip(c, lines, x, y_top, font=theme.BOLD, size=6.2, tracking=0.7):
    """A pale rounded label (who does a step). Returns its (width, height)."""
    pad_x, pad_y, lead = 5.0, 3.2, size + 2.2
    w = max(theme.tracked_width(t, font, size, tracking) for t in lines) + 2 * pad_x
    h = lead * len(lines) + 2 * pad_y - 2.2
    c.setFillColor(theme.CHIP_BG)
    c.setStrokeColor(theme.CHIP_LINE)
    c.setLineWidth(0.6)
    c.roundRect(x, y_top - h, w, h, 3, stroke=1, fill=1)
    for i, t in enumerate(lines):
        draw_tracked(c, t, x + pad_x, y_top - pad_y - size * 0.8 - i * lead, font, size, theme.INK, tracking)
    return w, h


def draw_logo_tile(c, logo, x, y, size, radius):
    """The logo on a white rounded tile with a hairline edge. (x, y) is the bottom-left corner."""
    if logo not in _logos:
        _logos[logo] = ImageReader(logo)
    c.setFillColor(theme.WHITE)
    c.setStrokeColor(theme.LINE)
    c.setLineWidth(0.6)
    c.roundRect(x, y, size, size, radius, stroke=1, fill=1)
    inset = size * 0.08
    c.drawImage(_logos[logo], x + inset, y + inset, size - 2 * inset, size - 2 * inset, mask="auto",
                preserveAspectRatio=True, anchor="c")


def _sign(v):
    return (v > 0) - (v < 0)


def _dist(a, b):
    return abs(b[0] - a[0]) + abs(b[1] - a[1])
