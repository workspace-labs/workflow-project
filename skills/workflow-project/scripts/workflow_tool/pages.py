"""Puts the whole workflow PDF together, on A4 pages lying sideways.

Order: the cover · the map (who takes part, and every part as one box with its page) · one page per
part (its board). What was assumed and what is still to confirm go under the map when they fit there,
and on a last page of their own when they do not.
Every page is drawn straight onto the canvas at fixed places, so each part's page number is known
before anything is drawn.

Each page has a `_plan_...` function that measures and wraps every word it will draw. `preflight` runs
them all first and returns plain problems; the drawing functions only draw a plan that fits.
"""

import datetime
import math

from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen.canvas import Canvas

from . import language, paint, render_diagram, theme
from .language import t
from .mirror import MirrorCanvas

PAGE_W, PAGE_H = landscape(A4)
MARGIN_X = 33.0
FRAME_W = PAGE_W - 2 * MARGIN_X
BODY_TOP = PAGE_H - 56.0            # below the brand line
BODY_BOTTOM = 36.0                  # above the footer
KEY_ROOM = 9.0 + render_diagram.KEY_H
TITLE_SIZES = (25.5, 21.0, 18.0)
LEDE = (theme.REGULAR, 11.0, 15.0)
LEDE_W = FRAME_W - 120.0
FOOTER = (theme.REGULAR, 8.2)
WEBSITE = (theme.REGULAR, 8.6)
FOOTER_ROOM = FRAME_W - 110.0       # the footer's left text, clear of "Page n of N"
COVER_X = 39.0
COVER_W = PAGE_W - 2 * COVER_X
COVER_SIZES = ((99.0, 1), (82.0, 1), (66.0, 1), (54.0, 2), (44.0, 2), (36.0, 3))
PATH_MOST = 12                      # ponytail: the cover names up to 12 parts; a longer project keeps a plain cover
CARD_GAP = 19.5
ACTOR_GAP = 9.0


# ---------------------------------------------------------------- small helpers

def nice_date(value):
    """The date in the workflow's language. Month names come from the language file, never from the
    computer: strftime("%B") follows the computer's language, which the font may not be able to draw."""
    try:
        day = datetime.datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return value
    return t("date_format", day=day.day, month=language.month(day.month), year=day.year)


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


def _wrap(text, font, size, room, most):
    """Like _wrap_strict, and None too when the text needs more than `most` lines."""
    lines = _wrap_strict(text, font, size, room)
    return lines if lines is not None and len(lines) <= most else None


def _fit(text, font, sizes, room):
    """The first of `sizes` ((size, most lines), ...) at which the text fits, and its lines; else None."""
    for size, most in sizes:
        lines = _wrap(text, font, size, room, most)
        if lines is not None:
            return size, lines
    return None


def _shown(word):
    return word if len(word) <= 24 else word[:22] + "…"


def _why(text, font, size, room, where):
    for word in text.split():
        if theme.width(word, font, size) > room:
            return 'the word "%s" is too wide' % _shown(word)
    return "it needs more lines than %s has room for" % where


def _refusal(what, text, font, size, room, where):
    return '%s does not fit %s: %s. Shorten it, or break long words with spaces.' % (
        what, where, _why(text, font, size, room, where))


def _text(c, lines, x, top, font, size, lead, colour):
    """Draws lines downward from `top`; returns the height where they end."""
    c.setFillColor(colour)
    c.setFont(font, size)
    y = top
    for line in lines:
        c.drawString(x, y - lead + (lead - size) / 2.0 + size * 0.22, line)
        y -= lead
    return y


def _begin(c):
    """A right-to-left page is the same page, mirrored."""
    if language.rtl():
        c.begin_page(PAGE_W)


# ---------------------------------------------------------------- the brand line and the footer

