# Research a question

Read when a plan, review or blocked ticket depends on a fact nobody has checked:
align, review and dispatch use it. The procedure gathers evidence; the caller decides
what to do with it.

## Rules

- Read primary sources: the project's own code, configuration and data, the official
  documentation, specifications and first-party interfaces of what it depends on.
  A secondary write-up is a lead to its source, not evidence.
- Cite every claim to the source that owns it: a path and line, a command and its
  output, or a link with the version it describes. A claim with no source is marked
  unverified, never stated as fact.
- Measure every real consumer, not one. When a fact is about how something is used,
  find all its callers, readers, inputs or users in scope and check each; a single
  sample shows only that one case. Name the ones that could not be checked.
- Settle every available fact before asking the user to choose. A question to the
  user carries only what the evidence cannot decide, [with context](../explain/ask.md).
- No separate fact-checker is mandatory. The researcher's citations are the check;
  the caller adds an independent verification only where a wrong fact would be costly.

## Run

Run it as a background worker so the caller keeps working while it reads, under
[launching a worker](../workers/launch.md). The worker reads and runs read-only
commands; it changes no code, configuration or tracker state.

Save the findings where the project already keeps such notes, following its
convention; with none, use the effort's `.scratch/<slug>/` folder and say where.
Return the file's path, the answer in a few lines, and the open points with what
each would take to settle.
