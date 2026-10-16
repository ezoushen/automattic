# Herdr environment guidance

Load alongside the current host adapter when `HERDR_ENV=1`. Herdr provides a
transport; it does not replace the Claude, Codex, Pi or OpenCode host identity.
Read the installed Herdr skill when using that transport. It owns CLI syntax,
session prerequisites and identity checks; this file owns Automattic coordination.

## Route before launching

Prefer configured native children for same-runtime assignments, including Pi-to-Pi.
Use Herdr for configured cross-runtime assignments or an explicit Herdr route.
Preserve an explicit user-selected executor and model policy;
do not infer the destination from a model name or silently replace a saved route.
Use [runtime definitions](selection.md#configure-a-role) to share launch routes
across models; model bindings declare each runtime's registered ID and thinking
policy. Role pools stay shared; routing profiles override candidate/thinking by
worker runtime only when selected explicitly. If a saved route sends same-runtime
work through Herdr, show the mismatch and
use the models skill for an authorized correction. Environment detection alone
does not rewrite configuration. Native capacity or permission limits do not
authorize a Herdr fallback; queue work or report the boundary.
Quota/provider failures instead follow [pool recovery](selection.md#feedback-and-recovery):
exclude the failed account/capability, choose a suitable allowed alternative and
state the switch. Do not try another model on the same exhausted account.

Pass the destination's host adapter to a cross-framework worker, plus this guide
if it runs inside Herdr. It completes the assigned scope directly. Additional
assignments return to the orchestrator, which resolves each worker from its actual
runtime bindings and the active router.

Use absolute paths for the adapter, role and required method sources, and verify
their reads succeeded before productive work. A long Claude prompt can arrive as
pasted content: naming a slash command inside it does not prove phase invocation.
Use a short native slash command for an authorized phase reserved for explicit
user invocation; keep its longer scenario in a supplied file. Use the Skill tool
only where the skill permits model invocation. Retain the actual source/result.
Session-local settings isolation must preserve required installed dependencies
and Herdr's native identity hook; verify both before accepting the launch.
Launch an OpenCode 2 worker as the full TUI (`opencode`); Herdr's integration
reports only its activity and session, not `mini`'s. Set its settings through
the [OpenCode adapter](opencode/adapter.md#top-level-workers) after the startup probe. For guarded retirement, use an isolated configuration that
preserves the installed server plugin and, for the full TUI, its native TUI session
reporter. Reproduce the installer's current TUI configuration in the isolated
config directory, including its referenced module; a server-plugin entry alone
does not load the TUI reporter. Use the supported configuration filename (for
example, `tui.jsonc`) rather than assuming another file is read. An isolated
OpenCode 2 configuration also needs its own service port (`opencode service set
port <free port>`); otherwise it collides with the user's background service.
Check `integration status` and the actual `agent_session` before productive work;
a current server alone does not establish that its integration is loaded.
If startup returns before the native input UI finishes loading, wait for its
actual input marker before the first prompt. After a stalled prompt, inspect the
same conversation and its native output before deciding whether to retry.
Accept startup only after all required source reads and the final assistant turn
have completed; an early READY sentence or transient settled status is insufficient.
Parse the complete retained native export before collection. If the installed
OpenCode CLI truncates exports captured through a pipe, redirect stdout directly
to a file and validate that artifact; exit zero alone does not establish integrity.

## Wait and recover

Bind each prompt, independent wait and collected result to its registered attempt
under [worker attempts and collection](worker-lifecycle.md). Resume from its pending
receipts and native worker state; rearm consumed waits after reconciliation.

Read the installed skill's completion section and current command-group help
before the first wait. Use its default settled-state operation, with a bounded
timeout; `idle` can be a completed turn. Reserve state filters for a specific
state-dependent task. For the lifecycle's `notify` channel, use
`herdr --session <session> agent prompt <parent> {receipt}` with no `--wait` or
`--timeout`; for wake-triage `capture`, use
`herdr --session <session> agent read <worker> --source visible --lines 200`. Acceptance still requires this assignment's full report
and revision, including evidence that the submitted work actually ran.

Preserve the exit status and error body. A syntax error needs corrected syntax
from the installed CLI, not another wait using the same command. After a timeout,
stalled prompt or uncertain submission, inspect that same worker before waiting
again or resubmitting; neither a shell success message nor timeout is completion.
Workers raise holds through the supplied escalation channel, or by returning
bounded. If a worker opens its native question UI instead (for example Codex
`request_user_input`), the orchestrator answers only within its own mandate. Record
the answer as orchestrator-originated, not the user's, and leave choices reserved to
the user with the user.
Inspect native approval dialogs against existing explicit user authorization;
when it covers the exact fixture action, apply that scoped approval without asking
again. Otherwise keep the dialog for the user. Stop obsolete owned monitors once the
assignment settles and its result is verified.

## Close owned workers after their final use

Record created pane/worker IDs with the assignment. After accepting its final
result and verifying durable reports/evidence, close its owned pane automatically
through the installed skill, then confirm closure and clear the live handle. Use
the [collection/retirement integration](worker-lifecycle.md#arm-collect-and-rearm)
so native closure also retires its registered handle.
An idle reviewer needed for a repair recheck stays available until that phase ends;
retiring it early requires the explicit handoff in the [skill executor](executors/skill.md).
Retain active, approval-blocked or deliberately reusable workers with a stated
reason. For a reusable worker, the reason names the assignment it will take next.
When that assignment goes to another worker or finishes, close the pane. Existing user panes and the caller's pane are not cleanup targets.
Before returning, account for every owned worker as closed or retained with its
next use/blocker; no separate cleanup request is needed for completed owned work.

## Hand off to another machine

Before sending work to a pane on another machine or session, verify that the
target can do it:
- its OS and toolchain;
- the repository, branches and credentials;
- the required devices;
- every named pin, such as a machine profile, actually exists there (`herdr machine list`).

If any of these is missing, report it rather than sending the work anyway. Write
the scenario to a file and send a short slash command. A synced copy of the board is
a second orchestrator. Add a `Handed off to <machine/pane> at <time>` line to the local run report before
the remote starts. If the handoff fails, add `Returned at <time>`.