def _rail(c, brand, x, right, y, on_dark=False):
    ink = theme.WHITE if on_dark else theme.INK
    if brand.logo:
        paint.draw_logo_tile(c, brand.logo, x, y - 7.5, 15.0, 3.6)
        x += 15.0 + 7.0
    paint.draw_accent_line(c, brand.name, brand.accent, x, y - 3.4, theme.BOLD, 9.8, ink,
                           accent_color=theme.COVER_BLUE_SOFT if on_dark else theme.ACCENT)
    font, size = theme.SEMIBOLD, 8.6
    w = theme.width(t("tag"), font, size) + 22.0
    c.setStrokeColor(ink if on_dark else theme.LINE)
    c.setLineWidth(1.0)
    c.roundRect(right - w, y - 8.5, w, 17.0, 8.5, stroke=1, fill=0)
    c.setFillColor(ink if on_dark else theme.INK_SOFT)
    c.setFont(font, size)
    c.drawCentredString(right - w / 2.0, y - size * 0.34, t("tag"))
    if on_dark and brand.website:       # the cover also says where to find whoever made this
        c.setFillColor(theme.COVER_SOFT)
        c.setFont(*WEBSITE)
        c.drawRightString(right - w - 14.0, y - WEBSITE[1] * 0.34, brand.website)


def _website_room(brand):
    """How wide the website may be on the cover's top line, beside the brand name and the tag."""
    name = (22.0 if brand.logo else 0.0) + theme.width(brand.name, theme.BOLD, 9.8)
    tag = theme.width(t("tag"), theme.SEMIBOLD, 8.6) + 22.0
    return min(COVER_W - name - tag - 2 * 14.0, 260.0)


def _footer_text(project):
    """The longest footer that fits: in full, then without version and date, then the name alone."""
    full = t("footer_full", name=project.name, version=project.version, date=nice_date(project.date))
    for text in (full, t("footer_short", name=project.name), project.name):
        if theme.width(text, *FOOTER) <= FOOTER_ROOM:
            return text
    return None


def _inner_page(c, project, brand, number, total):
    _begin(c)
    _rail(c, brand, MARGIN_X, PAGE_W - MARGIN_X, PAGE_H - 33.0)
    c.setFillColor(theme.INK_SOFT)
    c.setFont(*FOOTER)
    c.drawString(MARGIN_X, 17.0, _footer_text(project))
    c.drawRightString(PAGE_W - MARGIN_X, 17.0, t("page_of", n=number, total=total))


def _heading_height(sub_lines):
    return 46.0 + LEDE[2] * len(sub_lines) + 10.0


def _draw_heading(c, eyebrow, title, size, sub_lines):
    """The small blue line, the title and the sentence under it. Returns the height where the body starts."""
    c.setFillColor(theme.ACCENT)
    c.setFont(theme.BOLD, 9.4)
    c.drawString(MARGIN_X, BODY_TOP - 9.0, eyebrow)
    c.setFillColor(theme.INK)
    c.setFont(theme.EXTRABOLD, size)
    c.drawString(MARGIN_X, BODY_TOP - 38.0, title)
    _text(c, sub_lines, MARGIN_X, BODY_TOP - 46.0, LEDE[0], LEDE[1], LEDE[2], theme.INK_SOFT)
    return BODY_TOP - _heading_height(sub_lines)


# ---------------------------------------------------------------- the cover

def _cover_facts(project, brand):
    facts = [(t("prepared_for"), project.client), (t("prepared_by"), project.prepared_by or brand.name),
             (t("date"), nice_date(project.date)), (t("version"), project.version), (t("status"), project.status)]
    return [(label, value) for label, value in facts if value]


