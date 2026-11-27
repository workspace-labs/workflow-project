"""System definitions and their numbered refusals at the command line."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import support
from workflow_tool import model


class SystemsModel(unittest.TestCase):
    def test_systems_can_be_omitted(self):
        self.assertEqual(model.parse(support.small_workflow()).systems, [])

    def test_forward_references_and_optional_fields(self):
        data = support.small_workflow()
        data["project"]["systems"] = [
            {"name": "Form", "sends": [{"to": "Inbox", "what": "New request"}]},
            {"name": "Inbox", "detail": "Stores requests"},
        ]
        form, inbox = model.parse(data).systems
        self.assertEqual((form.name, form.detail), ("Form", ""))
        self.assertEqual([(send.to, send.what) for send in form.sends], [("Inbox", "New request")])
        self.assertEqual((inbox.name, inbox.detail, inbox.sends), ("Inbox", "Stores requests", []))

    def test_text_at_the_limits_is_accepted(self):
        data = support.small_workflow()
        data["project"]["systems"] = [
            {"name": "A" * 24, "detail": "B" * 32, "sends": [{"to": "Store", "what": "C" * 24}]},
            {"name": "Store"},
        ]
        self.assertEqual(len(model.parse(data).systems), 2)


class SystemsRefusals(unittest.TestCase):
    def assert_refused(self, systems, *messages):
        data = support.small_workflow()
        data["project"]["systems"] = systems
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder, "workflow.json")
            output = Path(folder, "workflow.pdf")
            source.write_text(json.dumps(data), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, "-B", str(Path(support.SCRIPTS, "draw_workflow.py")),
                 str(source), "-o", str(output)], text=True, capture_output=True)
            self.assertEqual(result.returncode, 1, result.stderr)
            numbered = result.stderr.splitlines()[1:]
            self.assertEqual(len(numbered), len(messages), result.stderr)
            for number, (line, message) in enumerate(zip(numbered, messages), 1):
                self.assertTrue(line.startswith("  %d. " % number), line)
                self.assertIn(message, line)
            self.assertFalse(output.exists())

    def test_unknown_keys_name_the_offending_fields(self):
        self.assert_refused(
            [{"name": "A", "detial": "Short", "sends": [{"to": "B", "what": "Order", "how": "Now"}]},
             {"name": "B"}], 'unknown field "detial"', 'unknown field "how"')

    def test_duplicate_names_are_refused(self):
        self.assert_refused([{"name": "A"}, {"name": " A "}], '"A" is listed twice')

    def test_unknown_receiver_is_named(self):
        self.assert_refused([{"name": "A", "sends": [{"to": "Gone", "what": "Order"}]},
                             {"name": "B"}], 'no system named "Gone"')

    def test_self_send_is_refused(self):
        self.assert_refused([{"name": "A", "sends": [{"to": "A", "what": "Order"}]},
                             {"name": "B"}], 'cannot send to itself')

    def test_each_system_must_send_or_receive(self):
        def advice(name):
            return '"%s" neither sends nor receives. Say what it sends or receives, or leave it out.' % name

        self.assert_refused([{"name": "A"}, {"name": "B"}], advice("A"), advice("B"))
        self.assert_refused([{"name": "A", "sends": [{"to": "B", "what": "Order"}]},
                             {"name": "B"}, {"name": "C"}], advice("C"))

    def test_second_send_to_the_same_receiver_is_refused(self):
        self.assert_refused(
            [{"name": "A", "sends": [{"to": "B", "what": "Order"}, {"to": "B", "what": "Receipt"}]},
             {"name": "B"}], '"A" sends to "B" more than once. Put both in one "what" field.')

    def test_two_and_three_system_loops_are_refused_with_reply_advice(self):
        for senders in ("AB", "ABC"):
            systems = [{"name": name, "sends": [{"to": senders[(i + 1) % len(senders)], "what": "Order"}]}
                       for i, name in enumerate(senders)]
            with self.subTest(senders=senders):
                self.assert_refused(systems, 'loop (' + ' -> '.join(senders + senders[0]) +
                                    '). Describe the reply in the "what"')

    def test_the_list_has_room_for_two_to_eight_systems(self):
        for systems in ([], [{"name": "A"}]):
            with self.subTest(systems=systems):
                self.assert_refused(systems, "at least 2 systems")
        self.assert_refused([{"name": str(i)} for i in range(9)], "use fewer systems")

    def test_field_lengths_are_reported_per_field(self):
        self.assert_refused(
            [{"name": "W" * 25, "detail": "W" * 33, "sends": [{"to": "B", "what": "W" * 25}]},
             {"name": "B"}], 'keep it to 24', 'keep it to 32', 'keep it to 24')

    def test_malformed_lists_objects_and_missing_values(self):
        for systems, message in (
                (None, 'must be a list'), ({}, 'must be a list'),
                ([9, {"name": "B"}], 'must be an object'),
                ([{"name": "A", "sends": None}, {"name": "B"}], 'must be a list'),
                ([{"name": "A", "sends": [True]}, {"name": "B"}], 'must be an object'),
                ([{"name": "A", "sends": [{"to": "B"}]}, {"name": "B"}], '"what" is missing'),
                ([{"name": "A", "sends": [{"what": "Data"}]}, {"name": "B"}], '"to" is missing'),
                ([{"sends": []}, {"name": "B"}], '"name" is missing')):
            with self.subTest(systems=systems):
                self.assert_refused(systems, message)


if __name__ == "__main__":
    unittest.main()
