---
name: models
description: "Inspect, configure or reset worker models, routes, pools, decision opt-ins/calibration, routers, profiles and thinking bounds, including session overrides."
disable-model-invocation: true
argument-hint: "[request|show|set|reset] [agent|router|decisions|profile|model-definition|runtime-definition|executor-definition] [--scope user|project|session] [--route] [--config-profile <name>] [runtime=claude|codex|pi|opencode] [--candidate <id>] [thinking=<label|JSON>]"
---

# models

Read [runtime bootstrap](../../bootstrap.md) and the host session part.
Handle the user's direct inspection, change or reset with the
[shared configuration procedure](../../harnesses/setup/procedure.md). It owns the
current shape, legacy command compatibility, scope precedence and validation.
No arguments means read-only inspection; a one-run choice is not a saved default.

For a guided explanation of the whole setup, offer
[setup-automattic](../setup-automattic/SKILL.md). A direct, fully specified change needs no walkthrough
or repeated approval. Apply existing authorization and report its effective result.
