"""Places one part on its board and wraps its words.

Pure geometry: nothing is drawn here. The board lies sideways: every lane is a row, and time runs
across, column by column, in the order the file lists the nodes. When the work passes straight down to
a lower lane, the next node sits in the same column, under the one before; otherwise it opens a new
column. Under the lanes, a strip says what comes out of each column's steps.

A start, stop or end is a small mark with its words. When it belongs to one step in its own lane, it
is a flag on that step's box, with no arrow: a start above the box, a stop or end below it. Otherwise
it stands alone as a pill, with its arrow.

Coordinates are points from the board's top-left corner; y grows downward.
"""

from . import language, theme
from .model import TERMINALS, WorkflowError
from .routing import ANSWER_PAD, Rect, RouteError, route_all

LABEL_W = 96.0        # the dark column with the lane names
LABEL_PAD = 9.0
PAD_SIDE = 14.0       # room before the first column and after the last
COL_GAP = 18.0        # room between two columns, where arrows bend
CHANNEL = 9.0         # arrows run down a column gap this far before the next column's boxes
LANE_PAD = 9.0        # room above and below a lane's tallest box, where arrows can run
GUTTER = 3.0          # arrows run this far from a lane's edge
LANE_MIN, LANE_MOST = 44.0, 190.0
BOX_MIN, BOX_MOST = 62.0, 150.0
PILL_SHARE = 0.85     # a start, stop or end on its own takes this much of a box's width
BOX_PAD_X, BOX_PAD_TOP, BOX_PAD_BOTTOM = 8.0, 7.5, 6.5
BOX_MIN_H = 30.0
NAME_SIZES = (10.4, 9.4, 8.6)
PILL_PAD_Y = 6.0
DOT_ROOM = 12.0       # the round mark before a start, stop or end, and the air after it
FLAG_GAP = 5.0        # between a flag and what is under it
TITLE_LINES, DETAIL_LINES, MARK_LINES, NAME_LINES, STRIP_LINES = 5, 4, 4, 3, 6
STRIP_PAD, STRIP_NUMBER_W, STRIP_ROW, STRIP_ENTRY_GAP, STRIP_MIN = 8.0, 17.0, 14.0, 5.0, 44.0


class Mark(object):
    """A start, stop or end as it is written: its node and its wrapped lines."""

    def __init__(self, node):
        self.node = node
        self.title_lines = []
        self.detail_lines = []

    @property
    def height(self):
        return theme.FLAG[2] * len(self.title_lines) + theme.STEP_DETAIL[2] * len(self.detail_lines)


class Placed(object):
    """One node with a place of its own: where it sits, and its words already wrapped into lines."""

    def __init__(self, node, lane_index):
        self.node = node
        self.lane_index = lane_index
        self.cx = self.cy = 0.0
        self.w = self.h = 0.0
        self.shape = "pill" if node.type in ("start",) + TERMINALS else "box"
        self.title_lines = []
        self.detail_lines = []
        self.mark = Mark(node) if self.shape == "pill" else None
        self.flag_above = None         # the start drawn as a flag above this box
        self.flag_below = None         # the stop or end drawn as a flag below it
        self.side_of = None            # (decision id, "top" | "bottom") when it sits in its decision's column
        self.on_main = True            # False for a step only another path reaches

    @property
    def rect(self):
        return Rect(self.cx - self.w / 2.0, self.cy - self.h / 2.0, self.cx + self.w / 2.0, self.cy + self.h / 2.0)

    @property
    def above(self):
        """How far it reaches above its middle, flag included."""
        return self.h / 2.0 + (self.flag_above.height + FLAG_GAP if self.flag_above else 0.0)

    @property
    def below(self):
        return self.h / 2.0 + (self.flag_below.height + FLAG_GAP if self.flag_below else 0.0)

    @property
    def flags(self):
        return [flag for flag in (self.flag_above, self.flag_below) if flag is not None]

    @property
    def label_rects(self):
        """The room its flags take, above and below the box."""
        x0, x1 = self.cx - self.w / 2.0, self.cx + self.w / 2.0
        found = []
        if self.flag_above:
            found.append(Rect(x0, self.cy - self.above, x1, self.cy - self.h / 2.0))
        if self.flag_below:
            found.append(Rect(x0, self.cy + self.h / 2.0, x1, self.cy + self.below))
        return found


