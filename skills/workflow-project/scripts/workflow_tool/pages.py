"""Puts the whole workflow PDF together.

Order: cover · the project on one page · the map (when there is more than one part) · for each
part, its swimlane and its table of steps · the end card. The page count grows with the project.
"""

import datetime
import io
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (BaseDocTemplate, Flowable, Frame, KeepTogether, NextPageTemplate, PageBreak,
                                PageTemplate, Paragraph, Spacer, Table, TableStyle)

from . import paint, theme
from .render_diagram import DiagramFlowable, Legend

PAGE_W, PAGE_H = A4
MARGIN_X = 42.0
FRAME_TOP = 66.0          # below the logo rail
FRAME_BOTTOM = 50.0       # above the footer
FRAME_W = PAGE_W - 2 * MARGIN_X
FRAME_H = PAGE_H - FRAME_TOP - FRAME_BOTTOM
LEGEND_ROOM = 9.0 + 12.0 + 4.0      # the space above the key, the key, a little air
WHO_WIDTH = 92.0                    # the step table's "Who" column
CHIP_ROOM = WHO_WIDTH - 2 * 6.0 - 2 * 5.0   # less the cell's padding and the chip's own padding
FACT_ROOM = PAGE_W - MARGIN_X - (MARGIN_X + 92.0)   # a cover fact's value column
FOOTER_ROOM = FRAME_W - 90.0        # the footer's left text, clear of "Page n of N"
MAP_TEXT_X, MAP_RIGHT = 56.0, 86.0  # a map card's text starts after the number, stops before the page


# ---------------------------------------------------------------- text styles

def _styles():
    return {
        "h1": ParagraphStyle("h1", fontName=theme.EXTRABOLD, fontSize=21, leading=25, textColor=theme.INK,
                             spaceBefore=4, spaceAfter=6),
        "h1part": ParagraphStyle("h1part", fontName=theme.EXTRABOLD, fontSize=17, leading=21, textColor=theme.INK,
                                 spaceBefore=3, spaceAfter=4),
        "lede": ParagraphStyle("lede", fontName=theme.REGULAR, fontSize=9.4, leading=13.6, textColor=theme.INK_SOFT,
                               spaceAfter=10),
        "h2": ParagraphStyle("h2", fontName=theme.BOLD, fontSize=11.2, leading=15, textColor=theme.INK,
                             spaceBefore=14, spaceAfter=5),
        "body": ParagraphStyle("body", fontName=theme.REGULAR, fontSize=9.6, leading=14.4, textColor=theme.INK_SOFT),
        "item": ParagraphStyle("item", fontName=theme.REGULAR, fontSize=9.4, leading=13.8, textColor=theme.INK_SOFT,
                               leftIndent=12, bulletIndent=0, spaceAfter=4, bulletFontName=theme.BOLD,
                               bulletColor=theme.ACCENT),
        "cell": ParagraphStyle("cell", fontName=theme.REGULAR, fontSize=8.3, leading=11.2, textColor=theme.INK_SOFT),
        "cellnum": ParagraphStyle("cellnum", fontName=theme.BOLD, fontSize=8.6, leading=11.2, textColor=theme.INK,
                                  alignment=2),
    }


def _accent(text, word):
    """Escapes text for a Paragraph and colours one word with the accent."""
    runs = paint.accent_runs(text, word)
    return "".join('<font color="#3E5BFF">%s</font>' % escape(t) if hot else escape(t) for t, hot in runs)


def _bold(text):
    return '<font name="%s" color="#10182E">%s</font>' % (theme.BOLD, escape(text))


def nice_date(value):
    try:
        day = datetime.datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return value
    return "%d %s %d" % (day.day, day.strftime("%B"), day.year)


# ---------------------------------------------------------------- small flowables

class Overline(Flowable):
    """Small letter-spaced capitals above a heading."""

    def __init__(self, text, color=None):
        Flowable.__init__(self)
        self.text, self.color = text.upper(), color or theme.INK_SOFT
        self.height = 12.0

    def wrap(self, available_width, available_height):
        return available_width, self.height

    def draw(self):
        paint.draw_tracked(self.canv, self.text, 0, 3.0, theme.BOLD, 7.0, self.color, 1.3)


