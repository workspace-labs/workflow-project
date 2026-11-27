"""Judge the placed systems with independent line/rectangle geometry."""

import copy
import json
import unittest
from itertools import combinations, permutations
from pathlib import Path

import geometry_oracle as oracle
import support
from workflow_tool import language, model, systems_layout


# Space below the heading on the landscape A4 systems page, in points.
WIDTH, HEIGHT = 775.8898, 432.2756


def arabic_fixture():
    return json.loads((Path(__file__).parent / "fixtures" / "systems-ar.json").read_text(encoding="utf-8"))


def coordinates(rect):
    return rect.x0, rect.y0, rect.x1, rect.y1


def layout_problems(diagram, width=WIDTH, height=HEIGHT):
    """Do not use Rect.overlaps, Rect.hit_by or the planner's clearance helpers here."""
    shapes = [(b.name, coordinates(b.rect)) for b in diagram.boxes]
    shapes += [(a.what, coordinates(a.label_rect)) for a in diagram.arrows]
    problems = []
    for name, (x0, y0, x1, y1) in shapes:
        if not (0 <= x0 < x1 <= width and 0 <= y0 < y1 <= height):
            problems.append("%s outside page" % name)
    for (a, rect_a), (b, rect_b) in combinations(shapes, 2):
        if oracle.boxes_overlap(rect_a, rect_b):
            problems.append("%s overlaps %s" % (a, b))
    for arrow in diagram.arrows:
        for p, q in zip(arrow.points, arrow.points[1:]):
            if not all(0 <= x <= width and 0 <= y <= height for x, y in (p, q)):
                problems.append("%s leaves page" % arrow.what)
            for name, rect in shapes:
                if oracle.segment_enters_box(p, q, rect):
                    problems.append("%s crosses %s" % (arrow.what, name))
    for i, j, _ in oracle.arrow_meetings([arrow.points for arrow in diagram.arrows]):
        problems.append("%s meets %s" % (diagram.arrows[i].what, diagram.arrows[j].what))
    return problems


def joining_workflow():
    # Two sources, a fork and a merge, deliberately out of dependency order.
    data = support.small_workflow()
    data["project"]["systems"] = [
        {"name": "Archive"},
        {"name": "Intake", "sends": [{"to": "Archive", "what": "Copy"}, {"to": "Desk", "what": "Case"}]},
        {"name": "Desk"},
        {"name": "Import", "sends": [{"to": "Desk", "what": "File"}]},
    ]
    return data


class SystemsGeometry(unittest.TestCase):
    def test_every_box_and_send_is_present_in_a_clean_layout(self):
        self.addCleanup(language.use, language.DEFAULT)
        for data in (support.example_data("shop-orders"), arabic_fixture(), joining_workflow()):
            project = model.parse(data)
            language.use(project.language)
            with self.subTest(example=project.name):
                diagram = systems_layout.lay_out(project.systems, WIDTH, HEIGHT)
                expected = data["project"]["systems"]
                boxes = {box.name: box.rect for box in diagram.boxes}
                self.assertCountEqual([b.name for b in diagram.boxes], [s["name"] for s in expected])
                self.assertCountEqual([(a.source, a.target, a.what) for a in diagram.arrows],
                                      [(s["name"], send["to"], send["what"]) for s in expected
                                       for send in s.get("sends", [])])
                self.assertEqual(layout_problems(diagram, WIDTH, HEIGHT), [])

                receivers = {a.target for a in diagram.arrows}
                left = min(box.x0 for box in boxes.values())
                for name, box in boxes.items():
                    self.assertEqual(box.x0 == left, name not in receivers, name)
                for arrow in diagram.arrows:
                    source, target = boxes[arrow.source], boxes[arrow.target]
                    self.assertLess(source.x1, target.x0)
                    for (x, y), edge_x, rect in ((arrow.points[0], source.x1, source),
                                                 (arrow.points[-1], target.x0, target)):
                        self.assertAlmostEqual(x, edge_x)
                        self.assertLess(rect.y0, y)
                        self.assertLess(y, rect.y1)

    def test_unequal_length_paths_reach_the_same_rightmost_receiver(self):
        data = support.small_workflow()
        data["project"]["systems"] = [
            {"name": "C"},
            {"name": "B", "sends": [{"to": "C", "what": "Log"}]},
            {"name": "A", "sends": [{"to": "C", "what": "Note"}, {"to": "B", "what": "Query"}]},
        ]
        project = model.parse(data)
        diagram = systems_layout.lay_out(project.systems, WIDTH, HEIGHT)
        boxes = {b.name: b.rect for b in diagram.boxes}
        self.assertLess(boxes["A"].x1, boxes["B"].x0)
        self.assertLess(boxes["B"].x1, boxes["C"].x0)
        self.assertCountEqual([a.what for a in diagram.arrows], ["Log", "Note", "Query"])
        self.assertEqual(layout_problems(diagram), [])

    def test_two_senders_can_each_reach_both_receivers_without_a_crossing(self):
        data = support.small_workflow()
        systems = [
            {"name": "Website", "sends": [{"to": "API", "what": "Page request"},
                                          {"to": "Login", "what": "Web credentials"}]},
            {"name": "Phone app", "sends": [{"to": "Login", "what": "App credentials"},
                                            {"to": "API", "what": "Mobile request"}]},
            {"name": "API"}, {"name": "Login"},
        ]
        expected = [(s["name"], send["to"], send["what"]) for s in systems for send in s.get("sends", [])]
        for order in permutations(systems):
            with self.subTest(order=[s["name"] for s in order]):
                data["project"]["systems"] = list(order)
                diagram = systems_layout.lay_out(model.parse(data).systems, WIDTH, HEIGHT)
                boxes = {b.name: b.rect for b in diagram.boxes}
                self.assertCountEqual([b.name for b in diagram.boxes], [s["name"] for s in systems])
                self.assertEqual(boxes["Website"].x0, boxes["Phone app"].x0)
                self.assertEqual(boxes["API"].x0, boxes["Login"].x0)
                self.assertLess(boxes["Website"].x1, boxes["API"].x0)
                self.assertCountEqual([(a.source, a.target, " ".join(a.label_lines)) for a in diagram.arrows],
                                      expected)
                self.assertEqual(layout_problems(diagram), [])
                for arrow in diagram.arrows:
                    for rect, (x, y), (px, py) in [
                            (boxes[arrow.source], arrow.points[0], arrow.points[1]),
                            (boxes[arrow.target], arrow.points[-1], arrow.points[-2])]:
                        if px == x:
                            self.assertTrue(rect.x0 < x < rect.x1)
                            self.assertAlmostEqual(y, rect.y0 if py < y else rect.y1, places=5)
                        else:
                            self.assertAlmostEqual(py, y, places=5)
                            self.assertTrue(rect.y0 < y < rect.y1)
                            self.assertAlmostEqual(x, rect.x0 if px < x else rect.x1, places=5)

    def test_oracle_catches_a_broken_copy_with_two_boxes_at_the_same_position(self):
        project = model.parse(joining_workflow())
        diagram = systems_layout.lay_out(project.systems, WIDTH, HEIGHT)
        self.assertEqual(layout_problems(diagram, WIDTH, HEIGHT), [])
        broken = copy.deepcopy(diagram)
        first, second = broken.boxes[:2]
        second.rect = first.rect
        self.assertIn("%s overlaps %s" % (first.name, second.name), layout_problems(broken, WIDTH, HEIGHT))
