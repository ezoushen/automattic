# Plan checks

Contents:
- [Coordinate the actual resource](#coordinate-the-actual-resource)
- [Plan and accept checks](#plan-and-accept-checks)
- [Identify executed inputs](#identify-executed-inputs)
- [Resume interrupted checks](#resume-interrupted-checks)

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