def _plan_cover(project, brand, total):
    problems = []
    plan = {"title": _fit(project.name, theme.EXTRABOLD, COVER_SIZES, COVER_W)}
    if plan["title"] is None:
        problems.append(_refusal('The project\'s "name"', project.name, theme.EXTRABOLD, 36.0, COVER_W, "the cover"))
    plan["line"] = t("cover_line_many" if total > 10 else "cover_line", pages=total)

    facts = _cover_facts(project, brand)
    plan["fact_w"] = min(COVER_W / len(facts), 190.0)
    plan["facts"] = []
    for label, value in facts:
        lines = _wrap(value, theme.BOLD, 10.2, plan["fact_w"] - 22.0, 4)
        if lines is None:
            problems.append(_refusal('The cover\'s "%s" line ("%s")' % (label, _shown(value)), value, theme.BOLD,
                                     10.2, plan["fact_w"] - 22.0, "the cover in four lines"))
        plan["facts"].append((label, lines or []))

    parts = project.parts if 1 < len(project.parts) <= PATH_MOST else []
    rows = 1 if len(parts) <= 6 else 2
    per_row = int(math.ceil(len(parts) / float(rows))) if parts else 1
    plan["cell_w"] = COVER_W / per_row
    plan["path"] = []
    for part in parts:
        fitted = _fit(part.title, theme.SEMIBOLD, ((12.5, 3), (10.5, 3)), plan["cell_w"] - 16.0)
        if fitted is None:
            problems.append(_refusal('Part %d\'s title ("%s")' % (part.number, _shown(part.title)), part.title,
                                     theme.SEMIBOLD, 10.5, plan["cell_w"] - 16.0, "the path on the cover"))
        plan["path"].append((part.number, fitted or (10.5, [])))
    plan["rows"] = [plan["path"][i:i + per_row] for i in range(0, len(plan["path"]), per_row)]
    return plan, problems


def _draw_cover(c, project, brand, plan):
    _begin(c)
    c.setFillColor(theme.INK)
    c.rect(0, 0, PAGE_W, PAGE_H, stroke=0, fill=1)
    _rail(c, brand, COVER_X, PAGE_W - COVER_X, PAGE_H - 39.0, on_dark=True)

    # the facts, along the bottom
    x = COVER_X
    extra = 13.0 * (max(len(lines) for _, lines in plan["facts"]) - 1)
    for label, lines in plan["facts"]:
        c.setFillColor(theme.COVER_SOFT)
        c.setFont(theme.REGULAR, 8.6)
        c.drawString(x, 54.0 + extra, label)
        _text(c, lines, x, 50.0 + extra, theme.BOLD, 10.2, 13.0, theme.WHITE)
        x += plan["fact_w"]

    # the path: every part on one line, from the first to the last
    line_y = 152.0 + extra + 92.0 * (len(plan["rows"]) - 1)
    path_top = line_y + 12.0 if plan["rows"] else 96.0 + extra
    for n, row in enumerate(plan["rows"]):
        y = line_y - 92.0 * n
        end = COVER_X + plan["cell_w"] * len(row)
        c.setStrokeColor(theme.COVER_BLUE)
        c.setLineWidth(3.0)
        c.line(COVER_X, y, end, y)
        for k, (number, (size, lines)) in enumerate(row):
            x = COVER_X + plan["cell_w"] * k
            c.setFillColor(theme.INK)
            c.circle(x + 6.5, y, 5.4, stroke=1, fill=1)
            c.setFillColor(theme.COVER_BLUE_SOFT)
            c.setFont(theme.MEDIUM, 9.8)
            c.drawString(x, y - 26.0, str(number))
            _text(c, lines, x, y - 31.0, theme.SEMIBOLD, size, size * 1.24, theme.WHITE)
        if n == len(plan["rows"]) - 1:
            c.setFillColor(theme.WHITE)
            c.circle(end - 6.5, y, 6.5, stroke=0, fill=1)

    # the name and its line, in the middle of the room that is left
    size, lines = plan["title"]
    block = size * 1.04 * len(lines) + 34.0
    top = (PAGE_H - 62.0 + path_top) / 2.0 + block / 2.0
    y = top
    c.setFillColor(theme.WHITE)
    c.setFont(theme.EXTRABOLD, size)
    for line in lines:
        y -= size * 1.04
        c.drawString(COVER_X - size * 0.035, y + size * 0.26, line)
    c.setFillColor(theme.COVER_SOFT)
    c.setFont(theme.MEDIUM, 17.5)
    c.drawString(COVER_X, y - 22.0, plan["line"])


# ---------------------------------------------------------------- the map

