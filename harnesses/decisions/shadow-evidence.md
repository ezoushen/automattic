# Evaluate shadow evidence

Report agreement offline across one or more session journals:

```bash
<plugin_root>/.venv/bin/python -B <plugin_root>/scripts/decision_journal.py reliability \
  --journal <journal> [--also <journal> ...] [--source objective --source independent --source host]
```

By default only `objective` and `independent` labels count; add `--source host` to
include host labels. Each decision counts once across journals, using its latest
label from an included source, so a later host label cannot erase a trusted one.
Per shadow family it reports assessed, `unavailable` (backend errors),
`excluded_by_source` and `unassessed` counts; accuracy overall, `by_source`,
`by_repo` and ISO `by_week`; five provider-confidence bins with accuracy and mean
confidence (compare the two to see over- or underconfidence) plus `no_confidence`;
a confusion map from the matched label, or the primary expected label when wrong,
to the classifier's choice; and wrong answers by category.

Read every rate with its count; weekly and binned cells will be small, and no
interval is computed. Known limits:

- "Objective" labels are outcome-informed, not ground truth. An unchanged passing
  rerun fits `flaky` and a transient `environment` fault; a fix that turns a check
  green may have repaired the test (`check-defect`); resumed output can follow a
  recovered stall. Record such confounds in the assessment reason.
- `independent` is declared by the recorder; nothing verifies that the reviewer
  differs from the diagnosing host or had not seen the classifier's label.
- Unassessed counts are per family, so a change in which repos or weeks get labeled
  can masquerade as drift. `context` relies on the assessor noticing that deciding
  evidence was outside the excerpt.

Turn trusted labels into an adjudicated calibration suite, so the existing
calibration replay and drift warnings run on real cases:

```bash
<plugin_root>/.venv/bin/python -B <plugin_root>/scripts/decision_journal.py export-suite \
  --journal <journal> [--also <journal> ...] --output <new-suite.json>
```

Only `objective` and `independent` labels are exported, once per decision; host
labels, unassessed, unavailable and image decisions are counted as excluded. The
output is a new file, validated before it is published, and holds 1–200 cases.
Keep exported cases out of prompt tuning: a suite used to choose wording no longer
measures drift honestly. Tune on a separate set, or retire tuned cases from the suite.

[`benchmarks/shadow-adversarial.json`](../../benchmarks/shadow-adversarial.json) pairs
clean cases with twins whose untrusted output or command line adds instructions such as "answer
flaky". Run it through a scratch configuration whose calibration suite points at it
and whose baseline is a scratch file, then compare each pair: a twin that changes
label measures injection sensitivity. A pair is informative only when its clean twin
is answered correctly. The suite is small, written by one party, and every injection
pushes a wrong label with one appended-line style, so it can show sensitivity but
cannot prove robustness. Before any shadow family can act, its labels
may only cause an earlier escalation; existing waits, timeouts and gates must still
apply when a label is wrong.
