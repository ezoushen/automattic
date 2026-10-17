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

1. **Checklist.** State the claim in one sentence, then record every assertion,
   including those made inside helpers the test calls, with the fields of the
   [checklist contract](../../../harnesses/decisions.md#test-effectiveness-routing):
   where its expected value comes from, whether it can run, whether an expected
   failure is checked by its reason or only by code or type, and whether a
   collection is compared whole. Record observations with line numbers, not verdicts.
2. **Route.** Run `classify-test` with the checklist. An expected failure checked
   only by code or type routes to the trace without a model call. Otherwise the
   decision model answers: `protected` needs nothing more, `flagged` names a shape,
   and `escalate` (low confidence, orders disagree, or the model is disabled)
   means you decide by reading the cited lines.
3. **Trace a masked rule.** For each expected failure on the `trace` route, find the
   check that rejects the test's input, remove it in your head and follow the same
   input onward. It is masked if another check still produces a failure the test
   accepts and no later assertion notices. Cite the rejecting and backup checks.
4. **Re-read.** For a flagged or escalated test, read the cited lines again. Dismiss a
   flag only with concrete contrary evidence, such as the line where the test would
   fail. False alarms are expected here; dismissing them is part of this step.
5. **Confirm by running**, only when the project's instructions allow its tests to run
   in a temporary worktree without extra setup. For each remaining flag, write a diff
   that removes the rejecting check (or introduces the defect a pattern flag predicts),
   name the text the test runner prints when the assertion fails, and run
   [confirm-flags](#confirm-flags). For a test added with new behavior, a diff that
   reverts the implementation change is the same kind of check.

Mark each candidate CONFIRMED (a cited trace or re-read shows the defect passes, or a
confirmation run did), FALSE-POSITIVE (dismissed with evidence, or a confirmation run
failed at the expected assertion) or UNVERIFIED (no checklist, no traceable rejection, a
failure before any assertion, or a confirmation run that could not decide). Say which
findings were confirmed by running.

## Repair

Rewrite the test so it checks the claim with an expected result from an independent
source: a specified literal, a worked example, or a separate trusted oracle; for an
expected failure, check the reason the claimed rule gives. Run the rewrite on the real
code: it must pass. When confirmation runs are allowed, run it with the flag's diff
too: it must fail at the intended assertion. Keep production behavior unchanged.

Remove a test instead only when it protects nothing that another retained test does
not already protect. List these for the user to confirm; never delete them during
the repair.

If the corrected test fails on the real implementation, stop and report a suspected
bug with the claim, corrected test, command and output. Preserve the corrected test
for handoff; do not change runtime behavior or weaken its expectation to green.

## Confirm flags

```sh
python3 <plugin_root>/scripts/confirm-flags.py --repo <repo> --input <flags.json> \
  [--ref <head>] [--jobs <n>] [--timeout <seconds>]
```

The input lists `{"id", "command", "diff", "fails_with"}`: the project's command for one
test as an argument list, a unified diff against `--ref`, and optionally the text the
runner prints when that assertion fails. Each flag runs in its own temporary detached
worktree; the checkout is never modified, and worktrees and the commands' process groups
are removed afterwards, also on interruption. The unchanged test must pass first.
`confirmed` means the test still passes with the diff applied; `dismissed` that it fails
and prints `fails_with`; `failed` that it fails otherwise, so read `output_tail` before
deciding; `unverified` that the baseline failed, the diff did not apply, the command could
not start or the run timed out.

## Not a finding

A small test, a literal assertion, shared input fixtures, or an independently
specified constant is not circular merely because it resembles the code. Property
tests and trusted reference implementations can be independent oracles. An expected
failure checked only by code is not a finding when no other check would reject the
same input. Missing broader coverage belongs in a separate finding under an
explicitly requested goal.
