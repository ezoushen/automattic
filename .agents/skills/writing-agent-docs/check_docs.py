#!/usr/bin/env python3
"""Find smells in agent-facing Markdown: docs too big for one read, broken links and
anchors, orphans, stale names and skill frontmatter outside the published format.

usage: check_docs.py [--root DIR] [--config FILE] [--changed BASE] [--json]

Exit 0: no errors; 1: errors found; 2: invalid input (bad config, base or repository).
Warnings are smells to judge. --changed limits per-file rules to files changed since
BASE (plus untracked files) and flags positional references on added lines; links,
anchors, orphans and code paths stay repo-wide, because a move breaks other files.
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote

INLINE_LINK = re.compile(r'!?\[((?:[^\[\]]|\[[^\]]*\])*)\]\(\s*(<[^>]*>|(?:[^()\s]|\([^()\s]*\))+)'
                         r'(?:\s+(?:"[^"]*"|\'[^\']*\'|\([^)]*\)))?\s*\)')
REFERENCE = re.compile(r'^\s{0,3}\[(?!\^)([^\]]+)\]:\s*(<[^>]*>|[^\s<>]*[./#:][^\s<>]*)'
                       r'(?:\s+(?:"[^"]*"|\'[^\']*\'|\([^)]*\)))?\s*$')
FENCE = re.compile(r'\s*(?:>\s*)*(`{3,}|~{3,})(.*)$')
ATX = re.compile(r'\s{0,3}(#{1,6})\s+(.*?)(?:\s+#+)?\s*$')
SETEXT = re.compile(r'\s{0,3}(=+|-+)\s*$')
MONTHS = 'January|February|March|April|May|June|July|August|September|October|November|December'
DATED = re.compile(rf'\b(?:(?:{MONTHS})\s+(?:\d{{1,2}},\s*)?20\d\d|as of\s+20\d\d|20\d\d-[01]\d-[0-3]\d)\b', re.I)
BACKSLASH = re.compile(r'\b[\w.-]+\\[\w.-]+\.\w+\b')
POSITIONAL = re.compile(r'\b(?:above|below)\b', re.I)
POSITIONAL_REFERENCE = re.compile(r'\b(?:the|this|these|those|see|as)\b[^.;:]{0,40}?\b(?:above|below)\b', re.I)
MD_NAME = re.compile(r'(?<![\w/.-])([\w.-]+(?:/[\w.-]+)*\.md)\b')
PERSON = re.compile(r"^(?:I|I'm|I'll|We|We'll|You|You'll)\b")


class Finding(dict):
    def __init__(self, path, line, severity, code, message):
        super().__init__(path=path, line=line, severity=severity, code=code, message=message)


class InputError(Exception):
    pass


def expand(root, patterns, exclude=()):
    patterns = [patterns] if isinstance(patterns, str) else patterns
    skipped = {path for pattern in exclude for path in root.glob(pattern)}
    return sorted({path for pattern in patterns for path in root.glob(pattern) if path.is_file()} - skipped)


def strip_code(line):
    return re.sub(r'(`+)(?:(?!\1).)+?\1', '', line)


def prose(path):
    """(line number, text) for lines outside frontmatter and fenced code (backtick or tilde)."""
    lines = path.read_text().splitlines()
    start = 0
    if len(lines) > 1 and lines[0] == '---' and re.match(r'[\w-]+:', lines[1]) and '---' in lines[1:]:
        start = lines.index('---', 1) + 1
    fence = None
    for number, line in enumerate(lines[start:], start + 1):
        match = FENCE.match(line)
        if fence is None and match:
            fence = match.group(1)
        elif fence is not None:
            if match and match.group(1)[0] == fence[0] and len(match.group(1)) >= len(fence) and not match.group(2).strip():
                fence = None
        else:
            yield number, line


def links(text):
    """(label, target) for inline links and reference definitions in one line of prose."""
    text = strip_code(text)
    found = [(label, target) for label, target in INLINE_LINK.findall(text)]
    if match := REFERENCE.match(text):
        found.append((match.group(1), match.group(2)))
    return [(label, target.strip('<>')) for label, target in found]


def slug(heading):
    """GitHub's anchor for a heading: rendered text, lowercased, punctuation dropped."""
    text = re.sub(r'!?\[([^\]]*)\]\([^)]*\)', r'\1', heading).replace('`', '')
    text = re.sub(r'(\*{1,3})(\S(?:.*?\S)?)\1', r'\2', text)
    text = re.sub(r'(?<!\w)(_{1,3})(\S(?:.*?\S)?)\1(?!\w)', r'\2', text)
    return re.sub(r'[^\w\- ]', '', text.strip().lower()).replace(' ', '-')


