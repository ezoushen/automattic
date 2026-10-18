# Claude Code workers

Before launching a worker, resolve [executors](../../harnesses/workers/launch.md) with the plugin's
validator Python and `agent_models.py --route --repo <canonical-repo> --harness claude
--job <job>`; include any explicit configuration profile. Record the full result,
without piping through head/tail or masking its exit status. Inspect the pool with
`--list-candidates`, establish the available model/effort pairs below, then select
with `--eligible-candidates` and `--eligible-thinking`. Render profiles only where
native controls require them.
Do this for review workers too, including each partition and later round; an
`automattic:<agent>` name is not a substitute for resolving user configuration. The operations
below apply to `native`; a selected external executor owns its launch/lifecycle
and model controls. The orchestrator retains this host adapter.

Start workers with the native `Agent` tool using the `automattic:<agent>` profile
(or its exact registered name) of the job's agent. Claude loads the agent file natively.
Supply absolute `adapter`, `agent_file`, `job_file`, `plugin_root` and `repo` alongside the
job's inputs, each as `name: value`. Do not request another automatic worktree: dispatch supplies an existing
one. Reuse an agent with `SendMessage`/native resume when supported; otherwise
start a replacement with the surviving report and worktree. Inspect the actual
tool schema; do not treat an ordinary message to an idle agent as a guaranteed
restart. Use native completion notifications or wait tools for background work.
Use an existing task's native wait/output mechanism or the selected executor's
wait operation. A background Bash task completing proves only that its command
ended: inspect the executor result before accepting worker completion. If the user
reports a finished worker while a wait remains pending, reconcile that worker and
repair the wait before launching the next batch. Do not make sleep-and-poll shell
jobs or idle timers to wait for Agent notifications. Stop owned monitors when their
work completes, and ignore late expiration notifications for finished assignments.

Bundled worker profiles allow `SendMessage`, `Monitor` and `TaskStop` for checkpoints
and owned background jobs. Before launch, confirm the current runtime exposes the
needed controls and supply the parent's actual recipient/handle in the assignment.
Workers send checkpoints to that parent; lifecycle actions cover only their assigned
jobs. A native task stop does not cancel a remote job: use the runner's own cancel
and confirm teardown. If messaging is unavailable, use the shared
[bounded return](../../harnesses/workers/focus.md#worker-return-and-checkpoints) fallback.
Regenerate a configured profile after a shipped profile changes; its content-derived
name changes with the tool list. An older registered snapshot retains its old tools,
and the Agent-model hook denies launching one whose tools differ from its shipped agent.

Apply only the model/effort settings returned by executor resolution. Bundled
profiles do not pin either field, so launching `automattic:<agent>` always passes
`model`. When resolution leaves the model unspecified, name the session's model
explicitly; the Agent-model hook requires that. Omitted effort inherits the **parent session's
effort**, which need not be the selected model's default.
See Claude's [native subagent controls](https://code.claude.com/docs/en/sub-agents).
Do not select models from ticket workload labels or re-resolve legacy preferences.
Do not change the main session's model. A model-only override uses Agent's native
`model` argument. If the resolved effort equals a verified inherited session effort,
the bundled agent can use it without a new profile; still confirm the child's metadata.
Otherwise render with `--profile`, prepare/discover the returned native profile and invoke its exact
name instead of `automattic:<agent>`. Set only the resolved fields; an effort-only
override leaves the model unspecified. The generated profile
preserves the shipped agent's tools, restrictions and principles. Inspect existing
native/user profile customizations before using it; carry forward their restrictions
or report a conflict, never weaken them to apply model settings. Verify model/effort
in native task metadata; forced environment settings or allowlists can override a
request. Do not invent an Agent `effort` argument absent from the current schema.
Profile rendering preserves the original decision ID/journal and routing snapshot;
it is not a new model-selection call or a replacement for the decision record.
Use the current session's registered agent inventory as discovery evidence; file
validation or discovery in a fresh subprocess does not prove registration here.
Prepare needed profiles before routing or fan-out. On a failed lookup, record the
capability failure once and reselect from verified combinations. For example, a
verified inherited `medium` permits `--eligible-thinking '{"opus":["medium"]}'`
when medium is allowed by config. `[null]` means an unconfigured/inherited policy,
not "use whichever allowed level the session happens to have"; it cannot replace
a configured bound. Unknown inherited effort supplies no eligible explicit level.
An unavailable effort does not establish that another profile is registered.
Only a successful new resolution supplies launch settings. If none is adequate,
report the missing registration/control; a resolver error cannot be bypassed with
a model-only launch. Preserve explicit pins and the main session's settings.
At launch, follow the shared [decision record](../../harnesses/routing/report.md):
record the host action (the worker lifecycle does this for workers it registers) and inspect the first child assistant entry's `message.model`,
`effort` and `perTurnEffort` (or equivalent native metadata). Read only those fields,
not the whole transcript. An absent field remains unverified; conflicting fields
require investigation. Record actual settings and evidence, including a mismatch.
Resolve a mismatch at a safe worker handoff before accepting its work or launching
another worker through the same failed control.
Apply the shared executor preflight and job-lifetime rules, including
native background Bash tasks still queued behind a build lock.

Every `Agent` call names its model, helpers included: Explore, general-purpose,
Plan, and other plugins' agents. Choose the cheapest model that is adequate:
- `haiku` for search, lookups and summaries;
- `sonnet` for research, review and bounded implementation;
- `opus` only for hard design, adversarial review or deep diagnosis.

Forks keep the parent's model, so fork only when the shared context is worth it.
The plugin's `PreToolUse` hook (`hooks/agent_model.py`) denies an Agent call with no
model whose definition doesn't pin one, and an automattic agent launch whose
prompt lacks `job_file:` or any input of that job, or names a job of another agent. `AUTOMATTIC_AGENT_MODEL_HOOK=off` disables
it. A second `PreToolUse` hook (`hooks/pr_body.py`) denies `gh pr create` and
`gh pr edit` unless the description comes from a `--body-file` that passes
`scripts/lint_pr_body.py`. `AUTOMATTIC_PR_HOOK=off` disables it. A `Stop` hook
(`hooks/yield_gate.py`) applies the worker lifecycle's yield gate when the session
stops; `AUTOMATTIC_YIELD_HOOK=off` disables it. A non-Anthropic model needs a configured cross-runtime route (Herdr, Pi or
Codex), not an Agent call. Offer those routes when an agent's configured pool
includes them and the assignment is long enough to justify the launch overhead.

Use at most the available child slots, with 8 as the scheduling ceiling rather
than a promise of capacity. Count review, reproduction and E2E workers too. A
reviewer completes its assigned axes directly. The orchestrator schedules separate
review assignments within available capacity.

Keep draining in the active session, using the runtime's background lifecycle.
If the user explicitly requests a persistent goal and this runtime supports it,
install it through the actual native goal operation using dispatch's scoped
completion condition. Do not assume that printing `/goal` executes it. Read the
current goal contract; do not depend on a particular evaluator, idle cadence or
turn limit. Follow shared [blocked continuation](../../harnesses/workers/focus.md#blocked-continuation)
for unresolved user decisions and resource grants. Without a goal, keep waiting
for live workers in the current run.
