---
name: setup-automattic
description: "Walk through the current Automattic setup and help change user, project or session configuration."
disable-model-invocation: true
argument-hint: "[question or desired change] [--scope user|project|session]"
---

# Set up Automattic

First read: [runtime bootstrap](../../bootstrap.md), the host session part, [procedure](../../flows/setup/procedure.md).
Help the user understand the effective setup and adjust it for their work. With
no request to change settings, stay read-only. A scope flag focuses the discussion;
it does not itself authorize edits. No board, new session or configuration file is
required to have this conversation.

Use the [shared configuration procedure](../../flows/setup/procedure.md) for
inspection and any requested changes. Read only the relevant referenced branches.
It is the same procedure used by models; do not invoke the explicit-only models
skill or require the user to type a second command. This adds a guided entry point,
not a new configuration format or a second resolver.

## Explain the actual setup

Establish the active host, canonical project, root session identity if available,
and applicable configuration sources. Inspect with the existing resolver and
offline decision status. Show configured values and where they came from; label
missing runtime evidence rather than starting workers or probing decision services.
Use existing project instructions for tracker and verification conventions. Those
remain project conventions, not new fields in executors.json. Installation and
provider/account settings remain with their own tools; explain any gap without
installing or reconfiguring them merely to complete this tour.

Begin with a compact picture of what is active and why. Explain responsibilities
before field names, using one representative agent from the actual configuration:

- **Available workers:** model definitions bind registered IDs and thinking limits
  to worker runtimes; each agent's pool controls which it may use.
- **How a worker runs:** runtime routes choose a native child, skill bridge or Bash
  executor for the caller. Named executor types reuse skill instructions.
- **Who chooses:** the router uses host judgment through a skill, a sparse profile,
  or a decision backend. A profile applies only its specified agent/runtime fields;
  configured pins and bounds still apply.
- **Which workflow decisions are delegated:** enabled decision families and their
  calibration evidence. Worker selection and recovery are separate opt-ins; showing
  a backend or profile does not activate it.
- **How decisions are checked:** the [decision journal](../../runtime/decisions/journal.md)
  links recommendations, host choices, observed worker settings and outcomes. Explain
  missing evidence and calibration warnings; inspection does not run a replay.

Tailor this map to the request. An unconfigured project can use native defaults;
do not fill every field or recommend every optional feature. Distinguish a possible
route from a selected assignment and requested settings from runtime-confirmed ones.
Use [show-me presentation guidance](../../addons/show-me/presentation.md) directly
when a small diagram or before/after view helps; no extra show-me invocation.
Keep the explanation in chat before asking for a decision.

## Discuss one useful topic at a time

Follow the user's question rather than a questionnaire over every field. Recommend
the next useful topic with its tradeoff, leave room for questions, and apply the
[question filter](../../flows/planning/question-filter.md) to material unresolved choices.
Discover facts from configuration and installed contracts yourself. Reuse stated
preferences; a fully specified change can proceed without a mandatory tour.

Explain scope before saving a change:

| Scope | Applies to | Save location |
| --- | --- | --- |
| User | Personal defaults across projects | `~/.config/automattic/executors.json` |
| Project | Overrides for this canonical project | `<repo>/.automattic/executors.json` |
| Session | This root session and its resumes in this project | Resolver-managed session record |

Show precedence from native defaults through user, project and session to explicit
assignment choices. A one-assignment choice is not another persistent scope. Explain
which objects replace rather than merge only when relevant to the proposed edit.
Project is the default for an unspecified durable change. A request for a temporary
or session-only change uses session scope; do not persist it as a project default.

When something is shadowed, show both the saved value at the requested scope and
what currently wins. Removing an override reveals the lower layer; it is not always
the same as disabling a feature or inheriting native settings. Explain that result
before proposing a reset. Resolve genuine ambiguity without adding an approval
round for an already explicit scoped request.

## Apply and explain the result

For an authorized change, use the shared procedure in this conversation: preserve
unrelated values, validate the candidate and affected references, save at the
requested scope, and inspect the resulting effective settings. Show a focused diff
and the behavioral consequence, including any higher layer that still masks it.
Settings apply to new assignments; existing workers keep their resolved choices.
Calibration runs and live worker probes are separate requests, not setup checks.

Finish an explanation when the user's question is answered; no configuration change
is required. Finish an edit with the saved path/scope, effective result and any
remaining runtime check. If the user wants to begin work afterward, point to the
appropriate phase in the pipeline map (`/automattic:pipeline`) and carry existing
authorization forward. A setup tour alone does not launch a workflow.
