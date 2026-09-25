"""Independent geometry for the tests.

Written separately from the tool's routing code on purpose (review finding F05): if the tool's own
collision check breaks, these must not break with it. Nothing here imports the drawing tool.
Coordinates are points, y grows downward, boxes are (x0, y0, x1, y1).
"""

EPS = 1e-9


def segment_enters_box(p, q, box):
    """True when a real stretch of segment p-q lies strictly inside box (Liang-Barsky clipping).

    Touching the border, running along it, or ending on it is not entering."""
    x0, y0, x1, y1 = box
    dx, dy = q[0] - p[0], q[1] - p[1]
    t_in, t_out = 0.0, 1.0
    for pk, qk in ((-dx, p[0] - x0), (dx, x1 - p[0]), (-dy, p[1] - y0), (dy, y1 - p[1])):
        if abs(pk) < EPS:
            if qk <= EPS:
                return False
            continue
        t = qk / pk
        if pk < 0:
            t_in = max(t_in, t)
        else:
            t_out = min(t_out, t)
        if t_in >= t_out:
            return False
    length = abs(dx) + abs(dy)
    return (t_out - t_in) * length > 0.01


def segments_meet(a, b, c, d):
    """True when segment a-b and segment c-d touch or cross anywhere, including overlapping collinearly."""
    def side(p, q, r):
        value = (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
        return 0 if abs(value) < EPS else (1 if value > 0 else -1)

    def within(p, q, r):
        return (min(p[0], q[0]) - EPS <= r[0] <= max(p[0], q[0]) + EPS and
                min(p[1], q[1]) - EPS <= r[1] <= max(p[1], q[1]) + EPS)

    s1, s2, s3, s4 = side(a, b, c), side(a, b, d), side(c, d, a), side(c, d, b)
    if s1 * s2 < 0 and s3 * s4 < 0:
        return True
    return ((s1 == 0 and within(a, b, c)) or (s2 == 0 and within(a, b, d)) or
            (s3 == 0 and within(c, d, a)) or (s4 == 0 and within(c, d, b)))


def boxes_overlap(a, b):
    """True when two boxes share any area (touching edges do not count)."""
    return min(a[2], b[2]) - max(a[0], b[0]) > EPS and min(a[3], b[3]) - max(a[1], b[1]) > EPS


def arrow_meetings(routes):
    """Every pair of different arrows whose lines touch or cross: [(first, second, point-ish), ...]."""
    found = []
    lines = [(i, a, b) for i, points in enumerate(routes) for a, b in zip(points, points[1:])]
    for n, (i, a, b) in enumerate(lines):
        for j, c, d in lines[n + 1:]:
            if i != j and segments_meet(a, b, c, d):
                found.append((i, j, (a, b, c, d)))
    return found


def controls_hold():
    """The reviewer's known controls: a segment through a box must hit it, one above it must not."""
    box = (0.0, 0.0, 10.0, 10.0)
    return (segment_enters_box((-1.0, 5.0), (11.0, 5.0), box) and
            not segment_enters_box((-1.0, 20.0), (11.0, 20.0), box) and
            segments_meet((0.0, 0.0), (10.0, 0.0), (5.0, -5.0), (5.0, 5.0)) and
            not segments_meet((0.0, 0.0), (10.0, 0.0), (0.0, 3.0), (10.0, 3.0)))