def _plan_map(project):
    """Who takes part and every part as a card, cut into as many pages as the cards need."""
    problems = []
    plan = {"size": TITLE_SIZES[0]}
    sub = _wrap(project.summary + " " + t("map_lede"), LEDE[0], LEDE[1], LEDE_W, 7)
    if sub is None:
        problems.append(_refusal('The project\'s "summary"', project.summary, LEDE[0], LEDE[1], LEDE_W,
                                 "the top of the map"))
    plan["sub"] = sub or []

    colours = dict((name, theme.ACTOR_COLOURS[index % len(theme.ACTOR_COLOURS)])
                   for index, (name, _) in enumerate(project.actors))
    for per_row in range(min(len(project.actors), 7), 0, -1):     # as many side by side as their words allow
        width = min((FRAME_W - ACTOR_GAP * (per_row - 1)) / per_row, 250.0)
        cards = [(name, _wrap(name, theme.BOLD, 11.0, width - 22.0, 2),
                  _wrap(role, theme.REGULAR, 9.2, width - 22.0, 6) if role else [], colours[name])
                 for name, role in project.actors]
        if all(names is not None and roles is not None for _, names, roles, _ in cards):
            break
    for name, names, roles, _ in cards:
        if names is None or roles is None:
            problems.append('The actor "%s" does not fit its card on the map: its name must fit two lines and its '
                            'role six. Shorten them, or break long words with spaces.' % _shown(name))
    cards = [(name, names or [], roles or [], colour) for name, names, roles, colour in cards]
    plan["actor_w"] = width
    plan["actor_rows"] = [cards[i:i + per_row] for i in range(0, len(cards), per_row)]
    plan["actor_heights"] = [max(13.0 + 14.0 * len(names) + 12.4 * len(roles) + 9.0 for _, names, roles, _ in row)
                             for row in plan["actor_rows"]]

    count = len(project.parts)
    most = count if count <= 6 else int(math.ceil(count / math.ceil(count / 6.0)))
    for per_row in range(most, 0, -1):          # as many side by side as their words allow
        width = min((FRAME_W - CARD_GAP * (per_row - 1)) / per_row, 230.0)
        cards = [_part_card_plan(part, width, colours) for part in project.parts]
        if all(card["fits"] for card in cards) or per_row <= min(most, 3):
            break
    plan["card_w"] = width
    for card in cards:
        if not card["fits"]:
            problems.append('Part %d ("%s") does not fit its box on the map: its title must fit three lines and '
                            'its summary nine, with no word or lane name wider than the box. Shorten them, or break '
                            'long words with spaces.' % (card["part"].number, _shown(card["part"].title)))
    rows = [cards[i:i + per_row] for i in range(0, len(cards), per_row)]

    # cut the rows of cards into pages
    first_room = (BODY_TOP - _heading_height(plan["sub"]) - 20.0 - sum(plan["actor_heights"])
                  - ACTOR_GAP * len(plan["actor_rows"]) - 8.0 - 20.0 - BODY_BOTTOM - 6.0)
    more_room = BODY_TOP - _heading_height([]) - 20.0 - BODY_BOTTOM - 6.0
    plan["pages"], room, used, page = [], first_room, 0.0, []
    for row in rows:
        height = max(card["height"] for card in row)
        if height > more_room:
            problems.append('The map\'s boxes for parts %d to %d are too tall for a page. Shorten their summaries.'
                            % (row[0]["part"].number, row[-1]["part"].number))
            height = more_room
        if used + height > room and (page or not plan["pages"]):
            plan["pages"].append((page, room, used))
            page, room, used = [], more_room, 0.0
        page.append((row, height))
        used += height + CARD_GAP
    plan["pages"].append((page, room, used))
    return plan, problems


def _part_card_plan(part, width, colours):
    """One part's card on the map: its wrapped words, its lane chips in rows, and its height."""
    room = width - 28.0
    title = _wrap(part.title, theme.BOLD, 13.5, room, 3)
    summary = _wrap(part.summary, theme.REGULAR, 9.6, room, 9) if part.summary else []
    chips, x, fits = [[]], 0.0, title is not None and summary is not None
    for lane in part.lanes:
        chip = theme.width(lane, theme.SEMIBOLD, 8.2) + 21.0
        fits = fits and chip <= room
        if chips[-1] and x + chip > room:
            chips.append([])
            x = 0.0
        chips[-1].append((x, chip, lane, colours.get(lane, theme.INK_SOFT)))
        x += chip + 4.0
    title, summary = title or [], summary or []
    height = 14.0 + 38.0 + 16.5 * len(title) + 4.0 + 12.6 * len(summary) + 8.0 + 16.0 * len(chips) + 8.0 + 27.0
    return {"part": part, "title": title, "summary": summary, "chips": chips, "height": height, "fits": fits}


