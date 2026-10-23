# Claude Code adapter

Registration: `.claude-plugin/plugin.json`, native `agents/*.md` profiles, and
`hooks/hooks.json`. SessionStart selects this adapter explicitly. Invoke phase
skills with `/zloop:<phase>`.

Read shared docs with the Read tool, not `cat`, `sed` or `head`: Bash output over
about 30 KB is saved to a file instead of shown, and a guessed line range can cut
a section short. Each doc under `skills/`, `runtime/`, `standards/` and `hosts/` fits one read.

zloop does not block Git commands. The orchestrator can perform authorized
publication and cleanup directly; workers retain their agent's permissions.
Follow native permissions. On permission denial, report the actual boundary and
stop that action; do not route around it.
Carry the denied operation/resource into worker and resume assignments so another
path spelling, copy command or tool does not repeat it. Keep startup update/auth/
permission prompts pending for the user; a review assignment does not authorize
upgrades or disabling approvals/sandboxing to make a delegate run.

Before launching, resuming or acting as a worker, also read [workers.md](workers.md): it holds
launch, profile and effort handling, the Claude hooks, child slots and goals. In worker
messages, `adapter` is this file's absolute path.

## Resume timer

An autopilot allowance pause schedules its resume with `CronCreate` with `recurring: false` and prompt
`/zloop:autopilot --take-over`, the cron pinned to the reset's minute, hour, day and month in local time, a few
minutes after it and off :00 and :30. Record the job id and the next run time the result gives on the card. The job
is session-only and fires only while the session is idle: it ends with the session, so a Claude that exits before the
reset resumes only when the user types the command. Cancel a leftover job with `CronDelete`. The user's request for
the resume (the run card) is the explicit request for scheduled work that [workers.md](workers.md) asks for.
