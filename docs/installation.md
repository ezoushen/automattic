# Installation

Requirements: Python **3.9+**, Git, Bash, and a Unix platform with `fcntl` (macOS/Linux).
The plugin needs no other skill package: its methods ship in this tree.

This is the maintained source tree. Package-manager cache copies are deployments;
make changes here. Development symlinks expose those changes without maintaining
separate copies of skills or scripts. Avoid enabling two Automattic releases in the
same session.

## Claude Code

To try the source without replacing the installed plugin:

```sh
claude --plugin-dir /absolute/path/to/automattic
```

Development installation: `automattic@automattic-dev` is enabled, with
`~/.claude/plugins/cache/automattic-dev/automattic/0.3.0` symlinked to this
workspace. Edit here, then run `/reload-plugins` in an existing Claude session to
refresh the hook inventory and skill instructions; new sessions read the current
files. No reinstall is needed. A marketplace update to another version can select a
new cache directory; relink that entry when changing the installed version. After
changing the Claude manifest, check `claude plugin list` for loading errors before
reloading Automattic.

## Codex

Codex's local catalog is `.agents/plugins/marketplace.json`:

```sh
codex plugin marketplace add /absolute/path/to/automattic
codex plugin add automattic@automattic-dev
```

The installer copies a snapshot. For development on this machine,
`~/.codex/plugins/cache/automattic-dev/automattic/0.3.0` is a real directory whose
workflow directories are symlinks into this checkout, including `skills`, `agents`,
`runtime`, `standards`, `hosts`, `hooks`, `scripts`, `schemas` and `benchmarks`, and
the top-level `bootstrap.md` file is a symlink too. Its `.codex-plugin/` directory and
small `plugin.json` registration are regular files/directories, copied from this
tree's Codex manifest; the portable root `plugin.json` is omitted from that local
wrapper: Codex 0.163 refuses the whole plugin, skills and hooks included, when the root
`plugin.json` is a symlink, and logs only `missing or invalid plugin.json`. This selects Codex's registration, including its SessionStart, PreToolUse and Stop hooks.
The installed scanner requires a real version directory and manifest. When setting
up elsewhere, replace only a verified Automattic snapshot with this wrapper and
links; preserve unrelated installations.

Changes within linked directories need no copying or reinstall. Start a new Codex
session to refresh loaded instructions and hooks; existing conversations may retain
earlier instructions. Review any native hook-trust prompt. A reinstall or version
change may replace the links; verify them afterward. Refresh the small registration
when the Codex manifest changes, and add a link when introducing a new top-level
package entry before starting a session. Check installation with
`codex plugin list --marketplace automattic-dev --json` and the
[native readers](development.md#native-checks). Also check runtime `skills/list` and
`hooks/list`: a listed installation alone does not prove that its skills or hook were
loaded. Its required presentation reference is packaged with the plugin.

## Pi

Development installation uses two symlinks to this source tree:

```sh
mkdir -p ~/.pi/agent/skills ~/.pi/agent/extensions
ln -s /absolute/path/to/automattic/skills ~/.pi/agent/skills/automattic
ln -s /absolute/path/to/automattic/hosts/pi/bootstrap.ts ~/.pi/agent/extensions/automattic.ts
```

Keep an existing matching symlink; do not overwrite a different installation. For
the earlier link to this repository's root, retarget only that verified development
symlink to `skills/`. Pi discovers skills recursively but treats a folder holding
`SKILL.md` as one skill, so a command's other docs and jobs never load as skills;
restricting the link prevents optional add-on skills elsewhere in the repository from
loading. Re-point an extension symlink that does not target `hosts/pi/bootstrap.ts`.

Run `/reload` in Pi, then `/skill:dispatch <scope> --autofix` or
`/skill:review walkthrough <target>`. The extension supplies the bootstrap and Pi's
session part before each turn; it registers no tools or commands. With explicit
extension loading disabled, supply `harness=pi` when invoking a phase instead.
Planning/review can run without delegation where the shared procedure allows it;
dispatch requires the installed `subagent` tool (pi-subagents). See the
[Pi session part](../hosts/pi/session.md).

## Runtime references

[OpenAI plugin packaging](https://developers.openai.com/plugins/build/plugins),
[Codex hooks](https://learn.chatgpt.com/docs/hooks),
[Codex subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents),
[Claude plugin reference](https://code.claude.com/docs/en/plugins-reference),
[Claude hooks](https://code.claude.com/docs/en/hooks).
