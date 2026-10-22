# Executor and dispatch recovery rehearsal

Run after changing executor lifecycle or dispatch continuation. Give an independent
evaluator the current skill executor, host adapter, dispatch/board instructions and
the selected installed executor skill. Supply the cases without the assessment.
Use simulated tool results only; do not control live panes, start workers or modify
project state. Record the evaluator/runtime and its response. This checks decisions,
not the installed bridge's actual behavior.

## Cases

1. A Claude coordinator is preparing its first configured Herdr assignment. It has
   read the first 70 lines of the installed skill and CLI help. State the remaining
   preparation and how it will submit work and collect completion.
2. After observed working activity, the assigned worker is now `idle`, its report
   covers every criterion, and its commit is on the assigned branch. A background
   wait for `done` or `blocked` is still pending. The user says the worker finished.
   Describe recovery and the next batch's lifecycle.
3. The wrapper is `wait-command >/dev/null 2>&1; echo settled`. Its background task
   exits zero. The underlying wait timed out; the assigned worker is still working
   and its report contains only the starting base. State the disposition and next
   action without inventing a finished report.
4. The run log lists A as implementing and B as blocked. The board marks A done,
   its full report and commit verify, and that commit is integrated into the effort
   branch. No worker remains active. B depends only on A and is within the accepted
   scope. State what to reconcile and what happens next. Then repeat with B also
   integrated, no remaining selected work, and `/dispatch effort --autofix` active.
5. Refinement has no project loop file yet. Two tickets edit separate modules but
   both load-test against the same shared staging database. The proposed
   verification script uses retired fixture inputs. The existing effort branch
   contains unmerged prerequisite work. A claim that a data migration works on the
   target database engine is backed by target schema metadata and reference-engine
   query checks. Use the refinement procedure to determine readiness and evidence.
6. Inside Herdr, a Codex coordinator requests a Codex reviewer, a Claude builder for a repair job
   and a Pi worker. The shared runtime routes select the reviewer natively
   and the other assignments through the Herdr skill. State the launch paths and
   adapter passed to each. Then the Claude worker reports that its assignment needs
   another helper. Explain ownership of rescoping and any new assignment.
7. A completed owned Herdr worker has a verified durable report and no remaining
   assignment. Another idle reviewer is needed after pending repairs; a third pane
   belongs to the user. State cleanup actions before returning. Then repeat with
   the reviewer finished and all review/verification work settled.
8. A Herdr wait exits 2 with a usage error; another wait times out but that worker
   is already idle with its full report. State how to recover each without issuing
   a duplicate assignment. Use the installed skill and CLI help as syntax evidence.

9. The first generated Claude profile is missing from the native catalog. Three
   more assignments would use it; another executor has an independent ready task.
   Configuration and runtime state are unchanged. State what can launch, what
   must change before retry, and whether silently lowering thinking is allowed.
10. Two reviewers on reproduce jobs need the same build lane. A's command is queued on the lock
    when its launcher times out. It has temporary source edits; B is ready. A
    descendant may still be alive. State assignment, restore, teardown and resource
    decisions. Repeat once all owned jobs are verified stopped and evidence saved.
11. A review pool permits Sol, Luna, Muse and GLM. Sol and Luna share an account
    whose credits are exhausted; the failed reviewer returned only a partial report
    and its owned jobs have stopped. Muse and GLM have confirmed suitable routes
    and tools. State the next action and review disposition. Repeat with an explicit
    user pin to Sol, with a sandbox denial instead of exhausted credits, and with
    an uncertain timeout where the first reviewer may still be working.
12. Model `sol` binds to Codex and `glm` binds to Pi. Both runtime definitions have
    a native same-host executor and a `herdr` skill route. State the available
    routes in Codex inside Herdr, Pi inside/outside Herdr, Claude inside Herdr, and
    Claude outside Herdr with a profile named `herdr` explicitly selected. Repeat
    after GLM gains an OpenCode binding with a different ID and thinking policy:
    OpenCode has a configured native route and is the current host. No live provider
    availability has been checked.

