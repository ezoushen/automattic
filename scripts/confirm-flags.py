#!/usr/bin/env python3
"""Confirm suspected masked-rule flags by running the flagged test with the rejecting check removed.

Opt-in and language-free: each flag supplies the project's own test command and a diff that removes one check.
Every run happens in a temporary detached git worktree at --ref; the checkout itself is never modified.
confirmed: the test still passes without the check. dismissed: it fails and its output contains the flag's
fails_with text. failed: it fails some other way, for the agent to read. unverified: no evidence either way.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import threading
import time

LIVE, LOCK, STOPPING = set(), threading.Lock(), threading.Event()


def load(path):
    flags = json.loads(Path(path).read_text())
    if not isinstance(flags, list) or not flags:
        raise ValueError('Input must be a nonempty list of flags')
    for flag in flags:
        if (not isinstance(flag, dict) or not {'id', 'command', 'diff'} <= set(flag) <= {'id', 'command', 'diff', 'fails_with'}
                or not isinstance(flag['id'], str) or not flag['id'].strip()
                or not isinstance(flag['command'], list) or not flag['command']
                or not all(isinstance(arg, str) for arg in flag['command'])
                or not isinstance(flag['diff'], str) or not flag['diff'].strip()
                or not isinstance(flag.get('fails_with', 'x'), str) or not flag.get('fails_with', 'x').strip()):
            raise ValueError('Each flag requires id, command (argument list) and a nonempty diff; fails_with is optional text')
    if len({flag['id'] for flag in flags}) != len(flags):
        raise ValueError('Flag ids must be unique')
    return flags


def git(repo, *args, **kwargs):
    return subprocess.run(['git', '-C', str(repo), *args], capture_output=True, text=True, **kwargs)


def stop(process):
    """Stop the command and everything it started: test runners often spawn their own children."""
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass


def run(command, cwd, timeout):
    """Return (exit code or None, output tail, seconds); None means it timed out or could not start."""
    started = time.monotonic()
    if STOPPING.is_set():
        return None, 'stopped before running', 0.0
    try:
        process = subprocess.Popen(command, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                   start_new_session=True)
    except OSError as error:
        return None, f'could not start the command: {error}', time.monotonic() - started
    with LOCK:
        LIVE.add(process)
    try:
        output, _ = process.communicate(timeout=timeout)
        return process.returncode, output[-1500:], time.monotonic() - started
    except subprocess.TimeoutExpired:
        stop(process)
        process.communicate()
        return None, f'timed out after {timeout}s', time.monotonic() - started
    finally:
        stop(process)  # leftover descendants of a finished command
        with LOCK:
            LIVE.discard(process)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--input', type=Path, required=True, help='JSON list of {id, command, diff, fails_with?}')
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

    def terminate(signum, frame):
        STOPPING.set()
        with LOCK:
            for process in list(LIVE):
                stop(process)
        raise SystemExit(128 + signum)  # unwinds into the cleanup below

    for signum in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(signum, terminate)

    def worktree(name):
        path = root / name
        added = git(args.repo, 'worktree', 'add', '--detach', '--quiet', str(path), ref)
        if added.returncode:
            raise RuntimeError(f'worktree: {added.stderr.strip()}')
        return path

    def baseline(index, command):
        # The unchanged test must pass first, or a failure with the check removed proves nothing.
        return run(command, worktree(f'baseline-{index}'), args.timeout)

    def confirm(index, flag, baselines):
        code, output, seconds = baselines[tuple(flag['command'])]
        if code != 0:
            return {'status': 'unverified', 'reason': f'baseline {output}' if code is None else 'the baseline run of the unchanged test fails',
                    'exit': code, 'seconds': round(seconds, 2), 'output_tail': output}
        path = worktree(f'flag-{index}')
        applied = git(path, 'apply', '--whitespace=nowarn', '-', input=flag['diff'] if flag['diff'].endswith('\n')
                      else flag['diff'] + '\n')
        if applied.returncode:
            return {'status': 'unverified', 'reason': f'diff does not apply: {applied.stderr.strip()[:300]}'}
        code, output, seconds = run(flag['command'], path, args.timeout)
        if code is None:
            status, reason = 'unverified', output
        elif code == 0:
            status, reason = 'confirmed', 'the test still passes without the check'
        elif 'fails_with' in flag and flag['fails_with'] in output:
            status, reason = 'dismissed', 'the test fails at the expected point without the check'
        else:
            status, reason = 'failed', 'the test fails; read the output to see whether an assertion failed'
        return {'status': status, 'reason': reason, 'exit': code, 'seconds': round(seconds, 2), 'output_tail': output}

    try:
        commands = list(dict.fromkeys(tuple(flag['command']) for flag in flags))
        with ThreadPoolExecutor(max(1, args.jobs)) as pool:
            baselines = dict(zip(commands, pool.map(lambda item: baseline(item[0], list(item[1])), enumerate(commands))))
            results = list(pool.map(lambda item: {'id': item[1]['id'], **confirm(item[0], item[1], baselines)},
                                    enumerate(flags)))
    finally:
        with LOCK:
            for process in list(LIVE):
                stop(process)
        for path in root.iterdir():
            git(args.repo, 'worktree', 'remove', '--force', str(path))
        shutil.rmtree(root, ignore_errors=True)
        git(args.repo, 'worktree', 'prune')
    print(json.dumps({'ref': ref, 'results': results}, indent=2))


if __name__ == '__main__':
    main()