def _draw_map_page(c, project, plan, index, part_pages, closing=None):
    """One page of the map. `closing` is the plan of what was assumed and is still to confirm, when it is
    drawn under this page's cards."""
    rows, room, used = plan["pages"][index]
    if index == 0:
        y = _draw_heading(c, t("map_overline"), t("map_title"), plan["size"], plan["sub"])
        c.setFillColor(theme.INK_SOFT)
        c.setFont(theme.BOLD, 9.4)
        c.drawString(MARGIN_X, y - 11.0, t("who"))
        y -= 20.0
        for row, height in zip(plan["actor_rows"], plan["actor_heights"]):
            for k, (_, names, roles, colour) in enumerate(row):
                x = MARGIN_X + (plan["actor_w"] + ACTOR_GAP) * k
                _actor_card(c, x, y, plan["actor_w"], height, names, roles, colour)
            y -= height + ACTOR_GAP
        y -= 8.0
    else:
        y = _draw_heading(c, t("map_overline_more"), t("map_title"), plan["size"], [])
    if rows:
        c.setFillColor(theme.INK_SOFT)
        c.setFont(theme.BOLD, 9.4)
        c.drawString(MARGIN_X, y - 11.0, t("main_parts"))
        y -= 20.0
    grow = 0.0 if closing or not rows else min(max(room - used + CARD_GAP, 0.0) / len(rows), 24.0)
    last = project.parts[-1].number
    for row, height in rows:
        height += grow
        for k, card in enumerate(row):
            x = MARGIN_X + (plan["card_w"] + CARD_GAP) * k
            _part_card(c, x, y, plan["card_w"], height, card, part_pages)
            if card["part"].number != last and k < len(row) - 1:
                _chevron(c, x + plan["card_w"] + CARD_GAP / 2.0, y - height / 2.0)
        y -= height + CARD_GAP
    if closing:
        _draw_closing(c, closing, y)


def _actor_card(c, x, top, width, height, names, roles, colour):
    c.saveState()
    clip = c.beginPath()
    clip.roundRect(x, top - height, width, height, 8.0)
    c.clipPath(clip, stroke=0, fill=0)
    c.setFillColor(colour)
    c.rect(x, top - 3.2, width, 3.2, stroke=0, fill=1)
    c.restoreState()
    c.setStrokeColor(theme.LINE)
    c.setLineWidth(0.8)
    c.roundRect(x, top - height, width, height, 8.0, stroke=1, fill=0)
    y = _text(c, names, x + 11.0, top - 11.0, theme.BOLD, 11.0, 14.0, theme.INK)
    _text(c, roles, x + 11.0, y - 1.0, theme.REGULAR, 9.2, 12.4, theme.INK_SOFT)


