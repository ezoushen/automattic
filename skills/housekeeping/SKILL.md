---
name: housekeeping
description: "Clean task-created residue and keep maintained documentation current, separating retained history into journals or changelogs when finishing work or preparing delivery."
argument-hint: "[task scope or paths to clean up]"
---

# Housekeeping

Leave the assigned project ready for handoff: remove disposable task residue,
update documentation affected by the change, and retain useful evidence. Work
within the current task's checkout and scope; no Automattic board is required.
Use existing authorization for routine cleanup and documentation updates.
A read-only assignment stays read-only: report candidates instead of editing.

## Establish what belongs to this task

Inspect the working tree, task diff and recorded commands/output paths. Distinguish
task-created intermediates from deliverables, required evidence and pre-existing
or other workers' files. Being untracked, ignored or inside a directory named
`tmp`, `build` or `.scratch` does not establish ownership or disposability.
If ownership or retention is uncertain, leave the item and report the uncertainty;
continue independent cleanup. Respect active worktree ownership and running jobs.
Before restoring experiment edits or removing outputs, verify all owned jobs using
them have stopped, including queued commands and descendants. Uncertain teardown
keeps those files/resources reserved; report the gap.

## Remove disposable residue

Remove identified task-created temporary scripts, scratch exports, experimental
edits and disposable test outputs once they are no longer needed. Retain regression
tests, fixtures, intentional generated deliverables and project-required outputs.
Preserve reports and the logs/screenshots they cite, unresolved failure evidence,
follow-ups and interruption/resume state. `.scratch/` is often working evidence,
not a directory to empty. Remove experimental edits surgically without restoring
over someone else's changes.
Apply [evidence retention](../../harnesses/checks.md#retain-evidence) to deletion by
size/type and outside worktrees too; verify proof and downstream references before
removing recordings or traces. Derived summaries may have narrower audit value.

Delete exact verified paths. Inspect directory contents and symlink destinations
before removal; do not follow a link and delete an external target. Use a project's
cleanup command only when its targets match this scope. Do not use blanket Git
clean/reset, erase shared caches, or change ignore rules merely to hide residue.
Branch/worktree retirement remains with the existing lifecycle owner; in
Automattic, dispatch and PR own it. This skill does not grant publication or
branch deletion permission or override native tool restrictions.

## Retire a worktree

The lifecycle owner first confirms that review/repair and applicable E2E are
complete or explicitly excluded, and no assignment, queued command or owned job
still needs the checkout. Integration and a clean Git status are insufficient:
ignored build directories can contain the only acceptance evidence.

Follow [evidence retention](../../harnesses/checks.md#retain-evidence) before removal.
Verify the retained copies and report links from outside the retiring checkout.
Missing evidence or uncertain ownership keeps it available for recovery. Use the
host's managed worktree retirement tool when provided; otherwise remove the exact
verified checkout without force. Before removing, check
`git -C <checkout> status --porcelain --ignored`. Never gate retirement on
`--untracked-files=no`. If plain `git worktree remove` refuses, the refusal is the
signal: inspect what is left and retain or delete it explicitly. Never add
`--force`. Preserve branches required by downstream work.

## Keep affected documentation current

Read the project's documentation conventions and update existing README, usage,
configuration or developer instructions when this task changes their claims. Treat
README, AGENTS.md, CLAUDE.md, skills and their maintained references as the current
contract. Rewrite the affected section in place: replace superseded instructions,
remove obsolete claims and keep supported behavior, active constraints and durable
rationale. A dated correction appended below stale guidance does not update it.
Historical behavior needed for supported compatibility or migration belongs only
where it helps a current user act; identify its applicable version or condition.

Keep session narratives, progress notes, before/after snapshots and change histories
out of maintained guidance, including skill bodies and references. Preserve useful
history in the project's existing journal/log convention, or `journals/` when none
exists. Use the established changelog for release history and Git commit messages
for change rationale and ticket/ADR references. Create a journal only when there is
history worth retaining; do not require one per task or duplicate existing reports.
When moving a useful snapshot, preserve its date, context and evidence, label it
historical, and update links. Do not leave a second copy in the maintained document.
Discard obsolete prose with no retention value; Git already preserves edits.

Required review reports, evidence logs, ledgers and tracker history keep their
established paths and append/resume contracts. They are historical records, not
maintained guidance; archiving them must not break active gates or evidence links.
Keep incidental test counts and run timings in verification reports; standing
instructions should name the required checks and outcomes. Preserve explicit
performance budgets and other contractual numbers. Do not rerun an unchanged
suite merely to refresh an incidental figure when valid evidence already exists.

For source comments and API docs, use [code-comments](../code-comments/SKILL.md)
as the writing standard. Verify examples and commands against the change. An
unclear behavior contract needs a decision, not prose that guesses or excuses a
bug. Unrelated documentation improvements stay in existing follow-ups (or the
handoff when no follow-up record exists), without expanding this task.

## Verify and hand off

Recheck the diff and working-tree status; confirm removed paths are gone and
retained evidence links still resolve. Read each affected maintained section as a
new user: it must give one current answer without requiring the reader to reconcile
old and new entries. Run existing checks affected by documentation
or tracked-file edits; reuse valid passing results for unchanged code/environment.
A clean handoff may retain intentional uncommitted work and required ignored
artifacts; an empty Git status is not the goal.

Prefer housekeeping before review so documentation changes are reviewed with the
implementation. If housekeeping changes tracked content after review, hand the
delta back to the existing review/delivery workflow; do not claim evidence for an
older head certifies the new one. Housekeeping does not certify the documentation
gate or start a second review loop.

Briefly report what was removed, documentation updated, evidence retained and
anything left with a reason. Use the existing task report or final response;
no new artifact or repeated pass is needed when nothing relevant has changed.
