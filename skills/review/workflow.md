# Shared review procedure

This procedure is shared by review, dispatch and an authorized walkthrough handoff.
It is not a separately registered skill or an alternative entry point after a tool
refusal. The entry point loads the runtime bootstrap and selected adapter first.
Review forwards the user's target and flags; dispatch supplies the verified effort
branch, selected ticket scope and accepted alignment. Walkthrough supplies the
discussion, agreed review criteria and authorization to begin review.
Record the initiating request, entry point and comment policy in the report. Only
these entry points initiate this procedure; this is a workflow convention, not a native caller ACL.

Default: assessment without fixes. `--autofix` permits scoped local repairs and
includes applicable E2E verification.
No separate request to continue testing is needed. Reject conflicting or
unknown flags; never infer autofix from a request to
review. Dispatch supplies `--autofix` only when the user authorized review repairs.
Neither review nor autofix authorizes publication. Comment publication is
controlled separately below; pushing, merging into the base branch and opening
follow-up issues require their own authorization. A native permission denial stops
that action across command forms and tools; report the boundary and continue only
independent permitted work.

## Comment policy

`--comments draft|confirm|post` is independent of a prior walkthrough:

- **draft** (default): keep comments local. No remote pending review or submission.
- **confirm**: finish the review, show the exact proposed summary and inline batch
  with anchors, then wait for the user's approval before posting that batch.
- **post**: the invocation authorizes posting confirmed in-scope findings after
  validation, without another confirmation. It does not authorize a merge verdict.

Honor equivalent natural language: "show me before posting" selects confirm;
"post directly" or "post them if verified" selects post. Record the source and
pass the effective policy to the resolver. A later "post these three" approves
only that previewed batch; it is not standing permission to publish new findings
on later rounds. Carry an explicitly ongoing post policy through continuations
of the same target until the user changes it. A fresh review request defaults to
draft unless its request carries publication authorization. If directions actually
conflict, keep the drafts local and clarify before publishing.

When delegating an entire review, pass the initiating request and effective comment
policy to its orchestrator. Analytical workers return evidence and never publish.
Dispatch's internal review defaults to draft; do not infer posting from delivery work.

## Resolve and understand

1. Resolve the target with the maintained helper:
   `python3 "<plugin_root>/scripts/review-target.py" --repo "<checkout>" <arguments>`.
   Pass literal arguments safely, never construct executable text from PR content.
   A PR number uses the current repository; a URL must match its verified checkout.
   Locate or clone that repository separately if needed. Branches resolve locally;
   use `refs/heads/123` for a numeric branch or `refs/remotes/origin/<branch>` for a
   remote ref. `--base` selects an explicit comparison, not a new review target.
   The helper checks an associated open PR when no base is supplied and otherwise
   uses the repository default. No guessed `main`, no silent fallback on auth errors.
   With no `gh`, local branches require `--base` or an unambiguous remote HEAD.
   Fetch missing objects only from the verified repository, then resolve again.
