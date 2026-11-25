"""Found gaps go through the usual file checks and appear in the drawn workflow."""

import json
import subprocess
import sys
import tempfile
import unittest
import unicodedata
from html import unescape
from itertools import groupby
from pathlib import Path

import pdf_words
import support
from workflow_tool import model

TOOL = Path(support.SCRIPTS) / "draw_workflow.py"
LISTS = ("found_gaps", "assumptions", "open_questions")
TITLES = {
    "en": ("Gaps found", "What we assumed", "Still to confirm"),
    "ar": ("ثغرات وجدناها", "ما افترضناه", "ما يحتاج إلى تأكيد"),
}
SHORT_LISTS = {
    "en": (
        ["The calendar keeps rejected dates.", "Refused requests vanish."],
        ["All managers have a login.", "Managers can read requests."],
        ["Who scans old files?", "When does the notice arrive?"],
    ),
    "ar": (
        ["تبقى مواعيد الطلب المرفوض في التقويم.", "تختفي الطلبات المرفوضة من الشاشة."],
        ["يدخل المدير بحساب خاص.", "يرى المدير كل طلب."],
        ["متى يرد المدير؟", "من يراجع الطلب؟"],
    ),
}
LONG_GAP = {
    "en": "The request screen shows the same status after a refusal. The employee gets no notice.",
    "ar": "تعرض شاشة الطلب حالة قديمة بعد أن يرفض المدير الطلب ويبقى الموظف ينتظر رد النظام.",
}


class FoundGapsModel(unittest.TestCase):
    def test_eight_found_gaps_are_accepted(self):
        data = support.small_workflow()
        gaps = ["The request screen has no message for case %d." % number for number in range(1, 9)]
        data["project"]["found_gaps"] = gaps
        self.assertEqual(model.parse(data).found_gaps, gaps)

    def test_found_gaps_must_be_a_list_of_no_more_than_eight_sentences(self):
        message = 'The project\'s "found_gaps" must be a list of up to 8 short sentences.'
        for value in (["A step was skipped."] * 9, "A step was skipped.", {"gap": "A step was skipped."}):
            with self.subTest(value=value):
                data = support.small_workflow()
                data["project"]["found_gaps"] = value
                with self.assertRaises(model.WorkflowError) as caught:
                    model.parse(data)
                self.assertEqual(caught.exception.problems, [message])

    def test_each_gap_is_limited_to_220_characters(self):
        data = support.small_workflow()
        data["project"]["found_gaps"] = ["A" * 220]
        self.assertEqual(model.parse(data).found_gaps, ["A" * 220])
        data["project"]["found_gaps"] = ["A" * 221]
        with self.assertRaises(model.WorkflowError) as caught:
            model.parse(data)
        self.assertEqual(caught.exception.problems, [
            'The project\'s "found_gaps", item 1 is too long (221 characters; keep it to 220).',
        ])

    def test_the_misspelt_field_is_refused_by_name(self):
        data = support.small_workflow()
        data["project"]["found_gaps"] = ["No reply is shown."]
        data["project"]["found_gap"] = ["The misspelt key must not be accepted."]
        with self.assertRaises(model.WorkflowError) as caught:
            model.parse(data)
        self.assertEqual(len(caught.exception.problems), 1)
        self.assertIn('unknown field "found_gap"', caught.exception.problems[0])


def run_tool(folder, data, *, check=False):
    source, output = Path(folder) / "workflow.json", Path(folder) / "workflow.pdf"
    source.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    args = ["--check"] if check else ["-o", str(output)]
    result = subprocess.run([sys.executable, "-B", str(TOOL), str(source)] + args,
                            capture_output=True, text=True)
    return result, output


