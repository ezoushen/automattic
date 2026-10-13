---
name: mandate
description: "Clarify the goal and material constraints; decide reversible details within the user's mandate."
disable-model-invocation: true
argument-hint: "<idea, plan, or decision to clarify> [--interactive]"
---

# mandate

First read [runtime bootstrap](../../harnesses/README.md) and the selected adapter.

A mandate is the user's goal, principles, constraints and reserved decisions.
Inside it the agent decides; a material choice outside it needs the user.
Reuse Matt's `/mattpocock-skills:grilling` design-tree reasoning internally with
the question filter below. A request to "grill" an Automattic plan uses this
bounded policy. Use Matt's exhaustive interview only when the user explicitly
requests that depth; naming grilling alone does not select it.
At exhaustive depth, relax the round's question-count/detail limit while keeping
the same fact/engineering/material-fork filter and settled decisions. Missing
sources remain investigation gaps; ask the human only for material choices they
can decide from their priorities.

## Establish authority

Start with the current request and accepted conversation, then relevant project
instructions, `CONTEXT.md`, decisions and an existing effort ledger. Read only
sources needed for this task. The goal need not be confirmed again when the user
already stated it. A decision the user reserved is always theirs.
Discover facts from code, tools or authoritative sources. Distinguish observed
facts, user decisions and agent assumptions; silence never promotes an assumption
into approval or a standing preference.
Start from the accepted code/documentation contract. Resolve available technical
facts, including pinned upstream behavior and acceptance-method reliability, before
presenting product alternatives. Narrowing a promised contract is a product change,
not the default cheap repair; keep the unmet requirement visible until authorized.

Record a principle or constraint the user states, at any phase, verbatim in the
ledger, with its source. Do not paraphrase it into a design term. Check every plan
element against the user's words. If an element deviates, say so and ask about it
as a material fork. Never describe the plan as matching ("exactly the plan") while
an exception exists, even an exception you have disclosed.

## Filter questions

For each unresolved choice:

1. **Discoverable fact:** investigate it. Dependent decisions wait for evidence;
   independent work continues.
2. **Reversible engineering choice within the mandate:** decide using the simplest
   adequate existing mechanism. Record a material assumption and what would
   invalidate it; routine helper placement needs no interview or ledger ceremony.
3. **Material fork:** ask only if plausible answers change the goal, accepted
   behavior, compatibility, scope, cost/resource boundary, an irreversible action,
   or a user-reserved choice. State the consequence and your recommendation.
   Missing context matters only when it changes such a decision.

After filtering the questions above, run the configured
[`mandate` checkpoint](../../harnesses/decisions.md#configured-checkpoint-command)
before choosing among permitted investigate/decide/ask actions. Record an evidenced
skip when the next step is settled or reserved to the user; user-reserved choices
remain human. Check this phase record before leaving mandate.

Reuse accepted priorities and ask for the highest unresolved goal, principle or
constraint that settles related forks together. Ask what may change before asking
how to implement it. Defer questions whose answer depends on that unresolved
choice, even when their technical alternatives are already known.

Compose the user-facing round in this order:

1. State the goal and material uncertainty in one or two sentences; keep the
   user's scope intact.
2. Ask the highest unresolved boundary in the user's terms: what may be removed
   or what must keep working. Usually ask one question; at most two independent
   choices, including subquestions and trailing approval asks. Defer questions
   that depend on an unanswered scope choice.
3. Give one recommendation and its main evidenced consequence. The user should
   be able to answer from their priorities without learning implementation details.
   Use only terms the user introduced or defined in the same sentence. Internal
   names such as components, readers, modes or ticket IDs fail this check.

End the question round after those three parts. Review the entire visible reply,
including tables, headings and trailing notes; a concise question inside a full
plan does not pass. Save the remaining investigation and ledger work internally.

For example: "Must existing behavior stay compatible, or may we change it if
measurements show that is necessary? I recommend preserving it while we
investigate." Keep consumer
classification, release strategies, mechanisms and checkpoint metadata internal.
Investigate usage; unknown consumers do not waive a public contract. A possible
agreement breach always needs a human ruling or an applicable existing user
condition before dependent work. Preserve callers while comparing compatible
options; ask about changing them only when that decision becomes necessary.

Before sending, check the entire reply against this shape and its evidence.
Keep every material source of the user's problem in the opening; a question about
one source must not silently narrow the goal to that source.
A measured size category is not an attainable saving; do not promise its recovery,
call an API change the only route or rule out compatible options without comparison.
If the draft fails, revise it before asking the user; repeated failure enters the
existing recovery/review path. Keep required calibration warnings to one brief
line when first surfaced, separate from the question.

Keep the remaining design tree internal. Surface another decision only when the
answer or new evidence makes it necessary; explain details on request. Record
material agent choices and unresolved risks, and pause work that depends on an
unanswered user decision. Stop interviewing when the next authorized work has a
sufficient mandate. A broad "looks good" cannot select between incompatible open
options: clarify the selection while continuing independent work.

## Record and continue

For work needing a plan, keep consequential decisions in the existing effort
ledger, normally `.scratch/<slug>/ledger.md`. Reuse its IDs across align/refine:

| # | Decision | Hinge (evidence and what would change it) | Rejected alternatives, if material |
|---|---|---|---|

Keep rows short; omit artificial alternatives and routine implementation choices.
Record the source of user decisions separately from agent decisions. Keep a
`## Standing directives` section in the ledger for the user's corrections to how
agents work (routing, reporting, retention, permissions), quoted with their date. Persist
standing principles only where this project already keeps them, using Matt's
`domain-modeling` when terminology or durable domain decisions actually change.
Follow the host's rules for writing memory; this skill supplies no extra permission.

When mandate completes, not after each question round, close the phase record.
End that reply with a short exit block:
- the user's decisions recorded;
- the agent's decisions, which the user may veto;
- pending actions only the user can take.

When a review triggered this mandate, add one line per open finding: fixed,
superseded, folded into decision `<id>`, or still open. The user should not have to
ask whether questions, decisions or findings remain.

Proceed with already authorized work once no material unresolved choice blocks it.
A ledger is inspectable evidence, not a compulsory approval turn or timeout-based
consent. If the request was only to plan, return the plan. With `--interactive`,
show the concise proposal and wait for the requested human check before dependent
execution; reuse approvals already given. Actual publication/resource permission
gates retain their existing authorization requirements.

Design choices belong to `/automattic:align`; ticket slicing to `/automattic:refine`.
They reuse this filter and ledger. Matt's explicitly human-in-the-loop activities
still need their live exchange; an agent decision cannot stand in for that human.
