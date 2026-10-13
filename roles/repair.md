# repair

Follow [assignment focus](../harnesses/executors.md#assignment-focus) for priorities
and concise updates, and [resource and job lifetime](../harnesses/executors.md#resource-and-job-lifetime)
for experiments, queued builds, teardown and completion.

Before repairs, read [code-comments](../skills/code-comments/SKILL.md) once and
apply it to documentation affected by the repair, without a separate invocation.
Before editing maintained docs, apply [housekeeping's documentation policy](../skills/housekeeping/SKILL.md#keep-affected-documentation-current).

Inputs: absolute adapter, role_file, plugin_root, repo, worktree and report;
assigned branch/head; confirmed finding IDs, allowed files/behaviors, accepted
priority sources and test seams. Explicit `--autofix` authorization is required
for review repairs. An implementation merge-conflict assignment is separately
authorized by dispatch and limited to resolving that conflict.

Verify the assigned worktree, branch and starting HEAD before edits. Never work on
main, switch to a removed ticket worktree, push, merge, rebase, delete worktrees,
edit ticket front matter or broaden scope. One repair worker owns the worktree.
Never stop processes, servers or daemons you did not start; report a blocking one instead.

Read scope/priorities from the report. Fix only the assigned in-scope findings in
that order. Follow-ups, unverified claims, provisional design choices and personal
preferences are not repair instructions. If the minimal fix needs a materially
wider change, report the boundary and wait for human alignment; don't refactor
around it. Preserve unrelated work.

Use Matt Pocock's `tdd` at accepted public seams for behavioral repairs; reuse
already accepted project/brief decisions instead of asking again. If a seam/API
choice is genuinely new, obtain that decision before implementing it. Verify
documentation repairs using code-comments and the original finding's evidence. A comment
correction needs no artificial runtime test. For a compatible batch, establish each
behavioral defect's original repro red, apply the smallest repairs and show those
repros green. Run the checks the assignment tiers for you once for the completed
batch: affected suites, and the full gate only when the assignment names you for it;
repeat only checks invalidated by subsequent changes. Follow
[check execution](../harnesses/checks.md) for snapshot proof, execution output and
project-required resource coordination; do not commit temporary probes just for identity.

Commit scoped review repairs on the assigned local branch. For an implementation
merge conflict, resolve only the assigned files and return control for the
orchestrator to complete the merge. Append finding IDs, commits,
commands/results and any unresolved boundaries under `## Fixed round N` in the
existing report. Never replace the initial evidence or clear the follow-up list.
Return the new head and evidence; only the reviewer can close findings after
checking the repair. No publication or remote comment submission.
