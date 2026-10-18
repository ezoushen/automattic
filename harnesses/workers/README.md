# Workers

Rules for the orchestrator and its workers, in the order a worker runs.

| File | Read |
|---|---|
| [launch.md](launch.md) | before every launch: resolve the executor and build the assignment |
| [skills.md](skills.md) | while building an assignment: which skills the worker gets |
| [thinking.md](thinking.md) | when a resolved agent allows the orchestrator to adjust thinking |
| [focus.md](focus.md) | throughout an assignment: priorities, checkpoints, return and blocked continuation |
| [resources.md](resources.md) | before admitting a batch, reserving a resource or starting an owned job |
| [prepare.md](prepare.md) | to register an attempt and verify its settings before productive work |
| [wait.md](wait.md) | to arm a wait, handle each wake and pass the yield gate |
| [collect.md](collect.md) | to collect a result, accept or decline it and record its outcome |
| [retire.md](retire.md) | to close a worker after its final use |
| [design-hold.md](design-hold.md) | when a worker may need to break or reinterpret the agreement |