class FoundGapsRefusals(unittest.TestCase):
    def assert_refused(self, data, expected):
        for check in (False, True):
            with self.subTest(check=check), tempfile.TemporaryDirectory() as folder:
                result, output = run_tool(folder, data, check=check)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertEqual(result.stderr.splitlines()[1:], ["  1. " + expected])
                self.assertNotIn("Ready to draw.", result.stdout)
                self.assertFalse(output.exists())

    def test_a_word_too_wide_names_the_gaps_list(self):
        data = support.small_workflow()
        data["project"]["found_gaps"] = ["W" * 100]
        self.assert_refused(data, 'A sentence under "Gaps found" has a word too wide for the page. '
                                 'Break long words with spaces.')

    def test_lists_too_long_for_a_page_name_only_the_lists_present(self):
        cases = (
            ((), 35, '"Gaps found"'),
            (("open_questions",), 28, '"Gaps found" and "Still to confirm"'),
            (("assumptions", "open_questions"), 18, '"Gaps found", "What we assumed", and "Still to confirm"'),
        )
        for other_lists, word_length, titles in cases:
            with self.subTest(lists=titles):
                data = support.small_workflow()
                sentence = " ".join(["W" * word_length] * (221 // (word_length + 1)))
                data["project"]["found_gaps"] = [sentence] * 8
                for key in other_lists:
                    data["project"][key] = ["The file has another list."]
                self.assert_refused(data, "The sentences under %s need more than a page holds. "
                                         "Shorten them, or keep fewer." % titles)


def reading_rows(words, rtl):
    """Group Poppler boxes by line, then put each line in reading order."""
    order = sorted(words, key=lambda word: (round(word[1], 1), -word[2] if rtl else word[0]))
    return (list(row) for _, row in groupby(order, key=lambda word: round(word[1], 1)))


def read_word(word, rtl):
    """Poppler gives this PDF's Arabic glyphs in visual order. Reassemble them before normalizing."""
    text = unescape(word[4])
    if rtl and any(unicodedata.bidirectional(letter) == "AL" for letter in text):
        text = text[::-1]
    return unicodedata.normalize("NFKC", text)


def boxes_for(words, text, rtl):
    expected = text.split()
    for row in reading_rows(words, rtl):
        read = [read_word(word, rtl) for word in row]
        for start in range(len(row) - len(expected) + 1):
            end = start + len(expected)
            if read[start:end] == expected:
                return row[start:end]
    return []


@unittest.skipUnless(pdf_words.AVAILABLE, "pdftotext is not installed")
class FoundGapsPdf(unittest.TestCase):
    def assert_lists_on_page(self, language, columns, *, last_page=False):
        rtl = language == "ar"
        name = "leave-request-ar" if rtl else "leave-request"
        data = support.example_data(name)
        for key, items in zip(LISTS, columns):
            data["project"][key] = items
        with tempfile.TemporaryDirectory() as folder:
            result, output = run_tool(folder, data)
            self.assertEqual(result.returncode, 0, result.stderr)
            drawn = pdf_words.pages(output)
            self.assertEqual(pdf_words.problems(output, trim=0.2 if rtl else 0.0), [])
        count = 4 if last_page else 3
        self.assertEqual(len(drawn), count)
        cover_line = ("كل خطوة وكل قرار، في %d صفحات." if rtl
                      else "Every step and every decision, on %d pages.") % count
        self.assertTrue(boxes_for(drawn[0][2], cover_line, rtl), cover_line)

        page_index = len(drawn) - 1 if last_page else 1
        width, _, words = drawn[page_index]
        headings = []
        for title, items in zip(TITLES[language], columns):
            pages_with_title = [index for index, (_, _, page_words) in enumerate(drawn)
                                if boxes_for(page_words, title, rtl)]
            self.assertEqual(pages_with_title, [page_index] if items else [], title)
            if items:
                boxes = boxes_for(words, title, rtl)
                start = min(width - word[2] if rtl else word[0] for word in boxes)
                headings.append((start, max(word[3] for word in boxes), items))
        starts = [start for start, _, _ in headings]
        self.assertEqual(starts, sorted(set(starts)), "lists follow the page's reading direction")
        if len(starts) == 3:
            self.assertAlmostEqual(starts[1] - starts[0], starts[2] - starts[1], places=3)

        above_lists = ("قبل البناء" if rtl else "Before it is built") if last_page else data["parts"][0]["title"]
        boxes = boxes_for(words, above_lists, rtl)
        self.assertTrue(boxes, above_lists)
        self.assertGreater(min(bottom for _, bottom, _ in headings), max(word[3] for word in boxes))

        footer_top = max(word[1] for word in words)
        for (left, heading_bottom, items), right in zip(headings, starts[1:] + [width]):
            body = [word for word in words if heading_bottom < word[1] < footer_top
                    and left <= (width - word[2] if rtl else word[0]) < right]
            rendered = [read_word(word, rtl) for row in reading_rows(body, rtl) for word in row]
            self.assertEqual(rendered, " ".join(items).split())

    def test_one_two_and_three_lists_draw_under_the_map_in_both_languages(self):
        for language, (gaps, assumptions, questions) in SHORT_LISTS.items():
            cases = ((gaps, [], []), (gaps, assumptions, []),
                     (gaps, [], questions), (gaps, assumptions, questions))
            for columns in cases:
                with self.subTest(language=language, lists=[key for key, items in zip(LISTS, columns) if items]):
                    self.assert_lists_on_page(language, columns)

    def test_taller_lists_get_the_last_page_in_both_languages(self):
        for language, (_, assumptions, questions) in SHORT_LISTS.items():
            with self.subTest(language=language):
                self.assert_lists_on_page(language, ([LONG_GAP[language]] * 8, assumptions, questions),
                                          last_page=True)