def _part_card(c, x, top, width, height, card, part_pages):
    part = card["part"]
    c.setFillColor(theme.WHITE)
    c.setStrokeColor(theme.LINE)
    c.setLineWidth(0.9)
    c.roundRect(x, top - height, width, height, 10.0, stroke=1, fill=1)
    left = x + 14.0
    c.setFillColor(theme.ACCENT)
    c.setFont(theme.EXTRABOLD, 38.0)
    c.drawString(left - 1.5, top - 14.0 - 29.0, str(part.number))
    y = _text(c, card["title"], left, top - 52.0, theme.BOLD, 13.5, 16.5, theme.INK)
    y = _text(c, card["summary"], left, y - 4.0, theme.REGULAR, 9.6, 12.6, theme.INK_SOFT) - 8.0
    for row in card["chips"]:
        for dx, chip, lane, colour in row:
            c.setFillColor(theme.CHIP_BG)
            c.roundRect(left + dx, y - 13.0, chip, 13.0, 6.5, stroke=0, fill=1)
            c.setFillColor(colour)
            c.circle(left + dx + 8.0, y - 6.5, 2.6, stroke=0, fill=1)
            c.setFillColor(theme.INK)
            c.setFont(theme.SEMIBOLD, 8.2)
            c.drawString(left + dx + 14.5, y - 6.5 - 8.2 * 0.34, lane)
        y -= 16.0
    base = top - height + 11.0
    c.setStrokeColor(theme.LINE)
    c.setLineWidth(0.8)
    c.line(left, base + 18.0, x + width - 14.0, base + 18.0)
    number = str(part_pages[part.number])
    c.setFillColor(theme.INK)
    c.setFont(theme.BOLD, 14.0)
    c.drawString(left, base, number)
    c.setFillColor(theme.INK_SOFT)
    c.setFont(theme.REGULAR, 8.4)
    c.drawString(left + theme.width(number, theme.BOLD, 14.0) + 5.0, base + 0.6, t("map_page"))


def _chevron(c, x, y):
    c.saveState()
    c.setStrokeColor(theme.ACCENT)
    c.setLineWidth(2.2)
    c.setLineJoin(1)
    c.setLineCap(1)
    path = c.beginPath()
    path.moveTo(x - 2.6, y + 5.2)
    path.lineTo(x + 2.6, y)
    path.lineTo(x - 2.6, y - 5.2)
    c.drawPath(path, stroke=1, fill=0)
    c.restoreState()


# ---------------------------------------------------------------- a part's page

def _plan_part(part, total_parts):
    problems = []
    eyebrow = t("part_of", n=part.number, total=total_parts) if total_parts > 1 else t("the_workflow")
    fitted = _fit(part.title, theme.EXTRABOLD, [(size, 1) for size in TITLE_SIZES], FRAME_W)
    if fitted is None:
        problems.append(_refusal('Part %d\'s title ("%s")' % (part.number, _shown(part.title)), part.title,
                                 theme.EXTRABOLD, TITLE_SIZES[-1], FRAME_W, "one line at the top of its page"))
    sub = _wrap(part.summary or t("part_lede"), LEDE[0], LEDE[1], LEDE_W, 2)
    if sub is None:
        problems.append(_refusal('Part %d\'s summary' % part.number, part.summary, LEDE[0], LEDE[1], LEDE_W,
                                 "two lines under its title"))
    return {"eyebrow": eyebrow, "title": fitted or (TITLE_SIZES[-1], [part.title]), "sub": sub or []}, problems


def board_room(part, total_parts):
    """How tall a part's board may be so it shares one page with its heading and key."""
    plan, _ = _plan_part(part, total_parts)
    return BODY_TOP - _heading_height(plan["sub"]) - KEY_ROOM - BODY_BOTTOM - 6.0


def _draw_part_page(c, part, total_parts, diagram):
    plan, _ = _plan_part(part, total_parts)
    size, lines = plan["title"]
    top = _draw_heading(c, plan["eyebrow"], lines[0], size, plan["sub"])
    render_diagram.draw_board(c, diagram, MARGIN_X, top)
    render_diagram.draw_key(c, MARGIN_X, top - diagram.height - 9.0 - render_diagram.KEY_H / 2.0)


# ---------------------------------------------------------------- the last page

def _plan_closing(project):
    """What was assumed and what is still to confirm; None when there is neither."""
    lists = [(t(key), items) for key, items in (("assumed", project.assumptions), ("confirm", project.open_questions))
             if items]
    if not lists:
        return None, []
    width = (FRAME_W - 36.0) / 2.0 if len(lists) == 2 else FRAME_W * 0.7
    problems, columns, tallest = [], [], 0.0
    room = BODY_TOP - _heading_height([]) - BODY_BOTTOM
    for title, items in lists:
        wrapped = [_wrap_strict(item, theme.REGULAR, 9.8, width - 14.0) for item in items]
        if any(lines is None for lines in wrapped):
            problems.append('A sentence under "%s" has a word too wide for the page. Break long words with '
                            'spaces.' % title)
            wrapped = [lines or [] for lines in wrapped]
        tallest = max(tallest, 20.0 + sum(13.6 * len(lines) + 5.0 for lines in wrapped))
        columns.append((title, wrapped))
    if tallest > room:
        problems.append('The sentences under "%s" and "%s" need more than a page holds. Shorten them, or keep '
                        'fewer.' % (t("assumed"), t("confirm")))
    return {"width": width, "columns": columns, "height": tallest}, problems


