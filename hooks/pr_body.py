#!/usr/bin/env python3
"""PreToolUse hook: `gh pr create` and `gh pr edit` publish only a linted description.

The PR rules live in standards/pr.md, which an agent working outside `/automattic:pr`
never reads. This hook brings them to the moment of publication. Set
AUTOMATTIC_PR_HOOK=off to disable the check.
"""
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import sys

ROOT = Path(__file__).resolve().parent.parent
GUIDE = ROOT / 'standards/pr.md'
SEPARATORS = {';', '&&', '||', '|', '&', '(', ')'}
INLINE = ('--body', '-b', '--fill', '--fill-first', '--fill-verbose')
FILE = ('--body-file', '-F')
WRAPPERS = {'do', 'then', 'else', '{', '!', 'time', 'command', 'env', 'export', 'exec', 'nohup'}
INTERPRETERS = {'python', 'python3', 'node', 'ruby', 'perl', 'bash', 'sh', 'zsh'}
ASSIGNMENT = re.compile(r'[A-Za-z_][A-Za-z0-9_]*=')
HEREDOC = re.compile(r'(?<!<)<<(?!<)-?\s*([\'"]?)([A-Za-z_][A-Za-z0-9_]*)\1')
VARIABLE = re.compile(r'\$(?:([A-Za-z_][A-Za-z0-9_]*)|\{([A-Za-z_][A-Za-z0-9_]*)\})')


