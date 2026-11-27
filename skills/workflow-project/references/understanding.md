# Understanding it first

Ask only what you do not already know, and ask in rounds. Stop when you can replay the whole flow
from A to Z in your own words and the person says "yes, that's it". Offer clickable choices where your
tool has them, always with a way to type their own answer.

## For a new project

1. **What is it?** One sentence, and the problem it solves.
2. **Who takes part?** Every person, team and system. Each one becomes a lane.
3. **What starts it?** The moment or event that begins it.
4. **What does done look like?** The normal ending.
5. **What are the main stages, in order?** These become the parts, the A to Z.
6. **In each stage, who does what, in what order?**
7. **Every decision:** who decides, and what happens for each answer?
8. **Where can it end early?** Refused, cancelled, closed, timed out.
9. **What gets sent back to be fixed?** By whom, and is there a limit?
10. **Any deadline or wait that changes the path?** ("no reply in 14 days")
11. **What must never happen?** Rules that shape a step or a decision.
12. **What is not part of it?** So nobody draws it in.

For the optional systems page, ask which screens, services and stores the project uses.
What does each send, and which system receives it? For a built project, trace those
connections in the code before asking about any that remain unclear.

## For a project that is already built

Read first, ask second. The project answers most of the twelve questions above by itself.

1. **Read what it says about itself:** the README, the docs, any earlier workflow or app flow.
2. **Read what it really does:** the screens or routes a person meets, and the code behind each one.
   Where the docs and the code disagree, the code is how it works today; note the difference.
3. **Name the parts as its users would**, not as its folders are named.
4. **Ask the person only what the project cannot tell you:** who uses it, which paths matter most, what
   is about to change.
5. **Anything you could not confirm** goes into `open_questions`, never into an invented step.
6. **Confirmed gaps** go into `found_gaps`. Record every gap you confirm while reading: a path that ends
   with nothing happening, a decision with a missing answer, a step nobody does, a screen that promises
   something the code never does, or a screen nothing leads to. Name the part and the step or screen.

## When a built project is to be developed

Read and map today's project first. Ask what the person wants added or changed and what must keep
working as it is. Wait for their yes on today's workflow and their agreement on the change before
mapping the change.

## For a new skill

First check whether an installed skill already does the job (installed ones only: no public search); map
only one that will be built.

1. **What should switch it on?** The words and situations, and what must not switch it on.
2. **Who takes part?** The person, the agent, the skill's own tools, other agents or reviewers.
3. **What does the agent do first, next and last?**
4. **Where does it decide something?** And where does it stop and ask the person?
5. **What does it hand back, and to whom?**
6. **What must it never do?**

## Never

- Never fill something you do not know with a guess. Put what you cannot confirm in `open_questions`.
  It appears as "Still to confirm".
- Never tidy a gap away, and never report a guess as a gap.
- Never add a step, actor or decision the person did not describe or confirm.
