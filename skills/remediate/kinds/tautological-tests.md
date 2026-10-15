# Tautological tests

## Signal

Look for assertions whose expected value comes from the same production constant,
helper, algorithm or output being checked; mock return values asserted back without
an observable contract; or a bypass that prevents the asserted failure operation
from running. Trace the actual assertion and setup before judging a test by shape.

## Proof

Identify the accepted contract and public seam. Establish an expected result from
an independent source: a specified literal, externally worked example or separate
trusted oracle. Explain which plausible defect the test claims to detect.

In an isolated copy, introduce that deliberately wrong implementation at the
relevant operation. Prove the operation executes and that the existing test still
passes. Retain the mutation, command/output and input identity. A broken fixture,
skipped test, import/setup error or mutation outside the claimed behavior proves
nothing about assertion sensitivity. If the original test fails for the intended
reason, drop this finding. If the independent contract or execution proof is
missing, mark it UNVERIFIED.

## Repair

Replace the circular expectation or bypass with an assertion at the accepted seam
using the independent expected result. Run it against the same wrong implementation:
it must now fail at the intended assertion. Restore the real code and run it again:
it must pass. Retain red/green evidence and run affected tests. Keep production
behavior unchanged; the mutation is temporary proof, never part of the repair.

If the corrected test fails on the real implementation, stop and report a suspected
bug with the contract, corrected test, command and output. Preserve the corrected
test for handoff; do not change runtime behavior or weaken its expectation to green.

## Not a finding

A small test, a literal assertion, shared input fixtures, or an independently
specified constant is not circular merely because it resembles the code. Property
tests and trusted reference implementations can be independent oracles. A test
that rejects the relevant wrong implementation already detects that defect.
Survival of an equivalent mutation, an unrelated mutation, or a wrong implementation
the test never claims to cover is not proof of tautology. Missing broader coverage
belongs in a separate finding under an explicitly requested goal.