def outline(path, cache={}):
    """Anchors (duplicates numbered as GitHub does) and level-2 (title, anchor) sections."""
    if path not in cache:
        slugs, sections, seen, paragraph = [], [], {}, []
        for number, line in prose(path):
            heading = None
            if paragraph and paragraph[-1][0] != number - 1:
                paragraph = []
            if match := ATX.match(line):
                heading = (len(match.group(1)), match.group(2))
            elif (match := SETEXT.match(line)) and paragraph:
                heading = (1 if match.group(1)[0] == '=' else 2, ' '.join(text.strip() for _, text in paragraph))
            if heading:
                base = slug(heading[1])
                slugs.append(base if base not in seen else f'{base}-{seen[base]}')
                seen[base] = seen.get(base, 0) + 1
                if heading[0] == 2:
                    sections.append((heading[1].strip(), slugs[-1]))
                paragraph = []
            elif not line.strip() or re.match(r'\s*([-*+>|]|\d+\.)(\s|$)', line):
                paragraph = []
            else:
                paragraph.append((number, line))
        cache[path] = slugs, sections
    return cache[path]


def frontmatter(text):
    """Top-level scalar fields of YAML frontmatter, including > and | block scalars."""
    if not text.startswith('---\n') or '\n---' not in text[4:]:
        return None, text
    head, body = text[4:].split('\n---', 1)
    fields, lines = {}, head.splitlines()
    for index, line in enumerate(lines):
        if not (match := re.match(r'([\w-]+):\s*(.*)', line)):
            continue
        value = match.group(2).strip()
        if not value or value[:1] in ('>', '|'):
            block = []
            for following in lines[index + 1:]:
                if following.strip() and not following[:1].isspace():
                    break
                block.append(following.strip())
            value = ('\n' if value[:1] == '|' else ' ').join(block).strip()
        fields[match.group(1)] = value.strip('"\'')
    return fields, body.split('\n', 1)[1] if '\n' in body else ''


def exists_exactly(path):
    """Exists with the same letter case in every component, as on a case-sensitive filesystem."""
    if not path.exists():
        return False
    current = Path(path.anchor)
    for part in path.parts[1:]:
        if part not in os.listdir(current):
            return False
        current = current / part
    return True


def git(root, *args):
    result = subprocess.run(['git', '-c', 'core.quotepath=off', '-C', str(root), *args], capture_output=True,
                            text=True, errors='replace')  # diffs carry file content in any encoding
    if result.returncode:
        raise InputError(f'git {" ".join(args)}: {result.stderr.strip()}')
    return result.stdout


def changed_files(root, base):
    """{path: added line numbers} for files changed since base, untracked files included."""
    top = Path(git(root, 'rev-parse', '--show-toplevel').strip()).resolve()
    git(root, 'rev-parse', '--verify', '--quiet', f'{base}^{{commit}}')
    names = set(filter(None, git(root, 'diff', '--name-only', '-z', '-M', base, '--').split('\0')))
    untracked = set(filter(None, git(root, 'ls-files', '--others', '--exclude-standard', '-z', '--full-name').split('\0')))
    added, current, previous = {}, None, ''
    diff = git(root, 'diff', '-U0', '-M', '--no-color', '--src-prefix=a/', '--dst-prefix=b/', base, '--')
    for line in diff.splitlines():
        header, previous = previous.startswith('--- ') and line.startswith('+++ '), line
        if header:
            name = line[4:].rstrip('\t')
            current = None if name == '/dev/null' else added.setdefault(top / name[2:], set())
        elif match := re.match(r'@@ -\S+ \+(\d+)', line):
            number = int(match.group(1))
        elif line.startswith('+') and current is not None:
            current.add(number)
            number += 1
    result = {}
    for name in names | untracked:
        path = (top / name).resolve()
        if path.suffix == '.md' and path.is_file() and path.is_relative_to(root):
            result[path] = set(range(1, len(path.read_text().splitlines()) + 1)) if name in untracked \
                else added.get(top / name, set())
    return result


