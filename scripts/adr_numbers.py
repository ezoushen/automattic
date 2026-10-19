#!/usr/bin/env python3
"""Report duplicated ADR numbers and the next free one, in the working tree or at a Git ref.

usage: adr_numbers.py --repo <checkout> [--dir docs/adr] [--ref <commit> [--against <commit>]] [--require-index]

Checks one folder of `NNNN-slug.md` files. With --against, the folder is checked as merging
the two commits would leave it, using `git merge-tree` (Git 2.38 or later) without touching
any branch or working tree. When the folder has a `README.md` index, or --require-index is
given, each ADR's status (front matter `status:`, default accepted) must match the index
section that lists it, every listed file must exist, and every `superseded by ADR-NNNN` must
be answered by that ADR's `supersedes:` and the reverse. Prints JSON {"dir", "duplicates":
{number: [files]}, "next", "index_problems": [...]}. Exits 1 on a duplicate number or an
index problem, 2 on invalid input. An absent folder has no problems and next "0001".
"""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys

NAME = re.compile(r'(\d{4})-.+\.md')
LINK = re.compile(r'\]\((\d{4}-[^)\s]+\.md)\)')
SECTIONS = {'accepted': 'Accepted', 'superseded': 'Superseded', 'deprecated': 'Deprecated'}


def git(repo, *args):
    return subprocess.run(['git', '-C', str(repo), *args], capture_output=True, text=True)


def names(repo, folder, ref):
    if ref is None:
        path = repo / folder
        return {p.name for p in path.iterdir() if p.is_file()} if path.is_dir() else set()
    resolved = git(repo, 'rev-parse', '--verify', '--quiet', f'{ref}^{{tree}}')
    if resolved.returncode:
        raise ValueError(f'{ref}: not a commit in {repo}')
    listed = git(repo, 'ls-tree', '-z', '--name-only', resolved.stdout.strip(), f'{folder.rstrip("/")}/')
    if listed.returncode:
        raise ValueError(listed.stderr.strip())
    return {Path(entry).name for entry in listed.stdout.split('\0') if entry}


def merged_tree(repo, ref, against):
    for name in (ref, against):
        if git(repo, 'rev-parse', '--verify', '--quiet', f'{name}^{{commit}}').returncode:
            raise ValueError(f'{name}: not a commit in {repo}')
    # Exit 1 means the merge has conflicts, which still yields a tree; anything else is fatal.
    merged = git(repo, 'merge-tree', '--write-tree', ref, against)
    if merged.returncode not in (0, 1):
        raise ValueError(merged.stderr.strip() or f'git merge-tree failed for {ref} and {against}')
    return merged.stdout.splitlines()[0]


def read(repo, folder, ref, name):
    if ref is None:
        return (repo / folder / name).read_text()
    shown = git(repo, 'show', f'{ref}:{folder.rstrip("/")}/{name}')
    if shown.returncode:
        raise ValueError(shown.stderr.strip())
    return shown.stdout


def front_matter(text):
    fields = {}
    if text.startswith('---\n') and '\n---\n' in text[4:]:
        for line in text[4:text.index('\n---\n', 4)].splitlines():
            key, _, value = line.partition(':')
            fields[key.strip()] = value.strip()
    return fields


def index_problems(texts, folder, require):
    """Problems between the ADRs, their supersede links and the index; texts maps file name to content."""
    adrs = {name: front_matter(text) for name, text in texts.items() if NAME.fullmatch(name)}
    status_of = {name: fields.get('status', 'accepted') for name, fields in adrs.items()}
    by_number = {}
    for name in adrs:
        by_number.setdefault(name[:4], []).append(name)
    problems = []
    for name, fields in sorted(adrs.items()):
        status = status_of[name]
        superseded = re.fullmatch(r'superseded by ADR-(\d{4})', status)
        if status not in ('accepted', 'deprecated') and not superseded:
            problems.append(f'{name}: unknown status {status}')
        if superseded and not any(name[:4] in re.findall(r'ADR-(\d{4})', adrs[newer].get('supersedes', ''))
                                  for newer in by_number.get(superseded[1], [])):
            problems.append(f'{name}: {status}, which does not name it in supersedes')
        for older in re.findall(r'ADR-(\d{4})', fields.get('supersedes', '')):
            if not any(status_of[o] == f'superseded by ADR-{name[:4]}' for o in by_number.get(older, [])):
                problems.append(f'{name}: supersedes ADR-{older}, which is not superseded by ADR-{name[:4]}')
    if 'README.md' not in texts:
        return problems + ([f'{folder.rstrip("/")}/README.md: no index'] if require and adrs else [])
    listed, section = {}, None
    for line in texts['README.md'].splitlines():
        if line.startswith('## '):
            section = line[3:].strip()
        for target in LINK.findall(line):
            listed.setdefault(target, []).append(section)
    for target in sorted(listed):
        if target not in adrs:
            problems.append(f'{target}: listed in the index but no such file')
    for name, status in sorted(status_of.items()):
        want = SECTIONS.get(status.split()[0]) if status.split() else None
        if want is None:
            continue
        sections = listed.get(name, [])
        if want not in sections:
            problems.append(f'{name}: {status} but not listed under {want}')
        for other in sorted(set(sections) - {want}):
            problems.append(f'{name}: {status} but also listed under {other}')
    return problems


def report(files):
    numbered = {}
    for name in sorted(files):
        match = NAME.fullmatch(name)
        if match:
            numbered.setdefault(match[1], []).append(name)
    duplicates = {number: group for number, group in sorted(numbered.items()) if len(group) > 1}
    highest = max(map(int, numbered), default=0)
    return duplicates, f'{highest + 1:04d}'


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--dir', default='docs/adr', help="the project's ADR folder")
    parser.add_argument('--ref', help='read the folder at this commit instead of the working tree')
    parser.add_argument('--against', help='check the folder as merging this commit would leave it')
    parser.add_argument('--require-index', action='store_true', help='a folder with ADRs must have README.md')
    args = parser.parse_args(argv)
    repo = args.repo.resolve()
    try:
        if not repo.is_dir():
            raise ValueError(f'{repo}: not a directory')
        if args.against and not args.ref:
            raise ValueError('--against needs --ref')
        ref = args.ref
        if args.against:
            ref = merged_tree(repo, args.ref, args.against)
        files = names(repo, args.dir, ref)
        duplicates, following = report(files)
        texts = {name: read(repo, args.dir, ref, name) for name in files
                 if NAME.fullmatch(name) or name == 'README.md'}
        problems = index_problems(texts, args.dir, args.require_index)
    except (ValueError, OSError) as error:
        print(error, file=sys.stderr)
        return 2
    print(json.dumps({'dir': args.dir, 'duplicates': duplicates, 'next': following, 'index_problems': problems},
                     ensure_ascii=False))
    return 1 if duplicates or problems else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
