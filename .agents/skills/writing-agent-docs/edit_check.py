#!/usr/bin/env python3
"""Claude Code PostToolUse hook: after an edit inside the repository, report the architecture
rules the edited tree now breaks (direction, cycles, imports, skill shape, first reads, host
shape, unmapped files), so the agent fixes them before going on. Other findings wait for the
commit. The edited tree is the Git checkout holding the file, so an edit in a worktree inside
the repository runs that worktree's own checker and configuration; a checker that fails to
run reports nothing rather than blocking the edit.

usage: edit_check.py [--root DIR] [--config FILE]   (hook event JSON on stdin)

Exit 0: nothing to report, or the edit is outside the repository; 2: rules broken, listed on
stderr, which Claude Code shows to the agent.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys

RULES = {'direction', 'cycle', 'import-direction', 'unmapped', 'entry-doc', 'first-read', 'first-read-line',
         'host-shape', 'shared-section'}
CHECKER = Path('.agents/skills/writing-agent-docs')


def checkout(path):
    """The top of the Git checkout holding path, or None."""
    folder = path.parent
    while not folder.is_dir() and folder != folder.parent:
        folder = folder.parent
    result = subprocess.run(['git', '-C', str(folder), 'rev-parse', '--show-toplevel'], capture_output=True, text=True)
    return Path(result.stdout.strip()).resolve() if result.returncode == 0 else None


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument('--config', type=Path)
    args = parser.parse_args()
    try:
        edited = Path(json.load(sys.stdin).get('tool_input', {}).get('file_path') or '')
    except (ValueError, AttributeError):
        return 0
    root = args.root.resolve()
    if not edited.is_absolute() or root not in edited.resolve().parents:
        return 0
    tree = checkout(edited.resolve()) or root
    if tree != root and root not in tree.parents:
        tree = root
    checker = tree / CHECKER / 'check_docs.py'
    if not checker.is_file():
        checker = Path(__file__).resolve().with_name('check_docs.py')
    config = args.config or tree / CHECKER / 'config.json'
    if not config.is_file():
        return 0
    run = subprocess.run([sys.executable, str(checker), '--root', str(tree), '--config', str(config), '--json'],
                         capture_output=True, text=True)
    try:
        findings = json.loads(run.stdout) if run.returncode in (0, 1) else []
    except ValueError:
        findings = []
    broken = [f for f in findings if f['severity'] == 'error' and f['code'] in RULES]
    if not broken:
        return 0
    where = '' if tree == root else f' in {tree}'
    for f in broken:
        print(f"{f['path']}:{f['line']} {f['code']}: {f['message']}", file=sys.stderr)
    print(f'The tree{where} breaks the module architecture; fix it before going on '
          '(.agents/skills/writing-agent-docs/SKILL.md, "Fix what it reports").', file=sys.stderr)
    return 2


if __name__ == '__main__':
    sys.exit(main())
