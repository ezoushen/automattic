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

Read each skill the assignment lists before the step it serves. Load another
skill when a step needs it. Report each skill you loaded beyond your agent and job files
and the listed ones, with its reason, and any listed skill you never used. See [assignment skills](skills.md).

Before returning or checkpointing, read [worker return and checkpoints](return.md).

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
