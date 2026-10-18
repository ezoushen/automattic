# Retrospectives and prompt replay

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
