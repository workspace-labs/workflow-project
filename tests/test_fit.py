"""Every word the PDF shows fits where it is drawn, or the workflow is refused before any PDF is written
(review findings F02 and F03). Accepted drawings are read back with pdftotext, not with the tool's own
measurements; malformed lanes give numbered reasons, never a traceback (F04)."""

import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest

import pdf_words
import support

TOOL = os.path.join(support.SCRIPTS, "draw_workflow.py")
FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")


def fixture(name):
    with open(os.path.join(FIXTURES, name + ".json"), encoding="utf-8") as handle:
        return json.load(handle)


def run(data, check=False):
    """Draws (or checks) a workflow; returns (exit code, stderr, path of the PDF or None)."""
    folder = tempfile.mkdtemp()
    path = os.path.join(folder, "workflow.json")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle)
    out = os.path.join(folder, "out.pdf")
    command = [sys.executable, "-B", TOOL, path] + (["--check"] if check else ["-o", out])
    result = subprocess.run(command, capture_output=True, text=True)
    return result.returncode, result.stderr, out if os.path.exists(out) else None


def rename_actor(data, old, new):
    data = copy.deepcopy(data)
    for actor in data["project"]["actors"]:
        if actor["name"] == old:
            actor["name"] = new
    for part in data["parts"]:
        part["lanes"] = [new if lane == old else lane for lane in part["lanes"]]
        for node in part["nodes"]:
            if node["lane"] == old:
                node["lane"] = new
    return data


class Refused(unittest.TestCase):
    """Each case must stop in both routes, name the field, and write no PDF."""

    def assertRefused(self, data, fragment):
        for check in (False, True):
            code, err, pdf = run(data, check)
            with self.subTest(check=check):
                self.assertEqual(code, 1, err)
                self.assertIn("1. ", err)
                self.assertIn(fragment, err)
                self.assertNotIn("Traceback", err)
                self.assertIsNone(pdf)

    def test_f02_actor_name_too_wide_for_its_lane(self):
        self.assertRefused(fixture("long-actor"), 'the lane name "CommunicationsDepartment" does not fit its column')

    def test_f02_actor_name_fits_its_lane_but_not_the_table(self):
        data = support.small_workflow()
        data = rename_actor(data, "Office", "CommunicationsDepartment")
        self.assertRefused(data, 'The actor name "CommunicationsDepartment" does not fit the "Who" column')

    def test_f03_project_name_with_one_giant_word(self):
        self.assertRefused(fixture("long-project-word"), 'The project\'s "name" does not fit the cover')

    def test_f03_client_with_one_giant_word(self):
        self.assertRefused(fixture("long-client"), 'The cover\'s "Prepared for" line')

    def test_f03_part_title_that_cannot_fit_the_map(self):
        data = support.example_data("building-permit")
        data["parts"][1]["title"] = "W" * 60
        self.assertRefused(data, 'does not fit its box on the map')

    def test_f04_malformed_lanes_get_numbered_reasons(self):
        base = fixture("access-request")
        cases = {"a list": [], "an object": {}, "null": None, "a number": 7, "true/false": True, "missing": "drop"}
        for kind, value in cases.items():
            data = copy.deepcopy(base)
            node = [n for n in data["parts"][0]["nodes"] if n["id"] == "submit"][0]
            if value == "drop":
                del node["lane"]
            else:
                node["lane"] = value
            with self.subTest(lane=kind):
                self.assertRefused(data, 'node "submit": "lane" must be the name of one of this part\'s lanes')
                self.assertRefused(data, "it is %s" % kind)
        data = copy.deepcopy(base)
        [n for n in data["parts"][0]["nodes"] if n["id"] == "submit"][0]["lane"] = "Nobody"
        self.assertRefused(data, 'node "submit": "lane" must be one of this part\'s lanes')


@unittest.skipUnless(pdf_words.AVAILABLE, "pdftotext is not installed")
class AcceptedAndClean(unittest.TestCase):
    """Long but honest text is drawn, and every drawn word stays on the page and clear of the others."""

    def assertClean(self, data):
        code, err, pdf = run(data)
        self.assertEqual(code, 0, err)
        self.assertEqual(pdf_words.problems(pdf), [])

    def test_the_examples_are_clean(self):
        for name in support.EXAMPLE_NAMES:
            with self.subTest(example=name):
                self.assertClean(support.example_data(name))
        self.assertClean(fixture("access-request"))

    def test_f02_a_long_actor_name_with_a_space_fits(self):
        self.assertClean(rename_actor(fixture("long-actor"), "CommunicationsDepartment", "Communications Department"))

    def test_f03_long_names_made_of_words_wrap(self):
        data = fixture("access-request")
        data["project"]["name"] = "Integrated Regional Access Request And Approval Management Platform"
        data["project"]["accent"] = "Platform"
        data["project"]["client"] = "The Department of Municipal Services and Transport, Northern Coastal Region"
        self.assertClean(data)

    def test_f03_long_map_titles_and_summaries_wrap(self):
        data = support.example_data("building-permit")
        for part in data["parts"][2:]:          # the short parts, so their pages keep room for the drawing
            part["title"] = "The complete and careful handling of every document in this stage"[:64]
            part["summary"] = ("Everything that happens in this part, written out in full so the map has to wrap it "
                               "across several lines without cutting anything short or running off the card.")
        self.assertClean(data)

    def test_the_old_failures_would_be_caught_by_this_check(self):
        """The same reader flags overlapping and off-page words, so a clean result above means something."""
        folder = tempfile.mkdtemp()
        pdf = os.path.join(folder, "bad.pdf")
        from reportlab.pdfgen import canvas
        c = canvas.Canvas(pdf)
        c.drawString(40, 700, "Overlapping words here")
        c.drawString(42, 700, "Overlapping words here")
        c.drawString(560, 600, "offthepage")
        c.drawString(-6, 500, "leftedge")           # starts left of the page: pdftotext gives it a negative xMin
        c.save()
        found = pdf_words.problems(pdf)
        self.assertTrue(any("overlaps" in line for line in found))
        # pdftotext keeps only the letters on the page: the start of the right one, the end of the left one
        self.assertTrue(any("'offth" in line and "runs off the page" in line for line in found))
        self.assertTrue(any("edge'" in line and "runs off the page" in line for line in found),
                        "a word running off the left edge is seen, not skipped")


if __name__ == "__main__":
    unittest.main()
