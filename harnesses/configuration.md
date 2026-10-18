# Configuration procedure

Shared by the user-invoked setup-automattic and models skills. The entry point first reads
[runtime bootstrap](README.md) and the active host adapter. The setup-automattic skill owns guided
explanation; models handles direct requests. Both use this procedure for inspection,
edits, resets and validation without invoking one another's explicit-only skill.
Respect native invocation restrictions; a refused operation stays refused.

## Select the configuration flow

For new setup and natural-language configuration requests, use model definitions and role entries
in `executors.json`; **--route** is the explicit command spelling for that flow.
Read [configuration examples](executors.md) and only the selected
executor's schema/adapter. Preserve structured `/models` legacy commands without
--route, --config-profile, --scope session or pool options, and explicit models.json
requests, using
[legacy preferences](models.md).
The optional harness argument means the host for per-agent setup and the target
preference harness for legacy settings. If omitted, use the current host; never
infer it from a model name. It does not change the main session or supply tools.
Use [host selection](executors.md#host-selection) to distinguish the
caller from the worker runtime. A named-profile request uses
`profiles.<name>.<role>.<worker-runtime>.candidate/thinking`; there is no `agents` or
`choices` wrapper. Require the target runtime for a profile edit, establishing it
from the requested candidate's binding when unambiguous. Preserve omitted fields.
Profiles never replace pools or routes. `--config-profile` explicitly selects a
profile router; host/Herdr names do not automatically select profiles.
For reusable models, read [model definitions](selection.md#configure-a-role).
Store descriptions under `models.<name>`; its `runtimes.<runtime>` bindings contain
the registered `id` and thinking policy. Top-level `runtimes.<runtime>.executors`
owns reusable launch routes indexed by caller context. For skill bridges, use
[caller-specific routes](selection.md#caller-specific-skill-routes).
Establish both the caller and worker runtime before editing; update the requested
caller's route and preserve sibling routes when saving the complete runtime definition.
Use configured native routes
for same-runtime work, including Pi, and a supported bridge for cross-runtime work.
Herdr routes require a real managed environment. Provider connections stay in the runtime.
Keep role pools shared. A routing profile may cover multiple worker runtimes.
Preserve selection policy when changing only transport.
For reusable skill usage, read [named skill executor types](executors.md#named-skill-executor-types).
An executor-definition request selects this per-agent flow. Store the complete skill
instance under `executor_types.<name>` and reference it with `{"type":"<name>"}`.
Keep destination routes and model settings separate; a definition name is not a host.
Resetting a named definition removes that definition only after its references have
been removed or reassigned as requested; preserve unrelated types and routes.

## Inspect effective settings

For **show** or an inspection without arguments, show the host, router and selected profile/source, then each
role's pool or fixed instance, settings and source.
Include shared decision backend, enabled families and offline calibration status;
`decisions.py status` reports saved warnings without inference or state writes.
Include a pool's candidates and descriptions, thinking defaults/allowed
sets or legacy adjustment permission, and active session ID/path/source when present.
Show runtime bindings, model IDs, definition sources, launch routes and excluded candidates with reasons;
include named executor types and their effective skill/config and definition source.
`--list-candidates` permits inspection even when no candidate has a matching route.
Report `selection_required` as an undecided assignment, not a selected model.
Show sparse profile overrides separately from the resolved pool.
Include native preferences only where
no agent instance is configured. A named bridge's destination may be unresolved;
show that honestly. Read-only inspection never creates files, installs dependencies,
loads executor skills or starts workers. Requested settings are not runtime proof.

## Apply requested changes

For **set --route** or a natural-language setup request, identify the shared role
or named model/runtime/executor definition being changed. For a model with multiple bindings,
establish the intended runtime from the request before changing its ID or thinking;
accept `runtime=<name>` to identify that binding and `id=<model-id>` for its registered
ID (`model=<id>` remains an input alias). Runtime launch routes are shared defaults;
routing profiles change only candidate/thinking fields, not runtime definitions.
Use project scope unless user or session scope is requested. With only model/thinking
choices and no existing instance, use `executor: {"type":"subagent"}`; omit empty config.
`executor=<type>` selects a built-in instance or a defined skill type. Built-ins
obtain their config from the request (agent name, skill/instruction, or argv);
named type references contain only `type`. Accept natural-language setup requests
and structured JSON. Derive the skill
instruction from the user's stated delegation goal or supported mode; keep it brief.
Tool syntax, settings mapping and lifecycle belong to the selected skill; shared
scope, review and recovery rules come from Automattic. Ask only if the target or goal is missing.
Do not invent command paths, agent names or models. Optional model policy defaults
to inherit. Explicit model/thinking choices select override;
changing only the executor must not silently carry model overrides to a different
runtime. Show any such conflict for the user to resolve. Merely choosing a skill
is not permission to install it or run a validation job.

For catalog entries, pools, bounded thinking or **--scope session**, read
[selection and session scope](selection.md). These options select
the per-agent flow. Accept a pool as structured JSON or construct it from the
user's named candidates as catalog references or complete executor/model policies.
Catalog membership alone does not grant every role access. For role grading,
research the exact model/runtime, choose candidates by the role's obligations, and
put conditional task limits in model descriptions. Keep dated comparisons in research
journals; use [assignment selection](selection.md#choose-for-an-assignment)
to filter each task. Pools have no model default; `--candidate <id>` identifies
the candidate to edit. Migrate old defaults explicitly using that guide.
For a per-candidate change, establish the target from the request before editing;
preserve the other candidates. Never silently collapse a pool to one
instance. Shared model/runtime/executor definition edits affect every referencing role. For
role-only model settings, copy the model definition under a distinct descriptive ID
and update that role's reference. For a role-only launch override, use a complete
executor instance; runtime names are fixed. Preserve other uses. Unknown references fail after layers are merged;
validate all affected references, including when removing a definition. Pools default
to automatic availability fallback; set `fallback:false` only when requested.
`thinking=<JSON>` accepts `{ "default": "medium", "allowed": ["medium", "high"] }`;
use this bounded form for new requests that permit automatic adjustment. Preserve
existing string/boolean settings unless their policy is being changed. A bounded
form replaces the legacy boolean; a single allowed value locks thinking.

Session edits use the stable root session ID from the assignment/environment or
existing effort record. If unavailable, generate and retain one before the first
override. Use the resolver's `--session` for all affected inspections and descendants.
Copy the effective role entry before a partial override, preserve unrelated session
entries, validate, and save the complete configuration through `--save-session`.
The saved file contains its repository/session identity plus `config`; the helper
input is only that `config` object. The coordinator owns writes. Report the ID and
absolute path so resume can recover them. Never write session preferences to user
or project defaults, or treat another host's parent profile as the child's host.
Construct edits from layers up to the requested scope: user only for a user edit,
user plus project for a project edit, and those layers plus the matching session
for a session edit. Copy the affected effective object at that scope before a
partial override; never copy a higher layer's values into a lower file. Inspect
durable settings without `--session` and with `AUTOMATTIC_SESSION` unset; for user
edits, read the user file directly rather than treating project resolution as user
defaults. Retain an active session's identity and show whether it still masks the
saved change. Explicit profile selection changes the view, not the saved router.

For a **router** request, store `{"type":"skill","skill":"<name>"}` with
optional user-specific `instruction`, `{"type":"profile","profile":"<name>"}`,
or `{"type":"decision-model"}` with the backend configured under
[`decisions`](decisions.md#configure). For a decisions request, preserve
the effective object, then edit backend, enabled families or calibration as requested.
Enable only explicitly requested families. Record the registered endpoint/model and
known revision; absolute suite/baseline paths belong to the chosen config scope.
Calibration commands belong to the [decision skill](../skills/decision/SKILL.md);
configuration edits and inspection remain offline. An old inline decision router
still applies to worker selection when shared decisions are absent.
Removing `decisions` reveals the lower object or legacy inline worker router; it
does not necessarily disable the service. To disable backend decisions at this
scope, preserve the required backend and set `enabled: []`. Disable only a requested
family by removing it from the effective enabled list. Resetting `router` reveals
the lower router, or the built-in skill when none remains. To select host judgment
over a lower router, save an explicit built-in skill router. Keep unrelated decision
families and calibration settings when changing only worker selection.
When no layer defines a router, use `automattic:model-routing` in the host's current context.
External routing skills return selections; they do not execute assignments. Keep
other API protocols and credentials in that skill's integration. Decision-model
settings belong in `decisions.backend`, not the worker catalog. Preserve the existing router
when editing pools or routes. This command does not invoke a router or probe its
service; a requested integration test is separate from configuration inspection.

For a **profile** request, edit the named role/runtime entry only. Omitted fields
leave selection unchanged. A candidate must be in the role pool and bound to that
worker runtime. A thinking-only entry is checked against the final selected model.
Resetting a profile field removes that override; resetting a role/runtime entry
removes only that entry. Preserve sibling roles/runtimes. Defining a profile does
not activate it unless requested. An explicit activation updates `router`.

Role entries, `router`, `decisions` and named profile definitions replace lower layers
in full. Before a partial edit at a new scope, copy the effective object and
preserve unrelated entries. Report the edited profile and whether it is active.
Complete instances store `models.model` and `models.thinking` together; catalog
bindings store `id` and `thinking` under `models.<name>.runtimes.<runtime>`. Neither reads
models.json. `effort=<label>` remains an input alias for thinking, not a second
stored field. Check requested controls against the actual installed destination's
contract/catalog when available. Reject known incompatible combinations. If the
runtime cannot be inspected, save explicitly requested, schema-valid settings and
label their runtime compatibility unverified; launch still requires preflight.
Never replace the user's model choice with a guessed supported value.
For string thinking, store `allow_thinking_override` alongside that binding's
thinking, or in a complete instance's `models` override policy. Enable it only when requested; a model/thinking change alone does not grant
adaptation. Preserve it when changing one setting. Follow the
[automatic adjustment contract](executors.md#automatic-thinking-adjustments)
for one-run agent decisions. Resetting all model settings to inherit also clears
this permission; resetting only thinking preserves it.

An explicit configuration change includes preparing the isolated validator
environment when necessary: reuse the plugin .venv or an existing compatible
Python, and install requirements.txt there if missing. Follow the executor guide;
do not change global Python or account-wide harness configuration. Read-only show
reports a missing dependency instead of installing it. Configuration changes do
not authorize live worker probes, third-party plugin installation or new credentials.

## Reset only the requested settings

For **reset --scope session** without fields or a candidate, remove the named role
entry to expose durable defaults, preserving unrelated entries. An explicit
whole-session reset uses `--reset-session`. Field/candidate resets use the instance
rules below. Within a pool, reset only the requested candidate's settings, preserving
its executor and siblings. Deleting a candidate requires an explicit request;
update any referencing profile entries in the same change.

For **reset --route** outside session scope or a reset of one candidate's model
settings, preserve the executor and set `models: {"mode":"inherit"}` when no fields
are selected.
Catalog runtime bindings require an ID. Removing only thinking is valid; inheritance
uses a complete executor instance instead of a model reference. Explain that
conversion and preserve sibling candidates and unrelated shared definitions.
Resetting a specific model/thinking field removes that override; it does not reveal legacy preferences. Removing the instance reveals a
lower scope; setting it to null masks lower instances and restores existing native
behavior. Report which reset was applied and its effective result. Do not silently
remove executor selection when the user asks only to reset models.

## Validate and report

Validate candidate executor JSON with `validate_execution_config` from
`scripts/agent_models.py` before replacing the original, then resolve every affected
role with --route --list-candidates, including every affected profile. Resolve
profile overrides with the relevant --target-runtime and candidate to check thinking.
A pending selection is valid and never authorizes a worker probe. Preserve unrelated
entries. Finish with the saved absolute path,
role, executor/selection, model policy, model/thinking (or inherited), and any
pending runtime checks. Show the focused diff without claiming a worker was tested.
New assignments read changes automatically; identify a reload only when native
profile discovery or plugin installation actually requires one.
The former per-model executor catalog needs the migration described in selection.md;
confirm destination runtimes from known configuration/contracts, preserve IDs and
thinking, and reconcile shared route conflicts. Back up the existing file before
migration. Legacy package/routes files use the executor guide's migration. Never
reinterpret malformed/old configuration as an absent configuration.
Named executor types encapsulate skill usage under the bundled schema; they do not
load custom schemas, code or nested definitions. Resolve references after merging
user/project/session layers; reject unknown names without invoking a skill.

## Legacy preferences and native profiles

For structured `/models` legacy commands without **--route**, **--config-profile**, session
scope or pool options, show/set/reset models.json.
Accept thinking as an input alias but store legacy `effort`; `defaults` applies only
here. Preserve its per-field precedence and null masks. Validate with `read_config`
and resolve the affected harness/role. No harness argument defaults to the current
host. Do not edit legacy settings expecting them to affect a configured instance.
A one-run request stays in the assignment, not a saved file.

For default native workers, prepare generated profiles only when requested controls
require them, preserving existing restrictions. Named sub-agents, skills and Bash
executors use their own supported controls; never replace a named delegate with an
Automattic profile. Changes apply to new workers; do not restart live workers or
change the main model. Clean up only generated profiles proven unused by active or
resumable assignments. Report required reloads and unverified capabilities.
