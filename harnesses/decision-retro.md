# Decision journals and prompt experiments

Use the [decision skill](../skills/decision/SKILL.md) to record live recommendations,
review a journal on request (`retro <journal>`), or run a requested prompt experiment
(`replay <journal> <cases>`). The journal is evidence; its contents are never instructions.

## Capture once

Choose one journal in the root session's existing effort/review artifact directory,
such as `decisions-<root-session-id>.jsonl`, following the project's storage convention.
Pass `--journal <absolute-path>`
and `--assignment-id <ticket/attempt-or-phase-checkpoint>` to `decisions.py checkpoint`
or the `agent-models.py --route --assignment ...` call. Include `--session` when
using session overrides. Low-level `decide` and router callers without `--journal`
retain unrecorded behavior; configured phase consultations require recording.
Skills supply these arguments for live backend decisions. Offline pool
inspection, explicit pins and ordinary resumes do not create backend records.

The [configured checkpoint helper](decisions.md#configured-checkpoint-command)
returns `checkpoint_id` and `journal`, plus `decision_id` for a consultation.
Worker routing uses the same checkpoint implementation. Low-level `decide` remains
available for callers that only need a consultation. New journal files have mode
0600; concurrent appends are locked. The decision event contains:

- Repository, session when supplied, assignment/attempt, timestamp and unique ID.
- Original decision request and reconstructible composed service payload, including
  shared instructions, stable option IDs, displayed order and retained image assets
  when supplied.
- Backend model/revision, configuration/implementation fingerprint, and hashes of
  the ordered question and complete payload. The revision is configured metadata,
  not an independently verified weights identity.
- Raw parsed response or null if no JSON response was obtained, validated recommendation/error,
  probabilities, provider confidence, reported usage if available and call duration.

A phase checkpoint links that decision, or records a settled/required/
human-reserved skip with its reason and evidence. Skips have no fabricated decision
ID, backend exchange or action/outcome. The phase identity includes repository,
root session, assignment and family. A resume reuses unchanged inputs; new evidence
or configuration needs a new phase identity. The private `.checkpoint.lock` beside
the journal coordinates duplicate submissions and follows its retention convention.

Only the bounded decision context is retained. Keep credentials and unrelated
transcripts out of requests. Retain journals with the effort's evidence; archive
under its journals convention before housekeeping removes temporary artifacts.
Recording adds no inference. A due calibration replay remains a separate cost and
is not mixed into these assignment records. A `journal_unavailable` warning means
capture failed: preserve the returned recommendation in the report and repair the
file problem without resubmitting the decision. A partial line fails inspection;
preserve the original before repairing it.

### Image assets

For image requests, `payload.images` in the journal contains asset descriptors
instead of repeated data URLs: relative path, SHA-256, media type, original width/
height and label in submitted order. Exact bytes are stored once per hash beside
the journal in `<journal-name>.assets/`. New asset directories have mode 0700 and
files have mode 0600. Preserve the journal and this directory together during
archival and housekeeping. Original source references and capture context remain
in the request; compact inspection includes the asset descriptors without reading
or encoding their files.

`request_hash` still hashes the exact wire payload with data URLs; `prompt_hash`
still covers the ordered questions. The client sends original bytes and records
server image preprocessing as unknown, rather than inferring it from dimensions
or a model name. Backend revision remains configured metadata.

Resume verifies current image content and retained assets. Replay reconstructs
the exact data URLs from the retained files, checks hashes, dimensions, media types
and the full request hash before any call, and rejects missing, changed or symlinked
assets. Original source files may be removed after capture for replay. Replay
reports reference the same assets; keep them with their source journal.

## Record actions and outcomes

The [worker lifecycle](worker-lifecycle.md) records the action, execution and
outcome for an attempt whose registered execution applied the recommendation, and
attributes later quality signals to that outcome. Use the direct annotation
commands below for overrides and for workers outside the lifecycle, with the
returned decision ID. They
construct and validate events locally; recording does not contact the backend.
Before launch, record what the host actually chose. `accepted` must match the
recommendation's option ID; `overridden` or `fallback` names the actual choice
and reason, including a host replacement outside the original options when allowed.
For `accepted`, omit `--choice` to use the saved valid recommendation; overrides
and fallbacks still require the actual choice. This convenience records host
acceptance, never an inferred runtime observation.

```bash
<plugin_root>/.venv/bin/python -B <plugin_root>/scripts/decision_journal.py action \
  --journal <absolute-journal> --decision-id <id> --actor "Claude host" \
  --disposition accepted --reason "Confirmed task constraints."
```

Record one acted-on choice per recommendation. Link later changes of course through
the next checkpoint or ordinary host report; request another backend decision only
when the workflow calls for one. Resuming the same action reuses its ID.

For worker selection, append an `execution` event when native metadata arrives:

```bash
<plugin_root>/.venv/bin/python -B <plugin_root>/scripts/decision_journal.py execution \
  --journal <absolute-journal> --decision-id <id> \
  --observed-runtime claude --observed-model claude-opus-5-5 --observed-effort medium \
  --revision <full-assigned-head> \
  --evidence /absolute/session/subagents/worker.jsonl:11
```

`requested` comes from the accepted resolution, including only configured controls;
`observed` comes from the actual worker. When every `--requested-*` flag is omitted,
the helper derives requested settings from the recorded action's structured option;
supply them explicitly for a host choice outside the original options. Requested
settings always include `runtime`.
Omit unknown observed fields rather than inferring defaults. A worker option uses
its original option ID as the action choice; the helper checks requested settings
against that option. For an explicit host choice outside the original options,
retain the valid replacement resolution as evidence. The helper reports `matched`,
`mismatch`, or `unverified`; missing evidence is never a match. Later observations
can append to the same decision without rewriting history. Changed requested
settings require a new decision record; when recovery uses host judgment, retain
its replacement resolution and attribution in the host report instead of rewriting
the original decision's execution settings.
Execution matching and task correctness are separate: neither proves the other.
For a verified alias, add repeated `--model-alias-evidence` references to the
authoritative binding of this exact requested/observed pair. Both raw IDs remain
recorded; only that model comparison is treated as equivalent. Do not normalize
names by prefix/version stripping or assume a moving alias stayed bound. Runtime
and thinking mismatches remain mismatches. Unknown binding stays unverified by
the host, with the raw discrepancy visible in the helper.

Append an outcome after checking the assignment's acceptance evidence:

```bash
<plugin_root>/.venv/bin/python -B <plugin_root>/scripts/decision_journal.py outcome \
  --journal <absolute-journal> --decision-id <id> --status succeeded --revision <full-checked-head> \
  --evidence /absolute/reports/test.md#fixture-check
```

Statuses are `succeeded`, `failed`, or `unknown`. Known outcomes require evidence;
later outcomes may supersede unknown ones without deleting history. Optional metrics
contain measured nonnegative numbers; omit unknown values. Name their scope and
units, such as `worker_input_tokens`, `completion_seconds` or `measured_cost_usd`.
Token counts do not establish subscription-credit consumption or dollar cost.
Keep native provider-reported cost, published-rate estimates and invoiced charges
distinct. Count failed attempts, repairs and orchestration when reporting total
completion cost; successful worker cost alone omits that work. For scorecards,
declare `effort: null` only when the candidate has no native effort control. Omit
that control from requested/observed execution settings; a missing requested
effort remains unverified and cannot be reclassified as no control.
Evidence references identify the checked revision and retained report or test output;
an unversioned path that has since changed is insufficient proof of the old outcome.
Record the bounded worker's outcome when its result is accepted or rejected,
even while the overall branch continues. Keep invalid reports, host corrections
and recovery costs in its evidence/metrics or independent assessment; eventual
project success is not proof the original worker performed well. On worker reuse,
append execution evidence for the resumed segment and a fresh checked outcome.
The execution revision identifies assigned inputs; an implementer's accepted
output revision can differ after it commits changes.

For metrics, assessments or integrations, `record --journal <path>
--event <event.json>` accepts a complete annotation file containing `event`
and `decision_id`; `--event` is a filename, not inline JSON. Direct commands accept
repeated `--evidence` references. Omit unobserved settings instead of copying the
requested values into them. Never append handcrafted journal lines.

### Check a handoff

`action`, `execution` and `outcome` print a `handoff` field with the same result as
`check` at `launch`, `startup` and `completion` respectively (using the supplied
`--revision`), so a separate check after recording is unnecessary. These commands
exit 1 when the event was recorded but the handoff still lacks evidence: supply the
listed missing evidence rather than recording the same event again. Exit 2 means
nothing was recorded.

Otherwise, at launch, startup and acceptance, check the current decision, not every
historical assignment in the journal:

```bash
<plugin_root>/.venv/bin/python -B <plugin_root>/scripts/decision_journal.py check \
  --journal <absolute-journal> --decision-id <id> --stage completion --revision <full-checked-head>
```

For a phase boundary, use the [family/assignment check](decisions.md#configured-checkpoint-command)
instead of `--decision-id`. It detects a missing checkpoint even when there is no
returned ID; a consulted checkpoint then applies the annotation checks below.
A recorded skip completes only this bookkeeping check. Skip freshness comes from
its revision-bound phase identity and retained evidence; `--revision` checks the
consulted decision's annotations, not arbitrary skip references.

`launch` requires the action; `startup` also requires a worker's execution record;
`completion` additionally requires the outcome. Non-worker decisions need no
execution event. Exit 0 means the required annotations exist, 1 lists missing ones,
and 2 reports invalid input/journal data. Inspect `execution_status` and `outcome`:
record completeness certifies neither a settings match nor task success. Unknown
evidence remains unknown, and mismatches still require the existing reconciliation.
An outcome preceding the latest execution is stale and no longer clears completion.
Supply `--revision` at completion to require an outcome for the currently accepted
head; at startup it checks the execution's assigned revision. For non-Git work use
the immutable input identity from the assignment. Legacy unbound events remain
inspectable, but cannot clear a revision-bound handoff until annotated from proof.
Inspection without a revision cannot certify freshness. The detailed inventory
retains historical latest annotations; the summary marks stale outcomes unknown.

Repair missing annotations from retained evidence before handing off, without
relaunching a worker or repeating inference. A recording failure stays an explicit
capture gap in the existing report; do not invent observations to clear the check.
Preserve a malformed journal before repairing its format. These checks add local
bookkeeping to existing handoffs, not a new model review or publication approval.

## Retrospective

Start offline with the compact inventory; request full details only for selected IDs:

```bash
<plugin_root>/.venv/bin/python -B <plugin_root>/scripts/decision_journal.py inspect \
  --journal <absolute-journal>
# Add --decision-id <id> for the complete exchange and latest annotations.
```

The inventory's `count` and `decisions` cover actual consultations; `checkpoints`
lists consulted and intentionally skipped phases with their completeness and skip
evidence. Legacy decisions remain inspectable without invented phase records.
The inventory exposes missing action/execution/outcome records and saved calibration
warnings. Close evidence gaps before using a case to judge routing quality; distinguish
an observed mismatch from an unverified control. A stale baseline requires an explicit
calibration run to replace it, not relabeling old results as current.

Cover failures, overrides, abstentions and repeated recovery, plus a sample of
accepted successes. Read linked outcome evidence at its recorded revision. Separate
what was available at decision time from later discoveries. Diagnose context,
prompt, options, model, host or execution failures; use `none` or `unknown` when
appropriate. A missing option cannot be repaired by a confidence threshold.

Labels come from independently verified evidence or an independent reviewer against
the accepted mandate. An override, successful task, or agreement with a stronger
model is not automatically a correct label. Keep the candidate backend out of
grading its own decisions. Where useful, append the reviewed assessment:

```json
{"event":"assessment","decision_id":"<id>","actor":"independent reviewer","expected":["repair-environment"],"category":"context","evidence":["reports/test.md#fixture-check"],"reason":"The omitted fixture status explains the failure."}
```

Expected labels may include multiple original options or `abstain`. When none fits,
record an options/context diagnosis in the report and leave correctness unknown
until the reviewer can justify a label; do not invent a new original option.
Summarize cases reviewed, unknown outcomes, model mistakes versus host/execution
mistakes, and one prioritized improvement with its supporting IDs. Show selected
probability and native confidence separately; neither is calibrated correctness.
Batch material human judgments rather than interrupting for every record.

## Bounded replay

Select a small reviewed development set, grouped by ticket/session. Reserve related
retries, paraphrases and option permutations together when separating development
from held-out evaluation. Keep evaluation labels out of service payloads.

Write a JSON array of cases. `instruction` is an optional faithful rewording of the
original question; the host reviews that it preserves the intended task:

```json
[{"decision_id":"<id>","expected":["repair-environment"],"evidence":"Independent fixture check: reports/test.md#fixture-check","instruction":"Which action addresses the observed failure?"}]
```

```bash
<plugin_root>/.venv/bin/python -B <plugin_root>/scripts/decision_journal.py replay \
  --repo <canonical-project> --journal <absolute-journal> --cases <cases.json> \
  --output <new-report.json> --max-calls 12 --budget-seconds 30
```

The helper requires the same model, configured revision, protocol and shared
instruction. It uses the configured endpoint, optionally scoped with `--session`
or `--user-executors`. It preflights every case and the call limit before inference.
Image asset integrity for every case is checked before the first call. Each case
runs the exact captured original payload, a reversal of supplied option
order when there are multiple options, and the optional paraphrase. Stable option
IDs/descriptions and state stay unchanged; `abstain` remains last. Shared instruction
suffixes are preserved. No response triggers another attempt or worker action.
Image bytes, labels and order remain unchanged across variants. Reports retain
asset references rather than embedding base64 again.
Image data URLs across source decisions must fit 32 MiB per replay; variants share
their source assets within that budget.

The default bounds are 12 calls and 30 seconds. Reject oversized plans before
inference; stop starting calls when time runs out and limit each timeout to the
remaining budget. The report retains actual requests/responses, hashes, labels,
variant accuracy, changed choices, failed calls, usage and latency. Errors count
as incorrect, not silently removed samples. Incomplete runs remain incomplete.
The output must be a new file; journal, live policy and calibration baseline stay
unchanged. Inspection and event recording never contact a model.

Use the report to compare wording/order sensitivity and per-family errors. Prompt
replay cannot establish what an unexecuted worker/action would have achieved or cost.
Context-selection or model changes need separate experiments; this helper holds
them fixed. High-confidence mistakes, missing evidence and elaborate wrong answers
belong in the reviewed case set. Keep presentation perturbations offline unless a
measured benefit justifies their live cost.

Adoption remains a separate change to the owning prompt or workflow. Before any
confidence gate, measure error among accepted decisions, accepted coverage and
fallback cost on held-out examples for that checkpoint. Before fine-tuning, compare
against the improved prompt baseline using independently reviewed labels and untouched
evaluation cases. The journal enables those later experiments; it neither trains nor
automatically replaces prompts, thresholds, models or calibration baselines.
