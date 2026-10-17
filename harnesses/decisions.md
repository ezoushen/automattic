# Workflow decisions and calibration

Automattic owns the workflow, allowed actions and evidence requirements. An optional
decision backend recommends one of the supplied choices or abstains. The host
accepts or overrides that recommendation and records the source. Matt's methods
continue to own planning, investigation and review; this interface adds no second
planning/review loop. No backend or decision family is enabled by default.

## Configure

Use `executors.json` at user, project or session scope. The complete `decisions`
object replaces the lower scope. Copy the effective object before a partial edit.
Use a separate baseline path for a project/session override so calibrating that
scope does not replace the reference used by other configurations.
The worker `router` remains independent: a skill/profile router keeps its behavior
even if recovery uses the decision backend.

```json
{
  "router": {"type": "decision-model"},
  "decisions": {
    "backend": {
      "protocol": "systemone",
      "endpoint": "http://127.0.0.1:1241/v1/systemone",
      "model": "local/OpenJev-27B-Splash"
    },
    "enabled": ["worker-selection", "recovery"],
    "calibration": {
      "suite": "/absolute/path/to/decisions.json",
      "baseline": "/absolute/path/to/decisions-baseline.json",
      "check_every": 50,
      "max_accuracy_drop": 0.1
    }
  }
}
```

Backend `timeout_seconds` defaults to 20, at most 60. Optional `revision` records a
known deployment/weights revision; change it when redeploying behind a stable model
alias. It is local metadata, not a remotely verified weights hash. Optional
`instruction` adds a shared decision preference. Worker-specific task fit remains
in the catalog and assignment. Backend protocol and model identity are separate:
System One is currently supported; Jev is not a package or service dependency.
Other backends can implement the same internal choice contract.

The earlier inline decision-model router remains supported for worker selection
only when `decisions` is absent. For shared decisions, move its protocol/endpoint/
model to `decisions.backend` and retain `router: {"type":"decision-model"}`.
An explicit `decisions.enabled: []` disables backend decisions, including legacy
worker calls; selection returns to the host. Omission of a family leaves it with
the existing host workflow. No calibration path is a credential store.

## Phase checkpoints

Read effective configuration once per root session, refreshing after changes.
Only enabled families consult [the shared skill](../skills/decision/SKILL.md).
The following defines each extension point; worker selection and recovery are the
initial opt-ins. Other families consult the same helper only after explicit
enablement. When no family is enabled, keep the ordinary host flow without creating
a journal or adding phase checks. With configured decisions, account for reached
boundaries of enabled families through consultations or recorded skips. Disabled
families need no checkpoint or check call: configuration is their record.

| Family | Checkpoint and bounded question | Existing owner retained |
| --- | --- | --- |
| `mandate` | Before grouping unresolved questions: investigate, make a reversible decision, or request material human direction? | User intent, reserved decisions and the question filter |
| `alignment` | After concrete alternatives exist: which alternative or uncertainty deserves investigation? | Matt's design methods, open-ended reasoning and accepted scope |
| `refinement` | After task boundaries exist: which supplied split/group addresses an evidenced gap? | Task identity, dependency validity and acceptance criteria |
| `worker-selection` | After preflight: which permitted model/thinking pair fits this assignment? | Existing router, pins, candidate eligibility and executor |
| `review-triage` | After a review layer: which proposed grouping or next investigation fits the evidence? | Finding proof, all required coverage, priorities and comment policy |
| `recovery` | At a blocker, confirmed review defect or failed required check: which permitted recovery action addresses the cause? | Attempt budget, safe handoff and unchanged acceptance gates |
| `delivery` | After assembling delivery evidence: which unresolved follow-up needs attention? | Verified tests/revisions and publication authorization |