class Chip(Flowable):
    """Who does a step, as a pale capital label."""

    def __init__(self, text):
        Flowable.__init__(self)
        self.text = text
        self.lines = [text.upper()]

    def wrap(self, available_width, available_height):
        self.lines = theme.chip_lines(self.text, available_width - 10.0)
        self.height = (6.2 + 2.2) * len(self.lines) + 4.2
        return available_width, self.height

    def draw(self):
        paint.draw_chip(self.canv, self.lines, 0, self.height)


class Marker(Flowable):
    """Invisible: remembers which page a part starts on, for the map and the page references."""

    def __init__(self, record, key):
        Flowable.__init__(self)
        self.record, self.key = record, key

    def wrap(self, available_width, available_height):
        return 0, 0

    def draw(self):
        self.record[self.key] = self.canv.getPageNumber()


class MapCards(Flowable):
    """The map: every part as one box, joined by arrows, with the page it is explained on."""
    GAP = 24.0

    def __init__(self, project, parts, cards, pages, first):
        Flowable.__init__(self)
        self.project, self.parts, self.cards, self.pages, self.first = project, parts, cards, pages, first

    def wrap(self, available_width, available_height):
        self.width = available_width
        return available_width, _map_height(self.cards, self.first)

    def draw(self):
        c = self.canv
        y = self.wrap(self.width, 0)[1]
        if not self.first:
            _map_arrow(c, 30.0, y, y - self.GAP + 2)
            y -= self.GAP
        for i, (part, card) in enumerate(zip(self.parts, self.cards)):
            top, height = y, card["height"]
            c.setFillColor(theme.WHITE)
            c.setStrokeColor(theme.BOX_STROKE)
            c.setLineWidth(0.8)
            c.roundRect(0, top - height, self.width, height, 9, stroke=1, fill=1)
            c.setFillColor(theme.ACCENT)
            c.circle(30.0, top - height / 2.0, 12.0, stroke=0, fill=1)
            c.setFillColor(theme.WHITE)
            c.setFont(theme.BOLD, 11)
            c.drawCentredString(30.0, top - height / 2.0 - 3.9, str(part.number))
            c.setFillColor(theme.INK)
            c.setFont(theme.BOLD, 12)
            for n, line in enumerate(card["title"]):
                c.drawString(MAP_TEXT_X, top - 21.0 - 14.0 * n, line)
            below_title = 14.0 * (len(card["title"]) - 1)
            c.setFillColor(theme.INK_SOFT)
            c.setFont(theme.REGULAR, 8.6)
            for n, line in enumerate(card["summary"]):
                c.drawString(MAP_TEXT_X, top - 34.5 - below_title - 11.0 * n, line)
            chips_top = top - 41.0 - below_title - 11.0 * max(len(card["summary"]) - 1, 0)
            for row, chips in enumerate(card["chips"]):
                for x, text in chips:
                    paint.draw_chip(c, [text], x, chips_top - 13.0 * row, size=5.6, tracking=0.6)
            page = self.pages.get(part.number)
            paint.draw_tracked(c, "PAGE", self.width - 20.0, top - 25.0, theme.BOLD, 6.2, theme.INK_FAINT, 1.0, "right")
            c.setFillColor(theme.ACCENT)
            c.setFont(theme.BOLD, 16)
            c.drawRightString(self.width - 20.0, top - 43.0, str(page) if page else "00")
            y = top - height
            if i < len(self.parts) - 1:
                _map_arrow(c, 30.0, y, y - self.GAP + 2)
            y -= self.GAP


def _map_card(part, width):
    """A map card's lines and height, or None when a word cannot fit (review finding F03)."""
    room = width - MAP_TEXT_X - MAP_RIGHT
    title = _wrap_strict(part.title, theme.BOLD, 12, room)
    summary = _wrap_strict(part.summary, theme.REGULAR, 8.6, room) if part.summary else []
    if title is None or summary is None or len(title) > 2 or len(summary) > 3:
        return None
    rows, x = [[]], MAP_TEXT_X
    for lane in part.lanes:
        text = lane.upper()
        chip = theme.tracked_width(text, theme.BOLD, 5.6, 0.6) + 10.0
        if chip > room:
            return None
        if rows[-1] and x + chip > MAP_TEXT_X + room:
            rows.append([])
            x = MAP_TEXT_X
        rows[-1].append((x, text))
        x += chip + 4.0
    height = 62.0 + 14.0 * (len(title) - 1) + 11.0 * max(len(summary) - 1, 0) + 13.0 * (len(rows) - 1)
    return {"title": title, "summary": summary, "chips": rows, "height": height}


