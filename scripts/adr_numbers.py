#!/usr/bin/env python3
"""Report duplicated ADR numbers and the next free one, in the working tree or at a Git ref.

usage: adr_numbers.py --repo <checkout> [--dir docs/adr] [--ref <commit> [--against <commit>]]

Checks one folder of `NNNN-slug.md` files. With --against, the folder is checked as a merge
of the two commits would leave it: the ref's files, without those the other commit deleted
or renamed since their merge base, plus those it added. Prints JSON {"dir",
"duplicates": {number: [files]}, "next"}. Exits 1 when a number is used twice, 2 on invalid
input. An absent folder has no duplicates and next "0001".
"""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys

NAME = re.compile(r'(\d{4})-.+\.md')


def git(repo, *args):
    return subprocess.run(['git', '-C', str(repo), *args], capture_output=True, text=True)


def names(repo, folder, ref):
    if ref is None:
        path = repo / folder
        return {p.name for p in path.iterdir() if p.is_file()} if path.is_dir() else set()
    resolved = git(repo, 'rev-parse', '--verify', '--quiet', f'{ref}^{{commit}}')
    if resolved.returncode:
        raise ValueError(f'{ref}: not a commit in {repo}')
    listed = git(repo, 'ls-tree', '-z', '--name-only', resolved.stdout.strip(), f'{folder.rstrip("/")}/')
    if listed.returncode:
        raise ValueError(listed.stderr.strip())
    return {Path(entry).name for entry in listed.stdout.split('\0') if entry}


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
    args = parser.parse_args(argv)
    repo = args.repo.resolve()
    try:
        if not repo.is_dir():
            raise ValueError(f'{repo}: not a directory')
        if args.against and not args.ref:
            raise ValueError('--against needs --ref')
        files = names(repo, args.dir, args.ref)
        if args.against:
            other = names(repo, args.dir, args.against)
            base = git(repo, 'merge-base', args.ref, args.against)
            ancestor = names(repo, args.dir, base.stdout.strip()) if base.returncode == 0 else set()
            files = (files - (ancestor - other)) | (other - ancestor)
        duplicates, following = report(files)
    except (ValueError, OSError) as error:
        print(error, file=sys.stderr)
        return 2
    print(json.dumps({'dir': args.dir, 'duplicates': duplicates, 'next': following}, ensure_ascii=False))
    return 1 if duplicates else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