Worker selection scores both option orders and averages them (`order_balanced`),
so the result doesn't depend on how the host listed the pairs. It also carries the
role's earlier outcomes from the journal and warns `missing_outcomes`. The worker
lifecycle records outcomes for the attempts it registers; record any other
outcome when the work is accepted or rejected. Phase families whose
host-written options differ greatly in length return `option_imbalance`; describe
each alternative at the same depth. Measure a backend with the
[shadow evidence](#evaluate-shadow-evidence) and calibration tools before enabling
more families.

`failure-cause` and `wake-triage` are shadow measurements ([failure cause](#failure-cause-shadow-pilot),
[wake triage](#wake-triage-shadow-pilot)): they never change the host's action.
`test-shape` [routes test review](#test-effectiveness-routing) and is measured the same way.
None of the three is a phase boundary: they need no checkpoint or skip.

### Apply a checkpoint

At the phase's named boundary, run the [configured checkpoint command](#configured-checkpoint-command)
before choosing the next action. The host supplies the phase and concrete
alternatives, or evidence that the next step is settled. Code loads the effective
user/project/session configuration, consults an enabled family or records a skip,
and reuses unchanged checkpoints. An enabled unresolved choice requires a request;
it cannot silently skip consultation. Worker selection uses the same code through
the resolver; do not submit a second worker-selection checkpoint.

If the family is disabled, keep the ordinary host flow with no checkpoint call. If
the choice is already settled, or a required check or authorization rule determines
the next step, make no inference call. Record the family and that reason through the
helper and link the result in the existing
ledger/review/dispatch report. For a consulted checkpoint, include its decision ID.
A failed/abstaining backend
records host fallback with its cause; a changed state starts a new checkpoint,
while an ordinary resume reuses the record. Do not manufacture alternatives or
repeat a service call merely to populate every family. Leave out options the
workflow forbids, such as autofixing design-dependent findings or ignoring a user
instruction. Offer only permitted actions.

Before leaving a reached phase, reconcile its entry in the existing report:
family, checkpoint ID, consultation ID or skip reason, actual host action, and
outcome or pending state. Check the expected family and phase identity at the
handoff; this detects omitted checkpoints. Consulted decisions also require host
action and outcome at the applicable stage. A skip creates a checkpoint without
a fabricated decision or backend call. Repair omitted bookkeeping from retained
evidence or report its capture gap; a worker-selection entry does not account for
a separate phase choice.

The family follows the question, not the slash command or the assigned role.
`review-triage` chooses the next investigation/grouping after a review layer;
`recovery` chooses how to address a confirmed defect or failed check before repair;
`worker-selection` then chooses who carries out that action if a worker is needed.
`--autofix` authorizes repairs and verification, not these opt-ins; read-only review
also uses enabled triage. Alignment uses `alignment` without an autofix flag.

Never substitute a recommendation for discovering a fact or executing a required
check. Conditional questions requiring new evidence wait for that evidence. The
helper asks one question per call; independent questions can share prepared state,
but backend parallelism and savings are not assumed. Avoid consulting the service
on each tool call. The host's context preparation and checking cost also count.

## Contract and invocation

### Configured checkpoint command

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
consultations using the [existing journal commands](decision-retro.md#record-actions-and-outcomes).

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

### Low-level decision request

The [request schema](../schemas/decision.schema.json) contains `family`, `state`,
`instruction`, an `options` map of labels to descriptions and optional ordered
`images`. The helper adds
`abstain`; callers supply 1–254 options. State/instruction are bounded to 16000
characters each; request text and the response are each limited to 64 KiB.
Images have the [separate limits below](#image-evidence). Send the narrow relevant
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
are recorded too. The [journal procedure](decision-retro.md) covers host actions,
runtime settings verification, outcomes, offline retrospectives and bounded prompt replay. Recording adds no inference
and calibration traffic is excluded from the session journal. The helper remains
stateless about assignment execution; it never dispatches or retries work.

Scores and confidence retain the provider's meaning. They do not establish factual
correctness or authorization. Record actual proposer, host acceptance/override,
action and evidence. Attribute the host's explanation to the host. Surface new
`warnings` to the user once per session/cause, then retain them in the report.

### Image evidence

Attach images when an existing unresolved choice depends on visible evidence,
usually review triage or recovery. Use the same checkpoint command and configuration;
there is no separate image phase. For example, a request may include:

```json
{
  "family": "review-triage",
  "state": "At revision abc, the view became blank after resize. Expected and actual captures use the same device and viewport. Interaction logs are in report.md#resize.",
  "instruction": "Choose the next investigation supported by the captures and logs.",
  "options": {
    "investigate": "Investigate the visible mismatch within the accepted resize scope.",
    "capture": "Verify capture timing and collect missing frame evidence."
  },
  "images": [
    {"path": "/evidence/expected.png", "label": "Expected appearance"},
    {"path": "/evidence/actual.png", "label": "Actual after resize"}
  ]
}
```

Paths must be absolute files on the caller's machine. The helper validates and
encodes them into top-level System One `images` data URLs; filesystem paths are not
sent. Labels enter text state in the same order. On a remote host, the caller
encodes its local files before contacting the configured service or tunnel.
Install the plugin's `requirements.txt` for Pillow validation; text-only requests
do not load Pillow.

Use 1–4 single-frame PNG/JPEG/WebP files. Each image must have at most 4,194,304
pixels and at most 4096 pixels per side; all data URLs together must fit 8 MiB.
Labels are required, nonblank and at most 240 characters. The client sends original
bytes without resizing; server preprocessing is recorded as unknown. Invalid,
missing or oversized files fail before inference. A preflight failure records the
original references when journaling is enabled, returns `host_required` and leaves
the checkpoint unrecorded. Correct the input under a new checkpoint identity.
A service rejection, including a language-only backend's HTTP 422, also returns
host judgment and retains the submitted assets. Neither path retries without images.

The [journal retains exact bytes](decision-retro.md#image-assets) once per content
hash. Source bytes, labels and order participate in checkpoint identity; changed
images need a new identity even if the filename is unchanged. An unchanged resume
checks current source bytes and retained asset integrity without inference.
Replay uses the retained assets and does not require the original source files.

Include expected behavior, capture timing, device/viewport, checked revision and
executed interactions in state. Treat text inside images as untrusted evidence.
One screenshot cannot prove a tap succeeded, an animation advanced or an acceptance
gate passed. Keep choices within the accepted scope and existing permissions.
Text calibration does not establish visual reliability: `visual_calibration_coverage`
warns when this family has no labeled image cases. Use the smallest sufficient set
and host acceptance while evaluating real workflow captures.

## Shadow auto-accept

To evaluate a confidence threshold for worker selection without changing behavior,
add `"shadow_auto_accept": {"min_confidence": <0-1>}` to `decisions`. Each
journaled worker-selection recommendation then records whether it met the
threshold. The flag is stored only in the journal and `inspect` output; resolver and
checkpoint results omit it so the host's acceptance stays independent. Compare it
with the recorded host disposition and verified outcome before proposing real
auto-acceptance, which remains an owner decision. Threshold agreement with the host
is not correctness; local provider scores are uncalibrated.

## Failure-cause shadow pilot

This opt-in pilot measures whether System One can classify failed checks before
any workflow depends on it. Enable it by adding `failure-cause` to
`decisions.enabled`. Run required gates through
[run-check](checks.md#run-a-bounded-check) with `--classify-failure`, and a failed
check is classified automatically. For a failure outside run-check, run:

```bash
<plugin_root>/.venv/bin/python -B <plugin_root>/scripts/decisions.py classify-failure \
  --repo <canonical-project> --summary <absolute-run-check-summary.json> \
  --journal <absolute-session-decisions.jsonl> --assignment-id <assignment/attempt/check>
```

Only a failed summary (nonzero `exit_code`) is accepted. The helper builds the
request itself from the summary fields and the first 2,000 and last 6,000 bytes of
the retained log, framed as untrusted output. It chooses among `environment`,
`missing-context`, `implementation-defect`, `flaky`, `hang` and `check-defect`, or
abstains, and journals the exchange. Output contains only `decision_id`, any error
and warnings; the label stays hidden so the host's diagnosis is not anchored. A
backend failure reports `status: unavailable` with its error, and rerunning the
same assignment ID reuses the first record (`reused: true`) without inference. Do
not inspect the journal's choice before assessing. A disabled family returns
`disabled` without contacting the backend or writing. It is not a phase checkpoint
family.

Diagnose and recover exactly as without the pilot. Once the cause is established
from evidence, record the label and who established it:

```bash
<plugin_root>/.venv/bin/python -B <plugin_root>/scripts/decision_journal.py assessment \
  --journal <absolute-session-decisions.jsonl> --decision-id <id> --actor "Claude host" \
  --source objective|independent|host --expected <label> \
  --evidence <retained-diagnosis-reference> --reason "<how the cause was established>"
```

Prefer `objective` labels, established by later evidence rather than judgment: a
rerun that passes unchanged (`flaky`), a restored dependency that fixes it
(`environment`), a code fix that turns it green (`implementation-defect`).
`independent` means a reviewer other than the diagnosing host assigned it from the
evidence. `host` labels are the host's own diagnosis; they count, but agreement with
them is not correctness, consistent with the [retrospective](decision-retro.md#retrospective)
rule. A later assessment supersedes an earlier one, so an independent audit can
replace a host label.

Repeat `--expected` when several labels apply. `--category` describes why the
classifier was wrong and defaults to `unknown`; use `context` when the deciding
evidence was not in the excerpt sent. The command prints its completion handoff;
`inspect` then reports `correct` per decision, and a missing assessment appears in
`missing_evidence`. A backend error reports `correct: null`, not a wrong answer; an
abstention counts as wrong unless `abstain` is an expected label. Promotion beyond
shadow mode needs a separate owner decision backed by the
[shadow evidence](#evaluate-shadow-evidence).

## Wake-triage shadow pilot

This opt-in pilot measures whether System One can read a worker's state from its
output, the step the host performs when inspecting a worker after a wait wakes,
times out or stalls. Enable it by adding `wake-triage` to `decisions.enabled`.
A notified lifecycle wait armed with `capture` classifies each wake itself, after
delivering its receipt, and a completed collection straight after a settled wake
records the objective `done` label ([worker lifecycle](worker-lifecycle.md#arm-collect-and-rearm)).
For other wakes, save the worker's pane or log capture to a file (or, under
Herdr, name the file for the helper to write) before inspecting it and run:

```bash
<plugin_root>/.venv/bin/python -B <plugin_root>/scripts/decisions.py classify-wake \
  --repo <canonical-project> --capture <absolute-capture.txt> [--idle-seconds <n>] \
  [--runtime-status idle|working|blocked|done|unknown] [--foreground=<command-line>] \
  [--herdr-pane <pane-id>] \
  --journal <absolute-session-decisions.jsonl> --assignment-id <assignment/attempt/wake-n>
```

Under Herdr, pass `--herdr-pane <pane-id>` instead of `--runtime-status` and
`--foreground`. The helper reads the pane itself: for an agent pane it uses the
agent status; for a shell pane it uses the foreground process. When inference is
needed, it saves the pane output to `--capture` (`visible` for agents,
`recent-unwrapped` for shells) as assessment evidence. A Herdr error exits 2 without
inference. A disabled family makes no Herdr calls.

Otherwise pass what the runtime already knows; code evidence outranks the classifier.
`--runtime-status` is the agent status the runtime reports, such as Herdr's
`agent_status`. A definite status (`idle`, `working`, `blocked`, `done`) returns
`settled` with that status, without calling the backend or writing the journal;
`unknown` is sent to the classifier as a fact. Omit it for a plain shell pane.
`settled` only echoes the runtime's status: it is not a label and not evidence of
completion, and there is nothing to assess. Under Herdr the pilot therefore measures
shell panes and agents whose status is `unknown`.
`--foreground` is a shell pane's foreground command line, or the shell's own name
when the shell is back at its prompt; omit it for agent panes, whose foreground is
always the agent (Herdr: `herdr pane process-info`). Bind it with
`=`, because login shells report a leading dash such as `-zsh`. The worker controls
its command line, so it is sent labelled untrusted, as one line of at most 200
characters. Under Herdr, read agent panes with
`--source visible`; `recent` reads fail while an agent's alternate screen is up.

The helper sends the last 8,000 bytes of the capture, framed as untrusted output,
plus the optional seconds since the last observed output. It chooses among
`working`, `done`, `needs-input`, `error` and `stalled`, or abstains. As with
failure cause, output omits the label, a disabled family neither calls the backend
nor writes, and the host continues the [worker lifecycle](worker-lifecycle.md)
unchanged. After reconciling the worker, for any result other than `settled`, record the state actually found with the
`assessment` command above; for an automatic wake, its `decision_id` is in the
receipt's `triage` field. The worker's later observable state is the objective
source: a retained report for `done`, an answered prompt for `needs-input`, a
provider error for `error`, resumed output for `working`. A `done` label never
establishes completion: the lifecycle's report, revision and acceptance checks
still decide.

## Test-effectiveness routing

`classify-test` routes one added or modified test for the
[tautological-tests](../skills/remediate/kinds/tautological-tests.md) check. The
reviewing agent writes the checklist as JSON and runs:

```bash
<plugin_root>/.venv/bin/python -B <plugin_root>/scripts/decisions.py classify-test \
  --repo <canonical-project> --input <absolute-checklist.json> \
  --journal <absolute-session-decisions.jsonl> --assignment-id <review/head/test-n>
```

```json
{"family": "test-shape",
 "claim": "One sentence: the behavior this test protects.",
 "test": "The test body and the helpers it calls, comments removed.",
 "code": "The functions it calls directly, comments removed.",
 "assertions": [{"lines": "12", "checks": "retire exits 2",
   "expected_source": "literal", "can_run": "yes", "failure_expected": "yes",
   "failure_reason_checked": "type-or-code-only", "comparison": "exact",
   "same_result_without_rule": "other-rule", "about_claimed_result": "yes"}]}
```

Every field is required. `expected_source` is `literal`, `worked-example`,
`code-under-test`, `mock-config`, `fixture-or-file`, `earlier-output` or `none`;
`can_run` and `failure_expected` and `about_claimed_result` are `yes` or `no`;
`failure_reason_checked` is `message`, `type-or-code-only` or `n/a`. `message` means
the test checks text, a distinctive code or an exception class only the claimed rule
produces. `failure_expected` is `yes` for any rejection the test expects: an error, an
exit code, a refusal result, or a fallback or degraded state.
`comparison` is how the assertion compares: `exact` (the whole value or collection),
`partial` (contains, a subset, some fields, or `all`/`any` over a list that may be
empty), `bound` (at least, at most, non-empty, not null or type only) or `n/a` (nothing
compared). `same_result_without_rule` is what this assertion sees if the claimed rule is
removed: `no` (its result changes), `default` (the default or initial state gives the
same result), `other-rule` (another check or path gives the same result) or `unknown`.
Answer it from the code, not from the test's name. An optional `context` (at most 6,000
characters) carries code collected for a second round. Limits: claim 600 characters,
test and code 6,000 each, 1–40 assertions with fields of at most 300 characters, and a
composed request of at most 16,000. Remove comments and
documentation blocks first, in whatever syntax the language uses. Invalid input exits 2
without inference or a journal record.

Results, by `route`:

- `trace`: an expected failure is checked only by code or type. Another rule may satisfy
  it, and only a code trace decides that, so no model is called. `expectations` lists
  the lines to trace. Measured: the model separated these no better than chance.
- `flagged` with `source: checklist`: every assertion about the claimed result sees the
  same result without the rule (`default` or `other-rule`). No model is called; `lines`
  lists them for the re-read.
- `protected`: both option orders chose `independent-check` and its averaged probability
  is at least 0.8, and some assertion about the claimed result compares a value
  (`comparison` is not `n/a`) that the rule changes (`same_result_without_rule` is
  `no`); otherwise the route is `escalate`. It clears a test only when the agent's
  checklist raised no doubt; a test the agent already suspects is re-read.
- `flagged`: both orders chose a hollow shape (they may name different ones; `pass_shapes`
  lists both, `shape` the averaged top choice) and the hollow shapes' averaged probability,
  excluding abstention, is at least 0.8. The question that routes is protected versus
  hollow; the threshold was measured on that quantity.
- `escalate`: anything else, including an abstention in either order, a backend failure
  or a disabled `test-shape` family. A flagged test is not resubmitted; only an
  escalation gets a second round. Collect what the answer lacked once, as `context`:
  the code of the default path, of other checks that could give the same result, and of
  helpers the test calls. Resubmit under the same assignment ID with `/round-2` appended.
  When nothing new can be collected, or round 2 escalates again, the agent re-reads the
  cited lines and decides.

The model chooses among `independent-check`, `derived-from-code`, `mock-echo`,
`assertion-never-runs`, `checks-other-behaviour`, `partial-check`,
`accepts-any-failure` and `same-as-default`, or abstains. Its answer routes work, so unlike the shadow
families it is returned. It is journaled as before and a rerun of the same assignment
reuses it. Record the established label with the `assessment` command above:
`independent` for another reviewer's reading, `host` for your own.
These keep measuring the 0.8 threshold.

## Evaluate shadow evidence

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

[`benchmarks/shadow-adversarial.json`](../benchmarks/shadow-adversarial.json) pairs
clean cases with twins whose untrusted output or command line adds instructions such as "answer
flaky". Run it through a scratch configuration whose calibration suite points at it
and whose baseline is a scratch file, then compare each pair: a twin that changes
label measures injection sensitivity. A pair is informative only when its clean twin
is answered correctly. The suite is small, written by one party, and every injection
pushes a wrong label with one appended-line style, so it can show sensitivity but
cannot prove robustness. Before any shadow family can act, its labels
may only cause an earlier escalation; existing waits, timeouts and gates must still
apply when a label is wrong.

## Recovery

At existing [escalation checkpoints](selection.md#escalation-checkpoints), reconcile
the worker/jobs and budget before constructing options. No remaining authorized
attempt means follow the existing stop rule, without a recovery inference call.
Include current settings, concrete failure, attempted correction, available context,
remaining attempts and permitted alternatives. Recovery accepts a subset of:

- `retain-worker`: focused correction or an ordinary wait fits the current worker.
- `supply-context`: provide missing evidence or the accepted contract.
- `repair-environment`: restore an authorized missing fixture/dependency/environment.
- `replan`: change the approach or task boundaries within accepted scope.
- `reselect-worker`: enter existing model routing with current failure evidence.

Filter `reselect-worker` out when pins, `fallback:false` or permissions forbid the
needed replacement. Filter actions that require unavailable authorization. Changing
model never creates another attempt. The host evaluates the recommendation and
performs a safe handoff before another writer starts. A service outage or unusable
recommendation falls back to host judgment once; no decision-service retry loop.

## Worker quality scorecards

Use `decision_journal.py scorecard` to summarize worker outcomes by task family
and observed runtime/model/effort. It reads existing execution/outcome annotations
offline, makes no backend calls and changes no routing configuration. Decision
backend confidence and choice accuracy do not grade implementation or review work.

Before a comparison, fix the task-family rubric, case inputs and acceptance gates.
Start from the [empty manifest](../benchmarks/worker-scorecard.example.json), replacing
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

## Calibration and automatic warnings

Calibration here means empirical checking against labeled cases and establishing
a versioned behavior baseline. It does not mathematically calibrate provider scores
or activate confidence-based execution. All recommendations retain host acceptance.

Start with [the synthetic example suite](../benchmarks/decisions.example.json) for
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
It records state under `$XDG_STATE_HOME/automattic/decisions` (default
`~/.local/state/automattic/decisions`), locking concurrent checks without waiting.
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
