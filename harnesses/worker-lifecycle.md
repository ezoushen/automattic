# Worker attempts and collection

Use this protocol for delegated assignments, including review, and on resume or
compaction. The coordinator owns its state; workers return evidence through their
assigned channel. Keep one absolute `workers.sqlite` path per orchestration run in
the main checkout's retained reports directory, `.scratch/<slug>/reports/workers.sqlite`;
the yield hooks read only that location. Use the maintained
`scripts/worker-lifecycle.py`; do not copy it into the project. Read-only workers
only return evidence. If the coordinator itself cannot write
coordination state, preserve the gap and use supported native waits and reports.

The helper records attempts and durable receipts. Its `submit` operation captures
session-bound native settings before invoking a productive prompt command. It
neither launches workers nor parses assignment output or approves a design.
Its wait can deliver durable receipts through a declared native parent callback;
it cannot wake a sleeping host. `collect` requires retirement or explicit retention; `retire`
uses Herdr's native lifecycle interface and confirms the bound pane is absent.
Native tools own those operations. Their callbacks are useful delivery signals;
the retained state remains the collection source after a callback or context is lost.
The wait wrapper requires a POSIX host with `ps` and process-group controls; use
the supported native wait/collection path when those controls are unavailable.

## Prepare and verify

1. Resolve settings from the **calling** host and save the resolver JSON. A Pi
   coordinator remains `--harness pi` when its selected destination is Codex.
   Map the resolved controls to the installed executor's actual model and effort
   controls. A model name or “think hard” in the prompt cannot set them.
2. Create a fresh worker/conversation for a new ticket or role. Obtain its native
   session identity as well as the transport handle. A fresh pane or a worker's
   claim of fresh context does not establish a new conversation. Register before
   submitting productive work, using the following illustrative input shape:

   ```json
   {
     "kind": "register", "attempt": "ticket-12/implementation-1",
     "assignment": "ticket-12", "repo": "/absolute/main-checkout",
     "worktree": "/absolute/ticket-worktree", "head": "pinned-input-revision",
     "execution": "/absolute/reports/resolved-execution.json", "runtime": "claude",
     "worker": "returned-transport-handle", "native_session": "native-conversation-id",
     "owned": true
   }
   ```

   Pass the event file with `record --state /absolute/reports/workers.sqlite
   --input /absolute/register.json`. Assignment IDs identify a ticket and bounded
   role scope; attempt IDs identify retries. The snapshot supplies the role and
   requested settings. A repair attempt adds `repairs`, naming the collected
   attempt whose work it fixes. When `wake-triage` is enabled, add `journal`, the
   absolute session decisions journal.

   When the snapshot applied a decision-model recommendation, the helper records
   that decision for you: its action at registration, its execution at verified
   startup and its outcome at collection. A `journal` field in a `record` or
   `collect` result reports a capture gap; without that field nothing was linked,
   so record an override yourself. An unbound forwarding executor needs an explicitly verified
   destination; a known destination must agree with the resolver.
3. Use `submit` below to capture settings automatically from native evidence for
   Claude, Codex, Pi and OpenCode. Other native formats use `record startup` with
   `attempt`, native `observed` runtime/model/effort and an
   `evidence` array of native metadata references. Verify every new attempt;
   cached executor availability does not prove a new worker's settings. Inherited
   controls remain omitted from `requested`; record actual controls when available.
   A legitimate model alias needs `model_alias_evidence` from the installed binding,
   not a similarity guess. Missing or conflicting requested controls leave work
   blocked. If metadata exists only after a first response, limit that initial turn
   to reading the assignment and reporting checkout anchors. Collect its native
   metadata before allowing edits or review verdicts.