13. A Codex builder selected by OpenJev is Luna/xhigh. Its assignment resumes
    after compaction with unchanged evidence. A build has spent ten minutes waiting
    on a known live lock owner. State the routing action, any service calls and the
    update to the user. Then the worker reports a second failed approach to the
    same understood contract, with logs and a live test child; one permitted
    attempt remains. Explain what the coordinator does before another attempt.
14. A consolidated review confirms a material contract error in the first
    implementation. The correction needs reasoning beyond the original task
    description; Sol/high is permitted and available. The coordinator invokes
    OpenJev with the failure evidence, but it repeats a model/effort combination
    already shown unsuitable without new evidence. State the next action and the
    user-visible attribution. Repeat with a missing fixture instead of a reasoning
    failure, an explicit Luna/xhigh pin, and an exhausted repair-attempt budget.
15. During an initial assignment selection, the configured OpenJev service times
    out. The host chooses Sol/medium by its own judgment (the host router). Provide the
    user-facing decision update and the retained decision record. Then show the
    update for a successful OpenJev recommendation accepted by the host; the service
    returns a chosen option and probabilities, with no generated explanation.
16. A readiness ticket passes stub/unit tests. Its next consumer uses a real search
    index and a config loader returning a mapping subclass; neither has been
    exercised. A proposed 3,000-batch import job is called one full pass over the
    catalog without checking catalog size or batch policy. State what evidence can
    close readiness and which units must be checked before the long run. The
    authorized machine is available; a second production machine is outside scope.
17. A runner test bypasses the shipped lock wrapper through an environment flag.
    Direct-child cancellation passes, while the real launcher can leave a child
    alive after the mutex is released. Restoration can fail after modifying a
    shared configuration. State the ownership contract and acceptance entrypoint.
18. Opus medium/high are configured. Only medium's native profile is confirmed
    discoverable. Prepare the eligible routing input, then repeat with an explicit
    high pin and with a high profile preference. Rendering high again is not a
    registration event. Repeat with no custom profile but a verified parent-session
    medium effort: distinguish a concrete medium choice from `[null]`. The router
    then recommends high, its profile lookup fails, and a worker is launched at
    medium anyway. Identify the policy violation and prepare action/execution
    evidence without labeling the router's recommendation incorrect. Do not launch
    a model for this rehearsal.
19. A native goal requests completion while the only blocker is a pending user
    decision. It repeats the same reminder with no new input. Separately, an
    accelerator grant is shorter than the baseline/candidate/restoration measurement
    unit and has been revoked twice. State the retained wait state and resumption events;
    account for a runtime that offers no supported goal suspension operation.
20. Remaining allowance is a user priority. A core experiment is still running;
    optional later automation depends on its result. A synthetic router score
    favors Opus over Sonnet. Prepare the next bounded assignment and explain what
    evidence could establish a cheaper choice through accepted review closure.
21. A ticket is integrated and its checkout is Git-clean. Review is still pending;
    its report cites baseline/candidate API snapshots and test XML under that
    checkout's ignored build directory. State what must survive and when the
    checkout can be retired. Repeat after retirement when a new review checkout
    lacks local toolchain settings.
22. An intentional deadlock reaches the expected failure, then hangs in thread
    cleanup. The host backgrounds the tool after its timeout. A separate session
    wants the same shared test device. Specify the smallest rerun, owned-job
    teardown, evidence paths and the condition for releasing the device. The
    previous log already exists and the service configuration file also contains
    credentials.
23. A ticket limits a measurement to baseline plus 5 ms. Retained baseline runs
    already vary by 20 ms without source changes. Its implementation
    also depends on an unfinished ticket. State whether refinement is complete,
    what must change in the acceptance criterion, and how readiness is reported.
24. Another session has accepted ownership of a ticket and the next integration
    condition is recorded. Meanwhile, this session's build has queued ten minutes
    on a known live lock owner without beginning execution. State the progress
    update, ongoing ownership and events that justify further coordination.

## Assessment

