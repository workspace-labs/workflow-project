# 0001: A small Python tool with reportlab draws the PDF

- Status: accepted (builder's decision inside the owner's approved design, 2026-09-25)
- Deciders: Claude (builder); the owner approved "the skill carries its own drawing tool so every agent
  draws the same PDF" in the read-back.

## Context

The owner wants the same workflow PDF from Claude Code, Claude chat and Cowork, Codex, Grok and ChatGPT.
Those agents share almost nothing except Python: chat sandboxes have Python and `reportlab`, but no
Chrome, no Graphviz and no Node guaranteed. The approved look (option A) needs exact fonts, colours
and clean right-angled arrows.

## Decision

The skill carries `scripts/draw_workflow.py`, written for Python 3.9+ with `reportlab` as the only
dependency. It lays out the swimlane itself (one row per node, arrows routed around every box by a small
search), and it embeds static Plus Jakarta Sans TTF files shipped inside the skill.

## Options considered

| Option | Why not |
|---|---|
| HTML + a headless browser to print the PDF (how the first sample was drawn) | Exact CSS look, but no browser exists in chat sandboxes, so agents would draw different things. |
| Graphviz or Mermaid layout | Not installed everywhere; their own look fights the house look; swimlanes are weak in both. |
| Each agent draws its own SVG or PDF from written rules | Every agent would draw a different diagram; nothing checks that arrows avoid boxes. |

## Consequences

- `reportlab` must be present (it is in the Claude and ChatGPT sandboxes; on a Mac it is one install).
- The fonts ship as five static TTF files (about 645 KB) because reportlab cannot use the app's variable
  woff2 file. They are the official Tokotype cuts, SIL Open Font License, credited in `CREDITS.md`.
- The layout is ours to maintain: `layout.py` places nodes, `routing.py` routes arrows. Both are covered
  by tests that check the drawing's geometry, not just that a file appears.
- A part has a page-size limit (about 9 to 10 rows, 5 lanes); bigger parts are split, as the owner asked.
