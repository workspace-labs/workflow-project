"""The board is clean: every node in its lane, nothing overlapping, no arrow through a box, and no two
arrows touching or crossing (review finding F01).

Every geometric judgement here comes from tests/geometry_oracle.py, which never imports the tool, so a
broken collision check in the tool cannot also blind these tests (review finding F05).
"""

import json
import os
import unittest

import geometry_oracle as oracle
import support
from workflow_tool import layout, model, pages

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")


def lay_out_all(data):
    project = model.parse(data)
    where = pages.page_plan(project)
    return [layout.lay_out(part, pages.FRAME_W, pages.board_room(part, len(project.parts)), where)
            for part in project.parts]


def shapes(placed):
    """Everything drawn for one node, as plain boxes: its shape, and the flags above and below it."""
    found = [("shape", (placed.cx - placed.w / 2.0, placed.cy - placed.h / 2.0,
                        placed.cx + placed.w / 2.0, placed.cy + placed.h / 2.0))]
    for words in placed.label_rects:
        found.append(("words", (words.x0, words.y0, words.x1, words.y1)))
    return found


def side_points(placed):
    """The four points where an arrow may meet a node, worked out here from its size alone."""
    half_w, half_h = placed.w / 2.0, placed.h / 2.0
    return [(placed.cx, placed.cy - half_h), (placed.cx, placed.cy + half_h),
            (placed.cx - half_w, placed.cy), (placed.cx + half_w, placed.cy)]


class CleanDiagrams(unittest.TestCase):
    def each_diagram(self):
        for name in support.EXAMPLE_NAMES:
            for diagram in lay_out_all(support.example_data(name)):
                yield name, diagram
        for diagram in lay_out_all(support.two_loops()):
            yield "two-loops", diagram
        with open(os.path.join(FIXTURES, "access-request.json"), encoding="utf-8") as handle:
            for diagram in lay_out_all(json.load(handle)):
                yield "access-request", diagram

    def test_every_node_sits_inside_its_lane(self):
        for name, d in self.each_diagram():
            for node_id, p in d.placed.items():
                _, y0, y1 = d.lanes[p.lane_index]
                for _, box in shapes(p):
                    with self.subTest(example=name, part=d.part.number, node=node_id):
                        self.assertGreaterEqual(box[1], y0)
                        self.assertLessEqual(box[3], y1)
                        self.assertGreater(box[0], layout.LABEL_W)
                        self.assertLess(box[2], d.width)
            self.assertLessEqual(d.lanes[-1][2], d.bottom + 0.01)
            self.assertLess(d.bottom, d.height, "the strip sits under the lanes")

    def test_nothing_overlaps(self):
        for name, d in self.each_diagram():
            items = [(node_id, r) for node_id, p in d.placed.items() for _, r in shapes(p)]
            for i, (a_id, a) in enumerate(items):
                for b_id, b in items[i + 1:]:
                    if a_id == b_id:
                        continue
                    with self.subTest(example=name, part=d.part.number, pair=(a_id, b_id)):
                        self.assertFalse(oracle.boxes_overlap(a, b))

    def test_every_arrow_joins_its_two_nodes_at_their_edges(self):
        for name, d in self.each_diagram():
            for route in d.routes:
                source, target = d.placed[route.edge.source], d.placed[route.edge.target]
                starts, ends = side_points(source), side_points(target)
                with self.subTest(example=name, arrow=(route.edge.source, route.edge.target)):
                    self.assertIn(route.points[0], starts)
                    self.assertIn(route.points[-1], ends)
                    for a, b in zip(route.points, route.points[1:]):
                        self.assertTrue(a[0] == b[0] or a[1] == b[1], "every line is straight across or down")

    def test_every_connection_is_an_arrow_or_a_flag(self):
        """Nothing in the file goes missing: each connection is drawn as an arrow, unless one end of it
        is a start, stop or end written as a flag on the other end's box."""
        for name, d in self.each_diagram():
            drawn = set((r.edge.source, r.edge.target) for r in d.routes)
            for edge in d.part.edges:
                with self.subTest(example=name, part=d.part.number, arrow=(edge.source, edge.target)):
                    if (edge.source, edge.target) in drawn:
                        self.assertIn(edge.source, d.placed)
                        self.assertIn(edge.target, d.placed)
                    else:
                        flag, box = ((edge.source, edge.target) if edge.source not in d.placed
                                     else (edge.target, edge.source))
                        self.assertNotIn(flag, d.placed)
                        self.assertIn(flag, [f.node.id for f in d.placed[box].flags])

    def test_no_arrow_passes_through_a_box_or_its_words(self):
        for name, d in self.each_diagram():
            for route in d.routes:
                segments = list(zip(route.points, route.points[1:]))
                for node_id, p in d.placed.items():
                    for kind, rect in shapes(p):
                        for index, (a, b) in enumerate(segments):
                            if index == 0 and node_id == route.edge.source and kind == "shape":
                                continue
                            if index == len(segments) - 1 and node_id == route.edge.target and kind == "shape":
                                continue
                            with self.subTest(example=name, arrow=(route.edge.source, route.edge.target), node=node_id):
                                self.assertFalse(oracle.segment_enters_box(a, b, rect), "the arrow crosses %s" % node_id)

    def test_no_two_arrows_touch_or_cross(self):
        for name, d in self.each_diagram():
            meetings = oracle.arrow_meetings([r.points for r in d.routes])
            with self.subTest(example=name, part=d.part.number):
                self.assertEqual([(d.routes[i].edge.source + "->" + d.routes[i].edge.target,
                                   d.routes[j].edge.source + "->" + d.routes[j].edge.target) for i, j, _ in meetings], [])

    def test_the_independent_checks_are_themselves_right(self):
        """The reviewer's controls: a line through a box hits it; one above it does not."""
        self.assertTrue(oracle.controls_hold())

    def test_every_start_stop_and_end_is_written_and_has_its_room(self):
        from workflow_tool import theme
        lead = theme.FLAG[2]
        for name, d in self.each_diagram():
            flags = dict((f.node.id, (f, p)) for p in d.placed.values() for f in p.flags)
            for node in d.part.nodes:
                if node.type not in ("start", "stop", "end"):
                    continue
                with self.subTest(example=name, part=d.part.number, node=node.id):
                    if node.id in d.placed:
                        mark, room = d.placed[node.id].mark, d.placed[node.id].h
                    else:
                        mark, host = flags[node.id]
                        rect = [r for r in host.label_rects
                                if (r.y1 <= host.cy) == (node.type == "start")][0]
                        room = rect.y1 - rect.y0
                    self.assertTrue(mark.title_lines, "every start, stop and end is labelled")
                    self.assertGreaterEqual(room + 0.01, lead * len(mark.title_lines))

    def test_an_answer_never_covers_a_box(self):
        for name, d in self.each_diagram():
            for route in d.routes:
                if route.label_at is None:
                    continue
                pill = (route.label_at.x0, route.label_at.y0, route.label_at.x1, route.label_at.y1)
                for node_id, p in d.placed.items():
                    for _, rect in shapes(p):
                        with self.subTest(example=name, answer=route.edge.label, node=node_id):
                            self.assertFalse(oracle.boxes_overlap(pill, rect))

    def test_the_strip_names_every_step_once_under_its_own_column(self):
        for name, d in self.each_diagram():
            numbers = [number for column in d.columns for number, _ in column.entries if number.isdigit()]
            steps = [str(n.number) for n in d.part.nodes if n.type == "step"]
            with self.subTest(example=name, part=d.part.number):
                self.assertEqual(sorted(numbers, key=int), steps)
            for column in d.columns:
                for node_id in column.ids:
                    p = d.placed[node_id]
                    self.assertGreaterEqual(p.cx - p.w / 2.0, column.cell[0])
                    self.assertLessEqual(p.cx + p.w / 2.0, column.cell[1])

    def test_blue_arrows_are_the_normal_path(self):
        for name, d in self.each_diagram():
            for route in d.routes:
                self.assertEqual(route.main, route.edge.main)