class Column(object):
    def __init__(self, ids):
        self.ids = ids                 # its nodes, in the order the file lists them
        self.x0 = self.x1 = 0.0        # where its boxes start and stop
        self.cell = (0.0, 0.0)         # where its cell in the strip starts and stops
        self.entries = []              # [(the step number or "?", what comes out, wrapped)], top lane first


class Diagram(object):
    """One part laid out: lanes, placed nodes, routed arrows and the strip under them."""

    def __init__(self, part, width):
        self.part = part
        self.width = width
        self.height = 0.0              # the whole board, strip included
        self.left = LABEL_W + 2.0      # arrows stay right of the lane names
        self.bottom = 0.0              # where the lanes end and the strip begins
        self.strip_h = STRIP_MIN
        self.lanes = []                # [(name, y0, y1)]
        self.lane_lines = []           # each lane's name, wrapped
        self.lane_size = theme.LANE_LABEL[1]    # the size all the names are written at
        self.placed = {}
        self.attached = {}             # the id of a start, stop or end drawn as a flag -> the id of its box
        self.columns = []
        self.channel_ys = []
        self.channel_xs = []
        self.routes = []

    @property
    def edges(self):
        """The arrows that are drawn: a flag needs none."""
        return [e for e in self.part.edges if e.source not in self.attached and e.target not in self.attached]


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


def lay_out(part, width, max_height, pages=None):
    """Returns the finished Diagram for one part, or raises WorkflowError saying what to change.

    `pages` is {part number: its page}, for an end that continues in another part.
    """
    diagram = Diagram(part, width)
    diagram.attached = _attach(part)
    for node in part.nodes:
        if node.id not in diagram.attached:
            diagram.placed[node.id] = Placed(node, part.lanes.index(node.lane))
    for node in part.nodes:
        if node.id in diagram.attached:
            host = diagram.placed[diagram.attached[node.id]]
            if node.type == "start":
                host.flag_above = Mark(node)
            else:
                host.flag_below = Mark(node)
    for placed in diagram.placed.values():
        placed.on_main = placed.shape != "box" or any(
            e.main for e in part.edges if placed.node.id in (e.source, e.target))

    _place_side_exits(diagram)
    _place_columns(diagram)
    problems = []
    _name_lanes(diagram, problems)
    for placed in diagram.placed.values():
        _size(placed, part, problems)
    _fill_strip(diagram, pages or {}, problems)
    if problems:
        raise WorkflowError(problems)
    _place_lanes(diagram, max_height)
    _channels(diagram)
    try:
        diagram.routes = route_all(diagram, diagram.edges)
    except RouteError as err:
        raise WorkflowError(['Part %d ("%s"): %s' % (part.number, part.title, err)])
    return diagram


def mark_text(node):
    """What a start, stop or end says."""
    if node.type == "start":
        return language.t("starts_when") + node.title
    if node.type == "stop":
        return language.t("stops") + node.title
    title = language.t("to_part", title=node.title, n=node.to_part) if node.to_part else node.title
    return language.t("ends") + title


def describe(part, node_id):
    """Where an arrow leads, in words: "step 3", "the question ...", "ends (...)"."""
    node = part.by_id[node_id]
    if node.type == "step":
        return language.t("to_step", n=node.number)
    if node.type == "decision":
        return language.t("to_question", title=node.title)
    if node.type == "stop":
        return language.t("to_stop", title=node.title)
    if node.type == "end":
        return language.t("to_end", title=node.title)
    return language.t("to_start")


# ---------------------------------------------------------------- who sits where

