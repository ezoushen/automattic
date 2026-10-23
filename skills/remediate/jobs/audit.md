---
name: audit
agent: reviewer
inputs: ["worktree", "head", "report", "goal", "kind", "inventory"]
returns: ["## Coverage", "## Findings"]
independent_of: []
acceptance: false
---

# audit

Detect and prove one remediation kind or goal across an assigned file inventory at a
pinned head. [Remediate](../SKILL.md) assigns it; there is no diff and no repair.

## Inputs

The assignment names the `worktree` and pinned `head`, the `report`, the `goal`, the
`kind` file (a built-in kind, or the free-form goal's written signal, independent
source, deciding proof, allowed repair and exclusions), and the `inventory`: the
files this worker owns, possibly one partition of a larger scan.

## Finish line

Everything in the inventory is in scope, including code that predates any change;
existing defects of the kind are the target, not follow-ups. Read the kind's Signal,
Proof and Not a finding sections and apply them to every item they cover: when the
kind's Proof has steps for every test, run them for every test in the inventory, not
only suspected ones. Discover comments and docstrings by inventorying the source
(language tokenizer/AST where available, otherwise careful reading); the comment
audit lists only added lines and is not a scan.

Record each candidate with an ID, file/line, the precise disputed assertion or
claim, its contract source and the counter-evidence considered. Prove it as the
kind's Proof says. Run experiments only where that Proof calls for them, as
temporary negative controls in an isolated copy, restored after saving their
evidence; a candidate the Proof confirms by reading needs no run. Mark a flag you
would dismiss, or one you cannot prove, UNVERIFIED (disputed) and list its ID for a
[reproduce](../../review/jobs/reproduce.md) job; another worker decides it.

Discoveries outside the kind or goal go to `## Follow-ups`. Done when every item the
kind's Proof covers has a recorded observation, every file in the inventory is
accounted for and every candidate has a verdict.

## Return

`## Coverage`: every inventory file, scanned or not and why, with the count of its
items and how many have a recorded observation; a generated or default verdict is
not one. `## Findings`: per
candidate, its ID, location, claim, contract source, deciding evidence (trace,
re-read lines, or mutation diff with command and output) and verdict, plus a
proposed minimal repair for CONFIRMED ones. End with counts per verdict and the IDs
that need a reproduce job. No repairs.
