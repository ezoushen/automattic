# Check execution

Use the project's required command, toolchain and resource reservation. Record the
checked revision, relevant inputs and expected outcome in the existing report.
Inspect only required configuration fields or value-presence flags; credentials
and whole environment/settings dumps do not belong in command output.

## Coordinate the actual resource

Run checks without an Automattic lock by default. Use the project's existing
coordination when commands share mutable outputs, a device or another exclusive
resource. Only an evidenced conflict calls for a resource-specific lock; a build
command or high CPU usage alone does not. Machine load belongs in the concurrency
budget. `build-lock.sh` remains an optional helper for projects that require it.
Retain the same verified resource identity across sessions and retries.

Load the selected runner's current skill/contract before its first use and after
relevant changes. A remote scheduler owns its remote capacity: do not hold a local
build mutex around submission or waiting. Record the actual job ID, execution
target and available inputs. Never assume a local script, ignored artifact, Git
metadata or host-specific path is present remotely; verify the runner's transport
contract and inputs before submitting. Use its supported script/artifact transfer.
If remembered runner limitations conflict with its current contract, verify the
supported operation through current help/status; keep accepted scope and permission
constraints intact. Build waits and watchdogs only for a capability the runner
actually lacks.

## Plan and accept checks

Name each required check's accepted criterion or project/CI requirement, phase and
owner, preconditions, expected duration and execution/teardown deadline. Give each
check a tier in the assignment:
- **focused:** the tests for the behavior being changed, run while editing;
- **affected:** the suites covering the changed code, run before the worker
  returns and again after each repair;
- **full gate:** the project's complete required gate, run once on the effort's
  integrated head before review and E2E (not per ticket merge) and once after the
  last repair, by the orchestrator or by an E2E run that already includes it.

Workers run the full gate only when the project requires it per change; name that
requirement and its source in the assignment. E2E adds only what CI and the full
gate do not cover. Acceptance reuses a worker's recorded checks at the same commit
rather than running them again. Repetitions, traces and negative controls follow
the accepted measurement contract or a concrete validity gap, rather than adding
another batch for confidence alone.

Before execution, reconcile each required check with retained evidence in the
existing report: accepted outcome, command and preconditions, original revision
and artifacts, then **reuse** with an equivalence reason or **execute** with the
specific missing/invalidated proof. A new phase, head hash or cache hit alone does
not invalidate evidence. Changed behavior, inputs, toolchain or environment can;
guarded and unguarded runs are not automatically equivalent. Honor any explicit
requirement for fresh execution. Retest affected checks, preserving other passes.
Before an expensive run or final handoff, refresh the relevant integration base,
dependency/release state and actual built artifact identity. Equal version or ABI
labels alone cannot establish matching content or symbols. Use copied or immutable
pinned build inputs; a writable dependency symlink can change a supposedly pinned run.

For a scenario, name the observable activity that distinguishes exercising the
behavior from merely keeping a process alive, and the conditions that invalidate
the run. Check driver/service readiness and fixture suitability before a long run.
Report expected versus observed activity with retained evidence: successful
interactions, loads, state changes or the project's equivalent signal. Exit zero,
completed loop counts and no crash do not prove the scenario happened. Failed
interactions, an unsuitable fixture or missing activity leave its proof incomplete;
an observed contract failure fails the check. The coordinator verifies these
signals before accepting a worker's pass, without replaying valid checks.
For script checks, invoke the verified script directly, or use a supported transfer
mechanism; `cat <script> | bash` can exit zero when the script is missing. Shell
pipelines must preserve producer failure. Require actual runner summaries/counts
or scenario readback, not a wrapper's printed success marker. Missing scripts or
setup leave the check incomplete even if the outer command exits zero.
Cached compilation does not imply tests executed. Record whether the relevant
test task ran or reused valid retained results; honor explicit fresh-test criteria
by rerunning that task through its supported controls, not rebuilding everything.

For a regression comparison, prove the candidate method reaches the failure on
the known failing/base build before comparing results. Match the trigger, fixture
and scene state, event sequence and observation windows. Detector calibration or
a generic smoke run does not validate a different scenario driver or input sequence.
If the method cannot reproduce the baseline, report the comparison inconclusive
and recover the method.
When two paths can share the same defect, compare against an independent oracle;
agreement between equally wrong outputs is not correctness evidence. Optimization
claims use comparable metrics and measured variability; an improved submetric does
not prove an unchanged or noisy end-to-end metric improved. Keep the original unmet
criterion visible alongside any human-approved narrowing or follow-up.

## Identify executed inputs

Evidence may identify a commit or an immutable working-tree snapshot. For a
snapshot, retain its base HEAD and manifest/content digest of the actual supplied
files, including applicable untracked inputs and transport exclusions, plus
toolchain, artifact and run identities. HEAD or a tracked diff hash alone cannot
identify a dirty run. Use the runner's verified snapshot metadata or a frozen
input copy; do not commit experiments merely to give checks a revision.
Remote workspaces may omit `.git`; supply verified source identity from submission.

Before final review/delivery, bind evidence to the committed candidate by proving
the relevant inputs equivalent or rerunning affected checks. Temporary instrumentation
and its removal can invalidate proof; an instrumented pass is not automatically
a pass for the delivered code. Final PR review still pins the committed diff.

## Resume interrupted checks

After reconciling owned jobs, preserve completed checks and individually evidenced
iterations when their code, inputs, environment and acceptance semantics still
match. Discard the unfinished iteration. Resume the remaining work; do not reset
the batch merely because the agent or session paused. Restart a continuous soak,
stateful measurement or batch whose accepted criterion requires uninterrupted
execution, recording that reason and preserving the partial evidence. A completed
failure follows the existing repair/retry policy; interruption does not erase it.

