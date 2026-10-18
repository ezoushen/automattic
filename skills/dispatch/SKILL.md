---
name: dispatch
description: "Implement scoped tickets and review the integrated changes; --autofix adds repairs and applicable E2E verification."
disable-model-invocation: true
argument-hint: "[effort|project|milestone|issue-ID|issue-URL] [--autofix]"
---

# dispatch

First read [runtime bootstrap](../../harnesses/README.md) and the selected adapter.
One orchestrator owns scheduling, worktree integration and board updates.
Workers receive the shared `roles/<role>.md` and only their task inputs. An effort
has a local slug for its branch, alignment and reports; tickets live in the
configured tracker or, only for local Markdown, `.scratch/<slug>/issues/`.
Read [board operations](board.md) and use the selected board throughout this skill.
Use [reference.md](reference.md) when a rule's rationale or a known failure mode
needs explanation.

Dispatch includes a read-only assessment after implementation, unless the
user explicitly requests implementation only. `--autofix` authorizes scoped review
repairs and applicable E2E verification; separate it from the board selector.
Carry forward existing explicit repair authorization, including an applicable
full-delivery request. Without that authorization, dispatch stops after read-only
review. Publication requires its own request.

## Setup

1. Resolve existing project instructions using [project-loop.md](project-loop.md).
   Reuse established sources; no new setup document is required. Pass the relevant
   sources and uncovered facts in assignments. The project defines required
   compile, suite and E2E gates; do not invent extra suites for every ticket.
   Verify unfamiliar or changed check commands resolve the intended tool/version
   in the worker environment before distributing them. Reuse valid preflight evidence.
2. Resolve absolute `plugin_root` and `repo` (the main Git checkout). Call the
   maintained scripts in the plugin directly. Never copy them into the repo.
   Add `.worktrees/` and `.scratch/` to the project's ignore rules if absent.
