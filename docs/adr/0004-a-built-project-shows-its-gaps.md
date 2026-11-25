# 0004: A built project shows its gaps

- Status: accepted (by the owner, 2026-11-25).
- Deciders: the owner for the workflow and Board look, Codex for the implementation.

## Context

The skill can draw a built project. Before developing a new feature or changing how the project
works, the person doing the work needs a map of today's flow and the gaps found while mapping it.
The tool requires every node to be reachable and every path to have a way to finish. Some real
gaps, like a screen nobody can reach, cannot be drawn under those rules. Redrawing one workflow
after a change would also lose the starting point.

## Decision

1. Draw how the built project works today. Use the existing stop when a path ends with nothing
   happening. Record confirmed gaps in `found_gaps` and keep what could not be confirmed in
   `open_questions`. A gap the tool cannot draw goes in the list alone.
2. Draw the gaps in the same style as the other lists. Keep the graph and drawing checks.
3. Hand over today's workflow first. The owner decides what work to take on. After the change is
   agreed, keep today's JSON and PDF and draw a second workflow for the agreed change.

## Options considered

| Option | Why it was passed over |
|---|---|
| Relax the graph checks for built projects | Both kinds of project need a readable map. The gap list can name an unreachable screen or a loop with no way out. |
| Mark changed steps with a new shape or colour | The two PDFs show the two states using the Board look the owner already chose. |
| Replace today's workflow after the change | Keeping both pairs gives the owner the map of what existed before the change. |

## Consequences

- The PDF shows where a confirmed path stops and lists gaps that cannot be drawn.
- The list covers only the gaps found while mapping how the project flows, so a full bug search,
  testing and review remain separate work.
- Files without gaps keep their existing page layout.
