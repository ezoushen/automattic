# Recovery and escalation

## Feedback and recovery

Classify the observed response before recovering. HTTP 429 alone does not establish
exhausted credit: inspect the service's error details and retry metadata. For a
temporary rate limit, retain the supported retry time, reduce admission against
the [shared account budget](../resources/resources.md#shared-capacity), and use a bounded retry
only when availability can change. If an eligible alternative is available, the
ordinary fallback can continue immediately. Proven exhausted quota or an outage
excludes candidates on the affected service/account; a new model name on that
same account is not recovery. Record the classification, affected account and
retry/fallback condition, without exposing credentials. Never create parallel
retry bursts or unbounded backoff that strands the assignment.

Availability failures trigger automatic recovery within the allowed pool: exhausted
credits/quota, unavailable model/provider/harness, missing executor capability or
an unsupported requested model/effort pair. Preserve the failure evidence, exclude
the failed candidate, and re-resolve with the remaining `--eligible-candidates`.
Exclude other candidates sharing a proven failed service/account or capability;
switching from one Codex model to another does not cure an exhausted Codex account.
Do not ask for another approval when a suitable configured alternative exists.
If resolution requests selection, follow its `selection_router` through the
[assignment selection flow](../routing/choose.md). A profile preference excluded by availability does not get retried;
its candidate-specific thinking is also released for the replacement. State the
switch and continue the same assignment, scope and gates. Never lower
an effort bound or approximate a setting to force a launch.

Retain exclusions in existing session/assignment state; do not keep retrying a known
failure until availability actually changes. A fixed instance has no alternatives.
If all permitted candidates are exhausted, report the blocker and ask only for the
missing decision. Explicit user pins and `fallback:false` remain constraints.
Authentication unavailability can use an already authorized alternative account;
never acquire credentials, change permissions or bypass a sandbox/tool denial.

A failed worker's partial report cannot close its obligation. Reconcile and stop
any owned live writer/jobs before replacement; an ambiguous timeout requires
inspection, not immediate resubmission. Give the replacement the same assignment,
retained evidence and revision. Its complete verified report may close the original
obligation. Availability recovery does not authorize parent self-approval or waive
independent review.

Keep the existing review/repair attempt limits across model switches. A switch
does not reset the counter or bypass a permission or resource ownership boundary. Record its
reason and previous configuration; revisit a failed combination only after relevant
new evidence or a state change. Reuse unaffected review coverage and existing gates
instead of adding a separate model-quality review. Compare accepted assignments
and total recovery cost; a few outcomes do not establish a universal model ranking.

## Escalation checkpoints

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

At a recovery boundary, run the [configured checkpoint command](../decisions/checkpoint.md#configured-checkpoint-command)
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
