---
name: remediate
description: "Find, prove and repair tautological tests, misleading comments or a specified goal within a chosen scope."
disable-model-invocation: true
argument-hint: "[tautological-tests|misleading-comments|<goal>] [--base <ref> [--head <ref>] | <path>... | --project] — defaults: both kinds on the current diff"
---

# remediate

First read [runtime bootstrap](../../bootstrap.md) and the host session part.
Run only on the user's explicit invocation. This procedure supplies its own
detection, proof and test-first repair loop; no external skill is required.
Remediation changes tests and documentation only. A suspected runtime bug is a
reportable result, not authorization to change runtime behavior.

## Arguments

| Argument | Meaning |
|---|---|
| `tautological-tests`, `misleading-comments` | One built-in kind. Omitted: both kinds. |
| `"<goal>"` | A free-form goal, quoted. |
| `--base <ref>` [`--head <ref>`] | **Diff** scope from base. Without `--head`: base against the working tree. |
| `<path>...` | **Paths** scope: the named files or directories. |
| `--project` | **Whole project** scope; findings are reported before any repair. |
| none | **Diff** scope against the established review target; asks for `--base` if none. |

Examples: `remediate tautological-tests tests/`,
`remediate misleading-comments --base main`, `remediate --project`.
Equivalent plain-language scope in the request is accepted.

## Establish goal and scope

Resolve the goal as [tautological-tests](kinds/tautological-tests.md),
[misleading-comments](kinds/misleading-comments.md), or the user's free-form goal.
Read only the selected kind. If no goal is given, run all built-in kinds
([tautological-tests](kinds/tautological-tests.md) and
[misleading-comments](kinds/misleading-comments.md)) in one pass instead of
asking. For a free-form goal, write its signal, independent source of intended behavior,
deciding proof, allowed repair and exclusions before scanning. Apply the same
proof bar as the built-in kinds; an unclear contract stays unresolved.

Resolve scope before acting:

- **Diff** (default): use the user's base/head or the established review target,
  including its changed tests/comments and the context necessary to judge them.
  If no base is established, ask for it. Pin the base/head and record whether
  working-tree changes are included; preserve unrelated changes.
- **Paths**: scan the named files/directories, including existing tests/comments
  within them. Follow callers and implementation for evidence, keeping repairs
  inside the selected paths.
- **Whole project**: only when explicitly requested. Inventory top-level modules
  and assign a reviewer the [audit](jobs/audit.md) job per module through normal
  routing. Follow the selected adapter's capacity and worker lifecycle; use sequential read-only
  passes when workers are unavailable. Record coverage and any unscanned modules.
  Present proven findings and dropped/unverified counts before any repair, then
  wait for the user's confirmation of the findings to repair. Time passing or a
  completed scan is not confirmation.

Diff/path invocations authorize repairs after proof. Whole-project confirmation
authorizes only the selected findings; refresh their evidence if inputs changed
while waiting. A free-form goal needing runtime changes exceeds this procedure:
report that boundary for a separate implementation task.

## Detect, prove, repair, recheck

