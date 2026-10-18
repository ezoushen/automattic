---
name: review
description: "Review a branch or PR within agreed scope; draft, preview or post comments, with optional repairs and E2E verification."
disable-model-invocation: true
argument-hint: "<branch|PR-number|PR-URL> [--autofix] [--comments draft|confirm|post] [--base <ref>]"
---

# review

First read [runtime bootstrap](../../bootstrap.md) and the host session part.
Run the [shared review procedure](workflow.md) with the user's target and flags.
This public command remains user-invoked; dispatch and an authorized walkthrough
handoff use the same procedure without calling this command through Skill.
For guided explanation and discussion before assessment, use
[walkthrough](../walkthrough/SKILL.md).