def _map_height(cards, first):
    return sum(card["height"] for card in cards) + MapCards.GAP * (len(cards) - 1) + (0 if first else MapCards.GAP)


def _map_arrow(c, x, y_from, y_to):
    c.setStrokeColor(theme.ACCENT)
    c.setLineWidth(1.5)
    c.line(x, y_from, x, y_to + 4.5)
    paint.arrowhead(c, (x, y_to), (x, y_from), theme.ACCENT)


# ---------------------------------------------------------------- the story

def _story(project, diagrams, pages, record):
    s = _styles()
    story = [Spacer(1, 1), NextPageTemplate("inner"), PageBreak()]
    total_parts = len(project.parts)

    # The project on one page
    story += [Overline("The project on one page"),
              Paragraph(_accent(project.name, project.accent), s["h1"]),
              Paragraph(escape(project.summary), s["body"]),
              Paragraph("Who takes part", s["h2"])]
    for name, role in project.actors:
        text = _bold(name) + (" — " + escape(role) if role else "")
        story.append(Paragraph(text, s["item"], bulletText="•"))
    story.append(Paragraph("The main parts, from A to Z", s["h2"]))
    for part in project.parts:
        page = pages.get(part.number)
        text = "%s%s &nbsp;<font color=\"#3E5BFF\">page %s</font>" % (
            _bold(part.title), (" — " + escape(part.summary)) if part.summary else "", page or "00")
        story.append(Paragraph(text, s["item"], bulletText="%d" % part.number))
    if project.assumptions:
        story.append(Paragraph("What we assumed", s["h2"]))
        story += [Paragraph(escape(t), s["item"], bulletText="•") for t in project.assumptions]
    if project.open_questions:
        story.append(Paragraph("Still to confirm", s["h2"]))
        story += [Paragraph(escape(t), s["item"], bulletText="•") for t in project.open_questions]

    # The map
    if total_parts > 1:
        for number, (chunk, cards) in enumerate(_map_pages(project, s)):
            story += _map_heading(s, number) + [MapCards(project, chunk, cards, pages, first=number == 0)]

    # One swimlane and one table per part
    for part, diagram in zip(project.parts, diagrams):
        story += [PageBreak(), Marker(record, part.number),
                  KeepTogether(_part_heading(part, total_parts, s) +
                               [DiagramFlowable(diagram), Spacer(1, 9), Legend(FRAME_W)]),
                  # the heading and its table stay together; a table taller than a page still splits,
                  # repeating its header row
                  KeepTogether([Paragraph("Every step in this part" if total_parts > 1 else "Every step", s["h2"]),
                                _step_table(part, s, pages, project)])]

    story += [NextPageTemplate("end"), PageBreak(), Spacer(1, 1)]
    return story


def _map_heading(s, number):
    return [PageBreak(), Overline("The map" if number == 0 else "The map, continued"),
            Paragraph(_accent("The project from A to Z", "Z"), s["h1"]),
            Paragraph("Each box is one part of the project, in the order it happens. The number on the "
                      "right is the page where that part is drawn in full.", s["lede"])]


def _map_pages(project, s):
    """The parts split into pages of map cards, each page filled no further than it can hold."""
    used = 0.0
    for flowable in _map_heading(s, 0)[1:]:
        _, height = flowable.wrap(FRAME_W, FRAME_H)
        used += height + flowable.getSpaceBefore() + flowable.getSpaceAfter()
    room = FRAME_H - used - 4.0
    pages, parts, cards = [], [], []
    for part in project.parts:
        card = _map_card(part, FRAME_W)
        if parts and _map_height(cards + [card], not pages) > room:
            pages.append((parts, cards))
            parts, cards = [], []
        parts.append(part)
        cards.append(card)
    pages.append((parts, cards))
    return pages


