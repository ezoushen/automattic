# Composable show-me

A maintained adaptation of [HumanLayer show-me](https://github.com/humanlayer/skills/tree/main/plugins/show-me),
under its [MIT license](LICENSE). Source: show-me 1.0.1 at HumanLayer skills commit
`ca7c8088db69e315a8b2deea43820270457f8f3c`. Upstream supplies the visual vocabulary;
Automattic separates it from the manual entry so explicit commands can share it.

[presentation.md](presentation.md) is the single presentation source. Automattic's
brief, walkthrough and setup-automattic read it directly; [skills/show-me/SKILL.md](skills/show-me/SKILL.md) preserves
the manual show-me command and its invocation policy. Reading this shared reference
is ordinary composition, not invocation of a disabled skill after a tool refusal.
The caller's scope controls whether files may be created.

These guided skills use the bundled reference without an extra plugin installation.
To expose the standalone command, link this edition's `skills/show-me` directory
into the host's skill directory, or load this directory as a Claude plugin.
Preserve unrelated installations and replace only a verified show-me entry. Use
one edition per host. For development, link the source instead of copying it and
reload the host's skills/plugins after changing the entry.
Use the command exposed by the host's catalog: the plugin entry is
`/show-me:show-me` in Claude and `$show-me:show-me` in Codex. A standalone Claude
skill link also exposes `/show-me`; both reach the same presentation source.

When updating from upstream, compare its skill body with `presentation.md`, retain
license/attribution, and keep the manual wrapper thin. Verify all consumers
reach this reference and retain their invocation/export boundaries. Update the
source revision here; implementation history belongs in journals or Git.
