# 0002: Arabic is drawn by the tool itself, on a mirrored page

- Status: accepted (the owner chose one skill with a language setting, Arabic first, and the font, on
  2026-10-03; how it is built is the builder's decision inside that)
- Deciders: the owner (one skill not two, Arabic first, Noto Naskh Arabic); Claude (builder) for the rest.

## Context

The owner wants the workflow PDF in Arabic, and later in other languages, from every agent. reportlab
draws a string left to right, one glyph per character: it does not join Arabic letters and does not order
a right-to-left line. Its own answer is two add-ons: `uharfbuzz` (joining) and `rlbidi` (ordering).
On the owner's Mac, on 2026-10-03, `rlbidi` could not be found to install at all, and `uharfbuzz` installed
only on Python 3.12, not on the Mac's own Python 3.9. `docs/scope.md` promises "Python 3.9+ and `reportlab`
are the only needs".

## Decision

1. **One skill, a `language` field.** Every fixed sentence lives in `assets/languages/<code>.json`.
2. **The tool joins and orders Arabic itself** (`workflow_tool/script.py`, about 150 lines, no dependency).
   Each letter is swapped for its start, middle, end or alone shape from Unicode's Arabic Presentation
   Forms-B, which Python's own `unicodedata` describes and which Noto Naskh Arabic contains. A small
   ordering rule keeps numbers and Latin words left to right inside a right-to-left line.
3. **A right-to-left page is the English page, mirrored** (`workflow_tool/mirror.py`). The canvas flips
   the page and flips words and pictures back. Layout and arrow routing do not know the direction.
4. **Arabic words use Noto Naskh Arabic; Latin words and numbers keep Plus Jakarta Sans.** Arabic is drawn
   12% larger than the Latin beside it, and small labels 20% larger again, because Naskh letters are small
   for their size and cannot be capitalised or spaced apart.

## Options considered

| Option | Why not |
|---|---|
| A second, Arabic-only skill | Two skills answering one request; every fix made twice; a third copy for the next language. |
| reportlab's add-ons (`uharfbuzz` + `rlbidi`) | Not installable everywhere (see Context), so some agents would refuse to draw. Breaks "same output everywhere". |
| Use the add-ons when present, the built-in joining otherwise | Two different drawings of the same file, depending on the machine. |
| A right-to-left version of each page | Five pages and the swimlane, each written twice, and each able to drift from its twin. |

## Consequences

- No new install; the same Arabic PDF on every agent.
- **Vowel marks (tashkeel) are placed by a rule of thumb**: centred on their letter, at the height the font
  gives them. A text-shaping library would place them exactly. Workflow steps are short phrases that
  rarely carry marks. If exact marks are ever needed, the place to change is `mirror.MirrorCanvas`.
- **Arabic only, not every Arabic-script language.** Persian and Urdu letters have no shapes in
  Presentation Forms-B; they are refused by name instead of being drawn unjoined.
- The skill grows by about 1 MB (four font files).
- The language is one setting for the whole run (`language.use`), not passed from function to function.
  That is enough while one run draws one PDF.
- The brand name and website are still checked against the Latin font only.