1. **Detect read-only.** Read the selected scope and the kind's Signal and Not a
   finding sections. Record candidates with IDs, file/line, the precise disputed
   assertion or claim, its contract source and counter-evidence. For comment
   diffs, run the [comment audit](#comment-audit) and inspect its output in context;
   its candidates alone prove no violation; it lists only comments added in the
   diff, and also read changed doc comments, which the audit intentionally
   excludes. A whole-project or paths scan discovers existing comments and
   docstrings by inventorying the source (language tokenizer/AST where available,
   otherwise careful reading). When the kind's Proof has steps for every test,
   run them for every test in scope during detection, before selecting candidates.
   For a paths or whole-project scan, reconcile the file inventory against the
   workers' coverage file by file, and scan every file no worker accounted for.
   Detection makes no source edits; delegated detection is a reviewer's audit job.
   Every delegated audit, reproduce or repair assignment names its job's inputs, with
   an absolute report outside the worktree, such as
   `<main checkout>/.scratch/remediate-<goal>/reports/<partition>.md`.
2. **Prove.** Apply the kind's Proof to each candidate. Retain the pinned inputs,
   exact command/trace or contract-to-code comparison and deciding observation.
   Run experiments only where the kind's Proof calls for them: temporary negative
   controls in isolation, restored after saving proof, with owned processes reconciled
   under [check execution](../../harnesses/checks/run.md). A candidate the kind's Proof
   confirms needs no further run.
   Send disputed or UNVERIFIED findings to a reviewer's [reproduce](../review/jobs/reproduce.md)
   job through normal routing, never to the worker that raised them, with the kind's
   proof steps, diagnosis-only scope and counter-evidence. A clean independent verification can replace a disputed initial claim.
   Mark each candidate CONFIRMED, FALSE-POSITIVE or UNVERIFIED. Drop disproven
   and unproven claims from repairs; report their counts and reasons. Missing
   tools or inability to reproduce leave proof incomplete, never confirmed.
3. **Repair confirmed findings.** Enforce the scope's confirmation rule first.
   Use a builder's [repair](../review/jobs/repair.md) job when delegated, supplying
   confirmed IDs, accepted seams, test/comment-only boundaries and this procedure. Otherwise
   apply the same bounded steps directly. For tests: follow the kind's Repair, with an
   expected result from an independent source and, for an expected failure, a check
   of the claimed rule's own reason; then run it against the real implementation.
   Production code is never altered to prove the rewrite.
   If it fails there, stop repairs and report a suspected runtime bug with the
   failing command/output; preserve the corrected test and evidence for handoff.
   Runtime behavior stays unchanged. For comments: use the kind's contract proof
   and the shared [writing guidance](../code-comments/SKILL.md), without inventing
   runtime tests for prose. Keep repairs surgical and preserve accurate docs.
4. **Recheck.** Verify every repaired finding against its original proof, rerun
   affected checks and the project's required gates, and read the final diff for
   runtime changes and unrelated edits. Remove only owned temporary controls.
   Recheck invalidated evidence after a repair; reuse unchanged passing evidence
   with its original input identity. Missing checks remain explicit gaps.
5. **Report.** Give goal, base/head or working-tree identity, scope and coverage;
   confirmed, repaired, dropped and unverified counts; per-finding proof and repair
   locations; commands/results and retained evidence; suspected bugs and remaining
   gates. Whole-project detection returns this report before requesting repair
   confirmation. For a free-form goal, offer to save its definition as a reusable
   kind; write it only if requested. Finish when every candidate is accounted for,
   or return the exact blocker with partial evidence. Publication and integration
   retain their existing owners and authorization.

## Comment audit

Run from any directory, resolving the script from `plugin_root`:

```sh
python3 <plugin_root>/scripts/comment_audit.py --repo <repo> --base <base> [--head <head>] [paths...]
```

It emits a JSON list of `{file, line, text}` for added plain comment lines,
ordered by path and new-file line number. Paths are relative to the repo root.
The comparison is a direct Git diff from base, not an inferred merge base.
Omit `--head` for staged plus unstaged tracked changes; untracked files are outside
Git's diff until added. An empty list means no candidates within supported syntax,
not that comments are correct. Errors exit nonzero and prevent a clean audit claim.

Supported extensions are `.py`, `.pyi`; `.js`, `.jsx`, `.mjs`, `.cjs`, `.ts`,
`.tsx`, `.mts`, `.cts`; `.sh`, `.bash`, `.zsh`; and `.sql`. Unknown types are skipped.
Full-file context distinguishes comments from quoted text, Python docstrings,
JS template text and common regex literals, shell here-documents and SQL dollar
strings. Added lines inside an existing plain block comment remain candidates.
Python string tokens and `/** ... */` documentation are excluded, as are first-line
shebangs, TypeScript triple-slash reference directives, leading license notices
and common lint/type pragmas (`noqa`, `type:`, `pylint`, `pyright`, `mypy`,
`fmt`, `isort`, `shellcheck`, `shfmt`, `sqlfluff`, `eslint`, `tslint`, `@ts-*`,
`prettier-ignore`, coverage-ignore directives and Python encoding declarations).
Ordinary triple-slash prose remains a candidate.

This is a bounded lexical audit, not a language parser or blocking hook. Inspect
JSX markup, ambiguous JS regex/division contexts, shell expansions and SQL dialect
syntax manually. Project-specific doc/pragma forms need contextual review. Apply
the kind's proof before deciding whether any listed comment needs repair.
