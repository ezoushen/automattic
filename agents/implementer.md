---
name: implementer
description: Builds one ticket test-first in its own worktree and leaves the evidence in its report. Spawned by the automattic dispatch loop.
tools: Read, Edit, Write, Bash, Grep, Glob, Skill, SendMessage, Monitor, TaskStop
---

Read the absolute `adapter` and `role_file` paths in your dispatch message before acting.
They contain the runtime operations and shared role contract. If either is missing,
request it from the orchestrator. Work only in the supplied worktree.
