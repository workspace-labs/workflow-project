"""Draws a laid-out part: the lanes, the boxes, the arrows, the strip under them, and the small key."""

from . import language, layout, paint, theme

MAIN_WIDTH, OTHER_WIDTH = 2.2, 1.4
DASH = (4.5, 3.6)
FRAME, RADIUS = 1.1, 10.0
KEY_ITEMS = ("main", "other", "decision", "start", "end", "stop")
KEY_H = 12.0


def draw_board(c, d, left, top):
    """Draws the board with its top-left corner at (left, top) on the page."""
    height = d.height

    def at(point):
        return left + point[0], top - point[1]

    def band(x0, y0, x1, y1, colour):
        c.setFillColor(colour)
        c.rect(left + x0, top - y1, x1 - x0, y1 - y0, stroke=0, fill=1)

    # grounds, clipped to the rounded frame
    c.saveState()
    frame = c.beginPath()
    frame.roundRect(left, top - height, d.width, height, RADIUS)
    c.clipPath(frame, stroke=0, fill=0)
    for i, (_, y0, y1) in enumerate(d.lanes):
        band(0, y0, d.width, y1, theme.LANE_TINT if i % 2 == 0 else theme.WHITE)
    band(0, 0, layout.LABEL_W, d.bottom, theme.INK)
    band(0, d.bottom, d.width, height, theme.STRIP)
    c.restoreState()

    c.setStrokeColor(theme.INK)
    c.setLineWidth(FRAME)
    for _, _, y1 in d.lanes:
        c.line(left + layout.LABEL_W, top - y1, left + d.width, top - y1)
    c.line(left, top - d.bottom, left + layout.LABEL_W, top - d.bottom)
    c.setStrokeColor(theme.WHITE)
    c.setLineWidth(0.6)
    for _, _, y1 in d.lanes[:-1]:
        c.line(left, top - y1, left + layout.LABEL_W, top - y1)
    c.setStrokeColor(theme.LINE)
    c.setLineWidth(0.75)
    for column in d.columns:
        c.line(left + column.cell[0], top - d.bottom - 0.6, left + column.cell[0], top - height)

    font, size, lead = theme.LANE_LABEL
    for (_, y0, y1), lines in zip(d.lanes, d.lane_lines):
        _lines(c, lines, left + layout.LABEL_PAD, top - (y0 + y1) / 2.0, font, size, lead, theme.WHITE)
    words = layout.wrap(language.t("col_out"), font, size, layout.LABEL_W - 2 * layout.LABEL_PAD, 4) or []
    _lines(c, words, left + layout.LABEL_PAD, top - d.bottom - layout.STRIP_PAD - lead * len(words) / 2.0 - 2.0,
           font, size, lead, theme.INK)

    for route in sorted(d.routes, key=lambda r: r.main):
        _draw_arrow(c, route, at)
    for placed in d.placed.values():
        _draw_node(c, placed, at)
    for route in d.routes:
        if route.label_at is not None:
            _draw_answer(c, route, at)
    _draw_strip(c, d, left, top)

    c.setStrokeColor(theme.INK)
    c.setLineWidth(FRAME)
    c.roundRect(left, top - height, d.width, height, RADIUS, stroke=1, fill=0)


def _lines(c, lines, x, middle, font, size, lead, colour):
    """Lines of text starting at x, centred as a block on the height `middle`."""
    c.setFillColor(colour)
    c.setFont(font, size)
    y = middle + lead * len(lines) / 2.0 - lead + (lead - size) / 2.0 + size * 0.22
    for text in lines:
        c.drawString(x, y, text)
        y -= lead


def _draw_arrow(c, route, at):
    points = [at(p) for p in route.points]
    colour = theme.ACCENT if route.main else theme.INK_SOFT
    c.saveState()
    c.setStrokeColor(colour)
    c.setLineWidth(MAIN_WIDTH if route.main else OTHER_WIDTH)
    c.setLineJoin(1)
    if not route.main:
        c.setDash(*DASH)
    c.drawPath(paint.rounded_path(c, points, 7.0, trim_end=5.5), stroke=1, fill=0)
    c.restoreState()
    paint.arrowhead(c, points[-1], points[-2], colour)


def _draw_answer(c, route, at):
    rect = route.label_at
    colour = theme.ACCENT if route.main else theme.INK_SOFT
    x0, y1 = at((rect.x0, rect.y1))
    w, h = rect.x1 - rect.x0, rect.y1 - rect.y0
    c.setFillColor(theme.WHITE)
    c.setStrokeColor(colour)
    c.setLineWidth(0.9)
    c.roundRect(x0, y1, w, h, h / 2.0, stroke=1, fill=1)
    font, size = theme.ANSWER
    c.setFillColor(colour)
    c.setFont(font, size)
    c.drawCentredString(x0 + w / 2.0, y1 + h / 2.0 - size * 0.34, route.edge.label)