class Refusals(unittest.TestCase):
    def refused(self, data):
        with self.assertRaises(model.WorkflowError) as caught:
            lay_out_all(data)
        return " ".join(caught.exception.problems)

    def test_a_part_too_long_for_a_page_is_refused(self):
        data = support.small_workflow()
        items = support.nodes(data)
        extra = [{"id": "s%d" % i, "type": "step", "lane": "Office" if i % 2 else "Customer",
                  "title": "Step number %d" % i, "detail": "one more thing"} for i in range(16)]
        items[2:2] = extra
        message = self.refused(data)
        self.assertIn("too long for one page", message)
        self.assertIn("Split it into two parts", message)

    def test_a_title_too_long_for_its_box_is_refused(self):
        data = support.small_workflow()
        support.nodes(data)[1]["title"] = "Extraordinarily comprehensive interdepartmental documentation"
        for i in range(4):          # many boxes side by side, so each one is narrow
            support.nodes(data).insert(2 + i, {"id": "x%d" % i, "type": "step", "lane": "Customer", "title": "Short"})
        self.assertIn("does not fit its box in 5 lines", self.refused(data))

    def test_a_result_too_long_for_the_strip_is_refused(self):
        data = support.small_workflow()
        support.nodes(data)[1]["result"] = "W" * 40
        self.assertIn('its "result" does not fit under its column', self.refused(data))

    def test_a_part_too_tall_for_a_page_is_refused(self):
        data = support.small_workflow()
        names = ["B", "C", "D"]
        data["project"]["actors"] += [{"name": n, "role": ""} for n in names]
        data["parts"][0]["lanes"] += names
        for i, lane in enumerate(["Customer", "Office"] + names):
            support.nodes(data).insert(2 + i, {
                "id": "x%d" % i, "type": "step", "lane": lane,
                "title": "A step whose title is long enough to need several lines in its box",
                "detail": "and a detail that is also long enough to need several lines of its own"})
        message = self.refused(data)
        self.assertIn("too tall for one page", message)
        self.assertIn("use fewer lanes", message)

    def test_an_arrow_that_cannot_fit_is_refused(self):
        data = support.small_workflow()
        data["parts"][0]["nodes"] = [
            {"id": "start", "type": "start", "lane": "Customer", "title": "Begins"},
            {"id": "d1", "type": "decision", "lane": "Customer", "title": "Which?",
             "branches": [{"label": "A", "to": "a"}, {"label": "B", "to": "b"}, {"label": "C", "to": "hub"}]},
            {"id": "a", "type": "step", "lane": "Office", "title": "Path A"},
            {"id": "d2", "type": "decision", "lane": "Office", "title": "Again?",
             "branches": [{"label": "Yes", "to": "hub"}, {"label": "No", "to": "c"}]},
            {"id": "b", "type": "step", "lane": "Customer", "title": "Path B", "next": "hub"},
            {"id": "c", "type": "step", "lane": "Customer", "title": "Path C", "next": "hub"},
            {"id": "hub", "type": "step", "lane": "Office", "title": "Everything meets"},
            {"id": "end", "type": "end", "lane": "Customer", "title": "Done"},
        ]
        self.assertIn("cannot be drawn without crossing a box", self.refused(data))


if __name__ == "__main__":
    unittest.main()
