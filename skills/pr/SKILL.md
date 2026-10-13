---
name: pr
description: "Create a PR for an effort with current review and verification evidence."
disable-model-invocation: true
argument-hint: "<effort-slug> — review and applicable verification must already pass"
---

# pr

First read [runtime bootstrap](../../harnesses/README.md) and the selected adapter.

The optional last phase of the pipeline. Everything the description needs already
exists in the effort's artifacts and configured board: the mandate and design in
`alignment.md`, decisions in `ledger.md`, stories in canonical tracker issues or
local Markdown tickets, and evidence in `reports/`. The PR description is assembled from them,
never written from memory. Every claim traces to the artefact that proves it: cite
that artefact in the report or ledger, and inline the figure in the PR body.

## Repository approval path

Read the project's current branch requirements, PR author identity and established
approval convention before publication. Record the requirements and known path
in the existing delivery report: an eligible independent reviewer, an already configured bot/App
author, or existing explicit user authorization for an administrative merge when
the repository permits it. An author cannot satisfy their own independent-review
requirement. Do not invent a bot, change branch rules or treat an impossible
self-review as live work that more waiting will resolve.

PR publication does not authorize merging. Carry forward a user's already explicit
merge/admin-merge authorization when applicable, without asking again; it never
waives required verification. Without an authorized path, name the exact approval
blocker for merging and its resume event. Pending approval does not block authorized
PR creation. Continue independent authorized work instead of polling an unchanged
requirement. Recheck the path if author or branch rules change.

## Steps

Before checking delivery evidence, apply [housekeeping](../housekeeping/SKILL.md)
to the effort worktree if it has not covered the current task state. If it changes
tracked content, return that delta to review and refresh required delivery evidence
before proceeding. Preserve artifacts used by the PR's claims.

1. **Confirm delivery evidence**, from the main checkout, using the selected
   [board's delivery gate](../dispatch/board.md). Remote issues are checked
   directly alongside Git and reports; no local ticket mirror or scheduler call.
   For local Markdown only, run
   `python3 "<plugin_root>/scripts/next-tickets.py" --repo "<repo>" <slug> --delivery`.
   Require implemented/integrated work and a clean review plus passed E2E for the
   current effort head and pinned base. Read coverage, decisions and artifacts too;
   structural markers alone are not proof. Follow-ups are separate future work, not PR
   blockers or implied permission to implement them. Missing/stale evidence means
   return to the corresponding phase, never call an implemented branch delivered.
   Run the configured [`delivery` checkpoint](../../harnesses/decisions.md#configured-checkpoint-command)
   for follow-up attention after checking the evidence, or record an evidenced skip
   when no discretionary choice remains. Check this phase record at delivery.
   Required gates and publication permission are facts the backend cannot waive.
2. **Read the whole range**, not the last commit: `git log --oneline main..feat/<slug>`
   and `git diff main...feat/<slug>`. Use the accepted brief to explain intent and
   the final diff to explain resulting behavior. Reuse the current review report;
   preparing the description does not start another review or testing loop.
3. **Write the description** following [writing.md](writing.md) into
   `.scratch/<slug>/pr.md`, run its self-check, and present it as a brief. Carry forward existing
   description/publication approval; obtain only a still-required decision.
   An unrelated reply or silence is not approval.
4. **Push and open.** Record the approval path above. When publication is authorized, run
   `git push -u origin feat/<slug>` directly. Verify the remote branch matches the
   reviewed local tip, then run
   `gh pr create --base main --head feat/<slug> --title "<type>: <goal in one line>" --body-file .scratch/<slug>/pr.md`.
   The type follows the repo's commit format (`feat`, `fix`, `refactor`, …), chosen
   from the accepted goal. When that format uses `!`, add it for a breaking change
   established by the accepted compatibility obligations and final diff. Report the URL.
5. **Watch the required checks** for the pushed SHA. Confirm the PR head equals that
   SHA, then run `gh pr checks <n> --required --watch` as a background job. When the
   repository reports no required checks, the watch returns at once: watch every
   check with `gh pr checks <n> --watch` instead, and treat each as required. A
   failing required check is not "delivered". Read the failed job's log and return through `recovery` to
   `review --autofix`. The repair reproduces the full failing CI job locally before
   pushing, and the watch restarts on the new SHA. Report "ready to merge" only when
   every required check is green and the approval path is known. The same watch
   follows every later push to the PR branch.
6. **After the merge, on request:** apply the
   [worktree retirement checks](../housekeeping/SKILL.md#retire-a-worktree), then
   delete `feat/<slug>` and its recorded ticket branches only after downstream
   dependencies no longer need them. Retain useful timing/retrospective evidence
   in the existing reports or journals.

## Description

[writing.md](writing.md) owns the description: structure, title, numbers, what
to leave out, diagrams, length, refreshing an existing PR, and the self-check.
It also applies to every later edit of the PR, whether or not this skill was
invoked. Supply it the accepted brief or issue, the final change range, current
verification evidence, material decisions and known limitations. Numbers come
from recorded command output, not recollection. Reports in gitignored `.scratch/`
are local evidence, not reviewer links. Publish artifacts only with authorization.