def _draw_node(c, placed, at):
    node = placed.node
    cx, cy = at((placed.cx, placed.cy))
    x0, top = cx - placed.w / 2.0, cy + placed.h / 2.0
    if placed.flag_above:
        _draw_mark(c, placed.flag_above, x0, cy + placed.above)
    if placed.flag_below:
        _draw_mark(c, placed.flag_below, x0, top - placed.h - layout.FLAG_GAP)
    if placed.shape == "pill":
        c.setFillColor(theme.WHITE)
        c.setStrokeColor(theme.RED if node.type == "stop" else theme.INK_SOFT)
        c.setLineWidth(1.0)
        c.roundRect(x0, top - placed.h, placed.w, placed.h, min(placed.h / 2.0, 9.0), stroke=1, fill=1)
        _draw_mark(c, placed.mark, x0 + layout.BOX_PAD_X, top - layout.PILL_PAD_Y)
        return
    question = node.type == "decision"
    c.saveState()
    c.setFillColor(theme.AMBER_FILL if question else theme.WHITE)
    c.setStrokeColor(theme.AMBER if question else theme.INK if placed.on_main else theme.INK_SOFT)
    c.setLineWidth(FRAME)
    if not placed.on_main:
        c.setDash(3.2, 2.6)
    c.roundRect(x0, top - placed.h, placed.w, placed.h, 8, stroke=1, fill=1)
    c.restoreState()
    c.setFillColor(theme.AMBER if question else theme.ACCENT)
    c.setStrokeColor(theme.WHITE)
    c.setLineWidth(1.2)
    c.circle(x0 + 3.0, top - 3.0, 7.6, stroke=1, fill=1)
    font, size = theme.BADGE
    c.setFillColor(theme.WHITE)
    c.setFont(font, size)
    c.drawCentredString(x0 + 3.0, top - 3.0 - size * 0.35, "?" if question else str(node.number))
    font, size, lead = theme.STEP_TITLE
    y = top - layout.BOX_PAD_TOP - size * 0.80
    c.setFillColor(theme.INK)
    c.setFont(font, size)
    for text in placed.title_lines:
        c.drawString(x0 + layout.BOX_PAD_X, y, text)
        y -= lead
    if placed.detail_lines:
        font, size, lead = theme.STEP_DETAIL
        y -= 1.2
        c.setFillColor(theme.INK_SOFT)
        c.setFont(font, size)
        for text in placed.detail_lines:
            c.drawString(x0 + layout.BOX_PAD_X, y, text)
            y -= lead


def _draw_mark(c, mark, x, top):
    """A start, stop or end: its round mark, then its words. Returns the height where it ends."""
    kind = mark.node.type
    font, size, lead = theme.FLAG
    draw_dot(c, kind, x + 3.8, top - lead / 2.0)
    y = top
    c.setFillColor(theme.RED if kind == "stop" else theme.INK_SOFT)
    c.setFont(font, size)
    for text in mark.title_lines:
        c.drawString(x + layout.DOT_ROOM, y - lead + (lead - size) / 2.0 + size * 0.22, text)
        y -= lead
    font, size, lead = theme.STEP_DETAIL
    c.setFillColor(theme.INK_SOFT)
    c.setFont(font, size)
    for text in mark.detail_lines:
        c.drawString(x + layout.DOT_ROOM, y - lead + (lead - size) / 2.0 + size * 0.22, text)
        y -= lead
    return y


def draw_dot(c, kind, x, y):
    """The round mark: a ring for a start, a full dot for an end, a red ring for a stop."""
    c.saveState()
    c.setLineWidth(1.7)
    if kind == "end":
        c.setFillColor(theme.INK)
        c.circle(x, y, 3.8, stroke=0, fill=1)
    else:
        c.setFillColor(theme.WHITE)
        c.setStrokeColor(theme.RED if kind == "stop" else theme.INK)
        c.circle(x, y, 3.0, stroke=1, fill=1)
    c.restoreState()


def _draw_strip(c, d, left, top):
    nfont, nsize = theme.STRIP_NUMBER
    font, size, lead = theme.STRIP_TEXT
    for column in d.columns:
        x = left + column.cell[0] + layout.STRIP_PAD
        y = top - d.bottom - layout.STRIP_PAD
        for number, lines in column.entries:
            c.setFillColor(theme.AMBER if number == "?" else theme.ACCENT)
            c.setFont(nfont, nsize)
            c.drawString(x, y - lead + (lead - nsize) / 2.0 + nsize * 0.22, number)
            c.setFillColor(theme.INK)
            c.setFont(font, size)
            line_y = y
            for text in lines:
                c.drawString(x + layout.STRIP_NUMBER_W, line_y - lead + (lead - size) / 2.0 + size * 0.22, text)
                line_y -= lead
            y -= max(layout.STRIP_ROW, lead * len(lines)) + layout.STRIP_ENTRY_GAP


def draw_key(c, x, y):
    """The key: what each line and mark means. (x, y) is where its first mark sits, on its middle line."""
    font, size = theme.REGULAR, 8.2
    for item in KEY_ITEMS:
        c.saveState()
        if item in ("main", "other"):
            c.setStrokeColor(theme.ACCENT if item == "main" else theme.INK_SOFT)
            c.setLineWidth(MAIN_WIDTH if item == "main" else OTHER_WIDTH)
            if item == "other":
                c.setDash(*DASH)
            c.line(x, y, x + 22.0, y)
            x += 22.0
        elif item == "decision":
            c.setFillColor(theme.AMBER_FILL)
            c.setStrokeColor(theme.AMBER)
            c.setLineWidth(1.0)
            c.roundRect(x, y - 4.5, 9.0, 9.0, 2.2, stroke=1, fill=1)
            x += 9.0
        else:
            draw_dot(c, item, x + 3.8, y)
            x += 7.6
        c.restoreState()
        word = language.t("key_" + item)
        c.setFillColor(theme.INK_SOFT)
        c.setFont(font, size)
        c.drawString(x + 5.0, y - size * 0.34, word)
        x += 5.0 + theme.width(word, font, size) + 16.0