def _attach(part):
    """The starts, stops and ends that are drawn as a flag on a box: {its id: the box's id}."""
    attached = {}
    for node in part.nodes:
        if node.type == "start" and not part.incoming(node.id):
            leaving = part.outgoing(node.id)
            host = part.by_id[leaving[0].target] if len(leaving) == 1 else None
            if host is not None and host.type in ("step", "decision") and host.lane == node.lane:
                attached[node.id] = host.id
        elif node.type in TERMINALS:
            arriving = part.incoming(node.id)
            host = part.by_id[arriving[0].source] if len(arriving) == 1 else None
            if host is not None and host.type == "step" and host.lane == node.lane:
                attached[node.id] = host.id
    return attached


def _place_side_exits(diagram):
    part = diagram.part
    taken = {}
    for node in part.nodes:
        if node.type not in TERMINALS or node.id not in diagram.placed:
            continue
        incoming = part.incoming(node.id)
        if len(incoming) != 1:
            continue
        decision = part.by_id[incoming[0].source]
        if decision.type != "decision" or decision.lane == node.lane or decision.index > node.index:
            continue
        here, there = diagram.placed[node.id], diagram.placed[decision.id]
        side = "top" if here.lane_index < there.lane_index else "bottom"
        if side in taken.setdefault(decision.id, set()):
            continue
        taken[decision.id].add(side)
        here.side_of = (decision.id, side)


