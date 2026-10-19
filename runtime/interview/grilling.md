# Grilling

Read by every command that interviews the user, including a request to "grill" a
plan, before its first question. Grilling settles what the user must decide; the
agent decides the rest within those decisions.

## Map the design tree

Map the plan as a design tree: every decision branches into the decisions that hang
off it. A question waits until the decisions it depends on are settled. Order the
tree by what the user decides from their priorities: goal and principles, then what
may change or must keep working, then the behavior the user would notice.

Never ask the user about implementation detail. When the tree reaches one, decide it
within the principles, record it in the ledger ([record](record.md)) and list it among
the agent's decisions the user may veto. Ask about a lower branch only when the
[question filter](question-filter.md) makes it a material fork.

## Work it in rounds

Each round asks the highest unsettled branches, composed as the
[question filter](question-filter.md) says: one or two questions per round, in the
user's terms, each with a recommendation that "yes" accepts. A question whose answer
depends on another one still open belongs to a later round. Each answer reshapes the
tree: recompute which branches are now askable before the next round.

Finding facts is the agent's job, never the user's. Look facts up in the background
(a worker or a search) without blocking the questions that do not depend on them;
only the dependent questions wait for the answer.

Exhaustive depth, on an explicit request, only raises the number of questions per
round; every question still concerns principles or a material fork, and implementation
detail stays with the agent.

## Finish

Grilling is done when no askable branch is left and nothing is silently assumed, and
it continues until the user confirms a shared understanding. Then close with the
[record](record.md) exit block: the user's decisions, the agent's decisions the user
may veto, and pending user actions.
