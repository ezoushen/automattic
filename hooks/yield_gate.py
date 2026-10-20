#!/usr/bin/env python3
"""Stop hook: keep the host working while a lifecycle worker could finish without waking it.

Reads every run's workers.sqlite under the main checkout's .scratch/*/reports/ that
changed in the last day, without writing to it, and applies the lifecycle's yield
gate. Every session is also held for each Herdr launch it logged (hooks/herdr_launch.py)
into a ticket worktree that no attempt accounts for and it did not dismiss; one without
AUTOMATTIC_WORKER, the marker every worker is launched with, also for each other such live
agent of its Herdr workspace. The session bound to coordinate an effort (next_tickets.py
--coordinate; without one, the pane that registered the attempt) is held for each collected
attempt that is not retained whose Herdr tab is still open, and for an effort whose review
report records autofix: true and no blocker, with every ticket done and delivery failing. A
check that cannot run, and a launch log line that is unreadable or malformed, are named gaps,
never a pass. `claude` and `codex` speak their shared Stop
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
COLLECT = ROOT / 'runtime/workers/collect.md'
HANDOFF = ROOT / 'skills/dispatch/handoff.md'
# hooks/herdr_launch.py appends each `herdr agent start` here, one JSON object per line.
LAUNCHES = '.scratch/herdr-launches.jsonl'
# scripts/next_tickets.py --coordinate records here, in an effort's reports/, the session that coordinates it.
BINDING = 'coordinator.json'


def lifecycle():
    return script('worker_lifecycle')


def script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f'scripts/{name}.py')
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
    # Every session answers for its own launches; a worker (its launch set AUTOMATTIC_WORKER) not for its siblings.
    return (missing + unregistered(root, pane, session, siblings=not os.environ.get('AUTOMATTIC_WORKER'))
            + stale_tabs(root, pane, session) + undelivered(root, pane, session))


def stale_tabs(root, pane, session):
    """Name each collected attempt that is not retained whose recorded Herdr tab its session still lists, for the
    session bound to coordinate its effort or, with none bound, the pane that registered it, however old the run."""
    module, listed, missing = None, {}, []
    for state in sorted(root.glob('.scratch/*/reports/workers.sqlite')):
        module = module or lifecycle()
        binding = state.with_name(BINDING)
        bound = coordinates(json.loads(binding.read_text()), pane, session) if binding.is_file() else None
        db = sqlite3.connect(f'{state.as_uri()}?mode=ro', uri=True, timeout=5)
        try:
            saved_attempts = module.attempts(db)
        finally:
            db.close()
        for saved in saved_attempts:
            herdr = saved.get('herdr') or {}
            mine = bound if bound is not None else bool(pane) and saved.get('coordinator') == pane
            if not (herdr.get('tab_id') and saved.get('result') and not saved.get('retained') and mine):
                continue
            where = (herdr['session'], herdr['workspace_id'])
            if where not in listed:
                try:
                    listed[where] = herdr_tabs(*where)
                except Exception as error:  # A check that cannot run is a named gap, never a pass.
                    listed[where] = set()
                    missing.append(f'could not check worker tabs: {error}')
            if herdr['tab_id'] in listed[where]:
                missing.append(f"{state}: {saved['attempt']}: Herdr tab {herdr['tab_id']} is still open after "
                               f'collection; retire the worker or record its retention ({COLLECT})')
    return missing


def herdr_tabs(session, workspace):
    """The IDs of the tabs a Herdr session lists in a workspace."""
    result = subprocess.run(['herdr', '--session', session, 'tab', 'list', '--workspace', workspace],
                            capture_output=True, text=True, timeout=5)
    if result.returncode:
        raise RuntimeError(f'herdr tab list exited {result.returncode}: {(result.stderr or result.stdout).strip()}')
    return {tab['tab_id'] for tab in json.loads(result.stdout)['result']['tabs']}


def undelivered(root, pane, session):
    """Name each effort this session was bound to coordinate (next_tickets.py --coordinate) whose delivery fails."""
    board, tickets, missing = None, None, []
    for path in sorted(root.glob(f'.scratch/*/reports/{BINDING}')):
        slug = path.parent.parent.name
        try:
            if not coordinates(json.loads(path.read_text()), pane, session):
                continue
            if board is None:
                module = script('next_tickets')
                module.ROOT, module.ISSUES = root, root / '.scratch'
                board, tickets = module, module.load()  # load() exits on a board it refuses.
            review = board.review_front_matter(slug) or {}
            # Only authorized repairs owe delivery, once every ticket is done; a recorded blocker is why it stops here.
            if (review.get('autofix') != 'true' or str(review.get('blocker') or 'none') != 'none'
                    or any(fm['status'] != 'done' for name, fm in tickets.items() if board.spec_of(name) == slug)):
                continue
            problems = board.delivery_problems(slug)
        except (Exception, SystemExit) as error:  # A check that cannot run is a named gap, never a pass.
            missing.append(f'could not check delivery of {slug}: {error}')
            continue
        if problems:
            missing.append(f"{slug}: delivery incomplete under autofix: {'; '.join(problems)}. Continue the autofix "
                           f'handoff ({HANDOFF}) until `python3 {ROOT}/scripts/next_tickets.py --repo {root} {slug} '
                           f'--delivery` passes, or record `blocker: <reason>` in {path.with_name("spec-review.md")}')
    return missing


def coordinates(binding, pane, session):
    """Whether a dispatch binding ({pane, sessions}) names this session: as for a launch, pane and host session must
    both match when both sides know a session."""
    return any(same_coordinator({'pane': binding['pane'], 'session': known}, pane, session)
               for known in binding['sessions'] or [None])


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
    """Whether an attempt accounts for a logged launch: it names the launch's pane or agent, and the coordinator
    recorded at registration is the pane that launched it; only a launch made outside Herdr can instead be cleared by
    an attempt with no recorded coordinator, registered no earlier."""
    if not handles(saved['worker']) & {launch['agent'], launch['pane']}:
        return False
    if saved.get('coordinator') or launch['coordinator']['pane']:
        return saved.get('coordinator') == launch['coordinator']['pane']
    return (saved['registered_at'] or 0) >= calendar.timegm(time.strptime(launch['time'], '%Y-%m-%dT%H:%M:%SZ'))


def readable(record):
    """Whether a launch log line is a well-formed launch or dismissal; any other line is named, never matched."""
    def text(value, optional=True):
        return isinstance(value, str) or optional and value is None

    def identity(value):
        return isinstance(value, dict) and set(value) == {'pane', 'session'} and all(map(text, value.values()))
    if not isinstance(record, dict):
        return False
    if 'dismissed' in record:
        target = record['dismissed']
        return (isinstance(target, dict) and len(target) == 1 and set(target) <= {'pane', 'agent'}
                and all(text(value, False) for value in target.values()) and identity(record.get('by')))
    try:
        time.strptime(record.get('time'), '%Y-%m-%dT%H:%M:%SZ')
    except (TypeError, ValueError):
        return False
    return ({'agent', 'pane'} <= set(record) and text(record['agent']) and text(record['pane'])
            and identity(record.get('coordinator')) and text(record.get('cwd')))


def unregistered(root, pane, session, siblings=True):
    """Name each Herdr worker that no attempt in any run and no dismissal of this coordinator accounts for: each
    launch it logged into a ticket worktree or an unknown cwd, with `siblings` each other live agent in a ticket
    worktree of its Herdr workspace; and each unreadable log line."""
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
        agents = herdr_agents() if siblings and workspace and worktrees.is_dir() else []  # No worktrees, no workers.
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
    return ('Stopping now leaves these gaps:\n'
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
