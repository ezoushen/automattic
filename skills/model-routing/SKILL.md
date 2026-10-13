---
name: model-routing
description: "Choose or reconsider one worker model and thinking setting for a bounded assignment at initial selection, evidence-based escalation or availability recovery."
argument-hint: "[assignment and eligible worker choices]"
---

# Model routing

Read the [runtime bootstrap](../../harnesses/README.md) and active host adapter.
Choose in the host's existing context. This skill returns a decision; the existing
executor handles dispatch. Use [selection](../../harnesses/selection.md#choose-for-an-assignment)
for resolver arguments, profile overrides and recovery.
When the configured router is `decision-model`, use its compact assignment input
as described in [System One routing](../../harnesses/selection.md#decision-model-router).
Supply `--assignment`, `--journal` and `--assignment-id` together for a live backend
choice, plus `--after-failure "<evidence>"` when retrying after a failed attempt. A missing-input or invalid-JSON error is a call/configuration problem to
correct, not evidence that the backend is unavailable. Host `--selection` is not
a shortcut around the configured router; preserve the actual fallback or override
reason and any existing backend decision when using it.
If this skill is the returned fallback after that service failed or abstained,
choose here directly and submit `--selection`; do not call the service again.
Shared `decisions` configuration supplies the backend and calibration policy.
Surface its new warnings through the [decision skill](../decision/SKILL.md).
At recovery checkpoints, choose the recovery action before worker reselection;
context or environment repairs can retain the existing choice.

Start with the supplied assignment, acceptance criteria and eligible role pool.
Compare model and native thinking together, using the catalog's task-fit descriptions,
known tool/context support, uncertainty, consequences of mistakes and relevant
verified outcomes. Weigh total completion cost, including repair, review, context
transfer and runtime startup. A local model is a normal candidate when it fits.
Apply the user's routing instruction and existing priority alignment.

Use the lightest adequate combination when the work is well understood and failure
is reliably detectable. Ambiguous diagnosis, broad contracts or weak failure signals
can justify a stronger starting choice. More thinking is useful only when the task
benefits from it. Avoid a universal model ranking, compulsory escalation ladder or
invented performance estimates; limited evidence supports a provisional judgment.

Return `candidate`, optional `thinking`, and one short `reason` through the
[selection contract](../../schemas/selection.schema.json). Choose within the filtered
pool and configured thinking bounds. With insufficient context, inspect the narrow
missing fact or make a reasonable provisional choice; routine routing is not a
human approval gate. Return `candidate: null` only when no permitted worker fits.

Select one owner for the bounded assignment. The worker completes it directly;
the orchestrator owns splitting, independent review and replacement. Reuse the
choice through ordinary resumes. At [escalation checkpoints](../../harnesses/selection.md#escalation-checkpoints),
judge whether new evidence warrants retaining, adjusting or replacing it.
Announce initial choices and reconsiderations through the
[decision report](../../harnesses/selection.md#report-routing-decisions), naming
the proposer, orchestrator, method and evidence.

After a router failure or abstention, preserve the failure and exclusions in the decision
record. A router outage is distinct from a worker's capability failure. Availability
recovery keeps the assignment's scope, gates, attempt limits and user pins.
