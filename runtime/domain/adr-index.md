# ADR index

`docs/adr/README.md` is the current-state index: under `## Accepted`, one line per
accepted ADR: its number, title and rule in one line, linked to its file; under
`## Superseded` and `## Deprecated`, the rest. It is updated in the same commit as the
ADRs it lists, so a member reviewing the change sees what now holds. Read the index
first, then only the ADRs that bear on the work. Write each entry as a list line that
links the file, such as `- [0001](0001-slug.md) Title: the rule`; a line the check cannot
read as an entry is reported, never skipped. The [ADR number check](adr.md#deliver-an-efforts-decisions) also verifies the
index against the files and both ends of every supersede link when run with `--index`,
which also makes a missing index a failure.

Statuses and supersession are in [ADRs](adr.md#change-and-follow-them).