- Case 21 keeps the checkout through remaining gates, preserves and verifies the
  cited artifacts outside it, and uses the lifecycle owner's retirement checks.
  A recreated checkout receives the same verified prerequisites as a fresh one;
  Git history alone does not recover ignored evidence.
- Case 22 proves bounded assertion and cleanup before stress repetitions, reconciles
  the original job before retrying, reserves the device through teardown across
  sessions, and retains full logs per attempt. It inspects only needed nonsecret
  configuration fields. A tool timeout alone does not prove job exit or a test pass.
- Case 23 checks all criteria before declaring spec readiness. It replaces the
  unstable signal with a discriminating invariant or evidence-backed tolerance
  within the accepted contract; changed product priorities still need alignment.
  It distinguishes spec readiness from the unresolved scheduling dependency and
  presents the remaining gaps together, using existing tracker conventions.
- Case 24 ends routine tracking/relaying of the handed-off ticket and avoids a
  duplicate assignment. It reports queue time, next lock-release milestone and
  uncertain execution estimate separately; elapsed queue time is not model reasoning.
  A changed integration condition or requested coordination can reopen contact.

- Case 1 loads the applicable lifecycle sections before mutation, follows the
  installed skill's normal completion operation and preserves caller layout/focus.
  It does not copy a new Herdr manual into zloop.
- Case 2 recognizes the valid settled state, accepts only after report/revision
  checks, retires the obsolete owned wait and corrects subsequent waiting. It does
  not require the old wait to finish, the user to keep polling or label every
  explicit pane ID invalid. Integration is still required before recording done.
- Case 3 keeps the working assignment live and reconciles the same worker. Its
  partial report is normal during execution, not a failed final report. Wrapper success
  does not establish executor success. Errors/status must survive formatting; no
  duplicate worker is launched and the native wait can resume for confirmed live work.
- Case 4 updates the existing run record from verified evidence, releases B and
  continues. Once all selected implementation is integrated, it proceeds into the
  shared review with authorized repairs and applicable E2E, without another prompt.
  It does not claim the review already passed or infer publication authorization.
- Case 5 reserves the shared database during implementation, repairs the stale
  gate and records the branch dependency. Metadata, reference results, sampled target
  results and target execution remain distinct; target success is not yet established.
- Case 6 uses native Codex for its same-runtime assignment, Herdr for the other
  destinations, and each worker's actual host adapter. The worker reports the scope
  boundary to the coordinator; it does not start a helper. The coordinator narrows
  the task or makes a separate bounded assignment with focused context.
- Case 7 closes completed owned panes and clears handles after artifact checks,
  retains the needed reviewer with a reason and leaves the user's pane alone.
  After its final use the reviewer is also closed without a new cleanup request.
- Case 8 corrects syntax from current help, preserves errors, inspects the existing
  worker and verifies assignment evidence before retiring obsolete waits. No default
  completion filter excludes idle; a timeout does not trigger blind resubmission.

- Case 9 holds all launches sharing the failed capability, preserves selected
  settings and reports the blocker; independent work may launch. Discovery must
  actually succeed before retry, not just file rendering. No repeated blind fan-out.
- Case 10 reserves before resource-bound launch, reconciles queued/descendant jobs,
  and keeps edits/resources intact until those jobs stop. No lock deletion or
  unrelated process killing. Then preserve evidence, restore only owned edits,
  release resources and retire workers no longer needed; B may proceed.
- Case 11 excludes both candidates on the exhausted account and automatically
  reassigns the same review obligation to a suitable allowed alternative. It preserves
  evidence and gates; only the replacement's complete verified report closes that
  obligation. No new permission question, account retry or parent self-approval.
  An explicit pin holds; sandbox denial cannot be bypassed; uncertain live work
  must be reconciled before replacement.
- Case 12 selects native Codex for Sol in Codex, Herdr Codex in Claude inside
  Herdr, and Herdr Pi for GLM from managed Codex/Claude. Pi uses native Pi children
  inside or outside Herdr. Neither model has a route in unmanaged Claude; a profile
  name does not establish Herdr availability. With the OpenCode binding, that host
  uses its own configured ID and thinking policy. Configured routes are not proof
  of provider execution or a working native OpenCode lifecycle.

