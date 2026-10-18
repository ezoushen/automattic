# Claude Code adapter

Registration: `.claude-plugin/plugin.json`, native `agents/*.md` profiles, and
`hooks/hooks.json`. SessionStart selects this adapter explicitly. Invoke phase
skills with `/automattic:<phase>`; use the Skill tool for available dependencies.
Confirm required dependency skills are installed before dispatch.

Read shared docs with the Read tool, not `cat`, `sed` or `head`: Bash output over
about 30 KB is saved to a file instead of shown, and a guessed line range can cut
a section short. Each shared doc under `harnesses/` fits one read.

Automattic does not block Git commands. The orchestrator can perform authorized
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
