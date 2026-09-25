"""Whose name, logo and website the PDF carries comes from assets/brand.json: WorkSpace Labs by default,
anyone else's when they replace that file."""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

import pdf_words
import support
from workflow_tool import brand

CONTROL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "access-request.json")


class DefaultBrand(unittest.TestCase):
    def test_workspace_labs_is_the_default(self):
        owner = brand.load()
        self.assertEqual(owner.name, "WorkSpace Labs")
        self.assertEqual(owner.accent, "Labs")
        self.assertEqual(owner.website, "workspace-labs.net")
        self.assertTrue(owner.logo.endswith("logo-mark.png") and os.path.isfile(owner.logo))


class BrandCopy(object):
    """Runs the tool from a copy of the skill whose brand file another user has replaced."""

    def skill_copy(self, brand_data, extra_files=()):
        """A fresh folder holding a copy of the skill; its brand file becomes brand_data (None keeps ours)."""
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder)
        skill = os.path.join(folder, "workflow-project")
        shutil.copytree(support.SKILL_DIR, skill)
        for name, source in extra_files:
            shutil.copy(source, os.path.join(skill, "assets", name))
        if brand_data is not None:
            with open(os.path.join(skill, "assets", "brand.json"), "w", encoding="utf-8") as handle:
                json.dump(brand_data, handle)
        return folder, skill

    def run_tool(self, brand_data, check):
        """Draws (or only checks) the control workflow with this brand. Returns the run and every PDF that
        appeared anywhere in the fresh folder, so a refusal can be proved to have written nothing."""
        folder, skill = self.skill_copy(brand_data)
        workflow = shutil.copy(CONTROL, folder)
        route = ["--check"] if check else ["-o", os.path.join(folder, "out.pdf")]
        result = subprocess.run([sys.executable, "-B", os.path.join(skill, "scripts", "draw_workflow.py"), workflow]
                                + route, capture_output=True, text=True)
        pdfs = [os.path.join(top, name) for top, _, names in os.walk(folder) for name in names if name.endswith(".pdf")]
        return result, pdfs

    def draw_with(self, brand_data, extra_files=()):
        folder, skill = self.skill_copy(brand_data, extra_files)
        out = os.path.join(folder, "out.pdf")
        result = subprocess.run([sys.executable, os.path.join(skill, "scripts", "draw_workflow.py"),
                                 os.path.join(skill, "examples", "leave-request.json"), "-o", out],
                                capture_output=True, text=True)
        data = open(out, "rb").read() if os.path.exists(out) else b""
        return result, data


class AnotherUsersBrand(BrandCopy, unittest.TestCase):
    def test_their_name_replaces_ours(self):
        result, data = self.draw_with({"name": "Acme Studio", "accent": "Studio", "website": "acme.example",
                                       "logo": "acme.png"},
                                      extra_files=[("acme.png", os.path.join(support.SKILL_DIR, "assets", "logo-mark.png"))])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(b"/Author (Acme Studio)", data)
        self.assertNotIn(b"WorkSpace Labs", data)
        self.assertIn(b"/Subtype /Image", data, "their logo is drawn")

    def test_no_logo_and_no_website_are_allowed(self):
        result, data = self.draw_with({"name": "Acme", "logo": "", "website": ""})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(b"/Author (Acme)", data)
        self.assertNotIn(b"/Subtype /Image", data, "no logo means no picture at all")

    def test_our_logo_is_in_our_pdf(self):
        result, data = self.draw_with({"name": "WorkSpace Labs", "accent": "Labs", "website": "workspace-labs.net",
                                       "logo": "logo-mark.png"})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(b"/Author (WorkSpace Labs)", data)
        self.assertIn(b"/Subtype /Image", data)

    def test_a_broken_brand_file_is_refused_in_plain_words(self):
        cases = [
            ({"accent": "X"}, 'needs a "name"'),
            ({"name": "Acme Studio", "accent": "Labs"}, '"accent" must be one word of the name'),
            ({"name": "Acme", "logo": "missing.png"}, 'the logo "missing.png" is not a picture'),
            ({"name": "Acme", "colour": "red"}, 'unknown field "colour"'),
        ]
        for data, fragment in cases:
            with self.subTest(brand=data):
                result, pdf = self.draw_with(data)
                self.assertEqual(result.returncode, 1)
                self.assertIn(fragment, result.stderr)
                self.assertIn("brand file", result.stderr)
                self.assertEqual(pdf, b"", "nothing is drawn")


