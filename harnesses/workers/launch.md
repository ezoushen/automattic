# Launch a worker

Read before every worker launch: executor resolution, host selection and what an assignment carries.

Contents:
- [Host selection](#host-selection)
- [Resolution and models](#resolution-and-models)
- [Assignment and outcome](#assignment-and-outcome)

Core owns assignments, scope, capacity, worktrees and acceptance gates. Three
built-in executor adapters own invocation and collection: `subagent`, `skill`,
and `bash`. Their JSON Schemas live in `schemas/executors/`; instances belong in
runtime launch routes or directly in `agents`. User-defined `executor_types`
encapsulate skill usage and expand to the existing skill adapter. Definitions are
configuration data; resolution never loads user-supplied code or schemas.

## Host selection

Claude and Codex startup hooks, and Pi's bootstrap extension, identify the current
host for its adapter. Without that hint, select the harness explicitly under the
[runtime bootstrap](../README.md). OpenCode currently requires explicit selection.

Top-level `agents` defines shared role pools or intentional fixed instances.
`router` selects a routing skill, a System One decision model or a sparse named profile. See
[routers and sparse profiles](../setup/routers.md#routers-and-sparse-profiles) for the
configuration and omission semantics. A profile key such as `implementer.codex`
addresses the worker runtime, even when the host is Claude.
Shared [decisions and calibration](../setup/routers.md#decision-backend) configure a reusable backend and
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

## Resolution and models

Before every worker launch, the orchestrator runs:

```sh
"<python>" "<plugin_root>/scripts/agent_models.py" --repo "<canonical-main-checkout>" --harness <host> --role <role> --route
```

Use plugin `.venv/bin/python` when present; otherwise use a Python environment
with the required dependency if configuration is present. A `selection_required`
result must complete [selection](../routing/choose.md) first; it has
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
[session scope](../setup/session.md).
`--route-choice '<JSON agent instance>'` selects a complete one-run instance without
saving it. Relative argv paths refer to the assigned worktree, not this config file.

When the result includes `candidate_pool`, follow [selection](../routing/choose.md)
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

## Assignment and outcome

For every delegated assignment and after interruption/compaction, use
worker attempts to [register native session identity and verify settings](prepare.md),
[wait](wait.md), [collect](collect.md) and [account for retirement](retire.md).
That protocol also owns [early design holds](design-hold.md) and their ruling/criteria gate.

Inspect each assignment's configuration, preflight executor/profile discovery and
supported settings, then select from those combinations before fan-out. Reuse
successful capability evidence for the same host/session, executor, settings and
environment; invalidate it when any changes or a launch fails. Use the first real
assignment to establish runtime availability when no read-only probe exists.
A missing profile or quota failure excludes all candidates sharing that failed
capability/account. Follow [automatic recovery](../routing/recovery.md#feedback-and-recovery)
to choose another suitable candidate in the allowed pool without another approval.
Retry a failed route only after a relevant state change. Permission denials remain
boundaries; do not use fallback to bypass them.
When availability differs by effort/profile, carry those exact supported pairs with
[`--eligible-thinking`](../routing/choose.md) into selection;
rendering a profile is not discovery evidence. Record the failed capability once
and reuse it across candidates sharing that route until registration or access changes.
Verify each new attempt's runtime settings against the resolved snapshot and follow
the [decision recording procedure](../routing/report.md). A failed
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
