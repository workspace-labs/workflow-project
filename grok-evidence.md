# Grok evidence — workflow-project

Status: FIXED IN THE WORKING TREE, NOT COMMITTED

Date: 2026-09-28. Examiner and fixer: Grok. Starting commit `5f9c543` on `main`. Tool version is now `0.2.1`. Nothing was committed or pushed.

## Bug 1 — the date followed the computer's language

`nice_date` in `skills/workflow-project/scripts/workflow_tool/pages.py` used `strftime("%B")`. That month name is the computer's language, not English. The font check ran earlier, while the date was still `2026-09-25`, so the tool said every word fit and then drew the month anyway.

A normal run on this Mac stayed in the C locale, so the 68 tests still printed "September". Once the process language was set:

- French printed "25 septembre 2026" on the cover and in the footer.
- Arabic printed "25", empty boxes, "2026". The font has no Arabic. `pdftotext` showed `DATE  25         2026`.
- Russian and Hindi months were the same kind of failure.

The skill promises one English PDF everywhere, and that letters the font cannot draw are refused.

**Fix.** `nice_date` now uses a fixed English month list. A valid `2026-09-25` is "25 September 2026" in the C locale, in French, in Arabic, and in Russian. A date that is not `YYYY-MM-DD` is still shown as written. The version stays 0.2.1. The workflow example fix below is unchanged.

## Bug 2 — "build ours" died at the same stop as "install it"

In `examples/workflow-project.json`, "One exists?" → Yes went to one red stop, "You choose / install it, or build ours". A stop has no way out, so choosing to build never reached the questions or Part 2. The skill says: if one exists, let the person choose, and map only a skill that will be built.

Putting the new choice on the old page made an arrow cross a box. "Asks the questions" already had three arrows in, and a fourth cannot enter. The first part is now two parts, which is what the tool asks for when a page cannot hold the arrows.

**Fix.**

- Part 1, "What was asked". A new project (not a new skill) is the blue path and goes straight to "Ready to ask → Part 2". A new skill is looked up. "One exists?" → No also goes on. "One exists?" → Yes asks "Build ours?". Yes goes on to Part 2. No stops at "Install it".
- Part 2, "Say it back". The questions, the read-back, and "That's it?".
- Map and draw now continues to Part 4. The PDF is 10 pages. The cover and the footer say Version 0.2.1. They used to say 0.1.

Checked on the drawn page: the blue line reaches "Ready to ask", the dashed Yes from "Build ours?" reaches that same end, and the red stop is only "Install it". The map's page numbers are 4, 6, 7, and 9, which are the pages those parts start on.

## Codex re-review — tests only

Codex confirmed both functional fixes. Two test findings stayed open. Only `tests/test_render.py` and this file changed for them. `pages.py`, the example, and version 0.2.1 were left as they were.

### F07 — the PDF test drew in another process

`test_the_drawn_date_stays_english` called `locale.setlocale` in the test process, then `subprocess` started a new Python to draw. That process does not inherit `setlocale`. Codex put the old `strftime("%B")` formatter back in a disposable copy and this PDF test still passed.

The PDF test now calls `locale.setlocale` and `draw_workflow.main` in the same process, for `ar_AE.UTF-8` and `fr_FR.UTF-8`. It reads the PDF back with `pdftotext` and requires "25 September 2026" on the cover and on every inner-page footer (the line that says `Page N of M`). `setUp` saves the process locale and `tearDown` puts it back. The small `nice_date` helper test is still there. It is not the proof below.

Proof, disposable copy only (`/tmp/wf-old-formatter.MJJPn0`), repo `pages.py` left on the English month list. Command: `WORKFLOW_PROJECT_SKILL_DIR=<that copy> python3 -B -m unittest test_render.DatesStayEnglish.test_the_drawn_date_stays_english` from `tests/`.

- Old `strftime("%B")` formatter: **FAILED**, exit 1. French cover line was `25 septembre 2026`. Arabic cover line was `25 2026` (the month was blank).
- Fixed formatter, full suite: **71 tests, OK**.

### F08 — no Poppler used to raise FileNotFoundError

The PDF test called `pdftotext` with `check=True`. A machine without Poppler got `FileNotFoundError` instead of a skip. The other PDF checks use `pdf_words.AVAILABLE` and skip with "pdftotext is not installed".

This test now has `@unittest.skipUnless(pdf_words.AVAILABLE, "pdftotext is not installed")`. With Poppler on `PATH` the assertions run (the 71-test run above). With `PATH=/usr/bin:/bin`, so `pdftotext` is not found:

```
test_the_drawn_date_stays_english ... skipped 'pdftotext is not installed'
OK (skipped=1)
```

Exit 0. The helper test does not use Poppler and is not skipped by this decorator.

## What the checks say now

`python3 -B -m unittest discover -s tests` from the repo — **71 tests, OK**.

The picture at the top of `README.md` is still the previous drawing. It was not regenerated.

## Not done

Not committed. Not pushed. The installed copies were updated from this tree so Claude and Codex load 0.2.1: `~/.agents/skills/workflow-project` (Claude's `~/.claude/skills/workflow-project` is a link to it) and `~/.codex/skills/workflow-project`. `dist/workflow-project.zip` was rebuilt. The owner still has to upload that zip for the Claude app, and to commit and push when they want GitHub updated.
