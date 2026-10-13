# Agent executors

Core owns assignments, scope, capacity, worktrees and acceptance gates. Three
built-in executor adapters own invocation and collection: `subagent`, `skill`,
and `bash`. Their JSON Schemas live in `schemas/executors/`; instances belong in
runtime launch routes or directly in `agents`. User-defined `executor_types`
encapsulate skill usage and expand to the existing skill adapter. Definitions are
configuration data; resolution never loads user-supplied code or schemas.

## Start with the models skill

For a guided explanation of the whole configuration and its scopes, use
[setup-automiattic](../skills/setup-automiattic/SKILL.md). For direct inspection and edits, use models below.
Both entry points follow the same [configuration procedure](configuration.md).

Use `/automattic:models` in Claude Code, `$automattic:models` in Codex, or
`/skill:models` in Pi. These are chat invocations, not shell commands. No arguments
means inspect only. For example, using Claude's spelling:

```text
/automattic:models set spec-reviewer --route executor=subagent mode=inherit
/automattic:models set spec-reviewer --route thinking=high
/automattic:models show spec-reviewer --route
/automattic:models reset spec-reviewer --route thinking
```

The second command explicitly overrides thinking; the worker's model remains at
its native default. The last removes only that thinking override. Use an actual
supported `model=<id>` when you want to select a model too. Labels are validated
against the destination before launch, not assumed portable across runtimes.

You can describe the same changes in natural language after the command. Name the
role, desired executor and any model/thinking choices. Available roles are
`implementer`, `spec-reviewer`, `reproducer`, `repair` and `e2e-runner`. The skill
uses the current host and project by default and asks only for missing choices
that cannot be established from the request or current setup.

Add `--scope user` for personal defaults or `--scope session` for a temporary
override; otherwise changes are project-local.
Explicit configuration requests authorize preparation of the plugin's isolated
validator environment if needed. Showing settings never installs dependencies or
starts a worker. After a change, the skill reports the saved path, effective
executor/model policy and any runtime checks still pending. Use the next ordinary
`dispatch` or `review` invocation to execute work; saving config does not run it.

## Configuration examples

Optional files: `~/.config/automattic/executors.json` and
`<canonical-main-checkout>/.automattic/executors.json`. Merge the requested role
into an existing file; do not replace unrelated agent entries. The
[configuration schema](../schemas/executors.schema.json) ships with the plugin.
An optional `$schema` path supports editors but does not change runtime validation.

This complete example selects the native spec reviewer and preserves its native
model/thinking settings:

```json
{
  "agents": {
    "spec-reviewer": {
      "executor": {"type": "subagent"},
      "models": {"mode": "inherit"}
    }
  }
}
```

To use another execution path, replace only that agent's `executor` object with
one of the following. Executor selection and model policy are separate choices.

**[Named sub-agent](executors/subagent.md)**, for example the official Codex plugin's delegate in Claude:

```json
{"type":"subagent","config":{"agent":"codex:codex-rescue"}}
```

**[Skill](executors/skill.md)**, with the instruction supplied after selecting the installed skill:

```json
{
  "type": "skill",
  "config": {
    "skill": "herdr",
    "instruction": "Launch a Codex worker for the supplied read-only review assignment and return its complete report."
  }
}
```

