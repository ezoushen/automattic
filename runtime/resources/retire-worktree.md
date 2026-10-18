# Retire a worktree

The lifecycle owner first confirms that review/repair and applicable E2E are
complete or explicitly excluded, and no assignment, queued command or owned job
still needs the checkout. Integration and a clean Git status are insufficient:
ignored build directories can contain the only acceptance evidence.

Follow evidence retention before removal.
Verify the retained copies and report links from outside the retiring checkout.
Missing evidence or uncertain ownership keeps it available for recovery. Use the
host's managed worktree retirement tool when provided; otherwise remove the exact
verified checkout without force. Before removing, check
`git -C <checkout> status --porcelain --ignored`. Never gate retirement on
`--untracked-files=no`. If plain `git worktree remove` refuses, the refusal is the
signal: inspect what is left and retain or delete it explicitly. Never add
`--force`. Preserve branches required by downstream work.
