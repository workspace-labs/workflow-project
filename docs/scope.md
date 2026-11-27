# Scope

## What it does

- Before a **new project** or a **new skill** is built, the agent understands it, then produces its
  workflow: a PDF showing how it works from A to Z.
- For a built project, the agent reads it first, then draws how it works today and shows the gaps found.
  Record each confirmed gap in the list, including gaps drawn as stops.
- A project with multiple screens, services or stores can include one systems page after the map.
  It names the systems and shows what each sends to the others. A people-only process skips this page.
- When someone asks to **develop a built project** (a new feature, or a change to how it works), hand
  over today's workflow first. A development adds or changes a step, a decision, an actor or a part.
  Keep today's JSON and PDF, then draw the workflow after the agreed change.
- Works for every agent the owner uses: Claude Code, Claude chat and Cowork, Codex, Grok, ChatGPT, and
  agents at work. On the Workspace board, the planner (Grok) makes it at the plan stage; there is no new
  app window.
- English or Arabic: `"language": "ar"` in the workflow file gives the same PDF in Arabic, every page
  mirrored to read right to left. Each language is one file of words in `assets/languages/`.
- One fixed look everywhere: the Board look (pages lying sideways, one page per part; the owner's choice,
  2026-11-12; `docs/adr/0003-the-board-look.md`). Whose name, logo and website the PDF carries
  comes from `assets/brand.json` (WorkSpace Labs by default), so another user can put their own brand on it.

## What it will NOT do

- No dashboards, number tiles or charts (the owner's rule).
- No workflow for fixes, small changes or rule changes.
- No fixing the project and no bug hunt. The list covers only the gaps found while mapping how the
  project flows, so a full bug search, testing and review remain separate work.
- No build plan (stages, dates, who builds what). The workflow shows how the finished project works.
- No drawing by hand when the tool refuses: the agent changes the file, or splits the part.
- No network access, no data collection, no new service: the tool reads one file and writes one PDF.
- Not Claude Code's multi-agent `Workflow` tool.

## How good it must be

- **Clean or refused.** No arrow ever crosses a box, a label or another arrow's line; every word fits its
  shape; nothing is cut off. When that cannot be done, the tool refuses with a numbered reason instead.
- **Plain words.** Every refusal says what to change, in a sentence a non-developer can follow.
- **Short.** One page per part: no part needs a second page to be understood.
- **Same output everywhere.** Python 3.9+ and `reportlab` are the only needs; the font and logo travel
  inside the skill.
- **Fast.** A five-part, eight-page document draws in under a second on the owner's Mac.
- **Proven.** Every rule above has an automated check, and a broken copy of the tool is caught.
