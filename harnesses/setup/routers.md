# Routers, profiles and decisions

## Routers and sparse profiles

`agents.<role>.candidates` is the allowed pool, without a model default. The optional
`router` chooses the selection strategy. Omission uses the built-in skill:

```json
{
  "router": {
    "type": "skill",
    "skill": "automattic:model-routing"
  }
}
```

The [model-routing skill](../../skills/model-routing/SKILL.md) guides the host's judgment
within its existing context. Add `instruction` only for user-specific preferences.
An installed routing skill can call Jev or another decision model and return the
same selection contract. That is a selection interface, not a worker executor;
inspection never loads the skill, calls an API or installs a dependency.
For a service exposing System One directly, use the built-in
[decision-model router](../routing/decision-model.md).

A profile router applies sparse overrides after establishing the worker runtime:

```json
{
  "profiles": {
    "balanced": {
      "implementer": {
        "codex": {"candidate": "sol", "thinking": "medium"},
        "pi": {"candidate": "glm"}
      }
    }
  },
  "router": {"type": "profile", "profile": "balanced"}
}
```

`implementer.codex` means the worker runs in Codex, including a Claude caller that
launches it through a bridge. The host still determines which launch routes exist.
No `choices` wrapper is used. Missing candidate, thinking, role or runtime leaves
that part of selection unchanged; an empty profile is valid. Profiles do not alter
pools or executors. Candidate overrides must belong to the role pool and have a
binding for that worker runtime. Thinking must fit the final candidate's policy.
Use catalog pools for runtime profiles; a complete instance with an opaque external
executor has no inferred worker runtime. `--target-runtime` requires a catalog
reference or pool so the resolver can verify the requested binding.

Profile selection precedence is `--config-profile`, then `AUTOMATTIC_PROFILE`,
then the configured `router`. Host/Herdr names never automatically select profiles.
With several reachable worker runtimes, a profile alone does not choose the runtime.
Use `--target-runtime` or let an assignment recommendation establish it. Partial
profiles can therefore still need host judgment. An explicit user candidate pin
bypasses profile overrides; an explicit thinking pin wins over profile thinking.

## Decision backend

Use `executors.json` at user, project or session scope. The complete `decisions`
object replaces the lower scope. Copy the effective object before a partial edit.
Use a separate baseline path for a project/session override so calibrating that
scope does not replace the reference used by other configurations.
The worker `router` remains independent: a skill/profile router keeps its behavior
even if recovery uses the decision backend.

```json
{
  "router": {"type": "decision-model"},
  "decisions": {
    "backend": {
      "protocol": "systemone",
      "endpoint": "http://127.0.0.1:1241/v1/systemone",
      "model": "local/OpenJev-27B-Splash"
    },
    "enabled": ["worker-selection", "recovery"],
    "calibration": {
      "suite": "/absolute/path/to/decisions.json",
      "baseline": "/absolute/path/to/decisions-baseline.json",
      "check_every": 50,
      "max_accuracy_drop": 0.1
    }
  }
}
```

Backend `timeout_seconds` defaults to 20, at most 60. Optional `revision` records a
known deployment/weights revision; change it when redeploying behind a stable model
alias. It is local metadata, not a remotely verified weights hash. Optional
`instruction` adds a shared decision preference. Worker-specific task fit remains
in the catalog and assignment. Backend protocol and model identity are separate:
System One is currently supported; Jev is not a package or service dependency.
Other backends can implement the same internal choice contract.

The earlier inline decision-model router remains supported for worker selection
only when `decisions` is absent. For shared decisions, move its protocol/endpoint/
model to `decisions.backend` and retain `router: {"type":"decision-model"}`.
An explicit `decisions.enabled: []` disables backend decisions, including legacy
worker calls; selection returns to the host. Omission of a family leaves it with
the existing host workflow. No calibration path is a credential store.
