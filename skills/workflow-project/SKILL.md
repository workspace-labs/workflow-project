---
name: workflow-project
description: "Use when someone asks for a NEW project or a NEW agent skill (an app, website, system, tool, service or skill), before anything is built: first understand it, then produce its workflow, a professional PDF showing how it works from A to Z (the whole project as a map, then one page per part: who does what, every step, every decision, where a request stops, what comes out), drawn in one fixed, clean house look by the skill's own tool. Also when asked for the workflow, process map or swimlane diagram of a project, including one that is ALREADY built: read it first, then draw how it really works. Not for fixes or small changes, not for a plan of how or when it will be built, and not for running several agents at once (some agents call that a workflow)."
---

# workflow-project

Companies and government offices expect the builder of a project to hand over its **workflow**: how
the finished project works, from A to Z. This skill makes that document, the same way on every agent.

**The PDF** lies sideways (A4 landscape): a cover with every part on one path · the map (who takes part,
every part as one box with its page, what was assumed and what is still to confirm) · then **one page
per part**: a board with one row per person or system, time running across, a blue line for the normal
path, dashed lines where it goes another way, and under it a strip saying what comes out of every step.
It grows with the project: 3 pages for a small one, a page more for every part. **No dashboard**: no
number tiles, no charts.

## When

- Someone asks for a **new project** or a **new skill**. Make the workflow before building anything.
- Someone asks for a project's workflow, process map or swimlane.
- The project is **already built**. Draw how it really works today, not how it was planned.
- **Not** for fixes, small changes, or a plan of the build's stages and dates. **Not** for running
  several agents at once: in some agents "use a workflow" means that, and this skill is not it.
- A workflow for this project **already exists** (for example, linked from the plan)? Read it and build
  from it. Do not draw a second one; if the project has changed, redraw the same one.

## 1. Understand it first

Never draw a guess.

- **A new skill?** First check the skills already installed. If one of them does the job, tell the
  person and let them choose: use it, or build their own. Do not search public skill directories. Map
  only a skill that will be built.
- **An already built project?** Read it before you ask anything: its README and docs, its screens or
  routes, and the code that does the work. Map what it does today. Ask the person only what the project
  cannot tell you, and put anything you could not confirm into `open_questions`.
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
- **Actors** are every person, team or system, each with a one-line role. A part uses 1 to 5 of them as
  lanes; two to four read best.
- **Nodes** in the order they happen: a start, the steps and decisions, and at least one end. A stop is
  where it ends early. `next` sends the flow somewhere other than the following node (loops, jumps).
- **The first answer of every decision is the normal path**, drawn blue. It must reach an end.
- **Short words.** A step is a few words with the verb first ("Checks the form"). A question is a few
  words ("Approved?"). A step's `result` is what comes out of it, in a few words ("A signed form").
- **Their language.** English is the default. For an Arabic workflow, write every word of the file in
  Arabic and add `"language": "ar"` to the project (example: `examples/leave-request-ar.json`). The tool
  then writes its own words in Arabic too and mirrors every page, so it reads right to left.

## 3. Draw it

```bash
python3 <this skill's folder>/scripts/draw_workflow.py workflow.json -o "<Project> - Workflow.pdf"
```

- It needs Python 3.9+ and the `reportlab` package. Claude's and ChatGPT's code sandboxes already have
  it. Anywhere else: `pip install reportlab`, and ask first if your rules say installs need approval.
- It checks everything before drawing: the file, every word against the place it is drawn, every arrow
  against every box and every other arrow. If it refuses, it lists numbered reasons. **Change exactly those in the file and run it
  again.** If a part is "too long" or "too tall" for one page, split it into two parts.
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

The tool draws one house look, the Board: pages lying sideways, a dark cover, white pages with ink-dark
rules, one blue for the normal path, amber for a question, red only for a stop, and one font, Alexandria,
for English and Arabic. Never restyle the PDF, swap its fonts or colours, or add charts, number tiles or
dashboards.

Whose **name, logo and website** the PDF carries comes from `assets/brand.json` (WorkSpace Labs by
default). To use your own brand, edit that file and put your logo beside it:

```json
{"name": "Acme Studio", "accent": "Studio", "website": "acme.example", "logo": "acme-logo.png"}
```

`accent` is one word of the name drawn in blue (or `""` for none); `logo` and `website` may be `""`. The
website is written on the cover's top line.
Only change the brand when the person asks for their own; the tool refuses a broken brand file.

## Limits

Say these when they matter:

- English and Arabic. Other languages are refused for now, and so are Persian and Urdu letters. In an
  Arabic workflow, Latin words and numbers ("PDF", "QR", "14") are fine.
- Arabic vowel marks (tashkeel) are drawn, but only roughly centred on their letter. Leave them out
  unless a word needs one.
- The brand name and website in `assets/brand.json` must be in Latin letters.
- A single word too wide for where it is drawn (a lane name, a box, the cover, the map) is refused: add a
  space or shorten it.
- A4 landscape, one page per part. A page holds about 8 columns of boxes (a step that follows the one
  above it in a lower lane shares its column) and up to 5 lanes; with 4 or 5 lanes keep titles short.
  Split bigger parts. Up to 3 answers per decision.
- On the map, parts follow one another in order.

## Files

| File | What it is |
|---|---|
| `scripts/draw_workflow.py` | the drawing tool (workflow file in, PDF out) |
| `references/workflow-format.md` | the file format and its rules |
| `references/understanding.md` | the questions to ask before mapping |
| `examples/` | four complete workflow files, one of them in Arabic |
| `assets/` | the font, Alexandria (SIL Open Font License, `assets/fonts/OFL-Alexandria.txt`), the words of each language (`assets/languages/`), `brand.json` and the logo |
