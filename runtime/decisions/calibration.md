# Calibration and automatic warnings

Calibration here means empirical checking against labeled cases and establishing
a versioned behavior baseline. It does not mathematically calibrate provider scores
or activate confidence-based execution. All recommendations retain host acceptance.

Start with [the synthetic example suite](../../benchmarks/decisions.example.json) for
integration checks. For task-quality evidence, create a held-out suite from actual
assignments and recovery outcomes, label it `adjudicated`, and record the acceptance
evidence for every expected choice. Multiple correct choices and abstention are
supported. Labels must be independently reviewed against the accepted mandate;
the candidate backend must not grade itself. Keep calibration data separate from
prompt tuning. A changed case or label invalidates the previous comparison.

Each case has a unique `id`, a decision `request`, `expected` labels, and `evidence`
explaining the label. The suite has `kind` and 1–200 cases. Include counterexamples,
missing evidence, capability failures, environmental failures and ordinary waits.
Worker cases should preserve actual question wording, option descriptions and
context from the production request. A synthetic suite cannot establish named
worker capability, production accuracy or optimal model cost.

```bash
# Read-only, offline: no inference or state writes.
<plugin_root>/.venv/bin/python -B <plugin_root>/scripts/decisions.py status --repo <repo>
# Explicitly run labeled cases and save/replace the configured baseline.
<plugin_root>/.venv/bin/python -B <plugin_root>/scripts/decisions.py calibrate --repo <repo>
# Replay against the saved baseline without replacing it.
<plugin_root>/.venv/bin/python -B <plugin_root>/scripts/decisions.py check --repo <repo>
```

The report retains case IDs/results, per-family accuracy and deferral rate, empirical
accuracy in confidence bins, and measured decision latency. It omits request state.
The fingerprint includes backend configuration, enabled families, worker catalog/
routes/pools, helper implementation and exact suite contents, including image content
hashes when present. Image cases use the same request shape and require independent
labels. All images are validated before the first benchmark call. Retain source
images with the suite; a text-only suite provides no visual quality evidence.
Image data URLs across a benchmark suite must fit 32 MiB; narrow larger suites.
A `revision` change
invalidates calibration immediately; a silent alias change needs behavioral evidence.
Same fingerprint does not prove unchanged remote weights.

Active decisions check the fingerprint without inference. After every `check_every`
successful service responses, the helper replays the suite, stops starting cases
after 30 seconds and caps request timeouts at the remaining replay budget.
It records state under `$XDG_STATE_HOME/zloop/decisions` (default
`~/.local/state/zloop/decisions`), locking concurrent checks without waiting.
There is no background service and no calibration call during inspection/resume.
Explicit calibration/check replays use the configured per-request timeout.

| Warning | Meaning and next action |
| --- | --- |
| `uncalibrated` | Missing/invalid baseline: prepare labels and run calibration. |
| `calibration_stale` | Configuration, implementation or suite changed: review changes and recalibrate. |
| `calibration_coverage` | An enabled family lacks labeled cases: add representative cases. |
| `visual_calibration_coverage` | This image request's family lacks labeled image cases: use host judgment and collect independently assessed captures. |
| `synthetic_baseline` | Integration examples only: collect adjudicated outcomes before quality claims. |
| `possible_drift` | Per-family accuracy dropped more than `max_accuracy_drop` on identical cases/setup: inspect the named regressions, then recalibrate after resolving or accepting the change. |
| `calibration_unavailable` | Replay/state unavailable or timed out: check health and rerun; quality drift is unverified. |

The default drop tolerance is 10 percentage points, an operational warning threshold,
not a statistical significance claim. Small/noisy samples need human interpretation.
Changes in task mix outside the suite, a model changing without changing these answers,
and production failure rates are not automatically detected. Review accepted worker
outcomes separately; compare total completion cost, including preparation, review,
repairs and fallback, before claiming savings. Backend outages are availability
failures rather than proof of quality drift.

Automatic checks never replace the baseline. Inspection and a warning do not grant
permission to turn a degraded run into the new reference. Persisted regression
warnings recur until a successful check clears them or an explicit calibration
creates a new baseline. The host continues using ordinary evidence-based judgment;
warnings neither weaken gates nor enable additional decision families.
