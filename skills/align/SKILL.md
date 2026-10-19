---
name: align
description: "Settle the goal and constraints, then establish a scoped WHAT / WHY / HOW plan, reusing accepted decisions and asking only material unresolved questions."
disable-model-invocation: true
argument-hint: "<idea, plan, decision or effort-slug> [--interactive]"
---

# align

Contents:
- [Settle the mandate](#settle-the-mandate)
- [Establish the design](#establish-the-design)
- [Save the current alignment](#save-the-current-alignment)

First read: the runtime bootstrap (`../../bootstrap.md`), the host session part, [grilling](../../runtime/interview/grilling.md), [question filter](../../runtime/interview/question-filter.md).

Settle the mandate, then turn it into a plan sufficient to split and verify. Reuse
the conversation and existing alignment; a mandate the user already stated need not
be settled again. Interview through [grilling](../../runtime/interview/grilling.md), including
requests to grill the design. Record consequential
decisions in the same ledger. Preserve the distinction between accepted user
decisions and reversible agent choices.
If a governing mandate constraint is unresolved, ask that first and wait for its
answer before presenting dependent WHAT / HOW alternatives. Keep provisional
mechanisms internal; asking to go through the mandate and the design does not combine
their question rounds into an implementation menu.
A request to settle only the goal and constraints ends with the mandate's exit block.

## Settle the mandate

A mandate is the user's goal, principles, constraints and reserved decisions.
Inside it the agent decides; a material choice outside it needs the user.
Work the mandate's design tree through [grilling](../../runtime/interview/grilling.md):
the user decides principles and material forks, the agent decides implementation
detail and shows it for veto, at every depth. Missing sources remain investigation
gaps; ask the human only for material choices they can decide from their priorities.

Work in this order: [establish authority](../../runtime/interview/authority.md),
[filter questions](../../runtime/interview/question-filter.md), then
[record and continue](../../runtime/interview/record.md).

## Establish the design

Prepare one concise WHAT / WHY / HOW brief:

- **WHAT:** observable outcomes, affected consumers, acceptance evidence and scope
  limits, including compatibility promises and non-goals. Each non-goal cites the
  ledger row that decided it, and whether that was the user or the agent. A
  non-goal that narrows an earlier user decision is a question for the user, not
  an agent choice. When real consumer data or consumers exist, acceptance uses them
  as well as fixtures.
- **WHY:** the concrete problem and why existing behavior/mechanisms are inadequate.
- **HOW:** the smallest adequate approach, responsibilities, interfaces and material
  tradeoffs. Reuse Matt's `codebase-design` when interface/ownership decisions need
  scrutiny rather than duplicating its design method.

Choose depth by uncertainty: context for system boundaries; modules for changing
responsibilities; behavior for flows, state and ordering. Include only the views
that resolve a live risk. These are lenses on one brief, not three approval turns.
Read the accepted [ADRs](../../runtime/domain/adr.md) in the area first; a plan that
contradicts one proposes a superseding ADR. Reuse existing mechanisms; compare an alternative only when it is viable and
material. Use the project's [glossary](../../runtime/domain/glossary.md) and keep it current as terms settle.
Use `prototype` only for a question that evidence on paper cannot settle.
Leave ordinary types, helper files and library plumbing to implementation. A
concrete interface or snippet belongs here only when needed to settle the contract.
Check that each acceptance method can distinguish success from failure with the
available inputs and environment before declaring the plan ready for refinement.
Name who can observe each outcome: code, an agent, or only the user. Plan the
user-only observations as one request, sent once an integrated build allows them.
Known unstable or unsuitable evidence is a readiness gap; investigate it now or
record the blocked criterion and next action rather than discovering it at delivery.
Point at the project's current runner contract and record only the task-specific
gates, inputs and ownership; do not copy transport or snapshot internals into the
plan. Refresh affected assumptions when that contract changes. For an accepted
delivery goal, establish the repository's [approval path](../../runtime/board/approval-path.md)
early so an impossible self-review is not discovered only after implementation.

Check the brief, and any design ruling it adopts, against the user's recorded
principles quoted in the Mandate section. A ruling that judges only API coherence
has not checked those principles. Report each deviation as a material fork.

Before selecting an approach or the next investigation, run the configured
[`alignment` checkpoint](../../runtime/decisions/checkpoint-command.md)
with concrete alternatives and evidence. Preserve accepted choices; record an
evidenced skip when the approach is already settled. Check this phase record
before declaring alignment ready.

Show the brief, consequential assumptions and any material unresolved questions.
Continue within existing authorization when these are settled. With `--interactive`,
wait for the requested check before dependent work; no repeated approval for
unchanged decisions. A plan-only request ends with the plan. A vague reply or
silence does not choose an unresolved alternative.

## Save the current alignment

Write `.scratch/<slug>/alignment.md` for an effort entering refinement. Keep it
current; preserve decision history in the ledger rather than accumulating obsolete
plans. The brief contains:

```markdown
# <slug> — alignment

## Mandate
Goal and principles in the user's words, quoted with their ledger IDs; direction
and limits with their decision sources.
Consumers and compatibility obligations, including lockstep dependencies.

## WHAT
Outcomes, scope/non-goals and acceptance evidence.

## WHY
Problem and relevant constraints.

## HOW
Approach, responsibilities, seams and only the diagrams/flows needed to explain them.
Consequential ledger IDs; open decisions and the work each blocks, if any.
```

When new evidence contradicts a decision, reopen it as soon as you see the evidence,
not at the next phase. Tell the user when it was their decision. Then reopen its dependent design,
tickets and review coverage. Preserve unaffected conclusions. Dispatch returns
here when implementation disproves a design assumption; refinement re-cuts only
affected work. Independent work may continue when its contracts, worktree and
resources do not depend on the open decision; overall status remains incomplete.

Ready for refinement when the outcomes, boundaries, approach and verification are
clear enough for executable tickets and no unresolved decision blocks that scope.
Close with the same exit block as the [mandate](../../runtime/interview/record.md):
user decisions, agent decisions open to veto, pending user actions, and any
carried-over findings with their disposition.
