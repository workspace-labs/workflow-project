"""The whole PDF is built: right page count, page numbers that agree, the house font inside, and a
command line that answers in plain words."""

import base64
import importlib.util
import io
import locale
import os
import re
import zlib
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

import pdf_words
import support
from workflow_tool import brand, layout, model, pages

EXPECTED_PAGES = {"leave-request": 5, "building-permit": 11, "workflow-project": 10}
TOOL = os.path.join(support.SCRIPTS, "draw_workflow.py")
ENGLISH_DATE = "25 September 2026"


def build(name, folder):
    project = model.parse(support.example_data(name))
    diagrams = [layout.lay_out(p, pages.FRAME_W, pages.diagram_room(p, len(project.parts))) for p in project.parts]
    path = os.path.join(folder, name + ".pdf")
    found = pages.build(project, diagrams, path, brand.load())
    with open(path, "rb") as handle:
        return project, found, handle.read()


def _draw_here(source, out):
    """Draw with this process's locale. A new Python would not inherit locale.setlocale."""
    spec = importlib.util.spec_from_file_location("draw_workflow_under_test", TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    stdout, stderr = io.StringIO(), io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        code = module.main([source, "-o", out])
    return code, stdout.getvalue(), stderr.getvalue()


def _lines(words):
    """Words on one baseline, left to right, joined into lines."""
    rows = []
    for x0, y0, x1, y1, text in sorted(words, key=lambda item: (round(item[1], 1), item[0])):
        if rows and abs(y0 - rows[-1][0]) <= 2.0:
            rows[-1][1].append(text)
        else:
            rows.append((y0, [text]))
    return [" ".join(parts) for _, parts in rows]


class DatesStayEnglish(unittest.TestCase):
    """The cover month used to follow the computer's language. Arabic drew empty boxes."""

    def setUp(self):
        self._previous_locale = locale.setlocale(locale.LC_ALL)

    def tearDown(self):
        locale.setlocale(locale.LC_ALL, self._previous_locale)

    def test_the_month_is_english_in_any_locale(self):
        for loc in ("C", "fr_FR.UTF-8", "ar_AE.UTF-8", "ru_RU.UTF-8"):
            with self.subTest(locale=loc):
                locale.setlocale(locale.LC_ALL, loc)
                self.assertEqual(pages.nice_date("2026-09-25"), ENGLISH_DATE)
                self.assertEqual(pages.nice_date("not-a-date"), "not-a-date")

    @unittest.skipUnless(pdf_words.AVAILABLE, "pdftotext is not installed")
    def test_the_drawn_date_stays_english(self):
        source = os.path.join(support.EXAMPLES, "leave-request.json")
        for loc in ("fr_FR.UTF-8", "ar_AE.UTF-8"):
            with self.subTest(locale=loc):
                locale.setlocale(locale.LC_ALL, loc)
                with tempfile.TemporaryDirectory() as folder:
                    out = os.path.join(folder, "out.pdf")
                    code, stdout, stderr = _draw_here(source, out)
                    self.assertEqual(code, 0, stderr or stdout)
                    self.assertNotIn("Traceback", stderr)
                    drawn = pdf_words.pages(out)
                    cover = _lines(drawn[0][2])
                    self.assertTrue(any(ENGLISH_DATE in line for line in cover), cover)
                    footers = []
                    for number, (_, _, words) in enumerate(drawn, 1):
                        for line in _lines(words):
                            if re.search(r"Page \d+ of \d+", line):
                                footers.append((number, line))
                    self.assertGreaterEqual(len(footers), 1, "no inner-page footer was drawn")
                    for number, line in footers:
                        self.assertIn(ENGLISH_DATE, line, "page %d footer %r" % (number, line))


class WholePdf(unittest.TestCase):
    def test_every_example_builds(self):
        with tempfile.TemporaryDirectory() as folder:
            for name, expected in EXPECTED_PAGES.items():
                with self.subTest(example=name):
                    project, found, data = build(name, folder)
                    self.assertTrue(data.startswith(b"%PDF-"))
                    self.assertEqual(found["total"], expected)
                    self.assertEqual(len(re.findall(rb"/Type /Page\b", data)), expected)

    def test_page_numbers_agree(self):
        with tempfile.TemporaryDirectory() as folder:
            project, found, _ = build("building-permit", folder)
        starts = [found[part.number] for part in project.parts]
        self.assertEqual(starts, sorted(starts))
        self.assertEqual(starts[0], 4, "cover, one page, map, then part 1")
        self.assertLess(starts[-1], found["total"], "the end card comes after the last part")

    def test_the_house_font_is_embedded_and_nothing_falls_back(self):
        with tempfile.TemporaryDirectory() as folder:
            _, _, data = build("leave-request", folder)
        for face in (b"PlusJakartaSans-Regular", b"PlusJakartaSans-Bold", b"PlusJakartaSans-ExtraBold"):
            self.assertIn(b"+" + face, data)
        self.assertEqual(data.count(b"/FontFile2"), 5, "all five weights are embedded")
        # reportlab always declares Helvetica as /F1 and selects it once per page; no text may be shown in it
        streams = _page_streams(data)
        self.assertEqual(len(streams), 5, "one drawing stream per page")
        self.assertEqual(_text_shown_in(streams, b"F1"), 0, "some text fell back to Helvetica")
        self.assertGreater(_text_shown_in(streams, None), 50, "the pages do show text")


def _page_streams(data):
    """The decoded drawing instructions of every page (streams that select a font)."""
    found = []
    for match in re.finditer(rb"/Filter \[ /ASCII85Decode /FlateDecode \][^>]*>>\s*stream\r?\n(.*?)endstream", data, re.S):
        raw = match.group(1).strip()
        if raw.endswith(b"~>"):
            raw = raw[:-2]
        try:
            found.append(zlib.decompress(base64.a85decode(raw)))
        except (ValueError, zlib.error):
            continue
    return [stream for stream in found if b" Tf" in stream]


def _text_shown_in(streams, font):
    """How many text-showing instructions run while `font` is selected (None counts every one)."""
    shown = 0
    for stream in streams:
        current = None
        for match in re.finditer(rb"/(F\d+)(?:\+\d+)? [\d.]+ Tf|\s(Tj|TJ)\b", stream):
            if match.group(1):
                current = match.group(1)
            elif font is None or current == font:
                shown += 1
    return shown


class CommandLine(unittest.TestCase):
    def run_tool(self, *args):
        result = subprocess.run([sys.executable, TOOL] + list(args), capture_output=True, text=True)
        return result.returncode, result.stdout, result.stderr

    def test_check_only(self):
        code, out, _ = self.run_tool(os.path.join(support.EXAMPLES, "leave-request.json"), "--check")
        self.assertEqual(code, 0)
        self.assertIn("Ready to draw.", out)

    def test_draws_to_the_named_file(self):
        with tempfile.TemporaryDirectory() as folder:
            target = os.path.join(folder, "out.pdf")
            code, out, _ = self.run_tool(os.path.join(support.EXAMPLES, "leave-request.json"), "-o", target)
            self.assertEqual(code, 0)
            self.assertIn("Drew 5 pages", out)
            self.assertTrue(os.path.getsize(target) > 10000)

    def test_a_broken_file_is_refused_with_numbered_reasons(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "broken.json")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write('{"project": {"summary": "x", "actors": ["A"]}, "parts": []}')
            code, _, err = self.run_tool(path, "--check")
        self.assertEqual(code, 1)
        self.assertIn("Not drawn yet.", err)
        self.assertIn('  1. The project\'s "name" is missing.', err)

    def test_no_file_is_a_usage_error(self):
        code, _, err = self.run_tool()
        self.assertEqual(code, 2)
        self.assertIn("usage:", err)

    def test_missing_reportlab_is_explained(self):
        sys.path.insert(0, support.SCRIPTS)
        import draw_workflow
        saved = sys.modules.get("reportlab")
        sys.modules["reportlab"] = None
        try:
            err = io.StringIO()
            with redirect_stderr(err), redirect_stdout(io.StringIO()):
                code = draw_workflow.main(["anything.json"])
        finally:
            sys.modules["reportlab"] = saved
        self.assertEqual(code, 3)
        self.assertIn("pip install reportlab", err.getvalue())

    def test_running_leaves_no_cache_files_in_the_skill(self):
        self.run_tool(os.path.join(support.EXAMPLES, "leave-request.json"), "--check")
        for root, dirs, files in os.walk(support.SKILL_DIR):
            self.assertNotIn("__pycache__", dirs, root)
            self.assertFalse([f for f in files if f.endswith(".pyc")], root)


if __name__ == "__main__":
    unittest.main()
