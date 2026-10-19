---
name: housekeeping
description: "Clean task-created residue and keep maintained documentation current, separating retained history into journals or changelogs when finishing work or preparing delivery."
argument-hint: "[task scope or paths to clean up]"
user-invocable: false
---

# Housekeeping

First read: this procedure only.

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
Apply [evidence retention](../../runtime/checks/run.md#retain-evidence) to deletion by
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

Follow [worktree retirement](../../runtime/resources/retire-worktree.md).

## Keep affected documentation current

Follow the [documentation standard](../../standards/documentation.md).

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