def _part_heading(part, total_parts, s):
    overline = "Part %d of %d" % (part.number, total_parts) if total_parts > 1 else "The workflow"
    lede = escape(part.summary) if part.summary else \
        "Each column is one person or system. Follow the blue line from start to end."
    return [Overline(overline),
            Paragraph(_accent(part.title, part.title.split()[-1]), s["h1part"]),
            Paragraph(lede, s["lede"])]


def diagram_room(part, total_parts):
    """How tall a part's swimlane may be so it shares one page with its heading and key."""
    s = _styles()
    used = 0.0
    for flowable in _part_heading(part, total_parts, s):
        _, height = flowable.wrap(FRAME_W, FRAME_H)
        used += height + flowable.getSpaceBefore() + flowable.getSpaceAfter()
    return FRAME_H - used - LEGEND_ROOM


def _step_table(part, s, pages, project):
    widths = [30.0, WHO_WIDTH, FRAME_W - 30.0 - WHO_WIDTH - 130.0, 130.0]
    header = [_HeaderCell(t) for t in ("No.", "Who", "What happens", "What comes out")]
    rows = [header]
    following = {}
    for position, node in enumerate(part.nodes):
        following[node.id] = part.nodes[position + 1].id if position + 1 < len(part.nodes) else None
    for node in part.nodes:
        number = Paragraph(str(node.number) if node.number else "", s["cellnum"])
        who = Chip(node.lane)
        detail = ("<br/>" + escape(node.detail)) if node.detail else ""
        if node.type == "start":
            what = _bold("Starts when: ") + escape(node.title)
            out = ""
        elif node.type == "step":
            what = _bold(node.title) + detail
            out = escape(node.result)
            if node.next and node.next != following[node.id]:
                out += ("<br/>" if out else "") + "Then: " + escape(_describe(part, node.next))
        elif node.type == "decision":
            what = _bold("Decision: ") + escape(node.title) + detail
            out = "<br/>".join('%s → %s' % (_bold(label), escape(_describe(part, target)))
                               for label, target in node.branches)
        elif node.type == "stop":
            what = '<font name="%s" color="#E03131">Stops: </font>%s%s' % (theme.BOLD, escape(node.title), detail)
            out = ""
        else:
            what = _bold("Ends: ") + escape(node.title) + detail
            out = ""
            if node.to_part:
                page = pages.get(node.to_part)
                out = "Continues in Part %d (page %s)" % (node.to_part, page or "00")
        rows.append([number, who, Paragraph(what, s["cell"]), Paragraph(out, s["cell"])])
    table = Table(rows, colWidths=widths, repeatRows=1)
    last = len(rows) - 1
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), theme.INK),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [theme.WHITE, theme.ZEBRA]),
        ("LINEBELOW", (0, 1), (-1, last - 1), 0.8, theme.TABLE_RULE),
        ("LINEBEFORE", (0, 1), (0, -1), 0.8, theme.TABLE_RULE),
        ("LINEAFTER", (0, 1), (-1, -1), 0.8, theme.TABLE_RULE),
        ("LINEBELOW", (0, last), (-1, last), 1.5, theme.INK),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("VALIGN", (0, 0), (-1, 0), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, 0), 6),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ("TOPPADDING", (0, 1), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
    ]))
    return table


class _HeaderCell(Flowable):
    def __init__(self, text):
        Flowable.__init__(self)
        self.text = text.upper()

    def wrap(self, available_width, available_height):
        self.width = available_width
        return available_width, 8.0

    def draw(self):
        align = "right" if self.text == "NO." else "left"
        x = self.width if align == "right" else 0
        paint.draw_tracked(self.canv, self.text, x, 1.2, theme.BOLD, 6.6, theme.WHITE, 1.0, align)


def _describe(part, node_id):
    node = part.by_id[node_id]
    if node.type == "step":
        return "step %d" % node.number
    if node.type == "decision":
        return "the question “%s”" % node.title
    if node.type == "stop":
        return "stops (%s)" % node.title
    if node.type == "end":
        return "ends (%s)" % node.title
    return "the start"


# ---------------------------------------------------------------- page furniture

