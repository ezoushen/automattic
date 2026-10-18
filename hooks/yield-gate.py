#!/usr/bin/env python3
"""Stop hook: keep the host working while a lifecycle worker could finish without waking it.

Reads every run's workers.sqlite under the main checkout's .scratch/*/reports/ that
changed in the last day, without writing to it, and applies the lifecycle's yield
gate. `claude` and `codex` speak their shared Stop hook protocol; `check <cwd>`
prints the gaps as JSON for other hosts. Set AUTOMATTIC_YIELD_HOOK=off to disable the check.
"""
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent.parent
RECENT_SECONDS = 24 * 3600
GUIDE = ROOT / 'harnesses/worker-lifecycle.md'


def lifecycle():
    spec = importlib.util.spec_from_file_location('worker_lifecycle', ROOT / 'scripts/worker_lifecycle.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main_checkout(cwd):
    result = subprocess.run(['git', '-C', str(cwd), 'rev-parse', '--path-format=absolute', '--git-common-dir'],
                            capture_output=True, text=True, timeout=5)
    return Path(result.stdout.strip()).parent if result.returncode == 0 else None


def gaps(cwd):
    root = main_checkout(cwd)
    if root is None:
        return []
    cwd, pane = Path(cwd).resolve(), os.environ.get('HERDR_PANE_ID')
    module, missing = None, []
    for state in sorted(root.glob('.scratch/*/reports/workers.sqlite')):
        if time.time() - state.stat().st_mtime > RECENT_SECONDS:
            continue
        module = module or lifecycle()
        db = sqlite3.connect(f'{state.as_uri()}?mode=ro', uri=True, timeout=5)
        try:
            # A session inside a worker's own worktree is that worker, not its coordinator.
            worker = any(Path(saved['worktree']) != root and cwd.is_relative_to(saved['worktree'])
                         for saved in module.attempts(db))

            def coordinated(saved):
                if pane and saved.get('coordinator'):
                    return saved['coordinator'] == pane
                return not worker
            missing += [f'{state}: {gap}' for gap in module.yield_gaps(db, coordinated)]
        finally:
            db.close()
    return missing


def reason(missing):
    return ('These lifecycle workers could finish without waking you:\n'
            + ''.join(f'- {gap}\n' for gap in missing)
            + 'Arm a notified wait, recover the receipt or collect the result (for a worker that is gone, '
            + f'a failed or cancelled result whose report says what was lost) before stopping ({GUIDE}).')


def main():
    if os.environ.get('AUTOMATTIC_YIELD_HOOK') == 'off':
        return 0
    if sys.argv[1:2] == ['check'] and len(sys.argv) == 3:
        print(json.dumps({'missing': gaps(Path(sys.argv[2]))}))
        return 0
    if sys.argv[1:] not in (['claude'], ['codex']):
        sys.exit('usage: yield-gate.py claude|codex < stop-hook-input, or yield-gate.py check <cwd>')
    payload = json.load(sys.stdin)
    if payload.get('stop_hook_active'):
        return 0
    missing = gaps(Path(payload.get('cwd') or os.getcwd()))
    if missing:
        print(json.dumps({'decision': 'block', 'reason': reason(missing)}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
