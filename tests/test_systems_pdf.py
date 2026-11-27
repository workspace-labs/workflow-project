"""Read the delivered PDFs back with Poppler, including each numbered part card and its destination."""

import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pdf_words
import support
from test_found_gaps import boxes_for, read_word, reading_rows, run_tool
from test_render import _draw_here
from test_systems_layout import arabic_fixture
from workflow_tool import language, pages, render_systems

FIXTURES = Path(__file__).parent / "fixtures"


def reading_order(words, rtl):
    return [read_word(word, rtl) for row in reading_rows(words, rtl) for word in row]


def inside(rect, word):
    # Poppler rounds positions in the PDF to thousandths of a point.
    return (rect[0] - .01 <= word[0] and rect[1] - .01 <= word[1] and
            rect[2] + .01 >= word[2] and rect[3] + .01 >= word[3])


def card_pointers(words):
    """Read the numeral immediately beside each small 'page' label, in visual row/column order."""
    found = []
    for x0, y0, _, y1, text in words:
        if text != "page":
            continue
        for nx0, ny0, nx1, ny1, number in words:
            if number.isdigit() and 0 < x0 - nx1 < 10 and ny0 <= y0 and ny1 >= y1:
                found.append((round(ny0, 1), nx0, int(number)))
    return [n for _, _, n in sorted(found)]


class SystemsPageRefusals(unittest.TestCase):
    def test_schema_valid_wide_words_and_crossing_sends_are_refused_before_writing(self):
        # All strings and counts are within the input limits. Only the geometry can reject them.
        wide_names = ["W" * 23 + suffix for suffix in "ABCDE"]
        wide = [{"name": n, "sends": [{"to": to, "what": "Copy"}]} for n, to in zip(wide_names, wide_names[1:])]
        wide.append({"name": wide_names[-1]})
        sinks = ["X", "Y", "Z"]
        crossing = ([{"name": n, "sends": [{"to": to, "what": "Copy"} for to in sinks]} for n in "ABC"]
                    + [{"name": n} for n in sinks])
        for systems, reason in ((wide, "too wide"), (crossing, "cross")):
            data = support.small_workflow()
            data["project"]["systems"] = systems
            for check in (True, False):
                with self.subTest(reason=reason, check=check), tempfile.TemporaryDirectory() as folder:
                    result, dest = run_tool(folder, data, check=check)
                    self.assertEqual(result.returncode, 1, result.stderr)
                    self.assertRegex(result.stderr.lower(), r"(?m)^  1\. .*" + reason)
                    if systems is wide:
                        self.assertIn("Shorten", result.stderr)
                    else:
                        senders = set(re.findall(r'"([ABC])"', result.stderr))
                        self.assertGreaterEqual(len(senders), 2, result.stderr)
                        self.assertIn("split", result.stderr.lower())
                    self.assertFalse(dest.exists())


