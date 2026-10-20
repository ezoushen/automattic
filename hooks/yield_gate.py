#!/usr/bin/env python3
"""Stop hook: keep the host working while a lifecycle worker could finish without waking it.

Reads every run's workers.sqlite under the main checkout's .scratch/*/reports/ that
changed in the last day, without writing to it, and applies the lifecycle's yield
gate. A coordinator (a session outside .worktrees/) is also held for each Herdr worker
in a ticket worktree that no attempt in any run registers: each launch it logged and
did not dismiss (hooks/herdr_launch.py) and each other live agent of its Herdr workspace. A check that
cannot run is a named gap, never a pass. `claude` and `codex` speak their shared Stop
hook protocol; `check <cwd> [session]` prints the gaps as JSON for other hosts. Set
AUTOMATTIC_YIELD_HOOK=off to disable the check.
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
    return missing + unregistered(root, pane, session)


def herdr_agents():
    """The live agents the session's Herdr server reports."""
    result = subprocess.run(['herdr', 'agent', 'list'], capture_output=True, text=True, timeout=5)
    if result.returncode:
        raise RuntimeError(f'herdr agent list exited {result.returncode}: {(result.stderr or result.stdout).strip()}')
    return json.loads(result.stdout)['result']['agents']


def launched_by(launch, pane, session):
    """Whether this session logged the launch: pane and host session must both match when both sides know the
    session, so a pane ID that a restarted Herdr reuses inherits nothing; otherwise the pane alone decides."""
    theirs = launch['coordinator']
    if theirs['session'] and session:
        return theirs == {'pane': pane, 'session': session}
    return bool(pane) and theirs['pane'] == pane


def handles(worker):
    """What a registered worker matches: itself, and the pane and name of a `<session>/<pane>/<name>` handle."""
    parts = worker.rsplit('/', 2)
    return {worker, *parts[1:]} if len(parts) == 3 else {worker}


def is_worker(pane, session, attempts, records):
    """Whether this session is a worker, wherever its cwd: Herdr launched or registered its pane or, outside Herdr,
    its session is an attempt's native session."""
    if pane:
        return (any(record.get('pane') == pane for record in records if 'dismissed' not in record)
                or any(pane in handles(saved['worker']) for saved in attempts))
    return any(saved['native_session'] == session for saved in attempts)


def unregistered(root, pane, session):
    """Name each Herdr worker that no attempt in any run registers: each launch this coordinator logged into a
    ticket worktree or an unknown cwd, and each other live agent in a ticket worktree of its Herdr workspace."""
    module, attempts = None, []
    for state in root.glob('.scratch/*/reports/workers.sqlite'):
        module = module or lifecycle()
        db = sqlite3.connect(f'{state.as_uri()}?mode=ro', uri=True, timeout=5)
        try:
            attempts += module.attempts(db)
        finally:
            db.close()
    workers = {handle for saved in attempts for handle in handles(saved['worker'])}
    log, worktrees = root / LAUNCHES, (root / '.worktrees').resolve()
    records = [json.loads(line) for line in log.read_text().splitlines()] if log.is_file() else []
    if is_worker(pane, session, attempts, records):
        return []  # Only its coordinator answers for its own launches and its siblings.
    launches = []
    for record in records:
        if 'dismissed' in record:  # Accounts for the launches of that pane or agent name logged before it.
            launches = [launch for launch in launches
                        if any(launch.get(key) != value for key, value in record['dismissed'].items())]
        else:
            launches.append(record)
    launches = [launch for launch in launches if launched_by(launch, pane, session)
                and not workers & {launch['agent'], launch['pane']}
                and ('cwd' not in launch or Path(launch['cwd']).resolve().is_relative_to(worktrees))]
    workers |= {handle for launch in launches for handle in (launch['agent'], launch['pane'])}  # Named once.
    workspace, failed = os.environ.get('HERDR_WORKSPACE_ID'), []
    try:
        agents = herdr_agents() if workspace else []
    except Exception as error:  # A check that cannot run is a named gap, never a pass.
        agents, failed = [], [f'could not check Herdr workers: {error}']
    live = [agent for agent in agents
            if agent.get('workspace_id') == workspace and agent['pane_id'] != pane and agent.get('cwd')
            and Path(agent['cwd']).resolve().is_relative_to(worktrees)
            and not workers & {agent.get('name'), agent['pane_id']}]
    return ([f"{log}: {launch['agent']} (pane {launch['pane']}): launched without a registered attempt"
             for launch in launches]
            + [f"Herdr agent {agent.get('name')} (pane {agent['pane_id']}) runs in {agent['cwd']} "
               'without a registered attempt' for agent in live] + failed)


def checked(cwd, session=None):
    """The gaps, or one naming why the check could not run: a broken check never passes silently."""
    try:
        return gaps(cwd, session)
    except Exception as error:
        return [f'could not check workers: {error}']


def reason(missing):
    return ('These workers could finish or run without waking you:\n'
            + ''.join(f'- {gap}\n' for gap in missing)
            + f'Register each launched worker, or dismiss a launch that needs none with `python3 {ROOT}/hooks/'
            + f'herdr_launch.py dismiss --pane <pane> --reason <why>` ({PREPARE}). '
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
        print(json.dumps({'decision': 'block', 'reason': reason(missing)}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
