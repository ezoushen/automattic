# Codex dispatch runtime

Resolve [executors](../../harnesses/workers/launch.md) first. Default to native children, not sidebar
tasks. An explicitly selected external executor owns its launch/lifecycle and
settings; the native operations below apply only to `executor: native`. Complete
the shared dispatch preflight: active adapter, native tools, permissions and
verified repository/worktree assignments.

For runtimes exposing `collaboration`:

| Operation | Tool |
|---|---|
| Start | `spawn_agent`, self-contained prompt, `fork_turns="none"` |
| Inspect | `list_agents` |
| Send to an active agent | `send_message` |
| Assign more work to an idle child | `followup_task` |
| Interrupt the current turn | `interrupt_agent`; the child remains available |
| Wait for updates | `wait_agent`, then consume delivered messages |

Follow current schemas and returned IDs, including runtimes exposing `wait`,
`send_input`, `resume_agent` or `close_agent` instead. No child tools → dispatch
unavailable. No peer messaging → relay evidence through the parent.

## Assignment and capacity

When acceptance requires native closure or capacity release, preflight the actual
close operation before spawning. A runtime exposing only `interrupt_agent` cannot
satisfy that requirement. Use an explicitly selected, preflighted external route
with confirmed cleanup when authorized; otherwise keep the assignment queued.
Do not launch a child first and discover this limitation during collection.

Supply absolute `adapter`, `agent_file`, `job_file`, `plugin_root`, `repo`, the job's inputs, relevant
user decisions and exact failure evidence. Children read the adapter, agent file and job
file, then verify worktree and branch. Pass paths instead of copied conversations.
After session loss, inspect saved IDs; reconstruct absent agents from surviving
files/worktrees and record replacement IDs.

Use only the route's resolved settings; ticket workload labels do not select models.
Map `model` to the native
spawn model and `effort` to `reasoning_effort` (or the current schema's equivalent).
`inherit` supplies no model/effort fields; do not reapply saved Automattic preferences.
Omit absent fields; use `fork_turns="none"` with this host's explicit overrides.
Check supported model/effort combinations. Native custom-agent configuration can
supersede spawn settings: inspect it and report conflicts rather than assuming the
spawn request proves the effective model. Do not rewrite global Codex configuration.

Derive the child ceiling from the current runtime's capacity, reserving the parent
slot when its limit includes the parent. For the local Markdown board, pass that
ceiling as `--max-live` on every scheduler call. Apply it to native tracker dispatch
too; admit only free slots, counting reviewer and verifier jobs. Idle or interrupted
agents may still occupy slots. Interruption ends a turn; reconcile owned jobs under
[job lifetime](../../harnesses/workers/resources.md#resource-and-job-lifetime). Release capacity only after
their teardown and a supported close operation with confirmed status. When closing
is unavailable, `followup_task` may continue only a collected, explicitly retained
same-assignment repair/recheck with matching agent, settings and permissions.
A new ticket, another agent, or a job whose `independent_of` lists one the worker
already did needs a fresh native conversation under
[worker attempts](../../harnesses/workers/prepare.md). If the runtime cannot
provide that context or release capacity, queue work and report the limitation.
Workers complete their assigned scope directly; additional decomposition returns
to the orchestrator.

## Peer messages

Supply relevant peer IDs; refresh via `list_agents`. Children can `send_message`
directly to active siblings; use full canonical task paths across parents. Send a
contract, finding or blocker with file/commit evidence and the requested action.
Copy scope/integration decisions to the orchestrator.

Messages cannot transfer file ownership, approve changes or complete tickets.
Scheduling, assignments, board updates and integration remain the orchestrator's.
It uses `followup_task` to wake idle children; `send_message` does not. Continue
independent work or report the dependency to the orchestrator; avoid mutual waits.
Reviewers form initial findings from code/criteria before consulting authors.

## Continuation

Wait in the active turn while children work; report meaningful progress. A spawn
or empty candidate list is not completion. Persist before interruption and resume
from disk. Goals require explicit user requests and follow runtime status rules;
a blocked board alone cannot justify changing goal status. Scheduled work requires
an explicit user request; an automation does not replace waiting for live children.

The [executor guides](../executors/README.md) cover each executor type a route can select.
