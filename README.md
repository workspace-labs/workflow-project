# workflow-project

An agent skill that makes a project's **workflow**: a clean, professional PDF showing how a new
project (or a new skill) works from A to Z, before anyone builds it. Companies and government
offices expect the builder to hand one over; this skill makes the same document on every agent.

**Version 0.2.0** · built 2026-09-25 · not committed, not published (the owner decides both).

## What the PDF holds

1. **Cover**: the project's name, who it is for, date, version, status.
2. **The project on one page**: what it is, who takes part, the main parts, what was assumed, what is still to confirm.
3. **The map** (when there is more than one part): every part as one box, in order, with the page it is on.
4. **For each part**: a swimlane page (one column per person or system; a blue line for the normal path;
   dashed grey lines for the other paths; gold diamonds for decisions; a red ring where it stops early),
   then a table of every step (who, what happens, what comes out).
5. **End card**: the logo, the project's name, two plain lines, `workspace-labs.net`.

The page count grows with the project. There is no dashboard, no number tiles, no charts. The look is the
WorkSpace Labs video look (Plus Jakarta Sans, light ground, one blue accent word).

## How it works

1. The agent **understands** the project first: it asks, then reads it back until the person says yes.
2. It **maps** the workflow into a small JSON file (format: `skills/workflow-project/references/workflow-format.md`).
3. The **drawing tool** checks the file and draws the PDF. It refuses anything messy (a word that does not
   fit, an arrow that would cross a box, a part too long for a page) and says exactly what to change.
4. The agent looks at every page and hands it over.

On the Workspace board, Grok makes it while planning a new project or skill; that board rule lives in
the Workspace app's `GROK.md`, so the skill itself stays general for every agent.

## Install

The skill is the folder `skills/workflow-project/`. Every agent reads the same folder.

| Agent | How |
|---|---|
| Claude Code and Grok (this Mac) | `~/.claude/skills/workflow-project` is a link to `skills/workflow-project/` here, so changes here are live. |
| Codex (this Mac) | the Mac's `sync-codex-skills.sh` copies it into `~/.codex/skills/` at the next Claude Workspace or cockpit start. |
| Claude app (chat and Cowork) | upload `dist/workflow-project.zip`: **Customize → Skills → upload**. |
| ChatGPT | same format. Where your plan offers **Skills → Create → Upload from your computer**, upload the same zip. Not tested yet. |
| Another computer | copy `skills/workflow-project/` into that agent's skills folder. |

Rebuild the zip after any change:

```bash
cd ~/Desktop/Projects/workflow-project
rm -f dist/workflow-project.zip && mkdir -p dist
(cd skills && zip -r -X ../dist/workflow-project.zip workflow-project -x '*/__pycache__/*' '*.pyc' '*.DS_Store')
```

## Your own brand

Every PDF carries a name, a logo and a website, WorkSpace Labs by default. They come from one small file,
`skills/workflow-project/assets/brand.json`:

```json
{"name": "WorkSpace Labs", "accent": "Labs", "website": "workspace-labs.net", "logo": "logo-mark.png"}
```

Another user replaces it with their own and puts their logo (PNG or JPEG) beside it. `accent` is the one
word of the name drawn in blue (`""` for none); `logo` and `website` may be `""`. The rest of the look (font,
colours, layout) stays the same for everyone. A broken brand file is refused before anything is drawn.

## Run the drawing tool yourself

```bash
python3 skills/workflow-project/scripts/draw_workflow.py skills/workflow-project/examples/building-permit.json -o "Building Permit - Workflow.pdf"
python3 skills/workflow-project/scripts/draw_workflow.py my-workflow.json --check     # checks only
```

It needs Python 3.9 or newer and the `reportlab` package (already in Claude's and ChatGPT's sandboxes).

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

## Credits and licence

Plus Jakarta Sans is by Tokotype, under the SIL Open Font License 1.1 (see `CREDITS.md`). The logo is
WorkSpace Labs' own artwork. The project's own licence is not chosen yet.