@unittest.skipUnless(pdf_words.AVAILABLE, "pdftotext is not installed")
class SystemsPdf(unittest.TestCase):
    def test_omitting_systems_preserves_every_page_and_word_of_all_five_examples(self):
        # Captured by rendering an isolated export of 505984a with its own unchanged CLI and assets.
        before = json.loads((FIXTURES / "example-words-0.5.0.json").read_text(encoding="utf-8"))
        self.assertEqual(set(before), {"shop-orders", "leave-request", "leave-request-ar",
                                       "building-permit", "workflow-project"})
        for name, expected_pages in before.items():
            with self.subTest(example=name), tempfile.TemporaryDirectory() as folder:
                data = support.example_data(name)
                data["project"].pop("systems", None)
                result, output = run_tool(folder, data)
                self.assertEqual(result.returncode, 0, result.stderr)
                drawn = pdf_words.pages(output)
                self.assertEqual(len(drawn), len(expected_pages))
                for n, (_, _, words) in enumerate(drawn):
                    self.assertEqual(" ".join(reading_order(words, name.endswith("-ar"))), expected_pages[n],
                                     "%s page %d differs from 0.5.0" % (name, n + 1))

    def assert_pagination(self, data, maps, closing):
        with tempfile.TemporaryDirectory() as folder:
            result, output = run_tool(folder, data)
            self.assertEqual(result.returncode, 0, result.stderr)
            drawn = pdf_words.pages(output)
        first_part = maps + 3
        total = first_part - 1 + len(data["parts"]) + int(closing)
        part_pages = list(range(first_part, first_part + len(data["parts"])))
        self.assertEqual(len(drawn), total)
        self.assertTrue(boxes_for(drawn[0][2], "on %d pages." % total, False))
        self.assertTrue(boxes_for(drawn[maps + 1][2], "What it is built from", False))
        self.assertTrue(boxes_for(drawn[maps + 1][2], "The systems", False))
        self.assertEqual([n for _, _, words in drawn[1:maps + 1] for n in card_pointers(words)], part_pages)
        for part, page in zip(data["parts"], part_pages):
            self.assertTrue(boxes_for(drawn[page - 1][2], part["title"], False), part["title"])
        for n, (_, height, words) in enumerate(drawn[1:], 2):
            self.assertTrue(boxes_for([w for w in words if w[1] > height - 32],
                                      "Page %d of %d" % (n, total), False))
        if closing:
            self.assertTrue(boxes_for(drawn[-1][2], "Before it is built", False))
        return drawn

    def test_shop_orders_cards_footers_and_continuation_lead_to_the_right_pages(self):
        drawn = self.assert_pagination(support.example_data("shop-orders"), maps=1, closing=False)
        self.assertTrue(boxes_for(drawn[3][2], "Continues in Part 2 (page 5)", False))

    def test_systems_follows_all_map_pages_and_leaves_closing_last(self):
        data = support.small_workflow()
        data["parts"] = [dict(data["parts"][0], title="Stage %s" % chr(65 + i)) for i in range(13)]
        data["project"]["systems"] = [{"name": "Inbox", "sends": [{"to": "Desk", "what": "Query"}]},
                                      {"name": "Desk"}]
        data["project"]["open_questions"] = [
            "How will staff handle the question when the office is closed, and who sends the response "
            "to the customer after the office opens?"
        ] * 8
        self.assert_pagination(data, maps=2, closing=True)

    def test_actual_words_fit_their_boxes_and_arrow_labels_in_both_reading_directions(self):
        self.addCleanup(language.use, language.DEFAULT)
        draw = render_systems.draw
        for data in (support.example_data("shop-orders"), arabic_fixture()):
            rtl = data["project"].get("language") == "ar"
            regions = []
            physical_boxes = {}
            systems = {s["name"]: s for s in data["project"]["systems"]}

            def record(c, diagram, left, top):
                # Convert the actual canvas placement into the top-left coordinates used by Poppler.
                # This includes the page's real mirror transform when drawing Arabic.
                def page_rect(rect):
                    ax, ay = c.absolutePosition(left + rect.x0, top - rect.y0)
                    bx, by = c.absolutePosition(left + rect.x1, top - rect.y1)
                    return min(ax, bx), pages.PAGE_H - ay, max(ax, bx), pages.PAGE_H - by
                for box in diagram.boxes:
                    rect = page_rect(box.rect)
                    physical_boxes[box.name] = rect
                    system = systems[box.name]
                    regions.append((rect, (box.name + " " + system.get("detail", "")).split()))
                for arrow in diagram.arrows:
                    regions.append((page_rect(arrow.label_rect), arrow.what.split()))
                # Check the rectangles actually sent to the PDF as well as the intended placement.
                painted = []
                round_rect = c.roundRect
                def record_box(x, y, w, h, *args, **kwargs):
                    ax, ay = c.absolutePosition(x, y + h)
                    bx, by = c.absolutePosition(x + w, y)
                    painted.append((min(ax, bx), pages.PAGE_H - ay, max(ax, bx), pages.PAGE_H - by))
                    return round_rect(x, y, w, h, *args, **kwargs)
                paths = []
                draw_path = c.drawPath
                def record_path(path, stroke=1, fill=0, fillMode=None):
                    paths.append((stroke, fill, path.getCode()))
                    return draw_path(path, stroke, fill, fillMode)
                with patch.object(c, "roundRect", record_box), patch.object(c, "drawPath", record_path):
                    draw(c, diagram, left, top)
                # Inspect the actual vector paths. Every send has a shaft and a filled triangle
                # whose tip meets a receiving edge and points in the page's reading direction.
                self.assertEqual(sum(stroke for stroke, _, _ in paths), len(diagram.arrows))
                tips = []
                for _, filled, path in paths:
                    if filled:
                        coords = re.findall(r"([-\d.]+) ([-\d.]+) [ml]", path)
                        self.assertEqual(len(coords), 3, path)
                        tip, wing_a, wing_b = [c.absolutePosition(float(x), float(y)) for x, y in coords]
                        self.assertEqual(tip[0] < wing_a[0], rtl)
                        self.assertEqual(tip[0] < wing_b[0], rtl)
                        tips.append(tuple(round(v, 2) for v in tip))
                expected_tips = [c.absolutePosition(left + a.points[-1][0], top - a.points[-1][1])
                                 for a in diagram.arrows]
                self.assertCountEqual(tips, [tuple(round(v, 2) for v in tip) for tip in expected_tips])
                self.assertCountEqual([tuple(round(v, 3) for v in r) for r in painted],
                                      [tuple(round(v, 3) for v in r) for r in physical_boxes.values()])

            with self.subTest(rtl=rtl), tempfile.TemporaryDirectory() as folder:
                source, output = Path(folder) / "in.json", Path(folder) / "out.pdf"
                source.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
                with patch.object(render_systems, "draw", record):
                    code, out, err = _draw_here(str(source), str(output))
                self.assertEqual(code, 0, err or out)
                drawn = pdf_words.pages(output)
                self.assertEqual(len(drawn), 4 if rtl else 5)
                words = drawn[2][2]
                if rtl:
                    self.assertTrue(boxes_for(words, "مكونات المشروع", True))
                    self.assertTrue(boxes_for(words, "الأنظمة", True))
                    self.assertTrue(boxes_for(words, "يوضح كل سهم ما يرسله نظام إلى آخر.", True))
                    for n, (_, height, page_words) in enumerate(drawn[1:], 2):
                        self.assertTrue(boxes_for([w for w in page_words if w[1] > height - 32],
                                                  "صفحة %d من 4" % n, True))
                self.assertEqual(pdf_words.problems(output, trim=0.2 if rtl else 0), [])
                for rect, expected in regions:
                    self.assertEqual(reading_order([w for w in words if inside(rect, w)], rtl), expected)
                self.assertEqual(set(physical_boxes), set(systems))
                for source_name, system in systems.items():
                    for send in system.get("sends", []):
                        source_box, target_box = physical_boxes[source_name], physical_boxes[send["to"]]
                        if rtl:
                            self.assertGreater(source_box[0], target_box[2], "Arabic flow starts on the right")
                        else:
                            self.assertLess(source_box[2], target_box[0])
