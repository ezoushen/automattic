---
name: autopilot
description: "Run the whole loop hands-off: settle the goal in one interview, confirm a run card with its stop condition, then refine, dispatch with autofix, review and open the PR without asking again."
disable-model-invocation: true
argument-hint: "<goal> | --take-over [--auto-merge]"
---

# autopilot

Contents:
- [Start](#start)
- [Run](#run)
- [Decide without asking](#decide-without-asking)
- [Stop](#stop)

First read: the runtime bootstrap (`../../bootstrap.md`), the host session part, [engineering judgment](../../standards/engineering.md).

Autopilot asks its questions in align only. Once the user confirms the run card, it
runs refine, dispatch with autofix, review and the PR alone, and ends in exactly one
terminal state, with its evidence. It starts only when the user types it; a message
that mentions it is not an invocation. It never widens native permissions.

## Start

- **`autopilot <goal>`:** run [align](../align/SKILL.md) on the goal, with its interview,
  ledger and alignment brief. The interview settles everything later phases would
  otherwise ask: goal, principles, acceptance criteria and their Verify lines, and
  anything reserved to the user.
- **`autopilot --take-over`:** start from the session's current state. It reuses accepted decisions, tickets and reports,
  and asks only the align questions still unsettled; a phase already finished is not redone.
- **`--auto-merge`:** with either form, also grants merging once the PR is open; see [Stop](#stop).

Then autopilot writes the [run card](run-card.md) to `.scratch/<slug>/autopilot.md` and asks the user to confirm it once.
Each acceptance criterion on the card has a Verify line that can tell success from
failure. No phase after align starts before that confirmation, and an unrelated reply
or silence is not one. The confirmed card is the user's explicit request for every
action it grants.

## Run

After confirmation, ask the user nothing. Re-read the card and the ledger before each
phase, and after every compaction or resume. Run each phase by its own procedure:

1. [refine](../refine/SKILL.md) the brief into tickets;
2. [dispatch](../dispatch/SKILL.md) them with `--autofix`, which includes review, repairs
   and applicable E2E;
3. [pr](../pr/SKILL.md): write the description, push the effort branch and open the PR,
   then watch the required checks.

Check the allowance at each phase boundary and before each worker launch with
`python3 "<plugin_root>/scripts/allowance.py" status`. When Claude or Codex is
`critical`, finish the step in progress, commit passing work and end `paused-allowance`.
Update the card's State section as each phase ends, with the commit and report it reached.

## Decide without asking

A question that would go to the user after confirmation is decided instead. Look the
facts up, apply the ledger's principles and [engineering judgment](../../standards/engineering.md),
prefer the reversible direction, and record its basis and reversibility in the ledger.
Continue with the decision. When no option fits the user's principles and the
acceptance criteria, the run ends `blocked`. A blocker that survives the escalation
rules' second attempt also ends `blocked`. The final report leads with the open assumptions.

The pause list is never decided: a login or permission prompt, credentials, spending
money, deleting data, a production change, merging without `--auto-merge`, or a
missing approval. Reaching one ends `waiting-on-user` instead of deciding it. Leave the native prompt pending, record
what is needed and the command that resumes the run (`autopilot --take-over`).

## Stop

Record exactly one terminal state, with its evidence, in the card's State section:

- `delivered`: the PR is open, its required checks pass, and review and E2E evidence is
  current for its head. Never record `delivered` while any acceptance criterion lacks passing evidence.
- `delivered-local`: the same, in a repository with no PR host: the effort branch and
  its delivery report are ready.
- `merged`: only with `--auto-merge`. It merges only through the repository's normal path, once required checks
  and the [approval path](../../runtime/board/approval-path.md) are satisfied, never by admin override or self-approval.
- `waiting-on-user`: a pause-list action is needed.
- `paused-allowance`: the allowance reached `critical`.
- `blocked`: no option fits the principles, or a blocker outlived its retries.

Then report in the conversation: the terminal state, the open assumptions first, the PR
or branch, the decisive evidence and what the user must do next, if anything.
