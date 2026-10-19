# Escalation checkpoints

The orchestrator owns when to reconsider a saved choice. Check at existing workflow
boundaries, without a new polling loop or separate model-quality review:

| Checkpoint | Evidence and decision |
| --- | --- |
| Unaccepted public API/ABI or behavior change, new platform exception, ADR conflict or stale acceptance criterion | Apply the [early design hold](design-hold.md). Complete the decision brief before adjudication; record the ruling and update canonical criteria before dependent work resumes. |
| Worker reports a blocker or repeated unproductive attempts | Inspect the failing approach and current run state. Decide whether to supply context, repair the environment, rescope or reconsider the worker. |
| A review layer completes or a required verification check fails | Use consolidated confirmed findings and failed checks before assigning the next repair. One material contract miss can justify escalation; comment counts alone cannot. |
| Before retrying or resuming after a failure | Compare new evidence with the saved decision and remaining attempt budget. Reuse the choice when nothing material changed; resolve an evidenced mismatch before another attempt. |

First distinguish missing context, changed requirements, environment/access failures
and a localized defect from evidence that the current model/effort is inadequate.
A focused correction can stay with the same worker. Repeated failure of the same
understood contract, an invalid approach or newly discovered complexity can justify
more permitted thinking, another allowed model, or a narrower assignment. Choose
the action that addresses the cause; no compulsory model ladder or extra failed
round is required. Elapsed time, a normal resource-lock wait or an incomplete live
report alone does not establish inadequacy.

At a recovery boundary, run the [configured checkpoint command](../decisions/checkpoint-command.md)
with family `recovery`, [permitted actions](../decisions/phases.md#recovery) and current
evidence, or a justified skip when the next step is required or settled. Check its
phase record before acting and its outcome at the handoff. A retain/context/environment
recommendation keeps model routing out of that checkpoint. Disabled or unavailable
recovery stays with host judgment.

For reselection, give the configured router the previous model/effort, concrete
failure evidence, attempted correction, unchanged acceptance criteria and remaining
budget in the compact assignment, and pass the failure with `--after-failure
"<evidence>"`; under `consult: "after-failure"` only that flag consults the service.
The orchestrator judges the proposal. If it
repeats a combination already shown unsuitable without new evidence, use host
selection once with that exclusion; do not cycle through router calls. Report a
deliberate retain decision when a focused retry is justified. Explicit pins,
thinking bounds, `fallback:false`, permissions and existing attempt limits still
apply; escalation cannot manufacture another attempt or unlock a pinned field.

Apply changes at a safe handoff after reconciling and stopping the previous owned
writer/jobs. Keep the same assignment identity, revision-bound evidence and attempt
history; append the replacement decision rather than overwriting the old one.
A decision snapshot changes for the next attempt, not midway through a live worker.
