# Assignment focus

Keep the highest-priority authorized outcome and its next acceptance condition in
the current assignment/report. Re-anchor to them on resume, handoff or changed user
direction. Choose the next action because it advances that outcome, removes its
blocker or satisfies a required gate. Finish the bounded deliverable and its checks
before optional polish. Record unrelated discoveries as a short follow-up and
continue; investigating them requires a demonstrated dependency or changed scope.

The orchestrator prioritizes unblocked work by the user's current priorities and
dependencies, and carries that focus into each worker assignment. A blocked worker
reports the exact blocker and retained state; the orchestrator chooses any already
authorized independent work. Idle capacity alone is not a reason to start more work.

Progress updates state the material result, any blocker and the next action.
Completion summaries lead with status, decisive verification and remaining action;
link the existing evidence report for details rather than repeating plans,
background or reasoning narration. Give more explanation when requested or
needed for a decision, and retain all required evidence in the report, including
complete report sections returned by read-only workers.

## Worker return and checkpoints

The assignment names the bounded deliverable, required checks and their phase/owners,
expected duration (with uncertainty), next observable milestone, and the supported
checkpoint recipient or bounded-return fallback. Verify that the worker's actual
tool permissions support this delivery path before launch. Worker return
and workflow acceptance are separate: return a complete account of passed, failed
and incomplete obligations; only verified passing evidence clears the workflow.
Initial implementation owns scoped code and implementation checks. Assign applicable
E2E explicitly to implementation or verification; reuse its valid evidence at the
later handoff rather than running it twice because the role changed. Account for
the whole ticket's criteria without making every later-phase gate the implementer's
return condition. Unassigned required checks need an owner before dispatch.

On an estimate overrun, stalled approach or newly discovered defect, send a concise
checkpoint to the supplied recipient with scope/check impact, completed proof, live
job handles and a revised next milestone. Updating a report alone does not deliver
a checkpoint. If the runtime cannot message the parent, preserve that information
in the report and return the bounded result at the next safe boundary after reconciling
owned jobs. Continue a productive authorized check; elapsed time alone is not
a failure or a reason to kill it. A failure requiring work outside the worker's
assigned responsibility, unavailable required resource, or repeated invalid attempts
without new evidence returns the bounded result to the
host after safe teardown. The host owns diagnosis, repairs, rescoping and recovery
under the existing policy; it continues independent work without another user turn.
No extra worker or decision-model consultation is required by a time checkpoint.

## Blocked continuation

Distinguish live work with an owned handle from a user decision or external resource
blocker. For the latter, record the missing input, retained jobs/checkpoints, next
authorized action and the event that can resume it in the existing report. Present
one concise decision brief. An unchanged completion reminder supplies no new evidence
and must not trigger another planning, routing or review pass.
Before ending a turn with a claim that work is continuing, identify the actual live
worker/job handle and completion event; for lifecycle workers, the yield gate
([worker lifecycle](wait.md)) is that check. Without one, either do the next authorized
action or report the concrete blocker and resume event; an idle session is not live work.

Use the host's supported input/wait/blocked lifecycle under its actual rules. Live
jobs keep their completion wait; a user decision keeps its approval pending. For an
explicit persistent goal, establish its supported blocked/resume behavior before
installing it. Never mark unfinished work complete or pause a goal without the
required user authorization. If an external evaluator keeps waking an unchanged
blocker and exposes no usable suspension operation, report that runtime limitation
and the native action needed from the user; Automattic cannot guarantee its wake cadence.
