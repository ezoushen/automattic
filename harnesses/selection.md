# Models, candidate selection and session overrides

Read this when a resolver result includes `candidate_pool`, when choosing thinking
within configured bounds, or when managing session overrides. Fixed configurations
retain their existing behavior. The orchestrator chooses; the resolver validates;
the selected executor applies settings and confirms what actually ran.

## Configure a role

Define models by task-fit description and **runtime bindings**. Each binding holds
that runtime's registered `id` and optional thinking policy. Define launch routes
once under top-level `runtimes`, shared by every model using that runtime. Roles
reference a model with `{"model":"sol"}` or list allowed models in a pool.

Here `sol` is the catalog name, `codex` is the worker runtime, and `gpt-6.1-sol` is its
registered model ID. Replace illustrative local IDs with installed catalog values:

```json
{
  "models": {
    "sol": {
      "description": "Cost-conscious complex implementation, repair and scoped review.",
      "runtimes": {
        "codex": {
          "id": "gpt-6.1-sol",
          "thinking": {"default": "medium", "allowed": ["medium", "high"]}
        }
      }
    },
    "glm": {
      "description": "Heavier local implementation and review.",
      "runtimes": {"pi": {"id": "local/glm"}}
    }
  },
  "runtimes": {
    "codex": {
      "executors": {
        "codex": {"type": "subagent"},
        "herdr": {
          "type": "skill",
          "config": {"skill": "herdr", "instruction": "Launch a Codex worker for the supplied assignment and return its complete report."}
        }
      }
    },
    "pi": {
      "executors": {
        "pi": {"type": "subagent"},
        "herdr": {
          "type": "skill",
          "config": {"skill": "herdr", "instruction": "Launch a Pi worker for the supplied assignment and return its complete report."}
        }
      }
    }
  },
  "agents": {
    "implementer": {"candidates": ["sol", "glm"]},
    "spec-reviewer": {"model": "sol"}
  }
}
```

`models.<name>.runtimes` lists supported worker runtimes: `claude`, `codex`, `pi`,
`opencode`. Herdr is a launch mechanism, not a worker runtime or model provider.
One model can have multiple bindings with distinct IDs and thinking policies.
Prefer its current-host binding when configured and reachable, then other bindings
in declaration order. This preference never infers model support from its name.

`runtimes.<target>.executors` contains routes indexed by **caller context**. Try
the actual caller's host key first, then `herdr` only with `HERDR_ENV=1`. For example,
`runtimes.pi.executors.pi` launches native Pi children; its `herdr` route lets a
Codex caller start Pi. A Pi worker started through Herdr still uses native Pi
children when configured. A caller-specific named subagent can bridge runtimes:
`runtimes.codex.executors.claude` may select an installed Codex delegate in Claude.
An unnamed subagent is valid only when caller and target are the same runtime.
Only the actual caller's key and an eligible `herdr` route participate; another
host's route is never borrowed, even when its skill file exists on disk or its
profile is selected. Caller keys already scope routes, so no separate
`supported_runtimes` field is needed.

Routing profiles override candidate/thinking by role and worker runtime; they do not create runtime capabilities.
A model with no reachable binding is an inspectable exclusion. Unknown model or
runtime references are configuration errors. The selected route still needs runtime
preflight. Native availability, tools and supported settings must be established;
configuration does not prove a provider or worker can execute.

Model, runtime, profile and named executor definitions merge by name across user, project and session layers;
each definition replaces the lower definition in full. Role entries, `router` and
`decisions` also replace in full. The resolver reports `target_runtime`, `executor_context`, model/binding
and executor sources; pool inspection includes each candidate's resolved route.
These fields describe the requested route, not observed runtime identity.

Existing complete executor instances and maps of complete candidates remain
supported, including inherit mode. Use these for destination defaults or a fixed
assignment-specific executor/model policy. For catalog migration, move the previous
`model` value to `models.<name>.runtimes.<target>.id`, thinking policy alongside it,
and launch routes to `runtimes.<target>.executors`. Confirm the destination from its
installed contract or existing known setup; never infer it from model names or prose
alone. Reconcile conflicting shared routes before saving. The old catalog layout
fails with a migration diagnostic; it is not silently treated as native defaults.

