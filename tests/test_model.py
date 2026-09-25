"""The workflow file is read correctly, and every mistake is refused with a sentence that says what to change."""

import json
import os
import re
import tempfile
import unittest

import support
from workflow_tool import model


def problems_for(data):
    try:
        model.parse(data)
    except model.WorkflowError as err:
        return err.problems
    return []


class ExamplesLoad(unittest.TestCase):
    def test_every_example_is_valid(self):
        for name in support.EXAMPLE_NAMES:
            with self.subTest(example=name):
                project = model.parse(support.example_data(name))
                self.assertTrue(project.parts)

    def test_normal_path_is_the_first_answer_of_every_decision(self):
        project = model.parse(support.example_data("leave-request"))
        part = project.parts[0]
        main = [(e.source, e.target) for e in part.edges if e.main]
        self.assertEqual(main, [("start", "form"), ("form", "balance"), ("balance", "enough"), ("enough", "review"),
                                ("review", "approve"), ("approve", "record"), ("record", "tell"), ("tell", "done")])
        other = [(e.source, e.target) for e in part.edges if not e.main]
        self.assertEqual(sorted(other), [("approve", "refused"), ("enough", "no-days")])

    def test_steps_are_numbered_in_reading_order(self):
        part = model.parse(support.example_data("leave-request")).parts[0]
        self.assertEqual([n.number for n in part.nodes if n.type == "step"], [1, 2, 3, 4, 5])

    def test_the_format_guide_example_is_valid(self):
        guide = os.path.join(support.SKILL_DIR, "references", "workflow-format.md")
        with open(guide, encoding="utf-8") as handle:
            text = handle.read()
        block = re.search(r"```json\n(\{\n  \"project\".*?\n\})\n```", text, re.S)
        self.assertIsNotNone(block, "the guide still opens with a complete example")
        project = model.parse(json.loads(block.group(1)))
        self.assertEqual(project.name, "Visitor Pass")

    def test_defaults_fill_in(self):
        project = model.parse(support.small_workflow())
        self.assertEqual(project.accent, "Project")
        self.assertEqual(project.version, "1.0")
        self.assertEqual(project.status, "Draft for review")


