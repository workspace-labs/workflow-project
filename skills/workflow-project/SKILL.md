---
name: workflow-project
description: "Use when someone asks for a NEW project or a NEW agent skill (an app, website, system, tool, service or skill), before anything is built: first understand it, then produce its workflow, a professional PDF showing how it works from A to Z (the whole project as a map, then one swimlane page per part: who does what, every step, every decision, where a request stops), drawn in one fixed, clean house look by the skill's own tool. Also when asked for a project's workflow, process map or swimlane diagram. Not for fixes or small changes, not for a plan of how or when it will be built, and not for running several agents at once (some agents call that a workflow)."
---

# workflow-project

Companies and government offices expect the builder of a project to hand over its **workflow**: how
the finished project works, from A to Z. This skill makes that document, the same way on every agent.

**The PDF:** a cover · the project on one page · the map (every part as one box, with its page) ·
for each part, a swimlane page (one column per person or system, a blue line for the normal path,
dashed lines where it goes another way) followed by a table of every step · the end card. It grows
with the project: 5 pages for a small one, 40 for a big one. **No dashboard**: no number tiles, no
charts.

## When

- Someone asks for a **new project** or a **new skill**. Make the workflow before building anything.
- Someone asks for a project's workflow, process map or swimlane.
- **Not** for fixes, small changes, or a plan of the build's stages and dates. **Not** for running
  several agents at once: in some agents "use a workflow" means that, and this skill is not it.
- A workflow for this project **already exists** (for example, linked from the plan)? Read it and build
  from it. Do not draw a second one; if the project has changed, redraw the same one.

## 1. Understand it first

Never draw a guess.

- **A new skill?** First check whether one already exists: the skills already installed, and the
  public skills directory (for example `npx skills find <words>`, where that command exists). If one
  exists, tell the person and let them choose. Map only a skill that will be built.
- **Ask until you understand.** The questions are in [references/understanding.md](references/understanding.md).
  Ask in rounds: each answer can open a sharper question. If a clarifying-questions skill is installed
  (such as `prompt-guard`), use it for the asking.
- **Read it back** in your own words and wait for their yes. Anything still unknown goes into
  `open_questions`, never into an invented step.

## 2. Map it

Write the workflow as a JSON file. The full format and its rules are in
[references/workflow-format.md](references/workflow-format.md). Complete examples are in `examples/`:
`leave-request.json` (one part), `building-permit.json` (four parts, loops, five lanes) and
`workflow-project.json` (this skill's own workflow).

- **Parts** are the main stages, in the order they happen: that is the A to Z.
- **Actors** are every person, team or system, each with a one-line role. A part uses 1 to 5 of them as lanes.
- **Nodes** in the order they happen: a start, the steps and decisions, and at least one end. A stop is
  where it ends early. `next` sends the flow somewhere other than the following node (loops, jumps).
- **The first answer of every decision is the normal path**, drawn blue. It must reach an end.
- **Short words.** A step is a few words with the verb first ("Checks the form"). A question is a few
  words ("Approved?").

## 3. Draw it

```bash
python3 <this skill's folder>/scripts/draw_workflow.py workflow.json -o "<Project> - Workflow.pdf"
```

- It needs Python 3.9+ and the `reportlab` package. Claude's and ChatGPT's code sandboxes already have
  it. Anywhere else: `pip install reportlab`, and ask first if your rules say installs need approval.
- It checks everything before drawing: the file, every word against the place it is drawn, every arrow
  against every box and every other arrow. If it refuses, it lists numbered reasons. **Change exactly those in the file and run it
  again.** If a part is "too long for one page", split it into two parts.
- **Never** draw the diagram yourself to get around a refusal, and never edit the tool to silence one.
  A messy workflow is worse than none.
- `--check` runs every check without drawing.

## 4. Look at every page

Render the pages if you can (`pdftoppm -r 70 -png "<file>.pdf" page`) and look at each one. Does every
step match what the person said? Are the "No" paths all there? If you cannot render pages, say so
plainly when you hand it over.

## 5. Hand it over

- Save it where the person will find it: where their own instructions say, else inside the project's
  `docs/workflow/`, or in a chat sandbox's outputs folder. Keep the `.json` next to the PDF so it can be
  changed and redrawn later.
- Tell them in two to four plain sentences: what it shows, how many parts and pages, and what is
  still to confirm. Then **stop**. Building starts only when they say yes.

## The look is fixed; the brand is yours

The tool draws one house look: Plus Jakarta Sans, a light ground, one blue accent word, red only for a
stop, the full-grid step table, and an end card. Never restyle the PDF, swap its fonts or colours, or
add charts, number tiles or dashboards.

Whose **name, logo and website** the PDF carries comes from `assets/brand.json` (WorkSpace Labs by
default). To use your own brand, edit that file and put your logo beside it:

```json
{"name": "Acme Studio", "accent": "Studio", "website": "acme.example", "logo": "acme-logo.png"}
```

`accent` is one word of the name drawn in blue (or `""` for none); `logo` and `website` may be `""`.
Only change the brand when the person asks for their own; the tool refuses a broken brand file.

## Limits

Say these when they matter:

- English text only. Arabic and other scripts are refused for now.
- A single word too wide for where it is drawn (a lane heading, the table's "Who" column, the cover, the
  map) is refused: add a space or shorten it.
- A4 portrait. Up to 5 lanes and about 9 to 10 rows per part: split bigger parts. Up to 3 answers per
  decision.
- On the map, parts follow one another in order.

## Files

| File | What it is |
|---|---|
| `scripts/draw_workflow.py` | the drawing tool (workflow file in, PDF out) |
| `references/workflow-format.md` | the file format and its rules |
| `references/understanding.md` | the questions to ask before mapping |
| `examples/` | three complete workflow files |
| `assets/` | the Plus Jakarta Sans font (SIL Open Font License, `assets/fonts/OFL.txt`), `brand.json` and the logo |