def _draw_closing(c, plan, y):
    """The two lists, side by side, from the height y downward."""
    for k, (title, items) in enumerate(plan["columns"]):
        x = MARGIN_X + (plan["width"] + 36.0) * k
        c.setFillColor(theme.INK_SOFT)
        c.setFont(theme.BOLD, 9.4)
        c.drawString(x, y - 11.0, title)
        top = y - 20.0
        for lines in items:
            c.setFillColor(theme.ACCENT)
            c.circle(x + 3.0, top - 6.8, 2.2, stroke=0, fill=1)
            top = _text(c, lines, x + 14.0, top, theme.REGULAR, 9.8, 13.6, theme.INK) - 5.0


# ---------------------------------------------------------------- the whole document

def page_plan(project):
    """Which page everything is on: {"total": pages, "map": map pages, "closing": True when what was assumed
    and is still to confirm needs a page of its own, part number: its page, ...}."""
    map_plan, _ = _plan_map(project)
    closing, _ = _plan_closing(project)
    _, room, used = map_plan["pages"][-1]
    found = {"map": len(map_plan["pages"]), "closing": bool(closing) and closing["height"] > room - used - 4.0}
    for part in project.parts:
        found[part.number] = 1 + found["map"] + part.number
    found["total"] = 1 + found["map"] + len(project.parts) + (1 if found["closing"] else 0)
    return found


def preflight(project, brand):
    """Measures every word the pages draw, before anything is drawn. Returns plain problems; an empty
    list means everything fits at the fixed design."""
    problems = []
    found = page_plan(project)
    problems += _plan_cover(project, brand, found["total"])[1]
    problems += _plan_map(project)[1]
    for part in project.parts:
        problems += _plan_part(part, len(project.parts))[1]
    problems += _plan_closing(project)[1]
    if _footer_text(project) is None:
        problems.append(_refusal('The project\'s "name"', project.name, FOOTER[0], FOOTER[1], FOOTER_ROOM,
                                 "the page footer"))
    if brand.website and theme.width(brand.website, *WEBSITE) > _website_room(brand):
        problems.append('The brand "website" ("%s") in assets/brand.json is too wide for the top of the cover, '
                        'beside the brand name. Use a shorter address.' % _shown(brand.website))
    return problems


def build(project, diagrams, out_path, brand):
    """Writes the PDF with the given brand (brand.load()). Returns page_plan(project)."""
    found = page_plan(project)
    total = found["total"]
    c = (MirrorCanvas if language.rtl() else Canvas)(out_path, pagesize=(PAGE_W, PAGE_H))
    c.setTitle(t("doc_title", name=project.name))
    c.setAuthor(project.prepared_by or brand.name)
    c.setSubject(t("doc_subject"))
    c.setCreator("workflow-project")

    _draw_cover(c, project, brand, _plan_cover(project, brand, total)[0])
    c.showPage()
    map_plan, _ = _plan_map(project)
    closing, _ = _plan_closing(project)
    for index in range(found["map"]):
        under = closing if index == found["map"] - 1 and not found["closing"] else None
        _inner_page(c, project, brand, 2 + index, total)
        _draw_map_page(c, project, map_plan, index, found, under)
        c.showPage()
    for part, diagram in zip(project.parts, diagrams):
        _inner_page(c, project, brand, found[part.number], total)
        _draw_part_page(c, part, len(project.parts), diagram)
        c.showPage()
    if found["closing"]:
        _inner_page(c, project, brand, total, total)
        _draw_closing(c, closing, _draw_heading(c, project.name, t("closing_title"), TITLE_SIZES[0], []))
        c.showPage()
    c.save()
    return found
