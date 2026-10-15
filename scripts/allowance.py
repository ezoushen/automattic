#!/usr/bin/env python3
"""Report how much of the Claude Code and Codex subscription windows is used, and the pressure level.

Codex readings come from the newest rollout's `token_count.rate_limits`. Claude readings come from
a snapshot that `record-claude` writes from the status line's JSON input, for example by adding
`printf '%s' "$JSON" | python3 <plugin>/scripts/allowance.py record-claude` to the status-line script.
A window's projected use at reset counts once a quarter of it has passed and while the reading is under
15 minutes old; an older reading counts only what was already used. Levels: `elevated` from
80% used or projected and `critical` from 90%; they fall only below 65% and 80% respectively and
after five minutes at the level, remembered between `status` and `record-claude` runs. No reading is
`unknown`, never zero.
"""

import argparse
import json
import os
from pathlib import Path
import sys
import time

LEVELS = ('normal', 'elevated', 'critical')
ENTER = {'elevated': 80, 'critical': 90}
LEAVE = {'elevated': 65, 'critical': 80}
DWELL = 300
TRUSTED_ELAPSED = 0.25
STALE_SECONDS = 900
CLAUDE_WINDOWS = {'five_hour': 300, 'seven_day': 10080}


def state_dir():
    state = Path(os.environ.get('XDG_STATE_HOME') or Path.home() / '.local/state').expanduser()
    if not state.is_absolute():
        raise ValueError('XDG_STATE_HOME must be an absolute directory')
    return state / 'automattic'


def codex_sessions():
    return Path(os.environ.get('CODEX_HOME') or Path.home() / '.codex') / 'sessions'


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f'.{os.getpid()}.tmp')
    temporary.write_text(json.dumps(value))
    temporary.replace(path)


def record_claude(stream, now, codex_root):
    """Keep the status line's rate limits and refresh the levels' memory; anything unreadable is ignored so
    the status line never fails."""
    try:
        limits = json.load(stream).get('rate_limits')
        if isinstance(limits, dict) and limits:
            write_json(state_dir() / 'claude-allowance.json', {'recorded_at': now, 'rate_limits': limits})
            status(codex_root or codex_sessions(), now)
    except (OSError, ValueError, AttributeError, KeyError):
        pass


def window(used, minutes, resets_at, now):
    """One current window with its elapsed share and, once trusted, its projected use at reset."""
    if not all(isinstance(value, (int, float)) for value in (used, minutes, resets_at)) or resets_at <= now:
        return None
    elapsed = round(min(1.0, max(0.0, 1 - (resets_at - now) / (minutes * 60))), 3)
    projected = round(used / elapsed, 1) if elapsed >= TRUSTED_ELAPSED else None
    return {'window_minutes': minutes, 'used_percent': used, 'resets_at': resets_at, 'elapsed': elapsed,
            'projected_percent': projected}


def codex_reading(root, now):
    for path in sorted(root.glob('**/rollout-*.jsonl'), key=lambda path: path.stat().st_mtime, reverse=True):
        limits = None
        with path.open(encoding='utf-8', errors='replace') as stream:
            for line in stream:
                if '"rate_limits"' not in line:
                    continue
                try:
                    payload = json.loads(line).get('payload', {})
                except ValueError:
                    continue
                found = payload.get('rate_limits') if payload.get('type') == 'token_count' else None
                if isinstance(found, dict) and found.get('limit_id') in (None, 'codex'):
                    limits = found
        if limits:
            windows = [window(part.get('used_percent'), part.get('window_minutes'), part.get('resets_at'), now)
                       for part in (limits.get('primary'), limits.get('secondary')) if isinstance(part, dict)]
            return {'age_seconds': round(now - path.stat().st_mtime), 'windows': [w for w in windows if w]}
    return None


def claude_reading(now):
    try:
        snapshot = json.loads((state_dir() / 'claude-allowance.json').read_text())
    except (OSError, ValueError):
        return None
    windows = [window(part.get('used_percentage'), minutes, part.get('resets_at'), now)
               for name, minutes in CLAUDE_WINDOWS.items()
               if isinstance(part := snapshot['rate_limits'].get(name), dict)]
    return {'age_seconds': round(now - snapshot['recorded_at']), 'windows': [w for w in windows if w]}


def settle(previous, score, now):
    """The pressure level for this score, holding a higher level until use falls well below it and a dwell passes."""
    target = 'critical' if score >= ENTER['critical'] else 'elevated' if score >= ENTER['elevated'] else 'normal'
    level = previous.get('level', 'normal')
    if LEVELS.index(target) >= LEVELS.index(level):
        return target
    if now - previous.get('since', 0) < DWELL:
        return level
    if level == 'critical' and score >= LEAVE['critical']:
        return 'critical'
    return 'elevated' if score >= LEAVE['elevated'] else 'normal'


def status(codex_root, now, persist=True):
    """Readings and levels per provider; `persist` keeps the levels for the next call's hysteresis."""
    path = state_dir() / 'allowance-levels.json'
    try:
        stored = json.loads(path.read_text())
    except (OSError, ValueError):
        stored = {}
    providers = {}
    for name, reading in (('claude', claude_reading(now)), ('codex', codex_reading(codex_root, now))):
        if not reading:
            providers[name] = {'level': 'unknown', 'reason': 'no reading'}
            continue
        # Use never falls before a reset, so a stale reading still sets a floor; its rate is unknown.
        reading['stale'] = reading['age_seconds'] > STALE_SECONDS
        if reading['stale']:
            for item in reading['windows']:
                item['projected_percent'] = None
        if not reading['windows']:
            providers[name] = dict(reading, level='unknown', reason='no current window')
            continue
        score = max(max(w['used_percent'], w['projected_percent'] or 0) for w in reading['windows'])
        previous = stored.get(name, {})
        level = settle(previous, score, now)
        if level != previous.get('level'):
            stored[name] = {'level': level, 'since': now}
        providers[name] = dict(reading, level=level)
    if persist:
        try:
            write_json(path, stored)
        except OSError:
            pass  # The levels still apply; only their hysteresis memory is lost.
    return {'providers': providers}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest='command', required=True)
    report = commands.add_parser('status', help='windows, projections and pressure level per provider')
    report.add_argument('--codex-root', type=Path, help='default: $CODEX_HOME/sessions or ~/.codex/sessions')
    report.add_argument('--now', type=float, help=argparse.SUPPRESS)
    record = commands.add_parser('record-claude', help='keep the rate limits from status-line JSON on stdin')
    record.add_argument('--codex-root', type=Path, help='default: $CODEX_HOME/sessions or ~/.codex/sessions')
    record.add_argument('--now', type=float, help=argparse.SUPPRESS)
    args = parser.parse_args()
    now = args.now if args.now is not None else time.time()
    if args.command == 'record-claude':
        record_claude(sys.stdin, now, args.codex_root)
        return
    try:
        print(json.dumps(status(args.codex_root or codex_sessions(), now), indent=2))
    except (OSError, ValueError) as error:
        parser.exit(2, f'{error}\n')


if __name__ == '__main__':
    main()
