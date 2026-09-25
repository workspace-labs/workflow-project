"""Draws each arrow as right-angled lines that go around the boxes, never through them.

For every arrow, routes with 0 to 4 bends are tried between the free sides of its two nodes. A
route is kept only if it touches no other node and no label, and comes no closer than ARROW_GAP to
any earlier arrow: arrows never touch or cross. The cheapest kept route wins (fewest bends, then
shortest). When no clean route exists the part is refused, because a messy diagram is worse than none.

Coordinates are points from the diagram's top-left corner; y grows downward.
"""

from . import theme

STUB_OUT = 7.0        # an arrow leaves its node straight for at least this long
STUB_IN = 8.0         # and arrives straight for at least this long, so the arrowhead shows
CLEARANCE = 3.0       # how close a line may pass to a box
ARROW_GAP = 3.0       # two different arrows never touch, cross, or run closer than this
SIDES = {"top": (0, -1), "bottom": (0, 1), "left": (-1, 0), "right": (1, 0)}

# What a route costs. A decision's sides belong to its answers, so an arrow entering one from the
# side costs more than an extra bend; long detours around the diagram cost more than a bend too.
# A route that touches or crosses another arrow is never allowed at any cost (review finding F01).
BEND = 30.0
PER_POINT = 0.12
DECISION_SIDE_ENTRY = 45.0


class Rect(object):
    def __init__(self, x0, y0, x1, y1):
        self.x0, self.y0, self.x1, self.y1 = x0, y0, x1, y1

    def inflate(self, d):
        return Rect(self.x0 - d, self.y0 - d, self.x1 + d, self.y1 + d)

    def overlaps(self, other):
        return self.x0 < other.x1 and other.x0 < self.x1 and self.y0 < other.y1 and other.y0 < self.y1

    def hit_by(self, a, b):
        """True when the straight line a-b (horizontal or vertical) passes through this rectangle."""
        if a[0] == b[0]:
            low, high = min(a[1], b[1]), max(a[1], b[1])
            return self.x0 < a[0] < self.x1 and low < self.y1 and self.y0 < high
        low, high = min(a[0], b[0]), max(a[0], b[0])
        return self.y0 < a[1] < self.y1 and low < self.x1 and self.x0 < high


class RouteError(Exception):
    pass


class Routed(object):
    """One finished arrow."""

    def __init__(self, edge, points, label_at=None):
        self.edge = edge
        self.points = points       # [(x, y), ...] from the source's side to the target's side
        self.label_at = label_at   # (x, y, "start" | "end") for a decision's answer, or None
        self.main = edge.main


def port(placed, side):
    """Where an arrow meets a node on the given side."""
    if placed.shape == "circle":
        dx, dy = SIDES[side]
        return (placed.cx + dx * placed.r, placed.cy + dy * placed.r)
    half_w, half_h = placed.w / 2.0, placed.h / 2.0
    dx, dy = SIDES[side]
    return (placed.cx + dx * half_w, placed.cy + dy * half_h)


class _Stuck(Exception):
    def __init__(self, edge):
        Exception.__init__(self)
        self.edge = edge


def route_all(diagram, edges):
    """Routes every edge of one part. Returns [Routed]; raises RouteError naming the arrow that cannot fit.

    Arrows are routed one by one, and each takes the sides of its nodes it uses. When one gets stuck
    because earlier arrows took the sides it needed, it is moved to the front and all are routed again.
    """
    def is_side_exit(edge):
        target = diagram.placed[edge.target]
        return target.side_of is not None and target.side_of[0] == edge.source

    def key(edge):
        return (0 if is_side_exit(edge) else 1, 0 if edge.main else 1,
                diagram.placed[edge.source].node.index, edge.branch or 0)

    order = sorted(edges, key=key)
    first_free = sum(1 for edge in order if is_side_exit(edge))
    stuck_edge = None
    for _ in range(len(order) + 1):
        try:
            return _route_in_order(diagram, order)
        except _Stuck as stuck:
            stuck_edge = stuck.edge
            if order.index(stuck_edge) <= first_free:
                break
            order.remove(stuck_edge)
            order.insert(first_free, stuck_edge)
    raise RouteError('the arrow from "%s" to "%s" cannot be drawn without crossing a box. List the nodes in the '
                     'order they happen, move a step to another lane, or split the part.'
                     % (stuck_edge.source, stuck_edge.target))


