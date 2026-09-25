# workflow-project

**Understand a new project first. Then hand over how it works, from A to Z.**

An agent skill that makes a project's **workflow**: a clean, professional PDF showing how a new project (or a
new skill) works, before anyone builds it. Who does what, every step, every decision, and where a request
stops early. Companies and government offices expect the builder to hand one over; this skill makes the same
document on every agent.

The skill is the folder [`skills/workflow-project/`](skills/workflow-project/): its instructions,
[`SKILL.md`](skills/workflow-project/SKILL.md), and its own drawing tool, so every agent draws the same PDF.

**Version 0.2.0**

---

## What the PDF holds

1. **Cover**: the project's name, who it is for, date, version, status.
2. **The project on one page**: what it is, who takes part, the main parts, what was assumed, what is still to confirm.
3. **The map** (when there is more than one part): every part as one box, in order, with the page it is on.
4. **For each part**: a swimlane page (one column per person or system; a blue line for the normal path;
   dashed grey lines for the other paths; gold diamonds for decisions; a red ring where it stops early),
   then a table of every step (who, what happens, what comes out).
5. **End card**: the logo, the project's name, two plain lines, and the website.

The page count grows with the project. There is no dashboard, no number tiles, no charts. The look is fixed:
Plus Jakarta Sans, a light ground, one blue accent word.

## How it works

1. The agent **understands** the project first: it asks, then reads it back until the person says yes.
2. It **maps** the workflow into a small JSON file (format: `skills/workflow-project/references/workflow-format.md`).
3. The **drawing tool** checks the file and draws the PDF. It refuses anything messy (a word that does not
   fit, an arrow that would cross a box, a part too long for a page) and says exactly what to change.
4. The agent looks at every page and hands it over.

## Install

The drawing tool needs Python 3.9 or newer and the `reportlab` package (already in Claude's and ChatGPT's
sandboxes; elsewhere `python3 -m pip install reportlab`).

**Claude Code, Codex and other agents**, in one line:

```bash
npx skills add workspace-labs/workflow-project -g
```

Or by hand, for Claude Code:

```bash
git clone https://github.com/workspace-labs/workflow-project.git
mkdir -p ~/.claude/skills
cp -R workflow-project/skills/workflow-project ~/.claude/skills/
```

**Claude app (chat and Cowork)**: make the zip, then upload it in **Customize → Skills**.

```bash
cd workflow-project
rm -f dist/workflow-project.zip && mkdir -p dist
(cd skills && zip -r -X ../dist/workflow-project.zip workflow-project -x '*/__pycache__/*' '*.pyc' '*.DS_Store')
```

**ChatGPT**: where your plan offers **Skills → Create → Upload from your computer**, upload the same zip.
Not tested yet.

Then start a fresh session and ask for a new project. The agent asks its questions first, then hands over the PDF.

## Your own brand

Every PDF carries a name, a logo and a website, WorkSpace Labs by default. They come from one small file,
`skills/workflow-project/assets/brand.json`:

```json
{"name": "WorkSpace Labs", "accent": "Labs", "website": "workspace-labs.net", "logo": "logo-mark.png"}
```

Replace it with your own and put your logo (PNG or JPEG) beside it. `accent` is the one word of the name
drawn in blue (`""` for none); `logo` and `website` may be `""`. The rest of the look (font, colours, layout)
stays the same for everyone. A broken brand file is refused before anything is drawn.

## Run the drawing tool yourself

```bash
python3 skills/workflow-project/scripts/draw_workflow.py skills/workflow-project/examples/building-permit.json -o "Building Permit - Workflow.pdf"
python3 skills/workflow-project/scripts/draw_workflow.py my-workflow.json --check     # checks only
```

## Test

```bash
python3 -m unittest discover -s tests
```

68 checks: the file rules and their plain-language refusals; the drawing's cleanliness (no arrow through a box,
no two arrows touching or crossing, nothing overlapping), judged by `tests/geometry_oracle.py`, which never
imports the tool; every word of accepted PDFs read back with `pdftotext` (skipped where poppler is missing);
the whole PDF (pages, page numbers, fonts); the brand file, including a name or website too wide for where
the pages draw it (refused in both routes); and the command line.

## Limits

- English text only. Arabic and other scripts are refused, not drawn wrong.
- A single word too wide for where it is drawn (a lane heading, the table's "Who" column, the cover, the
  map, the footer, the last page) is refused with a reason: add a space or shorten it.
- A4 portrait. Up to 5 lanes and about 9 to 10 rows per part (bigger parts are split); up to 3 answers per decision.
- Parts on the map follow one another in order.

## Layout

```
skills/workflow-project/     the skill (what gets installed)
  SKILL.md                   what the agent does
  references/                the file format, and the questions to ask first
  scripts/draw_workflow.py   the drawing tool
  scripts/workflow_tool/     its parts (see docs/architecture/boundaries.md)
  examples/                  three complete workflow files
  assets/                    the font (SIL Open Font License), brand.json and the logo
tests/                       the checks (not shipped with the skill)
docs/                        scope, architecture, decisions
```

## Update every machine

An installed copy does not update itself. After a change lands here, run the install line again on each
machine (or `git pull` in a clone the skill is linked from), then open a fresh session.

## Credits and licence

The code is under the MIT licence (`LICENSE`). Plus Jakarta Sans is by Tokotype, under the SIL Open Font
License 1.1 (see `CREDITS.md`). The logo and the WorkSpace Labs name are WorkSpace Labs' own and are not
covered by the MIT licence; replace them with yours through `assets/brand.json`.

---

<sub>by Workspace Labs</sub>
