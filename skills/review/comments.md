# Review comments

Read when a review decides, delegates or publishes comments.

## Comment policy

`--comments draft|confirm|post` is independent of a prior walkthrough:

- **draft** (default): keep comments local. No remote pending review or submission.
- **confirm**: finish the review, show the exact proposed summary and inline batch
  with anchors, then wait for the user's approval before posting that batch.
- **post**: the invocation authorizes posting confirmed in-scope findings after
  validation, without another confirmation. It does not authorize a merge verdict.

Honor equivalent natural language: "show me before posting" selects confirm;
"post directly" or "post them if verified" selects post. Record the source and
pass the effective policy to the resolver. A later "post these three" approves
only that previewed batch; it is not standing permission to publish new findings
on later rounds. Carry an explicitly ongoing post policy through continuations
of the same target until the user changes it. A fresh review request defaults to
draft unless its request carries publication authorization. If directions actually
conflict, keep the drafts local and clarify before publishing.

When delegating an entire review, pass the initiating request and effective comment
policy to its orchestrator. Analytical workers return evidence and never publish.
Dispatch's internal review defaults to draft; do not infer posting from delivery work.

## Delegated review

Walkthrough discussion and review-comment publication have separate authorization.
Carry the [comment policy](#comment-policy) and its
authorization source into delegated review orchestrators. For confirm mode, show
the full batch in the conversation/report before using a native question tool;
do not squeeze comment bodies into choice labels or require one approval per item.
For post mode, honor existing authorization without an extra confirmation.
