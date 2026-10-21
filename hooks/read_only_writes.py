#!/usr/bin/env python3
"""PreToolUse hook: an Automattic read-only subagent in Claude Code leaves the user's checkouts unchanged.

Claude Code names the subagent a tool call runs in (`agent_type`). For `automattic:<agent>`, or a generated
`automattic-<agent>-<digest>` profile, whose agent declares `writes: none`, it denies an Edit, Write or
NotebookEdit of a file inside the main checkout or one of its worktrees (the session cwd's git common dir family),
except under the main checkout's .scratch/<slug>/reports/ and in the `worktree:` the subagent's assignment names,
whose temporary experiment edits collection's restored-worktree check guards. The assignment is the first user
message of the subagent's own transcript, <session transcript without .jsonl>/subagents/agent-<agent_id>.jsonl,
present from its first tool call, so a write before registration is judged the same. Anything outside the family
(/tmp, the scratchpad, an isolated copy) is allowed, and so is everything for a session outside any checkout. It
also denies a Bash command that clearly writes such a file: a `>`, `>>`, `>|`, `&>` or `&>>` redirect, or `tee`, to
a literal path, relative ones following the command's own `cd`, real paths resolved. Collection's read-only worktree
check cannot see a write outside the worktree, since a subagent's transcript carries its coordinator's directory.
The reports and paths outside the family are decided before anything else is read; a check that cannot run for a
path inside the family denies the call.

Not caught: a target known only at run time (`$VAR`, `$(...)`, globs), `>&` to a file, `<>`, escaped spaces, `#`
inside a word, a shell's `-c` string, `sudo tee` or `xargs tee`, a `cd` that does not run (`false && cd x`), a symlink
the same command creates, an interpreter or tool that opens files itself (`python -c`, `sed -i`, `cp`, `git`), and
MCP tools.
"""
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
import agent_defs  # noqa: E402
import pr_body  # noqa: E402
import yield_gate  # noqa: E402

FILE_TOOLS = {'Edit': 'file_path', 'Write': 'file_path', 'NotebookEdit': 'notebook_path'}
REDIRECTS = {'>', '>>', '>|', '&>', '&>>'}
# Operators whose next word is not a file this command writes: input, heredoc delimiters and fd copies.
SKIPS_NEXT = {'<', '<<', '<<-', '<<<', '>&', '<&', '<>'}
ASSIGNED = re.compile(r'^worktree:[ \t]*(.+?)[ \t]*$', re.M)


def read_only(agent_type):
    """The Automattic agent a subagent type names when that agent declares `writes: none`, else None."""
    named = re.fullmatch(r'automattic(?::([a-z0-9-]+)|-([a-z0-9-]+)-[0-9a-f]{12})', agent_type or '')
    agent = named and (named.group(1) or named.group(2))
    definition = agent and agent_defs.load(ROOT)['agents'].get(agent)
    return agent if definition and definition.get('writes') == 'none' else None


def in_reports(path, main):
    """Whether a resolved path lies in some <main>/.scratch/<slug>/reports/."""
    try:
        parts = Path(path).relative_to(Path(os.path.realpath(main / '.scratch'))).parts
    except ValueError:
        return False
    return len(parts) >= 3 and parts[1] == 'reports'


def literal(word, cwd):
    """The absolute path a shell word names when it is a literal, else None: a quoted or unquoted word with no
    expansion, relative ones resolved against cwd when it is known."""
    if not word or any(char in word for char in '$`*?[{'):
        return None
    try:
        [text] = shlex.split(word)
    except ValueError:
        return None
    text = os.path.expanduser(text)
    if not (os.path.isabs(text) or cwd):
        return None
    return os.path.join(cwd or '', text)


def tokens(command):
    """The command's shell tokens, quotes kept, heredoc bodies cut out and each line ended by `;`."""
    lines, kept, index = command.replace('\\\n', ' ').split('\n'), [], 0
    while index < len(lines):
        line, index = lines[index], index + 1
        kept.append(line)
        for match in pr_body.HEREDOC.finditer(line):
            end = next((i for i in range(index, len(lines)) if lines[i].strip() == match.group(2)), None)
            if end is not None:
                index = end + 1
    found, pending = [], ''
    for line in kept:
        lexer = shlex.shlex(pending + line, posix=False, punctuation_chars=True)
        lexer.whitespace_split = True
        try:
            found += list(lexer) + [';']
            pending = ''
        except ValueError:
            pending += line + '\n'  # An open quote continues on the next line.
    return found


