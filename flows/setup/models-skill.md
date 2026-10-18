# Models skill

## Start with the models skill

For a guided explanation of the whole configuration and its scopes, use
setup-automattic. For direct inspection and edits, use models below.
Both entry points follow the same [configuration procedure](procedure.md).

Use `/automattic:models` in Claude Code, `$automattic:models` in Codex, or
`/skill:models` in Pi. These are chat invocations, not shell commands. No arguments
means inspect only. For example, using Claude's spelling:

```text
/automattic:models set reviewer --route executor=subagent mode=inherit
/automattic:models set reviewer --route thinking=high
/automattic:models show reviewer --route
/automattic:models reset reviewer --route thinking
```

The second command explicitly overrides thinking; the worker's model remains at
its native default. The last removes only that thinking override. Use an actual
supported `model=<id>` when you want to select a model too. Labels are validated
against the destination before launch, not assumed portable across runtimes.

You can describe the same changes in natural language after the command. Name the
agent, desired executor and any model/thinking choices. Available agents are
`builder`, `reviewer` and `verifier`. The skill
uses the current host and project by default and asks only for missing choices
that cannot be established from the request or current setup.

Add `--scope user` for personal defaults or `--scope session` for a temporary
override; otherwise changes are project-local.
Explicit configuration requests authorize preparation of the plugin's isolated
validator environment if needed. Showing settings never installs dependencies or
starts a worker. After a change, the skill reports the saved path, effective
executor/model policy and any runtime checks still pending. Use the next ordinary
`dispatch` or `review` invocation to execute work; saving config does not run it.