def _ground(c):
    c.setFillColor(theme.SPACE)
    c.rect(0, 0, PAGE_W, PAGE_H, stroke=0, fill=1)
    for (x, y, radius, tint) in ((PAGE_W * 0.08, PAGE_H * 1.08, PAGE_W * 0.95, theme.WASH_GOLD),
                                 (PAGE_W * 1.04, PAGE_H * -0.06, PAGE_W * 1.05, theme.WASH_BLUE)):
        c.saveState()
        clip = c.beginPath()
        clip.circle(x, y, radius)
        c.clipPath(clip, stroke=0, fill=0)
        c.radialGradient(x, y, radius, (tint, theme.SPACE), extend=False)
        c.restoreState()
    c.setStrokeColor(theme.GRID_LINE)
    c.setLineWidth(0.5)
    step = PAGE_W / 18.0
    x = step
    while x < PAGE_W:
        c.line(x, 0, x, PAGE_H)
        x += step
    y = step
    while y < PAGE_H:
        c.line(0, y, PAGE_W, y)
        y += step


def _rail(c, brand, y, tile):
    x = MARGIN_X
    if brand.logo:
        paint.draw_logo_tile(c, brand.logo, x, y - tile / 2.0, tile, tile * 0.24)
        x += tile + 8.0
    paint.draw_accent_line(c, brand.name, brand.accent, x, y - 3.4, theme.BOLD, 9.6 if tile < 20 else 11.0)
    font, size, tracking = theme.BOLD, 6.2, 1.2
    w = theme.tracked_width("WORKFLOW", font, size, tracking) + 16.0
    c.setFillColor(theme.TAG_BG)
    c.setStrokeColor(theme.TAG_LINE)
    c.setLineWidth(0.6)
    c.roundRect(PAGE_W - MARGIN_X - w, y - 7.5, w, 15.0, 7.5, stroke=1, fill=1)
    paint.draw_tracked(c, "WORKFLOW", PAGE_W - MARGIN_X - 8.0, y - 2.3, font, size, theme.ACCENT, tracking, "right")


def _make_templates(project, pages, brand):
    frame = Frame(MARGIN_X, FRAME_BOTTOM, FRAME_W, FRAME_H, 0, 0, 0, 0, id="body")
    total = pages.get("total")
    footer_left = _footer_text(project)

    def cover(c, doc):
        c.saveState()
        _ground(c)
        _rail(c, brand, PAGE_H - 46.0, 22.0)
        paint.draw_tracked(c, "PROJECT WORKFLOW", MARGIN_X, PAGE_H * 0.60, theme.BOLD, 7.6, theme.INK_SOFT, 1.5)
        size, lines = _fit_lines(project.name, theme.EXTRABOLD, (34, 29, 24), FRAME_W - 40.0, 3)
        y = PAGE_H * 0.60 - 42.0
        for line in lines:
            paint.draw_accent_line(c, line, project.accent, MARGIN_X, y, theme.EXTRABOLD, size)
            y -= size * 1.15
        c.setFillColor(theme.INK_SOFT)
        c.setFont(theme.MEDIUM, 13)
        c.drawString(MARGIN_X, y - 2.0, "How it works, from A to Z.")
        facts = [(label, _wrap_strict(value, theme.MEDIUM, 10, FACT_ROOM)) for label, value in _cover_facts(project, brand)]
        y = 190.0 + 13.0 * sum(len(lines) - 1 for _, lines in facts)
        for label, lines in facts:
            paint.draw_tracked(c, label.upper(), MARGIN_X, y, theme.BOLD, 6.4, theme.INK_FAINT, 1.2)
            c.setFillColor(theme.INK)
            c.setFont(theme.MEDIUM, 10)
            for n, line in enumerate(lines):
                c.drawString(MARGIN_X + 92.0, y - 0.5 - 13.0 * n, line)
            y -= 21.0 + 13.0 * (len(lines) - 1)
        c.restoreState()

    def inner(c, doc):
        c.saveState()
        _rail(c, brand, PAGE_H - 40.0, 16.0)
        c.setStrokeColor(theme.LINE_SOFT)
        c.setLineWidth(0.6)
        c.line(MARGIN_X, PAGE_H - 54.0, PAGE_W - MARGIN_X, PAGE_H - 54.0)
        c.line(MARGIN_X, 40.0, PAGE_W - MARGIN_X, 40.0)
        c.setFillColor(theme.INK_FAINT)
        c.setFont(theme.REGULAR, 7)
        c.drawString(MARGIN_X, 28.0, footer_left)
        c.drawRightString(PAGE_W - MARGIN_X, 28.0, "Page %d of %s" % (doc.page, total or "00"))
        c.restoreState()

    def end(c, doc):
        c.saveState()
        _ground(c)
        middle = PAGE_H * 0.54
        if brand.logo:
            paint.draw_logo_tile(c, brand.logo, PAGE_W / 2.0 - 29.0, middle + 52.0, 58.0, 14.0)
        size, lines = _fit_lines(project.name, theme.EXTRABOLD, (28, 24, 20), FRAME_W - 60.0, 2)
        y = middle + 12.0
        for line in lines:
            paint.draw_accent_line(c, line, project.accent, PAGE_W / 2.0, y, theme.EXTRABOLD, size, align="centre")
            y -= size * 1.15
        c.setFillColor(theme.INK_SOFT)
        c.setFont(theme.REGULAR, 11.5)
        y -= 4.0
        for sentence in _end_sentences(project, brand):
            for line in _wrap_strict(sentence, theme.REGULAR, 11.5, FRAME_W - 40.0):
                c.drawCentredString(PAGE_W / 2.0, y, line)
                y -= 17.0
        if brand.website:
            c.setFillColor(theme.ACCENT)
            c.setFont(theme.SEMIBOLD, 12.5)
            c.drawCentredString(PAGE_W / 2.0, y - 12.0, brand.website)
        c.restoreState()

    return [PageTemplate(id="cover", frames=[frame], onPage=cover),
            PageTemplate(id="inner", frames=[frame], onPage=inner),
            PageTemplate(id="end", frames=[frame], onPage=end)]


