#!/usr/bin/env python3
"""List added non-doc comment lines as JSON review candidates, not policy verdicts."""
import argparse
import io
import json
from pathlib import Path
import re
import subprocess
import tokenize

PYTHON = {'.py', '.pyi'}
JAVASCRIPT = {'.js', '.jsx', '.mjs', '.cjs', '.ts', '.tsx', '.mts', '.cts'}
SHELL = {'.sh', '.bash', '.zsh'}
PRAGMA = re.compile(
    r'^(?:noqa\b|type:\s|(?:pylint|pyright|mypy|shellcheck|shfmt|sqlfluff):?\s'
    r'|(?:fmt|isort):|(?:eslint|tslint)(?:[-\s:]|$)|@ts-(?:ignore|expect-error|check|nocheck)\b'
    r'|prettier-ignore\b|(?:istanbul|c8|v8)\s+ignore\b|(?:-\*-\s*)?coding[:=]\s*[-\w.]+)')
LICENSE = re.compile(r'\b(?:SPDX-License-Identifier:|Copyright\b|Licensed under\b|MIT License\b)', re.I)
QUOTED = re.compile(r"'(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\"", re.S)
SHELL_QUOTED = re.compile(r"'[^']*'|\"(?:\\.|[^\"\\])*\"", re.S)
JS_TOKEN = re.compile(r'[\w$]+|\+\+|--|[^\s]')
JS_REGEX = re.compile(r'/((?:\\.|\[(?:\\.|[^\]\\\n])*\]|[^/\\\n])+)/[a-z]*')
HEREDOC = re.compile(r'''<<(-?)\s*(?:'([^']+)'|"([^"]+)"|([a-zA-Z_]\w*))''')


def javascript_comments(source, start=0, stop_at_brace=False):
    """Scan JS strings, regex literals and template expressions before comments."""
    index = start
    can_regex = True
    while index < len(source):
        char = source[index]
        if char.isspace():
            index += 1
            continue
        if char == '}' and stop_at_brace:
            return index + 1
        if source.startswith(('//', '/*', '#!'), index):
            block = source.startswith('/*', index)
            end = source.find('*/' if block else '\n', index + 2)
            if end < 0:
                if block:
                    raise ValueError('unterminated JS block comment')
                end = len(source)
            elif block:
                end += 2
            doc = source.startswith('/**', index)
            yield index, end, doc
            index = end
            continue
        if char in "'\"":
            match = QUOTED.match(source, index)
            if not match:
                raise ValueError('unterminated JS string')
            index = match.end()
            can_regex = False
            continue
        if char == '`':
            index += 1
            while index < len(source) and source[index] != '`':
                if source[index] == '\\':
                    index += 2
                elif source.startswith('${', index):
                    index = yield from javascript_comments(source, index + 2, True)
                else:
                    index += 1
            if index >= len(source):
                raise ValueError('unterminated JS template')
            index += 1
            can_regex = False
            continue
        if char == '{' and stop_at_brace:
            index = yield from javascript_comments(source, index + 1, True)
            can_regex = False
            continue
        if char == '/' and can_regex:
            match = JS_REGEX.match(source, index)
            if match:
                index = match.end()
                can_regex = False
                continue
        match = JS_TOKEN.match(source, index)
        token = match.group()
        can_regex = (token in {'return', 'throw', 'case', 'delete', 'typeof', 'void',
                               'yield', 'await', 'in', 'of', 'instanceof'}
                     or not (token[0].isalnum() or token[0] in '_$' or token in {')', ']', '}', '++', '--'}))
        index = match.end()
    if stop_at_brace:
        raise ValueError('unterminated JS template expression')
    return index


def shell_comments(source):
    """Scan shell quoting, escaped hashes, word hashes and here-document bodies."""
    index = 0
    pending = []
    while index < len(source):
        char = source[index]
        if char == '\n' and pending:
            index += 1
            for delimiter, strip_tabs in pending:
                while index < len(source):
                    end = source.find('\n', index)
                    end = len(source) if end < 0 else end
                    line = source[index:end]
                    index = end + 1
                    if (line.lstrip('\t') if strip_tabs else line) == delimiter:
                        break
            pending.clear()
        elif char == '\\':
            index += 2
        elif char in "'\"":
            match = SHELL_QUOTED.match(source, index)
            if not match:
                raise ValueError('unterminated shell string')
            index = match.end()
        elif match := HEREDOC.match(source, index):
            pending.append((next(value for value in match.groups()[1:] if value is not None), bool(match[1])))
            index = match.end()
        elif char == '#' and (index == 0 or source[index - 1] in ' \t\r\n;|&()'):
            end = source.find('\n', index)
            end = len(source) if end < 0 else end
            yield index, end, False
            index = end
        else:
            index += 1


