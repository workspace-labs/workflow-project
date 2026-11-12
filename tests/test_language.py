"""Languages: the fixed words come from a file, and Arabic is joined, ordered and mirrored.

The expected letter shapes below were worked out by hand from the Unicode chart, not by the tool. The
drawn pages are judged by pdf_words (poppler) and the geometry oracle, which never import the tool.
"""

import json
import os
import re
import string
import subprocess
import sys
import tempfile
import unittest

import pdf_words
import support
import test_layout
from workflow_tool import language, model, pages, script

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
TOOL = os.path.join(support.SCRIPTS, "draw_workflow.py")
ARABIC = {"leave-request-ar": os.path.join(support.EXAMPLES, "leave-request-ar.json"),
          "building-permit-ar": os.path.join(FIXTURES, "building-permit-ar.json")}
INK = 0.2      # the inked part of an Arabic word: its box less a fifth at the top and at the bottom (see pdf_words)
SAME_PAGES_AS = {"leave-request-ar": 3, "building-permit-ar": 8}      # their English twins' page counts


def drawn(text):
    """What script.visual says is drawn, left to right, as one string."""
    return "".join(ch for ch, _ in script.visual(text))


def data_of(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def draw(source, out):
    return subprocess.run([sys.executable, "-B", TOOL, source, "-o", out], capture_output=True, text=True)


class InArabic(unittest.TestCase):
    """Runs with the language set to Arabic, and always puts English back."""

    def setUp(self):
        language.use("ar")

    def tearDown(self):
        language.use(language.DEFAULT)


class LanguageFiles(unittest.TestCase):
    def test_every_language_has_the_same_sentences_with_the_same_blanks(self):
        english = language.load("en")["words"]
        self.assertGreaterEqual(len(language.available()), 2)
        for code in language.available():
            found = language.load(code)
            with self.subTest(language=code):
                self.assertIn(found["direction"], ("ltr", "rtl"))
                self.assertEqual(len(found["months"]), 12)
                self.assertEqual(sorted(found["words"]), sorted(english))
                for key, sentence in english.items():
                    blanks = sorted(name for _, name, _, _ in string.Formatter().parse(sentence) if name)
                    theirs = sorted(name for _, name, _, _ in string.Formatter().parse(found["words"][key]) if name)
                    self.assertEqual(theirs, blanks, key)

    def test_english_is_the_default(self):
        project = model.parse(support.small_workflow())
        self.assertEqual(project.language, "en")
        self.assertFalse(language.rtl())

    def test_an_unknown_language_is_refused(self):
        data = support.small_workflow()
        data["project"]["language"] = "xx"
        with self.assertRaises(model.WorkflowError) as caught:
            model.parse(data)
        self.assertIn('"language" must be one of', " ".join(caught.exception.problems))

    def test_arabic_words_in_an_english_workflow_are_refused_with_the_way_out(self):
        data = support.small_workflow()
        data["project"]["name"] = "نظام الإجازات"
        with self.assertRaises(model.WorkflowError) as caught:
            model.parse(data)
        message = " ".join(caught.exception.problems)
        self.assertIn("characters the house font cannot draw", message)
        self.assertIn('"language": "ar"', message)

    def test_a_letter_that_cannot_be_joined_is_refused(self):
        data = data_of(ARABIC["leave-request-ar"])
        data["project"]["name"] = "نظام پیام"          # Persian letters: no joined shapes here
        with self.assertRaises(model.WorkflowError) as caught:
            model.parse(data)
        self.assertIn("cannot draw", " ".join(caught.exception.problems))


class Joining(unittest.TestCase):
    def test_letters_take_their_start_middle_and_end_shapes(self):
        # beh starts, yeh is in the middle, teh ends; drawn left to right that is teh, yeh, beh
        self.assertEqual(drawn("بيت"), "ﺖﻴﺑ")

    def test_letters_that_never_reach_forward_stay_apart(self):
        # dal, alef and reh do not join the letter after them; a letter standing alone stays the plain letter
        self.assertEqual(drawn("\u062f\u0627\u0631"), "\u0631\u0627\u062f")

    def test_lam_and_alef_become_one_shape(self):
        # seen starts, lam + alef is one end shape, meem stands alone
        self.assertEqual(drawn("\u0633\u0644\u0627\u0645"), "\u0645\ufefc\ufeb3")

    def test_a_mark_comes_just_before_its_letter(self):
        found = drawn("\u0628\u0651")
        self.assertEqual(found, "\u0651\u0628")


class Ordering(unittest.TestCase):
    def test_latin_words_keep_their_order(self):
        self.assertEqual(drawn("WorkSpace Labs"), "WorkSpace Labs")
        found = drawn("ملف PDF برمز QR")
        self.assertLess(found.index("QR"), found.index("PDF"), "the line still reads right to left")

    def test_a_number_reads_left_to_right_inside_arabic(self):
        found = drawn("الإصدار 1.0 · 2 أكتوبر 2026")
        self.assertIn("1.0", found)
        self.assertIn("2026", found)
        self.assertLess(found.index("2026"), found.index("1.0"), "what is said last is drawn leftmost")

    def test_brackets_still_face_their_words(self):
        found = drawn("(توقف)")
        self.assertTrue(found.startswith("(") and found.endswith(")"))


class ArabicDates(InArabic):
    def test_the_month_is_arabic_in_an_arabic_workflow(self):
        self.assertEqual(pages.nice_date("2026-09-25"), "25 سبتمبر 2026")

    def test_english_comes_back(self):
        language.use("en")
        self.assertEqual(pages.nice_date("2026-09-25"), "25 September 2026")


class ArabicDiagramsAreClean(InArabic, test_layout.CleanDiagrams):
    """Every geometry check the English examples pass, on Arabic text measured as Arabic."""

    def each_diagram(self):
        for name, path in ARABIC.items():
            for diagram in test_layout.lay_out_all(data_of(path)):
                yield name, diagram


@unittest.skipUnless(pdf_words.AVAILABLE, "pdftotext is not installed")
class ArabicPdf(unittest.TestCase):
    def test_it_draws_and_no_word_overlaps_or_leaves_the_page(self):
        with tempfile.TemporaryDirectory() as folder:
            for name, path in ARABIC.items():
                with self.subTest(example=name):
                    out = os.path.join(folder, name + ".pdf")
                    result = draw(path, out)
                    self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
                    self.assertNotIn("Traceback", result.stderr)
                    self.assertEqual(len(pdf_words.pages(out)), SAME_PAGES_AS[name])
                    self.assertEqual(pdf_words.problems(out, trim=INK), [])

    def test_the_page_is_mirrored_and_latin_words_are_not(self):
        with tempfile.TemporaryDirectory() as folder:
            arabic, english = os.path.join(folder, "ar.pdf"), os.path.join(folder, "en.pdf")
            self.assertEqual(draw(ARABIC["leave-request-ar"], arabic).returncode, 0)
            self.assertEqual(draw(os.path.join(support.EXAMPLES, "leave-request.json"), english).returncode, 0)
            sides = {}
            for label, pdf in (("ar", arabic), ("en", english)):
                width, _, words = pdf_words.pages(pdf)[1]          # an inner page: the brand sits in its top bar
                brand = {text: x0 for x0, _, _, _, text in words if text in ("WorkSpace", "Labs")}
                self.assertEqual(sorted(brand), ["Labs", "WorkSpace"], label)
                self.assertLess(brand["WorkSpace"], brand["Labs"], "%s: the name reads left to right" % label)
                sides[label] = brand["WorkSpace"] > width / 2.0
            self.assertEqual(sides, {"ar": True, "en": False}, "the brand moves to the right-hand side in Arabic")

    def test_the_arabic_font_is_inside_and_nothing_falls_back(self):
        import test_render
        with tempfile.TemporaryDirectory() as folder:
            out = os.path.join(folder, "ar.pdf")
            self.assertEqual(draw(ARABIC["leave-request-ar"], out).returncode, 0)
            with open(out, "rb") as handle:
                data = handle.read()
        self.assertTrue(re.search(rb"\+Alexandria-(Regular|Bold)", data), "the house font is not embedded")
        streams = test_render._page_streams(data)
        self.assertEqual(test_render._text_shown_in(streams, b"F1"), 0, "some text fell back to Helvetica")

    def test_an_english_workflow_after_an_arabic_one_is_english(self):
        import test_render
        with tempfile.TemporaryDirectory() as folder:
            first, second = os.path.join(folder, "ar.pdf"), os.path.join(folder, "en.pdf")
            self.assertEqual(test_render._draw_here(ARABIC["leave-request-ar"], first)[0], 0)
            self.assertEqual(test_render._draw_here(os.path.join(support.EXAMPLES, "leave-request.json"), second)[0], 0)
            lines = [line for _, _, words in pdf_words.pages(second) for line in test_render._lines(words)]
            self.assertTrue(any(re.search(r"Page 2 of 3", line) for line in lines), "the footer is not English")
        self.assertFalse(language.rtl())
        language.use(language.DEFAULT)


if __name__ == "__main__":
    unittest.main()
