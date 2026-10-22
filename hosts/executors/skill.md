# Skill executor

The [skill executor contract](../../runtime/config/skill-executor.md) applies; this part
adds the host and Herdr specifics.

Let the skill own its tools, launch syntax and lifecycle. For Herdr, use the
installed Herdr skill, including its managed-session prerequisite, identity checks
and output collection, plus [zloop's environment guidance](../herdr.md);
do not maintain a second CLI manual here. Limit layout
changes to those needed for the assignment, using the skill's caller context and
returned identities. An output-recovery procedure requiring writes is unavailable
to a read-only assignment unless those
writes were already authorized. Record incomplete evidence without widening access.

The orchestrator still owns capacity, workspace assignment and acceptance. Record
the skill identity, worker handle, assignment ID and requested/confirmed settings.
A ready pane or finished skill invocation does not prove the worker completed its
assignment. Use the skill's normal completion operation and settled states; a
custom state filter needs an assignment-specific reason. Preserve the operation's
exit status and error response through shell wrappers and output formatting.
A timeout, failed wait or missing status is a monitoring result, not worker success
or failure. Inspect the same worker and its report/revision before retrying or
rearming its wait; never label an unconditional shell message as completion.
When a worker is confirmed working, a partial report is normal: keep the assignment
live. When its authoritative state is settled and its full report/revision satisfy
acceptance, retire the obsolete wait and continue; the old predicate is not another
gate. Apply the shared integration and review gates before claiming overall delivery.
On lost context, recover that same assignment; retain pending user approvals
rather than answering them or switching executors.

Retire workers according to remaining phase responsibilities, not idle state alone.
Keep a reviewer needed for repair rechecks, or deliberately retire it after saving
its report/evidence and clear its live handle before resolving a replacement through
the configured route. Verify retained artifact links before closing owned panes or
removing worktrees. Releasing a finished wait does not retire its worker.