4. For supported native formats, invoke productive work through `submit --state
   ... --attempt ... --input /absolute/submit.json`, using this input shape:

   ```json
   {
     "native": "/absolute/native-session-evidence",
     "argv": ["installed-bridge", "activity-gated-prompt-and-wait", "worker", "assignment"],
     "timeout": 300,
     "notify": {
       "argv": ["herdr", "--session", "owned-session", "agent", "prompt", "parent-name", "{receipt}"],
       "timeout": 30
     }
   }
   ```

   `native` is the registered session's Claude/Pi JSONL, Codex rollout JSONL, or
   a current OpenCode export JSON file (`opencode session export <id>` in OpenCode 2,
   `opencode export` in OpenCode 1). Obtain it from the installed native
   interface, not a worker-authored settings claim. The helper binds the session
   and worktree, reads actual model/effort, and retains a minimal snapshot with the
   source prefix length and SHA-256; it does not copy conversation contents.
   Claude may report a subdirectory within the assigned checkout; nested Git
   repositories/worktrees and paths outside that checkout remain rejected.
   Pi controls follow the latest persisted branch. A failed Pi assistant response
   blocks submission until a successful probe on that branch. Unknown controls stay absent.
   An OpenCode assistant error blocks submission even when its model fields match;
   a failed request is not a successful startup probe. Tool errors in the latest
   OpenCode probe turn also block submission; a clean new probe clears prior errors.
   For every runtime, verify
   the probe's actual acknowledgement before productive work, rather than infer
   readiness from a transport idle state or settings alone.
   Verify source provenance and exclusive ownership of native controls; refresh an
   OpenCode export before submission. A source snapshot cannot intercept subsequent
   manual changes or an in-memory Pi branch switch that has not been persisted.

   Optional `model_alias_evidence` carries explicit host-verified installed binding
   references. It affects only model identity; effort must still match. The helper
   does not authenticate the semantic truth of these host assertions.
   Submission reobserves controls, checks design holds and reserves one productive
   invocation per attempt before starting an independent durable wait. A mismatch,
   unknown requested control, wrong session/worktree or incomplete record exits 2
   without invoking the command. The submit `argv` must succeed only once the worker
   shows activity on the prompt, as Herdr's `agent prompt --wait` does; its exit 0
   then records `submitted` with the wait log as evidence. Any other exit leaves
   the attempt unsubmitted: inspect the worker and record `submitted` only with
   evidence of activity. Reconciliation never authorizes resubmitting the
   same attempt; inspect the native worker and use `watch` for continued monitoring.
   Further same-assignment work requires a collected, retained previous attempt.

   For other native formats, check `gate --state ... --attempt ... --stage work`
   before productive submission or continuation. It exits 1 while settings are
   unverified or a design hold is active. Record `submitted` with evidence that
   the actual assignment prompt was
   accepted and produced activity. Submission success alone is insufficient.
   After a stalled or uncertain submission, inspect the same worker before retrying.

Same-assignment repair or recheck may retain context only after collecting the old
result, acknowledging its receipts and recording `retain` with a reason and next
use. Register the new attempt and verify its settings again. Reusing a native
session across tickets, repositories or roles is rejected even if its pane changed.
Pass a compact handoff: accepted decisions, pinned base/head, worktree, source/test
entry points, applicable evidence, unresolved risks and next action. Cache savings
do not justify carrying an unrelated conversation into a review.

