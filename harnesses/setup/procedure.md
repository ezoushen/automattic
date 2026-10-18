# Configuration procedure

Shared by the user-invoked setup-automattic and models skills. The entry point first reads
runtime bootstrap and the active host adapter. The setup-automattic skill owns guided
explanation; models handles direct requests. Both use this procedure for inspection,
edits, resets and validation without invoking one another's explicit-only skill.
Respect native invocation restrictions; a refused operation stays refused.
This file selects the flow and inspects settings. For edits read
[apply requested changes](apply.md); for resets and the final check read
[reset and validate](reset-and-validate.md).

## Select the configuration flow

For new setup and natural-language configuration requests, use model definitions and agent entries
in `executors.json`; **--route** is the explicit command spelling for that flow.
Read [configuration examples](executors.md) and only the selected
executor's schema/adapter. Preserve structured `/models` legacy commands without
--route, --config-profile, --scope session or pool options, and explicit models.json
requests, using
[legacy preferences](legacy-preferences.md).
The optional harness argument means the host for per-agent setup and the target
preference harness for legacy settings. If omitted, use the current host; never
infer it from a model name. It does not change the main session or supply tools.
Use [host selection](../workers/launch.md#host-selection) to distinguish the
caller from the worker runtime. A named-profile request uses
`profiles.<name>.<agent>.<worker-runtime>.candidate/thinking`; there is no `agents` or
`choices` wrapper. Require the target runtime for a profile edit, establishing it
from the requested candidate's binding when unambiguous. Preserve omitted fields.
Profiles never replace pools or routes. `--config-profile` explicitly selects a
profile router; host/Herdr names do not automatically select profiles.
For reusable models, read [model definitions](catalog.md#configure-an-agent).
Store descriptions under `models.<name>`; its `runtimes.<runtime>` bindings contain
the registered `id` and thinking policy. Top-level `runtimes.<runtime>.executors`
owns reusable launch routes indexed by caller context. For skill bridges, use
[caller-specific routes](catalog.md#caller-specific-skill-routes).
Establish both the caller and worker runtime before editing; update the requested
caller's route and preserve sibling routes when saving the complete runtime definition.
Use configured native routes
for same-runtime work, including Pi, and a supported bridge for cross-runtime work.
Herdr routes require a real managed environment. Provider connections stay in the runtime.
Keep agent pools shared. A routing profile may cover multiple worker runtimes.
Preserve selection policy when changing only transport.
For reusable skill usage, read [named skill executor types](executors.md#named-skill-executor-types).
An executor-definition request selects this per-agent flow. Store the complete skill
instance under `executor_types.<name>` and reference it with `{"type":"<name>"}`.
Keep destination routes and model settings separate; a definition name is not a host.
Resetting a named definition removes that definition only after its references have
been removed or reassigned as requested; preserve unrelated types and routes.

## Inspect effective settings

For **show** or an inspection without arguments, show the host, router and selected profile/source, then each
agent's pool or fixed instance, settings and source.
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
