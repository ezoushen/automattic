# Wait for a worker

One independent wait per attempt, then handle each wake. [Prepare the attempt](prepare.md) first.

## Arm a wait

Use **one independent wait per attempt**. Run `watch --state ... --attempt ...
--input /absolute/wait.json` through the host's supported background operation
with `notify`, and yield once no independent work remains. Keep foreground waits of
at most 60 seconds for a worker about to finish; do not poll workers in the foreground. The input
contains a literal `argv` array for the installed bridge's supported wait/prompt
operation and a `timeout` in seconds. The helper runs in the assigned worktree and
retains combined output under `workers.sqlite.logs/`.

Arm `notify` in that same request for background waits. Its literal `argv` must
contain one whole `{receipt}` argument; the helper replaces it with a JSON message
containing the stable event ID, assignment/attempt, input head, state path and
receipt. No shell expansion occurs. Use the installed native channel to the
actual available parent; the Herdr example in
[submit](prepare.md) reports prompt acceptance, not
an acknowledged or completed parent turn. The channel must return once the parent
accepts the message: waiting for the parent's turn outlasts the callback timeout
and records a failed delivery. Before the first wait on a channel, and again after
its latest delivery failed, `watch` sends a no-op `channel-check` message through
it, which the parent sees as a prompt, and refuses to arm when that fails. Verify the parent identity and that
its permissions permit receipt inspection before submission. Keep callback timeouts
at most 45 seconds. Without `notify`, only a foreground wait of at most 60 seconds
is accepted: the host must await its native return. Longer waits without a channel
fail before invoking the worker command.

The terminal receipt is committed before delivery. Delivery acceptance records
`delivery.state: sent`; failures/timeouts remain `failed`, and interruption before
the receipt is updated leaves `sending` with its owner's process identity. These
states never acknowledge a receipt or accept a worker's result. Callback output
is retained separately and cannot replace the worker log. On resume, inspect
`status.pending`, the same native parent and the callback log; consume an already
received event once using its ID. Recover an undelivered event with `deliver
--event-id ... --input /absolute/retry.json`:

```json
{"retry": true, "evidence": ["same parent resumed; prior delivery and ownership reconciled"]}
```

The saved channel is reused. A `notify` object may explicitly replace an unavailable
parent's channel after verifying its new identity. A live delivery owner prevents
retry; an uncertain prior send requires inspection, never a guessed failure.
Already sent/acknowledged events are idempotent. Recovery redelivers the same
event ID and never reruns productive work. Parent downtime remains pending;
resume inspection is required when no native channel is available.

Use the bridge's activity-gated prompt-and-wait operation when available; record
the accepted prompt evidence from its native result. Standalone waits may immediately
return stale idle. Never join independent waits in one shell command, suppress exit
statuses, or append a success message. The helper preserves the command's exit
status, uses 124 for its own deadline and 130 for an interrupted monitor. It stops
its own local wait process group; this does not stop a remote worker or its jobs.

## Wake and yield

At every host continuation and after a wait wakes, run `status`.
Use `--attempt` for a focused read; otherwise reconcile the run's full set of handles.
The output includes unacknowledged receipts, attempts requiring attention and
unresolved design holds, including holds whose blocked worker has been closed.
Before yielding, run `gate --state ... --stage yield` (no `--attempt`). It exits 1
and names each live worker without an armed wait that can wake you, each lost wait
and each undelivered receipt; fix those first. On Claude Code and Codex (Stop hooks)
and Pi (extension), the plugin also runs it when you stop, over runs active in the last
day, and sends you back once. It holds only the Herdr pane that registered a worker
or, outside Herdr, sessions that are not inside a worker's own worktree.
Every session is also held for each Herdr launch it logged ([launch log](prepare.md)) into
`.worktrees/` or a cwd Herdr did not report and, unless its launch marked it a worker
(`AUTOMATTIC_WORKER`, as [prepare](prepare.md) says) and inside Herdr, for each other live
agent of its workspace whose cwd is in `.worktrees/` (none asked when the checkout has no
`.worktrees/`), when no attempt names that pane or agent (alone or in a
`<session>/<pane>/<name>` handle; for a launch, an attempt registered from its pane, or
after it when it was made outside Herdr) and none of its
dismissals accounts for it, however old the run. A launch belongs to the pane that ran it
and, when both sides know one, the same host session, so a pane ID that a restarted Herdr
reuses inherits nothing. A check that cannot run (Herdr or git fails or times out) and a
launch log line that is unreadable or has malformed fields are named gaps, never a pass.
The session dispatch bound to coordinate an effort (`next_tickets.py --coordinate`) is also
held for each collected attempt, neither retained nor retired, whose recorded tab Herdr still lists
(with no binding, the Herdr pane that registered it is), and for an effort whose review
report records `autofix: true` (before it does, the binding's `--autofix`) and no `blocker`, with
every ticket done and `--delivery` failing, until it is finished: its branch deleted, its reviewed head
in main and a passing `e2e_status` recorded at a head in main.
A closed workspace or stopped Herdr session means the tab is gone.
`AUTOMATTIC_YIELD_HOOK=off` disables the hooks.
Read every completed wait's retained log and inspect the native worker/report. When
the opt-in [wake-triage pilot](../decisions/shadow-pilots.md#wake-triage-shadow-pilot) is enabled,
add `capture`, a literal argv that prints the worker's current output, to each
notified wait of an attempt registered with a `journal`. After delivering the
receipt, the helper runs it in the worktree (15-second limit) and journals a hidden
label; `status.pending[].payload.triage` holds its `decision_id` for the assessment.
Handle the wake as follows:

- Settled idle with this assignment's complete report may be completion. Idle
  without accepted prompt activity or a current report remains unverified.
- Error, timeout, provider failure or lost monitor requires inspection of the same
  worker and its owned jobs. Record `reconciled` with that evidence after the old
  wait has stopped. If work remains live, arm a new independent wait for it.
- A restart consumes the previous wait; rearm after reconciliation. An active wait
  cannot be replaced or declared reconciled. A killed monitor retains its local
  wait PID; reconcile its teardown before starting a replacement. Missing process
  evidence requires inspection, not a guessed stopped state.
