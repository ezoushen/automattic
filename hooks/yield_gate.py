#!/usr/bin/env python3
"""Stop hook: keep the host working while a lifecycle worker could finish without waking it.

Reads every run's workers.sqlite under the main checkout's .scratch/*/reports/ that
changed in the last day, without writing to it, and applies the lifecycle's yield
gate. A coordinator (a session outside .worktrees/) is also held for each Herdr worker
in a ticket worktree that no attempt in any run registers: each launch it logged
(hooks/herdr_launch.py) and each other live agent of its Herdr workspace. A check that
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
    # A session inside a ticket worktree is a worker: only its coordinator answers for unregistered workers.
    if not cwd.is_relative_to((root / '.worktrees').resolve()):
        missing += unregistered(root, pane or session, pane)
    return missing


def herdr_agents():
    """The live agents the session's Herdr server reports."""
    result = subprocess.run(['herdr', 'agent', 'list'], capture_output=True, text=True, timeout=5)
    if result.returncode:
        raise RuntimeError(f'herdr agent list exited {result.returncode}: {(result.stderr or result.stdout).strip()}')
    return json.loads(result.stdout)['result']['agents']


def unregistered(root, coordinator, pane):
    """Name each Herdr worker that no attempt in any run registers: each launch this coordinator logged into a
    ticket worktree or an unknown cwd, and each other live agent in a ticket worktree of its Herdr workspace."""
    module, workers = None, set()
    for state in root.glob('.scratch/*/reports/workers.sqlite'):
        module = module or lifecycle()
        db = sqlite3.connect(f'{state.as_uri()}?mode=ro', uri=True, timeout=5)
        try:
            workers |= {saved['worker'] for saved in module.attempts(db)}
        finally:
            db.close()
    log, worktrees = root / LAUNCHES, (root / '.worktrees').resolve()
    launches = [json.loads(line) for line in log.read_text().splitlines()] if log.is_file() else []
    launches = [launch for launch in launches if coordinator and launch['coordinator'] == coordinator
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
            + f'Register each launched worker ({PREPARE}). Arm a notified wait, recover the receipt or collect the '
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
