# Worker return and checkpoints

The assignment names the bounded deliverable, required checks and their phase/owners,
expected duration (with uncertainty), next observable milestone, and the supported
checkpoint recipient or bounded-return fallback. Verify that the worker's actual
tool permissions support this delivery path before launch. Worker return
and workflow acceptance are separate: return a complete account of passed, failed
and incomplete obligations; only verified passing evidence clears the workflow.
Initial implementation owns scoped code and implementation checks. Assign applicable
E2E explicitly to implementation or verification; reuse its valid evidence at the
later handoff rather than running it twice because the job changed. Account for
the whole ticket's criteria without making every later-phase gate the ticket job's
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
