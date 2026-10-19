# Architecture decision records

The repository's shared decision history: each ADR records that a decision was made
and why, for members and agents who were not there. Grilling offers them, delivery
carries an effort's lasting decisions into them, and later work follows them.

## Where they live

ADRs live in `docs/adr/NNNN-slug.md`: the number is the highest existing number plus
one, and the slug names the decision. Create `docs/adr/` lazily, with the first ADR.
With several bounded contexts ([glossary](glossary.md)), system-wide decisions stay in
the root `docs/adr/` and a context's own decisions in `docs/adr/` beside its code.

A project's existing decision-record convention wins, under its own name, location
and numbering; neither the folder nor any ADR is required.

## Format

```md
# {Short title of the decision}

{One to three sentences: the context, what was decided and why.}
```

An ADR is a title and one to three sentences. Add Status, Considered Options and
Consequences only when they add something: Status (`proposed`, `accepted`,
`deprecated` or `superseded by ADR-NNNN`) once a decision is revisited, Considered
Options when a rejected alternative is worth remembering, Consequences when a
downstream effect is not obvious.

## When to offer one

All three must hold; when any is missing, skip the ADR:

1. **Hard to reverse:** changing your mind later has a meaningful cost.
2. **Surprising without context:** a future reader would wonder why it was done this way.
3. **A real trade-off:** there were genuine alternatives, chosen between for specific reasons.

Typical cases: the architecture's shape, how contexts integrate, technology with
lock-in, ownership and scope boundaries (the explicit no's too), deliberate departures
from the obvious path, constraints invisible in the code, and a rejected alternative
someone would otherwise propose again.

Offer the ADR to the user and write it only after their yes; an agent never writes one
on its own judgment. Before offering, search the existing ADRs: a decision that changes
an earlier one is offered as a replacement, never a duplicate.

## Change and follow them

Never rewrite an accepted ADR. A changed decision is a new ADR that supersedes it, and
the old one's Status becomes `superseded by ADR-NNNN`. Accepted ADRs bind later work:
read those in the area before planning or changing it. Work that would contradict one
stops for a design decision; one that looks outdated is flagged to the user, not
silently followed.

## Deliver an effort's decisions

An effort's ledger stays in ignored `.scratch/`, so its lasting decisions reach other
members only as ADRs. When the effort's implementation is complete, list each ledger
row that passes the three tests as a candidate ADR in the run report, with the row it
comes from, and ask the user once for the whole list. Do not wait for the answer:
write only the candidates the user approves into the effort branch, those answered
before its review head is pinned, so the review covers them; candidates still
unanswered wait among the actions only the user can take, and an approved candidate
written later returns that change to review and E2E.

Numbers are claimed on `main`. Commit the approved ADRs before the check. Fetch first,
then, before pinning the review head, merge the verified `main` tip into the effort
branch and run the ADR number check; on a duplicate, renumber the effort's ADR to the
next free number and update every reference to it in the same commit. The delivery
gate repeats the check without merging, against each `main` the effort lands on: the
local one and, once fetched, the remote's when the effort is published:

```sh
python3 <plugin_root>/scripts/adr_numbers.py --repo <repo> --ref <effort branch> --against <main tip> [--dir <ADR folder>]
```

It prints the duplicated numbers and the next free one, and exits 1 on a duplicate.
Run it once for each ADR folder: the root one and each context's. It checks only
`NNNN-slug.md` names; a project whose own convention numbers differently uses its own
check or records an evidenced skip. A merge or renumbering after the review head is
pinned returns to review and E2E, and a duplicate number fails the delivery gate.