def _route_in_order(diagram, order):
    obstacles = {}
    for node_id, placed in diagram.placed.items():
        obstacles[node_id] = placed.rect.inflate(CLEARANCE)
        if placed.label_rect is not None:
            obstacles["label:" + node_id] = placed.label_rect.inflate(1.5)
    used = dict((node_id, set()) for node_id in diagram.placed)
    segments = []          # (a, b) of every arrow drawn so far
    routed = []
    for edge in order:
        best = _best_route(diagram, edge, obstacles, used, segments)
        if best is None:
            raise _Stuck(edge)
        points, exit_side, entry_side = best
        used[edge.source].add(exit_side)
        used[edge.target].add(entry_side)
        for a, b in zip(points, points[1:]):
            segments.append((a, b))
        label_at = None
        if edge.label:
            label_at, label_rect = _place_label(edge.label, points, exit_side, obstacles, segments)
            obstacles["answer:%s:%s" % (edge.source, edge.branch)] = label_rect
        routed.append(Routed(edge, points, label_at))
    return routed


# ---------------------------------------------------------------- choosing a route

def _best_route(diagram, edge, obstacles, used, segments):
    source = diagram.placed[edge.source]
    target = diagram.placed[edge.target]
    if target.side_of is not None and target.side_of[0] == edge.source:
        exits = [target.side_of[1]]
        entries = ["right" if target.side_of[1] == "left" else "left"]
    else:
        exits = [s for s in _exit_sides(source, edge, target) if s not in used[edge.source]]
        entries = [s for s in _entry_sides(target, source) if s not in used[edge.target]]
    best = None          # (cost, points, exit side, entry side)
    for bends in range(5):
        for exit_side in exits:
            start = port(source, exit_side)
            out = SIDES[exit_side]
            for entry_side in entries:
                end = port(target, entry_side)
                inward = tuple(-v for v in SIDES[entry_side])
                for points in _shapes(diagram, start, out, end, inward, bends):
                    scored = _score(points, out, inward, edge, source, target, exit_side, entry_side,
                                    obstacles, segments, diagram)
                    if scored is not None and (best is None or scored[0] < best[0]):
                        best = (scored[0], scored[1], exit_side, entry_side)
        # Every bend costs BEND, so a route with one more bend can no longer win once the best
        # cost is at or below that floor.
        if best is not None and best[0] <= BEND * (bends + 1):
            break
    if best is None:
        return None
    return best[1], best[2], best[3]


def _exit_sides(source, edge, target):
    if source.node.type == "decision":
        toward = "left" if target.cx < source.cx else "right"
        away = "right" if toward == "left" else "left"
        if edge.branch == 0:
            return ["bottom", toward, away]
        return [toward, "bottom", away]
    return ["bottom", "right", "left"]


def _entry_sides(target, source):
    toward = "left" if source.cx < target.cx else "right"
    away = "right" if toward == "left" else "left"
    return ["top", toward, away]


def _shapes(diagram, a, out, b, inward, bends):
    """Candidate paths with this many bends from a (leaving along `out`) to b (arriving along `inward`)."""
    ax, ay = a
    bx, by = b
    rows = sorted(set(diagram.channel_ys + [ay + out[1] * 11.0, by - inward[1] * 11.0]))
    cols = diagram.channel_xs
    vertical_out, vertical_in = out[0] == 0, inward[0] == 0
    if bends == 0:
        yield [a, b]
    elif bends == 1:
        if vertical_out and not vertical_in:
            yield [a, (ax, by), b]
        if not vertical_out and vertical_in:
            yield [a, (bx, ay), b]
    elif bends == 2:
        if vertical_out and vertical_in:
            for y in rows:
                yield [a, (ax, y), (bx, y), b]
        if not vertical_out and not vertical_in:
            for x in cols:
                yield [a, (x, ay), (x, by), b]
    elif bends == 3:
        if vertical_out and not vertical_in:
            for y in rows:
                for x in cols:
                    yield [a, (ax, y), (x, y), (x, by), b]
        if not vertical_out and vertical_in:
            for x in cols:
                for y in rows:
                    yield [a, (x, ay), (x, y), (bx, y), b]
    elif bends == 4 and vertical_out and vertical_in:
        for y1 in rows:
            for x in cols:
                for y2 in rows:
                    yield [a, (ax, y1), (x, y1), (x, y2), (bx, y2), b]


