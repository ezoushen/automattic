---
name: writing-agent-docs
description: Checks and guides changes to the agent-facing Markdown in this repository (skills, roles, harness docs and adapters). Use when adding, splitting, moving or editing these docs or their links, and before committing such changes.
---

# Writing agent docs

Agents load these files at run time, so their size, links and wording are behavior.
Run the checker on every change, then apply the [practices](#practices) to what it reports.

Contents:
- [Run the checker](#run-the-checker)
- [Fix what it reports](#fix-what-it-reports)
- [Practices](#practices)
- [Sources](#sources)

## Run the checker

```sh
python3 .agents/skills/writing-agent-docs/check_docs.py --changed main   # while changing docs
python3 .agents/skills/writing-agent-docs/check_docs.py                  # whole repository
```

Errors exit 1, invalid input (config, base or repository) exits 2; warnings are
smells to judge. `--changed <base>` limits per-file rules to files changed since that
base, plus untracked files, and flags references such as `the example above` on
added lines; renamed files keep their old lines. Links, anchors, orphans and code paths are always checked repo-wide,
because moving a file breaks the files that link it. `--json` prints findings for
scripts. `tests/test_cross_harness.py` runs the whole-repository check.

[config.json](config.json) says which files are agent docs, which files' links
count, where code names doc paths, the byte budget and the recorded debt.

## Fix what it reports

| Code | Meaning | Fix |
|---|---|---|
| `size` | Doc over 12 KiB | Split it by reader, not by line count |
| `debt` | Over budget or missing contents, recorded in config | Shrink it when you touch it; lower the recorded size when the message says so; never raise it to make room |
| `stale-debt` | A recorded debt no longer applies | Remove the entry |
| `contents` | Over 100 lines with 3+ sections, no exact `Contents:` list | Add or update the list right after the title |
| `skill-lines` | `SKILL.md` body over 500 lines | Move detail into files it links |
| `frontmatter` | Name or description outside the skill format | Fix the field |
| `link`, `anchor` | Target file or heading missing | Retarget to the file and section that hold the text |
| `orphan` | No doc or code links it | Link it where a reader needs it, or delete it |
| `code-path` | Code names a doc that does not exist | Update the path in the code |
| `positional` | `above` or `below` that may point at moved text | Link or name the target instead |
| `stale-name` | Text names a `.md` file that exists nowhere | Link the doc that now holds it, or add a generic project name to `known_names` |
| `dated`, `backslash`, `person` | Time-bound wording, Windows path, first/second-person description | Reword |
| `description-budget` | Skill descriptions over the local budget in config | Shorten descriptions |

## Practices

**Size every doc for one read.** A link names a file, and neither host can jump to
an anchor, so a doc should be small enough to read whole. Codex shows tool output
only up to its limit (`tool_output_token_limit`; 10k tokens for Codex models per
the maintainers, 8,000 on this machine) and drops the middle beyond it. Claude Code
shows a shell output over about 30 KB only as a saved file plus a preview, observed
in this repository's transcripts. Measured here before the harness split: a quarter
of Codex reads of the large shared docs came back middle-truncated, and Claude agents
mostly read guessed line windows of them. 12 KiB is about 3k tokens, so two or three
docs fit one Codex read.

**Split by reader, then by linked section.** Separate run-time rules from setup,
migration, troubleshooting and experiments. A section that many files link becomes
its own file, so a link names the whole read. Keep entry points to one hop where
possible: skill → bootstrap and adapter → leaf.

**Link the file you mean.** Retarget a link when you move its text, and re-read the
sentence around it: a link that used to name a whole file must now name the leaf
that holds what the sentence promises. When one old link covers two leaves, link
both. Every leaf needs an inbound link from a skill, role, adapter or folder index.

**Move text, don't rewrite it, when restructuring.** Move whole sections and verify
every old body line is still present. Then search the moved text for `above`,
`below`, `this file` and old file names; those break silently.

**Keep host differences in adapters.** Shared docs state host-neutral rules; how a
host reads files, waits or launches workers belongs in `harnesses/<host>/`.

**Write skill frontmatter to the format.**
- `name`: at most 64 lowercase letters, digits and hyphens, without "anthropic" or "claude".
- `description`: at most 1,024 characters, no XML tags, third person. Say what it
  does and when to use it, front-loading the trigger words.
- Codex fits its initial skill list into 2% of the context window (8,000 characters
  when the window is unknown; `skills.max_context_tokens` raises it to at most
  10,000 tokens) and shortens descriptions first when over. Every installed skill
  shares that list, so keep each description short. `description_budget` in config
  is a local warning threshold, not a host limit.

**Write for a model that already knows the domain.** State only what it would not
know, with one term per concept: instruction-following declines as more
instructions are loaded at once (IFScale). Avoid time-bound wording, and use forward slashes.
Give one default with an escape hatch rather than a menu. Put deterministic checks
in scripts that agents run, not prose they interpret.

**Measure with real use.** Unit tests prove structure, not reading behavior. After
a batch of doc changes, observe how each host actually reads them: truncated
outputs, guessed line ranges, links not followed. Compare with the previous commit
on the same host.

## Sources

- [Anthropic: Skill authoring best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)
- [OpenAI: Build skills for Codex](https://learn.chatgpt.com/docs/build-skills)
- [OpenAI: Codex configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference)
- [openai/codex #6426: token-based output truncation](https://github.com/openai/codex/issues/6426)
- [How Many Instructions Can LLMs Follow at Once? (IFScale)](https://arxiv.org/abs/2507.11538)
