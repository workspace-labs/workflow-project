"""Place systems by dependency, and fit each send and its words between the boxes.

Coordinates are relative to the diagram's top left. The same plan draws in either direction.
"""

from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache
from itertools import chain

from . import theme
from .layout import wrap
from .model import WorkflowError
from .routing import Rect

PAD = 10.0
DETAIL_GAP = 4.0
PORT_GAP = 28.0            # leaves room for words between arrows sharing a box's side
CLEAR = 5.0                # includes the stroke, rounded bends and arrowhead wings
LABEL_STYLE = theme.FLAG


@dataclass
class SystemBox:
    name: str
    rect: Rect
    name_lines: list
    detail_lines: list


@dataclass
class SystemArrow:
    source: str
    target: str
    what: str
    points: list
    label_rect: Rect
    label_lines: list


@dataclass
class SystemsDiagram:
    boxes: list
    arrows: list


def _refuse(reason):
    raise WorkflowError([reason + " Use fewer systems or split the workflow."])


def _columns(systems, parents):
    """The rightmost sender determines a receiver's column, regardless of input order."""
    @lru_cache(maxsize=None)
    def rank(name):
        return 1 + max((rank(sender) for sender in parents[name]), default=-1)

    columns = [[] for _ in range(max(rank(system.name) for system in systems) + 1)]
    for system in systems:
        columns[rank(system.name)].append(system)
    # Put receivers in the same vertical order as their senders where possible.
    positions = {}
    for column in columns:
        if positions:
            column.sort(key=lambda system: sum(positions[p] for p in parents[system.name])
                        / len(parents[system.name]))
        for i, system in enumerate(column):
            positions[system.name] = (i + 0.5) / len(column)
    return columns


def _span(text, style):
    font, size, _ = style
    longest = max((theme.width(w, font, size) for w in text.split()), default=0.0)
    return longest, theme.width(text, font, size)


def _column_sizes(columns, width):
    """Allocate each column and gutter its unbreakable words first, then share spare space."""
    spans = []
    for index, column in enumerate(columns):
        content = [_span(text, style) for system in column for text, style in
                   [(system.name, theme.STEP_TITLE), (system.detail, theme.STEP_DETAIL)]]
        minimum = max(64.0, max(word for word, _ in content) + 2 * PAD + 1)
        desired = max(125.0, min(182.0, max(full for _, full in content) + 2 * PAD + 1))
        spans.append((minimum, max(minimum, desired)))
        if index + 1 < len(columns):
            targets = {s.name for s in columns[index + 1]}
            labels = [_span(send.what, LABEL_STYLE) for system in column for send in system.sends
                      if send.to in targets]
            minimum = max(36.0, max((word for word, _ in labels), default=0) + 20.0)
            desired = max(90.0, max((full for _, full in labels), default=0) + 28.0)
            spans.append((minimum, max(minimum, desired)))
    room = width - 2.0 - sum(low for low, _ in spans)
    if room < 0:
        _refuse("The system boxes and the words on their arrows are too wide for one page. Shorten their words.")
    growth = sum(high - low for low, high in spans)
    share = min(1.0, room / growth) if growth else 0.0
    return [low + share * (high - low) for low, high in spans]


def _place_boxes(columns, width, height, parents):
    spans = _column_sizes(columns, width)
    x = (width - sum(spans)) / 2.0
    boxes = []
    for index, column in enumerate(columns):
        w = spans[index * 2]
        rows = []
        for system in column:
            names = wrap(system.name, *theme.STEP_TITLE[:2], w - 2 * PAD, 3)
            details = wrap(system.detail, *theme.STEP_DETAIL[:2], w - 2 * PAD, 4)
            if names is None or details is None:
                _refuse('The words in the "%s" system box need shorter lines.' % system.name)
            h = len(names) * theme.STEP_TITLE[2] + len(details) * theme.STEP_DETAIL[2]
            h += 2 * PAD + (DETAIL_GAP if details else 0)
            ports = max(len(parents[system.name]), len(system.sends))
            rows.append((system.name, names, details, max(44.0, h, 20 + (ports - 1) * PORT_GAP)))
        space = height - 2 - sum(h for _, _, _, h in rows)
        if space < (len(rows) - 1) * 10.0:
            _refuse("These system boxes and their arrows are too tall for one page.")
        gap = min(55.0, space / max(1, len(rows) - 1))
        y = (space - gap * (len(rows) - 1)) / 2.0 + 1
        for name, names, details, h in rows:
            boxes.append(SystemBox(name, Rect(x, y, x + w, y + h), names, details))
            y += h + gap
        if index + 1 < len(columns):
            x += w + spans[index * 2 + 1]
    return boxes


