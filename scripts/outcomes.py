#!/usr/bin/env python3
"""Keep each worker attempt's outcome across efforts and summarise it per role and candidate.

The worker lifecycle writes an attempt's result, acceptance or decline, and later reverts.
`import` adds past decision journals once. Implementers succeed when accepted; other roles
when their work completed. A revert, a decline or a failed or blocked result is a failure.
"""

import argparse
import json
import os
from pathlib import Path
import sqlite3
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import decision_journal  # noqa: E402


def ledger_path():
    state = Path(os.environ.get('XDG_STATE_HOME') or Path.home() / '.local/state').expanduser()
    if not state.is_absolute():
        raise ValueError('XDG_STATE_HOME must be an absolute directory')
    return state / 'automattic/outcomes.sqlite'


def connect():
    path = ledger_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=30, isolation_level=None)
    db.execute('PRAGMA journal_mode=WAL')
    db.execute('CREATE TABLE IF NOT EXISTS outcomes (key TEXT PRIMARY KEY, data TEXT NOT NULL)')
    return db


def put(key, row):
    """Write one attempt's current outcome; the latest write for a key wins."""
    db = connect()
    try:
        db.execute('INSERT OR REPLACE INTO outcomes VALUES (?, ?)',
                   (key, json.dumps(dict(row, recorded_at=time.time()))))
    finally:
        db.close()


def verdict(row):
    """'success', 'failure' or 'pending' for one attempt's outcome."""
    if row.get('reverts') or row.get('declined') or row.get('status') == 'failed':
        return 'failure'
    if row.get('status') != 'succeeded':
        return 'pending'
    if row.get('role') == 'implementer' and not row.get('accepted'):
        return 'pending'
    return 'success'


def summary(role=None):
    db = connect()
    try:
        rows = [json.loads(data) for (data,) in db.execute('SELECT data FROM outcomes ORDER BY key')]
    finally:
        db.close()
    roles = {}
    for row in rows:
        if role is not None and row.get('role') != role:
            continue
        counts = roles.setdefault(row['role'], {}).setdefault(
            row['candidate'], {'successes': 0, 'failures': 0, 'pending': 0})
        counts[{'success': 'successes', 'failure': 'failures', 'pending': 'pending'}[verdict(row)]] += 1
    return roles


def journal_rows(path):
    """Worker-selection outcomes from a decision journal, keyed by journal and decision."""
    rows = decision_journal.read(path)
    latest = {}
    for row in rows:
        if row['event'] in ('action', 'outcome'):
            latest.setdefault(row['decision_id'], {})[row['event']] = row
    for row in rows:
        request = row.get('request') if row['event'] == 'decision' else None
        if not isinstance(request, dict) or request.get('family') != 'worker-selection':
            continue
        state = request.get('state', '')
        if not state.startswith('Role: '):
            continue
        events = latest.get(row['decision_id'], {})
        choice = events.get('action', {}).get('choice') or (row.get('result') or {}).get('choice')
        option = request.get('options', {}).get(choice)
        if not option:
            continue
        outcome = events.get('outcome', {})
        role = state[len('Role: '):].split('\n', 1)[0]
        status = outcome.get('status', 'unknown')
        yield f"{Path(path).resolve()}#{row['decision_id']}", {
            'source': str(Path(path).resolve()), 'attempt': row.get('assignment'), 'role': role,
            'candidate': json.loads(option)['candidate'], 'status': status,
            # A journal records success when the host accepted the work.
            'accepted': role == 'implementer' and status == 'succeeded' or None,
            'reverts': outcome.get('metrics', {}).get('reverts', 0)}


def import_journals(paths):
    db = connect()
    try:
        known = {key for (key,) in db.execute('SELECT key FROM outcomes')}
    finally:
        db.close()
    imported = already = 0
    for path in paths:
        for key, row in journal_rows(path):
            if key in known:
                already += 1
                continue
            put(key, row)
            known.add(key)
            imported += 1
    return {'imported': imported, 'already': already}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest='command', required=True)
    report = commands.add_parser('summary', help='successes, failures and pending attempts per role and candidate')
    report.add_argument('--role')
    load = commands.add_parser('import', help='add past decision journals once')
    load.add_argument('journals', nargs='+', type=Path)
    args = parser.parse_args()
    try:
        if args.command == 'summary':
            result = {'ledger': str(ledger_path()), 'roles': summary(args.role)}
        else:
            result = import_journals(args.journals)
    except (OSError, ValueError, sqlite3.Error) as error:
        parser.exit(2, f'{error}\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
