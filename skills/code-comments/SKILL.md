---
name: code-comments
description: "Write code comments and API docs when adding or changing source documentation, or when behavior changes its contract. Not PR review comments."
argument-hint: "[files, symbols, or comment-writing task]"
---

# Code comments

Use this skill when writing or changing source comments, or when a behavior change
affects existing documentation. It is available to any agent and needs no Automattic
board or review session. Preserve the task's scope and the project's language,
terminology, documentation format and tool conventions.

## Establish the contract before writing

Read the affected declaration, implementation, relevant callers/tests and accepted
requirements. Comments and code are maintained source contracts: neither automatically
overrules the other when they disagree. Establish intended behavior from the accepted
contract; surface unresolved intent instead of inventing guarantees or rewriting
docs to excuse a bug. For a comments-only assignment, report a behavioral mismatch
without silently changing runtime code.

Document facts you can support. Distinguish promises from observations, caller
preconditions from checks performed by the callee, and current limitations from
future plans. Do not claim thread safety, atomicity, ordering, retries, ownership
or performance bounds merely because the implementation appears to suggest them.

## Write for the reader's decision

- **At the interface**, explain what the operation provides and what the caller
  must know to use it correctly. Start with its responsibility and result; a clear
  summary may be sufficient. Add inputs/results, units, boundaries, failures,
  ownership or lifecycle notes only when needed for correct use. Describe observable
  promises, not the current helper calls, loop structure or internal algorithm.
  Would this documentation remain true after a different implementation of the
  same contract? If not, remove incidental details or move necessary rationale
  beside the implementation. Do not omit meaningful edge cases to stay brief.
- **Beside the implementation**, explain non-obvious reasoning, invariants, ordering,
  tradeoffs or context from outside the project. Supplement the code; never narrate
  its statements. For an opaque algorithm or expression, explain the underlying
  idea only if it adds understanding beyond reading the code. Explain what a tempting
  change would break, rather than merely warning "do not change this."
- **For a workaround**, explain the current external constraint and when it stops
  applying. Keep work tracking and planned tasks in the issue tracker or PR;
  source comments describe the technical reason that matters to a maintainer.

Before adding prose, ask what a reader familiar with this codebase would learn.
If it only repeats the code or explains a routine local convention, leave it out.
Useful private documentation is allowed; empty tag templates and repeated
identifiers add no meaning. Don't delete a useful contract because the code looks
simple. Follow project documentation requirements;
there is no universal comment quota, ban on private docstrings, or mandatory list
of headings. Do not refactor unrelated code just to avoid explaining it.

## Make the prose precise and maintainable

Use concrete subjects, conditions and outcomes. Explain units and boundaries rather
than saying "small," "soon," "valid" or "safe" without context. State time/space
complexity when it affects caller expectations or project conventions require it;
define the input size and relevant worst-case/amortized assumptions. Verify the
bound instead of guessing it from the presence of a loop or a container type.

Comments are not a working journal. Do not add ADR/ticket/PR identifiers, review
rounds, implementation progress, change logs, author narratives or "fixed for X"
notes. Put relevant implementation history, ADR/ticket references and change
rationale in Git commit messages, following the project's commit convention.
Explain the durable technical
reason directly. A relevant external protocol/vendor reference may support that
reason, but its URL must not substitute for the explanation.

Keep one authoritative contract and use supported symbol references or inheritance
for shared behavior; document an override's differences. Keep implementation
rationale beside the affected code rather than duplicating it in API docs.

Add an example when prose leaves usage or an edge case unclear, not merely to
demonstrate an obvious call. Use the smallest example that resolves the ambiguity,
use the actual API, and show
necessary failure handling or cleanup. Validate them with existing tooling when
applicable; label illustrative pseudocode and never present it as a tested example.
Keep essential reasoning in the comment even when linking an external source.

Treat machine-consumed comments as functional syntax: documentation tags, compiler
directives, lint suppressions, generated markers and license notices can affect
behavior or tooling. Preserve their placement/meaning and follow the local tool's
format. Change generated documentation at its source rather than editing output.

## Check the change

Re-read each factual claim against the contract and code, including existing
comments affected by renamed symbols or changed behavior. Check referenced symbols,
examples, tags and rendered output where relevant. Use project documentation checks
when available; do not add a tooling stack or artificial runtime test for prose.
Remove obsolete explanations within the changed scope; do not preserve false
claims as historical notes. State checks that could not run and unresolved contract
questions honestly in the work report, not as an agent journal in source comments.

In Automattic, the reviewer owns the hard documentation gate and its verdict;
writing comments does not certify that gate. Leave unrelated documentation issues
as scoped follow-ups rather than expanding the assignment.

For the research basis and differences intentionally left to language/project
conventions, see [sources](references/sources.md). Read it when attribution or a
style decision needs explanation; routine writing does not require fresh research.
