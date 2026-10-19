# Decisions

The binding decisions of this repository, newest last. Format, statuses and supersession:
[ADRs](../../runtime/domain/adr.md); this index: [ADR index](../../runtime/domain/adr-index.md).

## Accepted
- [0001](0001-adr-numbers-are-checked-on-main.md) ADR numbers are re-checked on main when an effort lands: number on the branch, re-check against the fetched `main` before review, renumber on a collision.
- [0002](0002-grilling-asks-principles-only.md) Grilling never asks the user about implementation detail: principles and material forks only, at every depth; the agent shows material choices for veto.
- [0003](0003-adrs-record-what-others-follow.md) An ADR records a decision others must follow, or one that passes the three tests: bare rules go to the rules file.
- [0004](0004-adrs-are-superseded-never-rewritten.md) ADRs are superseded, never rewritten: the old ADR's status line is its only edit; a partial overrule supersedes the whole.
- [0005](0005-the-adr-index-is-the-current-state.md) The ADR index is the current-state view: updated in the same commit, checked with `--index`, read first.
- [0006](0006-adr-statuses-have-no-proposed.md) ADR statuses have no proposed: accepted, superseded by ADR-NNNN or deprecated; the user's yes accepts.

## Superseded

## Deprecated
