#!/usr/bin/env python3
"""Confirm suspected masked-rule flags by running the flagged test with the rejecting check removed.

Opt-in and language-free: each flag supplies the project's own test command and a diff that removes one check.
Every run happens in a temporary detached git worktree at --ref; the checkout itself is never modified.
confirmed: the test still passes without the check. dismissed: it fails. unverified: no evidence either way.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time


def load(path):
    flags = json.loads(Path(path).read_text())
    if not isinstance(flags, list) or not flags:
        raise ValueError('Input must be a nonempty list of flags')
    for flag in flags:
        if (not isinstance(flag, dict) or set(flag) != {'id', 'command', 'diff'} or not isinstance(flag['id'], str)
                or not flag['id'].strip() or not isinstance(flag['command'], list) or not flag['command']
                or not all(isinstance(arg, str) for arg in flag['command'])
                or not isinstance(flag['diff'], str) or not flag['diff'].strip()):
            raise ValueError('Each flag requires id, command (argument list) and a nonempty diff')
    if len({flag['id'] for flag in flags}) != len(flags):
        raise ValueError('Flag ids must be unique')
    return flags


def git(repo, *args, **kwargs):
    return subprocess.run(['git', '-C', str(repo), *args], capture_output=True, text=True, **kwargs)


def run(command, cwd, timeout):
    started = time.monotonic()
    try:
        process = subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return process.returncode, (process.stdout + process.stderr)[-1500:], time.monotonic() - started
    except subprocess.TimeoutExpired:
        return None, f'timed out after {timeout}s', time.monotonic() - started


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--input', type=Path, required=True, help='JSON list of {id, command, diff}')
    parser.add_argument('--ref', default='HEAD')
    parser.add_argument('--jobs', type=int, default=os.cpu_count() or 2)
    parser.add_argument('--timeout', type=float, default=600, help='seconds per test run')
    args = parser.parse_args()
    try:
        flags = load(args.input)
        resolved = git(args.repo, 'rev-parse', '--verify', f'{args.ref}^{{commit}}')
        if resolved.returncode:
            raise ValueError(f'Cannot resolve {args.ref}: {resolved.stderr.strip()}')
        ref = resolved.stdout.strip()
    except (OSError, ValueError) as error:
        parser.exit(2, f'{error}\n')
    root = Path(tempfile.mkdtemp(prefix='confirm-flags-'))

    def worktree(name):
        path = root / name
        added = git(args.repo, 'worktree', 'add', '--detach', '--quiet', str(path), ref)
        if added.returncode:
            raise RuntimeError(f'worktree: {added.stderr.strip()}')
        return path

    def baseline(command):
        # The unchanged test must pass first, or a failure with the check removed proves nothing.
        path = worktree(f'baseline-{abs(hash(tuple(command)))}')
        return run(command, path, args.timeout)

    def confirm(flag, baselines):
        code, output, seconds = baselines[tuple(flag['command'])]
        if code != 0:
            return {'status': 'unverified', 'reason': 'baseline run failed without any change' if code is not None
                    else f'baseline {output}', 'exit': code, 'seconds': round(seconds, 2), 'output_tail': output}
        path = worktree(f"flag-{abs(hash(flag['id']))}")
        patch = path / '.confirm-flag.diff'
        patch.write_text(flag['diff'] if flag['diff'].endswith('\n') else flag['diff'] + '\n')
        applied = git(path, 'apply', '--whitespace=nowarn', str(patch))
        patch.unlink()
        if applied.returncode:
            return {'status': 'unverified', 'reason': f'diff does not apply: {applied.stderr.strip()[:300]}'}
        code, output, seconds = run(flag['command'], path, args.timeout)
        status = 'unverified' if code is None else 'confirmed' if code == 0 else 'dismissed'
        reason = (output if code is None else 'the test still passes without the check' if code == 0
                  else 'the test fails without the check')
        return {'status': status, 'reason': reason, 'exit': code, 'seconds': round(seconds, 2), 'output_tail': output}

    try:
        commands = list(dict.fromkeys(tuple(flag['command']) for flag in flags))
        with ThreadPoolExecutor(max(1, args.jobs)) as pool:
            baselines = dict(zip(commands, pool.map(lambda command: baseline(list(command)), commands)))
            results = list(pool.map(lambda flag: {'id': flag['id'], **confirm(flag, baselines)}, flags))
    finally:
        for path in root.iterdir():
            git(args.repo, 'worktree', 'remove', '--force', str(path))
        shutil.rmtree(root, ignore_errors=True)
        git(args.repo, 'worktree', 'prune')
    print(json.dumps({'ref': ref, 'results': results}, indent=2))


if __name__ == '__main__':
    main()
