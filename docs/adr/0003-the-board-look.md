# 0003: The Board look: pages lying sideways, one page per part

- Status: accepted (the owner chose the look, the cover, its line and the Arabic font on 2026-11-12, from
  three looks drawn on a real project of his; how it is built is the builder's decision inside that)
- Deciders: the owner (the look: "A · Board", cover "Path", the line "Every step and every decision, on N
  pages.", Alexandria for English and Arabic; fewer pages; also for built projects); Claude (builder) for
  the rest.

## Context

The owner found the 0.2/0.3 PDF old and plain, hard to read, and full of gaps, and too long: a five-part
project took 13 pages, because every part had a swimlane page and then a table page that said the same
steps again. The upright page left the swimlane small and half of many pages empty.

## Decision

1. **A4 landscape. Lanes are rows; time runs across.** One page per part.
2. **The table is replaced by a strip under the lanes**, in the same columns as the boxes: what comes out
   of each step, and where each answer of a decision leads.
3. **A node shares the column of the one before it when the work passes straight down to a lower lane.**
   The first sample gave every step its own column; real titles did not fit the narrow boxes that made.
   Sharing keeps boxes wide and the arrows inside a column straight. A decision with three answers always
   opens a new column, so the arrow into it comes from the left and its three other sides stay free.
4. **Starts, stops and ends are words, not circles**: a flag on the box they belong to (no arrow), or a
   small pill with its own arrow. That saves a column for almost every start and end.
5. **Every page is drawn straight onto the canvas at fixed places** (no flowing layout). A part's page
   number is then known before drawing: cover, map page(s), then one page per part.
6. **The arrow router is the 0.2 router turned on its side**: the same clean-or-refused rule, now liking
   to leave a box on the right and arrive on the left.

## Options considered

| Option | Why not |
|---|---|
| B · Storyline: one numbered line down the page, colour says who | Easiest to read, but it is not the lane picture companies expect, and loops become "go back to step 2" in words. |
| C · Night lanes: dark pages, lanes with notes beside them | Heavy to print; the owner picked A. |
| One column per step, as first sketched | Boxes too narrow for real text at a readable size; every example was refused. |
| Shrinking the text until a part fits | "Hard to read" was one of the owner's three complaints. |
| Letting a long part run over two pages | Arrows would need off-page marks; splitting the part is simpler and reads better. |

## Consequences

- A five-part project is 7 or 8 pages instead of 13.
- **A page holds less across than the old page held down**: about 8 columns, and with 4 or 5 lanes only
  short titles. Bigger parts are refused with "split it into two parts"; the `building-permit` example
  needed that once.
- The project's `accent` word and the end card are no longer drawn; the brand's website moved to the cover.
- A single-part project still gets a map page (who takes part, the one part, the open questions).
- More than 12 parts: the cover keeps its title and facts but does not name the parts on its path.
