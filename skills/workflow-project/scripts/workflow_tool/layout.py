"""Places one part's lanes and nodes on the page and wraps their words.

Pure geometry: nothing is drawn here. Every node gets its own row, in the order the file lists
them, except a stop or end that only one decision leads to: it sits beside that decision, on the
decision's row. Coordinates are points from the diagram's top-left corner; y grows downward.
"""

from . import theme
from .model import WorkflowError
from .routing import Rect, RouteError, route_all

HEADER_H = 24.0       # the band with the lane names
PAD_TOP = 12.0
PAD_BOTTOM = 10.0
ROW_GAP = 16.0        # room between rows for bends and answer labels
LANE_PAD = 12.0       # room between a box and its lane's edge, where arrows can run
GUTTER = 4.0          # arrows run this far from a lane's edge, 8 points clear of the boxes
BOX_PAD_X = 9.0
BOX_PAD_TOP = 8.0
BOX_PAD_BOTTOM = 6.0
START_R, END_R, STOP_R = 6.5, 8.0, 7.5
LABEL_GAP = 3.0
SHAPES = {"start": "circle", "end": "circle", "stop": "circle", "step": "box", "decision": "diamond"}


class Placed(object):
    """One node, where it sits, and its words already wrapped into lines."""

    def __init__(self, node, lane_index, cx):
        self.node = node
        self.lane_index = lane_index
        self.cx = cx
        self.cy = 0.0
        self.shape = SHAPES[node.type]
        self.w = self.h = self.r = 0.0
        self.title_lines = []
        self.detail_lines = []
        self.label_above = node.type == "start"
        self.label_w = self.label_h = 0.0
        self.side_of = None            # (decision id, "left" | "right") when it sits beside its decision

    @property
    def rect(self):
        return Rect(self.cx - self.w / 2.0, self.cy - self.h / 2.0, self.cx + self.w / 2.0, self.cy + self.h / 2.0)

    @property
    def label_rect(self):
        if self.shape != "circle" or not self.label_h:
            return None
        if self.label_above:
            bottom = self.cy - self.r - LABEL_GAP
            return Rect(self.cx - self.label_w / 2.0, bottom - self.label_h, self.cx + self.label_w / 2.0, bottom)
        top = self.cy + self.r + LABEL_GAP
        return Rect(self.cx - self.label_w / 2.0, top, self.cx + self.label_w / 2.0, top + self.label_h)

    @property
    def above(self):
        extra = LABEL_GAP + self.label_h if self.label_above and self.label_h else 0.0
        return self.h / 2.0 + extra

    @property
    def below(self):
        extra = LABEL_GAP + self.label_h if self.shape == "circle" and not self.label_above and self.label_h else 0.0
        return self.h / 2.0 + extra


class Diagram(object):
    """One part laid out: lanes, placed nodes and routed arrows."""

    def __init__(self, part, width):
        self.part = part
        self.width = width
        self.height = 0.0
        self.top = HEADER_H + 2.0
        self.lane_width = width / float(len(part.lanes))
        self.lanes = [(name, i * self.lane_width, (i + 1) * self.lane_width) for i, name in enumerate(part.lanes)]
        self.placed = {}
        self.rows = []
        self.channel_ys = []
        self.channel_xs = []
        self.routes = []


def wrap(text, font, size, max_width, max_lines):
    """Splits text into lines no wider than max_width. None when it needs more than max_lines."""
    lines, current = [], ""
    for word in text.split():
        candidate = word if not current else current + " " + word
        if theme.width(candidate, font, size) <= max_width:
            current = candidate
            continue
        if theme.width(word, font, size) > max_width:
            return None
        if current:
            lines.append(current)
        current = word
    if current:
        lines.append(current)
    return lines if len(lines) <= max_lines else None


