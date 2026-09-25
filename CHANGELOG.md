# Changelog

All notable changes to this project. The version is `VERSION` in
`skills/workflow-project/scripts/workflow_tool/__init__.py`.

## [0.2.0] - 2026-09-25

### Published on GitHub

The accepted 0.2.0, unchanged, published at `workspace-labs/workflow-project`: a README for readers (install
for every agent, no paths from the builder's own machine), the MIT licence, and a picture drawn from the
included example's real pages. The fonts keep their SIL Open Font License; the logo stays WorkSpace Labs'
own. The skill folder is byte-identical to the reviewed and accepted version, so the version stays 0.2.0.

### Fix round 2 (Codex re-review 1: F03 only, the owner's go)

The version stays 0.2.0 (the owner's Rule 27). Tests only: the drawing tool is unchanged, so the skill
folder, and the zip's contents, are byte-identical to fix round 1.

- F03, brand half: new checks hold the brand width refusals in place. A brand name of 40 "W"s (as long as
  the brand file allows) is too wide for the bar at the top of the pages, and a 60-character website is too
  wide for the last page. Each alone, and both together, is refused in both routes (draw and `--check`):
  exit 1, a numbered reason naming the field, no traceback, no "Ready to draw.", and no PDF written.
  Brands that fit (ours, another user's, and empty or missing optional fields) are drawn, and their pages
  are read back with pdftotext. Before, either width check could be deleted and every test still passed.
- The tests' own page reader (`tests/pdf_words.py`) now sees a word that starts left of or above the page.
  pdftotext gives such a word a negative position, which the reader used to skip, so text running off the
  left or top edge passed its check unseen (found while proving the above: the clipped website was
  invisible to it). Its own check now draws a word off the left edge and must see it.
- 68 checks (was 64). A copy with the name check switched off, one with the website check switched off,
  one with both, and one with the old reader, are each caught.

### Fix round 1 (Codex review 1, the owner's authorization for F01-F06)

The version stays 0.2.0: a fix round keeps the number it first shipped with (the owner's Rule 27).

- F01: two arrows may no longer touch, cross or run closer than 3 points; a route that would is never
  chosen, and a part with no clean route is refused. The building-permit example redraws cleanly (only
  its Part 2 page changed).
- F02: an actor name must fit its lane heading and the step table's "Who" column word by word; a single
  word too wide for either is refused with a reason (add a space, or shorten it).
- F03: every word the pages draw by hand (cover title and facts, the brand bar, the footer, the last page,
  the map cards) is measured before anything is drawn; it fits, or the workflow is refused. Map cards now
  wrap long titles and summaries instead of cutting them short with an ellipsis (the same cause); the
  footer drops the version and date before it would cut the project's name.
- F04: a lane that is not text (a list, an object, a number, null, missing) gets a numbered reason instead
  of a Python traceback.
- F05: the geometry tests no longer share the tool's own collision check: tests/geometry_oracle.py
  measures lines and boxes independently, and tests/pdf_words.py reads word positions back from the
  finished PDF with pdftotext.
- F06: a brand field of the wrong type, or too long, is refused instead of silently dropped; missing or
  "" still means none.
- 64 checks (was 49). 15 deliberately broken copies, including the reviewer's "the box check always says
  no", are each caught.

Something new, and everything old still works: your own brand.

- Whose name, logo and website the PDF carries now comes from one small file,
  `skills/workflow-project/assets/brand.json`. WorkSpace Labs stays the default, so nothing changes on the
  owner's Mac; another user replaces that file (and their logo beside it) to put their own brand on every
  workflow. The owner's click, 2026-09-25: "Their own, yours by default".
- `logo` and `website` may be empty: no logo tile and no website line are drawn.
- A broken brand file is refused in plain words before anything is drawn.
- 5 new checks (49 in all), including another user's brand drawn from a copy of the skill; a copy of the
  tool that ignores the brand file is caught.

## [0.1.0] - 2026-09-25

The first version, built from the owner's five steps in chat on 2026-09-25.

- The `workflow-project` skill: understand a new project or skill first, map it, draw its workflow PDF,
  look at every page, hand it over. For every agent; on the Workspace board the planner makes it.
- The drawing tool: a workflow JSON file in, a finished PDF out: cover, the project on one page, the map,
  one swimlane page and one table of steps per part, the end card. No dashboard.
- The swimlane look the owner picked by eye (option A of two drawn samples): lanes as columns, a blue
  normal path, dashed grey other paths, gold decisions, red stops.
- Refuses anything messy with numbered plain-language reasons: bad fields, unreachable nodes, loops with
  no way out, words that do not fit, arrows that cannot avoid a box, parts too long for a page,
  characters the font cannot draw.
- Three examples: a one-part leave request, a four-part government building permit, and the skill's own workflow.
- 44 automated checks; eight deliberately broken copies of the tool are each caught by at least one check.
