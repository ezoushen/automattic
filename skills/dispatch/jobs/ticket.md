---
name: ticket
agent: builder
inputs: ["ticket", "ticket context", "focus", "checks", "timing", "checkpoint", "return", "brief", "report", "evidence", "worktree", "branch", "project instructions"]
returns: ["## Implemented"]
independent_of: []
acceptance: true
---

# ticket

Build exactly one ticket, test-first, in its own worktree. Dispatch assigns it.

## Inputs

The assignment names `ticket`, `brief`, `report`, `worktree`, `branch`, `evidence`,
`project instructions`, and sometimes `comments` (a previous attempt's failing
output — start from it). All paths are absolute main-checkout paths; the worktree
has no `.scratch/`. `ticket` is a canonical remote ID/URL with the current issue
context in the assignment, or an absolute local Markdown path. Remote assignments
need no local ticket file. Read the supplied criteria, dependencies, priority,
areas and workload; report missing or changed requirements to the orchestrator
rather than creating a mirror or changing the tracker yourself.

Read the ticket and accepted brief; use `CONTEXT.md` for domain vocabulary, relevant
ADRs for design constraints, and the applicable project build/test instructions.

## Finish line

On initial implementation, write `base: <git rev-parse HEAD>` as the first line of
`report` before any change. On resume, preserve the existing base and evidence.

Implement the accepted behavior; use `/mattpocock-skills:tdd` for behavioral changes
at the agreed seams. Documentation-only work uses code-comments' checks.
Choose the smallest sufficient verification: the focused and affected checks the
assignment tiers for you, and the full gate only when the assignment names you for
it. Use the assignment's explicit E2E owner under
[worker return and checkpoints](../../../harnesses/workers/focus.md#worker-return-and-checkpoints);
do not silently absorb the entire review/repair/E2E workflow into implementation.
Reuse passing evidence only when relevant code, inputs and environment match; retain
its original head and provenance. Run missing or invalidated checks and repair
failures caused by this ticket without another request. Keep unavailable required
checks explicit.
For important failure paths, check that the test actually reaches the failing
operation and that its assertion can fail; a dry-run bypass is not refusal evidence.
Use a focused negative control when necessary, not blanket mutation testing.
For changed parsers, accessors or lifecycles, account for affected entry points
and input classes; use a table when it clarifies coverage or the project requires it.

Run builds under check [planning](../../../harnesses/checks/plan.md) and
[execution](../../../harnesses/checks/run.md), with the project's required environment
and only its necessary resource coordination. A local build lock is optional; remote
queues own their capacity. Use verified snapshot identity for intermediate checks
rather than committing solely to give evidence a revision. Use the project's
boot/teardown procedure for runtime checks. Wait for owned processes to exit,
including descendants holding the build lock; report failed teardown without killing
unrelated processes or deleting the shared lock file.

Update affected comments/documentation alongside behavior using code-comments.
Documentation correctness remains a hard review gate. Use `CONTEXT.md` vocabulary
in documentation, test names and commit messages.
Commit scoped changes to the assigned branch. Review remains at the spec gate.

Done when the scoped deliverable and assigned checks are accounted for, or a
failure/blocker needs host recovery under the shared checkpoint rules. Retain
partial proof and reconcile owned jobs before returning. Acceptance requires
assigned gates green (or an authorized documented omission), at least one commit
past `base`, and required entry-point coverage. An incomplete builder may return
without those conditions; it cannot claim acceptance.

## Return

Append to `report` under `## Implemented`: commit SHAs; check commands, outcomes
and meaningful evidence or reuse provenance; affected entry-point coverage when
applicable; every ticket checkbox as `[x]` or the reason it stays `[ ]`.
For a later-phase criterion, name its assigned owner and phase; pending verification
is not a failed implementation check or proof of ticket completion.
Use the supplied evidence directory and the shared
[retention contract](../../../harnesses/checks/run.md#retain-evidence); report any
missing input. Planned checks and local substitutes for required remote checks stay
unchecked.

Report back with status (done, failed or incomplete), which checkboxes, remaining
work, and the exact failing command and output; link `report` for everything else.
