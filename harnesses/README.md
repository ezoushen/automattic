# Runtime bootstrap

Contents:
- [Long sessions](#long-sessions)
- [Explicit phase composition](#explicit-phase-composition)
- [Project conventions](#project-conventions)

The registered Claude/Codex SessionStart hook or Pi bootstrap extension supplies
`Automattic harness: claude|codex|pi`, the absolute plugin root, and the active
adapter path. Read **only that host adapter** once
per session before using a skill. Resolve shared files relative to the plugin
root (two directories above this skill's `SKILL.md`), never the target repository.

If the hint is absent, an explicit `harness=claude`, `harness=codex`, `harness=pi`
or `harness=opencode` in the user's
invocation selects `harnesses/<harness>/adapter.md`. Do not guess from model names
or the presence of compatibility environment variables. Resolve the adapter and
plugin root before workers start. Consume this selection before forwarding phase
arguments to command-line helpers. The bootstrap supplies context (Pi's also applies the
worker lifecycle's yield gate when a run settles); explicit
harness selection is also sufficient. Native permissions still apply.

Shared docs are grouped by reader, each folder with a README that lists its files:
[workers](workers/README.md) (launch, wait for, collect and retire workers),
[routing](routing/README.md) (choose and report worker models),
[decisions](decisions/README.md) (decision checkpoints and journals),
[checks](checks/README.md) (plan and run checks), [setup](setup/README.md)
(configuration format and procedure) and `executors/` (one guide per executor type).
A link names the file to read; read it whole. Each doc in these folders fits one read, and
a `#anchor` names a section inside it.

Notation such as `/automattic:refine` and `/mattpocock-skills:tdd` identifies a
skill, not a shell command. Use the active adapter's invocation mechanism. Shared
agents and jobs own behavior; host adapters and selected executors own runtime operations.
Resolve dependency identity from the active catalog once per session: for Matt use
the exact `mattpocock-skills:<name>` entry (or its verified host alias/path), never
a bare colliding name such as `tdd`. Carry that resolved identity into
workers; an unavailable dependency is a gap, not permission to substitute a
similarly named bundled skill. Refresh discovery after installation changes.
Memory and copied alignment are discovery hints for runner capabilities; verify
their claims against the current installed runner contract before distributing
assignments. If deployment is uncertain or changed, record the resolved plugin
root/version and relevant agent/job/skill content hashes once, and verify workers use
that source. A fresh development checkout is not proof that another host loaded it.
No script is copied to a
project. `plugin_root`, `repo`, `adapter`, `agent_file` and `job_file` in worker messages are
absolute paths, not assumed shell variables.

Orchestrators and workers follow shared [assignment focus](workers/focus.md)
for priority, scope and concise updates.

Before mandate/alignment questions, read the shared
[question filter](../skills/mandate/SKILL.md#filter-questions), including when the
user asks to "grill" the current plan. It owns question depth and continuation;
the dependency's exhaustive interview requires an explicit request for that depth.

Before each direct worker assignment, the orchestrator resolves
[optional executors](workers/launch.md). Unconfigured native dispatch retains its existing
preferences. Configured execution applies the resolved settings once to one worker.
Pools use a routing skill, a System One decision model or a sparse profile under [selection](routing/choose.md).
`selection_required` is an internal request for a decision, not executable settings.
Use the named `selection_router` and submit the result before dispatch.
Announce the [routing decision and attribution](routing/report.md).
Worker blockers and review/check failures invoke [escalation checkpoints](routing/recovery.md#escalation-checkpoints)
before the next attempt; ordinary resumes reuse the saved choice.

Include workers launched by dependency skills during planning/research in the same
capacity and assignment log. Where a configured agent applies, resolve it before
launch; otherwise record the dependency's native selection and its provenance.
Retain the assignment's stopping condition and observed model/effort; label missing
execution evidence instead of treating a hard-coded model as a routed choice.

Before the first phase checkpoint, inspect effective `decisions.enabled` using
offline status for this repo/session and retain it until configuration changes.
When any family is enabled, run the [configured checkpoint command](decisions/checkpoint.md#configured-checkpoint-command)
at each reached phase's named boundary and check its expected phase record before
handoff. Include an evidence-backed skip when no consultation is needed. With no
enabled families, retain the ordinary host flow without a journal or phase checks.
Worker selection already calls the shared helper; it does not cover alignment,
review triage or recovery. Recovery chooses an action before any worker reselection.
Surface new calibration warnings
with their cause and recalibration action, deduplicating unchanged warnings.

Explicit `--config-profile` or `AUTOMATTIC_PROFILE` selects a routing profile;
otherwise use the configured router, defaulting to the built-in routing skill.
Profile lookup is by agent and worker runtime, not caller. Consume selection options
before forwarding phase arguments to the scheduler or review target helper.
When `HERDR_ENV=1`, also read [Herdr environment guidance](herdr.md) before
cross-runtime dispatch, even when no startup hook supplied it. Carry root-session
identity and canonical repo to assignments; retain their resolved settings on resume.
Workers own their bounded task; further scoping and delegation belong to the
orchestrator under [job lifetime](workers/resources.md#resource-and-job-lifetime).
Agent-chosen thinking changes require the selected agent's allowed set or legacy
opt-in and the
[automatic adjustment path](workers/thinking.md); explicit
user override flags are not a substitute for that permission.
`/automattic:setup-automattic` guides configuration and `/automattic:models` handles direct
settings requests. Both use the [configuration procedure](setup/procedure.md) only
for user-requested changes; workflow execution reads
configuration without invoking either explicit-only skill.

## Long sessions

Correct procedure must survive compaction:
- **User corrections to how you work.** Routing, reporting, retention, permissions
  and principles are recorded when the user makes them, in the ledger's
  `## Standing directives` section (see
  [mandate](../skills/mandate/SKILL.md#record-and-continue)) or the host's project
  memory. A compaction summary is not a
  durable store.
- **After a compaction or resume,** re-read the active adapter and this bootstrap
  before the next worker launch or phase checkpoint. Reconcile the run report
  before answering status questions.
- **The host model's context window has to fit the work.** Orchestrate with a
  model of at least about 200k tokens of context; a 131k host overflowed mid-dispatch.
  Compact before the limit. If a host-model error drops a user request, tell the user which request
  did not run; don't let it vanish.

## Explicit phase composition

When the user explicitly requests refinement after another task, such as research,
use the [shared refinement procedure](../skills/refine/workflow.md) once its input
is ready, where the active runtime permits direct procedure loading. Do not call
an explicit-only skill through a forbidden tool or infer refinement from research
alone. Preserve native invocation policy: if a separate user invocation is required
or the operation is denied, retain the input and explain that restriction; do not
route around it. Dispatch's automatic review remains its own documented handoff.

## Project conventions

Follow current user direction, then the project's established workflow. Read its
`AGENTS.md`/`CLAUDE.md`, relevant project docs and any existing
`docs/agents/issue-tracker.md`; that filename and Matt's setup are not prerequisites.
Use the configured tracker and destination (for example Linear team/project or
GitHub repository/project), issue templates, labels, priority rules and status
transitions. Matt's offered integrations are not an allowlist. A Git remote or
an available connector alone does not establish a project-management convention.
Ask only when a material destination or convention remains ambiguous; with no
configured tracker, use local Markdown without requiring setup or migration.

The configured tracker is authoritative for work items. Read existing issues
before creating any, reuse their IDs/URLs, and carry accepted scope/priorities
forward. Use the project's available CLI/connector and existing authorization;
configuration alone does not authorize publishing drafts or contacting others.
An unavailable tracker is a reported blocker for dependent operations, not a
reason to silently create a competing local backlog or switch providers.

Dispatch reads and updates the configured board directly using its
[board operations](../skills/dispatch/board.md). Remote trackers do not require
local issue files or a mirrored backlog. Local ticket files and their Python
scheduler apply only to the local Markdown choice. The orchestrator owns tracker
updates as authorized by the task and project convention; workers report evidence
to it. Implementation integrated does not imply remote closure: the project may
require review, merge or release before closure.
Before creating a PR, editing its title or body, or pushing to a PR branch,
whether invoked as `/automattic:pr` or not, read the
[PR writing guide](../skills/pr/writing.md). Each such push or edit is a `delivery`
boundary and is followed by the PR skill's required-check watch.
Reconcile human edits at phase boundaries instead of overwriting them. Keep
unpublished review follow-ups local until their publication is authorized.
