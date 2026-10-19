# The ADR index is the current-state view

`docs/adr/README.md` lists every accepted ADR with its rule in one line, then the superseded and
deprecated ones; it changes in the same commit as the ADRs, `adr_numbers.py --index` checks it, and
agents read it before the ADRs. We added it so members and agents read what holds now without
following supersession chains, while each ADR still carries its own status.