## Arm, collect and rearm

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
actual available parent; the Herdr example above reports prompt acceptance, not
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
`AUTOMATTIC_YIELD_HOOK=off` disables the hooks.
Read every completed wait's retained log and inspect the native worker/report. When
the opt-in [wake-triage pilot](decisions.md#wake-triage-shadow-pilot) is enabled,
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

Collect the actual assignment with `result`: `status` (`completed`, `blocked`,
`failed` or `cancelled`), checked `head`, an existing absolute retained `report`,
and verification `evidence`. A wait receipt is not an assignment result. Record
completion only after the normal scope and acceptance checks. The helper retains
the report digest and requires the checked revision at `gate --stage accept
--revision ...`; a missing or changed report fails that gate. Keep collected reports
immutable; snapshot a canonical report before its next authorized append. Later
attempts retain their own report snapshots. Other evidence links and live runtime
gates remain under the shared acceptance contract.

For a checked result, use `collect --state ... --attempt ... --input
/absolute/result.json` after native inspection and wait reconciliation. The input
contains `status`, checked `head`, existing immutable `report`, verification
`evidence`, and a required `disposition`:

```json
{
  "status": "completed", "head": "checked-revision",
  "report": "/absolute/retained-report.md", "evidence": ["native-result-and-checks"],
  "disposition": {
    "kind": "retire", "session": "explicit-owned-herdr-session", "pane": "returned-pane-id",
    "jobs_evidence": ["owned-jobs-and-waits-reconciled"],
    "acceptance": {"decision": "deferred", "reason": "acceptance checks not run yet"}
  }
}
```

For a completed implementer, `acceptance` goes inside `disposition` (see acceptance
below); other roles omit it.

Collection persists the report and its digest, acknowledges only that attempt's
wait/result receipts, then performs the chosen disposition. A completed collection
straight after a settled, triaged wake records that wake's `done` label. To retain context,
use `disposition` with `kind: retain`, `reason`, `next_use` and `evidence`.
Retention may preserve a pending design-hold receipt; it does not acknowledge the
escalation, permit reuse, clear the hold or authorize dependent work. Mismatch and
hold receipts need explicit acknowledgement after the coordinator consumes them.
If retirement fails, the intact result stays collected. Resume with the same
status/head/report and valid disposition; do not overwrite the report or resubmit
productive work. Receipt acknowledgement survives restarts without deleting logs
or history. Other native transports use the recorded result/disposition protocol
and their supported native closure interface; record unsupported closure explicitly.

Acknowledge other consumed receipts with `ack --event-id ...`. Acknowledging
an error does not fix its settings mismatch or resolve its design hold. Continue the
board transition and review handoff once their prerequisites pass; monitoring alone
does not dispatch the next phase.

When the orchestrator accepts a completed result and integrates it, record
`accepted` on that attempt with the integrated `commit` and evidence. It is allowed
after the worker's session closed, once per attempt. Acceptance is the
orchestrator's judgement, not the worker's `completed` claim; the
[effort spend report](../docs/effort-spend.md) counts accepted tickets from it.

Closing or retiring a completed implementer attempt that is neither accepted nor
declined settles it: the `closed` record, the `retire` input and the `collect`
retire `disposition` each carry `"acceptance": {"decision": "accepted", "commit":
"...", "evidence": ["..."]}` (nonempty evidence) once integrated, `{"decision":
"declined", "reason": "..."}` when its criteria are unmet, or `{"decision":
"deferred", "reason": "..."}` when acceptance checks are still to run, which is
usual when retiring at collection. A missing decision is refused before the pane
closes. A deferred attempt asks for `record acceptance or decline` in `status` until
`accepted` or `declined` (with `reason` and evidence) is recorded; both are allowed
after the session closed, and each excludes the other.

Each collected attempt's outcome (result, acceptance or decline, reverts) also goes
to a machine-wide ledger, `$XDG_STATE_HOME/automattic/outcomes.sqlite`, with its
candidate and role, whatever routed it. `scripts/outcomes.py summary` counts
successes, failures and pending attempts per role and candidate: an implementer
succeeds when accepted, other roles when completed; a decline, revert or failed
result fails, and a blocked result, which waits on something outside the worker,
counts neither way. `outcomes.py import <decisions.jsonl | workers.sqlite>...` adds
past decision journals and lifecycle state files once. A lifecycle attempt replaces
the journal copy of its routing decision, whichever is imported first, and a
journal's `succeeded` counts as accepted only when the host recorded it. A journal
cannot tell a blocked result from a failed one, so prefer the state file;
re-importing a state file refreshes its rows. Sources it cannot read are listed under `errors` with exit 1;
the others are still imported. A failed ledger write is reported as `ledger` and never blocks the record.

Later evidence about collected work goes back to its attempt:
`attribute --state ... --attempt <collected attempt> --kind review-defect|revert|owner-defect
[--count <n>] --evidence <reference>` for a confirmed review finding, a reverted
integration or a defect the user found. Registering a repair with `repairs`
attributes its `repair-round`. Each signal updates the routed outcome, so later
routing sees it.

For Herdr, `collect` with `disposition.kind: retire` closes the registered
conversation's pane after final use. An already collected result uses `retire
--state ... --attempt ... --input /absolute/retire.json`, with `session`, `pane`
and `jobs_evidence`. The helper checks ownership, intact collected report,
acknowledged receipts, stopped waits, native runtime/conversation identity and
idle/done state before closing. The registered `worker` must be the returned pane
ID, unique agent name, or explicit `session/pane/name` handle; use the latter for
retained cross-session records. The inherited caller pane is excluded and, when caller context is present,
`pane current --current` resolves moved caller IDs in the explicit session. A
missing caller in that session is allowed; other resolution errors fail closed.
Outside a pane, the host must verify that the target is its owned worker. Job reconciliation and
creation ownership are still host-verified assertions; the helper cannot inspect
all native worker jobs or authenticate ownership claims.

Closure is recorded only after `pane get` returns the native `pane_not_found`
error. A transport error or replaced conversation never counts as closure. If a
pane disappeared before any retirement intent, the host must inspect its native
closure and reconcile owned jobs, then use the evidence-backed `record closed`
path; absence alone does not establish ownership or safe cleanup. A
retirement intent survives interruption: retry the original target after its
monitor is gone, and confirm absence without closing another pane or duplicating
the result. Native pane IDs are not reused. Retirement closes the shared native
conversation for all its historical attempts; `status` includes `native_closed_by`
on each historical attempt to identify that final attempt. Earlier retained
attempts no longer reserve its live handle,
but the retired conversation cannot be registered again; later work starts with
a fresh native session and a compact handoff. Only the final registered attempt may
retire a conversation, after all its attempts have intact results, consumed receipts
and stopped waits. A retirement intent blocks registration of a continuation;
work gates reject the retired conversation across its history. Retain incomplete/active/blocked
workers with their concrete next use or capability limitation. For other native
transports, close through the installed lifecycle tool, confirm closure, then
record `closed` with native evidence. The helper requires a
collected intact report and acknowledged receipts. Retain only a stated next use
or a concrete runtime/ownership limitation, with `retain`, `reason`, `next_use` and
evidence. An unsupported close operation leaves capacity unavailable until the
runtime confirms release. Existing user panes stay with their owner.

## Hold a design decision early

Escalate when the worker is unsure how to proceed inside the agreement, or when
findings might break it. Possible public API/ABI or observable behavior changes,
platform exceptions, ADR conflicts and impossible/stale criteria are agreement
risks even before they are confirmed. Stop dependent edits immediately; continue
independent authorized work. Do not wait for a finished implementation or let a
reviewer infer the intended decision from an unfinished diff.

Use `escalate --state ... --attempt ... --input /absolute/escalation.json` through
the worker's supplied progress channel, with this shape:

```json
{
  "risk": "possible-breach", "reason": "Evidence may conflict with the accepted public API",
  "criteria": "/absolute/canonical-ticket.md", "brief": "/absolute/decision-brief.md",
  "phase": "alignment", "evidence": ["native finding and governing requirement"]
}
```

`criteria` must exist; the brief can still be pending so a writing delay does not
delay the hold. The hold is committed before notification, using the attempt's
armed parent channel or an explicit `notify` object in this request. Delivery
failure leaves the hold and its event pending. With no callback, consume the
foreground return through the native progress channel; read-only workers return
the structured blocker and the coordinator records it immediately. A blocked
return is not permission to continue dependent work.

Before writing any new artifact, prefer the direct form when the worker can invoke
the permitted lifecycle command. It creates no intermediate request/brief file:

```sh
python3 /absolute/plugin/scripts/worker-lifecycle.py escalate \
  --state /absolute/reports/workers.sqlite --attempt ticket-12/implementation-1 \
  --risk possible-breach --criteria /absolute/canonical-ticket.md \
  --brief /absolute/decision-brief.md --reason 'API compatibility is uncertain' \
  --evidence 'native finding and governing requirement'
```

The armed parent channel is inherited. If a native approval blocks the worker's
progress operation, the coordinator consumes its available finding and records
the hold through its own authorized progress channel. Preserve the worker's actual
permission dialog; this fallback neither approves it nor performs its pending
file/code operation. Finish the brief before a ruling, after the hold is visible.

Use `within-agreement` only when compliance is known and the uncertainty is about
the engineering choice. The selected `alignment` or `recovery` phase uses its
existing decision opt-in; `consultation_enabled` reports the registered snapshot,
not proof that consultation ran. The host runs the current configured checkpoint
with concrete alternatives. If disabled, unavailable or abstaining, investigate
or obtain suitable technical advice and retain the escalation until resolved.
Settled engineering choices need no consultation. Backend advice never grants
authority to change the agreement. A later `possible-breach` finding upgrades an
existing in-scope hold; it cannot be downgraded by another model's opinion.
Carry forward already accepted decisions with their source; implementing that
settled contract requires no new hold or user confirmation.

Complete the brief before adjudication: governing requirement, current evidence,
alternatives, compatibility/user effects, recommendation and the decision owner.
Use a separate fresh assignment for independent adjudication. Routine reversible
engineering stays with the coordinator; user-reserved product/API choices need
the user's ruling. Model strength does not transfer that authority.

Record `ruling` only after the brief exists and the actual authority has decided:
include `authority` (`host`, `human` or `user`), `decision`, the held canonical
`criteria` path and an `evidence` array containing the ruling and ticket/ledger
revision. Escalations through `escalate` additionally require an immutable existing
`ruling_source` file and `source_kind`: `user-message` for a human ruling, or
`host-investigation`/`phase-decision` for an in-scope host ruling. A possible breach
requires human authority and a user-message source; a backend response cannot
stand in for it. The coordinator verifies that the source actually contains that
human's decision. Legacy manual `record hold` defaults to possible breach and
retains its reference-based criteria contract; it does not provide the canonical
file integrity checks of `escalate`.

The helper keeps work and completion gated until resolution, then retains hashes
of the approved criteria and immutable ruling source across retries. Changed or
missing sources fail subsequent gates. Update the governing criteria before resuming;
do not rewrite them later merely to match the delivered implementation.
A host may record the ruling against a closed blocked attempt; closing a worker
does not dispose of its outstanding decision.

The helper checks record structure, not the legitimacy of an asserted approval or
the substance of a criterion. The coordinator must verify those sources. Keep
backend decision/action/execution/outcome recording under
[routing decisions](selection.md#report-routing-decisions); lifecycle receipts
do not substitute for measured worker-quality or completion-cost evidence.
