# Keep affected documentation current

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

For source comments and API docs, use [code-comments](code-comments.md)
as the writing standard. Verify examples and commands against the change. An
unclear behavior contract needs a decision, not prose that guesses or excuses a
bug. Unrelated documentation improvements stay in existing follow-ups (or the
handoff when no follow-up record exists), without expanding this task.
