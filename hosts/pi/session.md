# Pi adapter

The bootstrap extension supplies this adapter's absolute path. Pi discovers the
shared skills recursively through the development symlink; invoke explicit phases
with `/skill:dispatch`, `/skill:review`, etc. Preserve `disable-model-invocation`.
Resolve Matt's dependencies from Pi's active skill catalog and read their files
when needed. Claude profiles and Codex metadata do not register Pi workers.

The extension also guards against loops: a tool call that returned the same result
three times in a row is blocked when repeated, with a reason telling the agent to
change approach or report that it is blocked, and a second blocked repeat stops the
turn. Calls whose output changes, such as polling, are not affected.
`AUTOMATTIC_LOOP_GUARD=off` disables it.

Before delegating, resuming or acting as a worker, also read [workers.md](workers.md). In worker
messages, `adapter` is this file's absolute path.
