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
  so an earlier or later rule can satisfy it.

A shape is a lead, never a finding. When the `test-shape`
[shadow pilot](../../../harnesses/decisions.md#test-effectiveness-shadow-pilots) is
enabled, record each added or modified test with it before judging; its label stays
hidden and changes nothing.

## Proof

Work per test, in an isolated worktree, with the project's own test command. Nothing
here depends on the language.

1. **Claim.** State in one sentence the behavior the test protects, from the ticket
   criterion, the test name and its assertions. A claim that cannot be stated is
   itself worth reporting.
2. **Revert check**, for a test added with new behavior: revert the implementation
   change, keep the test, and run it. It must fail at an assertion. If it passes,
   it protects nothing the change added: CONFIRMED. Skip this step for refactors
   and for tests of behavior that already existed.
3. **Defects.** Write one to three small, plausible defects in the claimed behavior
   as diffs to the code under test, preferring the lines the change touched: delete
   the guard that produces an expected rejection, drop or truncate part of a result,
   off-by-one a bound, swap an order.
4. **Run each defect.** The test passes on the real code. With the defect, record
   the outcome and the operation's observable output in both runs: return value,
   exit code, error text, records written. Failing at an assertion means the test
   protects that behavior. A setup error, import error, skip or crash before any
   assertion proves nothing. Passing makes the defect a survivor.
5. **Judge survivors.** A survivor is a finding only if the defect changed the
   claimed behavior. Compare the two runs' outputs against the claim. A difference
   outside the claim means the defect is equivalent for this test; drop it. Output
   that is identical, or that still fails for another reason, can also mean another
   rule decided the result and masked the claimed one. Then run one probe: the same
   operation with an input that only the claimed rule should reject or change, every
   other precondition valid. If the defect changes the probe's result, the test is
   masked and the finding stands; if not, drop the defect. When the `defect-effect`
   shadow pilot is enabled, record the survivor with it before judging.

Retain for each candidate the claim, defect diff, commands, outputs and input
identity. Mark it CONFIRMED (revert check passed, or a survivor changed the claimed
behavior), FALSE-POSITIVE (the test failed at an assertion, or the defect was
equivalent) or UNVERIFIED (no claim, no runnable command, or no observable output).

## Repair

Rewrite the test so it checks the claim with an expected result from an independent
source: a specified literal, a worked example, or a separate trusted oracle. Run the
rewrite against the surviving defect, or against the reverted implementation: it
must now fail at the intended assertion. Restore the real code and run it again: it
must pass. Keep production behavior unchanged; defects and reverts are temporary.

Remove a test instead only when it failed on none of the defects and every defect
it covers is caught by another retained test. List these for the user to confirm;
never delete them during the repair.

If the corrected test fails on the real implementation, stop and report a suspected
bug with the claim, corrected test, command and output. Preserve the corrected test
for handoff; do not change runtime behavior or weaken its expectation to green.

## Not a finding

A small test, a literal assertion, shared input fixtures, or an independently
specified constant is not circular merely because it resembles the code. Property
tests and trusted reference implementations can be independent oracles. A test
that fails at an assertion on the relevant defect already protects that behavior.
Survival of an equivalent defect, an unrelated defect, or one outside the test's
claim is not proof of tautology. Missing broader coverage belongs in a separate
finding under an explicitly requested goal.
