# Codex adapter

Use the shared skills and roles. Resolve a dependency from the active skill catalog
and read it when its step applies; slash notation identifies a skill, not a shell
command. Preserve the existing explicit invocation policy in `agents/openai.yaml`.

For planning phases, this adapter is sufficient. Before dispatch, starting/resuming
a worker, or acting as one, also read [dispatch.md](dispatch.md). Load only the
assigned role and its task inputs; do not preload every phase, role or dependency.

Apply shared instructions within the active runtime's instruction hierarchy.
Carry forward the user's existing decisions and authorization across phases;
do not require another reply just to acknowledge an already approved decision.
Unresolved product choices and actual permission boundaries still need the user.
Project-required compile, suite and E2E gates remain mandatory; record the checked
commit or [verified input snapshot](../checks.md#identify-executed-inputs). Reuse
passing evidence only while the relevant code and environment are unchanged, and
tie delivery evidence to the final reviewed commit. Broaden verification for
changed code, failures or concrete gaps.

Model and thinking choices come from [executor resolution](../executors.md);
the dispatch adapter only maps its returned settings to native controls.
Omitted settings retain native defaults. This plugin does not
set API pricing, caching, service tiers or account limits.

Automattic does not block Git commands. The orchestrator can perform authorized
publication and cleanup directly; workers retain their assigned role boundaries.
Follow native permissions, and never route around a denial or treat Claude
profile tool lists as Codex restrictions.