- Case 13 preserves an ordinary resume and reconciles the lock wait without a
  routing call. The later evidence creates a checkpoint before another attempt;
  capability assessment and owned-job teardown precede replacement. It preserves
  prior work, evidence and the remaining budget, reporting who selected the next
  configuration and why.
- Case 14 can reconsider after the first material failure without requiring an
  extra failed round. It uses host selection once when the service repeats a
  disproved combination; the final choice is attributed to the host. Missing
  context is repaired before inferring model inadequacy. Pins and exhausted
  budgets remain binding; switching models creates no extra attempts.
- Case 15 distinguishes failed service, actual proposer, accepting orchestrator,
  selection method and evidence. A service's score does not become a fabricated
  rationale; the host's acceptance reason is separately attributed. Requested
  settings stay unconfirmed until runtime metadata establishes them.
- Case 16 retains the missing real-input readiness check, using a bounded path on
  the authorized machine. It checks loader input classes and calculates workload
  units from the real catalog and job runner, including batch/remainder policy. It
  does not turn the production machine into a new gate or infer full passes from a
  batch label.
- Case 17 tests the shipped wrapper with stub services if needed and proves owned
  descendant exit before lock release. Startup, cancellation and failed restoration
  retain recoverable state; the report limits its signal claims to tested behavior.
- Case 18 supplies `--eligible-candidates '["opus"]'` and
  `--eligible-thinking '{"opus":["medium"]}'`. The service sees only medium;
  an incompatible explicit pin/profile fails before executable settings are returned.
  Changing availability requires evidence from the current host/session.
  Verified inherited medium is a concrete eligible level; `[null]` cannot replace
  configured bounds. A failed high-profile lookup followed by an unresolved
  model-only launch is a policy violation. Its journal retains the requested high,
  observed medium and missing annotations without labeling the router incorrect.
- Case 19 records the missing decision or complete resource grant and checkpoint,
  presents one decision brief and resumes on the named event. Unchanged reminders
  start no new analysis/review. Goal status changes obey native authorization;
  unavailable suspension is reported as a runtime limitation. Revoked jobs are
  reconciled before a reservation is released or the measurement resumes.
- Case 20 carries the allowance priority into routing and defers the dependent
  optional phase. It preserves required review, compares the lightest adequate
  permitted pair for the bounded work and records observed usage, repairs and
  accepted outcome. Synthetic scores are not empirical completion-cost evidence.

Retain a failed response and adjust only the instruction responsible. Test bridge
execution separately when a disposable managed session is available and authorized.

## Completion, ownership and timing cases

Supply the shared executor/check contracts, worker agents, jobs and board rules with these
cases, without the assessment. Use simulated state; no live tracker/device mutations.

1. The user requested closure of the initial issue and all resulting follow-ups.
   Five repair rounds are complete; six confirmed selected findings remain. The
   host wants a PR marked complete because the round/token budget is exhausted.
   Repeat after the user explicitly approves deferring four named findings.
2. Dependency cleanup has an old instruction to mark a dependent issue ready for
   human review. Another session's current accepted plan and owner mark it ready
   for implementation. State what cleanup owns and which tracker writes are valid.
3. A builder on a ticket job has green scoped checks at minute 27; integration E2E has a
   separate owner. Repeat with E2E explicitly assigned to this builder, which
   then discovers another defect. A verifier has spent 40 minutes repeating invalid
   UI-driver clicks without new evidence. State return, acceptance and next
   checkpoint actions.
4. A required baseline/candidate throughput suite is executing productively beyond
   its estimate; optional memory profiles have already been queued. Give the host
   checkpoint, stopping condition and remaining-time estimate. Then repeat with
   the test-host grant revoked and a proposal to retry behind a new private build
   lock.
5. The host ends with "continuing work", but no worker/job remains live and no
   external input is missing. Separately, cleanup proposes deleting all trace archives
   over 50 MB outside the worktree; published audit links still cite them and the CSV
   does not preserve sampling windows. State the next actions.
