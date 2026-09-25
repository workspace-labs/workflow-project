"""Draws a laid-out part (lanes, nodes, arrows) and the small key under it."""

from reportlab.platypus import Flowable

from . import paint, theme
from .layout import BOX_PAD_TOP, HEADER_H

MAIN_WIDTH, OTHER_WIDTH = 1.5, 1.1
DASH = (3.2, 2.6)
DECISION_STROKE = theme.mix(theme.WHITE, theme.GOLD, 0.85)


class DiagramFlowable(Flowable):
    def __init__(self, diagram):
        Flowable.__init__(self)
        self.diagram = diagram
        self.width, self.height = diagram.width, diagram.height

    def wrap(self, available_width, available_height):
        return self.width, self.height

    def draw(self):
        draw_diagram(self.canv, self.diagram)


class Legend(Flowable):
    """The key: what each shape and line means."""
    ITEMS = ("step", "decision", "start", "end", "stop", "main", "other")
    WORDS = {"step": "Step", "decision": "Decision", "start": "Start", "end": "End", "stop": "Stops early",
             "main": "Normal path", "other": "Other path"}

    def __init__(self, width):
        Flowable.__init__(self)
        self.width, self.height = width, 12.0

    def wrap(self, available_width, available_height):
        return self.width, self.height

    def draw(self):
        c, x, y = self.canv, 0.0, 6.0
        font, size = theme.REGULAR, 7.2
        for item in self.ITEMS:
            x += _legend_icon(c, item, x, y) + 4.0
            c.setFillColor(theme.INK_SOFT)
            c.setFont(font, size)
            c.drawString(x, y - 2.5, self.WORDS[item])
            x += theme.width(self.WORDS[item], font, size) + 13.0


def draw_diagram(c, d):
    height = d.height

    def at(point):
        return point[0], height - point[1]

    # ground, lane tints and the lane-name band, clipped to the rounded frame
    c.saveState()
    frame = c.beginPath()
    frame.roundRect(0, 0, d.width, height, 9)
    c.clipPath(frame, stroke=0, fill=0)
    c.setFillColor(theme.WHITE)
    c.rect(0, 0, d.width, height, stroke=0, fill=1)
    for i, (_, x0, x1) in enumerate(d.lanes):
        if i % 2 == 1:
            c.setFillColor(theme.LANE_TINT)
            c.rect(x0, 0, x1 - x0, height - HEADER_H, stroke=0, fill=1)
    c.setFillColor(theme.SPACE)
    c.rect(0, height - HEADER_H, d.width, HEADER_H, stroke=0, fill=1)
    c.restoreState()

    c.setLineWidth(0.7)
    c.setStrokeColor(theme.LINE_SOFT)
    for _, x0, _ in d.lanes[1:]:
        c.line(x0, 0, x0, height)
    c.setStrokeColor(theme.LINE)
    c.line(0, height - HEADER_H, d.width, height - HEADER_H)
    font, size = theme.LANE_LABEL
    for name, x0, x1 in d.lanes:
        lines = theme.chip_lines(name, (x1 - x0) - 10.0, font, size, 1.0)
        base = height - HEADER_H / 2.0 - size * 0.35 + (len(lines) - 1) * (size + 1.6) / 2.0
        for i, text in enumerate(lines):
            paint.draw_tracked(c, text, (x0 + x1) / 2.0, base - i * (size + 1.6), font, size, theme.INK, 1.0, "centre")

    for route in sorted(d.routes, key=lambda r: r.main):
        _draw_arrow(c, route, at)
    for placed in d.placed.values():
        _draw_node(c, placed, at)
    for route in d.routes:
        if route.label_at:
            x, y, anchor = route.label_at
            font, size = theme.BRANCH_LABEL
            c.setFont(font, size)
            c.setFillColor(theme.ACCENT if route.main else theme.INK_SOFT)
            x, y = at((x, y))
            if anchor == "end":
                c.drawRightString(x, y, route.edge.label)
            else:
                c.drawString(x, y, route.edge.label)

    c.setStrokeColor(theme.LINE)
    c.setLineWidth(0.8)
    c.roundRect(0.4, 0.4, d.width - 0.8, height - 0.8, 9, stroke=1, fill=0)


def _draw_arrow(c, route, at):
    points = [at(p) for p in route.points]
    color = theme.ACCENT if route.main else theme.OTHER_PATH
    c.saveState()
    c.setStrokeColor(color)
    c.setLineWidth(MAIN_WIDTH if route.main else OTHER_WIDTH)
    c.setLineJoin(1)
    if not route.main:
        c.setDash(*DASH)
    c.drawPath(paint.rounded_path(c, points, 5.0, trim_end=4.5), stroke=1, fill=0)
    c.restoreState()
    paint.arrowhead(c, points[-1], points[-2], color)