def _fit_lines(text, font, sizes, room, most):
    """The largest of `sizes` at which text wraps into at most `most` lines, and those lines; None when no
    size fits (preflight refuses the workflow before anything is drawn)."""
    for size in sizes:
        lines = _wrap_strict(text, font, size, room)
        if lines is not None and len(lines) <= most:
            return size, lines
    return None


def _wrap_strict(text, font, size, room):
    """Lines no wider than room, split between words; None when a single word is wider than room."""
    lines, current = [], ""
    for word in text.split():
        if theme.width(word, font, size) > room:
            return None
        candidate = word if not current else current + " " + word
        if theme.width(candidate, font, size) <= room:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _cover_facts(project, brand):
    facts = [("Prepared for", project.client), ("Prepared by", project.prepared_by or brand.name),
             ("Date", nice_date(project.date)), ("Version", project.version), ("Status", project.status)]
    return [(label, value) for label, value in facts if value]


def _end_sentences(project, brand):
    who = ("Prepared for %s." % project.client) if project.client else \
        ("Prepared by %s." % (project.prepared_by or brand.name))
    return ["How %s works, from A to Z." % project.name, who]


def _footer_text(project):
    """The longest footer that fits: in full, then without version and date, then the name alone."""
    full = "%s \u2014 workflow \u00b7 Version %s \u00b7 %s" % (project.name, project.version, nice_date(project.date))
    for text in (full, "%s \u2014 workflow" % project.name, project.name):
        if theme.width(text, theme.REGULAR, 7) <= FOOTER_ROOM:
            return text
    return None


def _rail_room(brand, tile):
    tag = theme.tracked_width("WORKFLOW", theme.BOLD, 6.2, 1.2) + 16.0
    return FRAME_W - (tile + 8.0 if brand.logo else 0.0) - tag - 12.0


def _shown(word):
    return word if len(word) <= 24 else word[:22] + "\u2026"


def _widest_word(text, font, size, room):
    for word in text.split():
        if theme.width(word, font, size) > room:
            return _shown(word)
    return None


