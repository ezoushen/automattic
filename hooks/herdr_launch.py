#!/usr/bin/env python3
"""PreToolUse hook: log each `herdr agent start` a session runs, so the yield gate can name unregistered workers.

Appends one JSON line per launch to the main checkout's .scratch/herdr-launches.jsonl: the time, agent name and
pane, the coordinator (its HERDR_PANE_ID and host session ID) and the pane's cwd when Herdr reports it. Claude and
Codex run it before Bash; Pi's extension passes its bash and bg_run calls. It never blocks the command.

`herdr_launch.py dismiss --pane <pane> | --name <agent> --reason <text>`, run in the checkout, appends a dismissal
that accounts for the launches of that pane or agent name logged before it, such as one that failed or a probe.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import pr_body
import yield_gate


def starts(command):
    """Yield (Herdr session or None, agent name, pane) for each `herdr [--session S] agent start` the command runs."""
    for tokens, _ in pr_body.logical_lines(command):
        start = 0
        for index, token in enumerate(tokens + [';']):
            if token not in pr_body.SEPARATORS and index < len(tokens):
                continue
            words, start = pr_body.unwrap(tokens[start:index]), index + 1
            while words and pr_body.ASSIGNMENT.match(words[0]):
                words = pr_body.unwrap(words[1:])
            if not words or Path(words[0]).name != 'herdr':
                continue
            session, words = None, words[1:]
            if words[:1] == ['--session'] and len(words) > 1:
                session, words = words[1], words[2:]
            if words[:2] != ['agent', 'start']:
                continue
            words = words[2:words.index('--')] if '--' in words else words[2:]
            names, options, at = [], {}, 0
            while at < len(words):
                flag, joined, value = words[at].partition('=')
                if flag.startswith('--'):
                    if not joined:
                        value, at = (words[at + 1] if at + 1 < len(words) else ''), at + 1
                    options[flag] = value
                else:
                    names.append(words[at])
                at += 1
            yield session, names[0] if names else None, options.get('--pane')


def pane_cwd(session, pane):
    """The pane's working directory as its Herdr server reports it, or None."""
    try:
        result = subprocess.run(['herdr', *(['--session', session] if session else []), 'pane', 'get', pane],
                                capture_output=True, text=True, timeout=3)
        return json.loads(result.stdout)['result']['pane'].get('cwd') if result.returncode == 0 else None
    except Exception:
        return None  # An unknown cwd still counts at stop.


def main():
    try:
        event = json.load(sys.stdin)
        command = (event.get('tool_input') or {}).get('command') or ''
        launches = list(starts(command)) if 'herdr' in command else []
        if not launches:
            return
        root = yield_gate.main_checkout(event.get('cwd') or os.getcwd())
        if root is None:
            return
        coordinator = {'pane': os.environ.get('HERDR_PANE_ID'), 'session': event.get('session_id')}
        log = root / yield_gate.LAUNCHES
        log.parent.mkdir(parents=True, exist_ok=True)
        for session, agent, pane in launches:
            record = {'time': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'agent': agent, 'pane': pane,
                      'coordinator': coordinator}
            cwd = pane and pane_cwd(session, pane)
            with log.open('a') as stream:
                stream.write(json.dumps(dict(record, **({'cwd': cwd} if cwd else {}))) + '\n')
    except Exception:
        return  # Recording never blocks the command.


def dismiss(argv):
    """Append a dismissal of the earlier launches of one pane or agent name, with the reason they need no attempt."""
    parser = argparse.ArgumentParser(prog='herdr_launch.py dismiss')
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument('--pane')
    target.add_argument('--name')
    parser.add_argument('--reason', required=True)
    args = parser.parse_args(argv)
    if not args.reason.strip():
        parser.error('--reason must say why the launch needs no registered attempt')
    root = yield_gate.main_checkout(os.getcwd())
    if root is None:
        parser.error('run it inside the checkout whose launches it dismisses')
    record = {'time': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
              'dismissed': {'pane': args.pane} if args.pane else {'agent': args.name}, 'reason': args.reason}
    with (root / yield_gate.LAUNCHES).open('a') as stream:
        stream.write(json.dumps(record) + '\n')


if __name__ == '__main__':
    if sys.argv[1:2] == ['dismiss']:
        dismiss(sys.argv[2:])
    else:
        main()