def shell_writes(command, cwd):
    """The literal paths a Bash command writes by redirection or `tee`, following its own `cd`."""
    written, words, subshells, at, items = [], [], [], 0, tokens(command)
    while at < len(items):
        token, at = items[at], at + 1
        operator = token != '((' and not token.strip('();<>|&')
        if token in REDIRECTS and at < len(items):
            written.append(literal(items[at], cwd))
            at += 1
        elif token in SKIPS_NEXT:
            at += 1
        elif token in ('((', '[['):  # Arithmetic and tests compare with `>`; they write nothing.
            close = '))' if token == '((' else ']]'
            at = next((i + 1 for i in range(at, len(items)) if items[i] == close), len(items))
        elif not operator:
            words.append(token)
        if operator:
            words = pr_body.unwrap(words)
            while words and pr_body.ASSIGNMENT.match(words[0]):
                words = pr_body.unwrap(words[1:])
            if words[:1] == ['cd']:
                cwd = literal(words[1] if len(words) > 1 else '~', cwd)
            elif words and Path(words[0]).name == 'tee':
                written += [literal(word, cwd) for word in words[1:] if not word.startswith('-')]
            words = []
            if '(' in token:
                subshells.append(cwd)
            elif ')' in token and subshells:
                cwd = subshells.pop()  # A `cd` inside a subshell ends with it.
    return [path for path in written if path]


def checkouts(main):
    """The main checkout and every worktree of its repository, real paths, the main checkout first."""
    result = subprocess.run(['git', '-C', str(main), 'worktree', 'list', '--porcelain'], capture_output=True,
                            text=True, timeout=5, check=True)
    return [Path(os.path.realpath(line[len('worktree '):])) for line in result.stdout.splitlines()
            if line.startswith('worktree ')]


def assigned_worktree(event):
    """The real path of the `worktree:` the subagent's assignment names, or None when it cannot be read: the first
    user message of its own transcript, which Claude Code keeps in the session's directory."""
    transcript, agent_id = event.get('transcript_path') or '', event.get('agent_id')
    if not (agent_id and transcript.endswith('.jsonl')):
        return None
    try:
        with open(Path(transcript[:-len('.jsonl')]) / 'subagents' / f'agent-{agent_id}.jsonl') as rows:
            first = next(row for row in map(json.loads, rows) if row.get('type') == 'user')
        content = first['message']['content']
        text = content if isinstance(content, str) else '\n'.join(block.get('text', '') for block in content)
    except (OSError, ValueError, StopIteration, KeyError, TypeError, AttributeError):
        return None
    match = ASSIGNED.search(text)
    return Path(os.path.realpath(match.group(1))) if match else None


def protected(paths, cwd, event):
    """(main checkout, assigned worktree, the paths a read-only agent may not write): those inside the main checkout or
    one of its worktrees, outside its reports and the assigned worktree. The reports and paths outside those checkouts
    are decided first, so no later lookup can deny them."""
    main = yield_gate.main_checkout(cwd)
    if main is None:
        return None, None, []  # A session outside any checkout protects none.
    resolved = [os.path.realpath(os.path.join(cwd, os.path.expanduser(path))) for path in paths]
    held = [path for path in resolved if not in_reports(path, main)]
    family = checkouts(main) if held else []
    held = [path for path in held if any(Path(path).is_relative_to(checkout) for checkout in family)]
    assigned = assigned_worktree(event) if held else None
    if assigned not in family[1:]:  # Only a worktree of the family, never the main checkout itself.
        assigned = None
    return main, assigned, [path for path in held if not (assigned and Path(path).is_relative_to(assigned))]


def main():
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return
    tool, tool_input = event.get('tool_name'), event.get('tool_input') or {}
    agent = tool in (*FILE_TOOLS, 'Bash') and read_only(event.get('agent_type'))
    if not agent:
        return
    cwd = event.get('cwd') or os.getcwd()
    try:
        paths = (shell_writes(tool_input.get('command') or '', cwd) if tool == 'Bash'
                 else [tool_input.get(FILE_TOOLS[tool]) or ''])
        root, assigned, written = protected(paths, cwd, event) if paths else (None, None, [])
    except Exception as error:  # A check that cannot run denies the call.
        deny(f'{event["agent_type"]} is read-only (writes: none) and this write could not be checked: {error}')
        return
    if written:
        own = f' and in its assigned worktree {assigned}' if assigned else ''
        deny(f'{event["agent_type"]} is read-only (writes: none): inside the checkouts it writes only its report under '
             f'{root}/.scratch/<slug>/reports/{own}, and {", ".join(written)} is outside them '
             f'({ROOT}/agents/{agent}.md).')


def deny(reason):
    print(json.dumps({'hookSpecificOutput': {
        'hookEventName': 'PreToolUse', 'permissionDecision': 'deny', 'permissionDecisionReason': reason}}))


if __name__ == '__main__':
    main()