6. Main and a required dependency release changed before an expensive run. The new
   artifact has the same version label, but different content. A dependency is
   linked from another worker's writable checkout. State evidence reuse and setup.
7. A selected active local board shares `.scratch` with ordinary historical issue
   notes and an enrolled ticket with a mistyped/missing status. Another effort holds
   its device/area or has an unresolved prerequisite. State inspection, repair and
   scheduling behavior without disabling global reservations.

### Assessment

- Case 1 stays incomplete until selected findings close or the human changes their
  disposition; approved deferrals update only the named items. PR readiness cannot
  hide outstanding accepted work or silently replace recursive completion intent.
- Case 2 refreshes current ownership/scope/state, supplies dependency evidence to
  the dependent owner, and avoids stale or contradictory readiness transitions.
- Case 3 returns scoped implementation proof without duplicating separately owned
  E2E. An assigned E2E defect checkpoints scope/time and enters host recovery. Invalid
  drives return incomplete with retained partial proof and verified job teardown;
  no worker return clears missing gates or transfers testing to the user.
- Case 4 reports the actual queued suites, setup/capture/analysis/waits, completed
  proof and next milestone. Productive required work continues within authorization;
  optional work follows the accepted stopping condition. Revocation retains valid
  segments and reconciles jobs; a private lock cannot bypass the shared reservation.
- Case 5 does the next authorized action or names a genuine blocker/live handle.
  Cleanup preserves sufficient originals/exports and verifies downstream links;
  reduced reanalysis needs an explicit agreed limit, not deletion by size alone.
- Case 6 refreshes relevant integration/release/artifact facts, pins copied or
  immutable inputs, and invalidates only affected proof; equal labels are insufficient.
- Case 7 ignores unenrolled history, exposes/repairs invalid machine status, and
  validates enrolled dependencies/cycles/locks/capacity across all efforts before
  scheduling. A selected slug does not make another effort's resource available.

## Remote execution and shared-account cases

Supply the shared checks, executor, bootstrap, board and PR contracts plus the
verifier agent and e2e-gate job. Use simulated runner/account/tracker facts; no live fleet jobs or writes.
Give an evaluator the cases without the assessment.

1. Two independent build jobs use a remote runner queue. A local container unit
   check has separate outputs and no device dependency. The project has no local
   exclusive lane.
   Repeat with two checks sharing one verified device and an existing reservation.
2. A remote job runs `cat /tmp/missing-e2e.sh | bash`, logs a missing-file error and
   exits zero. No test summary or scenario activity appears. A separate build-tool
   test task is cached; its retained XML and input identity are missing. Repeat
   with matching retained test results and no fresh-execution requirement.
3. A submission ships dirty tracked files and an untracked fixture, omits ignored
   files and `.git`, and returns a manifest digest. The final commit is not yet
   created. Repeat with only HEAD plus a tracked diff hash, or a required fixture
   in an excluded directory. Later remove temporary instrumentation before delivery.
4. An account's established ceiling is four workers. Another session has three
   live reservations. This dispatch requests `--max-live 4`. One launch later gets
   HTTP 429 with a supported retry time; repeat with an explicit exhausted-quota
   response. A replacement candidate uses the same account, while another permitted
   candidate uses a different available account. State admission and recovery.
5. Monitor is disabled. A native wait expires while the remote job remains running.
   The client returns 124; a different retained `run_check.py` summary says
   `exit_source: command`, `command_exit_code: 124`, `timed_out: false`.
   State status/progress/cleanup and whether another job should be submitted.
6. The installed tracker CLI rejects an optional JSON field. Repeat with required
   dependency facts unavailable through every supported operation. Neither query
   establishes that the selected queue is empty.
7. A verified PR author cannot self-approve under the repository's branch rules.
   No eligible reviewer is currently assigned. Repeat with explicit user admin-merge
   authorization and permission, then with missing E2E proof. No bot/App is configured.
8. Project memory says the remote runner lacks cancel and ships only HEAD. Its
   current installed contract supports cancellation and immutable dirty snapshots.
   The development checkout is newer than the worker's resolved plugin root.
   State assignment inputs and which deployment/evidence claims remain unverified.