Use `thinking: {"default":"medium","allowed":["medium","high"]}` on a runtime
binding, or `models.thinking` on a complete instance. The default must belong to the
nonempty, unique allowed set. A single value locks thinking. Omit
`allow_thinking_override` with this form; strings and the legacy boolean remain
supported. Bounds apply to explicit task thinking too. Runtime-specific IDs and
thinking policy move together; one runtime never borrows another's labels.

Provider URLs, credentials, quantization and inference options stay in the owning
runtime's configuration. Register local models there and reference their exact IDs.
Omit thinking when no supported control is configured. Record serving versions with
evidence when they affect comparisons; Automattic does not configure model servers.

### Caller-specific skill routes

For cross-runtime delegation through a skill, configure each caller's own interface.
For example, this runtime definition launches Pi through different skills in Claude
Code and Codex, while Pi uses native children:

```json
{
  "runtimes": {
    "pi": {
      "executors": {
        "claude": {
          "type": "skill",
          "config": {
            "skill": "example-claude-pi-bridge",
            "instruction": "Delegate the supplied assignment to Pi and return its complete report."
          }
        },
        "codex": {
          "type": "skill",
          "config": {
            "skill": "example-codex-pi-bridge",
            "instruction": "Delegate the supplied assignment to Pi and return its complete report."
          }
        },
        "pi": {"type": "subagent"}
      }
    }
  }
}
```

The skill names are illustrative. Replace them with verified interfaces in each
caller; one portable skill may use the same name in both entries. Preserve existing
sibling routes, including `herdr`, when editing a runtime definition. Model IDs and
thinking stay in the model's Pi binding. Apply the same pattern under
`runtimes.opencode` for skills that launch OpenCode.

