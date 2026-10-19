# Runtime bootstrap

The registered Claude/Codex SessionStart hook or Pi bootstrap extension supplies
`Automattic harness: claude|codex|pi`, the absolute plugin root, this bootstrap and the
active host's session part (`hosts/<host>/session.md`). Read this file and **only that
host's session part** once per session before using a skill. Resolve shared files relative to the plugin
root (two directories above this skill's `SKILL.md`), never the target repository.

If the hint is absent, an explicit `harness=claude`, `harness=codex`, `harness=pi`
or `harness=opencode` in the user's
invocation selects `hosts/<harness>/session.md`. Do not guess from model names
or the presence of compatibility environment variables. Resolve the session part and
plugin root before workers start. Consume this selection before forwarding phase
arguments to command-line helpers. The bootstrap supplies context (Pi's also applies the
worker lifecycle's yield gate when a run settles); explicit
harness selection is also sufficient. Native permissions still apply.

Shared docs are grouped by reader, each folder with a README that lists its files:
[workers](runtime/workers/README.md) (launch, wait for, collect and retire workers),
[routing](runtime/routing/README.md) (choose and report worker models),
[decisions](runtime/decisions/README.md) (decision checkpoints and journals),
[checks](runtime/checks/README.md) (plan and run checks), [config](runtime/config/README.md)
(configuration format) and `hosts/executors/` (one guide per executor type).
A link names the file to read; read it whole. Each doc in these folders fits one read, and
a `#anchor` names a section inside it.

Notation such as `/automattic:refine` and `/mattpocock-skills:tdd` identifies a
skill, not a shell command. Use the active adapter's invocation mechanism. Shared
agents and jobs own behavior; host adapters and selected executors own runtime operations.
Resolve dependency identity from the active catalog once per session: for Matt use
the exact `mattpocock-skills:<name>` entry, never a bare colliding name such as `tdd`
([before a launch](runtime/workers/before-launch.md) has the rest).

Orchestrators and workers follow shared [assignment focus](runtime/workers/focus.md)
for priority, scope and concise updates.

`/automattic:setup` explains configuration and handles direct settings requests, only for user-requested changes;
workflow execution reads configuration without invoking that explicit-only command.

## Triggers

Each rule below fires outside its owner's document: when the trigger occurs, read the owner, whatever skill is running.

| When | Read |
|---|---|
| Before creating a PR, editing its title or body, or pushing to a PR branch, invoked as `/automattic:pr` or not | [PR writing guide](standards/pr.md); each such push or edit is a `delivery` boundary followed by the [required-check watch](standards/pr.md#watch-the-required-checks) |
| Before mandate/alignment questions, including a request to "grill" the plan | [question filter](flows/interview/question-filter.md): it owns question depth and continuation; the dependency's exhaustive interview requires an explicit request for that depth |
| Explicit phase composition, such as refinement after research | [refinement procedure](skills/refine/SKILL.md#explicit-phase-composition) |
| Before each worker launch, including workers that dependency skills launch | [launch](runtime/workers/launch.md), [before launch](runtime/workers/before-launch.md), then the host's worker part, which its session part names |
| Worker blockers and review/check failures, before the next attempt | [escalation checkpoints](runtime/workers/recovery.md#escalation-checkpoints); ordinary resumes reuse the saved choice |
| Before the first phase checkpoint, when `decisions.enabled` has a family | [phase checkpoints](runtime/decisions/checkpoint.md#phase-checkpoints) |
| `HERDR_ENV=1`, before cross-runtime dispatch, even when no hook supplied it | `hosts/herdr.md` |
| Choosing or updating a tracker, board or destination; project workflow | [tracker and project conventions](flows/board/conventions.md), [board operations](flows/board/board.md) |
| After a compaction or resume | re-read this bootstrap and the host session part before the next worker launch or phase checkpoint; [long sessions](runtime/workers/long-sessions.md) |
| A user correction to how you work | record it under the ledger's `## Standing directives` ([record and continue](flows/interview/record.md)) or the host's project memory; a compaction summary is not a durable store |
