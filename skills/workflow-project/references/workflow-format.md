# The workflow file

One JSON object with `project` and `parts`. The drawing tool refuses any unknown field by name, so
a typo never goes unnoticed.

## Contents

- A complete small file
- `project`
- `parts`
- Nodes
- Decisions
- Loops, jumps and joins
- How it is drawn
- What the tool refuses

## A complete small file

```json
{
  "project": {
    "name": "Visitor Pass",
    "accent": "Pass",
    "client": "Head office",
    "summary": "Visitors ask for a pass online; security approves it and the visitor gets a QR code.",
    "actors": [
      {"name": "Visitor", "role": "Asks for the pass and shows the QR code."},
      {"name": "Security", "role": "Approves or refuses the pass."}
    ],
    "open_questions": ["Can a pass be used on more than one day?"]
  },
  "parts": [
    {
      "title": "Get a pass",
      "summary": "From the request to the QR code.",
      "lanes": ["Visitor", "Security"],
      "nodes": [
        {"id": "start", "type": "start", "lane": "Visitor", "title": "Plans a visit"},
        {"id": "ask", "type": "step", "lane": "Visitor", "title": "Fills in the form", "detail": "name, date, host", "result": "A pass request"},
        {"id": "ok", "type": "decision", "lane": "Security", "title": "Approved?",
         "branches": [{"label": "Yes", "to": "qr"}, {"label": "No", "to": "refused"}]},
        {"id": "refused", "type": "stop", "lane": "Visitor", "title": "Refused", "detail": "the reason is given"},
        {"id": "qr", "type": "step", "lane": "Security", "title": "Sends the QR code", "result": "The pass"},
        {"id": "done", "type": "end", "lane": "Visitor", "title": "Has the pass"}
      ]
    }
  ]
}
```

## `project`

| Field | Needed | What it is |
|---|---|---|
| `name` | yes | The project's name, up to 70 characters. It is the cover's title. |
| `accent` | no | One word of the name. Still accepted so older files keep working; the Board look does not draw it. |
| `language` | no | `"en"` (the default) or `"ar"`. With `"ar"`, write the whole file in Arabic: the tool writes its own words in Arabic and mirrors every page, so the first lane is on the right. |
| `summary` | yes | What it is, in two or three sentences (up to 700 characters). |
| `actors` | yes | Every person, team or system: `[{"name": "...", "role": "..."}]`. Names up to 28 characters; they are the lane names. |
| `client` | no | Who it is for ("Prepared for …"). |
| `prepared_by` | no | Default: the brand's name from `assets/brand.json`. |
| `date` | no | `YYYY-MM-DD`. Default: today. |
| `version` | no | Default: `1.0`. |
| `status` | no | Default: `Draft for review`, in the workflow's language. |
| `assumptions` | no | Up to 8 short sentences: what you assumed. |
| `open_questions` | no | Up to 8 short sentences: what is still to confirm. |

## `parts`

The main stages, in the order they happen. Each part becomes one page: its board, with the strip of
what comes out under it.

| Field | Needed | What it is |
|---|---|---|
| `title` | yes | A few words, up to 64 characters ("Check the documents"). It must fit one line at the top of its page. |
| `summary` | no | One sentence under the title (up to 220 characters). |
| `lanes` | yes | 1 to 5 actor names, top to bottom. Put whoever starts it first. Every lane must be used. Two to four read best. |
| `nodes` | yes | The start, steps, decisions and ends, **in the order they happen**. |

## Nodes

Every node has `id` (letters, numbers, `-` or `_`, unique in its part), `type`, `lane` and `title`.

| `type` | Extra fields | Drawn as |
|---|---|---|
| `start` | `next` | A ring and "Starts when: …". Exactly one, first in the list. |
| `step` | `detail`, `result`, `next` | A box with its number. `detail` is the small second line; `result` is "what comes out", written under the board beside the step's number. |
| `decision` | `branches`, `detail` | An amber box holding the question, marked "?". Under the board: where each answer leads. |
| `stop` | `detail` | A red ring and "Stops: …": it ends early here (refused, closed, cancelled). |
| `end` | `detail`, `to_part` | A dark dot and "Ends: …": it finishes here. `to_part: 2` adds "→ Part 2". At least one per part. |

- A box is as wide as its column: wide with few columns, narrow with eight. A title may take up to five
  lines and a detail four, but a few words read best; a word wider than the box is refused.
- A question is a few words: "Approved?", "Over 4 floors?".
- A `result` is a few words: it must fit under its column in six lines.

## Decisions

```json
{"id": "paid", "type": "decision", "lane": "Finance", "title": "Paid?",
 "branches": [{"label": "Yes", "to": "approve"}, {"label": "No", "to": "remind"}]}
```

- 2 or 3 answers. Labels up to 14 characters ("Yes", "No", "Needs info").
- **The first answer is the normal path.** Following the first answer of every decision from the start
  must reach an `end` without going back: that path is drawn blue.

## Loops, jumps and joins

- After a `start` or `step`, the flow goes to the **next node in the list**, unless `next` says otherwise.
- A loop: `{"id": "remind", ..., "next": "pay"}` sends the flow back to an earlier node.
- A join: two paths may lead to the same node (a decision's answer and a step's `next`).
- List a side path's steps right after the decision that starts it, then the normal path's next step.

## How it is drawn

- The page lies sideways. Every lane is a row; time runs across, column by column, in list order.
- A node sits **under** the one before it, in the same column, when the work passes straight down to a
  lower lane. Otherwise it opens a new column. A decision with three answers always opens one.
- A start, stop or end that belongs to one step in its own lane is a **flag** on that step's box, with
  no arrow: "Starts when" above the box, "Stops" or "Ends" below it. Otherwise it is a small pill with
  its own arrow; a stop or end that only one decision leads to sits in that decision's column.
- Under the lanes, a strip says what comes out of each column's steps, and where each answer leads.
- Arrows are right-angled lines routed around every box. Blue is the normal path; dashed grey is every
  other path. A step only another path reaches has a dashed edge.
- A page holds about 8 columns, and as many lanes as their boxes leave room for: with 4 or 5 lanes keep
  titles and details short.

## What the tool refuses

It never draws something messy. Each refusal is a numbered sentence saying what to change:

- a missing or unknown field, a duplicate id, a `next` or answer pointing to no node;
- a lane that is not an actor, an empty lane, more than 5 lanes;
- no start, a start that is not first, no end, a node nothing leads to, a loop with no way out;
- a normal path (first answers) that goes back or finishes at a stop;
- words that do not fit their shape, or a part too long or too tall for one page (split it);
- a single word too wide for where it is drawn: a lane name, a box, the strip under the board, the
  cover, the map or the footer (add a space, or shorten it);
- an arrow that cannot be drawn without crossing a box or touching another arrow (reorder the nodes,
  move a step to another lane, or split the part);
- characters the font cannot draw, and Arabic letters in a workflow that is not Arabic: anything but English in an English workflow; in an Arabic one, anything
  but Arabic letters, Latin letters and numbers (Persian and Urdu letters are refused).
