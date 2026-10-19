#!/usr/bin/env python3
"""Claude Code PostToolUse hook: after an edit inside the repository, report the architecture
rules the tree now breaks (direction, cycles, imports, skill shape, first reads, host shape,
unmapped files), so the agent fixes them before going on. Other findings wait for the commit.

usage: edit_check.py [--root DIR] [--config FILE]   (hook event JSON on stdin)

Exit 0: nothing to report or the edit is outside the repository; 2: rules broken, listed on
stderr, which Claude Code shows to the agent.
"""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_docs  # noqa: E402
from architecture import Architecture  # noqa: E402

RULES = {'direction', 'cycle', 'import-direction', 'unmapped', 'entry-doc', 'first-read', 'first-read-line',
         'host-shape'}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument('--config', type=Path, default=Path(__file__).with_name('config.json'))
    args = parser.parse_args()
    edited = Path(json.load(sys.stdin).get('tool_input', {}).get('file_path') or '')
    root = args.root.resolve()
    if not edited.is_absolute() or root not in edited.resolve().parents:
        return 0
    config = json.loads(args.config.read_text())
    architecture = Architecture.load(args.config.parent / config['architecture'])
    broken = [f for f in check_docs.check(root, config, None, architecture)
              if f['severity'] == 'error' and f['code'] in RULES]
    if not broken:
        return 0
    for f in broken:
        print(f"{f['path']}:{f['line']} {f['code']}: {f['message']}", file=sys.stderr)
    print('The tree breaks the module architecture; fix it before going on '
          '(.agents/skills/writing-agent-docs/SKILL.md, "Fix what it reports").', file=sys.stderr)
    return 2


if __name__ == '__main__':
    sys.exit(main())
