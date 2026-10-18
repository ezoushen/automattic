# Prepare a worker attempt

Use this protocol for delegated assignments, including review, and on resume or
compaction. The coordinator owns its state; workers return evidence through their
assigned channel. Keep one absolute `workers.sqlite` path per orchestration run in
the main checkout's retained reports directory, `.scratch/<slug>/reports/workers.sqlite`;
the yield hooks read only that location. Use the maintained
`scripts/worker_lifecycle.py`; do not copy it into the project. Read-only workers
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

After preparing an attempt, [wait](wait.md), [collect](collect.md) and [retire](retire.md).

1. Resolve settings from the **calling** host and save the resolver JSON. A Pi
   coordinator remains `--harness pi` when its selected destination is Codex.
   Map the resolved controls to the installed executor's actual model and effort
   controls. A model name or “think hard” in the prompt cannot set them.
2. Create a fresh worker/conversation for a new ticket or agent. Obtain its native
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
     "owned": true, "packet": "/absolute/reports/ticket-12-assignment.txt"
   }
   ```

   Pass the event file with `record --state /absolute/reports/workers.sqlite
   --input /absolute/register.json`. Assignment IDs identify a ticket and bounded
   job scope; attempt IDs identify retries. The execution snapshot must carry
   `agent` and `job`, and supplies the requested settings. `packet` is the exact
   assignment text sent to the worker; registration refuses it when it lacks
   `adapter`, `agent_file`, `job_file`, `plugin_root`, `repo` or any of the job's
   inputs as `name: value`. A repair attempt adds `repairs`, naming the collected
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
session across tickets, repositories or agents is rejected even if its pane changed.
A reused worker also cannot take a job whose `independent_of` lists a job it already
did: a worker that did a diff-review cannot then take a reproduce job.
Pass a compact handoff: accepted decisions, pinned base/head, worktree, source/test
entry points, applicable evidence, unresolved risks and next action. Cache savings
do not justify carrying an unrelated conversation into a review.
