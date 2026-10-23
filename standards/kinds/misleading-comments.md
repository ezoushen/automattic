# Misleading comments

## Signal

Look for comments or docstrings that promise behavior the implementation does not
provide, describe a removed path, contradict the accepted contract, or narrate code
without adding a caller contract or necessary constraint. Check renamed symbols,
units, ownership, ordering and failure behavior against relevant callers and tests.
Numbers, counts and absolute words (all, every, only, never) go stale first: check
each against the code it describes. A list of added comments is a discovery aid, not
proof.

## Proof

Quote the exact disputed claim and locate the authoritative contract, implementation
and relevant callers/tests. Show a concrete counterexample or trace that contradicts
the claim. Static proof is sufficient for an explicit mismatch such as a renamed
parameter; concurrency or runtime guarantees require evidence that actually decides
that guarantee. Code alone does not settle intended behavior when it conflicts
with the contract: report unresolved intent or a suspected bug.

For narration, show what the comment restates and why it adds neither an interface
contract nor a constraint that cannot be encoded as a type, assertion, test or lint
rule, subject to project convention. A preference for fewer words is insufficient.
Record counter-evidence; drop accurate, useful comments. Missing contract or deciding
evidence leaves the candidate UNVERIFIED and outside repairs.

## Repair

Correct the smallest false claim using the established contract, or remove proven
redundant narration. Apply [code-comments](../code-comments.md) and the
project's documentation format. Preserve useful function/interface docs and technical
constraints. Update examples and symbol references within scope; run existing doc
checks when applicable and re-read every changed claim against its proof. No
artificial runtime test is needed for prose. If correctness requires changing runtime
behavior, stop and report the suspected bug instead of changing code or documenting
the bug as intended behavior.

## Not a finding

Accurate function/interface documentation, required project docs, machine-consumed
directives, shebangs, license notices and generated markers are not narration.
A necessary external constraint can justify a non-doc comment. A comment's age,
length or appearance in a candidate list alone proves no defect. Preserve accurate
existing comments unless the selected goal and scope establish a proven violation;
this kind is not a repo-wide comment purge.
