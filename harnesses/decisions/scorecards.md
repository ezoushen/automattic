# Worker quality scorecards

Use `decision_journal.py scorecard` to summarize worker outcomes by task family
and observed runtime/model/effort. It reads existing execution/outcome annotations
offline, makes no backend calls and changes no routing configuration. Decision
backend confidence and choice accuracy do not grade implementation or review work.

Before a comparison, fix the task-family rubric, case inputs and acceptance gates.
Start from the [empty manifest](../../benchmarks/worker-scorecard.example.json), replacing
its illustrative candidates and references with permitted native settings and
pinned evidence. One manifest declares one `controlled` or `historical` cohort and
one context policy: `fresh` or `same-assignment-continuation`. Keep these cohorts
separate. Continuation still requires the lifecycle's explicit same-assignment
retention; a scorecard declaration grants no permission to reuse a session.

Each case has `case_id`, `input_revision` matching the execution's starting revision,
and an `acceptance` reference identifying its unchanged gates. Each trial references
one unique worker-selection `decision_id`, its `case_id`, checked result `revision`,
native `worker` identity and independent `reviewer` identity. Add the review's
`verdict` (`accepted`, `rejected`, `unknown`), `category` (`none`, `implementation`,
`environment`, `provider`, `unknown`) and nonempty `evidence` references. For example:

```json
{
  "case_id": "example-contract",
  "decision_id": "<recorded-worker-selection-id>",
  "revision": "<independently-checked-result-head>",
  "worker": "<native-implementation-session-id>",
  "reviewer": "<independent-review-session-id>",
  "verdict": "accepted",
  "category": "none",
  "evidence": ["<retained-review-and-gate-proof-at-result-head>"]
}
```

The host verifies the references, native identities, review independence, rubric
predeclaration and the declared mode, context policy, task family and case IDs.
Those cohort/case labels are host assertions, not derived from the journal.
The reducer checks supplied identities and journal bindings; it
does not inspect artifacts to adjudicate quality or prove those assertions. A
successful worker self-report alone is insufficient. Record the host's checked
outcome before scoring; an independent review that finds an implementation defect
requires a failed outcome and rejected verdict against that result revision.

```bash
<plugin_root>/.venv/bin/python -B <plugin_root>/scripts/decision_journal.py scorecard \
  --journal <absolute-session-decisions.jsonl> --cases <absolute-manifest.json>
```

The report retains trials and exclusion reasons, input/rubric references, snapshot
hashes, declared candidates and per-case sample counts. A quality score is available
only when every declared case has graded evidence for that candidate. It is the
mean of case acceptance rates multiplied by 100, so repeating an easier case does
not increase its weight. This is an observed acceptance score, not a universal
model ranking or a statistically validated estimate. Unequal sample counts and
historical task selection still require interpretation.

Use accepted/none for success, rejected/implementation for a model defect, and
unknown with the applicable operational/unknown category when no quality verdict
is available. A missing decision ID makes the manifest invalid and aborts scoring;
a non-worker-selection decision is excluded.

Missing/stale outcomes, mismatched/unobserved settings, changed inputs, undeclared
candidates, self-review and conflicting verdicts are excluded. Provider/environment
failures and unresolved causes remain in the report but do not count as model
defects. Unmeasured candidates and incomplete case coverage remain ungraded.

Accepted trials report each recorded metric's trial-weighted mean and available
sample count. Compare these means only with the same case mix and metric coverage;
unequal repeats can change a speed/cost mean without changing per-case performance.
A metric for an ungraded candidate does not justify selection.
Use `verified_completion_seconds` for the full assignment through accepted review,
including retries, repair and verification; use `host_recovery_seconds` for measured
recovery. Retain source references with the outcome. Native token/cache counters
may be recorded under their original meanings; missing fields remain absent rather
than zero. Preserve operational failure metrics in trial details. Token counts and
cache ratios do not establish dollars or subscription credits.

Use comparable task-family evidence in the existing selection's assignment summary
and evidence references. Inspect acceptance first, then verified completion time
and measured expense. Preserve allowed candidates, explicit pins and fallback for
ungraded models; the reducer neither picks a winner nor applies settings.
