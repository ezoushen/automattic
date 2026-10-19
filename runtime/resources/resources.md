# Runner contract checks

Before admitting a batch, read [shared capacity](capacity.md); before reserving an exclusive
resource or starting a job a worker owns, read [resource and job lifetime](lifetime.md).
This file holds the runner contract checks.

Before implementing a runner, identify who owns the launcher, descendants, mutex,
temporary configuration and restoration. Verify promised startup/Ready, early-exit,
cancellation and restoration-failure behavior through the actual shipped entrypoint,
including its lock wrapper. Stub external services when appropriate while retaining
that process boundary. An environment flag that bypasses the wrapper cannot prove
its signal or lock behavior. Confirm descendants exit before releasing exclusivity;
preserve recoverable configuration when restoration fails. Describe only the tested
signal guarantees, including any inherited file-descriptor limits.