def lay_out(part, width, max_height):
    """Returns the finished Diagram for one part, or raises WorkflowError saying what to change."""
    diagram = Diagram(part, width)
    problems = []
    font, size = theme.LANE_LABEL
    for name, x0, x1 in diagram.lanes:
        room = (x1 - x0) - 10.0
        lines = theme.chip_lines(name, room, font, size, 1.0)
        if len(lines) > 2 or any(theme.tracked_width(line, font, size, 1.0) > room for line in lines):
            problems.append('Part %d ("%s"): the lane name "%s" does not fit its column (%d lanes). Put a space '
                            'between its words, or use a shorter actor name.'
                            % (part.number, part.title, name, len(diagram.lanes)))
    for node in part.nodes:
        lane_index = part.lanes.index(node.lane)
        placed = Placed(node, lane_index, (lane_index + 0.5) * diagram.lane_width)
        _size(placed, diagram.lane_width, part, problems)
        diagram.placed[node.id] = placed
    if problems:
        raise WorkflowError(problems)

    _place_side_exits(diagram)
    _place_rows(diagram)
    if diagram.height > max_height:
        per_row = diagram.height / max(len(diagram.rows), 1)
        raise WorkflowError(['Part %d ("%s") is too long for one page: its drawing needs %d points and a page '
                             'holds %d (about %d rows; it has %d). Split it into two parts.'
                             % (part.number, part.title, diagram.height, max_height,
                                int(max_height // per_row), len(diagram.rows))])
    _channels(diagram)
    try:
        diagram.routes = route_all(diagram, part.edges)
    except RouteError as err:
        raise WorkflowError(['Part %d ("%s"): %s' % (part.number, part.title, err)])
    return diagram


def _size(placed, lane_width, part, problems):
    node = placed.node
    where = 'Part %d ("%s"), node "%s"' % (part.number, part.title, node.id)
    if placed.shape == "box":
        placed.w = lane_width - 2 * LANE_PAD
        inner = placed.w - 2 * BOX_PAD_X
        font, size, lead = theme.STEP_TITLE
        placed.title_lines = wrap(node.title, font, size, inner, 2)
        if placed.title_lines is None:
            problems.append('%s: the title does not fit its box in two lines; shorten it to a few words '
                            '(about %d characters).' % (where, _fits(inner, font, size, 2)))
            return
        height = BOX_PAD_TOP + lead * len(placed.title_lines) + BOX_PAD_BOTTOM
        if node.detail:
            dfont, dsize, dlead = theme.STEP_DETAIL
            placed.detail_lines = wrap(node.detail, dfont, dsize, inner, 2)
            if placed.detail_lines is None:
                problems.append('%s: the detail does not fit its box in two lines; keep it to about %d characters.'
                                % (where, _fits(inner, dfont, dsize, 2)))
                return
            height += 2.0 + dlead * len(placed.detail_lines)
        placed.h = max(height, 32.0)
    elif placed.shape == "diamond":
        _size_diamond(placed, lane_width, where, problems)
    else:
        placed.r = {"start": START_R, "end": END_R, "stop": STOP_R}[node.type]
        placed.w = placed.h = 2 * placed.r
        room = lane_width - 10.0
        font, size, lead = theme.TERMINAL_TITLE
        title = node.title
        if node.type == "end" and node.to_part:
            title = "%s → Part %d" % (title, node.to_part)
        placed.title_lines = wrap(title, font, size, room, 2)
        if placed.title_lines is None:
            problems.append('%s: the title is too long to sit under its circle; keep it to about %d characters.'
                            % (where, _fits(room, font, size, 2)))
            return
        lines_w = [theme.width(t, font, size) for t in placed.title_lines]
        placed.label_h = lead * len(placed.title_lines)
        if node.detail and node.type != "start":
            dfont, dsize, dlead = theme.TERMINAL_DETAIL
            placed.detail_lines = wrap(node.detail, dfont, dsize, room, 2)
            if placed.detail_lines is None:
                problems.append('%s: the detail is too long to sit under its circle; keep it to about %d characters.'
                                % (where, _fits(room, dfont, dsize, 2)))
                return
            lines_w += [theme.width(t, dfont, dsize) for t in placed.detail_lines]
            placed.label_h += dlead * len(placed.detail_lines)
        placed.label_w = max(lines_w) + 2.0


def _size_diamond(placed, lane_width, where, problems):
    font, size, lead = theme.DECISION_TEXT
    most = min(lane_width / 2.0 - 8.0, 46.0)
    for lines_allowed, half_height in ((1, 20.0), (2, 25.0)):
        offsets = [0.0] if lines_allowed == 1 else [-lead / 2.0, lead / 2.0]
        # the narrowest text row decides how wide the lines may be
        room = min(2 * (most * (1 - (abs(dy) + size * 0.45) / half_height) - 3.0) for dy in offsets)
        lines = wrap(placed.node.title, font, size, room, lines_allowed)
        if lines is not None:
            break
    if lines is None:
        problems.append('%s: the question does not fit its diamond; keep it to a few words, like "Approved?" '
                        '(about %d characters).' % (where, _fits(room, font, size, 2)))
        return
    offsets = [0.0] if len(lines) == 1 else [-lead / 2.0, lead / 2.0]
    need = 26.0
    for text, dy in zip(lines, offsets):
        half_text = theme.width(text, font, size) / 2.0 + 3.0
        need = max(need, half_text / (1 - (abs(dy) + size * 0.45) / half_height))
    placed.title_lines = lines
    placed.w = 2 * min(need, most)
    placed.h = 2 * half_height


def _fits(room, font, size, lines):
    return int(room / (size * 0.55) * lines)


def _place_side_exits(diagram):
    part = diagram.part
    taken = {}
    for node in part.nodes:
        if node.type not in ("end", "stop"):
            continue
        incoming = part.incoming(node.id)
        if len(incoming) != 1:
            continue
        decision = part.by_id[incoming[0].source]
        if decision.type != "decision" or decision.lane == node.lane or decision.index > node.index:
            continue
        here, there = diagram.placed[node.id], diagram.placed[decision.id]
        side = "left" if here.lane_index < there.lane_index else "right"
        if side in taken.setdefault(decision.id, set()):
            continue
        taken[decision.id].add(side)
        here.side_of = (decision.id, side)


def _place_rows(diagram):
    part = diagram.part
    beside = {}
    for node in part.nodes:
        placed = diagram.placed[node.id]
        if placed.side_of is not None:
            beside.setdefault(placed.side_of[0], []).append(node.id)
    for node in part.nodes:
        if diagram.placed[node.id].side_of is None:
            diagram.rows.append([node.id] + beside.get(node.id, []))
    y = HEADER_H + PAD_TOP
    diagram.row_spans = []
    for row in diagram.rows:
        above = max(diagram.placed[i].above for i in row)
        below = max(diagram.placed[i].below for i in row)
        centre = y + above
        for node_id in row:
            diagram.placed[node_id].cy = centre
        diagram.row_spans.append((y, centre + below))
        y = centre + below + ROW_GAP
    diagram.height = y - ROW_GAP + PAD_BOTTOM


def _channels(diagram):
    """The free lines where arrows may run: between rows, and in the gutters beside the lanes."""
    spans = diagram.row_spans
    ys = [(HEADER_H + spans[0][0]) / 2.0]
    ys += [(spans[i][1] + spans[i + 1][0]) / 2.0 for i in range(len(spans) - 1)]
    ys.append((spans[-1][1] + diagram.height) / 2.0)
    diagram.channel_ys = ys
    xs = []
    for _, x0, x1 in diagram.lanes:
        xs += [x0 + GUTTER, x1 - GUTTER, (x0 + x1) / 2.0]
    diagram.channel_xs = sorted(set(x for x in xs if 1.0 < x < diagram.width - 1.0))
