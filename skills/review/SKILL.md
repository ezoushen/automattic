---
name: review
description: "Review a branch or PR within agreed scope, or first walk through it to understand it; draft, preview or post comments, with optional repairs and E2E verification."
disable-model-invocation: true
argument-hint: "[walkthrough] <branch|PR-number|PR-URL> [--autofix] [--comments draft|confirm|post] [--base <ref>]"
---

# review

First read: [runtime bootstrap](../../bootstrap.md), the host session part, [review](../../flows/review/review.md), [walkthrough](../../flows/review/walkthrough.md).
Run the [shared review procedure](../../flows/review/review.md) with the user's target and flags.
A first argument `walkthrough` selects the [walkthrough procedure](../../flows/review/walkthrough.md)
and is not forwarded: explain and discuss the remaining target first, then continue into
review only when the user asks. A branch named `walkthrough` is given as `refs/heads/walkthrough`.
This public command remains user-invoked; dispatch and an authorized walkthrough
handoff use the same procedure without calling this command through Skill.