def tracked_names(root):
    try:
        names = git(root, 'ls-files', '-z', '--cached', '--others', '--exclude-standard').split('\0')
        return {Path(name).name for name in names if name.endswith('.md')}
    except (InputError, FileNotFoundError):
        return {path.name for path in root.rglob('*.md') if '.git' not in path.parts}


def check(root, config, changed=None):
    findings = []
    rel = lambda path: str(path.relative_to(root))
    docs = expand(root, config['docs'])
    linking = sorted(set(expand(root, config['linking'])) | set(docs))
    skills = expand(root, config['skill_files'])
    entry = set(expand(root, config.get('entry_points', [])))
    in_scope = (lambda path: True) if changed is None else (lambda path: path in changed)
    basenames = tracked_names(root) | set(config.get('known_names', []))

    # Size, contents and per-line smells in each agent doc.
    for path in docs:
        if not in_scope(path):
            continue
        size, limit = path.stat().st_size, config['max_bytes']
        debt = config.get('debt', {}).get(rel(path), {})
        if size > limit and size <= debt.get('bytes', 0):
            lower = f'; lower the recorded size to {size}' if size < debt['bytes'] else ''
            findings.append(Finding(rel(path), 1, 'warning', 'debt',
                                    f'{size} bytes, over {limit}; recorded debt may shrink, not grow{lower}'))
        elif size > limit:
            findings.append(Finding(rel(path), 1, 'error', 'size',
                                    f'{size} bytes, over {limit}: split it by reader so it fits one read'))
        elif 'bytes' in debt:
            findings.append(Finding(rel(path), 1, 'warning', 'stale-debt', 'within budget now; remove its recorded size'))
        lines = path.read_text().splitlines()
        _, sections = outline(path)
        if (len(lines) <= 100 or len(sections) < 3) and debt.get('contents'):
            findings.append(Finding(rel(path), 1, 'warning', 'stale-debt', 'no contents list needed; remove its recorded debt'))
        elif len(lines) > 100 and len(sections) >= 3:
            listed = []
            if 'Contents:' in lines[:30]:
                for line in lines[lines.index('Contents:') + 1:]:
                    if not (match := re.match(r'- \[(.+)\]\(#([^)]+)\)$', line)):
                        break
                    listed.append(match.groups())
            if listed == sections and debt.get('contents'):
                findings.append(Finding(rel(path), 1, 'warning', 'stale-debt', 'contents list present; remove its recorded debt'))
            elif listed != sections and debt.get('contents'):
                findings.append(Finding(rel(path), 1, 'warning', 'debt', 'recorded debt: contents list missing or stale'))
            elif listed != sections:
                findings.append(Finding(rel(path), 1, 'error', 'contents',
                                        'a long multi-section doc starts with "Contents:" listing every ## section in order'))
        for number, line in prose(path):
            text = strip_code(line)
            if DATED.search(text):
                findings.append(Finding(rel(path), number, 'warning', 'dated',
                                        'time-bound wording goes stale; state the current behaviour'))
            if BACKSLASH.search(text):
                findings.append(Finding(rel(path), number, 'warning', 'backslash', 'use forward slashes in paths'))
            plain = '' if REFERENCE.match(text) else INLINE_LINK.sub(lambda m: m.group(1), text)
            for name in MD_NAME.findall(plain):
                if '/' in name:
                    exists = (path.parent / name).exists() or (root / name).exists()
                else:
                    exists = name in basenames
                if not exists:
                    findings.append(Finding(rel(path), number, 'warning', 'stale-name',
                                            f'{name} names no file in this repository; link the doc that holds it'))
            label_points_away = any(POSITIONAL.search(label) and target.split('#')[0]
                                    for label, target in links(line) if '://' not in target)
            added_reference = changed is not None and number in changed[path] and POSITIONAL_REFERENCE.search(text)
            if label_points_away or added_reference:
                findings.append(Finding(rel(path), number, 'warning', 'positional',
                                        '`above`/`below` breaks when text moves; link or name the target'))

    for name in config.get('debt', {}):
        if root / name not in docs and (changed is None or not (root / name).exists()):
            findings.append(Finding(name, 1, 'warning', 'stale-debt', 'not an agent doc in this repository; remove its recorded debt'))

    # Skill frontmatter.
    total = 0
    for path in skills:
        fields, body = frontmatter(path.read_text())
        name, description = (fields or {}).get('name', ''), (fields or {}).get('description', '')
        total += len(description)
        if not in_scope(path):
            continue
        problems = []
        if not re.fullmatch(r'[a-z0-9-]{1,64}', name) or re.search(r'anthropic|claude', name):
            problems.append('name is 1-64 lowercase letters, digits or hyphens, without "anthropic" or "claude"')
        if not description or len(description) > 1024 or re.search(r'<[^>]+>', description):
            problems.append('description is 1-1024 characters without XML tags')
        if problems:
            findings.append(Finding(rel(path), 1, 'error', 'frontmatter', '; '.join(problems)))
        elif PERSON.match(description):
            findings.append(Finding(rel(path), 1, 'warning', 'person',
                                    'write the description in the third person: what it does and when to use it'))
        if len(body.splitlines()) > 500:
            findings.append(Finding(rel(path), 1, 'error', 'skill-lines',
                                    'SKILL.md body over 500 lines; move detail into linked files'))
    if total > config['description_budget'] and skills and (changed is None or any(map(in_scope, skills))):
        findings.append(Finding(rel(skills[-1]), 1, 'warning', 'description-budget',
                                f'skill descriptions total {total} characters, over the local budget of '
                                f'{config["description_budget"]}; hosts shorten descriptions to fit their skill list'))

    # Links and anchors, repo-wide; collect what each doc reaches.
    reached = set()
    for path in linking:
        for number, line in prose(path):
            for _, link in links(line):
                if re.match(r'[a-z][\w+.-]*:', link, re.I):
                    continue  # URL schemes: https:, mailto: and the like.
                target, _, anchor = link.partition('#')
                anchor = unquote(anchor)
                target = unquote(target.split('?', 1)[0])
                resolved = (path.parent / target).resolve() if target else path.resolve()
                if not exists_exactly(resolved):
                    findings.append(Finding(rel(path), number, 'error', 'link', f'{link} does not exist'))
                    continue
                if resolved != path.resolve():
                    reached.add(resolved)
                if anchor and resolved.suffix == '.md' and anchor not in outline(resolved)[0]:
                    findings.append(Finding(rel(path), number, 'error', 'anchor', f'{link}: no such heading'))

    # Doc paths named in code.
    pattern = re.compile(config['code_doc_pattern'])
    for path in expand(root, config.get('code', []), config.get('exclude', [])):
        for number, line in enumerate(path.read_text(errors='replace').splitlines(), 1):  # any source encoding
            for doc in pattern.findall(line):
                if exists_exactly(root / doc) and (root / doc).is_file():
                    reached.add((root / doc).resolve())
                else:
                    findings.append(Finding(rel(path), number, 'error', 'code-path', f'{doc} does not exist'))

    for path in docs:
        if path not in entry and path.resolve() not in reached:
            findings.append(Finding(rel(path), 1, 'error', 'orphan', 'no doc or code links it, so no agent reaches it'))
    return sorted(findings, key=lambda f: (f['path'], f['line'], f['code'], f['message']))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--root', type=Path)
    parser.add_argument('--config', type=Path, default=Path(__file__).with_name('config.json'))
    parser.add_argument('--changed', metavar='BASE')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()
    try:
        root = (args.root or Path(git(Path.cwd(), 'rev-parse', '--show-toplevel').strip())).resolve()
        config = json.loads(args.config.read_text())
        changed = changed_files(root, args.changed) if args.changed else None
    except (InputError, OSError, ValueError) as error:
        print(f'check_docs.py: {error}', file=sys.stderr)
        return 2
    findings = check(root, config, changed)
    if args.json:
        print(json.dumps(findings, indent=1))
    else:
        for f in findings:
            print(f"{f['path']}:{f['line']}: {f['severity']} {f['code']}: {f['message']}")
        errors = sum(f['severity'] == 'error' for f in findings)
        print(f'{errors} errors, {len(findings) - errors} warnings')
    return 1 if any(f['severity'] == 'error' for f in findings) else 0


if __name__ == '__main__':
    sys.exit(main())