def preflight(project, brand):
    """Measures every word the pages draw by hand, before anything is drawn (review findings F02 and
    F03). Returns plain problems; an empty list means everything fits at the fixed design."""
    problems = []

    def refuse(what, text, font, size, room, where):
        word = _widest_word(text, font, size, room)
        why = 'the word "%s" is too wide' % word if word else "it needs more lines than %s has room for" % where
        problems.append('%s does not fit %s: %s. Shorten it, or break long words with spaces.' % (what, where, why))

    for name in sorted(set(lane for part in project.parts for lane in part.lanes)):
        for line in theme.chip_lines(name, CHIP_ROOM):
            if theme.tracked_width(line, theme.BOLD, 6.2, 0.7) > CHIP_ROOM:
                problems.append('The actor name "%s" does not fit the "Who" column of the step table: the word "%s" is '
                                'too wide. Put a space between its words, or use a shorter name.' % (name, _shown(line)))
                break
    if _fit_lines(project.name, theme.EXTRABOLD, (34, 29, 24), FRAME_W - 40.0, 3) is None:
        refuse('The project\'s "name"', project.name, theme.EXTRABOLD, 24, FRAME_W - 40.0, "the cover")
    if _fit_lines(project.name, theme.EXTRABOLD, (28, 24, 20), FRAME_W - 60.0, 2) is None:
        refuse('The project\'s "name"', project.name, theme.EXTRABOLD, 20, FRAME_W - 60.0, "the last page")
    for label, value in _cover_facts(project, brand):
        lines = _wrap_strict(value, theme.MEDIUM, 10, FACT_ROOM)
        if lines is None or len(lines) > 2:
            refuse('The cover\'s "%s" line ("%s")' % (label, _shown(value)), value, theme.MEDIUM, 10, FACT_ROOM,
                   "the cover in two lines")
    for sentence in _end_sentences(project, brand):
        if _wrap_strict(sentence, theme.REGULAR, 11.5, FRAME_W - 40.0) is None:
            refuse('The last page\'s line "%s"' % _shown(sentence), sentence, theme.REGULAR, 11.5, FRAME_W - 40.0,
                   "the last page")
    if _footer_text(project) is None:
        refuse('The project\'s "name"', project.name, theme.REGULAR, 7, FOOTER_ROOM, "the page footer")
    for tile, size in ((22.0, 11.0), (16.0, 9.6)):
        if theme.width(brand.name, theme.BOLD, size) > _rail_room(brand, tile):
            problems.append('The brand "name" ("%s") in assets/brand.json does not fit the bar at the top of the pages '
                            'beside the WORKFLOW tag. Use a shorter name.' % _shown(brand.name))
            break
    if brand.website and theme.width(brand.website, theme.SEMIBOLD, 12.5) > FRAME_W - 40.0:
        problems.append('The brand "website" ("%s") in assets/brand.json is too wide for the last page. Use a '
                        'shorter address.' % _shown(brand.website))
    if len(project.parts) > 1:
        for part in project.parts:
            if _map_card(part, FRAME_W) is None:
                problems.append('Part %d ("%s") does not fit its box on the map: its title must fit two lines and its '
                                'summary three, with no word wider than a line. Shorten them, or break long words '
                                'with spaces.' % (part.number, _shown(part.title)))
    return problems


# ---------------------------------------------------------------- building

def build(project, diagrams, out_path, brand):
    """Writes the PDF with the given brand (brand.load()). Builds until page numbers settle, because the
    map and the footers name real pages. Returns {"total": pages, part number: first page, ...}."""
    pages = {}
    for _ in range(4):
        record = {}
        buffer = io.BytesIO()
        total = _build_once(project, diagrams, pages, record, buffer, brand)
        found = dict(record)
        found["total"] = total
        if found == pages:
            with open(out_path, "wb") as handle:
                handle.write(buffer.getvalue())
            return found
        pages = found
    raise RuntimeError("The page numbers did not settle after four passes.")


def _build_once(project, diagrams, pages, record, target, brand):
    doc = BaseDocTemplate(target, pagesize=A4, leftMargin=MARGIN_X, rightMargin=MARGIN_X, topMargin=FRAME_TOP,
                          bottomMargin=FRAME_BOTTOM, title="%s — Workflow" % project.name,
                          author=project.prepared_by or brand.name, subject="How it works, from A to Z",
                          creator="workflow-project")
    doc.addPageTemplates(_make_templates(project, pages, brand))
    doc.build(_story(project, diagrams, pages, record))
    return doc.page
