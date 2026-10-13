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
Check `opencode models --verbose` or the runtime catalog for the exact model and
same-named variant; models without that variant cannot fulfill the effort request.
For effort-only settings, establish the otherwise inherited model first. Do not
translate arbitrary effort labels into provider-specific token budgets.

Confirm the loaded profile with `opencode debug agent <name>` (resolved model and
variant), then use its registered name when the native Task tool supports it.
Preserve project/native permissions; inspect any existing customized worker profile
and retain its restrictions or report a conflict before using a generated profile.
Pass absolute `plugin_root`, `adapter`, `role_file`, canonical `repo` and assigned
worktree/branch plus task inputs. Workers read the shared role; model settings do
not authorize additional work or change role boundaries. Native profile inspection
proves configuration loading, not successful provider execution.

This adapter covers model configuration and profile selection. Full Automattic
native dispatch lifecycle/worktree integration in OpenCode is not implemented or verified;
do not claim native end-to-end support or invent a substitute CLI. Configured
external execution still needs its own capability checks and acceptance evidence.
Configuration management does not install a provider, change the main agent,
or enable another harness.