def _place_columns(diagram):
    part = diagram.part
    beside = {}
    for node_id, placed in diagram.placed.items():
        if placed.side_of is not None:
            beside.setdefault(placed.side_of[0], []).append(node_id)

    def lanes_of(node_id):
        return [diagram.placed[i].lane_index for i in [node_id] + beside.get(node_id, [])]

    def straight(node_id, mine, taken):
        """True when every arrow between this node and the column's nodes can run straight up or down:
        no other node of the column stands between the two."""
        for edge in part.edges:
            other = edge.source if edge.target == node_id else edge.target if edge.source == node_id else None
            if other not in taken:
                continue
            low, high = sorted((taken[other], mine[0]))
            if any(low < lane < high for lane in list(taken.values()) + mine[1:]):
                return False
        return True

    columns, taken, before = [], {}, None       # taken: the open column's nodes -> their lanes
    for node in part.nodes:
        placed = diagram.placed.get(node.id)
        if placed is None or placed.side_of is not None:
            continue
        mine = lanes_of(node.id)
        follows = before is not None and any(e.source == before.node.id and e.target == node.id for e in part.edges)
        if not follows or not straight(node.id, mine, taken) or len(node.branches) > 2:
            clear = False        # three answers need three free sides: the arrow in must come from the left
        elif "pill" in (placed.shape, before.shape):
            clear = max(mine) < min(taken.values()) or min(mine) > max(taken.values())
        else:                       # a box shares a column only when the work passes straight down to it
            clear = min(mine) > max(taken.values())
        if not (columns and clear):
            columns.append(Column([]))
            taken = {}
        columns[-1].ids += [node.id] + beside.get(node.id, [])
        taken.update(zip([node.id] + beside.get(node.id, []), mine))
        before = placed

    gaps = [PAD_SIDE]
    font, size = theme.ANSWER
    for column in columns[:-1]:
        gap = COL_GAP
        for node_id in column.ids:      # room for an answer's pill before the line where arrows bend
            for label, _ in part.by_id[node_id].branches:
                gap = max(gap, 3.0 + theme.width(label, font, size) + 2 * ANSWER_PAD + 6.0 + CHANNEL)
        gaps.append(gap)
    gaps.append(PAD_SIDE)
    shares = [PILL_SHARE if all(diagram.placed[i].shape == "pill" for i in c.ids) else 1.0 for c in columns]
    room = diagram.width - LABEL_W - sum(gaps)
    box_w = room / sum(shares)
    if box_w < BOX_MIN:
        holds = int((diagram.width - LABEL_W - 2 * PAD_SIDE + COL_GAP) // (BOX_MIN + COL_GAP))
        raise WorkflowError(['Part %d ("%s") is too long for one page: it needs %d columns side by side and a '
                             'page holds about %d. Split it into two parts.'
                             % (part.number, part.title, len(columns), holds)])
    spare = max(room - BOX_MOST * sum(shares), 0.0) / len(gaps)
    box_w = min(box_w, BOX_MOST)
    x = LABEL_W
    for column, gap, share in zip(columns, gaps, shares):
        x += gap + spare
        column.x0, column.x1 = x, x + box_w * share
        for node_id in column.ids:
            placed = diagram.placed[node_id]
            placed.cx, placed.w = (column.x0 + column.x1) / 2.0, column.x1 - column.x0
        x = column.x1
    edges = [LABEL_W] + [c.x0 - CHANNEL for c in columns[1:]] + [diagram.width]
    for column, x0, x1 in zip(columns, edges, edges[1:]):
        column.cell = (x0, x1)
    diagram.columns = columns


def _place_lanes(diagram, max_height):
    """Every box of a lane sits on one line, so an arrow to the next box in the lane runs straight."""
    part = diagram.part
    reach = []          # per lane: how far its nodes reach above and below that line
    for index in range(len(part.lanes)):
        mine = [p for p in diagram.placed.values() if p.lane_index == index]
        reach.append((max([p.above for p in mine] or [0.0]), max([p.below for p in mine] or [0.0])))
    needs = [max(above + below + 2 * LANE_PAD, LANE_MIN) for above, below in reach]
    room = max_height - diagram.strip_h
    if sum(needs) > room:
        raise WorkflowError(['Part %d ("%s") is too tall for one page: its %d lanes need %d points and a page '
                             'holds %d. Shorten its longest titles and details, use fewer lanes, or split it '
                             'into two parts.' % (part.number, part.title, len(needs), sum(needs), room)])
    share = (room - sum(needs)) / len(needs)
    y, lines = 0.0, []
    for name, need, (above, below) in zip(part.lanes, needs, reach):
        height = min(need + share, max(need, LANE_MOST))
        diagram.lanes.append((name, y, y + height))
        lines.append(y + (height - above - below) / 2.0 + above)
        y += height
    for placed in diagram.placed.values():
        placed.cy = lines[placed.lane_index]
    diagram.bottom = y
    diagram.height = y + diagram.strip_h


def _channels(diagram):
    """The free lines where arrows may run: just before each column, and along the lanes."""
    xs = [column.x0 - CHANNEL for column in diagram.columns] + [diagram.columns[-1].x1 + CHANNEL]
    diagram.channel_xs = sorted(set(x for x in xs if diagram.left < x < diagram.width - 1.0))
    ys = []
    for _, y0, y1 in diagram.lanes:
        ys += [y0 + GUTTER, y1 - GUTTER, (y0 + y1) / 2.0]
    diagram.channel_ys = sorted(set(ys))


# ---------------------------------------------------------------- words

def _name_lanes(diagram, problems):
    """Wraps the lane names beside their lanes, all at one size: the largest at which every name fits."""
    part = diagram.part
    font, _, _ = theme.LANE_LABEL
    room = LABEL_W - 2 * LABEL_PAD
    for size in NAME_SIZES:
        lines = [wrap(name, font, size, room, NAME_LINES) for name in part.lanes]
        if all(found is not None for found in lines):
            break
    for name, found in zip(part.lanes, lines):
        if found is None:
            problems.append('Part %d ("%s"): the lane name "%s" does not fit beside its lane. Put a space '
                            'between its words, or use a shorter actor name.' % (part.number, part.title, name))
    diagram.lane_size = size
    diagram.lane_lines = [found or [] for found in lines]


def _size(placed, part, problems):
    node = placed.node
    where = 'Part %d ("%s"), node "%s"' % (part.number, part.title, node.id)
    for flag in placed.flags:
        flag_where = 'Part %d ("%s"), node "%s"' % (part.number, part.title, flag.node.id)
        _wrap_mark(flag, placed.w - DOT_ROOM, flag_where, problems)
    if placed.shape == "pill":
        _wrap_mark(placed.mark, placed.w - 2 * BOX_PAD_X - DOT_ROOM, where, problems)
        placed.h = placed.mark.height + 2 * PILL_PAD_Y
        return
    inner = placed.w - 2 * BOX_PAD_X
    font, size, lead = theme.STEP_TITLE
    placed.title_lines = wrap(node.title, font, size, inner, TITLE_LINES)
    if placed.title_lines is None:
        placed.title_lines = []
        problems.append('%s: the title does not fit its box in %d lines; shorten it to a few words (about %d '
                        'characters), or split the part so its boxes get wider.'
                        % (where, TITLE_LINES, _fits(inner, size, TITLE_LINES)))
        return
    height = BOX_PAD_TOP + lead * len(placed.title_lines) + BOX_PAD_BOTTOM
    if node.detail:
        dfont, dsize, dlead = theme.STEP_DETAIL
        placed.detail_lines = wrap(node.detail, dfont, dsize, inner, DETAIL_LINES)
        if placed.detail_lines is None:
            placed.detail_lines = []
            problems.append('%s: the detail does not fit its box in %d lines; keep it to about %d characters, or '
                            'split the part so its boxes get wider.'
                            % (where, DETAIL_LINES, _fits(inner, dsize, DETAIL_LINES)))
            return
        height += 2.0 + dlead * len(placed.detail_lines)
    placed.h = max(height, BOX_MIN_H)


def _wrap_mark(mark, room, where, problems):
    node = mark.node
    font, size, _ = theme.FLAG
    mark.title_lines = wrap(mark_text(node), font, size, room, MARK_LINES)
    if mark.title_lines is None:
        mark.title_lines = []
        problems.append('%s: the title is too long for its place on the board; keep it to about %d characters.'
                        % (where, _fits(room, size, MARK_LINES)))
    if node.detail and node.type != "start":
        dfont, dsize, _ = theme.STEP_DETAIL
        mark.detail_lines = wrap(node.detail, dfont, dsize, room, MARK_LINES)
        if mark.detail_lines is None:
            mark.detail_lines = []
            problems.append('%s: the detail is too long for its place on the board; keep it to about %d '
                            'characters.' % (where, _fits(room, dsize, MARK_LINES)))


def _fits(room, size, lines):
    return int(room / (size * 0.58) * lines)


def _fill_strip(diagram, pages, problems):
    """What comes out of each column, under the lanes."""
    part = diagram.part
    following = {}
    for position, node in enumerate(part.nodes):
        following[node.id] = part.nodes[position + 1].id if position + 1 < len(part.nodes) else None
    font, size, lead = theme.STRIP_TEXT
    tallest = 0.0
    for column in diagram.columns:
        room = column.cell[1] - column.cell[0] - 2 * STRIP_PAD - STRIP_NUMBER_W
        for node_id in sorted(column.ids, key=lambda i: diagram.placed[i].lane_index):
            node = part.by_id[node_id]
            number, texts = "", []
            if node.type == "step":
                number = str(node.number)
                if node.result:
                    texts.append(node.result)
                if node.next and node.next != following[node.id] and node.next not in diagram.attached:
                    texts.append(language.t("then", target=describe(part, node.next)))
            elif node.type == "decision":
                number = "?"
                texts = ["%s %s %s" % (label, language.t("leads_to"), describe(part, target))
                         for label, target in node.branches]
            for end in [node] + [flag.node for flag in diagram.placed[node_id].flags]:
                if end.type == "end" and end.to_part:
                    texts.append(language.t("continues", n=end.to_part, page=pages.get(end.to_part, "00")))
            lines = []
            for text in texts:
                wrapped = wrap(text, font, size, room, STRIP_LINES)
                lines = None if wrapped is None or lines is None else lines + wrapped
            if lines is None or len(lines) > STRIP_LINES:
                what = "where its answers lead" if node.type == "decision" else 'its "result"'
                problems.append('Part %d ("%s"), node "%s": %s does not fit under its column in %d lines. Keep it '
                                'to about %d characters, or split the part so its columns get wider.'
                                % (part.number, part.title, node.id, what, STRIP_LINES,
                                   _fits(room, size, STRIP_LINES)))
                lines = []
            if number or lines:
                column.entries.append((number, lines))
        height = sum(max(STRIP_ROW, lead * len(lines)) + STRIP_ENTRY_GAP for _, lines in column.entries)
        tallest = max(tallest, height - STRIP_ENTRY_GAP)
    diagram.strip_h = max(2 * STRIP_PAD + tallest, STRIP_MIN)
