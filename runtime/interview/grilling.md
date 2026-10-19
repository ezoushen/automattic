# Grilling

Read before any interview's first question, including a request to "grill" a plan. The user decides principles; the agent decides the rest within them.

## Map the design tree

Map the plan as a design tree: each decision branches into those that hang off it. A
question waits until the decisions it depends on are settled. Order the tree: goal and
principles, then what may change or must keep working, then the behavior the user
would notice.

Never ask the user about implementation detail. When the tree reaches one, decide it
within the principles; a material agent choice is recorded in the ledger
([record](record.md)) and listed among the agent's decisions the user may veto, while a
routine one needs neither. Ask about a lower branch only when the
[question filter](question-filter.md) makes it a material fork.

## Work it in rounds

Each round asks the highest unsettled branches, composed as the question filter says:
one or two questions per round, in the user's terms, each with a recommendation that
"yes" accepts. After each answer, recompute which branches are now askable.

Call out a term the user uses against its definition, and add the term to the
[glossary](../domain/glossary.md) the moment it settles. When a
decision settles that qualifies for an ADR, offer an [ADR](../domain/adr.md); write it only
after the user's yes.

Finding facts is the agent's job, never the user's. Look facts up in the background,
without blocking the questions that do not depend on them.

Exhaustive depth, on an explicit request, only raises the number of questions per
round; implementation detail still stays with the agent.

## Finish

Grilling stops asking when the question filter's stop rule holds and nothing is
silently assumed, and it is done only when the user confirms a shared understanding. A plan the user calls ready, or an accepted mandate that already settles
the next step, is that confirmation; otherwise ask once, with the summary. Then close
with the [record](record.md) exit block: the user's decisions, the agent's decisions the user
may veto, and pending user actions.