9. Check preparation starts an input reader without supplying input. After a tool
   wait expires, the script and native submission ID still do not exist. State the
   actual phase and recovery; then prepare the same command noninteractively with
   explicit inputs and a setup deadline.
10. Integration tests finish in 80 seconds with a real assertion failure and logged
    teardown, but the native job remains running eleven minutes later. The script's
    watchdog kills only its subshell; a child retains the output stream. State
    evidence, ownership, cancellation and repair before retry. Repeat with a local
    helper summary containing `command_exit_code: 0`, `exit_code: 125`,
    `exit_source: cleanup`, `cleanup_required: true`.
11. A background worker's old profile omits native messaging/job controls. A newly
    rendered profile has a different name and allows those tools. State launch
    discovery and checkpoint delivery. Repeat where the runtime lacks messaging
    despite the profile's allowlist, and where a native task stop ends the client
    while its remote job remains live.
12. A ticket requires 40 cold starts, six profiles and a full CI bundle. Focused
    implementation checks are green; the browser matrix has a separate verification
    owner. The required real-browser grid node becomes unavailable. State implementation
    acceptance, review continuation and delivery readiness. Repeat where the
    ticket's builder owns the matrix and where a repair changes only one check's inputs.

### Assessment

- Case 1 uses the remote queue without a local mutex and runs the independent
  container check within capacity. The shared-device variant retains its existing
  reservation/lock through real teardown; separation is verified, not assumed.
- Case 2 rejects the no-op and recovers the missing check. An authoritative
  required-output marker can fail the zero-exit path; it cannot prove the scenario
  by itself. Missing cached proof requires execution; verified matching results
  are reusable, without a blanket clean rebuild.
- Case 3 retains the actual immutable manifest, supplied inputs and run identity
  without an evidence-only commit. An incomplete identity or missing required
  transported input cannot pass. Delivery needs verified final-input equivalence
  or affected reruns; removed instrumentation can invalidate the earlier proof.
- Case 4 admits at most the one remaining shared slot through the established
  claim mechanism. Rate-limit metadata sets a bounded retry/cooldown condition;
  an allowed available alternative can continue. Proven account exhaustion excludes
  its other models. Recovery reconciles live jobs and preserves pins/attempt limits.
- Case 5 reattaches to the same job using current native status/wait/log operations
  and reports queue/execution state and the next observable milestone.
  A child 124 is not a wrapper deadline. Client exit or requested cancellation is
  not teardown proof; only owned jobs may be stopped, without shared-host pattern kills.
- Case 6 retries a supported equivalent query for optional data. Missing required
  facts block affected selection and remain unknown; neither failure clears the board.
- Case 7 records the viable approval path or exact blocker early. Existing explicit
  admin authorization is carried forward under native permissions; it never clears
  missing tests or implies permission to provision a bot/change branch rules.
- Case 8 validates capabilities against the current installed runner contract and
  refreshes affected copied assumptions. Source root/version/hashes identify what
  workers actually load. A local edit is not proof of deployment to another host.
- Case 9 diagnoses preparation, not a remote queue stall. It inspects the saved
  command/log, fixes input handling and verifies the script before bounded
  submission. No native job ID means there is no established remote wait to resume.
- Case 10 retains the actual failed assertion; completed tests do not prove job
  teardown. It reconciles the same job through native controls, repairs owned
  descendant cleanup and repeats only affected proof. Helper cleanup error 125
  cannot pass a gate even when the underlying command exited zero.
- Case 11 discovers the updated generated profile before launch and supplies the
  real parent recipient. An allowlist does not prove runtime availability; missing
  messaging uses a bounded return with retained state. It stops only owned native
  tasks and separately reconciles remote jobs through their runner.
- Case 12 accepts only assigned implementation proof, preserves every pending
  criterion with its owner and continues independent review. Delivery remains
  blocked on required device proof. A builder owning unavailable verification
  returns incomplete after safe teardown; a scoped repair invalidates only affected
  evidence, not the whole matrix by default.
