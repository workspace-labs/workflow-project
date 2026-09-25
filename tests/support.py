"""Shared test setup: finds the skill's drawing tool and gives small ready-made workflows.

Set WORKFLOW_PROJECT_SKILL_DIR to test a copy of the skill (used to prove the tests catch a broken copy).
"""

import copy
import json
import os
import sys

sys.dont_write_bytecode = True

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL_DIR = os.environ.get("WORKFLOW_PROJECT_SKILL_DIR") or os.path.join(REPO, "skills", "workflow-project")
SCRIPTS = os.path.join(SKILL_DIR, "scripts")
EXAMPLES = os.path.join(SKILL_DIR, "examples")
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

from workflow_tool import theme  # noqa: E402

theme.register_fonts()

EXAMPLE_NAMES = ("leave-request", "building-permit", "workflow-project")


def example_data(name):
    with open(os.path.join(EXAMPLES, name + ".json"), encoding="utf-8") as handle:
        return json.load(handle)


def small_workflow():
    """A valid one-part workflow that tests change one piece at a time."""
    return copy.deepcopy({
        "project": {
            "name": "Test Project",
            "summary": "A small workflow used by the tests.",
            "actors": [{"name": "Customer", "role": "Asks."}, {"name": "Office", "role": "Answers."}],
        },
        "parts": [{
            "title": "Ask and answer",
            "lanes": ["Customer", "Office"],
            "nodes": [
                {"id": "start", "type": "start", "lane": "Customer", "title": "Has a question"},
                {"id": "ask", "type": "step", "lane": "Customer", "title": "Sends the question"},
                {"id": "ok", "type": "decision", "lane": "Office", "title": "Clear?",
                 "branches": [{"label": "Yes", "to": "answer"}, {"label": "No", "to": "stop"}]},
                {"id": "stop", "type": "stop", "lane": "Customer", "title": "Asked to rewrite"},
                {"id": "answer", "type": "step", "lane": "Office", "title": "Sends the answer"},
                {"id": "end", "type": "end", "lane": "Customer", "title": "Has the answer"},
            ],
        }],
    })


def two_loops():
    """Two decisions that both send the work back up the same lane: their return arrows must not share a line."""
    data = small_workflow()
    data["parts"][0]["nodes"] = [
        {"id": "start", "type": "start", "lane": "Customer", "title": "Sends a form"},
        {"id": "receive", "type": "step", "lane": "Office", "title": "Receives the form"},
        {"id": "check", "type": "step", "lane": "Office", "title": "Checks the form"},
        {"id": "complete", "type": "decision", "lane": "Office", "title": "Complete?",
         "branches": [{"label": "Yes", "to": "review"}, {"label": "No", "to": "check"}]},
        {"id": "review", "type": "step", "lane": "Office", "title": "Reviews it"},
        {"id": "approved", "type": "decision", "lane": "Office", "title": "Approved?",
         "branches": [{"label": "Yes", "to": "end"}, {"label": "No", "to": "receive"}]},
        {"id": "end", "type": "end", "lane": "Customer", "title": "Has the answer"},
    ]
    return data


def nodes(data, part=0):
    return data["parts"][part]["nodes"]
