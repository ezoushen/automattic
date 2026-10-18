# Automattic

One maintained workflow for Claude Code, Codex and Pi: mandate → align → refine →
dispatch → review (including E2E with autofix) → PR. Effort state stays in `.scratch/<slug>/` in the target repository;
skills, agent and job instructions, scheduling and check execution guidance stay in this plugin.

This is the maintained source tree. Package-manager cache copies are deployments;
make changes here. Development symlinks expose those changes without maintaining
separate copies of skills or scripts.

## Layout

| Path | Owns |
|---|---|
| `skills/` | Thin entry skills: explicit workflow, briefing and settings skills; automatically selectable decision, routing, writing and housekeeping skills. A skill names its flow or runtime doc and links no other skill |
| `scripts/` | Scheduler, optional build mutex, worker/decision resolution, calibration and runnable checks |
| `bootstrap.md` | Session rules every host reads first, with the triggers table for rules that fire outside their owner |
| `flows/delivery/`, `flows/review/`, `flows/remediation/` | Procedures by phase with their job files (`jobs/`): dispatch, housekeeping and PR; shared review; remediation audit |
| `standards/` | What good looks like: PR description, code comments, documentation and the remediation kinds (`kinds/`) |
| `hosts/claude/` | Claude session part and worker part (lifecycle and native settings controls) |
| `hosts/codex/` | Codex session part, worker part (lifecycle and capacity) and hook registration |
| `hosts/pi/` | Pi session part, worker part (shared-agent delegation) and bootstrap extension |
| `hosts/opencode/` | Model settings/profile selection; not a full workflow adapter |
| `schemas/` | Configuration, worker selection and decision request contracts |
| `benchmarks/` | Synthetic decision calibration examples |
| `addons/show-me/` | Shared presentation reference and thin manual show-me entry |
| `hosts/herdr.md`, `hosts/executors/` | Herdr environment guidance; Bash, Sub-agent and Skill execution adapters |
| `runtime/workers/`, `checks/`, `routing/`, `resources/`, `decisions/`, `config/` | Shared runtime rules by reader, each file small enough for one read; a module depends only on those after it in this order, and the configuration format is in `config/` |
| `flows/board/`, `flows/planning/`, `flows/setup/` | Shared flows: board operations and tracker conventions; question filter, authority, ledger record and refinement; configuration change procedure for the setup-automattic and models skills |
| `agents/` | Three worker agents (builder, reviewer, verifier): permissions, principles and core skills; Claude loads them natively |
| `hooks/` | Shared session-start hook; Claude hook registration |
| `plugin.json`, `.claude-plugin/`, `.codex-plugin/` | Portable metadata and compatibility registration |

The host bootstrap injects the paths of `bootstrap.md` and the active host's session
part. Phase skills load them before acting; code-comments and housekeeping also work independently. Codex workers use their native child-agent tools with an
explicit agent and job paths; no imported agent copies or orchestration server is
needed. All three workflow hosts load the same shared skill files.

Codex planning loads a short session part; worker lifecycle and peer messaging are
loaded only for dispatch or worker assignments. Children can exchange concrete
findings through native messaging while the orchestrator retains ownership of
scheduling and integration.

## Architecture

The Markdown is layered so a reader follows links in one direction. Entry skills and
hooks sit on top; below them come `bootstrap.md`, the flows (delivery and remediation, review,
planning, board and setup), `agents/`, `standards/`, `hosts/` and the `runtime/` modules
(workers, checks, routing, resources, decisions, config). A doc links only its own module or
a lower one, no skill links another, and `scripts/` and `hooks/` import under the same order.
`.agents/skills/writing-agent-docs/architecture.json` records the order; the doc checker
and `tests/test_import_direction.py` enforce it with no recorded debt.