Herdr requires a managed Herdr session. A skill's prerequisites and the host's
invocation rules still apply; names are not assumed available across hosts.
For different delegation skills in Claude Code and Codex, configure
[caller-specific skill routes](selection.md#caller-specific-skill-routes).

**Bash**, for a program implementing the [assignment/result contract](executors/bash.md):

```json
{"type":"bash","config":{"argv":["bash","/absolute/path/to/worker.sh"]}}
```

Replace the script path with your actual program. This is not a generic wrapper
around any CLI: the program must consume the assignment and model policy on stdin
and return the required result on stdout. Relative argv paths use the worker's
assigned worktree. Use an absolute script path to avoid ambiguity.

To override model/thinking, replace the agent's `models` object:

```json
{"mode":"override","model":"your-runtime-model-id","thinking":"high","allow_thinking_override":false}
```

Replace the illustrative model ID with the one you explicitly choose. Either
model or thinking may be omitted; omitted fields retain destination defaults.
Use `{"mode":"inherit"}` to clear both overrides and preserve native settings.
There is no `destination` field or schema definition inside the configuration.

For multiple permitted workers per role, bounded thinking, or temporary overrides,
use [models, candidate selection and session scope](selection.md). Define reusable
models under top-level `models` with descriptions and runtime bindings containing
registered IDs and thinking policy. Top-level `runtimes` owns shared launch routes.
Roles reference one definition or a pool of definition
names. The router selects within those pools; sparse profiles contain optional
role/runtime overrides. Existing fixed instances and maps of complete
candidates remain valid. Models and thinking are chosen together before invocation.

## Named skill executor types

Define a skill and its usage instruction once under `executor_types`, then select
that name with `type`. The example skill name is illustrative; use a verified
installed skill for each caller:

```json
{
  "executor_types": {
    "pi-direct": {
      "type": "skill",
      "config": {
        "skill": "example-pi-bridge",
        "instruction": "Use the single-task delegation entrypoint."
      }
    }
  },
  "runtimes": {
    "pi": {
      "executors": {
        "claude": {"type": "pi-direct"},
        "pi": {"type": "subagent"}
      }
    }
  }
}
```

References also work in a complete agent instance, a map of candidates, or an
explicit task choice. Model policy remains on the agent or model binding. Caller
restrictions remain on runtime routes; naming a type does not supply a skill,
change the host, establish Herdr, or bypass compatibility checks.

Definitions use the existing skill executor schema and must contain a complete
`type: "skill"` / `config` instance. Names cannot replace `subagent`, `skill` or
`bash`. References contain only `type`: change the shared definition or define a
distinct name for another usage. Nested type references and parameter templates
are not supported.

Definitions merge by name across user, project and session scopes; the higher
scope replaces the whole definition. Routing profiles contain role/runtime candidate and thinking overrides.
The resolver checks referenced names after loading these layers and reports an
unknown name as a configuration error. Inspect all affected roles before saving
or removing a shared definition. Structural schema validation alone cannot prove
that references resolve across files.

Resolved output retains `configured_executor_type` and `executor_definition_source`,
while `executor_type: "skill"` and `executor_config` give the adapter its expanded
instructions. Candidate inspection returns expanded instances with the same source
metadata in `candidate_routes`. No skill is invoked during configuration inspection.

## Host selection

Claude and Codex startup hooks, and Pi's bootstrap extension, identify the current
host for its adapter. Without that hint, select the harness explicitly under the
[runtime bootstrap](README.md). OpenCode currently requires explicit selection.

Top-level `agents` defines shared role pools or intentional fixed instances.
`router` selects a routing skill, a System One decision model or a sparse named profile. See
[routers and sparse profiles](selection.md#routers-and-sparse-profiles) for the
configuration and omission semantics. A profile key such as `implementer.codex`
addresses the worker runtime, even when the host is Claude.
Shared [decisions and calibration](decisions.md) configure a reusable backend and
explicit phase opt-ins. A decision-model worker router can use that backend;
skill/profile routers retain their existing selection policy.

Routing profile selection is explicit: `--config-profile <name>`, then
`AUTOMATTIC_PROFILE`, then the configured router. Omitting the router uses the
built-in routing skill. Profile names do not establish Herdr or select the host.
Caller-specific native routes continue to win over a Herdr bridge when available;
Herdr routes still require `HERDR_ENV=1` and runtime preflight. A single routing
profile can contain preferences for several worker runtimes without duplicating
models, pools or launch routes.

The existing `--profile` flag renders a native worker settings file only after
selection completes. It is separate from routing `--config-profile`.

## Manual setup and inspection

The configuration skill can perform setup. For manual setup, replace
`<plugin_root>` with the maintained Automattic directory and prepare its isolated
Python environment once, or use an existing environment with requirements.txt:

```sh
python3 -m venv "<plugin_root>/.venv"
"<plugin_root>/.venv/bin/python" -m pip install -r "<plugin_root>/requirements.txt"
```

Reuse a working environment; do not recreate it on every configuration change.
Configured execution needs `jsonschema`; unconfigured native resolution remains
stdlib-only. Ordinary dispatch never installs dependencies automatically.

After saving the requested configuration, inspect one role without starting work:

```sh
"<plugin_root>/.venv/bin/python" "<plugin_root>/scripts/agent-models.py" --repo "<project>" --harness claude --role spec-reviewer --route
```

Replace `claude` with the current host (`claude`, `codex`, `pi`, or `opencode`).
The command validates the applicable configuration layers and prints the effective
executor, settings and their source. It does not confirm availability or launch a job.
No reload is needed for JSON changes: new assignments resolve them afresh. Already
running or resumable workers keep their launch settings.

## Resolution and models

Before every worker launch, the orchestrator runs:

```sh
"<python>" "<plugin_root>/scripts/agent-models.py" --repo "<canonical-main-checkout>" --harness <host> --role <role> --route
```

Use plugin `.venv/bin/python` when present; otherwise use a Python environment
with the required dependency if configuration is present. A `selection_required`
result must complete [selection](selection.md#choose-for-an-assignment) first; it has
no launch settings. Then read the returned `executor_guide` and active host adapter.
Resolution returns instructions/settings; it never launches a worker. Inspection
is offline and read-only. An explicit `--assignment` can call the decision backend
and update calibration monitoring state. Only explicit session save/reset
operations change the session configuration.

Agent precedence is **one-run choice → session → project → user → existing native**.
Role entries replace in full. Model, runtime, routing profile and executor-type
definitions merge by name across user → project → session, replacing each definition
in full; `router` and `decisions` each replace the lower object in full.
References expand after this merge.
Profiles override only the specified candidate/thinking fields after worker runtime
selection. The result records sources, target runtime and caller context.
A shared agent set to `null` masks lower entries and restores existing native
behavior, including saved native model preferences. Deleting it reveals the lower
layer. Select a native executor with inherit to bypass those legacy preferences.
The session layer applies only with a root session ID; see
[session scope](selection.md#session-scope).
`--route-choice '<JSON agent instance>'` selects a complete one-run instance without
saving it. Relative argv paths refer to the assigned worktree, not this config file.

When the result includes `candidate_pool`, follow [selection](selection.md#choose-for-an-assignment)
before launch. The configured router recommends model/thinking jointly; the resolver
enforces configuration bounds. Adapters translate its returned settings to native
controls; they do not choose models or supply role-based defaults. With no override, retain the
destination's native settings. Ticket `model: standard|deep` and legacy
`sonnet|opus` values describe workload only and never select or promote a model.

For a configured agent, omitted `models` means `{"mode":"inherit"}`:

- **inherit** preserves the actual destination's model and reasoning settings.
  Send no overrides, read no Automattic model preferences, and do not promote by
  workload. Bridges that discard destination settings cannot claim inheritance.
- **override** uses only the agent's `models.model`/`models.thinking`, followed by
  explicit task `--model`/`--thinking`. Omitted fields retain destination defaults.
  Task value `native` removes that override for this launch. New instances never
  merge the older models.json files. Inherit rejects override fields/task flags.

### Automatic thinking adjustments

Prefer `thinking: {"default":"medium","allowed":["medium","high"]}` for bounded
choices. This form grants adjustment within the set and cannot be combined with
`allow_thinking_override`. The default must belong to the set; a single value locks
thinking. See [selection](selection.md) for joint model/effort decisions and examples.

For string thinking settings, `models.allow_thinking_override` defaults to `false`.
In override mode, set it to `true` to let the orchestrator adjust thinking, for example raising
medium to high for a complex repair. It grants no permission to change the model,
executor or saved configuration. To retain destination defaults while allowing
adjustments, use `{"mode":"override","allow_thinking_override":true}` without
model/thinking fields. Strict inherit mode continues to send no overrides.

Resolve an agent-chosen adjustment with `--route --adaptive-thinking <label>`.
The resolver rejects it unless the selected agent opts in, and enforces any allowed
set. Reserve `--thinking`
and complete `--route-choice` overrides for explicit user choices; never use them
to bypass this permission. A user-specified thinking level takes precedence over
adaptation. With a string setting it works even when automatic adjustment is
disabled; with bounded thinking it must belong to the allowed set.

Choose a supported level based on the assignment's complexity and record the
reason, baseline (or inherited), and effective setting in its existing report.
Labels and their ordering belong to the destination runtime; do not guess a
portable ranking. The resolver returns the permission, `thinking_baseline`, any
`thinking_allowed`, and
effective `settings.effort`; adapters apply that result through their existing
controls. The permission allows either direction, but does not require a change.
It applies to new assignments; do not restart a live worker to alter thinking.
Resolution validates configuration, while executor preflight verifies that the
chosen runtime/model supports the requested level.

`thinking` is a runtime label, not a portable numerical budget. The resolver
normalizes it to internal `settings.effort` for existing adapters. The destination
must support the requested model/label pair; do not substitute a prompt instruction
or approximate label. Settings are requested, not confirmed, until native metadata
establishes them. Do not infer the destination from model names or skill prose alone:
inspect the installed invocation contract. Catalog `target_runtime` is the requested
destination; verify the bridge actually uses it. Named bridges, skills and programs
retain `harness: null` rather than claiming native execution. Complete instances can
still delegate without a catalog binding when their installed contract owns routing.

`native_dispatch: true` uses the existing host worker and permits native profile
rendering. Named sub-agents retain their selected profile and its own controls;
Bash/Skill workers use their executor's controls. Never also spawn a native worker
or re-resolve saved preferences after selecting an executor.

## Assignment and outcome

For every delegated assignment and after interruption/compaction, use
[worker attempts and collection](worker-lifecycle.md) to register native session
identity, verify settings, collect independent waits and account for retirement.
That protocol also owns early design holds and their ruling/criteria gate.

Inspect each assignment's configuration, preflight executor/profile discovery and
supported settings, then select from those combinations before fan-out. Reuse
successful capability evidence for the same host/session, executor, settings and
environment; invalidate it when any changes or a launch fails. Use the first real
assignment to establish runtime availability when no read-only probe exists.
A missing profile or quota failure excludes all candidates sharing that failed
capability/account. Follow [automatic recovery](selection.md#feedback-and-recovery)
to choose another suitable candidate in the allowed pool without another approval.
Retry a failed route only after a relevant state change. Permission denials remain
boundaries; do not use fallback to bypass them.
When availability differs by effort/profile, carry those exact supported pairs with
[`--eligible-thinking`](selection.md#choose-for-an-assignment) into selection;
rendering a profile is not discovery evidence. Record the failed capability once
and reuse it across candidates sharing that route until registration or access changes.
Verify each new attempt's runtime settings against the resolved snapshot and follow
the [decision recording procedure](selection.md#report-routing-decisions). A failed
resolution never permits launching with omitted settings.

Supply a unique assignment ID, canonical repo, assigned worktree, branch/head,
pinned review base, absolute shared role/core paths, scope/priorities, task inputs,
permissions, model policy/settings and expected evidence. Use fresh worker context.
Carry the user's current allowance priority, required deliverable and deferred
optional work in both the compact routing input and the worker assignment. Existing
acceptance gates remain part of the deliverable. A quota concern does not imply a
global model change; use the accepted priority when choosing this assignment.
Include absolute adapter and role paths in the opening message, alongside any
assignment-packet path. If only a packet path is supplied, open it directly to
resolve those paths, then read the named adapter and role before acting. Include
known source/test entry points and relevant prior evidence with its revision and
applicability limits.
Workers verify those anchors against their assigned checkout, then investigate
remaining gaps with bounded reads; expand when the evidence requires it.
The current adapters require access to the supplied paths; remote filesystem
translation is not implemented. Verify that the selected executor can fulfill the
assignment before starting. Missing skills, tools, permissions or settings support
block that launch; the coordinator may select another permitted candidate under
the recovery policy. Configuration is not proof of runtime capability.

Use the executor's existing lifecycle, record its run handle and requested/confirmed
settings, and count it in core capacity/locks. Collect a complete report attributable
to this assignment and revision; the orchestrator persists read-only reports. A
finished process, settled pane or empty output does not prove acceptance. Apply
shared review/verification gates after collection. On timeout or session loss,
reconcile the same run before retrying; never duplicate uncertain live work. Keep
pending approvals for the user and clean up only this assignment's resources.

## Assignment focus

Keep the highest-priority authorized outcome and its next acceptance condition in
the current assignment/report. Re-anchor to them on resume, handoff or changed user
direction. Choose the next action because it advances that outcome, removes its
blocker or satisfies a required gate. Finish the bounded deliverable and its checks
before optional polish. Record unrelated discoveries as a short follow-up and
continue; investigating them requires a demonstrated dependency or changed scope.

The orchestrator prioritizes unblocked work by the user's current priorities and
dependencies, and carries that focus into each worker assignment. A blocked worker
reports the exact blocker and retained state; the orchestrator chooses any already
authorized independent work. Idle capacity alone is not a reason to start more work.

Progress updates state the material result, any blocker and the next action.
Completion summaries lead with status, decisive verification and remaining action;
link the existing evidence report for details rather than repeating plans,
background or reasoning narration. Give more explanation when requested or
needed for a decision, and retain all required evidence in the report, including
complete report sections returned by read-only workers.

### Worker return and checkpoints

The assignment names the bounded deliverable, required checks and their phase/owners,
expected duration (with uncertainty), next observable milestone, and the supported
checkpoint recipient or bounded-return fallback. Verify that the worker's actual
tool permissions support this delivery path before launch. Worker return
and workflow acceptance are separate: return a complete account of passed, failed
and incomplete obligations; only verified passing evidence clears the workflow.
Initial implementation owns scoped code and implementation checks. Assign applicable
E2E explicitly to implementation or verification; reuse its valid evidence at the
later handoff rather than running it twice because the role changed. Account for
the whole ticket's criteria without making every later-phase gate the implementer's
return condition. Unassigned required checks need an owner before dispatch.

On an estimate overrun, stalled approach or newly discovered defect, send a concise
checkpoint to the supplied recipient with scope/check impact, completed proof, live
job handles and a revised next milestone. Updating a report alone does not deliver
a checkpoint. If the runtime cannot message the parent, preserve that information
in the report and return the bounded result at the next safe boundary after reconciling
owned jobs. Continue a productive authorized check; elapsed time alone is not
a failure or a reason to kill it. A failure requiring work outside the worker's
assigned responsibility, unavailable required resource, or repeated invalid attempts
without new evidence returns the bounded result to the
host after safe teardown. The host owns diagnosis, repairs, rescoping and recovery
under the existing policy; it continues independent work without another user turn.
No extra worker or decision-model consultation is required by a time checkpoint.

## Shared capacity

Before a batch and each worker launch, reconcile active assignments through native
executor status and the project's existing shared run logs or coordinator. Include
other sessions and projects using a verified common service/account, plus workers
started by dependency skills. A loop's `--max-live` is only its local admission
limit; it does not grant that many additional account slots. Apply any established
account ceiling as well as executor and exclusive-resource limits. Use the existing
claim/reservation mechanism and verify ownership before launching; do not build a
second scheduler or assume independent accounts merely because hosts differ.

Keep known reservations until actual work ends or ownership is reconciled. Unknown
account use is a capacity uncertainty for dependent fan-out, not proof that all
work must stop; continue independent authorized work and establish the available
budget with the current owner. Without a shared mechanism, report the coordination
limit and avoid competing batches against the known account. Automattic's local
board cannot enforce an account-wide ceiling across unrelated processes.

On throttling or quota errors, apply [availability recovery](selection.md#feedback-and-recovery)
to the evidenced service/account. Do not restart every interrupted worker at once
or treat an error response as proof that its existing job has stopped. Reconcile
live handles and retained reports before replacement, and retain the failure and
retry condition in the existing assignment log.

## Resource and job lifetime

Each bounded assignment has one worker owner. The worker completes it directly
and returns its evidence to the orchestrator; it does not start a second planning,
implementation or review team. The orchestrator owns any rescoping, independent
assignments and replacement handoffs. Provide only the requirements, source anchors
and evidence needed for that assignment. Review is a separate scoped assignment.
Workers surface blocking failures or repeated unproductive approaches promptly
through the executor's existing progress/report channel, with attempted actions,
evidence and live-job state. The orchestrator applies the
[escalation checkpoints](selection.md#escalation-checkpoints) when receiving that
evidence; it need not wait for a final completion report.
Workers surface an [early design decision](worker-lifecycle.md#hold-a-design-decision-early)
when unsure how to proceed within the agreement or when findings might break it,
including public contracts, platform exceptions and governing criteria. Stop only
dependent edits and supply the requirement, evidence and decision-brief path.
Use the supplied attempt/state with `worker-lifecycle.py escalate` and its armed
parent channel before dependent work. A read-only or unsupported progress channel
returns the structured blocker immediately; the coordinator records the hold.
Within-agreement uncertainty uses the phase's optional decision consultation or
host investigation. A possible agreement breach always reaches the human; neither
a worker nor a backend may authorize it. Resume only after a sourced ruling and
current canonical criteria. Carry unaffected accepted decisions forward.
A forwarding executor may transport the request to its one worker, without becoming
an additional reasoning or delegation layer.

Use [check execution](checks.md) for bounded failure controls, complete attempt logs
and evidence that survives checkout retirement.

The coordinator reserves verified exclusive resources before launching dependent
experiments: mutable build outputs, device, fixture, shared service or worktree.
Follow [resource coordination](checks.md#coordinate-the-actual-resource): a local
mutex is optional, and a remote scheduler owns its execution capacity. Launch one
experiment at a time only when they need the same exclusive resource. Other
analysis can proceed. Record ownership and waiting work in the existing
assignment/report, not a second queue.
Include other active sessions using the same device or build lane, even when they
use a different workflow. When a lock is needed, verify its common path and carry
the reservation into the project's existing instructions for standalone checks;
a worktree isolates files, not devices. Unconfirmed availability stays blocked
for dependent checks.
Reserve a complete measurement unit with its owner, expected duration and release
event (for example, baseline plus candidate plus restoration). A grant with insufficient
known availability stays a resource blocker. If revoked, checkpoint where supported,
reconcile owned jobs and resume from retained evidence after a stable grant; record
any measurements invalidated by interruption. Do not start optional later phases
just to fill a wait when their value depends on an unfinished result or the user's
allowance priority calls for deferring them.
Carry the same shared reservation and any required lock identity through retries
and recovery.
A new private lock path cannot make a busy shared lane available; an independent
lane needs verified resource separation. Same-file concurrency requires explicit
non-overlapping ownership and a semantic integration check, not just separate worktrees.

Before queuing a measurement, record its question, required suites, optional
extensions and stopping condition in the existing assignment/report. Distinguish
setup, capture and whole-experiment budgets. Report the suites actually queued and
completed so the host's estimate includes resource waits, execution and analysis.
Notify the host at meaningful milestones or material plan changes through the
existing channel; unchanged polling adds no progress. Defer optional exploration
only under the accepted stopping condition; required work retains its completion intent.

Every worker owns its spawned test jobs as well as its agent handle. Record job
handles and the worktree/resource they use, including commands still queued on a
lock or remote queue. Use the runner's current supported wait/status/log/cancel
operations. A native wait expiring leaves the job live until its status proves
otherwise; reconnect to the same ID instead of resubmitting. If a monitor tool is
unavailable, use supported bounded waits and status reads. Follow the host's
communication requirements and report meaningful milestones. Distinguish queue
time from execution and report an estimate overrun with the next observable
milestone; unchanged polls need no
repeated narration. Collect completion and verify owned descendants have stopped
before restoring experimental files, reporting finished, releasing a reservation or retiring a
worktree/worker. A launcher timeout or cancellation request is not proof of teardown.
On interruption, reconcile the same jobs; stop only owned jobs through supported
lifecycle tools or verified owned process handles and verify exit. Never use a
shared-host command-pattern kill that can affect another session. A local client
exit does not prove a remote job or device lease ended. If teardown cannot be
proved, report incomplete cleanup and retain the reservation. Never delete a
required shared lock to unblock it.
For checks resumed after interruption, follow [check recovery](checks.md#resume-interrupted-checks)
to preserve completed evidence and restart only what the measurement requires.

For work owned by another session, hand over the required dependency or result,
confirm its owner and retain this session's next integration condition. End routine
status relays after that handoff; re-engage when that condition changes or the user
requests coordination. Ownership transfer does not authorize duplicate work or
publication on the other session's behalf.

Before accepting a worker result, the coordinator reconciles its jobs and evidence.
Retain a reviewer needed for an upcoming repair check, recording that next use.
Once no assignment remains, preserve its report and retire the owned worker handle
through the executor's supported close operation. If capacity requires earlier
retirement, preserve evidence, clear the handle and resolve a replacement normally.
With no close operation, record the completed handle; release scheduler capacity
only after actual work has ended. Leave the parent session and unrelated user agents
alone. Herdr-specific operations live in [Herdr guidance](herdr.md).

## Runner contract checks

Before implementing a runner, identify who owns the launcher, descendants, mutex,
temporary configuration and restoration. Verify promised startup/Ready, early-exit,
cancellation and restoration-failure behavior through the actual shipped entrypoint,
including its lock wrapper. Stub external services when appropriate while retaining
that process boundary. An environment flag that bypasses the wrapper cannot prove
its signal or lock behavior. Confirm descendants exit before releasing exclusivity;
preserve recoverable configuration when restoration fails. Describe only the tested
signal guarantees, including any inherited file-descriptor limits.

## Blocked continuation

Distinguish live work with an owned handle from a user decision or external resource
blocker. For the latter, record the missing input, retained jobs/checkpoints, next
authorized action and the event that can resume it in the existing report. Present
one concise decision brief. An unchanged completion reminder supplies no new evidence
and must not trigger another planning, routing or review pass.
Before ending a turn with a claim that work is continuing, identify the actual live
worker/job handle and completion event; for lifecycle workers, the yield gate
([worker lifecycle](worker-lifecycle.md#arm-collect-and-rearm)) is that check. Without one, either do the next authorized
action or report the concrete blocker and resume event; an idle session is not live work.

Use the host's supported input/wait/blocked lifecycle under its actual rules. Live
jobs keep their completion wait; a user decision keeps its approval pending. For an
explicit persistent goal, establish its supported blocked/resume behavior before
installing it. Never mark unfinished work complete or pause a goal without the
required user authorization. If an external evaluator keeps waking an unchanged
blocker and exposes no usable suspension operation, report that runtime limitation
and the native action needed from the user; Automattic cannot guarantee its wake cadence.

## Reset and troubleshooting

Command examples below use Claude's spelling; use the corresponding models command
in Codex or Pi.

| Intent or problem | Action |
|---|---|
| Keep the executor, restore native model/thinking | `/automattic:models reset <role> --route` |
| Clear only one override | `/automattic:models reset <role> --route thinking` or `model` |
| Use the lower-layer configuration again | Ask the skill to remove the selected profile or shared agent entry |
| Mask a personal executor selection for this project | Set the project agent entry to null; existing native preferences then apply |
| Missing `jsonschema` | Use the prepared plugin Python environment, or run the setup steps above |
| Named agent, skill or provider unavailable | Exclude the failed capability and use a suitable allowed pool candidate; report exhaustion if none remain |
| Unsupported model, thinking or inheritance | Exclude that combination; recover within the pool without approximating settings or breaking user pins |
| Settings appear ignored | Inspect with --route; configured agents bypass legacy models.json and active workers retain their launch settings |
| Wrong profile selected | Inspect config_profile/profile_source; --config-profile takes precedence over AUTOMATTIC_PROFILE and the configured router |

## Migration

The former `executors` package registry and `routes` format now fail with a migration
diagnostic; they are never silently treated as native defaults. On explicit request,
replace each route with an `agents.<role>` instance. A former Herdr route becomes a
`skill` instance selecting the installed Herdr skill and a concrete delegation
instruction. Remove the old package registration only after translating its uses.
For override mode, copy the desired effective destination preferences into the
instance, renaming `effort` to `thinking`; do not infer a model from the parent.
Preview/validate the replacement before writing it. Existing `models.json` remains
supported for unconfigured native workers; migrating it is optional and explicit.

Installation preserves existing user configuration and writes no model/thinking
presets; to pin a pair for a role, save it through the models skill. Reload native
agent definitions when they change; existing workers retain their launch settings.
