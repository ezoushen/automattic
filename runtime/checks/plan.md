# Plan checks

To plan a check's tier and owner and to accept or reuse its result, read [plan and accept checks](accept.md).

Contents:
- [Coordinate the actual resource](#coordinate-the-actual-resource)
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
budget. `scripts/resource_lock.py` remains an optional helper for projects that require it.
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
