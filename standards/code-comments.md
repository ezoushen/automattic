# Code comments

Follow the project's documented comment and documentation conventions first.
Within that convention, keep function/interface docs. Add any other comment only
for a constraint that cannot be encoded as a type, assertion, test or lint rule,
after trying to encode it. Non-obvious reasoning, an opaque algorithm or a
workaround alone does not justify a comment. Never narrate code or record history.
Apply this rule to changed code; do not purge unrelated existing comments.

## Establish and document the contract

Read the affected declaration, implementation, callers/tests and accepted
requirements. Function/interface docs explain responsibility, result and what the
caller needs for correct use: relevant inputs, units, boundaries, failures,
ownership or lifecycle. Keep them concise, accurate and independent of the current
implementation. Preserve useful private function docs; omit empty templates and
repeated signatures. Use examples only when they clarify usage or an edge case.

Support every claim with the accepted contract and code. Distinguish caller
preconditions from callee checks and promises from observations. If code and docs
disagree, establish intended behavior; report unresolved intent or a behavioral
mismatch rather than inventing guarantees or weakening docs to excuse a bug.
A comments-only assignment does not authorize runtime changes.

## Before adding another comment

Try to express the constraint as a type, assertion, test or lint rule. If it can
be enforced there, encode it there within the task's scope and omit the comment.
If it cannot, explain only the remaining constraint and what violating it breaks.
In the work report, record the attempted encoding and why it cannot capture the
constraint; do not put the agent's investigation in source comments.

No narration, progress notes, change logs, author stories, review rounds or
ADR/ticket/PR identifiers. Put implementation history and change rationale in Git
commit messages. A vendor/protocol link may support an allowed constraint comment
but cannot replace its explanation.

Preserve machine-consumed syntax such as compiler directives, lint/type pragmas,
generated markers and required license notices according to the project's tooling
and documented convention. Do not use these forms to disguise prose comments.
Change generated documentation at its source.

## Check the change

Re-read changed docs against the contract, implementation and callers. Verify
references, examples and tool-recognized tags with existing project checks;
do not invent runtime tests for prose. Remove obsolete claims in the changed
scope. Report unavailable checks and unresolved contract questions honestly.

The zloop reviewer owns the documentation gate; writing docs does not certify
it. Leave unrelated problems as scoped follow-ups. For attribution questions, see
[sources](code-comments-sources.md); project policy controls where those sources allow
broader implementation commentary.
