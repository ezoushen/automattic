#!/usr/bin/env python3
"""Claude Code PostToolUse hook: after an edit inside the repository, report the architecture
rules the edited tree now breaks (direction, cycles, imports, skill shape, first reads, host
shape, unmapped files), so the agent fixes them before going on. Other findings wait for the
commit. The edited tree is the Git checkout holding the file, so an edit in a worktree inside
the repository checks that worktree with its own checker configuration.

usage: edit_check.py [--root DIR] [--config FILE]   (hook event JSON on stdin)

Exit 0: nothing to report, or the edit is outside the repository; 2: rules broken, listed on
stderr, which Claude Code shows to the agent.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_docs  # noqa: E402
from architecture import Architecture  # noqa: E402

RULES = {'direction', 'cycle', 'import-direction', 'unmapped', 'entry-doc', 'first-read', 'first-read-line',
         'host-shape'}
CONFIG = Path('.agents/skills/writing-agent-docs/config.json')


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
    config_path = args.config or tree / CONFIG
    if not config_path.is_file():
        return 0
    config = json.loads(config_path.read_text())
    architecture = Architecture.load(config_path.parent / config['architecture'])
    broken = [f for f in check_docs.check(tree, config, None, architecture)
              if f['severity'] == 'error' and f['code'] in RULES]
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
