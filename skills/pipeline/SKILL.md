---
name: pipeline
description: "The map of the idea-to-PR pipeline: which skill to reach for, what each owns, what each hands on."
disable-model-invocation: true
---

# pipeline

Contents:
- [Guides and configuration](#guides-and-configuration)
- [The outer loop](#the-outer-loop)
- [Failure modes and where the loop catches them](#failure-modes-and-where-the-loop-catches-them)
- [Re-entry](#re-entry)
- [Flows](#flows)
- [Matt Pocock's skills underneath](#matt-pococks-skills-underneath)
- [Left to the human](#left-to-the-human)
- [Delivery composition](#delivery-composition)

First read: [runtime bootstrap](../../bootstrap.md), the host session part.

The automattic plugin: six phase skills, one artefact directory `.scratch/<slug>/`, one principle: the
principal answers **steering** questions (goal, principles, constraints) and
**context** questions (what the machine cannot know); the agent decides everything
else and records consequential choices as a ledger row — number, decision, hinge, rejected
alternatives — the principal can veto. All three planning skills append to one
`ledger.md`.

| Phase | Skill | Owns | Writes | Hands on |
|---|---|---|---|---|
| Interview | `/automattic:mandate` | the question filter; the mandate's tree (goal, principles, constraints, context); the ledger row shape | `ledger.md` (first rows), standing principles in `CONTEXT.md`/ADRs/memory | slug, ledger |
| Alignment | `/automattic:align` | WHAT / WHY / HOW, depth proportional to risk; reuse accepted decisions and ask only material forks | `alignment.md` | the brief |
| Refinement | `/automattic:refine` | ticket slicing, edges, sizing and their rejected alternatives | configured tracker issues, or local Markdown tickets | dispatch-ready tickets |
| Execution | `/automattic:dispatch` | scheduling on `blocked_by`, capacity and area locks; worktrees and integration; builder evidence and merge-conflict jobs; handoff to shared review | `reports/*.md`, `feat/<slug>` | implementation status and review report |
| Review | `/automattic:review` | direction → blast radius → implementation, complete layer batches, scoped invalidation, reproduction, optional autofix with applicable E2E, local comment drafts and follow-ups | review and verification report | reviewed commit, gate outcomes and unresolved findings |
| Delivery | `/automattic:pr` (optional) | the description assembled from the artefacts above | `pr.md`, the PR | a URL |

## Guides and configuration

For a change you want to understand before assessing it, use
[/automattic:walkthrough](../../flows/review/guided.md). It teaches and discusses the PR,
then can hand agreed criteria into the same review procedure when requested.
It is optional; direct review starts assessment without this learning step.

Configuration is optional and separate from the delivery phases. Use
/automattic:setup-automattic to understand the current setup and update it
at user, project or session scope. Use `/automattic:models` for direct settings requests;
see [configuration examples](../../runtime/config/executors.md). Existing native behavior
continues without configuration. Setup does not start workers or change review gates.

Optional [workflow decisions](../../runtime/decisions/phases.md) use a shared backend only
at explicitly enabled checkpoints. Worker selection chooses within the allowed pool;
recovery considers the cause before rerouting. The host accepts or overrides each
recommendation, reports its source and surfaces calibration warnings. Existing
phase owners and gates remain in place; there is no second planning/review loop.

Dispatch reuses [existing project execution facts](../../flows/board/project-loop.md):
commands, areas/resources, verification and environment constraints. Missing
facts go in the effort's alignment/report; no new maintained setup file is required.
Run history stays in reports/journals. Workers call shared plugin scripts directly.

## The outer loop

Loop engineering is the design of the loop that drives agents, so a human does not.
The inner loop is the agent's own (perceive, reason, act, observe — `/mattpocock-skills:tdd`); the
outer loop is this pipeline's, and each skill is one of its nodes:

| Node | What it does here | Skill |
|---|---|---|
| Intent | success criteria and constraints: the mandate's limits, the brief, every criterion's `Verify` command | `/automattic:mandate`, `/automattic:align`, `/automattic:refine` |
| Context | a state payload, not a conversation: ticket, brief, project vocabulary/instructions, absolute paths | `/automattic:dispatch` prompts |
| Action | one fresh builder per ticket in its own worktree | `/automattic:dispatch` |
| Observation | the report's recorded evidence; board acceptance checks; scoped review with repros; applicable verification | `/automattic:dispatch`, shared review procedure |
| Adjustment | use blocker/failure evidence to correct context, environment, approach or worker; preserve scope and attempt limits | `/automattic:dispatch`, shared review procedure, re-entry below |

Issue state lives in the configured board; execution evidence lives in reports
and the ledger. Read both fresh every iteration. Local front matter applies only
to projects using local Markdown tickets.
Policy is the contracts: scoped source reads when needed, no `main` from a subagent,
area locks and device reservations, runtime capacity, native permissions and
human-authorized merge by the orchestrator.

## Failure modes and where the loop catches them

| Mode | Symptom | Caught by |
|---|---|---|
| Thrashing | an agent edits without converging | one `Verify` command per criterion; dispatch handles non-converging tickets; review keeps per-finding repair limits across E2E failures |
| Overfitting tests | suite green, behaviour wrong | verify the accepted behavior and affected entry points; satisfy the project's applicable compile, suite and E2E gates |
| Context drift | work on stale assumptions | fresh context per ticket; canonical board refreshed each iteration; reviewer verifies its range first; a resumed agent is told what survived |
| Unsafe autonomy | over-reach or destruction | subagents never push, merge or touch `main`; native permissions; runtime capacity; human-authorized merge by the orchestrator |
| Comprehension debt | the human stops reading | consequential ledger rows and a concise alignment brief; only material questions; on-demand briefings and walkthroughs; a proportional PR description |

## Re-entry

- A blocked ticket whose cause is a missing **fact** → `/mattpocock-skills:research`; a **defect** →
  `/mattpocock-skills:diagnosing-bugs`; a **contract decision** → resolve against accepted
  priorities and record the deciding source; unresolved conflicts return for human
  alignment while independent work continues, not a retrospective rewrite of criteria; a **wrong
  design** → `/automattic:align` at the affected level, then `/automattic:refine` re-cuts.
- A question no level can settle on paper → `/mattpocock-skills:prototype`; its answer returns as a
  row.
- A veto or a steering answer is recorded where `/automattic:mandate` establishes authority, so the
  same question is decided, not asked, next time.

## Flows

Each phase skill is a thin entry over a flow folder; shared runtime rules sit below the flows.

- [Planning](../../flows/planning/authority.md): authority, the question filter, the ledger record and refinement.
- [Board](../../flows/board/board.md): tracker conventions, scope and the project loop.
- [Delivery](../../flows/delivery/dispatch.md): dispatch, housekeeping, PR and the ticket and merge-conflict jobs.
- [Review](../../flows/review/review.md): the shared review procedure and its jobs.
- [Remediation](../../flows/remediation/procedure.md): the audit procedure and job.
- [Setup](../../flows/setup/procedure.md): the configuration procedure.

## Matt Pocock's skills underneath

Dependency: `mattpocock-skills`. Reuse `tdd`, `research`,
`diagnosing-bugs`, `domain-modeling`, `prototype` and `grilling` for their respective
work. Planning uses [mandate's question policy](../../flows/planning/question-filter.md)
with grilling's internal design-tree reasoning. The review skill supplies scope,
priority and allowed mutation
context and its own [Standards/Spec method](../../flows/review/method.md). Simplicity is part of that review.
Honor each dependency's actual invocation
policy in the active catalog; never bypass a denied invocation by copying its body.
For PR descriptions, the [PR guide](../../standards/pr.md) owns structure,
evidence, refresh and self-check. The PR phase (`/automattic:pr`) owns delivery
evidence and publication.
Planning and execution skills keep shared methods by reference (`/automattic:refine`
applies `/mattpocock-skills:to-tickets`' slicing rules unchanged). `/automattic:refine` also
accepts Matt's `spec.md` and prose `/mattpocock-skills:to-tickets` tickets, adapting them to the
project's ticket convention.

## Left to the human

Authorization for merging `feat/<slug>` into `main`, releases and lockstep repins
belongs to the human; the orchestrator carries out those steps when already
authorized. Retrospective evidence stays in the existing reports or journals.

## Delivery composition

Dispatch's handoff applies housekeeping and runs the [shared review
procedure](../../flows/review/review.md); only an explicit implementation-only request
omits review. Existing accepted alignment supplies scope, non-goals, priorities
and test seams. Without those decisions, review records provisional priorities or
asks for material human choices. Follow-ups never expand the current review batch;
dispatch's [overall selection](../../flows/board/scope.md)
determines whether they enter the next batch under existing authorization.

`review --autofix` owns scoped repairs, local effort integration and applicable E2E
verification, using the verifier's e2e-gate job and board reservations. Dispatch with
autofix uses that same procedure. Reuse its result; there is no second E2E phase
in dispatch or PR. Standalone read-only review remains a review/comment workflow.

Autofix continues until review, documentation and applicable verification gates
pass, or records concrete blockers. It does not require a separate full-delivery
request to run tests. For an Automattic effort the shared procedure also checks the
board's delivery gate. PR remains a consumer of that completed evidence and owns
its description/publication; invoking PR does not start testing or grant repairs.
Implementation-only and read-only requests can therefore leave delivery gates
unsatisfied, which their final reports must state.
