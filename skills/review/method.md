# Implementation review method

The implementation-review owner applies this method once to the eligible batch.
It has two axes, reported separately: **Standards** (does the change follow the
project's documented rules?) and **Spec** (does it do what was accepted?). A change
can pass one and fail the other; merging or reranking them lets one mask the other.

## Pin the range

Use the assignment's pinned `diff_base` and `head`: the change is
`git diff <diff_base>..<head>`, its commits `git log --oneline <diff_base>..<head>`.
Confirm both resolve and the diff is non-empty before reviewing. A tool's default
range or working directory does not establish the target.

## Standards

Sources, in order of authority:

1. The project's documented rules: coding-standards and contributing files, agent
   instruction files (`AGENTS.md`, `CLAUDE.md` and equivalents), and conventions
   recorded in its docs or decisions.
2. Automattic's built-in rules, which a documented project rule overrides:
   [code-comments](../code-comments/SKILL.md) and
   [tautological-tests](../remediate/kinds/tautological-tests.md), applied as the
   [reviewer](../../agents/reviewer.md) agent describes.
3. Simplicity within the change: logic the diff duplicates, and parameters,
   branches or abstractions it adds that nothing in the accepted scope uses.

Skip what the project's tooling already enforces. Each finding cites its source
(file and rule, or the built-in rule) and the hunk, with proof: for duplication,
both hunks; for unused additions, the search showing no caller. A preference
without a documented rule or proof is not a finding.

## Spec

Use the supplied brief, ticket, alignment or accepted decisions. A PR description
is evidence of intent, not an approved requirement. Without a spec, report the axis
as limited and invent no requirements.

Report, quoting the spec line for each:

- requirements missing or only partly implemented;
- behavior the change adds that was not asked for;
- requirements that appear implemented but behave wrongly, each with an executed
  reproduction or a traced failure path.

## Report

Write `## Standards` and `## Spec` as complete sections, then one summary line per
axis: finding count and the most severe finding. Do not pick one winner across
axes. A return-summary length limit applies to the summary only, never to findings
or coverage.