def _ports(edges, boxes, outgoing):
    """Order each side's ports by the vertical positions of the opposite boxes."""
    groups = defaultdict(list)
    side, other = (0, 1) if outgoing else (1, 0)
    for i, edge in enumerate(edges):
        groups[edge[side]].append(i)
    result = {}
    for name, indexes in groups.items():
        # On a shared row, put the longer send above the shorter one at both ends.
        # It can then pass over intermediate boxes without crossing their local sends.
        def port_order(i):
            opposite = boxes[edges[i][other]]
            return _middle_y(opposite), -abs(opposite.x0 - boxes[name].x0)

        indexes.sort(key=port_order)
        rect = boxes[name]
        for slot, i in enumerate(indexes):
            y = _middle_y(rect) + (slot - (len(indexes) - 1) / 2.0) * PORT_GAP
            result[i] = (rect.x1 if outgoing else rect.x0, round(y, 6))
    return result


def _middle_y(rect):
    return (rect.y0 + rect.y1) / 2.0


def _paths(start, end, boxes, height):
    """Try straight or two bends, then shelves above and below intervening boxes."""
    x0, y0 = start
    x1, y1 = end
    if y0 == y1:
        yield [start, end]
    else:
        for fraction in (0.5, 0.3, 0.7, 0.15, 0.85):
            x = x0 + 10.0 + fraction * (x1 - x0 - 20.0)
            yield [start, (x, y0), (x, y1), end]
    between = [r for r in boxes.values() if r.x0 > x0 and r.x1 < x1]
    shelves = {v for r in between for v in (r.y0 - 25, r.y1 + 25)}
    for y in sorted(shelves, key=lambda v: (abs(v - y0) + abs(v - y1), v)):
        if not 5 < y < height - 5 or y in (y0, y1):
            continue
        for stub in (13.0, 25.0, 37.0):
            if x1 - x0 > 2 * stub + 10.0:
                yield [start, (x0 + stub, y0), (x0 + stub, y), (x1 - stub, y),
                       (x1 - stub, y1), end]


def _stroke(a, b):
    return Rect(min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])).inflate(CLEAR)


def _outside_paths(source, target, boxes, width, height):
    """Come around the columns when opposing sends cannot share the space between them."""
    a, b = boxes[source], boxes[target]
    ax, bx = (a.x0 + a.x1) / 2, (b.x0 + b.x1) / 2
    # A shelf outside the rows leaves the words and the arrows in the gutter undisturbed.
    across = [r for r in boxes.values() if a.x0 <= r.x0 <= b.x0]
    for ay, by, shelf in ((a.y0, b.y0, min(r.y0 for r in across) - 24.0),
                          (a.y1, b.y1, max(r.y1 for r in across) + 24.0)):
        if not CLEAR < shelf < height - CLEAR:
            continue
        yield [(ax, ay), (ax, shelf), (bx, shelf), (bx, by)]
        left, right = a.x0 - 24.0, b.x1 + 24.0
        if left > CLEAR:
            yield [(a.x0, _middle_y(a)), (left, _middle_y(a)), (left, shelf), (bx, shelf), (bx, by)]
        if right < width - CLEAR:
            yield [(ax, ay), (ax, shelf), (right, shelf), (right, _middle_y(b)), (b.x1, _middle_y(b))]


def _blocker(strokes, source, target, boxes, used):
    """Return the name of a box or the two names of a send that the proposed path hits."""
    for index, rail in enumerate(strokes):
        for name, box in boxes.items():
            if (index == 0 and name == source) or (index == len(strokes) - 1 and name == target):
                continue
            if rail.overlaps(box):
                return (name,)
        for connection, earlier in used.items():
            if any(rail.overlaps(obstacle) for obstacle in earlier):
                return connection
    return None