def _draw_node(c, placed, at):
    node = placed.node
    cx, cy = at((placed.cx, placed.cy))
    if placed.shape == "box":
        x0, top = cx - placed.w / 2.0, cy + placed.h / 2.0
        c.setFillColor(theme.WHITE)
        c.setStrokeColor(theme.BOX_STROKE)
        c.setLineWidth(0.8)
        c.roundRect(x0, top - placed.h, placed.w, placed.h, 7, stroke=1, fill=1)
        c.setFillColor(theme.ACCENT)
        c.setStrokeColor(theme.WHITE)
        c.setLineWidth(1.4)
        c.circle(x0 + 13.0, top, 6.2, stroke=1, fill=1)
        font, size = theme.BADGE
        c.setFillColor(theme.WHITE)
        c.setFont(font, size)
        c.drawCentredString(x0 + 13.0, top - size * 0.36, str(node.number))
        font, size, lead = theme.STEP_TITLE
        y = top - BOX_PAD_TOP - size * 0.78
        c.setFillColor(theme.INK)
        c.setFont(font, size)
        for text in placed.title_lines:
            c.drawCentredString(cx, y, text)
            y -= lead
        if placed.detail_lines:
            font, size, lead = theme.STEP_DETAIL
            y -= 1.4
            c.setFillColor(theme.INK_SOFT)
            c.setFont(font, size)
            for text in placed.detail_lines:
                c.drawCentredString(cx, y, text)
                y -= lead
    elif placed.shape == "diamond":
        hw, hh = placed.w / 2.0, placed.h / 2.0
        path = c.beginPath()
        path.moveTo(cx, cy + hh)
        path.lineTo(cx + hw, cy)
        path.lineTo(cx, cy - hh)
        path.lineTo(cx - hw, cy)
        path.close()
        c.setFillColor(theme.DECISION_FILL)
        c.setStrokeColor(DECISION_STROKE)
        c.setLineWidth(1.0)
        c.setLineJoin(1)
        c.drawPath(path, stroke=1, fill=1)
        font, size, lead = theme.DECISION_TEXT
        c.setFillColor(theme.INK)
        c.setFont(font, size)
        first = cy - size * 0.34 + (len(placed.title_lines) - 1) * lead / 2.0
        for i, text in enumerate(placed.title_lines):
            c.drawCentredString(cx, first - i * lead, text)
    else:
        stroke = {"start": (theme.ACCENT, 1.4), "end": (theme.INK, 2.4), "stop": (theme.RED, 2.0)}[node.type]
        c.setFillColor(theme.WHITE)
        c.setStrokeColor(stroke[0])
        c.setLineWidth(stroke[1])
        c.circle(cx, cy, placed.r, stroke=1, fill=1)
        _draw_terminal_label(c, placed, cx, cy)


def _draw_terminal_label(c, placed, cx, cy):
    node = placed.node
    tfont, tsize, tlead = theme.TERMINAL_TITLE
    dfont, dsize, dlead = theme.TERMINAL_DETAIL
    title_color = {"start": theme.INK_SOFT, "end": theme.INK, "stop": theme.RED}[node.type]
    lines = [(t, tfont, tsize, tlead, title_color) for t in placed.title_lines]
    lines += [(t, dfont, dsize, dlead, theme.INK_SOFT) for t in placed.detail_lines]
    if placed.label_above:
        top = cy + placed.r + 3.0 + placed.label_h
    else:
        top = cy - placed.r - 3.0
    y = top
    for text, font, size, lead, color in lines:
        y -= lead
        c.setFillColor(color)
        c.setFont(font, size)
        c.drawCentredString(cx, y + (lead - size) * 0.5 + 1.0, text)


def _legend_icon(c, item, x, y):
    c.saveState()
    if item == "step":
        c.setFillColor(theme.WHITE)
        c.setStrokeColor(theme.BOX_STROKE)
        c.setLineWidth(0.8)
        c.roundRect(x, y - 4.5, 14, 9, 2.5, stroke=1, fill=1)
        width = 14.0
    elif item == "decision":
        path = c.beginPath()
        path.moveTo(x + 6, y + 5.5)
        path.lineTo(x + 12, y)
        path.lineTo(x + 6, y - 5.5)
        path.lineTo(x, y)
        path.close()
        c.setFillColor(theme.DECISION_FILL)
        c.setStrokeColor(DECISION_STROKE)
        c.setLineWidth(0.9)
        c.drawPath(path, stroke=1, fill=1)
        width = 12.0
    elif item in ("start", "end", "stop"):
        color, line = {"start": (theme.ACCENT, 1.2), "end": (theme.INK, 2.0), "stop": (theme.RED, 1.8)}[item]
        c.setFillColor(theme.WHITE)
        c.setStrokeColor(color)
        c.setLineWidth(line)
        c.circle(x + 4.5, y, 4.0, stroke=1, fill=1)
        width = 9.0
    else:
        c.setStrokeColor(theme.ACCENT if item == "main" else theme.OTHER_PATH)
        c.setLineWidth(MAIN_WIDTH if item == "main" else OTHER_WIDTH)
        if item == "other":
            c.setDash(*DASH)
        c.line(x, y, x + 16, y)
        width = 16.0
    c.restoreState()
    return width
