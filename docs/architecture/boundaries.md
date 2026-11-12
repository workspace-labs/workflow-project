# Boundaries

The drawing tool's code has one home: `skills/workflow-project/scripts/`, because the skill folder is
what gets installed and uploaded. Tests live outside it in `tests/`, so they never ship.

## One job per file

| File | Its one job | May use |
|---|---|---|
| `draw_workflow.py` | the command line: reads the arguments, loads the brand, runs the steps below in order, prints the result | everything below |
| `workflow_tool/model.py` | reads the workflow file and checks it; returns the project or plain-language problems | `theme` (font coverage only), `language` (which languages exist) |
| `workflow_tool/layout.py` | places lanes and nodes, wraps their words, sizes rows | `theme`, `routing`, `model` (its error) |
| `workflow_tool/routing.py` | routes every arrow around every box | `theme` (label size) |
| `workflow_tool/render_diagram.py` | draws a laid-out part and the key | `theme`, `paint`, `layout` (constants), `language` |
| `workflow_tool/pages.py` | assembles the whole PDF (cover, one-pager, map, parts, tables, end card) and, first, measures every word it draws by hand (`preflight`) | `theme`, `paint`, `render_diagram`, `language`, `mirror`, `richtext` |
| `workflow_tool/mirror.py` | the canvas for a right-to-left language: mirrors the whole page and draws the words the right way round | `theme` |
| `workflow_tool/richtext.py` | a paragraph for a right-to-left language: breaks lines in reading order | `theme` |
| `workflow_tool/brand.py` | reads and checks `assets/brand.json`: whose name, logo and website the PDF carries | `theme`, `model` (its error) |
| `workflow_tool/paint.py` | small canvas helpers: letter-spaced text, accent words, chips, arrows, logo tile | `theme`, `language` |
| `workflow_tool/theme.py` | the look: colours, fonts, text sizes, text measuring (in a right-to-left language, exactly as the word will be drawn) | reportlab, `language`, `script` |
| `workflow_tool/language.py` | the language of this run: its fixed words (`assets/languages/<code>.json`), months and reading direction | nothing of ours |
| `workflow_tool/script.py` | Arabic text ready to draw: letters joined, the line put in drawing order | nothing at all (Python's Unicode tables) |

## Direction

`language` and `script` are at the bottom and depend on nothing of ours; `theme` sits on them. Geometry (`layout`, `routing`) never imports
drawing code (`paint`, `render_diagram`, `pages`): it can be tested without drawing anything. Only the
command line wires the parts together.

## Right to left

A right-to-left page is the English page, mirrored: `pages.py` asks the canvas to flip each page
(`mirror.py`), and the canvas flips the words and the logo back. So `layout.py` and `routing.py` know
nothing about direction, and no page has a second version. Why it is built this way, and why without a
text-shaping library, is in `docs/adr/0002-arabic-is-drawn-by-the-tool-itself.md`.

## The look

Every colour, font and size comes from `theme.py`. Changing the look means changing that file, and the
look is the owner's decision (locked to the WorkSpace Labs video look). The brand (name, logo, website) is
not the look: it lives in `assets/brand.json`, read by `brand.py`, and `pages.build()` receives it.
