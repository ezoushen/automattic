#!/usr/bin/env python3
"""Report duplicated ADR numbers and the next free one, in the working tree or at a Git ref.

usage: adr_numbers.py --repo <checkout> [--dir docs/adr] [--ref <branch or commit>]

Prints JSON {"dir", "duplicates": {number: [files]}, "next"}. Exits 1 when a number is
used twice, 2 on invalid input. An absent folder has no duplicates and next "0001".
"""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys

NAME = re.compile(r'(\d{4})-.+\.md')


def names(repo, folder, ref):
    if ref is None:
        path = repo / folder
        return sorted(p.name for p in path.iterdir() if p.is_file()) if path.is_dir() else []
    resolved = subprocess.run(['git', '-C', str(repo), 'rev-parse', '--verify', '--quiet', f'{ref}^{{commit}}'],
                              capture_output=True, text=True)
    if resolved.returncode:
        raise ValueError(f'{ref}: not a commit in {repo}')
    listed = subprocess.run(['git', '-C', str(repo), 'ls-tree', '--name-only', resolved.stdout.strip(),
                             f'{folder.rstrip("/")}/'], capture_output=True, text=True, check=True)
    return sorted(Path(line).name for line in listed.stdout.splitlines())


def report(files):
    numbered = {}
    for name in files:
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
    args = parser.parse_args(argv)
    try:
        duplicates, following = report(names(args.repo.resolve(), args.dir, args.ref))
    except (ValueError, subprocess.CalledProcessError, OSError) as error:
        print(error, file=sys.stderr)
        return 2
    print(json.dumps({'dir': args.dir, 'duplicates': duplicates, 'next': following}))
    return 1 if duplicates else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
