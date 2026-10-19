# Routers, profiles and decisions

The backend that decision-model routers and checkpoints call is in [decision backend](decision-backend.md).

## Routers and sparse profiles

`agents.<agent>.candidates` is the allowed pool, without a model default. The optional
`router` chooses the selection strategy. Omission uses the built-in skill:

```json
{
  "router": {
    "type": "skill",
    "skill": "automattic:model-routing"
  }
}
```

The model-routing skill guides the host's judgment
within its existing context. Add `instruction` only for user-specific preferences.
An installed routing skill can call Jev or another decision model and return the
same selection contract. That is a selection interface, not a worker executor;
inspection never loads the skill, calls an API or installs a dependency.
For a service exposing System One directly, use the built-in
decision-model router.

A profile router applies sparse overrides after establishing the worker runtime:

```json
{
  "profiles": {
    "balanced": {
      "builder": {
        "codex": {"candidate": "sol", "thinking": "medium"},
        "pi": {"candidate": "glm"}
      }
    }
  },
  "router": {"type": "profile", "profile": "balanced"}
}
```

`builder.codex` means the worker runs in Codex, including a Claude caller that
launches it through a bridge. A job name beside the agent names (for example
`"repair": {"codex": {"candidate": "sol"}}`) overrides the agent's entry for that job.
For a job with its own pool, an agent-level pin applies only where its candidate is
in that pool; a job-level pin must be. The host still determines which launch routes exist.
No `choices` wrapper is used. Missing candidate, thinking, agent or runtime leaves
that part of selection unchanged; an empty profile is valid. Profiles do not alter
pools or executors. Candidate overrides must belong to the agent pool and have a
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