## Run a bounded check

Prefer an existing project runner that already preserves full output, propagates
failure and tears down owned jobs. Otherwise, on POSIX hosts:

```sh
python3 "<plugin_root>/scripts/run_check.py" \
  --timeout <seconds> --log "<retained-evidence>/attempt-01.log" -- \
  <project-check-command> <args>
```

Create the evidence directory first. Apply required environment and any project-required
resource coordination to the command. Choose the deadline from the check's
expected duration, including any authorized lock wait. Give the host tool enough
time for that deadline plus teardown; a tool that backgrounds on timeout does not
bound the check itself.
Bound setup/submission and synchronous driver operations too. Check required
script paths and syntax before execution, supply their inputs explicitly, and
use noninteractive commands. A timeout increase needs evidence of productive work
and a revised milestone; repeated invalid setup returns for host recovery.

The runner closes stdin, creates a private log exclusively, combines stdout/stderr there, and
prints a JSON summary with `exit_code`, `timed_out` and the absolute `log` path.
When the check has an authoritative execution marker, add repeatable
`--require-output <literal>` arguments before `--`; each must be nonblank single-line
text from the actual check. Missing output turns a zero exit into 1 and is listed
in `missing_output`. Existing command failures retain their exit code. These markers
are execution preconditions, not a substitute for the scenario's acceptance evidence.
`command_exit_code` preserves the child's result; `exit_source`, `timed_out` and
`interrupted_signal` distinguish command failure, output failure and wrapper deadlines.
Signals use 128 + signal. A deadline returns
124 after TERM and a one-second grace before KILL of the owned process group.
SIGINT/SIGTERM interruption also stops that group before returning. Existing logs
are never overwritten; setup or cleanup errors return 125 (invalid arguments: 2).
On normal command exit, any surviving process-group members are stopped before
returning. `cleanup_required: true` records that the command left descendants;
an otherwise zero exit becomes 125 with `exit_source: cleanup`. An original nonzero
exit is preserved. Fix the command's joins/teardown before claiming the gate passed.
Commands needing stdin must read an explicit file or redirect input inside the
command; interactive operations belong outside this helper.
When the opt-in [failure-cause pilot](decisions.md#failure-cause-shadow-pilot) is
enabled, run required gates with `--classify-failure <absolute-session-decisions.jsonl>
--assignment-id <assignment/attempt/check> --repo <canonical-project>` before `--`,
with a new ID for each retry. A failed check then journals a hidden label; the
summary gains `failure_cause` with its `status` and `decision_id`, never the label.
Use a new attempt path on retry; inspect the saved log
instead of rerunning a build merely to expose output hidden by a filter.
Keep commands and their completion waits owned through the actual result; a
background launch is not a completed check. In progress reports, distinguish
execution from build/resource queueing and user-paused time, and name the next
observable milestone. Base estimates on measured runs when available; label
uncertainty rather than attributing the entire elapsed time to model reasoning.
Use one authoritative completion wait per remote job, with native status/log reads
for progress or recovery. Reconnect or replace a failed waiter; do not nest a
polling job around its output or resubmit the check merely to resume waiting.
Prefer the runner's native deadline/cancel operations over another watchdog.
A tool wait expiring does not prove that the remote job timed
out or stopped; reconnect to the same job and inspect its authoritative state.
Code 124 alone cannot distinguish the runner's timeout from a child's timeout.
Do not resubmit until ownership and the previous job's state are reconciled.

The runner cannot tear down processes detached into another session, simulator or
remote service. Use the project's owned job IDs and teardown procedure for those.
Hard-killing the runner bypasses cleanup. A normal command exit also does not prove
background jobs stopped: reconcile owned jobs under
[resource and job lifetime](executors.md#resource-and-job-lifetime) before releasing
the reservation. Cleanup uncertainty leaves the gate incomplete.

## Prove the failure path

Before a long stress run or intentional deadlock, use the smallest negative control
to prove both the expected assertion and bounded cleanup. Include cancellation,
worker/thread joins and finally blocks in that bound. Preserve its failing evidence,
then restore the temporary mutation only after owned jobs have stopped. Verify the
restoration before running the passing case or releasing the checkout/device.
An outer timeout alone proves neither the intended assertion nor safe teardown.

## Retain evidence

Assign an absolute evidence directory outside disposable worktrees, normally beside
the main-checkout report under `reports/evidence/<assignment>/<attempt>/<head>/`.
Each execution gets its own log and result paths. Preserve failed attempts alongside
the final pass; shared names such as a global `gates.log` can overwrite sibling proof.

Copy the logs, test XML, screenshots, ABI comparisons and other files needed for the
acceptance claims out of ignored build/temp directories while they still exist.
Retain the original base/head, exact command, exit code, execution time and relevant
toolchain/input identity in the report. Preserve both baseline and candidate files
for before/after claims. Compare source/copy hashes and update report links to the
retained copies; a symlink into the retiring checkout is not a retained copy.
Keep only the files needed to support the claims, not a second build tree.
This policy also applies to cleanup outside worktrees or by file size/type. Preserve
the minimum original recordings/traces needed for audit and reanalysis, or sufficient
exports with explicit limits. Verify downstream references before deletion. A derived
CSV alone does not preserve every claim made from a video or trace; any agreed loss
of reanalysis stays explicit in the report rather than leaving broken proof links.

Acceptance requires the retained artifacts to exist and support the claimed result.
A checked box, reported pass or surviving Git commit cannot replace missing output.
Recover existing evidence first; rerun only the missing or invalidated checks when
needed. The lifecycle owner applies
[worktree retirement](../skills/housekeeping/SKILL.md#retire-a-worktree) after the
remaining gates and verifies that removal cannot break these evidence links.
