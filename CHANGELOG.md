# Changelog

All notable changes to this project. The version is `VERSION` in
`skills/workflow-project/scripts/workflow_tool/__init__.py`.

## [0.4.1] - 2026-11-12

### Changed

- **A new skill is checked against the installed skills only.** The step that searched public skill
  directories (`npx skills find`) is removed from `SKILL.md`, `references/understanding.md` and the skill's
  own example workflow, matching the owner's rule of 2026-10-08. Words only: the drawing tool is unchanged.

## [0.4.0] - 2026-11-12

The Board look, chosen by the owner from three looks drawn on a real project (2026-11-12). Before 1.0.0 a
minor version may replace things: this one replaces the whole look and the page order.

### Changed

- **Pages lie sideways** (A4 landscape) and each part takes **one page** instead of two. Its lanes are rows
  and time runs across. The table of steps is gone: a strip under the lanes says what comes out of every
  step and where every answer leads. A five-part project is 7 or 8 pages where it was 13.
- **A step sits under the one before it**, in the same column, when the work passes straight down to a
  lower lane, so boxes stay wide enough for real sentences.
- **Starts, stops and ends are written out** ("Starts when: …", "Ends: …"): as a flag on a step's box when
  they belong to it, as a small pill with its own arrow when they do not. A decision is an amber box
  marked "?", no longer a diamond.
- **A dark cover** with every part on one path, and the line "Every step and every decision, on N pages."
- **The map** now carries who takes part, every part as a card with its page, and, when they fit, what was
  assumed and what is still to confirm. The separate "project on one page" and the end card are gone; when
  the two lists do not fit under the map they get a last page of their own.
- **One font, Alexandria**, for English and Arabic (the owner's pick, 2026-11-12). Plus Jakarta Sans and Noto
  Naskh Arabic are removed. Arabic is no longer drawn larger than the Latin beside it.
- The brand's website is written on the cover's top line (it was on the end card).
- The skill now also covers a project that is **already built**: read it first, then draw how it works today
  (`SKILL.md`, `references/understanding.md`).
- New limits: a page holds about 8 columns and up to 5 lanes; with 4 or 5 lanes titles must be short. The
  `building-permit` example had one part too big for the new page and is now five parts.
- The project's `accent` word is still accepted but no longer drawn.

### Fixed

- A letter standing alone is drawn as the plain letter, so Arabic no longer depends on a font carrying the
  "isolated" copies of every letter.
- Arabic letters in a workflow that is not Arabic are refused by rule, now that the font could draw them
  (unjoined and in the wrong order).

### Removed

- `workflow_tool/richtext.py` and the platypus page flow: every page is drawn at fixed places, so each
  part's page number is known before anything is drawn.

## [0.3.0] - 2026-10-03

### Added

- **Arabic.** Add `"language": "ar"` to a workflow file written in Arabic and the whole PDF is Arabic: the
  tool's own words (headings, the step table, the key, the footer, the month), and every page mirrored so it
  reads right to left: the first lane on the right, the logo on the right, the table's columns in Arabic
  order. English stays the default, and an English PDF is drawn exactly as before (the three examples were
  compared page by page, picture for picture, before and after).
- **No new install.** The tool joins the Arabic letters and orders the line itself (`script.py`), so Python
  3.9+ and `reportlab` are still the only needs. Why, and what that costs, is in
  `docs/adr/0002-arabic-is-drawn-by-the-tool-itself.md`.
- **The Arabic font is Noto Naskh Arabic**, the owner's pick from eleven candidates shown on the real page
  (2026-10-03). Latin words and numbers inside Arabic keep Plus Jakarta Sans. Four static cuts ship in
  `assets/fonts/` (about 1 MB), SIL Open Font License, credited in `CREDITS.md`.
- **Languages are files.** Every fixed sentence moved out of the code into `assets/languages/en.json`;
  `ar.json` is its translation. A check holds every language file to the same sentences and blanks.
- A fourth example, `examples/leave-request-ar.json`.

### Changed

- A workflow with Arabic words but no `"language": "ar"` is still refused, and the refusal now says to add it.

### Known limits

- Arabic vowel marks (tashkeel) are centred on their letter by a rule of thumb, not by the font's own
  placement tables. Persian and Urdu letters are refused. The brand name stays in Latin letters.

## [0.2.1] - 2026-09-28

### Fixed

- The date on the cover and in the footer is always English. It used to follow the computer's language, so a French machine printed "septembre" and an Arabic machine printed a month the font cannot draw, as empty boxes, while the tool still said every word fit.
- The skill's own workflow. If a skill already exists, "Build ours?" now goes on to the questions, and "Install it" is the stop. Before, both choices died at one stop. The first part is now "What was asked" and the questions are the next part, "Say it back", because the extra choice would not fit on the old page without an arrow through a box.

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
