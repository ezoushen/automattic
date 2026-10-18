# Skill executor

Resolve `executor_config.skill` through the actual caller's installed skill catalog
or documented skill loader. A copy installed for another host does not establish
availability here. Check the selected skill's caller support and required tools,
including for a shared `herdr` route; a profile name never changes the caller.
Use the exact selected skill; do not guess a filesystem
path, install a substitute or invoke a similarly named sub-agent. Skill invocation
rules still apply: reading instructions is not a workaround for an explicit-only
invocation restriction. Report an unavailable or non-composable skill as a blocker.
The coordinator may recover through another allowed candidate under the shared
[recovery policy](../../runtime/workers/recovery.md#feedback-and-recovery); this executor does not
choose replacement models or bypass invocation restrictions.

Provide `executor_config.instruction` followed by the current shared assignment
and resolved model policy/settings. Keep scope, worktree, pinned revision, agent
and job files, permissions and acceptance criteria in the assignment. The configured
instruction describes how to delegate; it does not replace the agent or job file.

Before the first launch, read the selected skill's applicable preflight, launch,
completion, recovery and cleanup instructions, including their referenced procedures.
An opening excerpt or CLI help alone does not establish the lifecycle contract.
Establish that it can launch the requested worker, honor its access limits and
collect its complete result. Read the destination's settings guidance as needed.
Use the skill's supported delegation entrypoint for the supplied assignment;
Automattic retains planning, review and acceptance gates. If the skill requires an
incompatible orchestration loop, treat it as non-composable rather than bypassing
its rules or nesting a second workflow.
`inherit` must preserve that destination's model/thinking configuration; merely
omitting flags is insufficient if the bridge discards it. `override` must map
`settings.model` and `settings.effort` to real controls for the final worker.
Do not approximate a thinking label with a prompt or select a replacement model.
If the skill cannot fulfill the assignment or model policy, report the exact gap.

Let the skill own its tools, launch syntax and lifecycle. For Herdr, use the
installed Herdr skill, including its managed-session prerequisite, identity checks
and output collection, plus [Automattic's environment guidance](../herdr.md);
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