class WrongTypesAreRefused(BrandCopy, unittest.TestCase):
    """Review finding F06: a wrong type is refused, never silently dropped; missing or "" still means none."""

    def test_wrong_types_and_lengths_are_refused(self):
        cases = [
            ({"name": "Acme Studio", "accent": 123, "logo": "", "website": ""}, '"accent" must be text'),
            ({"name": "Acme Studio", "accent": "Studio", "logo": "", "website": []}, '"website" must be text'),
            ({"name": "Acme Studio", "logo": 5}, '"logo" must be text'),
            ({"name": 7}, '"name" must be text'),
            ({"name": "Acme Studio", "accent": "Studio", "website": "w" * 61}, '"website" is too long'),
        ]
        for data, fragment in cases:
            with self.subTest(brand=data):
                result, pdf = self.draw_with(data)
                self.assertEqual(result.returncode, 1)
                self.assertIn(fragment, result.stderr)
                self.assertEqual(pdf, b"")

    def test_missing_or_empty_optional_fields_still_mean_none(self):
        for data in ({"name": "Acme Studio"}, {"name": "Acme Studio", "accent": "", "website": "", "logo": ""}):
            with self.subTest(brand=data):
                result, pdf = self.draw_with(data)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(b"/Author (Acme Studio)", pdf)


WIDE_NAME = "W" * 40                # as long as the brand file allows, and wider than the bar at the top
WIDE_SITE = "w" * 56 + ".org"       # 60 characters: as long as allowed, and wider than the last page
TOP_BAR = 60.0                      # points from the top edge: the brand bar, above the page's content


class BrandTextMustFitThePage(BrandCopy, unittest.TestCase):
    """Review finding F03, brand half (Codex re-review 1): a brand name or website inside the brand file's
    character limits can still be too wide for where the pages draw it. It is refused by field, in both
    routes, before anything is written. The expectations are the command line's own outcome and, for
    accepted brands, the words pdftotext reads back; nothing asks the tool how wide its text is."""

    def assertRefusedByField(self, brand_data, refused, allowed):
        for check in (False, True):
            with self.subTest(route="--check" if check else "draw"):
                result, pdfs = self.run_tool(brand_data, check)
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertNotIn("Traceback", result.stderr)
                self.assertNotIn("Ready to draw", result.stdout)
                self.assertEqual(pdfs, [], "nothing is written")
                self.assertNotIn("too long", result.stderr, "inside the length limits: refused for its width")
                numbered = re.findall(r"^\s+\d+\. (.*)$", result.stderr, re.M)
                for field in refused:
                    self.assertTrue(any(line.startswith('The brand "%s"' % field) and "assets/brand.json" in line
                                        and "Use a shorter" in line for line in numbered),
                                    "no numbered reason names the brand %r:\n%s" % (field, result.stderr))
                for field in allowed:
                    self.assertFalse(any('The brand "%s"' % field in line for line in numbered), result.stderr)

    def test_a_name_too_wide_for_the_bar_at_the_top(self):
        self.assertRefusedByField({"name": WIDE_NAME, "accent": "", "logo": "", "website": ""},
                                  refused=["name"], allowed=["website"])

    def test_a_website_too_wide_for_the_last_page(self):
        self.assertRefusedByField({"name": "Acme Studio", "accent": "Studio", "logo": "", "website": WIDE_SITE},
                                  refused=["website"], allowed=["name"])

    def test_both_at_once_are_both_named(self):
        self.assertRefusedByField({"name": WIDE_NAME, "accent": "", "logo": "", "website": WIDE_SITE},
                                  refused=["name", "website"], allowed=[])

    def test_brands_that_fit_are_drawn_in_both_routes(self):
        controls = [  # (brand file, None = ours; the name's words; the website, None = no website line)
            (None, ["WorkSpace", "Labs"], "workspace-labs.net"),
            ({"name": "Acme Studio", "accent": "Studio", "logo": "", "website": "acme.example"},
             ["Acme", "Studio"], "acme.example"),
            ({"name": "Acme Studio", "accent": "", "logo": "", "website": ""}, ["Acme", "Studio"], None),
            ({"name": "Acme Studio"}, ["Acme", "Studio"], None),
        ]
        for brand_data, name_words, website in controls:
            with self.subTest(brand=brand_data):
                result, pdfs = self.run_tool(brand_data, check=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("Ready to draw.", result.stdout)
                self.assertEqual(pdfs, [], "--check writes nothing")
                result, pdfs = self.run_tool(brand_data, check=False)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(len(pdfs), 1)
                if not pdf_words.AVAILABLE:
                    continue
                pages = pdf_words.pages(pdfs[0])
                for number, (_, _, words) in enumerate(pages[:-1], 1):
                    bar = [word[4] for word in words if word[1] < TOP_BAR]
                    for part in name_words:
                        self.assertIn(part, bar, "page %d: the bar at the top shows the brand name" % number)
                self.assertEqual(pages[-1][2][-1][4], website or name_words[-1] + ".",
                                 "the last page ends with the website, or with the name when there is none")
                shown = set(word[4] for _, _, words in pages for word in words)
                self.assertEqual(shown & ({"WorkSpace", "Acme"} - set(name_words)), set(), "only this brand")
                self.assertEqual(pdf_words.problems(pdfs[0]), [])


if __name__ == "__main__":
    unittest.main()