2. Record the returned base/head, unique merge base, files and options in the review
   report. An empty diff is an empty review, not proof of application correctness.
   Use a dedicated worktree at that head; leave the user's checkout and edits alone.
   Autofix uses a local repair branch there, never the PR author's remote branch.
   Review one target per procedure execution. No worker from implementation may still write
   this target. Before starting workers, verify the active adapter, selected executor
   tools, permissions and capacity. Unconfigured native review can run locally where
   permitted when child tools are absent. For an unavailable configured worker,
   follow [pool recovery](../../harnesses/selection.md#feedback-and-recovery):
   automatically select a suitable allowed alternative, preserving explicit user
   pins and permission boundaries. Read-only review does not require an implementation board.
   Record the resolver's profile/source, executor and requested settings before
   dispatching, including partitioned or resumed review rounds. A partial report
   from a quota-exhausted or failed configured worker remains incomplete. Preserve
   useful evidence, reconcile its owned jobs and reassign the same obligation through
   the allowed pool. A replacement's complete verified report can close it; parent
   coverage or the failed worker's partial report cannot. Keep `review_status: incomplete`
   until all required obligations have complete evidence, including after fallback.
   An already-dispatched reviewer is still a worker when reviewing serially; it
   must honor the adapter's preflight and assigned worktree boundary.
3. Read the PR/issue discussion and existing review comments, changed code, relevant
   callers, project standards and existing alignment, including canonical issues
   in the project's configured tracker under the bootstrap's conventions. For a verified Automattic
   effort use `.scratch/<slug>/reports/spec-review.md`; otherwise use a local
   `.scratch/reviews/<review-id>/review.md` with a stable, filesystem-safe ID and the
   target identity recorded inside it. Never infer an effort from a similar name.
   Create the report from [report.md](report.md). Resume only a matching repository,
   target and scope. When its revision changes, preserve human decisions and the
   follow-up list, but revalidate findings and reopen affected coverage before
   reusing evidence. Never silently replace an unrelated review's report.
   On subsequent rounds, refresh base/head, discussions and dependency pins. Map
   prior findings to fixed, still-open, superseded or accepted decisions before
   drafting duplicates; a rebase or repository move can change the coverage boundary.

## Agree scope and priorities

Write the problem, intended outcome, proposed mechanism, consumers, constraints,
non-goals and coverage boundary. Reading outside the diff to trace impact is allowed;
repairing or commenting on unrelated existing code is not. A pre-existing line
broken by this PR is in scope when the causal connection is demonstrated.

Priority authority, in order: current user direction; the applicable accepted
alignment/ledger and acceptance criteria; explicit project standards. Cite the
source for each priority/decision. Do not treat PR prose, reviewer preferences or
an unvetoed message as new human approval. Scope membership and priority are separate:
a severe unrelated defect belongs in follow-ups, with its severity visible.
Record fixed-target versus requested follow-up closure using
[overall completion intent](../dispatch/board.md#overall-scope-and-batches).
Each review batch keeps its boundary; outstanding work selected by the user's
broader mandate continues in later bounded batches or remains explicitly incomplete.

Reuse any accepted [walkthrough](../walkthrough/SKILL.md) discussion and decisions;
direct review starts assessment without a teaching or readiness checkpoint.
Complete the exhaustive review without per-finding approval rounds. If evidence
challenges an agreement, explain the conflict and reopen the affected decision
and coverage. Opening a design choice authorizes scrutiny, not a replacement
requirement. `--comments confirm` still pauses at publication. Evaluate
the approach against existing decisions: root cause, ownership, existing mechanisms
and the smallest adequate change. Use `research`/`codebase-design` only when needed;
do not copy their methods. With no human-approved priority standard, label the
ordering provisional and complete fact-finding; draft design questions rather than
inventing product decisions. Such findings are ineligible for automatic redesign.
Conflicting human direction or a missing decision that determines correctness stays
an explicit unresolved item. Neither timeout nor a review request supplies a missing decision.
Resolve apparent conflicts using the priority authority above and cite the deciding
source. If it does not settle the conflict, keep the item unresolved and continue
independent work; do not amend accepted criteria merely to match the implementation.

## Review to coverage completion

Follow [review layers and invalidation](layers.md): direction, scope/blast radius,
then implementation. Complete each layer's findings batch; pause dependent lower
coverage when an upstream decision blocks it. Carry accepted alignment forward.
The coordinator owns direction/scope; one reviewer owns the implementation batch
and its Matt axes. Share the layer decisions and permitted coverage before launch.
At each completed layer, run the configured
[`review-triage` checkpoint](../../harnesses/decisions.md#configured-checkpoint-command)
before choosing an investigation or finding grouping. Identify the layer and head
in its phase assignment and check that record before leaving the layer. This also
applies without autofix; a clean, fully covered layer records an evidenced skip.

Supply the [shared reviewer](../../roles/spec-reviewer.md) with absolute adapter,
role, plugin, repo, worktree, report and scope-source paths; pinned base, diff_base,
head, the full changed-file list, allowed behavior boundary and priority sources.
Keep static reads pinned to Git objects or a stable checkout for the whole review.
Do not share a mutable checkout with E2E that switches base/candidate or changes
experimental inputs; a single startup HEAD check cannot protect subsequent reads.
Dynamic checks need their own reserved stable view and restoration evidence.
Assign one absolute evidence directory outside disposable worktrees and pass it
to reviewers, reproducers, repairers and E2E runners. Write retained evidence there
from the start and verify report links resolve before accepting a result. A
`report_transport: return` worker returns evidence for the orchestrator to persist
within its permissions. Experiments still execute in the assigned worktree.
Pass the actual brief/spec when one exists; do not invent a spec or require tickets
for someone else's PR. Resolve Matt's exact namespaced dependency through the
bootstrap and pass its identity. Use that review once for the eligible implementation
batch; preserve both axes while Automattic owns coverage, evidence and disposition.
The shared reviewer's documentation gate is mandatory: code comments and API docs
are source contracts, including unchanged docs invalidated by the diff. Record
their coverage and `documentation_status` for the pinned head. Confirmed in-scope
documentation defects block approval/delivery for every review; priority determines
repair order, not whether they can be ignored. Unresolved intent/evidence keeps
the gate incomplete. Keep unrelated documentation work in follow-ups.
Another reviewer's approval does not waive these gates or change the user's priority
standard. Choosing not to post a finding does not change its evidence or gate status.

If the project configures an external reviewer and its applicability condition
holds, run it once for this pinned revision with the exact project command/model
and scope. Keep its raw output and model in the report; apply the same scope and
evidence filter to every candidate. Its availability is not a requirement for
standalone review unless the project explicitly makes it a gate.

Continue until every coverage item is reviewed or explicitly blocked, every
candidate is confirmed/dismissed/unverified, and newly implicated paths have been
checked under the layer dependencies. Record blocked dependent coverage explicitly;
it cannot count as reviewed. Reopen only affected coverage when new evidence lands.
Short progress updates do not replace the consolidated result.

Use the [reproducer](../../roles/reproducer.md) for difficult/disputed findings.
No source fixes during validation. Tests and experiments use the isolated worktree;
retain evidence outside it and remove only the experiment edits you introduced.
Record the command, working directory, exit status and diagnostic. A missing file
or failed setup is an execution gap, not a reproduced defect or a disproved finding;
correct permitted setup and rerun before judging the result.
All review checks, including those run by the orchestrator, follow
[check execution](../../harnesses/checks.md) for runner inputs, execution proof and
project-required resource coordination. A remote queue needs no local build mutex.

Out-of-scope candidates go immediately to `## Follow-ups` with location, rationale,
impact, relation to the current goal and the decision needed to pursue them. Keep
stable IDs and deduplicate by root cause. Do not pursue, fix, publish or silently
promote them within this review. Return them to dispatch, whose
[overall selection](../dispatch/board.md#overall-scope-and-batches) may already
authorize triage and implementation in a later batch. Without that authorization,
retain them for a user scope decision. Show important follow-ups at the end without mixing them into
the PR's blockers or letting them consume the active review.
An in-scope question or test waiting on a design decision stays in Findings/Coverage
with that dependency; waiting or assignment to another reviewer does not make it
out of scope.

Some findings stay in scope and cannot be deferred by the agent alone:
- a finding introduced by this batch, including minor ones and comment-rule
  violations such as ticket or decision IDs in code;
- a finding that shares a root cause with selected work;
- a finding that narrows a user decision.

Repair these, or ask the user to defer each one as a numbered decision. "Logged,
not scheduled" in a status message is not a decision.

## Optional repair

Only with `--autofix`, assign confirmed in-scope findings in the agreed priority
order to [repair](../../roles/repair.md). Include the exact allowed files/behaviors,
priority authority and accepted test seams. No automatic fix for unverified claims,
follow-ups, personal taste or unresolved design decisions. A materially wider fix
returns for human alignment; meanwhile finish independent permitted work.

Batch compatible confirmed findings after the layer's findings are consolidated.
Attribute each confirmed finding to the collected worker attempt that introduced it,
when known, with the lifecycle's `attribute --kind review-defect`; a repair attempt
names the attempt it fixes in `repairs`
([worker lifecycle](../../harnesses/worker-lifecycle.md#arm-collect-and-rearm)).
Before assigning the next repair or retry, apply the shared
[escalation checkpoints](../../harnesses/selection.md#escalation-checkpoints)
to this evidence: run the configured `recovery` checkpoint for the action before
deciding who executes it. A worker-routing call alone does not satisfy recovery.
Check this phase record before acting, record its outcome at the repair handoff,
then report any separate worker decision with attribution. An orchestrator-authored
fix after review is a repair too. It needs the `recovery` record and a recheck of
its delta before delivery.
One writer per worktree; one required suite run can cover compatible repairs, while
each finding retains its own deciding evidence. After repairs, verify original
repros and required checks; review the repair delta and affected behavior. Preserve
initial coverage, reopen impacted items, and update the reviewed head only after they pass. Two
unsuccessful repair attempts for the same finding → record blocked with evidence;
continue other findings. No unchanged third attempt. With `--autofix`, continue
through the E2E verification below even if no repairs were needed. A read-only
review does not automatically run E2E.

## Pin review evidence

Before finalizing, re-read the target head and base. If they moved, report this
snapshot as stale and review the delta against a newly pinned pair before claiming
the current PR was reviewed. Preserve user scope decisions; don't carry old inline
locations forward blindly. For autofix, distinguish the local repair head from
the unchanged remote head; preview fixed code locally and leave unresolved comments
anchored only where they remain valid on the actual PR diff.

Set `review_status: clean|findings|incomplete` and `review_head` in the report, and
set `review_by` to the reviewer runs (agent or attempt IDs) that produced it.
Clean requires complete coverage, no unresolved in-scope findings or scope decisions
(including undecided agent deferrals of the three non-deferrable kinds above),
evidence for the pinned revision, and `documentation_status: passed`. A missing
documentation check cannot be treated as passed; an old report needs that review
before reuse. Follow-ups outside this batch don't prevent its clean status;
requested follow-up closure still governs completion of the overall invocation.
Record `review_base` and `review_diff_base` too; a changed base invalidates scope.

## Verify autofix through E2E

For `--autofix`, continue here in the same invocation. A clean review is an
intermediate result, not a reason to stop and ask the user to run pipeline or PR.
The orchestrator owns remaining gates after analytical and repair workers return;
a read-only reviewer's role boundary does not transfer verification to the user.

Determine applicable gates from the accepted scope, project verification commands
and, when present, the project loop file and selected tickets' `touches` union.
Include required compile/suite checks and E2E, not every step listed for unrelated
areas. When the repository has CI workflows, the required gates include every job CI
requires on the PR. Read them from `.github/workflows/` (or the CI configuration in
use). Either run each locally, or record which CI jobs remain to be watched after
the push. Consumer-repository branches made for the effort are review targets as
well. Review each against its own base. Record why operator-only pilots, production rollouts and post-merge checks
fall outside this scope. If such an action is an explicit prerequisite within the
accepted scope, retain it as a real blocker; never silently waive it or execute it
without its authorization. No board or Automattic project file is required for
standalone review; use the repository's existing verification conventions.

For a verified Automattic effort, the orchestrator integrates accepted local
repairs into the effort branch while no worker owns that worktree. Prefer
fast-forward; review any new merge result or conflict resolution before E2E.
Before expensive gates, reconcile the intended integration base and known required
dependency merges under existing authorization. Coordinate who owns the branch
update; another session or remote update may already have moved it. Integrate the
required changes before pinning the verification head, rather than repeatedly
chasing optional base updates while checks run. If the base moves later, inspect
the actual delta and invalidate only affected evidence; required up-to-date rules
still apply.
Confirm `review_head` equals the integrated head. For any other target, verify
the local repair branch without changing the author's branch or the user's
checkout. Finish intended tracked housekeeping changes before pinning that head.

Prepare the per-check reuse/execute plan using
[plan and accept checks](../../harnesses/checks.md#plan-and-accept-checks), including
implementation, review and repair evidence. Pass that plan to the E2E runner;
preserve justified reuse in its assignment rather than replacing it with a demand
for fresh execution of every gate. Missing run preconditions require fresh evidence
from the affected checks; recomputing old results cannot establish them. Schedule
authorized verification under the project's resource rules, including when no code defect
remains. A runtime estimate alone is not a permission boundary; honor explicit
user budgets and resource limits. Ask for a decision only when a concrete boundary
blocks execution or the user proposes an exception, keeping missing proof visible.

For checks requiring execution, use the existing [E2E runner](../../roles/e2e-runner.md), supplying absolute adapter,
role, plugin, repo, worktree, project-instruction and report paths, the reviewed
head, applicable checks, and reusable evidence. Follow the same adapter, permission
and native capacity checks as review workers. With no worker tools, run
locally where permitted. Reserve required devices through the configured
[board operations](../dispatch/board.md), or existing project resource conventions
for standalone review. Do not create local tickets for remote boards or standalone
reviews. Reconcile interrupted reservations and release only after actual teardown.
Supply the expected duration and next milestone under
[worker return and checkpoints](../../harnesses/executors.md#worker-return-and-checkpoints).
Accept a bounded failed/incomplete return promptly and take the existing recovery
action; keep the workflow gated and reuse already completed valid segments.

Feed a failing check back into this review procedure with its exact evidence.
Confirmed in-scope defects enter the existing repair loop; review the repair delta,
integrate when applicable, then rerun the failed and affected checks. Keep the same
finding IDs and repair-attempt counts across E2E; do not restart the retry budget
or spawn another dispatch loop. Continue independent checks when safe. Missing
access, unresolved intent or a wider repair is a reported blocker, not a new gate
approval round for already authorized testing.

Write the check-by-check evidence, reuse reasons, exclusions and gaps under `## E2E`.
Before accepting a pass, verify the scenario's expected versus observed activity
and invalid-run conditions, not just its exit code or the worker's summary.
On resumption, apply [resume interrupted checks](../../harnesses/checks.md#resume-interrupted-checks).
Give each unfinished gate its next action and responsible role, or the concrete
blocker that prevents progress. "Awaiting stakeholder decision" needs an identified
decision beyond executing already authorized verification.
Set `e2e_status: passed` only when every applicable gate is satisfied or has an
explicit project-approved omission; a verified absence of applicable E2E checks
needs a reason. Set `e2e_head` to the validated head, `e2e_by` to the E2E runner run (or the
orchestrator's run log where it ran the checks itself), and retain original execution
heads for reused checks. Any unresolved failed check makes the aggregate `failed`;
otherwise missing evidence/access or unresolved requirements make it `incomplete`.
Keep every per-check failure and gap visible. Neither status certifies verification.
Recheck the target/base and local repair head before finishing; any movement or
new tracked edits reopens affected review and verification. For an Automattic
effort, apply the board's delivery gate after teardown (`--delivery` only for local
tickets). Unimplemented required work or broader uncovered scope still blocks it.
On later user follow-ups, reconcile the selected issues and report before continuing.
New code or relevant environment changes invalidate affected passes immediately:
mark them incomplete, retain the old evidence, and review/verify the delta before
restoring passed status. A completed subset does not certify the whole effort.

Autofix finishes when all applicable review/documentation/verification gates pass,
or with the concrete blockers and remaining checks. Do not leave E2E at `not-run`
merely because review ended. Code publication remains with the PR command;
review-comment publication follows the selected comment policy.

## Finish

Reconcile worker reports into the top-level Coverage and Findings before claiming
completion: replace pending placeholders with reviewed items or explicit gaps,
retain superseded evidence with its final disposition, and align front matter,
documentation status, drafts and summary. An unresolved required decision or
coverage gap keeps the review incomplete; confirmed defects alone mean findings.

Prepare one review summary and inline drafts: finding ID, priority with its source,
type, repository-relative path, LEFT/RIGHT, exact diff line, commit SHA, triggering
condition/evidence, consequence and requested change. Confirm anchors against the
pinned diff. Broad design questions or unavailable anchors belong in the summary.
Retain raw Standards/Spec reports; consolidate duplicate comment drafts with both
source axes attached. Exclude fixed/dismissed findings and unrelated follow-ups.
Use native inline previews where supported; otherwise leave comment-ready text in
the report. Apply the comment policy below. End with scope, coverage/gaps, prioritized findings, repair results
and E2E/verification status when autofix ran, review report location, and the separate
follow-up list. Distinguish a clean review from incomplete verification.
Summaries must preserve the report's finding dispositions and decision sources;
do not summarize accepted exceptions or unverified claims as disproved defects.
When all findings are resolved but required evidence is still incomplete, report
both facts; reserve "review complete" and "verified" for their satisfied gates.
For operational efforts, distinguish script readiness, measured benefit, an adoption
decision, per-target application and rollout verification. Implementation counts and
local integration do not establish those outcomes. Reconcile them and remaining
investigation with the selected issues and dispatch report before claiming completion.

## Publish authorized comments

For confirm mode, present the complete proposed batch before asking once for
approval. User edits or selected IDs define the authorized batch. For post mode,
proceed after validation without asking again. Draft mode ends with local artifacts.
A branch without a verified PR keeps local drafts; comment permission does not
authorize creating a PR. Local autofix commits must not be anchored to an unchanged
remote head or posted as defects already repaired on the remote PR.

Immediately before posting, refresh the PR head, base and discussion. If the range
changed, revalidate affected coverage, findings and anchors first. In confirm mode,
show an updated batch for approval when its reviewed revision or content changes.
Avoid duplicate comments by checking existing threads, including the user's own
previous submissions. Reply to an existing thread when the authorized action is a
follow-up; permission to post new findings alone does not authorize resolving or
dismissing other reviews. Evaluate explicit thread-resolution requests against the
verified fix and native permissions, not an invented prohibition on other authors.

Post only substantiated in-scope claims with valid anchors. Keep uncertain impact
or unresolved contract choices clearly labeled; include questions only when the
user authorized them, never as confirmed bugs. Otherwise keep those concerns local;
`--comments post` alone authorizes confirmed findings, not unverified questions.
Exclude unrelated follow-ups from
both inline comments and the remote summary unless separately requested. If review
coverage is incomplete, disclose its limits while posting any authorized confirmed
subset; publication never upgrades the review or documentation verdict.

Use a COMMENT review unless the user explicitly requested APPROVE or REQUEST_CHANGES.
Verify the returned review/comments against the PR and reviewed commit; record
IDs/URLs, posted finding IDs, revision and authorization source in the report.
On an uncertain or partial response, reconcile remote state before retrying so
already-posted comments are not duplicated. Report posted, withheld and pending
items separately. Do not claim a local draft or pending review was published.
