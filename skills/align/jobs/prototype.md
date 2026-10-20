---
name: prototype
agent: builder
inputs: ["question", "worktree", "branch", "report"]
returns: ["## Verdict"]
independent_of: []
acceptance: false
---

# prototype

Align assigns it: answer one question with throwaway code by [prototype](../../prototype/SKILL.md).

## Inputs

The assignment names the `question`, a throwaway `branch` in its own `worktree`
created from the effort's base, and the `report`. An assignment with more than one
question, or one of neither kind the prototype procedure names, goes back to align.

## Finish line

Build it as the prototype procedure says, committing only to the assigned throwaway
branch. Done when the run gives a verdict on the question, or shows the question
cannot be answered this way.

## Return

Append `## Verdict` to `report`: the question, the verdict with the output that
decided it, the run command, and the throwaway branch and commit. Align records
it: the verdict and the question it settled go to the ledger and, when it qualifies,
an ADR offered under the [ADR rules](../../../runtime/domain/adr.md#when-to-offer-one).
