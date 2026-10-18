---
name: brief
description: "Brief the user on current progress, remaining work, verification and decisions for the active task or a named effort, branch or PR."
disable-model-invocation: true
argument-hint: "[effort|branch|PR-number|PR-URL] [focus or question] — defaults to the active task"
---

# brief

First read [runtime bootstrap](../../bootstrap.md) and the host session part.
This is a manually requested, read-only briefing, not another workflow phase.
Use the active task and its accepted scope unless the user names a different
target. No Automattic board or report is required. If target identity is ambiguous,
state what can be established and ask only for the missing selection.

## Establish the current snapshot

Read the accepted goal, latest user direction and relevant task state. Refresh
only the evidence needed for this briefing: scoped board/tracker entries, Git
branch/head and working changes, existing implementation/review/E2E reports, and
the assigned workers' current state through the active runtime's read-only tools.
Use canonical tracker records rather than inventing a local mirror. Worktree-local
changes and reports may be newer than the main checkout; check their identity.

Use the current conversation for intent and decisions, not as proof that a worker
finished or a check passed. Compare report revisions with the target. Label stale,
unavailable or conflicting evidence and give its last known time/revision when
available. A completed command, idle worker or old green report alone does not
establish completed work. Do not wait for workers to finish just to give a briefing.

## Brief the human

Lead with the goal and the most consequential current fact in plain language.
Then give the smallest useful view of:

- What is complete, with its meaningful result.
- What is running now, what comes next and what remains outside this batch.
- Review and verification status, separating passed checks from gaps or failures.
- Blockers and decisions that actually need the user, with a recommendation and
  consequence. Say when no user decision is needed.

Use the project's domain language. Explain mechanisms or tradeoffs only when they
help the user steer. A small status table or flow can connect completed/current/next
work; skip it when a sentence is clearer. Link the few artifacts that support the
important claims. Give counts only for a verified scope; no invented percentages,
ETAs or adoption claims. Separate local implementation, integration, verification
and publication. Keep unrelated follow-ups separate from current blockers.

If a previous briefing is available, emphasize the meaningful changes since it;
still make this briefing understandable on its own. Otherwise report current state
without inventing a baseline. Match an explicitly requested depth or focus.

## Show-me presentation

Read the bundled [show-me presentation guidance](../../addons/show-me/presentation.md)
and use it to present this snapshot in the same response. Automattic owns the
facts and scope; the maintained show-me adaptation owns the visual vocabulary.
Select the smallest view that clarifies current state or dependencies; plain prose
is sufficient for a simple status. No second manual invocation is needed.

This shared reference is deliberately outside either skill's invocation boundary.
The standalone show-me command remains manual. Use the reference directly, not
an unavailable or forbidden Skill call. Default to in-chat presentation; exports
or file creation require the user's request. If the bundled file is unavailable,
report the packaging gap and still give the factual briefing without installing
anything or claiming presentation guidance was loaded.

## Preserve the workflow

A briefing does not launch workers, repair defects, run verification, update a
tracker, alter scheduling or close panes. Do not invoke dispatch, review, PR or
housekeeping as a side effect. Inspect existing worker state within the selected
executor's access boundaries; unavailable monitoring stays an explicit limitation.

Present the briefing in the conversation. Do not append it to README, project
instructions, skills or a recurring status document. Save/export only when asked,
following [housekeeping's history policy](../housekeeping/SKILL.md#keep-affected-documentation-current).
Existing authorized work retains its scope and ownership: after an in-flight
briefing, resume it unless the user pauses or redirects it. A standalone briefing
does not resurrect an inactive task.
