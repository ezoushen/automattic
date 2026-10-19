---
name: writing-agent-docs
description: Checks and guides changes to the agent-facing Markdown in this repository (skills, agents, jobs, harness docs and adapters). Use when adding, splitting, moving or editing these docs or their links, and before committing such changes.
---

# Writing agent docs

Agents load these files at run time, so their size, links and wording are behavior.
Run the checker on every change, then apply the [practices](#practices) to what it reports.

Contents:
- [Run the checker](#run-the-checker)
- [Fix what it reports](#fix-what-it-reports)
- [Extend the architecture](#extend-the-architecture)
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
scripts. The pre-commit hook runs it with `--changed HEAD`; the pre-push hook runs the
whole-repository check on each pushed commit, as does `tests/test_cross_harness.py`.

[config.json](config.json) says which files are agent docs, which files' links
count, where code names doc paths, the byte budget and the recorded debt.
[architecture.json](architecture.json) holds the module architecture: ordered levels
(top may depend on lower ones and on itself, never on a sibling or a higher level),
which files each module owns, the first-read budget and the debt for that contract.
Debt entries only shrink: one entry covers every link between its two files, a violation
between any other pair is an error, and a fixed one is `stale-debt`.
A doc, or a script or hook under `owned_code`, that no module owns is `unmapped`, so a new
folder needs a module before its files pass.

`tests/test_import_direction.py` applies the same levels to the imports of `scripts/`
and `hooks/`, including imports inside functions. To prove a restructuring lost nothing
run `check_fold.py --base <commit>`: it reports every body line (link targets ignored)
and every skill, agent, job, kind, decision family, hook event and script command that
differs from the base; list deliberate edits in a JSON file passed with `--allow`.

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
| `direction` | A link goes to a higher level, a sibling module or another skill | Move the shared text below its users, or invert the link |
| `cycle` | Modules link each other in a loop | Break the loop at the link `direction` also reports |
| `first-read` | Bootstrap, host session, skill and the docs its `First read:` paragraph links, over the budget | Move detail out of those docs or the bootstrap |
| `first-read-line` | A `SKILL.md` has no line starting `First read:` | Add a paragraph starting `First read:` that links the docs the skill reads before acting |
| `host-shape` | A folder under `hosts/` that does not hold exactly `session.md` and `workers.md` | Move other text to the runtime doc that owns it |
| `shared-section` | A section linked from 3+ files in other modules | Make it its own file |
| `unmapped` | No module in architecture.json owns the doc | Add its path to the owning module |
| `positional` | `above` or `below` that may point at moved text | Link or name the target instead |
| `stale-name` | Text names a `.md` file that exists nowhere | Link the doc that now holds it, or add a generic project name to `known_names` |
| `dated`, `backslash`, `person` | Time-bound wording, Windows path, first/second-person description | Reword |
| `description-budget` | Skill descriptions over the local budget in config | Shorten descriptions |

## Extend the architecture

Layers, top first: skills and hooks; `bootstrap.md`; flows (`flows/<flow>/`);
`agents/`; `standards/`; `hosts/`; `runtime/` modules; add-ons. A doc or script depends
on its own module or a lower level, never on a sibling or a higher level, and a skill
links no other skill. **Strict:** these direction rules, the first-read budget, the host
shape and unmapped docs are errors with no recorded debt. **Room:** a new module
joins `architecture.json` in a level of its own or beside siblings that need not link
each other, so the order grows without loosening a rule. Run the checker and
`tests/run_all.py` after each addition.

- **Add a host:** create `hosts/<host>/` holding exactly `session.md` (read at session
  start) and `workers.md` (read when launching); add the name to `HARNESSES` in
  `scripts/agent_models.py`, register its session hint in the bootstrap or hook, and
  never link the host files from shared docs (the `hosts` module is `unlinked`).
- **Add an executor:** write `hosts/executors/<type>.md` and list it in that folder's
  README; shared docs name an executor only through the configuration.
- **Add an agent:** write `agents/<name>.md` with permissions, principles ending in
  `shown by:` and core skills; the agent holds only what every one of its jobs shares.
- **Add a job:** write `flows/<flow>/jobs/<job>.md` naming its agent, inputs, finish
  line and return; the name is unique across flows. Detail only some jobs need
  belongs here, not in the agent.
- **Add a kind:** write `standards/kinds/<kind>.md` and link it from the agent or
  job that applies it.
- **Add a standard:** write `standards/<name>.md`, mapped to the `standards` module,
  and link it from the agents and flows that follow it.
- **Add a flow:** create `flows/<flow>/` with a procedure and a folder index, add the
  module to `architecture.json` at its level, name the flow in the pipeline map, and
  keep its skill a thin entry that links the procedure.

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
possible: skill → bootstrap and host session part → leaf.

**Link the file you mean.** Retarget a link when you move its text, and re-read the
sentence around it: a link that used to name a whole file must now name the leaf
that holds what the sentence promises. When one old link covers two leaves, link
both. Every leaf needs an inbound link from a skill, agent, job, adapter or folder index.

**Move text, don't rewrite it, when restructuring.** Move whole sections and verify
every old body line is still present. Then search the moved text for `above`,
`below`, `this file` and old file names; those break silently.

**Keep an agent file to what all its jobs share.** `agents/<name>.md` holds
permissions, principles and core skills only. Every line must hold for every job of
that agent; a rule that only some jobs need belongs in their
`flows/<flow>/jobs/<job>.md`. End each principle with `shown by:` and the
observable evidence that it was followed. State rules directly, without identity
phrasing such as "you are" or "act as an expert". `tests/test_agent_definitions.py`
checks the structure.

**Keep host differences in adapters.** Shared docs state host-neutral rules; how a
host reads files, waits or launches workers belongs in `hosts/<host>/`: `session.md`
(read at session start) and `workers.md` (read when launching).

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
