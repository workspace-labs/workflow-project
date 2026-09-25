# Scope

## What it does

- Before a **new project** or a **new skill** is built, the agent understands it, then produces its
  workflow: a PDF showing how it works from A to Z.
- Works for every agent the owner uses: Claude Code, Claude chat and Cowork, Codex, Grok, ChatGPT, and
  agents at work. On the Workspace board, the planner (Grok) makes it at the plan stage; there is no new
  app window.
- One fixed look everywhere: the WorkSpace Labs video look. Whose name, logo and website the PDF carries
  comes from `assets/brand.json` (WorkSpace Labs by default), so another user can put their own brand on it.

## What it will NOT do

- No dashboards, number tiles or charts (the owner's rule).
- No workflow for fixes, small changes or rule changes.
- No build plan (stages, dates, who builds what). The workflow shows how the finished project works.
- No drawing by hand when the tool refuses: the agent changes the file, or splits the part.
- No network access, no data collection, no new service: the tool reads one file and writes one PDF.
- Not Claude Code's multi-agent `Workflow` tool.

## How good it must be

- **Clean or refused.** No arrow ever crosses a box, a label or another arrow's line; every word fits its
  shape; nothing is cut off. When that cannot be done, the tool refuses with a numbered reason instead.
- **Plain words.** Every refusal says what to change, in a sentence a non-developer can follow.
- **Same output everywhere.** Python 3.9+ and `reportlab` are the only needs; the font and logo travel
  inside the skill.
- **Fast.** A four-part, eleven-page document draws in under a second on the owner's Mac.
- **Proven.** Every rule above has an automated check, and a broken copy of the tool is caught.