def _label_sites(points, what):
    """Place unboxed words beside a horizontal or vertical stretch of their own arrow."""
    font, size, lead = LABEL_STYLE
    segments = sorted(zip(points, points[1:]),
                      key=lambda ab: -abs(ab[1][0] - ab[0][0]))  # longest horizontal stretch first
    for (x0, y0), (x1, y1) in segments:
        horizontal = y0 == y1
        available = abs(x1 - x0) - 12.0 if horizontal else 92.0
        tried = set()
        for room in (available, available * 0.66, available * 0.42):
            lines = wrap(what, font, size, room, 3)
            if not lines or tuple(lines) in tried:
                continue
            tried.add(tuple(lines))
            w = max(theme.width(line, font, size) for line in lines) + 4
            h = lead * len(lines) + 4
            for t in (0.5, 0.25, 0.75, 0.125, 0.875):
                mid_x, mid_y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
                for side in (-1, 1):
                    cx = mid_x if horizontal else mid_x + side * (w / 2 + CLEAR + 1)
                    cy = mid_y + side * (h / 2 + CLEAR + 1) if horizontal else mid_y
                    yield Rect(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2), lines


def _route_all(edges, starts, ends, boxes, width, height, order, outside):
    # Reserve every line before placing any words. A label beside one line must
    # leave room for the next arrow, especially where several leave one box.
    used, paths = {}, {}
    for i in order:
        source, target, _ = edges[i]
        candidates = _paths(starts[i], ends[i], boxes, height)
        if outside:
            candidates = chain(candidates, _outside_paths(source, target, boxes, width, height))
        blockers = []
        for points in candidates:
            strokes = [_stroke(a, b) for a, b in zip(points, points[1:])]
            blocker = _blocker(strokes, source, target, boxes, used)
            if blocker is None:
                paths[i] = points
                used[source, target] = strokes
                break
            blockers.append(blocker)
        else:
            obstacle = next((b for b in blockers if len(b) == 2 and b[0] != source), blockers[0])
            other = 'the "%s" box' % obstacle if len(obstacle) == 1 else 'the arrow from "%s" to "%s"' % obstacle
            return None, ('No clear path was found for the arrow from "%s" to "%s". One route would cross '
                          'or pass too close to %s. Split these connections into separate workflows.'
                          % (source, target, other))

    obstacles = list(boxes.values()) + [rail for rails in used.values() for rail in rails]
    arrows = []
    for i in order:
        source, target, what = edges[i]
        for rect, lines in _label_sites(paths[i], what):
            if rect.x0 < 1 or rect.x1 > width - 1 or rect.y0 < 1 or rect.y1 > height - 1:
                continue
            if not any(rect.overlaps(other) for other in obstacles):
                arrows.append(SystemArrow(source, target, what, paths[i], rect, lines))
                obstacles.append(rect.inflate(1))
                break
        else:
            return None, ('The words "%s" have no clear space beside the arrow from "%s" to "%s". '
                          'Shorten the "what" text or split these connections into separate workflows.'
                          % (what, source, target))
    return arrows, None


def lay_out(systems, width, height):
    """Return one clean diagram for the validated systems, or raise a plain WorkflowError."""
    parents = defaultdict(list)
    edges = []
    for system in systems:
        for send in system.sends:
            edges.append((system.name, send.to, send.what))
            parents[send.to].append(system.name)
    boxes = _place_boxes(_columns(systems, parents), width, height, parents)
    by_name = {box.name: box.rect for box in boxes}
    starts = _ports(edges, by_name, outgoing=True)
    ends = _ports(edges, by_name, outgoing=False)
    # Reserve short routes first, leaving the outer channels for longer sends.
    order = sorted(range(len(edges)), key=lambda i: (ends[i][0] - starts[i][0], -abs(ends[i][1] - starts[i][1])))
    for outside in (False, True):
        for attempt in (order, list(reversed(order))):
            arrows, problem = _route_all(edges, starts, ends, by_name, width, height, attempt, outside)
            if arrows is not None:
                return SystemsDiagram(boxes, arrows)
    raise WorkflowError([problem])
