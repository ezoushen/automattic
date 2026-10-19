# Automattic

One workflow for Claude Code, Codex and Pi: **align → refine → dispatch → review → PR**.
The plugin holds the procedures, agents, jobs and scripts; each effort's state lives in
the target repository under `.scratch/<slug>/`.

## Commands

Typed as `/automattic:<name>` in Claude Code, `$automattic:<name>` in Codex and
`/skill:<name>` in Pi. Each command's procedure is its `skills/<name>/SKILL.md`.

| Command | Does |
|---|---|
| `align` | Settle the goal and constraints, then a WHAT / WHY / HOW plan |
| `refine` | Split the plan into tickets on the project's tracker or local Markdown |
| `dispatch` | Implement the tickets, then review; `--autofix` adds repairs and E2E |
| `review` | Review a branch or PR; `review walkthrough <target>` explains it first |
| `pr` | Open the PR once review and verification evidence is current |
| `remediate` | Find, prove and repair tautological tests or misleading comments |
| `setup` | Explain or change worker, routing and decision settings |
| `brief` | Report progress; `brief map` shows which command fits |

The agent loads four more skills itself: code-comments, housekeeping, decision and
model-routing. Claude Code keeps them out of its command menu; Codex and Pi list them.

## Concepts

- **Mandate and ledger.** The user owns the goal, principles, constraints and any
  decision they reserve. Inside that mandate the agent investigates facts and makes
  reversible choices itself, asking only about material forks. Consequential
  decisions go in `.scratch/<slug>/ledger.md` with their hinge, so the user can veto
  them without approving each one. `align` writes the plan to `alignment.md`.
- **Tickets on the project's tracker.** The configured tracker (Linear, GitHub, …) is
  the authority for work items; local Markdown under `.scratch/<slug>/issues/` is the
  fallback. Existing project conventions take precedence.
- **One orchestrator, three agents.** The orchestrator owns scheduling, worktrees,
  integration and board updates. Each assignment goes to one worker, which gets an
  agent file (builder, reviewer or verifier: permissions and principles) and a job file
  (inputs, finish line, return). Workers do not create nested teams.
- **Evidence, not claims.** Reports in `.scratch/<slug>/reports/` hold check output and
  decisions. Review reconciles that evidence; `--autofix` repairs in-scope findings
  and runs applicable E2E. `pr` only publishes once review and E2E evidence is current.
- **Layered review.** Direction (WHY / WHAT / HOW), then scope, then implementation;
  an unresolved upstream decision pauses only the review that depends on it. Comments
  stay local drafts unless `--comments confirm` or `post` is given. Code comments and
  API docs are contracts, so their correctness is a hard gate, and every added test
  is checked for being [tautological](standards/kinds/tautological-tests.md).
- **Workers and routing.** No configuration is needed. `setup` chooses each agent's
  executor (native sub-agent, a skill such as Herdr, or a Bash program), model,
  thinking level, pools and routers; see [configuring workers](docs/configuration.md).
- **Hooks.** SessionStart loads `bootstrap.md` and the host's session part. In Claude,
  PreToolUse checks require each Agent call to name a model and carry its job's inputs
  (`hooks/agent_model.py`) and let `gh pr create|edit` publish only a linted body
  (`hooks/pr_body.py`); a Stop check keeps the session alive while a worker could
  finish unseen (`hooks/yield_gate.py`; Pi and Codex apply the same gate). There is
  no Git command blocklist; native permissions apply.

## Layout

| Path | Owns |
|---|---|
| `skills/<command>/` | One folder per skill: a command's procedure in `SKILL.md`, its other docs and its job files (`jobs/`). The decision, routing and writing skills are thin entries over a `runtime/` or `standards/` doc |
| `bootstrap.md` | Session rules every host reads first, with the triggers table for rules that fire outside their owner |
| `flows/interview/`, `flows/board/` | Shared procedures no command owns: authority, the question filter and the ledger record; board operations and tracker conventions |
| `agents/` | The builder, reviewer and verifier agents; Claude loads them natively |
| `standards/` | What good looks like: PR descriptions, code comments, documentation and the remediation kinds |
| `hosts/claude/`, `hosts/codex/`, `hosts/pi/`, `hosts/opencode/` | Each host's session part and worker part; OpenCode covers model settings only |
| `hosts/herdr.md`, `hosts/executors/` | Herdr guidance; Bash, sub-agent and skill executors |
| `runtime/workers/`, `checks/`, `routing/`, `resources/`, `decisions/`, `config/` | Shared runtime rules, each file small enough for one read; `config/` holds the configuration format |
| `scripts/`, `hooks/`, `schemas/` | Scheduler, resolution, checks and hooks; configuration and decision contracts |
| `addons/show-me/`, `benchmarks/` | Shared presentation reference; synthetic decision calibration examples |

## Architecture

The Markdown is layered so a reader follows links in one direction. Hooks and the commands
(`skills/<command>/`: brief; dispatch and remediate; pr; review; housekeeping; align, refine
and setup) sit on top; below them come `bootstrap.md`, the shared `flows/` (interview; board),
`agents/`, `standards/`, `hosts/` and the `runtime/` modules
(workers, checks, routing, resources, decisions, config). A doc links only its own module
or a lower one, so a command may read a lower command's procedure but never a sibling's
or a higher one's, and no two modules depend on each other. A doc path named in prose or
code counts as a dependency, and `scripts/` and `hooks/` import under the same order.
`.agents/skills/writing-agent-docs/architecture.json` records the order; the doc checker
enforces it on every commit and push, and in Claude Code after every edit. To add a host,
executor, agent, job, kind, standard, flow or command, follow
[extend the architecture](.agents/skills/writing-agent-docs/SKILL.md#extend-the-architecture).

## Install and develop

- [Installation](docs/installation.md): requirements and the Claude, Codex and Pi setups.
- [Configuring workers](docs/configuration.md): executors, models, pools, routers and decisions.
- [Development](docs/development.md): the suite, Git hooks, native checks, rehearsals and usage tools.
