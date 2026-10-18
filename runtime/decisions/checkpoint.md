# Checkpoint command and decision requests

Contents:
- [Phase checkpoints](#phase-checkpoints)
- [Configured checkpoint command](#configured-checkpoint-command)
- [Low-level decision request](#low-level-decision-request)

## Phase checkpoints

Before the first phase checkpoint, inspect effective `decisions.enabled` using
offline status for this repo/session and retain it until configuration changes.
When any family is enabled, run the [configured checkpoint command](#configured-checkpoint-command)
at each reached phase's named boundary and check its expected phase record before
handoff. Include an evidence-backed skip when no consultation is needed. With no
enabled families, retain the ordinary host flow without a journal or phase checks.
Worker selection already calls the shared helper; it does not cover alignment,
review triage or recovery. Recovery chooses an action before any worker reselection.
Surface new calibration warnings
with their cause and recalibration action, deduplicating unchanged warnings.

## Configured checkpoint command

Use this entry point for phase decisions:

```bash
<plugin_root>/.venv/bin/python -B <plugin_root>/scripts/decisions.py checkpoint \
  --repo <canonical-project> --family <family> --request <absolute-request.json> \
  --journal <absolute-session-decisions.jsonl> --assignment-id <phase/scope/revision>
```

A disabled family returns a `disabled` skip without writing the journal, whether or
not `--request` is supplied. The family/assignment check reports it complete only
when decisions are configured and the journal holds no checkpoint for that family
and assignment under any session; an existing record is always checked, and a
missing configuration reports the checkpoint missing rather than disabled.
For an enabled phase with no discretionary choice, replace `--request` with
`--skip settled|required-action|human-reserved --reason <concrete-reason>` and
one or more `--evidence <reference>` arguments. Requests and explicit skips are
mutually exclusive. Evidence references identify the accepted plan, gate,
authorization rule or retained result; an unsupported assertion is not proof.

The recorded result contains `checkpoint_id`, `checkpoint_status` and either the
captured `decision_id` or skip reason. On a configured consultation,
`checkpoint_recorded: false` exposes a capture gap; it is not a completed checkpoint.
Record host acceptance/override and outcomes for
consultations using the [existing journal commands](annotate.md).

Check the expected phase identity before leaving that phase:

```bash
<plugin_root>/.venv/bin/python -B <plugin_root>/scripts/decision_journal.py check \
  --journal <absolute-session-decisions.jsonl> --repo <canonical-project> \
  --family <family> --assignment-id <same-phase/scope/revision> \
  --stage completion --revision <checked-head-or-identity>
```

Use `--stage launch` before acting on a consultation, and `completion` after its
outcome is known or explicitly recorded as unknown with pending evidence. Use
the same `--session <root-session-id>` on both commands when applicable. The check
exits 1 for missing checkpoints or required annotations and 2 for invalid input.
Completeness is bookkeeping, not evidence that a quality gate passed. Skips need
no synthetic action or outcome. Completely unconfigured workflows can receive a
disabled result without creating a journal; they retain the ordinary host flow.

An unchanged resume returns `reused: true`, including an abstention or backend
failure, without another inference or calibration call. Concurrent duplicate
submissions share one consultation. A changed question, options (including order), relevant
configuration or skip evidence requires a new phase identity. For Git scopes,
include the relevant revision in that identity; do not reuse a skip after its
evidence changes. If only checkpoint capture failed, a retry can recover the
already captured decision locally. If decision capture itself failed, retain the
returned result and report the gap; do not repeat inference just for bookkeeping.

The host identifies phases, supplies task-specific options and judges
evidence. The helper does not intercept arbitrary tools or infer phase transitions
from prose. Native permissions and required checks remain authoritative.

## Low-level decision request

The [request schema](../../schemas/decision.schema.json) contains `family`, `state`,
`instruction`, an `options` map of labels to descriptions and optional ordered
`images`. The helper adds
`abstain`; callers supply 1–254 options. State/instruction are bounded to 16000
characters each; request text and the response are each limited to 64 KiB.
Images have [separate limits](images.md). Send the narrow relevant
facts, not transcripts, entire repositories or secrets. Retain the request with
the assignment when needed for evidence, using existing project conventions.

```bash
<plugin_root>/.venv/bin/python -B <plugin_root>/scripts/decisions.py decide \
  --repo <canonical-project> --request <absolute-request.json> \
  --journal <absolute-session-decisions.jsonl> --assignment-id <assignment/attempt>
```

Use `--session <root-session-id>` for session overrides; `AUTOMATTIC_SESSION` also
applies. `--user-executors` selects an alternate user configuration for evaluation.
No subprocess worker is created. `recommended` includes the choice and proposer;
`host_required` means disabled, abstained, failed or invalid. Resume reuses the
accepted decision until relevant evidence changes. The caller links assignment,
attempt and evidence identity through the returned `decision_id` in its existing
report. With `--journal`, the helper records the exact composed request, raw response,
validated result, model/configuration fingerprint and request latency. Failed calls
are recorded too. The [journal](journal.md), [annotation](annotate.md) and
[retrospective](retro.md) procedures cover host actions, runtime settings
verification, outcomes, offline retrospectives and bounded prompt replay. Recording adds no inference
and calibration traffic is excluded from the session journal. The helper remains
stateless about assignment execution; it never dispatches or retries work.

Scores and confidence retain the provider's meaning. They do not establish factual
correctness or authorization. Record actual proposer, host acceptance/override,
action and evidence. Attribute the host's explanation to the host. Surface new
`warnings` to the user once per session/cause, then retain them in the report.
