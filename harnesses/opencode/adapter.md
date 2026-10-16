# OpenCode settings adapter

Select with `harness=opencode`; there is no Automattic OpenCode bootstrap extension.
Load shared skills through OpenCode's native skill discovery and preserve their
explicit invocation policy. Resolve dependencies from the active catalog.

Resolve [executors](../executors.md) first. A configured external executor, such as
the Herdr skill, owns invocation and collection through its own adapter. Apply
[pool recovery](../selection.md#feedback-and-recovery) for availability failures.
The native settings procedure below does not implement that external lifecycle.

For model management, use only the settings returned by executor resolution.
Do not select models from workload labels or re-resolve legacy preferences.
Omitted settings retain native defaults. For a default native worker override, render
with `--profile` and prepare the returned `.opencode/agents/` snapshot. It uses
`mode: subagent`, optional `model: provider/model` and optional `variant: <effort>`.
OpenCode applies both a profile's model and its variant only to a Task subagent; for
a top-level worker, see [top-level workers](#top-level-workers). Check the model's variants with
`opencode api GET /api/model -H x-opencode-directory:<dir>`; a model without the
same-named variant cannot fulfill the effort request. For effort-only settings,
establish the otherwise inherited model first. Do not translate arbitrary effort
labels into provider-specific token budgets.

Confirm the loaded profile with `opencode api GET /api/agent -H
x-opencode-directory:<dir>` (its `model.providerID`, `model.id` and `model.variant`);
retry while the list lacks the built-in `build` agent, which a directory's first
request can omit. Then use its registered name when the native Task tool supports it.
Preserve project/native permissions; inspect any existing customized worker profile
and retain its restrictions or report a conflict before using a generated profile.
Pass absolute `plugin_root`, `adapter`, `role_file`, canonical `repo` and assigned
worktree/branch plus task inputs. Workers read the shared role; model settings do
not authorize additional work or change role boundaries. Native profile inspection
proves configuration loading, not successful provider execution.

## Top-level workers

A top-level OpenCode 2 worker, such as one launched through Herdr, runs the full TUI,
which has no model flag and ignores a profile's variant. After the startup probe
has created its session, switch that session through the API, agent first:

```
opencode api POST /api/session/<id>/agent -H x-opencode-directory:<worktree> -d '{"agent":"build"}'
opencode api POST /api/session/<id>/model -H x-opencode-directory:<worktree> \
  -d '{"model":{"providerID":"<provider>","id":"<model>","variant":"<effort>"}}'
```

Use `build` unless the assignment names another agent; a user's default agent may
be an orchestrator that delegates. The switch takes effect on the next turn, so send
a second read-only probe, then export the session (`opencode session export <id>`)
and submit with that export: its latest assistant turn must show both settings. `opencode mini
--model <provider/model>#<variant>` applies settings at launch, but Herdr cannot
observe `mini`'s activity, so it does not suit lifecycle workers.

This adapter covers model configuration and profile selection. Full Automattic
native dispatch lifecycle/worktree integration in OpenCode is not implemented or verified;
do not claim native end-to-end support or invent a substitute CLI. Configured
external execution still needs its own capability checks and acceptance evidence.
Configuration management does not install a provider, change the main agent,
or enable another harness.
