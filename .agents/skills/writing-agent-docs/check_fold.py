#!/usr/bin/env python3
"""Prove a restructuring kept everything: every body line of the agent docs and the
feature surface (skills, agents, jobs, kinds, decision families, hook events, script
commands) match a base commit, except differences listed as deliberate.

usage: check_fold.py --base BASE [--root DIR] [--config FILE] [--allow FILE] [--json]

Lines compare after link targets are dropped, so moving text and retargeting its links
is free, but a dropped, duplicated-then-lost or reworded line is reported. --allow names
a JSON file: {"lines": [base lines that may be gone], "surface": ["removed skill x",
"added skill y"]}. Exit 0: nothing differs; 1: differences; 2: invalid input.
"""
import argparse
import ast
from collections import Counter
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_docs  # noqa: E402


def normalize(line):
    line = check_docs.INLINE_LINK.sub(lambda m: ('!' if m.group(0)[0] == '!' else '') + f'[{m.group(1)}]()', line)
    return re.sub(r'^(\s{0,3}\[[^\]]+\]:)\s+\S.*$', r'\1', line).strip()


def body_lines(root, config):
    lines = Counter()
    for path in check_docs.expand(root, config['docs']):
        lines.update(normalize(line) for line in path.read_text().splitlines() if line.strip())
    return lines


def surface(root, fold):
    """Feature-surface entries as (kind, text); file locations never appear, so moves are free."""
    found = set()
    files = lambda key: check_docs.expand(root, fold.get(key, []))
    for path in files('skills'):
        found.add(('skill', (check_docs.frontmatter(path.read_text())[0] or {}).get('name') or path.parent.name))
    for path in files('agents'):
        found.add(('agent', (check_docs.frontmatter(path.read_text())[0] or {}).get('name') or path.stem))
    for path in files('jobs'):
        fields = check_docs.frontmatter(path.read_text())[0] or {}
        rest = ' '.join(f'{key}={value}' for key, value in sorted(fields.items()) if key != 'name')
        found.add(('job', f'{fields.get("name") or path.stem} {rest}'.strip()))
    for path in files('kinds'):
        found.add(('kind', path.stem))
    for path in files('hooks'):
        for event in json.loads(path.read_text()).get('hooks', {}):
            found.add(('hook-event', f'{path.parent.name}/{event}'))
    for path in files('commands'):
        for node in ast.walk(ast.parse(path.read_text(), str(path))):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.args
                    and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str)):
                continue
            if node.func.attr == 'add_parser':
                found.add(('command', f'{path.stem} sub:{node.args[0].value}'))
            elif node.func.attr == 'add_argument' and node.args[0].value.startswith('-'):
                found.add(('command', f'{path.stem} option:{node.args[0].value}'))
    schema = fold.get('decision_families')
    if schema and (root / schema).is_file():
        for family in json.loads((root / schema).read_text())['properties']['family']['enum']:
            found.add(('decision-family', family))
    return found


def export(root, base, target):
    result = subprocess.run(['git', '-C', str(root), 'archive', '--format=tar', base], capture_output=True)
    if result.returncode:
        raise check_docs.InputError(f'git archive {base}: {result.stderr.decode(errors="replace").strip()}')
    with tarfile.open(fileobj=io.BytesIO(result.stdout)) as archive:
        archive.extractall(target, filter='data')


def compare(root, base_root, config, fold, allow):
    differences = []
    allowed_lines = {normalize(line) for line in allow.get('lines', [])}
    missing = body_lines(base_root, config) - body_lines(root, config)
    for line, count in sorted(missing.items()):
        if line not in allowed_lines:
            differences.append({'kind': 'line', 'text': line, 'count': count})
    before, after = surface(base_root, fold), surface(root, fold)
    allowed = set(allow.get('surface', []))
    for verb, entries in (('removed', before - after), ('added', after - before)):
        for kind, text in sorted(entries):
            if f'{verb} {kind} {text}' not in allowed:
                differences.append({'kind': kind, 'text': f'{verb} {text}'})
    return differences


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--base', required=True)
    parser.add_argument('--root', type=Path)
    parser.add_argument('--config', type=Path, default=Path(__file__).with_name('config.json'))
    parser.add_argument('--allow', type=Path)
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()
    try:
        root = (args.root or Path(check_docs.git(Path.cwd(), 'rev-parse', '--show-toplevel').strip())).resolve()
        config = json.loads(args.config.read_text())
        fold = json.loads((args.config.parent / config['architecture']).read_text())['fold']
        allow = json.loads(args.allow.read_text()) if args.allow else {}
        with tempfile.TemporaryDirectory(prefix='fold base ') as directory:
            export(root, args.base, directory)
            differences = compare(root, Path(directory), config, fold, allow)
    except (check_docs.InputError, OSError, ValueError, KeyError) as error:
        print(f'check_fold.py: {error}', file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(differences, indent=1))
    else:
        for item in differences:
            print(f'{item["kind"]}: {item["text"]}' + (f' (x{item["count"]})' if item.get('count', 1) > 1 else ''))
        print(f'{len(differences)} differences')
    return 1 if differences else 0


if __name__ == '__main__':
    sys.exit(main())
