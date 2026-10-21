#!/usr/bin/env python3
"""PreToolUse hook: an Automattic read-only subagent in Claude Code writes only under the reports.

Claude Code names the subagent a tool call runs in (`agent_type`). For `automattic:<agent>`, or a generated
`automattic-<agent>-<digest>` profile, whose agent declares `writes: none`, it denies an Edit, Write or
NotebookEdit of a file outside the main checkout's .scratch/<slug>/reports/ and, for a subagent registered as an
attempt's native_session (its agent_id) in a workers.sqlite there, that attempt's worktree, whose temporary
experiment edits collection's restored-worktree check guards. It also denies a Bash command that clearly writes such
a file: a `>`, `>>`, `>|`, `&>` or `&>>` redirect, or `tee`, to a literal path, relative ones following the
command's own `cd`. Collection's read-only worktree check cannot see a write outside the worktree, since a
subagent's transcript carries its coordinator's directory. A check that cannot run denies the call.

Not caught: a target known only at run time (`$VAR`, `$(...)`, globs), `>&` to a file, a shell's `-c` string, an
interpreter or tool that opens files itself (`python -c`, `sed -i`, `cp`, `git`), and MCP tools.
"""
import json
import os
from pathlib import Path
import re
import shlex
import sqlite3
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
    return [path for path in written if path and not path.startswith('/dev/')]


def registered_worktrees(main, agent_id):
    """The worktrees of the attempts registered with this subagent's agent_id as their native_session, read-only."""
    if not agent_id:
        return []
    found = []
    for state in sorted(main.glob('.scratch/*/reports/workers.sqlite')):
        db = sqlite3.connect(f'{state.as_uri()}?mode=ro', uri=True, timeout=5)
        try:
            found += [saved['worktree'] for saved in yield_gate.lifecycle().attempts(db)
                      if saved.get('native_session') == agent_id]
        finally:
            db.close()
    return sorted(set(found))


def outside(paths, cwd, agent_id):
    """(main checkout, the subagent's registered worktrees, the paths resolved against cwd that lie outside both the
    main checkout's reports and those worktrees)."""
    main = yield_gate.main_checkout(cwd)
    if main is None:
        raise RuntimeError(f'{cwd} is in no git checkout, so its reports cannot be located')
    worktrees = registered_worktrees(main, agent_id)
    allowed = [Path(os.path.realpath(worktree)) for worktree in worktrees]
    resolved = [os.path.realpath(os.path.join(cwd, os.path.expanduser(path))) for path in paths]
    return main, worktrees, [path for path in resolved if not in_reports(path, main)
                             and not any(Path(path).is_relative_to(worktree) for worktree in allowed)]


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
        root, worktrees, written = outside(paths, cwd, event.get('agent_id')) if paths else (None, [], [])
    except Exception as error:  # A check that cannot run denies the call.
        deny(f'{event["agent_type"]} is read-only (writes: none) and this write could not be checked: {error}')
        return
    if written:
        own = ''.join(f' and its registered worktree {worktree}' for worktree in worktrees)
        deny(f'{event["agent_type"]} is read-only (writes: none): it writes only its report under '
             f'{root}/.scratch/<slug>/reports/{own}, and {", ".join(written)} is outside them '
             f'({ROOT}/agents/{agent}.md).')


def deny(reason):
    print(json.dumps({'hookSpecificOutput': {
        'hookEventName': 'PreToolUse', 'permissionDecision': 'deny', 'permissionDecisionReason': reason}}))


if __name__ == '__main__':
    main()