def linter():
    spec = importlib.util.spec_from_file_location('lint_pr_body', ROOT / 'scripts/lint_pr_body.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.lint


def expand(word, variables):
    """Substitute $NAME and ${NAME} set earlier in the command; leave unknown ones in place."""
    return VARIABLE.sub(lambda match: variables.get(match.group(1) or match.group(2), match.group(0)), word)


def tokenize(text):
    lexer = shlex.shlex(text, posix=True, punctuation_chars=';&|()')
    lexer.whitespace_split = True
    return list(lexer)


def logical_lines(command):
    """Yield (tokens, heredoc bodies) per logical line, with the bodies cut out and quoted newlines joined."""
    lines, pending, bodies, index = command.replace('\\\n', ' ').split('\n'), '', [], 0
    while index < len(lines):
        line, index = lines[index], index + 1
        for match in HEREDOC.finditer(line):
            end = next((i for i in range(index, len(lines)) if lines[i].strip() == match.group(2)), None)
            if end is None:
                continue  # No delimiter line: a quoted `<<`, not a heredoc.
            bodies.append(''.join(text + '\n' for text in lines[index:end]))
            index = end + 1
        try:
            tokens = tokenize(pending + line)
        except ValueError:
            pending += line + '\n'  # An open quote continues on the next line.
            continue
        yield tokens, bodies
        pending, bodies = '', []


def resolve(text, cwd):
    """Return the absolute path a literal word names, or None when the hook cannot know it."""
    text = os.path.expanduser(text)
    if '$' in text or '`' in text or text in ('', '-') or not (os.path.isabs(text) or cwd):
        return None
    return os.path.normpath(os.path.join(cwd, text))


def changes(words, stdin):
    """Yield (path word, new content or None when unknowable) for each file a simple command may write."""
    redirects = [(words[i], words[i + 1]) for i in range(len(words) - 1) if words[i] in ('>', '>>')]
    redirects += [(word[:2] if word.startswith('>>') else '>', word.lstrip('>'))
                  for word in words if word.startswith('>') and word.strip('>')]
    for operator, target in redirects:
        known = words[:1] == ['cat'] and operator == '>' and stdin is not None
        yield target, stdin if known else None
    edits_in_place = words[:1] in (['sed'], ['perl']) and any(word.startswith('-i') for word in words)
    script_on_stdin = words[:1] and words[0] in INTERPRETERS and '-' in words[1:]
    if edits_in_place or script_on_stdin or words[:1] == ['tee']:
        yield from ((word, None) for word in words[1:] if not word.startswith('-'))


def unwrap(words):
    """Drop keywords and wrappers that precede the command they run."""
    while words and words[0] in WRAPPERS:
        words = words[1:]
    return words


def pr_commands(command, cwd):
    """Yield (arguments, working directory, files written so far, heredoc stdin) for each `gh pr create|edit`."""
    variables, written, subshells = {}, {}, []
    for tokens, bodies in logical_lines(command):
        start = 0
        for index, token in enumerate(tokens + [';']):
            if token not in SEPARATORS and index < len(tokens):
                continue
            words = [expand(word, variables) for word in tokens[start:index]]
            start = index + 1
            words = unwrap(words)
            assignments = 0
            while assignments < len(words) and ASSIGNMENT.match(words[assignments]):
                assignments += 1
            if assignments == len(words):
                variables.update(word.split('=', 1) for word in words)
            words = unwrap(words[assignments:])
            heredocs = [word for word in words if word.startswith('<<') and not word.startswith('<<<')]
            stdin = bodies.pop(0) if heredocs and bodies else None
            if words[:1] == ['cd']:
                cwd = resolve(words[1] if len(words) > 1 else '~', cwd)
            elif words[:2] == ['gh', 'pr'] and len(words) > 2 and words[2] in ('create', 'edit'):
                yield words[3:], cwd, written, stdin
            else:
                for target, content in changes(words, stdin):
                    if resolve(target, cwd):
                        written[resolve(target, cwd)] = content
            if token == '(':
                subshells.append(cwd)
            elif token == ')' and subshells:
                cwd = subshells.pop()  # A `cd` inside a subshell ends with it.


def options(args):
    """Return {flag: value} for the body flags, with --flag=value split."""
    found = {}
    for index, arg in enumerate(args):
        flag, _, value = arg.partition('=') if arg.startswith('--') else (arg, '', '')
        if flag in INLINE + FILE:
            if not value and flag not in ('--fill', '--fill-first', '--fill-verbose'):
                value = args[index + 1] if index + 1 < len(args) else ''
            found[flag] = value
    return found


def problems(args, cwd, written, stdin):
    found = options(args)
    if any(flag in found for flag in INLINE):
        return ['write the description to a file and pass it with --body-file; inline or --fill bodies '
                'cannot be linted or kept as the source of truth']
    path_text = next((found[flag] for flag in FILE if flag in found), None)
    if path_text is None:
        return []
    path = resolve(path_text, cwd)
    if path_text == '-' and stdin is not None:
        body = stdin
    elif path in written and written[path] is not None:
        body = written[path]
    elif path and path not in written and os.path.isfile(path):
        body = Path(path).read_text(errors='replace')
    else:
        return [f'--body-file "{path_text}" is not a file the hook can read before the command runs; write it '
                'in an earlier command, then pass its literal path so the body can be linted']
    return linter()(body)[0]  # Titles follow each repository's own convention.


def main():
    if os.environ.get('AUTOMATTIC_PR_HOOK') == 'off':
        return
    try:
        event = json.load(sys.stdin)
        if event.get('tool_name') != 'Bash':
            return
        command = (event.get('tool_input') or {}).get('command') or ''
        if 'gh' not in command:
            return
        errors = [error for found in pr_commands(command, event.get('cwd') or os.getcwd())
                  for error in problems(*found)]
    except Exception:
        return  # A broken check must never block work.
    if errors:
        reason = (f'Before publishing a PR description, read {GUIDE} and fix: ' + '; '.join(errors) +
                  f'. Check the file with `python3 {ROOT}/scripts/lint_pr_body.py <file>`.')
        print(json.dumps({'hookSpecificOutput': {
            'hookEventName': 'PreToolUse', 'permissionDecision': 'deny', 'permissionDecisionReason': reason}}))


if __name__ == '__main__':
    main()
