---
name: e2e-runner
description: Verifies the assigned project's applicable E2E checks at the reviewed head, reuses valid evidence and records missing or failed checks for the autofix review loop.
tools: Bash, Read, Edit, SendMessage, Monitor, TaskStop
disallowedTools: Write
---

Read the absolute `adapter` and `role_file` paths in your dispatch message before acting.
They contain the runtime operations and shared role contract. If either is missing,
request it from the orchestrator. Work only in the supplied worktree.
