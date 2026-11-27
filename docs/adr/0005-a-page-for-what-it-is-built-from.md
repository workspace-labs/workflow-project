# 0005. A page for what it is built from

- Status: accepted (by the owner, 2026-11-27).
- The owner decides acceptance.

## Context

A workflow board follows people and systems through time. Clients and technical reviewers
also need to see which screens, services and stores make up a project and what passes between them.

## Decision

- Add one optional page after the last map page, before the first part. Omitting
  `project.systems` preserves the existing pages, words and page references.
- Put every system with no incoming send in the first column. Put every other system
  one column after its furthest sender. This keeps merges readable even when a send
  skips a column or the input lists receivers first. The existing mirror canvas places
  the first column on the right in Arabic.
- Each box has a unique name and may have a detail. Each forward arrow names what is sent.
  Refuse a self-send or a cycle. A request and its reply can share the same arrow label.
- Bound the input to two through eight systems and measure the actual boxes, words,
  arrowheads and paths against the available area. A diagram that cannot be placed
  cleanly receives a numbered refusal with advice to shorten its text or use fewer systems.
- Reuse the rectangle from `routing.py` and the board's word wrapping and drawing helpers.
  The board router assigns entire sides to individual arrows and places decision labels
  in pills. The systems diagram needs several arrows on the same side and unboxed words
  beside each arrow, so `systems_layout.py` chooses those paths and reserves label space.
- When arrows would cross between columns, try an outside path around the boxes using the same clearance checks.

## Consequences

The systems diagram uses the existing palette and type styles and fits on one landscape
page. A dense project may need a smaller selection of systems even within the eight-system
limit. The map cards, continuation references and footers use the shared page plan.
