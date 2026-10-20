# Dispatch iteration

The iteration stage of [dispatch](SKILL.md); the [review handoff](handoff.md) follows it.

## One iteration

1. Re-read the scoped board and canonical tracker issues under the bootstrap's
   project conventions.
   Refresh human changes to scope, criteria and priority before assigning work;
   materially changed active work returns for alignment. A principle the user states
   mid-dispatch is recorded verbatim and checked against the plan under
   [authority rules](../../runtime/interview/authority.md). Keep local runtime state
   and canonical issue state distinct, and apply authorized tracker transitions
   at the project's actual milestones. Read pending receipts and attention items
   under [worker waits](../../runtime/workers/wait.md#wake-and-yield)
   before new dispatch; design holds pause dependent work until their ruling and
   updated criteria are recorded. Reconcile persisted live tickets with
   selected executor's run status and on-disk reports before starting replacements. An absent agent is
   interrupted work, not evidence of success. Resume its existing worktree or
   start a replacement with what survived; never discard edits to retry.
2. For cross-effort edges, the prerequisite effort must be entirely done, and
   have current review/E2E delivery evidence; its retained `feat/<dependency>` tip
   must be an ancestor of local `main`.
   Merge into main is the wave boundary and requires applicable user authorization;
   carry that authorization forward rather than requesting it again. If the selected
   effort branch already exists,
   merge that verified `main` into its spec worktree before selection, while no
   selected worker is using it. Verify the dependency tip is present there as
   part of board selection. Keep dependency branches until their dependents have started.
   Squash/cherry-pick equivalence is not inferred; re-cut the edge with explicit
   evidence if history was rewritten. Never merge an unfinished external effort
   into a selected branch or infer merge permission merely from a backlog request.
3. Select candidates through the chosen board operations. Validation failure → repair the scoped ticket
   graph or report the out-of-scope defect. Admit only verified available executor
   and shared account capacity, refreshing reservations before each launch.
   An empty candidate list is not completion: inspect scoped execution counts. Live work → arm a
   notified wait for each worker, pass the lifecycle's
   [yield gate](../../runtime/workers/wait.md#wake-and-yield), then yield. Ready work without
   a candidate → identify area/capacity/dependency/integration waits. If none can be
   resolved within scope, record the attempted resolution and block those tickets.
4. For each candidate, from `repo`, ensure the effort branch and its worktree exist:
   `feat/<slug>` in its spec worktree, or `main` in the main checkout when the user
   said to work [directly on main](modes.md#directly-on-main). A new effort branches
   from `main` after fetching and comparing it with its remote. A stale or diverged
   local `main`, or a stale consumer checkout used as a base, is reported, and the
   effort branches from the verified remote tip (on `main`, the user is asked).
   Apart from working directly on main, never commit to the user's local `main`. Choose [how a ticket runs](modes.md). An inline ticket skips only the
   ticket branch and worktree, their preparation, the builder launch with its launch
   decision record, and the merge; everything else in steps 4 and 5 applies to both
   modes. For a delegated ticket, create the ticket branch/worktree
   from that effort branch using the project's naming convention. The fallback
   is `feat/<slug>-<key>` in `.worktrees/<slug>-<key>`, where key is local `NN` or
   a stable safe remote issue key from board operations. Reuse existing branches and
   worktrees after verifying their identity. Merge the current effort branch into
   a resumed ticket branch before restarting it; preserve and resolve local edits.
   When the user allows stacking, a dependent ticket may branch from an accepted
   ticket branch that is not yet integrated. Record the stack in the run report, and
   merge the base's later fixes into the dependent branch before accepting it.
   Prepare fresh and recreated worktrees with the same project-identified gitignored
   build inputs; verify required paths without printing credential-bearing files.
   Plan the assigned checks using [plan and accept checks](../../runtime/checks/accept.md).
   Verify the runner's current contract and the worker's checkpoint capability;
   carry the runner's currently supported wait/status/log/cancel operations
   ([check execution](../../runtime/checks/run.md#run-a-bounded-check)).
   Create reports directory, claim the ticket and record implementation started,
   then start a `builder` with:

   ```text
   adapter: <absolute active adapter>  plugin_root: <absolute>  repo: <absolute main checkout>
   agent_file: <plugin_root>/agents/builder.md  job_file: <plugin_root>/skills/dispatch/jobs/ticket.md
   ticket: <canonical ID/URL or absolute local ticket path>
   ticket context: <current issue content, criteria, dependencies, priority and revision>
   focus: <highest-priority outcome, next acceptance condition and deferred optional work>
   checks: <each check's criterion or project requirement and tier: focused and affected for this worker; full gate and E2E with phase and owner; reusable proof>
   timing: <expected duration with uncertainty; next observable milestone>
   checkpoint: <supported parent recipient/handle or bounded-return fallback>
   return: <assigned deliverable/checks accounted for, or shared failure/incomplete boundary>
   brief: <absolute alignment.md>  report: <absolute reports/key.md>
   evidence: <absolute main-checkout reports/evidence/key/attempt/head directory>
   worktree: <absolute>  branch: <assigned branch>  project instructions: <paths and applicable facts>
   skills: <situational skill paths or names, each with its fact>
   comments: <previous failing command/output, if any>
   ```

   Every worker, probe, checker or E2E run started while the dispatch is active is
   registered in the run report with its assignment, device reservation and result,
   including ad-hoc ones the user requests mid-run. Status answers read that one
   record. Record the returned agent ID through board operations and complete the
   [launch decision record](../../runtime/routing/report.md).
   If spawning fails, reconcile whether a child was actually created before retrying.
5. When a worker finishes, perform the selected board's acceptance checks for report
   structure and branch ancestry; they also run the effort's
   [standing measurements](../../runtime/board/project-loop.md#standing-measurements) at the
   ticket head and refuse a missing or worse value or a changed measurement tool, which only a
   ledger-cited `allows` excuses.
   Then judge assigned implementation criteria and recorded checks in `## Implemented`.
   Account for every ticket criterion, retaining later-phase obligations for their named
   owners. Those pending gates do not block implementation acceptance/integration; they
   still block delivery until verified.
   Structural acceptance is not a code review.
   Accept the worker's recorded checks at their commit; do not rerun them, apart from those measurements.
   Collecting through the worker lifecycle records the decision outcome. Otherwise
   record it against that acceptance evidence or mark it unknown, then run the
   [completion record check](../../runtime/decisions/annotate.md#check-a-handoff)
   for the recorded decision. Preserve any capture gap explicitly; bookkeeping
   failure does not justify repeating implementation or inventing passing evidence.
   Apply [worker return and checkpoints](../../runtime/workers/return.md):
   a failed/incomplete return hands recovery to the host, not verification to the user.
   Missing assigned implementation evidence → blocked with the exact failure in the issue or run report.
   Accepted → retain the [check evidence](../../runtime/checks/evidence.md)
   outside the ticket worktree, verify its report links, then merge its branch in
   the spec worktree. Record implementation integrated, record lifecycle `accepted`
   on the attempt with the integrated commit, and apply the project's
   corresponding tracker transition. Not accepted → record lifecycle `declined` with
   the reason. Retiring its worker first requires an
   [acceptance decision](../../runtime/workers/collect.md#accept-and-record-outcomes), usually `deferred`
   until these checks finish. Keep the ticket worktree through the remaining
   review/repair and applicable E2E; integration alone does not retire it.
   Once an integrated build allows checks that only the user can observe
   (`Verify (user)`), send the user one request covering all of them,
   [with context](../../runtime/ask/ask.md).
   On conflict, assign a builder the `merge-conflict` job and its inputs in the spec
   worktree, except on `main` ([directly on main](modes.md#directly-on-main)).
   No other worker may use that worktree then; the orchestrator completes the merge.
6. A blocked ticket is the orchestrator's work: research missing facts under
   [research](../research/SKILL.md), diagnose defects under
   [diagnosis](../diagnose/SKILL.md), resolve engineering choices within accepted constraints, or return to
   align/refine for design errors. Apply [escalation checkpoints](../../runtime/workers/escalation.md)
   before retrying a worker, and report the retain/replacement decision.
   Read scoped source/diffs when needed to resolve
   the block. Before asking the user to provide or start a resource, check what is already
   available yourself, and name what you checked when you
   [ask with context](../../runtime/ask/ask.md). Ask the user only for missing
   context, product choices or actual permission boundaries. Replacing a criterion's
   `Verify` method with a weaker one is the user's decision. Record failed commands
   verbatim. Resolve → ready.
   Two failed attempts at the same ticket → split it around one deterministic
   Verify per criterion; never an unchanged third attempt. Like any new cut, the new
   tickets wait for the user's check.
   An agent's permission limit does not establish a human-only task. Separate missing
   authorization, access, capability and unresolved user choices. When the user has
   authorized the operation, the orchestrator may perform it within native permissions;
   a genuine operator-only restriction still applies. Verify target identities from
   the project's inventory and probe the relevant capability, not an unrelated
   privileged command. Record the actual blocker and continue independent work.
7. Quote fresh scoped execution counts and report implementation completion separately
   from review and E2E. Answer a direct user question first, from current recorded
   state, and name any pending check before processing queued notifications. For a
   gate expected to take over 15 minutes, report its milestones and ETA; don't go
   silent. Name the effort branch/worktree and blocked tickets.
   Persist authorization and scope changes alongside the board operations' execution
   updates; carry unresolved selected work through follow-ups in the conversation.
   Once implementation reaches its completion condition, continue into the handoff.

