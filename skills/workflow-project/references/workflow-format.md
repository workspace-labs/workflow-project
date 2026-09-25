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
| `accent` | no | One word of the name drawn in blue. Default: the last word. |
| `summary` | yes | What it is, in two or three sentences (up to 700 characters). |
| `actors` | yes | Every person, team or system: `[{"name": "...", "role": "..."}]`. Names up to 28 characters; they are the lane names. |
| `client` | no | Who it is for ("Prepared for …"). |
| `prepared_by` | no | Default: the brand's name from `assets/brand.json`. |
| `date` | no | `YYYY-MM-DD`. Default: today. |
| `version` | no | Default: `1.0`. |
| `status` | no | Default: `Draft for review`. |
| `assumptions` | no | Up to 8 short sentences: what you assumed. |
| `open_questions` | no | Up to 8 short sentences: what is still to confirm. |

## `parts`

The main stages, in the order they happen. Each part becomes one swimlane page and its table.

| Field | Needed | What it is |
|---|---|---|
| `title` | yes | A few words, up to 64 characters ("Check the documents"). Its last word is drawn in blue. |
| `summary` | no | One sentence under the title (up to 220 characters). |
| `lanes` | yes | 1 to 5 actor names, left to right. Put whoever starts it on the left. Every lane must be used. |
| `nodes` | yes | The start, steps, decisions and ends, **in the order they happen**. |

## Nodes

Every node has `id` (letters, numbers, `-` or `_`, unique in its part), `type`, `lane` and `title`.

| `type` | Extra fields | Drawn as |
|---|---|---|
| `start` | `next` | A blue ring, its title above it. Exactly one, first in the list. |
| `step` | `detail`, `result`, `next` | A box with its number. `detail` is the small second line; `result` is "what comes out" in the table. |
| `decision` | `branches`, `detail` | A gold diamond holding the question. `detail` appears only in the table. |
| `stop` | `detail` | A red ring: it ends early here (refused, closed, cancelled). |
| `end` | `detail`, `to_part` | A dark ring: it finishes here. `to_part: 2` adds "→ Part 2". At least one per part. |

- A step's title fits two lines of its box: about 25 characters with four lanes, fewer with five.
- A question fits its diamond in one or two short lines: "Approved?", "Over 4 floors?".
- A start's title sits above its ring; a stop's or end's sits below it, in up to two short lines.

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

- Each node gets its own row, top to bottom, in list order. A stop or end that only one decision leads
  to sits beside that decision, on the same row.
- Arrows are right-angled lines routed around every box. Blue is the normal path; dashed grey is every
  other path.

## What the tool refuses

It never draws something messy. Each refusal is a numbered sentence saying what to change:

- a missing or unknown field, a duplicate id, a `next` or answer pointing to no node;
- a lane that is not an actor, an empty lane, more than 5 lanes;
- no start, a start that is not first, no end, a node nothing leads to, a loop with no way out;
- a normal path (first answers) that goes back or finishes at a stop;
- words that do not fit their shape, or a part too long for one page (split it);
- a single word too wide for where it is drawn: a lane heading, the step table's "Who" column, the
  cover, the map, the footer or the last page (add a space, or shorten it);
- an arrow that cannot be drawn without crossing a box or touching another arrow (reorder the nodes,
  move a step to another lane, or split the part);
- characters the house font cannot draw (English text only for now).