def _score(points, out, inward, edge, source, target, exit_side, entry_side, obstacles, segments, diagram):
    points = _simplify(points)
    if len(points) < 2:
        return None
    first, last = _direction(points[0], points[1]), _direction(points[-2], points[-1])
    if first != out or last != inward:
        return None
    if _length(points[0], points[1]) < STUB_OUT or _length(points[-2], points[-1]) < STUB_IN:
        return None
    for x, y in points:
        if not (1.0 <= x <= diagram.width - 1.0 and diagram.top <= y <= diagram.height - 1.0):
            return None
    count = len(points) - 1
    for index, (a, b) in enumerate(zip(points, points[1:])):
        for key, rect in obstacles.items():
            if index == 0 and key == edge.source:
                continue
            if index == count - 1 and key == edge.target:
                continue
            if rect.hit_by(a, b):
                return None
    for a, b in zip(points, points[1:]):
        for c, d in segments:
            if _meets(a, b, c, d):
                return None
    bends = count - 1
    length = sum(_length(p, q) for p, q in zip(points, points[1:]))
    cost = bends * BEND + length * PER_POINT
    if source.node.type == "decision" and exit_side == "bottom" and edge.branch not in (None, 0):
        cost += 10.0
    if target.node.type == "decision" and entry_side != "top":
        cost += DECISION_SIDE_ENTRY
    return cost, points


def _simplify(points):
    cleaned = [points[0]]
    for point in points[1:]:
        if abs(point[0] - cleaned[-1][0]) < 0.01 and abs(point[1] - cleaned[-1][1]) < 0.01:
            continue
        cleaned.append(point)
    changed = True
    while changed and len(cleaned) > 2:
        changed = False
        for i in range(1, len(cleaned) - 1):
            a, b, c = cleaned[i - 1], cleaned[i], cleaned[i + 1]
            if (a[0] == b[0] == c[0]) or (a[1] == b[1] == c[1]):
                if _direction(a, b) == _direction(b, c):
                    del cleaned[i]
                    changed = True
                    break
                return []          # the path doubles back on itself
    for a, b in zip(cleaned, cleaned[1:]):
        if a[0] != b[0] and a[1] != b[1]:
            return []              # not a right-angled path
    return cleaned


def _direction(a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    return ((dx > 0) - (dx < 0), (dy > 0) - (dy < 0))


def _length(a, b):
    return abs(b[0] - a[0]) + abs(b[1] - a[1])


def _meets(a, b, c, d):
    """True when two right-angled lines come within ARROW_GAP of each other: touching, crossing,
    or running alongside. Both are treated as thin boxes grown by the gap, which also catches a line
    that stops just short of another."""
    gap = ARROW_GAP
    return (min(a[0], b[0]) <= max(c[0], d[0]) + gap and min(c[0], d[0]) - gap <= max(a[0], b[0]) and
            min(a[1], b[1]) <= max(c[1], d[1]) + gap and min(c[1], d[1]) - gap <= max(a[1], b[1]))


# ---------------------------------------------------------------- a decision's answer label

def _place_label(text, points, exit_side, obstacles, segments):
    font, size = theme.BRANCH_LABEL
    w, h = theme.width(text, font, size), size * 0.8
    x, y = points[0]
    if exit_side == "bottom":
        options = [(x + 4, y + 10, "start"), (x - 4, y + 10, "end")]
    else:
        sign = -1 if exit_side == "left" else 1
        anchor = "end" if sign < 0 else "start"
        options = [(x + sign * 5, y - 4, anchor), (x + sign * 5, y + 10, anchor)]
    best = None
    for lx, ly, anchor in options:
        x0 = lx - w if anchor == "end" else lx
        rect = Rect(x0 - 1, ly - h - 1, x0 + w + 1, ly + 2)
        clashes = sum(1 for r in obstacles.values() if r.overlaps(rect))
        clashes += sum(1 for a, b in segments if rect.hit_by(a, b))
        if best is None or clashes < best[0]:
            best = (clashes, (lx, ly, anchor), rect)
    return best[1], best[2]