To add a host, executor, agent, job, kind, standard or flow, follow
[extend the architecture](.agents/skills/writing-agent-docs/SKILL.md#extend-the-architecture),
which holds the rules for agents and contributors alike.

## Requirements and usage

Python **3.9+**, Git, Bash, and a Unix platform with `fcntl` (macOS/Linux). The
workflow composes the installed Matt Pocock skills. Simplicity review uses its
Standards axis. Resolve Matt by its exact
namespaced catalog entry so a bundled skill with the same short name cannot replace
it. Claude declares Matt as a plugin dependency; other hosts use their installed
skill catalog.

Briefing and walkthroughs use the [composable show-me adaptation](addons/show-me/README.md),
with HumanLayer's MIT-licensed visual guidance in one shared reference. Both skills
use it directly in the same response on every host; no second command or external
show-me plugin is required. The adaptation also preserves a manual show-me entry
for standalone use. See its README for installation and upstream updates.
After changing Claude dependencies, check `claude plugin list` for loading errors
before reloading Automattic. Codex has no Claude-style skill dependency declaration;
its required presentation reference is packaged with the plugin.

Default sub-agent execution requires native child tools (Pi uses
pi-subagents); configured executors require their selected tools/skills instead.
All hosts apply the shared resolver's model/thinking settings and retain native
defaults for omitted fields. Adapters translate settings into native controls;
workload labels do not select models.

PR descriptions use WHAT / WHY / HOW, adapted to the repository's PR template.
The [PR skill](flows/delivery/pr.md#description) reuses Matt's writing reference when
available and existing verification evidence; Automattic owns delivery and publication.

Existing project-management conventions take precedence over Matt's setup options.
Use the configured Linear, GitHub or other tracker as the work-item authority;
local Markdown is the fallback. Remote dispatch reads and updates issues directly,
without `.scratch/*/issues`, local ticket front matter or the local scheduler.
Reports retain only execution/recovery evidence. Tracker updates follow the
project's authorization, priority and completion rules; no synchronization service.

Local Markdown scheduler use, from any directory (not required for remote trackers):

```sh
python3 /path/to/automattic/scripts/next_tickets.py --repo /path/to/project feature-name --check
python3 /path/to/automattic/scripts/next_tickets.py --repo /path/to/project feature-name --max-live 3
python3 /path/to/automattic/scripts/next_tickets.py --repo /path/to/project feature-name --set feature-name/01 status=implementing --counts
```

Omit the slug for all efforts. An unknown slug or argument fails. Scope controls
selection, board, counts and mutation; locks and validation still see other
efforts. Use one orchestrator per checkout. Project-specific build commands and
gates come from the repository's existing instructions and build/CI configuration.
No new project loop document is required. Invoke the plugin's build wrapper
directly, never copy it into the project.

To try the source in Claude without replacing the installed plugin:

```sh
claude --plugin-dir /absolute/path/to/automattic
```

Claude user development installation: `automattic@automattic-dev` is enabled,
with `~/.claude/plugins/cache/automattic-dev/automattic/0.3.0` symlinked to this
workspace. Edit here, then run `/reload-plugins` in an existing Claude session;
new sessions read the current files. No reinstall is needed. A marketplace update
to another version can select a new cache directory; relink that entry when
changing the installed version. Use the native package-reader checks below to
verify discovery after changes.

Use `/automattic:pipeline` in Claude or `$automattic:pipeline` in Codex to see the
workflow. Codex's local catalog is `.agents/plugins/marketplace.json`:

```sh
codex plugin marketplace add /absolute/path/to/automattic
codex plugin add automattic@automattic-dev
```

The installer copies a snapshot. For development on this machine,
`~/.codex/plugins/cache/automattic-dev/automattic/0.3.0` is a real directory whose
workflow directories are symlinks into this checkout, including `skills`, `agents`,
`flows`, `runtime`, `standards`, `hosts`, `hooks`, `scripts`, `schemas`, `benchmarks` and `addons`, and
the top-level `bootstrap.md` file is a symlink too.
Its `.codex-plugin/` directory and
small `plugin.json` registration are regular files/directories, copied from this
tree's Codex manifest; the portable root `plugin.json` is omitted from that local
wrapper. This selects Codex's registration, including its SessionStart and Stop hooks.
The installed scanner requires a real version directory and manifest. When setting
up elsewhere, replace only a verified Automattic snapshot with this wrapper and
links; preserve unrelated installations. Edit workflow content in the source.

Changes within linked directories need no copying or reinstall. Start a new Codex
session to refresh loaded instructions and hooks; existing conversations
may retain earlier instructions. Review any native hook-trust prompt. A reinstall
or version change may replace the links; verify them afterward. Refresh the small
registration when the Codex manifest changes and add a link when introducing a new
top-level package entry; `flows/`, `runtime/`, `standards/`, `hosts/` and `bootstrap.md` are such entries, so link each in an
existing cache directory before starting a session. Check installation with
`codex plugin list --marketplace automattic-dev --json` and the native readers below.
Also check runtime `skills/list` and `hooks/list`: a listed installation alone does
not prove that its skills or hook were loaded.
Avoid enabling two Automattic releases in the same session.

Pi development installation uses two symlinks to this source tree:

```sh
mkdir -p ~/.pi/agent/skills ~/.pi/agent/extensions
ln -s /absolute/path/to/automattic/skills ~/.pi/agent/skills/automattic
ln -s /absolute/path/to/automattic/hosts/pi/bootstrap.ts ~/.pi/agent/extensions/automattic.ts
```

Keep an existing matching symlink; do not overwrite a different installation.
For the earlier link to this repository's root, retarget only that verified
development symlink to `skills/`. Pi discovers skills recursively; restricting the
link prevents optional add-on skills elsewhere in the repository from loading.
Re-point an extension symlink that does not target `hosts/pi/bootstrap.ts`.
Run `/reload` in Pi, then `/skill:dispatch <scope> --autofix` or
`/skill:walkthrough <target>`. The extension supplies the bootstrap and Pi's session part before
each turn; it registers no tools or commands. With explicit extension loading
disabled, supply `harness=pi` when invoking a phase instead. Planning/review can
run without delegation where the shared procedure allows it; dispatch requires
the installed `subagent` tool. See the [Pi session part](hosts/pi/session.md).

## Guided setup

Use [setup-automattic](skills/setup-automattic/SKILL.md) for a guided explanation of the current
configuration and help changing it. It shows available workers, launch routes,
selection policy, decision opt-ins and which scope supplies each effective value.

| Host | Command |
|---|---|
| Claude Code | `/automattic:setup-automattic` |
| Codex | `$automattic:setup-automattic` |
| Pi | `/skill:setup-automattic` |

Start with a tour or a specific question:

```text
/automattic:setup-automattic
/automattic:setup-automattic Why does this project use a different router from my user default?
/automattic:setup-automattic Disable recovery decisions for this session only.
```

A tour is read-only. Requested changes continue in the same conversation, at user,
project or session scope, with a focused diff and effective result. It follows the
project's existing tracker and verification conventions without creating a competing
setup. No worker launch or calibration run is part of inspection.

`setup-automattic` and `models` use one [configuration procedure](flows/setup/procedure.md).
Use `models` for direct inspection/edits when you already know the setting; no second
command is needed during a guided setup.

## Inspect recorded Claude usage

The read-only [usage helper](docs/claude-usage.md) ranks local session families,
includes native workers and separately attributes related worktree sessions over
an explicit time window. It reports recorded tokens without estimating account
credits and makes no model calls.

The read-only [effort spend report](docs/effort-spend.md) divides an effort's worker
and coordinator tokens by its accepted tickets, and shows which triggers and
activities the coordinator's tokens went to. It reads Claude, Codex and Pi
transcripts.

`scripts/allowance.py status` reports the Claude Code and Codex allowance windows and
their pressure levels; see [selection](runtime/routing/choose.md#allowance) for the
status-line line that feeds Claude's.

`scripts/outcomes.py summary [--agent <agent>] [--job <job>]` counts each candidate's accepted,
failed and pending attempts across efforts from the lifecycle's outcome ledger;
`scripts/outcomes.py import <decisions.jsonl | workers.sqlite>...` adds past decision
journals and lifecycle state files once.

## Configure workers

No configuration is required for the existing native workflow. To choose how a
worker runs, its model, or its thinking level, use the **models** skill in chat:

| Host | Command |
|---|---|
| Claude Code | `/automattic:models` |
| Codex | `$automattic:models` |
| Pi | `/skill:models` |

Start by inspecting the current setup, then configure one agent. These examples use
Claude's command spelling; use the corresponding command above in Codex or Pi:

```text
/automattic:models
/automattic:models set reviewer --route executor=subagent mode=inherit
/automattic:models show reviewer --route
```

`--route` selects the new per-agent configuration. The first set command selects
the native reviewer and preserves its native model/thinking settings, bypassing
older Automattic model overrides for that agent. Other agents stay unchanged. The
skill prepares the isolated validator environment when needed, validates the
configuration and reports where it was saved. It does not start a worker.

Inside Herdr, [caller-specific routes](runtime/config/catalog.md#caller-specific-skill-routes) let
Claude/Codex use native workers for same-runtime work and Herdr for other destinations.
The [Herdr guidance](hosts/herdr.md) covers waits and automatic cleanup of owned workers.

You can also describe the change after the command:

```text
/automattic:models Configure this project's reviewer to use the subagent codex:codex-rescue and inherit its destination settings.
/automattic:models Reset only the reviewer's thinking override; keep its executor and model.
```

The named delegate requires the official Codex plugin in Claude Code. Names and
model controls must exist in the host where execution takes place; configuration
validation does not prove that a live delegate can run.

Project scope is the default. Add `--scope user` for personal defaults shared
across projects, or `--scope session` for temporary overrides that survive resume.
To select a model, supply its actual supported ID and optionally
`thinking=high`; explicit choices enable override mode. Changing models never
changes the main session. Reset with `--route` and no field selection restores
inheritance while keeping the selected executor.
For bounded thinking, use `thinking={"default":"medium","allowed":["medium","high"]}`.
An agent can define a pool of allowed candidates. The `router` chooses through a
skill, a built-in System One decision-model client, or a named profile. Profiles
use `profiles.<name>.<agent>.<worker-runtime>.candidate/thinking`; omitted fields
leave selection unchanged. See [routers and sparse profiles](runtime/config/routers.md#routers-and-sparse-profiles)
for examples. The built-in [model-routing skill](skills/model-routing/SKILL.md)
chooses in the host's existing context, without a separate model call.
For a local Jev/OpenJev service, configure its endpoint and model ID under
`decisions.backend`, enable `worker-selection`, and select
`router: {"type":"decision-model"}`. The
[decision-model router](runtime/routing/decision-model.md) selects a
permitted model/effort pair and falls back to host judgment if unavailable or
undecided. The [shared decision loop](runtime/decisions/phases.md) uses the same backend
for recovery and other explicitly enabled phase checkpoints. The configured
checkpoint helper records consultations or justified skips, reuses unchanged
resumes and checks expected phase records at existing handoffs. Enable only the
desired families. Labeled calibration replays establish a
baseline; active use warns about changed configuration or possible behavioral drift.
Synthetic examples are integration checks, not evidence of production accuracy.
The [decision journal](runtime/decisions/journal.md) retains exact prompts, responses,
host actions, requested/observed worker settings and outcomes beside session artifacts.
Use `/automattic:decision retro <journal>` for an offline retrospective, or
`/automattic:decision replay <journal> <cases>` for an explicitly requested, bounded
wording/order experiment. Replay preserves live settings and the calibration baseline;
it does not train a model.
Existing checkpoints accept [bounded image evidence](runtime/decisions/images.md)
for visual choices, with hashed retained assets and exact replay; screenshots do not
replace executed acceptance evidence.

Each bounded assignment goes directly to one worker. The orchestrator owns
rescoping, independent review and replacements; workers complete their scope
without creating nested teams. Existing fixed instances and thinking bounds remain
supported. Configuration inspection never starts a router or worker.

The [configuration guide](runtime/config/executors.md) contains executor examples
and manual setup; [reset and troubleshooting](flows/setup/troubleshooting.md)
covers reset recipes and fixes. Choose:

- **Sub-agent:** the host's native worker or an installed named delegate.
- **Skill:** an installed skill plus a follow-up instruction, such as Herdr.
- **Bash:** a program implementing the documented assignment/result contract.

Encapsulate reusable skill usage under `executor_types.<name>`, then select
`{"type":"<name>"}` in a route or agent. See
[named skill executor types](runtime/config/executors.md#named-skill-executor-types).

Define each model once under `models` with a task-fit description and runtime
bindings. Each binding holds its registered `id` and thinking policy; top-level
`runtimes` holds shared launch routes. Agents reference model names individually or
in pools; complete executor instances remain supported. A Pi model can use a native
Pi subagent or a Herdr-launched Pi worker from Codex, using the same binding.
When credits or a provider are unavailable, automatically choose a suitable remaining
pool candidate, preserving user pins, scope and permissions. No extra approval is
needed; exhausted pools report the blocker. Pools can opt out with `fallback:false`.

Configuration lives in `.automattic/executors.json` or
`~/.config/automattic/executors.json`; its schemas ship with this plugin.
Use `router: {"type":"profile","profile":"balanced"}`, `--config-profile <name>`,
or `AUTOMATTIC_PROFILE` to select a routing profile. With no router configured,
the host uses `automattic:model-routing`; no host/Herdr profile is selected implicitly.
See [host selection](runtime/workers/launch.md#host-selection) for precedence.
User-defined executor types encapsulate skill usage; built-in executors remain
subagent, skill and bash. OpenCode's native dispatch workflow is not implemented;
a configured external executor owns its lifecycle and needs runtime verification.

Existing `models.json` preferences still apply to unconfigured native workers.
Older structured `/models` commands without `--route`, `--config-profile`, session scope
or pool options keep that behavior; see
[legacy model preferences](flows/setup/legacy-preferences.md). New agent instances do not merge
those files. Old executor-package/`routes` files need the explicit
[migration](flows/setup/troubleshooting.md#migration).

## On-demand briefing

Request a read-only progress snapshot with `/automattic:brief` in Claude,
`$automattic:brief` in Codex, or `/skill:brief` in Pi. It defaults to the active
task; optionally name an effort, branch, PR or a focus such as "what needs me?".

The [brief skill](skills/brief/SKILL.md) explains the goal, completed/current/next
work, review and verification status, and decisions needing your input. It checks
fresh scoped evidence, identifies stale or unavailable state, and preserves the
running workflow. It creates no journal or maintained-document update.
The bundled show-me reference supplies a compact visual when it clarifies progress
or dependencies, in the same briefing response. The standalone show-me command
remains manual. Briefing defaults to in-chat output; exports require a request.

## Planning without repeated approvals

Mandate and alignment reuse accepted goals and constraints, investigate facts and
choose reversible engineering details. Only material unresolved forks need your
input. Alignment produces one WHAT / WHY / HOW brief, with diagrams at the depth
the decision needs. Add `--interactive` to either command when you want a human
checkpoint before dependent work; a plan-only request remains planning only.

## Guided walkthrough

Use `/automattic:walkthrough <branch|PR-number|PR-URL>` in Claude,
`$automattic:walkthrough <target>` in Codex, or `/skill:walkthrough <target>` in Pi
when you want to understand a change and form a judgment. `--base <ref>` selects
the comparison. The [walkthrough](flows/review/guided.md) explains WHY / WHAT /
HOW using the shared show-me guidance, deepens through your questions, and guides
the next step. It can finish with shared understanding and review criteria.
When you ask to proceed, it continues into the shared review procedure in the same
conversation, carrying the target, decisions and authorization forward. You do not
need another command or task. `/brief` remains a progress snapshot.

## Scoped review

```text
/automattic:review feature/login --base main
/automattic:review 123
/automattic:review 123 --comments confirm
/automattic:review 123 --comments post
/automattic:review https://github.com/owner/repo/pull/123 --autofix
```

Review proceeds through direction (WHY / WHAT / HOW), scope/blast radius, then
implementation. Foreign PRs establish direction; our own work reuses alignment and
checks for drift. Each layer collects its findings together. An unresolved upstream
decision pauses dependent detail review while independent scopes continue. Matt's
Standards/Spec review runs once for each eligible implementation batch; later rounds
reopen only affected scope and evidence. Security, testability, integrity and
maintainability are lenses within these layers. Documentation correctness stays a
hard gate. See [review layers](flows/review/layers.md).

Review starts assessment directly, reusing any accepted walkthrough decisions.
By default it produces local comment drafts without changing source code.
`--autofix` permits confirmed in-scope repairs and includes applicable E2E
verification, even when review finds no repair to make.
Choose `--comments confirm` to see the exact batch before approving publication,
or `--comments post` to authorize direct posting of verified findings. The default
`--comments draft` stays local. These choices are independent of a prior walkthrough
and autofix; "show me before posting" and "post directly" work too.
Approving one previewed batch does not authorize new findings on later rounds.
Comment publication does not authorize pushing code or a merge verdict.
Priority comes from current user
direction, accepted alignment/ledger and project standards; absent authority is
marked provisional. Unrelated advice is retained in a separate follow-up list and
cannot become a blocker or repair without an explicit scope decision.
For an explicit request to exhaust a backlog, dispatch refreshes that selection
after each batch and queues matching follow-ups and children of selected issues.
Each review stays scoped; finishing one batch does not finish the broader request.
Merge and rollout authorization remain separate and are reused when already given.

Code comments and API documentation are source contracts. Their correctness is a
hard review/delivery gate, including existing docs invalidated by the change.
Missing, incomplete or failed documentation review blocks delivery even when
executable tests pass; unrelated documentation cleanup remains a follow-up.

[code-comments](standards/code-comments.md) holds the shared, language-independent
writing rules. Builder workers load it at entry; any agent can select
it automatically while writing comments or invoke `/automattic:code-comments`.
Its [research basis](standards/code-comments-sources.md) separates common
principles from language-specific style choices. Review owns the hard gate.

[housekeeping](flows/delivery/housekeeping.md) removes task-created disposable
intermediates and test outputs, preserves required evidence and updates affected
project documentation using existing conventions. Maintained docs describe current
behavior; retained development history belongs in `journals/` or the project's
established changelog. Builders apply that policy while editing,
and review checks it. Invoke `/automattic:housekeeping`
independently; dispatch applies it before review, and PR preparation checks
for remaining work. It reuses code-comments for source documentation. Cleanup
does not delete unrelated files, retire branches or replace the review gate.

[remediate](skills/remediate/SKILL.md) finds and proves `tautological-tests`,
`misleading-comments` or a free-form goal. Invoke
`/automattic:remediate [kind|"goal"] [--base <ref> | <path>... | --project]` in Claude,
`$automattic:remediate ...` in Codex or `/skill:remediate ...` in Pi; OpenCode uses
its native skill discovery. The skill's [arguments](flows/remediation/procedure.md#arguments)
table lists each value and its default.
It runs only when explicitly requested. Scope defaults to the established diff;
named paths repair after proof, while whole-project scans report first and wait
for confirmation before repairs. It changes tests/comments only and reports a
suspected runtime bug when a corrected test fails on the real implementation.
A test is [tautological](standards/kinds/tautological-tests.md) when a defect in
the behavior it claims leaves it passing; review applies the same check to every
added or modified test by reading: an assertion checklist, routing by the decision
model, and a code trace for expected failures checked only by code.
The [comment audit](flows/remediation/procedure.md#comment-audit) lists added plain
comment lines as review candidates, with language and syntax limits documented
there. Remediation supplies its own proof and test-first repair procedure.

The [shared review procedure](flows/review/review.md) owns the review workflow's
repair loop with its own [Standards/Spec method](flows/review/method.md) and reuses Matt's
grilling, diagnosis and TDD where applicable.
`/automattic:review`, `/automattic:walkthrough` and `/automattic:dispatch` retain
`disable-model-invocation: true`. Manual review forwards its target and flags;
walkthrough hands off when requested, and dispatch runs the same procedure after
implementation, without a `Skill(automattic:review)` call. Explicit implementation-only
requests skip review; otherwise dispatch defaults to read-only assessment.
`/automattic:dispatch <scope> --autofix` includes the same repair/verification loop. This entry-point
restriction is a workflow convention, not a native caller-specific permission.
The report tracks coverage rather than a fixed number of findings.
[pipeline](skills/pipeline/SKILL.md) maps the workflow; autofix review owns E2E
execution and device reservation. It reconciles existing evidence, runs missing
applicable checks, and feeds failures back through the same scoped repair loop.
Operator-only work outside the accepted scope stays excluded. Genuine missing
access, unresolved decisions and exhausted repairs remain explicit blockers.
PR consumes the completed evidence; it does not start testing. The selected board's delivery gate
requires matching review/E2E evidence (`--delivery` for local tickets only), so implementation alone cannot certify
release readiness. PR targets require authenticated `gh`; branch review with an
explicit base works offline. The target helper never fetches or checks out code.

## Permission boundary

Automattic registers SessionStart to load the bootstrap and the active host's session part. In Claude it also
registers two PreToolUse checks: Agent calls name a model, use a current worker
profile and carry the `job_file` and inputs of a job of that agent (`hooks/agent_model.py`), and `gh pr create|edit` publishes only a linted
`--body-file` (`hooks/pr_body.py`), plus a Stop check that keeps the session working
while a lifecycle worker could finish unseen (`hooks/yield_gate.py`; Pi's extension
and Codex's Stop hook apply the same gate). It has no Git command blocklist. The orchestrator performs authorized pushes and branch/worktree
cleanup directly; workers retain their agent's permissions and native
permissions still apply. Actual permission denials are respected.

Run `/reload-plugins` in an existing Claude session to
refresh the hook inventory and skill instructions. No reinstall is needed for the
development symlink.

## Verification

`scripts/test-all.sh` runs every `tests/test_*.py` file in parallel (about 15 s)
with the plugin environment's `.venv` and exits 1 on any failure. Enable the hooks once
per clone with `git config core.hooksPath .githooks`:
- `pre-commit` (about a second) runs the
  [doc checker](.agents/skills/writing-agent-docs/SKILL.md) on changed files and
  checks the syntax of staged Python and shell files. The doc check reads files as they
  are on disk, so unstaged edits and untracked docs count, not only what is staged.
- `pre-push` checks out each pushed commit into a temporary worktree and runs the
  whole-repo doc check and this suite there, so the result is the pushed code's.
  Commits the remote already has are not rerun; an older commit without the checker
  or suite is pushed with a warning. The checks run in a session of their own, without
  a terminal: Ctrl-C or any signal to the hook reaches them once, as the same signal,
  followed by TERM after 2 s and KILL after 5 s, and the temporary worktree is
  removed. Not covered: a check that starts its own session (`setsid`), and `kill -9`
  of the hook, which leaves the checks running; the next push removes their worktree
  once they have finished.

`--no-verify` skips either hook. Tests are `unittest` cases, so
one file, class or test runs on its own. The default suite needs an installed `claude`
for `test_claude_effort.py`, which runs it against a local fake API; the package and
profile readers of the installed CLIs are opt-in:

```sh
.venv/bin/python -B tests/test_router_profiles.py
.venv/bin/python -B -m unittest discover -s tests -t tests
# Installed CLI discovery, OpenCode 2 and Claude profile readers; no model calls:
AUTOMATTIC_NATIVE=1 .venv/bin/python -B tests/test_cross_harness.py
AUTOMATTIC_NATIVE=1 .venv/bin/python -B tests/test_agent_models.py
# Pi SDK discovery and bootstrap, isolated from user extensions; no model calls:
AUTOMATTIC_NATIVE_PI=1 .venv/bin/python -B tests/test_cross_harness.py
```

`tests/support.py` locates and loads the scripts and builds an environment whose
Automattic state, configuration and Codex home are temporary; use it for a new test
that runs a script which writes machine state.

The regression check uses temporary Git repositories, files and locks. It covers
scoping, cross-effort locking/capacity, unknown arguments, mutation boundaries,
cycles, prerequisite branch ancestry, evidence acceptance, malformed input, both
hook registrations, shared file links, and build-lock exclusion/release/exit status.

Use the [review behavior rehearsal](docs/review-rehearsal.md) to check walkthrough
discussion, review handoff and finding adjudication separately from package registration.
Use the [dispatch recovery rehearsal](docs/dispatch-rehearsal.md) to check executor
completion, failed waits, state reconciliation and automatic review continuation.

Native package checks validate discovery, invocation metadata and registration.
When this source is installed in Claude, the native check also verifies that the installed
development plugin is enabled and has no loading errors, including missing dependencies.
Pi's isolated SDK check also exercises bootstrap startup/reload. These checks do
not launch workers or establish that native hooks are trusted in a live session.
Use native readers for shared skill metadata: the generic skill-creator validator
does not accept the Claude-specific frontmatter supported by this package.

**Still requires a live installed session in each harness:** worker spawning and
context loading, review/fix/E2E, and interruption/resume. These are not claimed as
passing. The dispatch preflight checks adapter, tool and worktree assignments.

Runtime references:
[OpenAI plugin packaging](https://developers.openai.com/plugins/build/plugins),
[Codex hooks](https://learn.chatgpt.com/docs/hooks),
[Codex subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents),
[Claude plugin reference](https://code.claude.com/docs/en/plugins-reference), and
[Claude hooks](https://code.claude.com/docs/en/hooks).
