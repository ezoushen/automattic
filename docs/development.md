# Development

Changes to the plugin follow its own architecture rules
([writing-agent-docs](../.agents/skills/writing-agent-docs/SKILL.md)); the checks
below enforce them. Read the [decision index](adr/README.md) before an architectural change:
only accepted ADRs bind, and a change that conflicts with one is raised, not worked around.

## Suite and hooks

`python3 tests/run_all.py` runs every `tests/test_*.py` file in parallel (about 15 s)
with the plugin environment's `.venv` and exits 1 on any failure. Tests are
`unittest` cases, so one file, class or test runs on its own. The default suite needs
an installed `claude` for `test_claude_effort.py`, which runs it against a local fake
API. `tests/support.py` locates and loads the scripts and builds an environment whose
Automattic state, configuration and Codex home are temporary; use it for a new test
that runs a script which writes machine state.

Enable the Git hooks once per clone with `git config core.hooksPath .githooks`:
- `pre-commit` (about a second) runs the doc checker on changed files and checks the
  syntax of staged Python and shell files. The doc check reads files as they are on
  disk, so unstaged edits and untracked docs count, not only what is staged.
- `pre-push` checks out each pushed commit into a temporary worktree and runs the
  whole-repo doc check and the suite there, so the result is the pushed code's.
  Commits the remote already has are not rerun; an older commit without the checker
  or suite is pushed with a warning. The checks run in a session of their own, without
  a terminal: Ctrl-C or any signal to the hook reaches them once, as the same signal,
  followed by TERM after 2 s and KILL after 5 s, and the temporary worktree is
  removed. Not covered: a check that starts its own session (`setsid`), and `kill -9`
  of the hook, which leaves the checks running; the next push removes their worktree
  once they have finished.

In Claude Code, `.claude/settings.json` also runs the architecture part of the doc
checker after every Edit or Write. `--no-verify` skips either Git hook.

## Native checks

The package and profile readers of the installed CLIs are opt-in and make no model
calls:

```sh
.venv/bin/python -B tests/test_router_profiles.py
.venv/bin/python -B -m unittest discover -s tests -t tests
# Installed CLI discovery, OpenCode 2 and Claude profile readers:
AUTOMATTIC_NATIVE=1 .venv/bin/python -B tests/test_cross_harness.py
AUTOMATTIC_NATIVE=1 .venv/bin/python -B tests/test_agent_models.py
# Pi SDK discovery and bootstrap, isolated from user extensions:
AUTOMATTIC_NATIVE_PI=1 .venv/bin/python -B tests/test_cross_harness.py
```

They validate discovery, invocation metadata and registration. When this source is
installed in Claude, the check also verifies that the development plugin is enabled
and has no loading errors, including missing dependencies. Pi's isolated SDK check
also exercises bootstrap startup/reload. They do not launch workers or establish that
native hooks are trusted in a live session. Use native readers for shared skill
metadata: the generic skill-creator validator does not accept the Claude-specific
frontmatter this package uses.

**Still requires a live installed session in each host:** worker spawning and context
loading, review/fix/E2E, and interruption/resume. These are not claimed as passing.
Use the [review behavior rehearsal](review-rehearsal.md) for walkthrough discussion,
review handoff and finding adjudication, and the
[dispatch recovery rehearsal](dispatch-rehearsal.md) for executor completion, failed
waits, state reconciliation and automatic review continuation.

## Usage and spend tools

- The read-only [usage helper](claude-usage.md) ranks local Claude session families,
  includes native workers and attributes related worktree sessions over an explicit
  time window. It reports recorded tokens without estimating account credits.
- The read-only [effort spend report](effort-spend.md) divides an effort's worker and
  coordinator tokens by its accepted tickets and shows what the coordinator's tokens
  went to. It reads Claude, Codex and Pi transcripts.
- `scripts/allowance.py status` reports the Claude Code and Codex allowance windows and
  their pressure levels; see [selection](../runtime/routing/choose.md#allowance).
- `scripts/outcomes.py summary [--agent <agent>] [--job <job>]` counts each
  candidate's accepted, failed and pending attempts across efforts;
  `scripts/outcomes.py import <decisions.jsonl | workers.sqlite>...` adds past decision
  journals and lifecycle state files once.

## Local Markdown board

The scheduler runs from any directory and is not used for remote trackers:

```sh
python3 /path/to/automattic/scripts/next_tickets.py --repo /path/to/project feature-name --check
python3 /path/to/automattic/scripts/next_tickets.py --repo /path/to/project feature-name --max-live 3
python3 /path/to/automattic/scripts/next_tickets.py --repo /path/to/project feature-name --set feature-name/01 status=implementing --counts
```

Omit the slug for all efforts. An unknown slug or argument fails. Scope controls
selection, board, counts and mutation; locks and validation still see other efforts.
Use one orchestrator per checkout. Invoke the plugin's resource lock
(`scripts/resource_lock.py`) directly when a project needs it; never copy it into the
project.
