# Pi workers

## Delegation

Resolve [executors](../../runtime/workers/launch.md) first. The operations below apply to `native`;
an explicitly selected external executor owns its launch/lifecycle and settings.
Native dispatch requires Pi's `subagent` capability (provided here by pi-subagents).
Inspect its current schema and `subagent({ action: "list", capabilities: true })`
before assigning work. Use `action: "guide", topic: "tool-reference"` for unfamiliar
operations. A missing delegation capability blocks that native launch. Return the
gap to [pool recovery](../../runtime/workers/recovery.md#feedback-and-recovery); use only an already
configured suitable alternative. Do not install a provider to force a launch.

Use the registered generic `worker` with the assigned `agent_file` (builder, reviewer
or verifier) and `job_file`. Verify its actual tools
meet the assignment; project profiles can override defaults. Agent permissions
still apply even when its tool list permits writes. Do not request nonexistent
Automattic-named Pi profiles or copy the Claude profiles into Pi.

Start a child with `agent: "worker", task: <assignment>, cwd: <assigned worktree>,
context: "fresh", async: true, worktree: false`. Automattic already owns the
worktree; explicitly disable extra isolation even if Pi's configured default
enables it. Include absolute `adapter`, `agent_file`, `job_file`,
`plugin_root`, `repo`, report and input paths, branch/head, accepted scope and
decisions. The child reads these files and verifies its checkout before acting.
Fresh context keeps prior hypotheses and unrelated parent history out of reviews.

Use only the route's resolved settings by the **shared agent**, not the generic
native `worker` name. Ticket workload labels do not select models. Validate an
explicit override against the native provider/model catalog; report unsupported
combinations for pool recovery without approximating them. Map a model override to the dispatch `model` field;
map effort to its `provider/model:<effort>` suffix. The installed pi-subagents
dispatch does not accept a separate thinking parameter. For effort-only overrides,
resolve the model the worker would otherwise use from native settings/catalog
(including provider and agent defaults); do not assume it is the parent's model or
pass `inherit:<effort>`. If that model cannot be established, report the missing
capability. Validate suffix support and inspect returned effective metadata.
`inherit` passes no model/effort override; do not reapply Automattic preferences.

Use the smaller of available runtime capacity and the shared scheduling ceiling
of 8; an unlimited runtime does not remove that ceiling. Count all live workers.
Pass this ceiling as `--max-live` to local-board scheduling calls, and apply the
same admission limit to remote trackers. Workers complete their assigned scope
directly; the orchestrator handles any additional worker assignments.

## Continuation and coordination

After an async launch, persist the returned run ID and wait through Pi's native
completion notifications: yield the turn when no independent work remains, then
resume the same dispatch on notification. Report it as running, not finished.
Use a bounded `action: "status", id: <run-id>` for stale/blocked work; do not poll
or sleep to keep the parent alive. Follow runtime wait instructions for work that
lacks native notifications. Workers registered in the worker lifecycle (such as
Herdr panes) need a passing `gate --stage yield` before you yield.

Use `action: "steer"` for a running child. For completed work, inspect
`action: "children.list"` and use `action: "resume", id: <resumable-id>, message: ...`.
Resume may return a new run ID; record it and consume its completion. Queuing a
message alone does not restart a completed child. If resume is unavailable, verify
the old writer stopped, preserve its worktree/report and assign a replacement.

Use `contact_supervisor` when available for decisions or blockers. Relay concrete
peer evidence through the orchestrator unless peer messaging is actually exposed;
messaging never transfers file ownership or approves scope changes. Permission
failures are boundaries; availability failures use the shared recovery policy.
Reconcile partially started children before retrying or replacing them.

The orchestrator retains board updates, integration and authorized publication.
Automattic adds no Git blocklist. Native permissions and agent permissions
remain binding. Scheduling a recurring run or enabling a persistent goal requires
an explicit user request; ordinary async dispatch uses completion notifications.

The [executor guides](../executors/README.md) cover each executor type a route can select.
