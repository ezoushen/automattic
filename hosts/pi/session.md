# Pi adapter

The bootstrap extension supplies this adapter's absolute path. Pi discovers the
shared skills recursively through the development symlink; invoke explicit phases
with `/skill:dispatch`, `/skill:review`, etc. Preserve `disable-model-invocation`.
Claude profiles and Codex metadata do not register Pi workers.

The extension also guards against loops: a tool call that returned the same result
three times in a row is blocked when repeated, with a reason telling the agent to
change approach or report that it is blocked, and a second blocked repeat stops the
turn. Calls whose output changes, such as polling, are not affected.
`AUTOMATTIC_LOOP_GUARD=off` disables it.

Pi's `bash` has no default timeout, so the extension gives a call that sets none a
120 s timeout, as Claude Code and OpenCode do natively; Codex returns from a long
command after a few seconds and leaves it running in a session. An explicit `timeout`
is kept, and background tools such as `bg_run` are not bounded.

Before delegating, resuming or acting as a worker, also read [workers.md](workers.md). In worker
messages, `adapter` is this file's absolute path.
