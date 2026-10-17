# Tautological tests

A test is tautological for the behavior it claims when a plausible defect in that
behavior leaves it passing. It then adds run time and coverage without protecting
anything. Judge each test against its own claim: the same test can protect one
rule and be hollow for another.

## Signal

Look for these shapes, then trace the actual assertions and setup before judging:

- an expected value computed by the code under test or a copy of its logic;
- assertions on values the test configured on a mock;
- an assertion that cannot fail: swallowed, after a return, in an uncalled callback;
- assertions on internal state or another behavior while the claimed result goes unchecked;
- a check of only part of the claimed result, such as a loop that stops at the
  shorter of two lists;
- an expected error or exit code without a check that the claimed rule caused it,
  so another rule can satisfy it.

## Proof

Work per test by reading; nothing here changes code or depends on the language.
Steps 1 and 2 apply to every test in scope, not only the ones you suspect: a test
that looks fine at a glance is where hollow checks hide.

1. **Checklist.** State the claim in one sentence, then record every assertion,
   including those made inside helpers the test calls, with the fields of the
   [checklist contract](../../../harnesses/decisions.md#test-effectiveness-routing):
   where its expected value comes from, whether it can run, whether an expected
   failure (any rejection, including a refused or degraded state) is checked by its
   reason or only by code or type, how strictly it compares, and what it would see
   if the claimed rule were removed: read the default path and the other checks the
   same input reaches. Record observations with line numbers, not verdicts. A
   script may extract test bodies and code, but each field is what you observed by
   reading that test; a generated or default value is not an observation. Answer
   `unknown` only when the code does not settle it.
2. **Route.** Run `classify-test` with the checklist. An expected failure checked
   only by code or type routes to the trace, and a checklist where no claim assertion
   tells the rule apart is flagged, both without a model call. Otherwise the decision
   model answers: `protected` clears a test only when its checklist raised no doubt
   (a test you already suspect is re-read whatever the route), `flagged` names a
   shape, and `escalate` (low confidence, orders disagree, or the model is disabled)
   gets one more round with the context it lacked, as the
   [routing contract](../../../harnesses/decisions.md#test-effectiveness-routing)
   describes. When nothing new can be collected or round 2 escalates, decide by
   reading the cited lines.
3. **Trace a masked rule.** For each expected failure on the `trace` route, find the
   check that rejects the test's input, remove it in your head and follow the same
   input onward. It is masked if another check still produces a failure the test
   accepts and no later assertion notices. Cite the rejecting and backup checks.
4. **Re-read.** For a flagged or escalated test, read the cited lines again. Dismiss
   an escalation only with concrete contrary evidence, such as the line where the test
   would fail. A flag you would dismiss is disputed: the reproducer decides it, given
   your contrary evidence and the flagged shape. False alarms are expected here.
Mark each candidate CONFIRMED (a cited trace or re-read shows the defect passes),
FALSE-POSITIVE (dismissed with cited evidence) or UNVERIFIED (no checklist, or no
traceable rejection). Confirming a finding changes no code and runs no test; a
reproducer for a disputed or UNVERIFIED candidate repeats these reading steps.

## Repair

Rewrite the test so it checks the claim with an expected result from an independent
source: a specified literal, a worked example, or a separate trusted oracle; for an
expected failure, check the reason the claimed rule gives. Run the rewrite on the real
code: it must pass. Keep production behavior unchanged.

Remove a test instead only when it protects nothing that another retained test does
not already protect. List these for the user to confirm; never delete them during
the repair.

If the corrected test fails on the real implementation, stop and report a suspected
bug with the claim, corrected test, command and output. Preserve the corrected test
for handoff; do not change runtime behavior or weaken its expectation to green.

## Not a finding

A small test, a literal assertion, shared input fixtures, or an independently
specified constant is not circular merely because it resembles the code. Property
tests and trusted reference implementations can be independent oracles. An expected
failure checked only by code is not a finding when no other check would reject the
same input. Missing broader coverage belongs in a separate finding under an
explicitly requested goal.
