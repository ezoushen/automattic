#!/usr/bin/env python3
"""Stop hook: keep the host working while a lifecycle worker could finish without waking it.

Reads every run's workers.sqlite under the main checkout's .scratch/*/reports/ that
changed in the last day, without writing to it, and applies the lifecycle's yield
gate. A coordinator (a session whose pane or session no launch or attempt names as a
worker) is also held for each Herdr worker in a ticket worktree that no attempt accounts
for and it did not dismiss: each launch it logged (hooks/herdr_launch.py) and each other
live agent of its Herdr workspace. A check that cannot run, and an unreadable launch log
line, are named gaps, never a pass. `claude` and `codex` speak their shared Stop
hook protocol; `check <cwd> [session]` prints the gaps as JSON for other hosts. Set
AUTOMATTIC_YIELD_HOOK=off to disable the check.
"""
import calendar
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
GUIDE = ROOT / 'runtime/workers/wait.md'
PREPARE = ROOT / 'runtime/workers/prepare.md'
# hooks/herdr_launch.py appends each `herdr agent start` here, one JSON object per line.
LAUNCHES = '.scratch/herdr-launches.jsonl'


def lifecycle():
    spec = importlib.util.spec_from_file_location('worker_lifecycle', ROOT / 'scripts/worker_lifecycle.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main_checkout(cwd):
    """The main checkout holding cwd, None outside any repository; raises when git cannot tell."""
    result = subprocess.run(['git', '-C', str(cwd), 'rev-parse', '--path-format=absolute', '--git-common-dir'],
                            capture_output=True, text=True, timeout=5, env=dict(os.environ, LC_ALL='C'))
    if result.returncode == 0:
        return Path(result.stdout.strip()).parent
    if 'not a git repository' in result.stderr:
        return None
    raise RuntimeError(f'git rev-parse exited {result.returncode}: {result.stderr.strip()}')


def gaps(cwd, session=None):
    root = main_checkout(cwd)
    if root is None:
        return []
    # A session is a worker exactly when its launch set AUTOMATTIC_WORKER; any other session is a coordinator.
    pane, worker = os.environ.get('HERDR_PANE_ID'), bool(os.environ.get('AUTOMATTIC_WORKER'))
    module, missing = None, []
    for state in sorted(root.glob('.scratch/*/reports/workers.sqlite')):
        if time.time() - state.stat().st_mtime > RECENT_SECONDS:
            continue
        module = module or lifecycle()
        db = sqlite3.connect(f'{state.as_uri()}?mode=ro', uri=True, timeout=5)
        try:
            def coordinated(saved):
                if pane and saved.get('coordinator'):
                    return saved['coordinator'] == pane
                return not worker
            missing += [f'{state}: {gap}' for gap in module.yield_gaps(db, coordinated)]
        finally:
            db.close()
    # Only a coordinator answers for its launches and the live agents in its workspace's worktrees.
    return missing + ([] if worker else unregistered(root, pane, session))


def herdr_agents():
    """The live agents the session's Herdr server reports."""
    result = subprocess.run(['herdr', 'agent', 'list'], capture_output=True, text=True, timeout=5)
    if result.returncode:
        raise RuntimeError(f'herdr agent list exited {result.returncode}: {(result.stderr or result.stdout).strip()}')
    return json.loads(result.stdout)['result']['agents']


def same_coordinator(theirs, pane, session):
    """Whether a recorded coordinator ({pane, session}) is this session: pane and host session must both match when
    both sides know the session, so a pane ID that a restarted Herdr reuses inherits nothing; else the pane decides."""
    if theirs['session'] and session:
        return theirs == {'pane': pane, 'session': session}
    return bool(pane) and theirs['pane'] == pane


def handles(worker):
    """What a registered worker matches: itself, and the pane and name of a `<session>/<pane>/<name>` handle."""
    parts = worker.rsplit('/', 2)
    return {worker, *parts[1:]} if len(parts) == 3 else {worker}


def clears(saved, launch):
    """Whether an attempt accounts for a logged launch: it names the launch's pane or agent, and its coordinator
    recorded at registration is the launch's pane or, with none recorded, it was registered no earlier."""
    if not handles(saved['worker']) & {launch['agent'], launch['pane']}:
        return False
    if saved.get('coordinator'):
        return saved['coordinator'] == launch['coordinator']['pane']
    return (saved['registered_at'] or 0) >= calendar.timegm(time.strptime(launch['time'], '%Y-%m-%dT%H:%M:%SZ'))


def readable(record):
    """Whether a launch log line holds a launch or a dismissal the gate can match."""
    if not isinstance(record, dict):
        return False
    if 'dismissed' in record:
        return isinstance(record['dismissed'], dict) and isinstance(record.get('by'), dict)
    return isinstance(record.get('coordinator'), dict) and {'time', 'agent', 'pane'} <= record.keys()


def unregistered(root, pane, session):
    """Name each Herdr worker that no attempt in any run and no dismissal of this coordinator accounts for: each
    launch it logged into a ticket worktree or an unknown cwd, and each other live agent in a ticket worktree of its
    Herdr workspace; and each unreadable log line."""
    module, attempts = None, []
    for state in root.glob('.scratch/*/reports/workers.sqlite'):
        module = module or lifecycle()
        db = sqlite3.connect(f'{state.as_uri()}?mode=ro', uri=True, timeout=5)
        try:
            registered = {row[0]: json.loads(row[1])['recorded_at']
                          for row in db.execute("SELECT attempt, payload FROM events WHERE kind = 'register'")}
            attempts += [dict(saved, registered_at=registered.get(saved['attempt'])) for saved in module.attempts(db)]
        finally:
            db.close()
    workers = {handle for saved in attempts for handle in handles(saved['worker'])}
    log, worktrees = root / LAUNCHES, (root / '.worktrees').resolve()
    records, unreadable = [], []
    for number, line in enumerate(log.read_text().splitlines() if log.is_file() else [], 1):
        try:
            record = json.loads(line)
        except ValueError:
            record = None
        if readable(record):
            records.append(record)
        else:  # Named, and ignored for matching, so one bad line hides no other gap.
            unreadable.append(f'{log}: launch log line {number} is unreadable; fix or remove it')
    launches = []
    for record in records:
        if 'dismissed' in record:  # Accounts for its coordinator's launches of that pane or name logged before it.
            launches = [launch for launch in launches
                        if any(launch.get(key) != value for key, value in record['dismissed'].items())
                        or not same_coordinator(launch['coordinator'], record['by']['pane'], record['by']['session'])]
        else:
            launches.append(record)
    launches = [launch for launch in launches if same_coordinator(launch['coordinator'], pane, session)
                and not any(clears(saved, launch) for saved in attempts)
                and ('cwd' not in launch or Path(launch['cwd']).resolve().is_relative_to(worktrees))]
    workers |= {handle for launch in launches for handle in (launch['agent'], launch['pane'])}  # Named once.
    workers |= {value for record in records if 'dismissed' in record  # This coordinator's dismissals cover live agents.
                and same_coordinator(record['by'], pane, session) for value in record['dismissed'].values()}
    workspace, failed = os.environ.get('HERDR_WORKSPACE_ID'), []
    try:
        agents = herdr_agents() if workspace and worktrees.is_dir() else []  # No worktrees, no ticket workers.
    except Exception as error:  # A check that cannot run is a named gap, never a pass.
        agents, failed = [], [f'could not check Herdr workers: {error}']
    live = [agent for agent in agents
            if agent.get('workspace_id') == workspace and agent['pane_id'] != pane and agent.get('cwd')
            and Path(agent['cwd']).resolve().is_relative_to(worktrees)
            and not workers & {agent.get('name'), agent['pane_id']}]
    return ([f"{log}: {launch['agent']} (pane {launch['pane']}): launched without a registered attempt"
             for launch in launches]
            + [f"Herdr agent {agent.get('name')} (pane {agent['pane_id']}) runs in {agent['cwd']} "
               'without a registered attempt' for agent in live] + unreadable + failed)


def checked(cwd, session=None):
    """The gaps, or one naming why the check could not run: a broken check never passes silently."""
    try:
        return gaps(cwd, session)
    except Exception as error:
        return [f'could not check workers: {error}']


def reason(missing, session=None):
    dismiss = f"python3 {ROOT}/hooks/herdr_launch.py dismiss --pane <pane>{f' --session {session}' if session else ''}"
    return ('These workers could finish or run without waking you:\n'
            + ''.join(f'- {gap}\n' for gap in missing)
            + f'Register each launched worker, or dismiss a launch that needs none with `{dismiss} --reason <why>` '
            + f'({PREPARE}). '
            + 'Arm a notified wait, recover the receipt or collect the '
            + 'result (for a worker that is gone, a failed or cancelled result whose report says what was lost) '
            + f'before stopping ({GUIDE}).')


def main():
    if os.environ.get('AUTOMATTIC_YIELD_HOOK') == 'off':
        return 0
    if sys.argv[1:2] == ['check'] and len(sys.argv) in (3, 4):
        print(json.dumps({'missing': checked(Path(sys.argv[2]), *sys.argv[3:])}))
        return 0
    if sys.argv[1:] not in (['claude'], ['codex']):
        sys.exit('usage: yield_gate.py claude|codex < stop-hook-input, or yield_gate.py check <cwd> [session]')
    payload = json.load(sys.stdin)
    if payload.get('stop_hook_active'):
        return 0
    missing = checked(Path(payload.get('cwd') or os.getcwd()), payload.get('session_id'))
    if missing:
        print(json.dumps({'decision': 'block', 'reason': reason(missing, payload.get('session_id'))}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
