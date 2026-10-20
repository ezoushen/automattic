# Tracker and project conventions

Read before choosing a tracker, board or destination, and before updating one.

## Project conventions

Follow current user direction, then the project's established workflow. Read its
`AGENTS.md`/`CLAUDE.md` and relevant project docs, including any tracker doc
they name.
Use the configured tracker and destination (for example Linear team/project or
GitHub repository/project), issue templates, labels, priority rules and status
transitions. No fixed list of trackers limits the choice. A Git remote or
an available connector alone does not establish a project-management convention.
Ask only when a material destination or convention remains ambiguous; with no
configured tracker, use local Markdown without requiring setup or migration.

The configured tracker is authoritative for work items. Read existing issues
before creating any, reuse their IDs/URLs, and carry accepted scope/priorities
forward. Use the project's available CLI/connector and existing authorization;
configuration alone does not authorize publishing drafts or contacting others.
An unavailable tracker is a reported blocker for dependent operations, not a
reason to silently create a competing local backlog or switch providers.

Dispatch reads and updates the configured board directly using its
[board operations](board.md). Remote trackers do not require
local issue files or a mirrored backlog. Local ticket files and their Python
scheduler apply only to the local Markdown choice. The orchestrator owns tracker
updates as authorized by the task and project convention; workers report evidence
to it. Implementation integrated does not imply remote closure: the project may
require review, merge or release before closure.
Reconcile human edits at phase boundaries instead of overwriting them. Keep
unpublished review follow-ups local until their publication is authorized.