3. Check the active adapter, selected executor tools and permissions. Verify assigned
   repository/worktree identities before starting workers. Automattic does not
   require a Git denial probe or impose a Git-command blocklist.
   Reconcile the [shared capacity budget](../../harnesses/workers/resources.md#shared-capacity)
   across known sessions/accounts before admitting the batch; local scheduler
   capacity is not an account-wide allocation.
4. Resolve and validate the selected board and invocation scope using board
   operations. Remote projects use native issue queries and dependencies directly;
   do not create local ticket files or call the local scheduler for them.

A supplied scope is never widened, even to unblock it. Use the board's
[overall scope and batches](board.md#overall-scope-and-batches) rules to preserve
backlog-wide requests across narrower batches, including selected parent/child work.
Consider other efforts' live work for capacity, area and device conflicts without modifying them through
a scoped call. One orchestrator per main checkout; two independent
sessions must not schedule/mutate the same board concurrently.

## State and continuation

```
per ticket: ready → implementing → done                 any stage → blocked
```

These are execution milestones, not required tracker status names. Only the
orchestrator records them through the selected board operations. Here `done`
means implementation accepted and integrated. Review evidence belongs
to the review report, not the last implementation ticket. Reports always live in the main
checkout's `.scratch/<slug>/reports/`; worktrees do not contain that ignored state.

Implementation completion for the current batch: every selected ticket is done,
or blocked with the orchestrator's actual unblock attempt and failure recorded
in the issue or run report; execution counts show `0 ready` and `0 live`. Name blocked tickets and
their reasons; do not call that full delivery. The adapter owns waiting and any
explicitly authorized goal. Quoting `/goal` is never a lifecycle operation.
This is the handoff point, not the end of dispatch: complete the review handoff
below or record why it is excluded/blocked before reporting the invocation finished.

## One iteration

1. Re-read the scoped board and canonical tracker issues under the bootstrap's
   project conventions.
   Refresh human changes to scope, criteria and priority before assigning work;
   materially changed active work returns for alignment. A principle the user states
   mid-dispatch is recorded verbatim and checked against the plan under
   [mandate's authority rules](../mandate/SKILL.md#establish-authority). Keep local runtime state
   and canonical issue state distinct, and apply authorized tracker transitions
   at the project's actual milestones. Read pending receipts and attention items
   under [worker waits](../../harnesses/workers/wait.md#wake-and-yield)
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
   [yield gate](../../harnesses/workers/wait.md#wake-and-yield), then yield. Ready work without
   a candidate → identify area/capacity/dependency/integration waits. If none can be
   resolved within scope, record the attempted resolution and block those tickets.
4. For each candidate, from `repo`, ensure `feat/<slug>` and its spec worktree
   exist. A new effort branches from `main` after fetching and comparing it with
   its remote. A stale or diverged local `main`, or a stale consumer checkout used
   as a base, is reported, and the effort branches from the verified remote tip;
   never commit to the user's local `main`. Then create the ticket branch/worktree
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
   Plan the assigned checks using [plan and accept checks](../../harnesses/checks/plan.md#plan-and-accept-checks).
   Verify the runner's current contract and the worker's checkpoint capability;
   carry the runner's currently supported wait/status/log/cancel operations
   ([check execution](../../harnesses/checks/run.md#run-a-bounded-check)).
   Create reports directory, claim the ticket and record implementation started,
   then start `implementer` with:

   ```text
   adapter: <absolute active adapter>  role_file: <plugin_root>/roles/implementer.md
   plugin_root: <absolute>  repo: <absolute main checkout>
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
   [launch decision record](../../harnesses/routing/report.md).
   If spawning fails, reconcile whether a child was actually created before retrying.
5. When a worker finishes, perform the selected board's acceptance checks for report
   structure and branch ancestry; then judge assigned implementation criteria and
   recorded checks in `## Implemented`. Account for every ticket criterion, retaining
   later-phase obligations for their named owners. Those pending gates do not block
   implementation acceptance/integration; they still block delivery until verified.
   Structural acceptance is not a code review.
   Accept the worker's recorded checks at their commit; do not rerun them.
   Collecting through the worker lifecycle records the decision outcome. Otherwise
   record it against that acceptance evidence or mark it unknown, then run the
   [completion record check](../../harnesses/decisions/annotate.md#check-a-handoff)
   for the recorded decision. Preserve any capture gap explicitly; bookkeeping
   failure does not justify repeating implementation or inventing passing evidence.
   Apply [worker return and checkpoints](../../harnesses/workers/focus.md#worker-return-and-checkpoints):
   a failed/incomplete return hands recovery to the host, not verification to the user.
   Missing assigned implementation evidence → blocked with the exact failure in the issue or run report.
   Accepted → retain the [check evidence](../../harnesses/checks/run.md#retain-evidence)
   outside the ticket worktree, verify its report links, then merge its branch in
   the spec worktree. Record implementation integrated, record lifecycle `accepted`
   on the attempt with the integrated commit, and apply the project's
   corresponding tracker transition. Not accepted → record lifecycle `declined` with
   the reason. Retiring its worker first requires an
   [acceptance decision](../../harnesses/workers/collect.md#accept-and-record-outcomes), usually `deferred`
   until these checks finish. Keep the ticket worktree through the remaining
   review/repair and applicable E2E; integration alone does not retire it.
   Once an integrated build allows checks that only the user can observe
   (`Verify (user)`), send the user one request covering all of them.
   On conflict, assign the shared repair role in the
   spec worktree with branch, starting head, integration scope and conflict details.
   No other worker may use that worktree then; the orchestrator completes the merge.
6. A blocked ticket is the orchestrator's work: research missing facts, diagnose
   defects, resolve engineering choices within accepted constraints, or return to
   align/refine for design errors. Apply [escalation checkpoints](../../harnesses/routing/recovery.md#escalation-checkpoints)
   before retrying a worker, and report the retain/replacement decision.
   Read scoped source/diffs when needed to resolve
   the block. Before asking the user to provide or start a resource, check what is already
   available yourself, and name what you checked when you ask. Ask the user only for missing
   context, product choices or actual permission boundaries. Replacing a criterion's
   `Verify` method with a weaker one is the user's decision. Record failed commands
   verbatim. Resolve → ready.
   Two failed attempts at the same ticket → split it around one deterministic
   Verify per criterion; never an unchanged third attempt.
   A worker-role restriction does not establish a human-only task. Separate missing
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

## Review handoff

Stop after implementation only when the user explicitly requested that boundary;
state that review has not run and provide the exact standalone review command.
Otherwise continue in this invocation, without waiting for another user turn.

For each selected effort with integrated changes, finish or reconcile its writers,
then apply [housekeeping](../housekeeping/SKILL.md) to the effort worktree. Commit
intended tracked cleanup/documentation changes there before pinning the review
head; preserve unrelated local edits. Run the
[shared review procedure](../review/workflow.md) on the verified effort branch,
one target at a time. Pass the selected ticket scope, accepted alignment/ledger,
priority sources, project instructions and report path. Include `--autofix` only
when repairs are authorized. If the user explicitly requested a walkthrough before
review, follow [walkthrough](../walkthrough/SKILL.md) first and honor its transition
policy. With no integrated changes, report that there is no review target.

Review the integrated result even if other selected tickets are blocked; record
missing implementation against the selected criteria and keep delivery blocked.
Apply the review's layer dependencies: continue independent scopes, pausing lower
coverage whose contracts or resources depend on a blocked decision.
Do not broaden the assignment to unselected tickets or unrelated branch changes.
Keep a review limited to selected tickets distinct from effort-wide delivery proof.
An active writer that cannot be reconciled safely or unavailable review capability
leaves the handoff blocked with its reason, never silently skipped or marked clean.

Do not call `Skill(automattic:review)` or ask the user to run `/review` to continue
an ordinary dispatch. The public review skill remains user-invoked; its shared
procedure is already part of this user-invoked dispatch. Native tool refusals
remain binding, including those from reviewer dependencies; stop the denied action
and record the gap. There is one review loop, maintained in the shared procedure.

Record its report, scope/coverage, findings and follow-ups alongside implementation
status. With `--autofix`, the shared procedure includes repair integration and
applicable E2E before returning; do not run a duplicate verification phase in
dispatch. Read and execute [Verify autofix through E2E](../review/workflow.md#verify-autofix-through-e2e)
before returning from an autofix handoff, including when all code findings are closed.
`pr` still requires current review/E2E evidence as well as done tickets.
Once the remaining gates are complete or explicitly excluded, retire an unused
ticket worktree through [housekeeping's retirement checks](../housekeeping/SKILL.md#retire-a-worktree).
Keep the effort worktree and any checkout still needed by an active assignment.
Then reconcile the overall queue under the board's continuation rules. Return a
final result only when that scope is complete or cannot progress past documented
blockers; do not end a backlog-wide invocation at the first batch's delivery gate.
Before the result lists an item as unverified, run any check for it that fits the
remaining budget, such as a search, a read or a short command, and report what it
showed. List as unverified only items that need missing access, an owner decision
or a run beyond budget, and name which.
