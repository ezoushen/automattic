---
name: prototype
agent: builder
inputs: ["question", "worktree", "branch", "report"]
returns: ["## Verdict"]
independent_of: []
acceptance: false
---

# prototype

Build throwaway code that answers one question evidence on paper cannot settle.
Align assigns it; the answer, not the code, is the deliverable.

## Inputs

The assignment names the `question`, a throwaway `branch` in its own `worktree`
created from the effort's base, and the `report`. The question is one of two kinds:
does the logic hold, or what should it look like. A logic question concerns a state
model, an ordering or a rule's edge cases; a look question, an interface or output a
person judges by seeing it. An assignment with more than one question, or one of
neither kind, goes back to align.

## Finish line

- Write only what answers the question: one entry point, nothing reusable, no
  abstraction for later. Put it beside the code it informs, named and headed so a
  reader sees it is clearly marked as a prototype and not product code.
- Make it trivial to run: one command from the project's existing runner or tooling,
  stated at the top of the prototype and in the report.
- Keep no persistence: state lives in memory. When the question is about storage
  itself, use a scratch store named for the prototype and remove it afterwards.
- Show the whole relevant state after each step or variant, so the answer can be
  read from the output rather than inferred.
- For a logic question, drive the cases that are hard to reason about on paper; for
  a look question, offer a few clearly different variants side by side.

The prototype is evidence, not product behavior: test-first and mutation checks do
not apply to it, because none of it merges. Commit it only to the throwaway branch;
it never merges into the effort branch or `main`, which keep only the verdict.

Done when the run gives a verdict on the question, or shows the question cannot be
answered this way.

## Return

Append `## Verdict` to `report`: the question, the verdict with the output that
decided it, the run command, and the throwaway branch and commit. Align records
it: the verdict and the question it settled go to the ledger and, when it qualifies,
an ADR offered under the [ADR rules](../../../runtime/domain/adr.md#when-to-offer-one).
