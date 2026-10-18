# Record actions and outcomes

The [worker lifecycle](../workers/prepare.md) records the action, execution and
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

## Check a handoff

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

For a phase boundary, use the [family/assignment check](checkpoint.md#configured-checkpoint-command)
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