class Refusals(unittest.TestCase):
    def assertRefused(self, data, fragment):
        found = problems_for(data)
        self.assertTrue(any(fragment in p for p in found), "expected %r in %r" % (fragment, found))

    def test_bad_json_names_the_line(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "broken.json")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write('{"project": {"name": "X",}\n}')
            with self.assertRaises(model.WorkflowError) as caught:
                model.load(path)
        self.assertIn("not valid JSON (line 1", caught.exception.problems[0])

    def test_missing_project_name(self):
        data = support.small_workflow()
        del data["project"]["name"]
        self.assertRefused(data, 'The project\'s "name" is missing.')

    def test_lane_must_be_an_actor(self):
        data = support.small_workflow()
        data["parts"][0]["lanes"][1] = "office"
        self.assertRefused(data, 'is not one of the project\'s actors. (did you mean "Office"?)')

    def test_node_lane_must_be_a_lane_of_its_part(self):
        data = support.small_workflow()
        support.nodes(data)[1]["lane"] = "Somebody"
        self.assertRefused(data, '"lane" must be one of this part\'s lanes')

    def test_exactly_one_start_first(self):
        data = support.small_workflow()
        support.nodes(data)[1]["type"] = "start"
        self.assertRefused(data, 'needs exactly one "start" (it has 2)')
        data = support.small_workflow()
        items = support.nodes(data)
        items[0], items[1] = items[1], items[0]
        self.assertRefused(data, 'put the "start" first')

    def test_an_end_is_required(self):
        data = support.small_workflow()
        support.nodes(data)[-1]["type"] = "stop"
        self.assertRefused(data, 'needs at least one "end"')

    def test_next_must_exist(self):
        data = support.small_workflow()
        support.nodes(data)[1]["next"] = "nowhere"
        self.assertRefused(data, '"next" points to "nowhere", but this part has no node with that id.')

    def test_a_decision_has_two_or_three_answers(self):
        for count in (1, 4):
            data = support.small_workflow()
            decision = support.nodes(data)[2]
            decision["branches"] = [{"label": "A%d" % i, "to": "answer"} for i in range(count)]
            with self.subTest(answers=count):
                self.assertRefused(data, 'a decision needs "branches": 2 or 3 answers')

    def test_ids_are_unique(self):
        data = support.small_workflow()
        support.nodes(data)[4]["id"] = "ask"
        self.assertRefused(data, 'two nodes use the id "ask"')

    def test_every_node_is_reachable(self):
        data = support.small_workflow()
        support.nodes(data).append({"id": "orphan", "type": "stop", "lane": "Office", "title": "Nobody comes here"})
        self.assertRefused(data, 'nothing leads to "orphan"')

    def test_a_loop_needs_a_way_out(self):
        data = support.small_workflow()
        items = support.nodes(data)
        items[2]["branches"] = [{"label": "Yes", "to": "answer"}, {"label": "No", "to": "retry"}]
        items[3] = {"id": "retry", "type": "step", "lane": "Customer", "title": "Tries again", "next": "again"}
        items.insert(4, {"id": "again", "type": "step", "lane": "Office", "title": "Reads it again", "next": "retry"})
        self.assertRefused(data, 'there is no way to finish')

    def test_normal_path_must_reach_an_end(self):
        data = support.small_workflow()
        support.nodes(data)[2]["branches"].reverse()
        self.assertRefused(data, 'finishes at the stop "stop"')

    def test_normal_path_must_move_forward(self):
        data = support.small_workflow()
        support.nodes(data)[2]["branches"][0] = {"label": "Yes", "to": "ask"}
        support.nodes(data)[2]["branches"][1] = {"label": "No", "to": "answer"}
        self.assertRefused(data, 'goes back to "ask"')

    def test_at_most_five_lanes(self):
        data = support.small_workflow()
        names = ["A", "B", "C", "D", "E", "F"]
        data["project"]["actors"] += [{"name": n, "role": ""} for n in names]
        data["parts"][0]["lanes"] = ["Customer", "Office"] + names[:4]
        self.assertRefused(data, "has 6 lanes; a page holds 5")

    def test_unknown_fields_are_named(self):
        data = support.small_workflow()
        support.nodes(data)[1]["detials"] = "typo"
        self.assertRefused(data, 'unknown field "detials"')

    def test_to_part_must_name_another_part(self):
        data = support.small_workflow()
        support.nodes(data)[-1]["to_part"] = 1
        self.assertRefused(data, '"to_part" must be the number of another part')

    def test_text_the_font_cannot_draw_is_refused(self):
        data = support.small_workflow()
        support.nodes(data)[1]["title"] = "يرسل السؤال"
        self.assertRefused(data, "characters the house font cannot draw")

    def test_a_lane_that_is_not_text_is_refused_not_crashed(self):
        for value in ([], {}, None, 7):
            data = support.small_workflow()
            support.nodes(data)[1]["lane"] = value
            with self.subTest(lane=value):
                self.assertRefused(data, '"lane" must be the name of one of this part\'s lanes')

    def test_an_empty_lane_is_refused(self):
        data = support.small_workflow()
        data["project"]["actors"].append({"name": "Idle", "role": ""})
        data["parts"][0]["lanes"].append("Idle")
        self.assertRefused(data, 'the lane "Idle" has nothing in it')

    def test_every_problem_is_reported_at_once(self):
        data = support.small_workflow()
        del data["project"]["summary"]
        support.nodes(data)[1]["next"] = "nowhere"
        found = problems_for(data)
        self.assertTrue(any('"summary"' in p for p in found))
        self.assertTrue(any('"nowhere"' in p for p in found))


if __name__ == "__main__":
    unittest.main()
