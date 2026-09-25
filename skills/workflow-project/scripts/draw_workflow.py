#!/usr/bin/env python3
"""Draws a project's workflow PDF from a workflow file.

    python3 draw_workflow.py workflow.json -o "Project - Workflow.pdf"
    python3 draw_workflow.py workflow.json --check        (checks only, writes nothing)

Needs Python 3.9+ and the reportlab package. The file format is in references/workflow-format.md.
Whose name, logo and website the PDF carries comes from assets/brand.json.
Exit codes: 0 drawn or checked, 1 the workflow needs changes (each one is listed), 2 bad command,
3 reportlab is missing.
"""

import argparse
import os
import sys

sys.dont_write_bytecode = True          # keep the skill folder free of cache files
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Draw a project's workflow PDF from a workflow file.")
    parser.add_argument("workflow", nargs="?", help="the workflow file (JSON)")
    parser.add_argument("-o", "--output", help='where to write the PDF (default: "<Project> - Workflow.pdf" beside it)')
    parser.add_argument("--check", action="store_true", help="check the workflow and its layout without drawing")
    parser.add_argument("--version", action="store_true", help="print the tool's version")
    args = parser.parse_args(argv)

    try:
        import reportlab  # noqa: F401
    except ImportError:
        print("The drawing tool needs the Python package reportlab. Install it with:  pip install reportlab",
              file=sys.stderr)
        return 3

    from workflow_tool import VERSION, brand, layout, model, pages, theme

    if args.version:
        print("workflow-project drawing tool %s" % VERSION)
        return 0
    if not args.workflow:
        parser.print_usage(sys.stderr)
        return 2

    theme.register_fonts()
    try:
        owner = brand.load()
        project = model.load(args.workflow)
    except model.WorkflowError as err:
        return _refuse(err.problems)

    diagrams, problems = [], []
    for part in project.parts:
        try:
            room = pages.diagram_room(part, len(project.parts))
            diagrams.append(layout.lay_out(part, pages.FRAME_W, room))
        except model.WorkflowError as err:
            problems += err.problems
    problems += pages.preflight(project, owner)
    if problems:
        return _refuse(problems)

    steps = sum(1 for p in project.parts for n in p.nodes if n.type == "step")
    decisions = sum(1 for p in project.parts for n in p.nodes if n.type == "decision")
    print("Checked: %s, %s, %s, %s." % (_count(len(project.parts), "part"),
                                           _count(len(project.actors), "person or system", "people or systems"),
                                           _count(steps, "step"), _count(decisions, "decision")))
    print("Every arrow goes around the boxes, and every word fits its shape.")
    if args.check:
        print("Ready to draw.")
        return 0

    output = args.output or os.path.join(os.path.dirname(os.path.abspath(args.workflow)),
                                         "%s - Workflow.pdf" % _safe_name(project.name))
    folder = os.path.dirname(os.path.abspath(output))
    if not os.path.isdir(folder):
        print("The folder for the PDF does not exist: %s" % folder, file=sys.stderr)
        return 2
    found = pages.build(project, diagrams, output, owner)
    print("Drew %d pages: %s" % (found["total"], os.path.abspath(output)))
    return 0


def _refuse(problems):
    print("Not drawn yet. Change these in the workflow file, then run again:", file=sys.stderr)
    for number, problem in enumerate(problems, 1):
        print("  %d. %s" % (number, problem), file=sys.stderr)
    return 1


def _count(number, one, many=None):
    return "%d %s" % (number, one if number == 1 else (many or one + "s"))


def _safe_name(name):
    return "".join(ch for ch in name if ch not in '\\/:*?"<>|').strip() or "Project"


if __name__ == "__main__":
    sys.exit(main())