A caller-specific route takes precedence over the shared Herdr route even inside
Herdr. Configure one only when its [skill contract](executors/skill.md) can honor the
assignment and model policy. Neither an explicit caller key nor the shared `herdr`
key proves that the skill and its tools work in the current host.
To reuse the same skill usage across routes, define a
[named executor type](executors.md#named-skill-executor-types) and reference it with
`{"type":"<name>"}`. Different callers can select different definitions.

## Routers and sparse profiles

`agents.<role>.candidates` is the allowed pool, without a model default. The optional
`router` chooses the selection strategy. Omission uses the built-in skill:

```json
{
  "router": {
    "type": "skill",
    "skill": "automattic:model-routing"
  }
}
```

The [model-routing skill](../skills/model-routing/SKILL.md) guides the host's judgment
within its existing context. Add `instruction` only for user-specific preferences.
An installed routing skill can call Jev or another decision model and return the
same selection contract. That is a selection interface, not a worker executor;
inspection never loads the skill, calls an API or installs a dependency.
For a service exposing System One directly, use the built-in
[decision-model router](#decision-model-router).

A profile router applies sparse overrides after establishing the worker runtime:

```json
{
  "profiles": {
    "balanced": {
      "implementer": {
        "codex": {"candidate": "sol", "thinking": "medium"},
        "pi": {"candidate": "glm"}
      }
    }
  },
  "router": {"type": "profile", "profile": "balanced"}
}
```

`implementer.codex` means the worker runs in Codex, including a Claude caller that
launches it through a bridge. The host still determines which launch routes exist.
No `choices` wrapper is used. Missing candidate, thinking, role or runtime leaves
that part of selection unchanged; an empty profile is valid. Profiles do not alter
pools or executors. Candidate overrides must belong to the role pool and have a
binding for that worker runtime. Thinking must fit the final candidate's policy.
Use catalog pools for runtime profiles; a complete instance with an opaque external
executor has no inferred worker runtime. `--target-runtime` requires a catalog
reference or pool so the resolver can verify the requested binding.

Profile selection precedence is `--config-profile`, then `AUTOMATTIC_PROFILE`,
then the configured `router`. Host/Herdr names never automatically select profiles.
With several reachable worker runtimes, a profile alone does not choose the runtime.
Use `--target-runtime` or let an assignment recommendation establish it. Partial
profiles can therefore still need host judgment. An explicit user candidate pin
bypasses profile overrides; an explicit thinking pin wins over profile thinking.

## Choose for an assignment

1. Inspect with `--list-candidates` and filter by task fit, actual tools, context,
   permissions and availability. `candidate_routes` shows worker runtimes and
   caller routes; it does not prove live support. Preserve a fixed instance.
2. Resolve with the filtered `--eligible-candidates` and, when preflight restricts
   efforts, `--eligible-thinking '{"opus":["medium"]}'`. With the decision-model
   router, each configured candidate left out needs a reason in
   `--excluded-candidates '{"sol":"<task fit, tools, context, permission or availability fact>"}'`.
   Convenience or habit is not a reason, and neither is "no registered profile" when
   the inherited-effort path in the host adapter can launch the pair. A missing
   reason fails the call. The
   reasons travel with the decision request and its journal record. This optional map narrows
   configured thinking choices for the current assignment. Omitted candidates keep
   their configured choices, `[]` excludes a candidate and `[null]` permits only
   inherited thinking. It does not probe the runtime or persist capability state.
   The decision service sees only remaining pairs; final settings from profiles,
   host recommendations and explicit pins are checked too. An unavailable pinned
   or profile setting fails before launch. Apply the existing recovery policy to
   exclude that unavailable choice and select an eligible alternative; explicit
   pins and `fallback:false` still block substitution.
   When a runtime inherits a **verified concrete level**, expose that level if
   configuration permits it. `[null]` cannot relax an explicit thinking policy.
   Verify profile discovery in the running host; file creation or a fresh host's
   inventory does not establish the running host's capability.
   A pool without a choice
   returns `status: selection_required`, eligible options and `selection_router`,
   without executable settings. For a skill router, load that skill in the
   orchestrator, choose a model and thinking setting, and submit `--selection`.
   For a decision-model router, supply `--assignment <compact-text-file>` with
   the filtered pool, `--journal <absolute-journal>` and
   `--assignment-id <assignment/attempt>`, following [its protocol](#decision-model-router).
   This is normal internal continuation, not a human approval checkpoint.
3. For `router.type: profile`, establish the target runtime from the proposed
   candidate or `--target-runtime`. Apply the specified fields only. A single
   eligible candidate can resolve directly; no list position becomes a default.
4. Preflight the final settings, save the resolved JSON with the assignment, and
   [report the decision](#report-routing-decisions) before passing it once to the
   selected executor. A `selection_required` result cannot launch a worker or
   render a native profile. Reuse the snapshot on ordinary resume; new failure
   evidence invokes the [escalation checkpoints](#escalation-checkpoints).
   A resolver error supplies no launch settings. Preserve the last valid snapshot;
   write a replacement to a temporary file and promote it only after successful
   resolution and JSON validation. Recover through supported choices rather than
   dropping rejected fields or bypassing resolution.

Use the plugin's Python environment, not a guessed system interpreter. Examples
extend `<plugin_root>/.venv/bin/python -B <plugin_root>/scripts/agent-models.py --repo <repo> --harness <host> --role <role> --route`:

```text
--list-candidates
--selection '{"candidate":"sol","thinking":"high","reason":"Cross-module contracts need deeper diagnosis."}'
--config-profile balanced --target-runtime codex
--selection '{"candidate":"sol","reason":"Only this worker supports the required tools."}' --eligible-candidates '["sol"]'
--assignment /absolute/path/assignment-summary.txt --journal /absolute/path/decisions.jsonl --assignment-id task/1 --eligible-candidates '["luna","sol"]'
--assignment /absolute/path/assignment-summary.txt --journal /absolute/path/decisions.jsonl --assignment-id task/1 --eligible-candidates '["opus"]' --eligible-thinking '{"opus":["medium"]}'
--candidate sol --thinking medium
```

`--eligible-candidates` is an inline JSON array of configured IDs, not a comma
list, filename or model ID. Save a resolver response only after checking its exit
status and parsing the JSON; do not pipe away errors or overwrite a valid snapshot
with failed output. Read launch controls from `settings.model` / `settings.effort`,
the route from `executor` / `executor_config`, and decision provenance from
`decision_model`; absent fields stay absent. `selection_required` supplies no launch.

`--target-runtime` restricts catalog bindings; it never changes the caller adapter
or creates a route. `--candidate` and `--thinking` are user pins, not a way for the
orchestrator to bypass configured bounds. Reserve `--route-choice` for an explicit
user-requested complete instance outside saved policy. Within a pool, `--model`
may only confirm the selected candidate's registered ID.

The [selection contract](../schemas/selection.schema.json) is `candidate`, optional
`thinking`, and a nonempty `reason`. Omitted thinking preserves the candidate's
baseline unless the profile supplies it. `candidate: null` means no suitable worker
and stops resolution. An invalid recommendation returns `selection_required` with
`selection_error` and the built-in router; it never executes an implicit fallback.

An external routing skill owns its API, credentials and uncertainty handling.
Pass a compact assignment, eligible model/effort options, user guidance and relevant
verified outcomes. A Jev adapter can choose one enumerated model/effort pair and
record factual decision provenance; it must not invent a generated explanation.
Unavailability, abstention or invalid router output falls back once to the built-in
host skill. Distinguish router uncertainty from no suitable worker; neither consumes
worker repair attempts. The router cannot launch workers, widen pools, waive gates
or recursively select itself. No provider-specific dependency is required by core.

## Decision-model router

`decision-model` describes the router's job; `systemone` names the supported API
protocol. Jev/OpenJev is the model serving it. The router is separate from worker
models, runtimes and executors. Shared backend configuration supports the
[decision loop and calibration](decisions.md):

```json
{
  "router": {"type": "decision-model"},
  "decisions": {
    "backend": {
      "protocol": "systemone",
      "endpoint": "http://127.0.0.1:1241/v1/systemone",
      "model": "local/OpenJev-27B-Splash"
    },
    "enabled": ["worker-selection", "recovery"]
  }
}
```

Use the service's registered model ID and full POST endpoint. This example is a
local Splash lane; it is not a bundled server or a required port. Optional
`timeout_seconds` defaults to 20 (greater than zero, at most 60); `instruction`
in `decisions.backend` adds user-specific decision preferences. An older inline
router remains supported for worker selection when shared `decisions` is absent.
This client supports unauthenticated
HTTP(S) System One endpoints. Other protocols or authentication can stay behind
an installed routing skill. No chat-completions compatibility is assumed.

After worker preflight, pass a compact text file with `--assignment` and the
filtered `--eligible-candidates`. Include the problem, acceptance checks,
uncertainty, relevant verified outcomes and user priorities. Reuse an existing
assignment summary when suitable; do not send transcripts, full repositories or
secrets. The helper adds the role, caller and eligible model descriptions, IDs,
resolved runtimes and model/effort options, excluding executor instructions and
commands. The summary must fit 16000 characters and the request 64 KiB.
For live decisions, also pass `--journal <absolute-session-decisions.jsonl>` and
`--assignment-id <assignment/attempt>`. The resolver records a configured
`worker-selection` checkpoint and reuses it on unchanged resumes. The returned `decision_model.decision_id`
links the exact request to the host action and verified outcome through the
[decision journal](decision-retro.md). Reuse that ID on resume; do not repeat a
service call to recover missing history.

One [System One Choice](https://docs.typesafe.ai/primitives/choice) scores complete
model/effort pairs together, with an abstain option. Only declared bounded
thinking values are enumerated. A string baseline stays fixed for this router;
an absent thinking setting stays inherited. Define an `allowed` set to let the
decision model choose among efforts. Explicit task thinking filters the options
and wins. The service cannot invent candidates, effort labels or routes. At most
254 worker options fit one request; narrow larger pools during preflight.

`--list-candidates`, fixed instances, explicit candidate pins and supplied
`--selection` decisions do not call the service. An assignment summary alone
does not change a skill/profile router. Without `--assignment`, ordinary
resolution remains offline; a sole candidate can use its baseline. Supplying
the summary allows effort selection even for a sole candidate. When filtering
leaves exactly one model/effort option, the resolver sends no request; with a journal
it records a `settled` worker-selection checkpoint and reports `sole-option` as the
selection source, so there is no decision ID to annotate. Persist and
reuse the returned decision until an [escalation checkpoint](#escalation-checkpoints)
warrants a replacement; resume alone does not invalidate it.

Successful output includes `decision_model` provenance: returned model, option
mapping, choice and probabilities, plus confidence when provided. The selection
reason records the service's choice; it is not a generated rationale. Confidence
measures score concentration, not calibrated correctness; no universal confidence
threshold is imposed. Preflight and final verification still apply.
`decision_warnings` carries calibration status and detected benchmark regressions;
surface new warnings using the [decision skill](../skills/decision/SKILL.md).
Configured periodic calibration replays are separate diagnostic requests and never
replace the saved baseline or consume worker attempts.

Add `"consult": "after-failure"` to route by rule first; it requires a
`fallback_profile`, which then settles routine routes with no service call and
reports `selection_source: rule-profile`. The service is consulted only when the
profile has no route for the role's worker runtime, or when the host retries after
a failed or rejected attempt with `--after-failure "<failure evidence>"`, which the
request states. The default, `"always"`, consults on every `--assignment`.

With an optional `"fallback_profile": "<profile>"` on the decision-model router, an
outage, timeout, abstention or invalid answer first applies that
[sparse profile](#routers-and-sparse-profiles) deterministically. The result reports
`selection_source: fallback-profile` with the `selection_error`, the decision record
and a `decision_fallback` entry in `decision_warnings`; report that warning so a
backend outage stays visible. Configuration, journal-identity or eligibility errors
never use the fallback. If the profile leaves the choice open, or
none is configured, the following host path applies.

An outage, timeout, abstention or invalid answer returns `selection_required`,
`selection_error` and the built-in host skill as `selection_router`. Continue
there with the same exclusions and pins, then submit `--selection`; this bypasses
another service call. Do not loop on the endpoint, consume worker repair attempts
or ask the user to route an ordinary assignment. If no permitted worker fits,
stop under the existing no-suitable-worker rule. Each choice request is sent once;
the HTTP client rejects redirects and limits response size to 64 KiB. Saving or
inspecting configuration never probes the endpoint.

## Migrate earlier configurations

Back up the file. Move `agents.<role>.default` to the appropriate
`profiles.<name>.<role>.<worker-runtime>.candidate`, keeping pools in `agents`.
Use `router.type: skill` or `decision-model` for adaptive selection, or select that profile explicitly.
Keep per-model thinking baselines and bounds. Earlier `profiles.<name>.agents`
entries require an explicit migration: shared models/routes/pools belong at the
top level, and only candidate/thinking preferences belong in routing profiles.
Do not translate a host profile name into a worker runtime without checking its
actual bindings. Legacy layouts fail with migration guidance rather than silently
changing dispatch behavior.

## Session scope

`--session <root-session-id>` or `AUTOMATTIC_SESSION` enables the session layer.
Use the real root session ID when available; otherwise create one stable ID when
the first session override is requested and retain it in existing effort state.
Pass that ID and canonical repository to descendants and resume messages. Workers
use their actual host adapter; carrying the session ID does not pin the parent's host.
Only the coordinator changes the shared override record.

State lives under `${XDG_STATE_HOME:-~/.local/state}/automattic/sessions/`, keyed by
canonical repository and root session ID. The record includes both identities and
`config`, using the same schema (including `executor_types`) as executors.json. Inspection does
not create it. New sessions use durable defaults; resume with the same ID restores
the session layer. Store policy only; keep transcripts and credentials in their
owning systems.

Use the models skill with `--scope session` to edit it. Its helper operations are:

```text
--session <id> --save-session <configuration.json>
--session <id> --reset-session
```

These are explicit writes: save validates and atomically replaces the session's
complete configuration, so preserve unrelated entries from its existing `config`.
Reset removes only this session record and exposes project/user defaults. Both
require the normal repo/host/role/route arguments. For a role-only reset, remove
its override from the saved configuration instead of resetting the whole session.
The resolver returns the absolute state path in `session.path`. Root identity is
checked when reading, replacing or deleting an existing record.

## Feedback and recovery

Classify the observed response before recovering. HTTP 429 alone does not establish
exhausted credit: inspect the service's error details and retry metadata. For a
temporary rate limit, retain the supported retry time, reduce admission against
the [shared account budget](executors.md#shared-capacity), and use a bounded retry
only when availability can change. If an eligible alternative is available, the
ordinary fallback can continue immediately. Proven exhausted quota or an outage
excludes candidates on the affected service/account; a new model name on that
same account is not recovery. Record the classification, affected account and
retry/fallback condition, without exposing credentials. Never create parallel
retry bursts or unbounded backoff that strands the assignment.

Availability failures trigger automatic recovery within the allowed pool: exhausted
credits/quota, unavailable model/provider/harness, missing executor capability or
an unsupported requested model/effort pair. Preserve the failure evidence, exclude
the failed candidate, and re-resolve with the remaining `--eligible-candidates`.
Exclude other candidates sharing a proven failed service/account or capability;
switching from one Codex model to another does not cure an exhausted Codex account.
Do not ask for another approval when a suitable configured alternative exists.
If resolution requests selection, follow its `selection_router` through the
[assignment selection flow](#choose-for-an-assignment). A profile preference excluded by availability does not get retried;
its candidate-specific thinking is also released for the replacement. State the
switch and continue the same assignment, scope and gates. Never lower
an effort bound or approximate a setting to force a launch.

Retain exclusions in existing session/assignment state; do not keep retrying a known
failure until availability actually changes. A fixed instance has no alternatives.
If all permitted candidates are exhausted, report the blocker and ask only for the
missing decision. Explicit user pins and `fallback:false` remain constraints.
Authentication unavailability can use an already authorized alternative account;
never acquire credentials, change permissions or bypass a sandbox/tool denial.

A failed worker's partial report cannot close its obligation. Reconcile and stop
any owned live writer/jobs before replacement; an ambiguous timeout requires
inspection, not immediate resubmission. Give the replacement the same assignment,
retained evidence and revision. Its complete verified report may close the original
obligation. Availability recovery does not authorize parent self-approval or waive
independent review.

Keep the existing review/repair attempt limits across model switches. A switch
does not reset the counter or bypass a permission or resource ownership boundary. Record its
reason and previous configuration; revisit a failed combination only after relevant
new evidence or a state change. Reuse unaffected review coverage and existing gates
instead of adding a separate model-quality review. Compare accepted assignments
and total recovery cost; a few outcomes do not establish a universal model ranking.

## Escalation checkpoints

The orchestrator owns when to reconsider a saved choice. Check at existing workflow
boundaries, without a new polling loop or separate model-quality review:

| Checkpoint | Evidence and decision |
| --- | --- |
| Unaccepted public API/ABI or behavior change, new platform exception, ADR conflict or stale acceptance criterion | Apply the [early design hold](worker-lifecycle.md#hold-a-design-decision-early). Complete the decision brief before adjudication; record the ruling and update canonical criteria before dependent work resumes. |
| Worker reports a blocker or repeated unproductive attempts | Inspect the failing approach and current run state. Decide whether to supply context, repair the environment, rescope or reconsider the worker. |
| A review layer completes or a required verification check fails | Use consolidated confirmed findings and failed checks before assigning the next repair. One material contract miss can justify escalation; comment counts alone cannot. |
| Before retrying or resuming after a failure | Compare new evidence with the saved decision and remaining attempt budget. Reuse the choice when nothing material changed; resolve an evidenced mismatch before another attempt. |

First distinguish missing context, changed requirements, environment/access failures
and a localized defect from evidence that the current model/effort is inadequate.
A focused correction can stay with the same worker. Repeated failure of the same
understood contract, an invalid approach or newly discovered complexity can justify
more permitted thinking, another allowed model, or a narrower assignment. Choose
the action that addresses the cause; no compulsory model ladder or extra failed
round is required. Elapsed time, a normal build-lock wait or an incomplete live
report alone does not establish inadequacy.

At a recovery boundary, run the [configured checkpoint command](decisions.md#configured-checkpoint-command)
with family `recovery`, [permitted actions](decisions.md#recovery) and current
evidence, or a justified skip when the next step is required or settled. Check its
phase record before acting and its outcome at the handoff. A retain/context/environment
recommendation keeps model routing out of that checkpoint. Disabled or unavailable
recovery stays with host judgment.

For reselection, give the configured router the previous model/effort, concrete
failure evidence, attempted correction, unchanged acceptance criteria and remaining
budget in the compact assignment, and pass the failure with `--after-failure
"<evidence>"`; under `consult: "after-failure"` only that flag consults the service.
The orchestrator judges the proposal. If it
repeats a combination already shown unsuitable without new evidence, use host
selection once with that exclusion; do not cycle through router calls. Report a
deliberate retain decision when a focused retry is justified. Explicit pins,
thinking bounds, `fallback:false`, permissions and existing attempt limits still
apply; escalation cannot manufacture another attempt or unlock a pinned field.

Apply changes at a safe handoff after reconciling and stopping the previous owned
writer/jobs. Keep the same assignment identity, revision-bound evidence and attempt
history; append the replacement decision rather than overwriting the old one.
A decision snapshot changes for the next attempt, not midway through a live worker.

## Report routing decisions

Before the initial dispatch and each evidence-driven retain, escalation or fallback,
the orchestrator gives a concise user-visible update and records the same decision
in the existing assignment/review report. Batch independent announcements when useful.
Ordinary resumes refer to the saved decision; repeat neither the announcement nor
the router call when no decision changed.

Include assignment/attempt, previous → requested model and thinking, target runtime
and executor, **who proposed**, **who accepted or overrode**, **how it was selected**,
and the concrete evidence/reason. Use actual identities where available; label an
unavailable host model ID as unknown. Distinguish requested from runtime-confirmed
settings, and preserve the policy source/session and resolved JSON.

For a recorded backend decision, the [worker lifecycle](worker-lifecycle.md)
records it when the registered execution applied the recommendation: the
`action` at registration, the `execution` at verified startup and the `outcome`
at collection. Later review defects, repair rounds, reverts and owner-found
defects reach that outcome through `attribute`. Read its `journal` output for a
capture gap. Without the lifecycle, or for an override, append the host `action`
before executing it, `execution` at worker startup and the task `outcome` at the
acceptance checkpoint with the [direct annotation commands](decision-retro.md#record-actions-and-outcomes);
each prints its launch, startup or completion [handoff check](decision-retro.md#check-a-handoff),
so no separate check call is needed. An override explained only in prose is missing the actual
host action. Reconcile that capture gap from retained evidence, preserving unknowns.
Complete this bounded result's record before reusing its worker, even if the overall
workflow is ongoing. Pass the checked revision to completion; a prior segment's
outcome cannot accept a resumed head. Retain verified alias evidence and report
errors/host recovery separately from eventual delivery success under the journal contract.
A launch failure or settings mismatch belongs to host/execution evidence, not a
label that the decision model chose badly. Report a new calibration warning with
its next step; preserve it without rerunning calibration automatically.

Attribution follows the actual path: an explicit user pin, named profile, named
routing skill, host judgment or the decision service's returned model/protocol.
For OpenJev, preserve its option/probability record and separately state the
orchestrator's reason for invoking or accepting it. The score is not a generated
rationale or proof of correctness. If the service fails and the host chooses,
attribute the final choice to the host and name the failed service separately.

Example: "Ticket 12, repair attempt 2: Luna/xhigh → Sol/high via native Codex.
Proposed by OpenJev through System One; accepted by the Codex orchestrator. Trigger:
R1-SPEC-02 still reproduces after the focused correction. Settings requested;
runtime confirmation pending. Existing retry budget unchanged."

Keep acceptance results, classified failures, elapsed time and available usage
evidence with those decisions; mark missing metrics unavailable. Histories belong
in the existing run reports/journals, not maintained skills or configuration.
For Claude, [recorded usage accounting](../docs/claude-usage.md) includes the native
family and separately associated worktree sessions. Keep requested settings beside
runtime-confirmed settings; tokens do not establish subscription credits. Evaluate
a cheaper routing choice on a bounded assignment through accepted review/repair
closure before claiming a completion-cost improvement from synthetic scores.
