#!/usr/bin/env python3
"""Run every tests/test_*.py regression script in parallel.

usage: tests/run_all.py

Uses the plugin environment's .venv (the main checkout's, from a worktree) unless
PYTHON names another interpreter. Prints each failing script's output tail and
exits 1 when any script fails. Native checks (AUTOMATTIC_NATIVE=1) stay opt-in; see the README.
"""
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
# A Git hook exports these; the tests' temporary repositories must not inherit them.
GIT_VARIABLES = ('GIT_DIR', 'GIT_INDEX_FILE', 'GIT_WORK_TREE', 'GIT_PREFIX', 'GIT_OBJECT_DIRECTORY', 'GIT_COMMON_DIR')


def interpreter(env):
    if os.environ.get('PYTHON'):
        return os.environ['PYTHON']
    common = subprocess.run(['git', 'rev-parse', '--git-common-dir'], cwd=ROOT, env=env,
                            capture_output=True, text=True).stdout.strip()
    main = (ROOT / common).resolve().parent if common else ROOT
    for candidate in (ROOT / '.venv/bin/python', main / '.venv/bin/python'):
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return shutil.which('python3') or sys.executable


def main():
    # Exit through the context manager on a hook's teardown, so the log directory is removed.
    for number in (signal.SIGTERM, signal.SIGHUP):
        signal.signal(number, lambda number, frame: sys.exit(128 + number))
    env = {key: value for key, value in os.environ.items() if key not in GIT_VARIABLES}
    python = interpreter(env)
    with tempfile.TemporaryDirectory() as logs:
        jobs = []
        for test in sorted((ROOT / 'tests').glob('test_*.py')):
            log = open(Path(logs) / f'{test.stem}.log', 'w+', errors='replace')
            jobs.append((test.stem, log, subprocess.Popen([python, '-B', str(test)], stdin=subprocess.DEVNULL,
                                                          stdout=log, stderr=subprocess.STDOUT, env=env)))
        failed = False
        for name, log, process in jobs:
            if process.wait():
                failed = True
                log.seek(0)
                print(f'FAIL {name}')
                print(''.join(log.readlines()[-20:]), end='')
            log.close()
    if not failed:
        print(f'{len(jobs)} regression scripts passed ({python})')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
