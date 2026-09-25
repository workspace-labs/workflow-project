"""The whole PDF is built: right page count, page numbers that agree, the house font inside, and a
command line that answers in plain words."""

import base64
import io
import os
import re
import zlib
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

import support
from workflow_tool import brand, layout, model, pages

EXPECTED_PAGES = {"leave-request": 5, "building-permit": 11, "workflow-project": 9}
TOOL = os.path.join(support.SCRIPTS, "draw_workflow.py")


def build(name, folder):
    project = model.parse(support.example_data(name))
    diagrams = [layout.lay_out(p, pages.FRAME_W, pages.diagram_room(p, len(project.parts))) for p in project.parts]
    path = os.path.join(folder, name + ".pdf")
    found = pages.build(project, diagrams, path, brand.load())
    with open(path, "rb") as handle:
        return project, found, handle.read()


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