def comments(source, suffix):
    """Yield (start, end, is_doc) spans using full-file lexical context."""
    if suffix in PYTHON:
        offsets = [0]
        for line in source.splitlines(keepends=True):
            offsets.append(offsets[-1] + len(line))
        for token in tokenize.generate_tokens(io.StringIO(source).readline):
            if token.type == tokenize.COMMENT:
                yield (offsets[token.start[0] - 1] + token.start[1],
                       offsets[token.end[0] - 1] + token.end[1], False)
        return
    if suffix in JAVASCRIPT:
        yield from javascript_comments(source)
        return
    if suffix in SHELL:
        yield from shell_comments(source)
        return
    pattern = (r"\$(?P<tag>[a-zA-Z_]\w*|)\$[\s\S]*?\$(?P=tag)\$"
               r"|'(?:''|[^'])*'|\"(?:\"\"|[^\"])*\"|--[^\n]*|/\*[\s\S]*?\*/")
    for match in re.finditer(pattern, source):
        token = match.group()
        if token.startswith(('#', '//', '/*', '--')):
            yield match.start(), match.end(), token.startswith('/**')


def comment_lines(source, suffix):
    """Map plain comment spans to file lines, excluding header notices and pragmas."""
    spans = list(comments(source, suffix))
    header_end = 0
    for start, end, doc in spans:
        if source[header_end:start].strip():
            break
        if header_end and re.search(r'\n[ \t\r]*\n', source[header_end:start]):
            break
        header_end = end
    licensed_header = header_end if LICENSE.search(source[:header_end]) else 0
    result = {}
    for start, end, doc in spans:
        token = source[start:end]
        body = re.sub(r'^(?:#|//|--|/\*)\s*', '', token)
        reference = re.match(r'///\s*<(?:reference|amd-module|amd-dependency)\b', token)
        if doc or reference or end <= licensed_header or PRAGMA.match(body):
            continue
        line = source.count('\n', 0, start) + 1
        if line == 1 and token.startswith('#!'):
            continue
        for offset, text in enumerate(token.splitlines()):
            number = line + offset
            result[number] = (result[number] + ' ' + text) if number in result else text
    return result


def git(repo, *args):
    """Run read-only Git operations without external diff or text conversion."""
    return subprocess.check_output(['git', '-C', str(repo), *args], stderr=subprocess.PIPE)


def audit(repo, base, head, paths):
    """Return added comment lines between a base commit and a head or working tree."""
    base = git(repo, 'rev-parse', '--verify', '--end-of-options', base + '^{commit}').decode().strip()
    revisions = [base]
    if head:
        head = git(repo, 'rev-parse', '--verify', '--end-of-options', head + '^{commit}').decode().strip()
        revisions.append(head)
    options = ['--no-ext-diff', '--no-textconv', '--no-renames', '--no-color',
               '--output-indicator-new=+', '--output-indicator-old=-', '--output-indicator-context= ']
    names = git(repo, 'diff', *options, '--name-only', '-z', *revisions, '--', *paths)
    findings = []
    for name in sorted(filter(None, names.decode().split('\0'))):
        suffix = Path(name).suffix.lower()
        if suffix not in PYTHON | JAVASCRIPT | SHELL | {'.sql'}:
            continue
        if head:
            if git(repo, 'ls-tree', head, '--', name).startswith(b'120000 '):
                continue
        elif (repo / name).is_symlink():
            continue
        diff = git(repo, 'diff', *options, '--unified=0', *revisions, '--', name).decode(errors='replace')
        added = set()
        line = None
        for row in diff.splitlines():
            hunk = re.match(r'^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@', row)
            if hunk:
                line = int(hunk[1])
            elif line is not None and row.startswith('+'):
                added.add(line)
                line += 1
            elif line is not None and row.startswith(' '):
                line += 1
        if not added:
            continue
        content = git(repo, 'show', f'{head}:{name}') if head else (repo / name).read_bytes()
        source = content.decode(tokenize.detect_encoding(io.BytesIO(content).readline)[0]
                                if suffix in PYTHON else 'utf-8')
        candidates = comment_lines(source, suffix)
        findings.extend({'file': name, 'line': number, 'text': candidates[number]}
                        for number in sorted(added & candidates.keys()))
    return findings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path.cwd())
    parser.add_argument('--base', required=True, help='base commit (direct diff, no merge-base lookup)')
    parser.add_argument('--head', help='head commit; default: staged and unstaged tracked changes')
    parser.add_argument('paths', nargs='*', help='optional Git path filters')
    args = parser.parse_args()
    try:
        print(json.dumps(audit(args.repo.resolve(), args.base, args.head, args.paths), indent=2))
    except (OSError, ValueError, SyntaxError, tokenize.TokenError, subprocess.CalledProcessError) as error:
        parser.exit(1, f'comment-audit: {error}\n')


if __name__ == '__main__':
    main()
