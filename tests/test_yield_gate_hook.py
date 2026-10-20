#!/usr/bin/env python3
"""The Stop hook keeps a host working while a lifecycle worker could finish unseen."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

import support

ROOT = support.ROOT
HOOK = ROOT / 'hooks' / 'yield_gate.py'
LAUNCH = ROOT / 'hooks' / 'herdr_launch.py'
LIFECYCLE = ROOT / 'scripts' / 'worker_lifecycle.py'


class GateRepo(unittest.TestCase):
    """A repository whose sessions reach a stub `herdr` on PATH, never a live Herdr server."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='automattic yield ')
        self.addCleanup(self.tmp.cleanup)
        # Outcomes go to a ledger under the state home; keep the user's ledger out of tests.
        self.enterContext(patch.dict(os.environ, {'XDG_STATE_HOME': str(Path(self.tmp.name) / 'state')}))
        self.repo = Path(self.tmp.name).resolve() / 'project'
        self.repo.mkdir()
        subprocess.run(['git', 'init', '-q', str(self.repo)], check=True)
        self.state = self.repo / '.scratch/effort/reports/workers.sqlite'
        self.execution = self.repo / '.scratch/effort/reports/execution.json'
        self.execution.parent.mkdir(parents=True)
        self.execution.write_text(json.dumps({'agent': 'builder', 'job': 'ticket', 'settings': {'model': 'sonnet'}}))
        self.bin = Path(self.tmp.name) / 'bin'
        self.bin.mkdir()
        self.served = self.bin / 'herdr.json'
        self.serve()
        # `agent list` answers with the served agents; `pane get` with the served panes of the `--session` server.
        stub = self.bin / 'herdr'
        stub.write_text(f'#!{sys.executable}\n' + f'''
import json, sys, time
served = json.load(open({str(self.served)!r}))
args, session = sys.argv[1:], 'default'
if args[:1] == ['--session']:
    session, args = args[1], args[2:]
if served['hang']:
    time.sleep(30)
if served['fail']:
    print(json.dumps({{'error': {{'code': 'server_unavailable', 'message': served['fail']}}}}), file=sys.stderr)
    sys.exit(1)
if args == ['agent', 'list']:
    print(json.dumps({{'result': {{'agents': served['agents'], 'type': 'agent_list'}}}}))
elif args[:2] == ['pane', 'get'] and args[2] in served['panes'].get(session, {{}}):
    print(json.dumps({{'result': {{'pane': served['panes'][session][args[2]], 'type': 'pane_info'}}}}))
elif args[:2] == ['pane', 'get']:
    print(json.dumps({{'error': {{'code': 'pane_not_found'}}}}), file=sys.stderr)
    sys.exit(1)
else:
    sys.exit(3)
''')
        stub.chmod(0o700)

    def serve(self, agents=(), panes=None, fail=None, hang=False):
        """What the stub Herdr server reports: live agents, panes by server, or a failure."""
        self.served.write_text(json.dumps({'agents': list(agents), 'panes': panes or {}, 'fail': fail, 'hang': hang}))

    def env(self, pane='w1:p1', **values):
        """The environment of a session in Herdr pane `pane` of workspace w1, or outside Herdr when None."""
        env = {key: value for key, value in os.environ.items() if not key.startswith('HERDR_')}
        env['PATH'] = f"{self.bin}{os.pathsep}{env['PATH']}"
        return dict(env, **({'HERDR_PANE_ID': pane, 'HERDR_WORKSPACE_ID': 'w1'} if pane else {}), **values)

    def lifecycle(self, kind, attempt='ticket-1/1', pane='w1:p1', **fields):
        event = self.state.parent / 'event.json'
        event.write_text(json.dumps(dict(kind=kind, attempt=attempt, **fields)))
        subprocess.run([sys.executable, '-B', str(LIFECYCLE), 'record', '--state', str(self.state),
                        '--input', str(event)], check=True, capture_output=True, env=self.env(pane))

    def stop(self, cwd=None, active=False, env=None, pane='w1:p1', host='claude', session=None):
        payload = {'hook_event_name': 'Stop', 'cwd': str(cwd or self.repo), 'stop_hook_active': active,
                   **({'session_id': session} if session else {})}
        result = subprocess.run([sys.executable, str(HOOK), host], input=json.dumps(payload),
                                capture_output=True, text=True, env=self.env(pane, **(env or {})), timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout) if result.stdout.strip() else None

    def check(self, cwd=None, pane='w1:p1', session=None, env=None):
        """The gaps `yield_gate.py check <cwd> [session]` reports, as Pi's extension runs it."""
        result = subprocess.run([sys.executable, str(HOOK), 'check', str(cwd or self.repo), *filter(None, [session])],
                                capture_output=True, text=True, timeout=20, env=self.env(pane, **(env or {})))
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)['missing']


class YieldGateHook(GateRepo):
    def setUp(self):
        super().setUp()
        self.lifecycle('register', assignment='ticket-1', repo=str(self.repo), worktree=str(self.repo),
                       head='head-1', execution=str(self.execution), runtime='claude', worker='pane-1',
                       native_session='native-1', owned=True,
                       packet=str(support.assignment_file(self.execution.parent, 'ticket')))
        self.lifecycle('startup', observed={'runtime': 'claude', 'model': 'sonnet'}, evidence=['native.jsonl:1'])
        self.lifecycle('submitted', evidence=['native.jsonl:2:accepted prompt'])

    def test_a_live_worker_without_a_wake_path_blocks_the_stop_once(self):
        decision = self.stop(cwd=self.repo / '.scratch')
        self.assertEqual(decision['decision'], 'block')
        self.assertIn('ticket-1/1: no armed wait', decision['reason'])
        self.assertIn(str(self.state), decision['reason'])
        self.assertIn('workers/wait.md', decision['reason'])
        # A stop that a stop hook already continued is let through, so a gap the host cannot fix never loops.
        self.assertIsNone(self.stop(active=True))
        self.assertIsNone(self.stop(env={'AUTOMATTIC_YIELD_HOOK': 'off'}))

    def test_codex_uses_the_same_stop_protocol(self):
        self.assertEqual(self.stop(host='codex')['decision'], 'block')
        self.assertIsNone(self.stop(host='codex', active=True))

    def test_only_the_herdr_pane_that_registered_a_worker_is_held(self):
        self.assertIsNone(self.stop(pane='w1:p9'))
        self.assertEqual(self.stop(pane='w1:p1')['decision'], 'block')

    def test_a_worker_session_in_its_own_worktree_is_not_held(self):
        worktree = self.repo / '.worktrees/ticket-2'
        worktree.mkdir(parents=True)
        execution = self.state.parent / 'execution.json'
        self.lifecycle('register', 'ticket-2/1', None, assignment='ticket-2', repo=str(self.repo),
                       worktree=str(worktree), head='head-1', execution=str(execution), runtime='claude',
                       worker='pane-2', native_session='native-2', owned=True,
                       packet=str(support.assignment_file(execution.parent, 'ticket')))
        self.assertIsNone(self.stop(cwd=worktree, pane=None))
        self.assertEqual(self.stop(pane=None)['decision'], 'block')

    def test_runs_idle_for_a_day_and_other_directories_are_not_checked(self):
        before = self.state.stat().st_mtime
        stale = time.time() - 2 * 24 * 3600
        os.utime(self.state, (stale, stale))
        self.assertIsNone(self.stop())
        # Checking reads the state without touching it.
        self.assertEqual(self.state.stat().st_mtime, stale)
        self.assertGreater(before, stale)
        outside = Path(self.tmp.name) / 'elsewhere'
        outside.mkdir()
        self.assertIsNone(self.stop(cwd=outside))

    def test_check_mode_reports_gaps_for_other_hosts(self):
        result = subprocess.run([sys.executable, str(HOOK), 'check', str(self.repo)],
                                capture_output=True, text=True, timeout=20, env=self.env())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['missing'], [f'{self.state}: ticket-1/1: no armed wait'])

    @unittest.skipUnless(shutil.which('node'), 'Node.js runs the Pi extension')
    def test_pi_continues_once_when_a_completed_run_would_settle_with_a_gap(self):
        script = f"""
const bootstrap = await import({json.dumps((ROOT / 'hosts/pi/bootstrap.ts').as_uri())});
const handlers = {{}};
bootstrap.default({{ on: (event, handler) => {{ handlers[event] = handler; }} }});
const settle = (outcome) => handlers.agent_before_settle(
  {{ type: 'agent_before_settle', outcome, entries: [], continue: false }},
  {{ cwd: {json.dumps(str(self.repo))}, sessionManager: {{ getSessionId: () => 'pi-1' }} }});
const first = await settle('completed');
const repeated = await settle('completed');
handlers.agent_settled({{ type: 'agent_settled', aborted: false }});
console.log(JSON.stringify([first, repeated, await settle('aborted'), await settle('completed')]));
"""
        result = subprocess.run(['node', '--input-type=module', '-e', script], capture_output=True, text=True,
                                timeout=30, env=self.env())
        self.assertEqual(result.returncode, 0, result.stderr)
        first, repeated, aborted, next_run = json.loads(result.stdout)
        self.assertTrue(first['continue'])
        self.assertEqual(first['entries'][0]['type'], 'custom_message')
        self.assertIn('ticket-1/1: no armed wait', first['entries'][0]['content'])
        # One continuation per run, so a gap the host cannot fix never loops; an abort is never resumed.
        self.assertIsNone(repeated)
        self.assertIsNone(aborted)
        self.assertTrue(next_run['continue'])


class UnregisteredWorkers(GateRepo):
    """Each `herdr agent start` is logged, so a worker its coordinator never registered is named at stop."""

    def setUp(self):
        super().setUp()
        self.worktree = self.repo / '.worktrees/ticket-1'
        self.worktree.mkdir(parents=True)
        self.serve(panes={'default': {'w1:p5': {'pane_id': 'w1:p5', 'cwd': str(self.worktree)}}})

    def launch(self, command, cwd=None, pane='w1:p1', session='host-1', env=None):
        """Run the Bash PreToolUse hook as Claude or Codex does before `command`."""
        payload = {'hook_event_name': 'PreToolUse', 'tool_name': 'Bash', 'tool_input': {'command': command},
                   'cwd': str(cwd or self.repo), 'session_id': session}
        result = subprocess.run([sys.executable, str(LAUNCH)], input=json.dumps(payload), capture_output=True,
                                text=True, env=self.env(pane, **(env or {})), timeout=20)
        # The hook never blocks the command: no decision and a clean exit, whatever happened.
        self.assertEqual((result.returncode, result.stdout), (0, ''), result.stderr)

    def logged(self):
        log = self.repo / '.scratch/herdr-launches.jsonl'
        return [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []

    def register(self, worker, attempt):
        """Register `worker` for an attempt in the run's workers.sqlite, as prepare.md has the coordinator do."""
        self.lifecycle('register', attempt, assignment=attempt.split('/')[0], repo=str(self.repo),
                       worktree=str(self.worktree), head='head-1', execution=str(self.execution), runtime='claude',
                       worker=worker, native_session=f'native-{attempt}', owned=True,
                       packet=str(support.assignment_file(self.execution.parent, 'ticket')))

    def gap(self, agent, pane):
        return f"{self.repo / '.scratch/herdr-launches.jsonl'}: {agent} (pane {pane}): launched without a registered attempt"

    def pi(self, body, pane=None, env=None):
        """Run `body` with Pi's extension `handlers` (the last of each event) and a `ctx` for session pi-1 here."""
        script = f"""
const bootstrap = await import({json.dumps((ROOT / 'hosts/pi/bootstrap.ts').as_uri())});
const handlers = {{}};
bootstrap.default({{ on: (event, handler) => {{ handlers[event] = handler; }} }});
const ctx = {{ cwd: {json.dumps(str(self.repo))}, sessionManager: {{ getSessionId: () => 'pi-1' }} }};
{body}
"""
        result = subprocess.run(['node', '--input-type=module', '-e', script], capture_output=True, text=True,
                                timeout=60, env=self.env(pane, **(env or {})))
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_each_herdr_agent_start_is_logged_in_the_main_checkout_for_its_coordinator(self):
        # Rule 1: time, agent name, pane, coordinator (HERDR_PANE_ID, else the host session) and the pane's cwd
        # as the named Herdr server reports it; a command that only mentions a launch records nothing.
        self.serve(panes={'s1': {'w1:p5': {'pane_id': 'w1:p5', 'cwd': str(self.worktree)}},
                          'default': {'w1:p5': {'pane_id': 'w1:p5', 'cwd': '/elsewhere'}}})
        before = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        self.launch('herdr --session s1 agent start builder-1 --kind codex --pane w1:p5 -- -m x', cwd=self.worktree)
        self.launch('git commit -qm "herdr agent start x --pane w1:p5" && echo herdr agent start y --pane w1:p5\n'
                    'FOO=1 herdr agent start reviewer-2 --kind claude --pane w1:p6', pane=None)
        after = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        logged = self.logged()
        for record in logged:
            self.assertTrue(before <= record.pop('time') <= after)
        self.assertEqual(logged, [
            {'agent': 'builder-1', 'pane': 'w1:p5', 'coordinator': 'w1:p1', 'cwd': str(self.worktree)},
            {'agent': 'reviewer-2', 'pane': 'w1:p6', 'coordinator': 'host-1'}])

    def test_logging_never_blocks_the_command_even_when_herdr_or_the_log_fails(self):
        # Rule 1: a hung Herdr still leaves a record with the cwd unknown; an unwritable log only loses the record.
        self.serve(hang=True)
        started = time.monotonic()
        self.launch('herdr agent start builder-1 --kind codex --pane w1:p5')
        self.assertLess(time.monotonic() - started, 10)
        self.assertEqual([{key: value for key, value in record.items() if key != 'time'} for record in self.logged()],
                         [{'agent': 'builder-1', 'pane': 'w1:p5', 'coordinator': 'w1:p1'}])
        (self.repo / '.scratch/herdr-launches.jsonl').unlink()
        (self.repo / '.scratch/herdr-launches.jsonl').mkdir()
        self.serve()
        self.launch('herdr agent start builder-2 --kind codex --pane w1:p5')

    @unittest.skipUnless(shutil.which('node'), 'Node.js runs the Pi extension')
    def test_pi_logs_launches_from_bash_and_bg_run_without_blocking_them(self):
        # Rule 1 on Pi: its tool_call covers bash and bg_run; the coordinator outside Herdr is Pi's session ID.
        verdicts = self.pi("""
const call = (toolName, command) => handlers.tool_call({ type: 'tool_call', toolCallId: toolName, toolName,
  input: { command, name: 'launch' } }, ctx);
console.log(JSON.stringify([await call('bash', 'herdr agent start builder-1 --kind codex --pane w1:p5'),
  await call('bg_run', 'herdr agent start builder-2 --kind pi --pane w1:p6')]));
""")
        self.assertEqual(verdicts, [None, None])
        self.assertEqual([{key: value for key, value in record.items() if key != 'time'} for record in self.logged()], [
            {'agent': 'builder-1', 'pane': 'w1:p5', 'coordinator': 'pi-1', 'cwd': str(self.worktree)},
            {'agent': 'builder-2', 'pane': 'w1:p6', 'coordinator': 'pi-1'}])

    def test_an_unregistered_launch_into_a_worktree_holds_its_coordinator_after_the_pane_closed(self):
        # Rule 2: the log outlives the panes; an attempt whose worker is the pane or the agent name clears the gap.
        self.serve(panes={'default': {pane: {'pane_id': pane, 'cwd': str(self.worktree)} for pane in ('w1:p5', 'w1:p6')}})
        self.launch('herdr agent start builder-1 --kind codex --pane w1:p5', pane=None)
        self.launch('herdr agent start builder-2 --kind codex --pane w1:p6', pane=None)
        self.serve()  # Both panes closed: Herdr no longer reports them.
        missing = [self.gap('builder-1', 'w1:p5'), self.gap('builder-2', 'w1:p6')]
        self.assertEqual(self.check(pane=None, session='host-1'), missing)
        for host in ('claude', 'codex'):
            decision = self.stop(pane=None, session='host-1', host=host)
            self.assertEqual(decision['decision'], 'block')
            self.assertIn(''.join(f'- {gap}\n' for gap in missing), decision['reason'])
            self.assertIn('workers/prepare.md', decision['reason'])
        self.register('w1:p5', 'ticket-1/1')
        self.assertEqual(self.check(pane=None, session='host-1'), [self.gap('builder-2', 'w1:p6')])
        self.register('builder-2', 'ticket-2/1')
        self.assertEqual(self.check(pane=None, session='host-1'), [])
        self.assertIsNone(self.stop(pane=None, session='host-1'))

    def test_launches_outside_worktrees_are_not_gaps_but_an_unknown_cwd_is(self):
        # Rule 2: E2E subjects and demos run in panes outside .worktrees/; a cwd Herdr did not report still counts.
        demo = Path(self.tmp.name) / 'demo'
        demo.mkdir()
        cwds = {'w1:p5': demo, 'w1:p6': self.repo, 'w1:p8': self.repo / '.worktrees-archive/ticket-1'}
        self.serve(panes={'default': {pane: {'pane_id': pane, 'cwd': str(cwd)} for pane, cwd in cwds.items()}})
        for agent, pane in (('demo-1', 'w1:p5'), ('e2e-1', 'w1:p6'), ('helper-1', 'w1:p7'), ('old-1', 'w1:p8')):
            self.launch(f'herdr agent start {agent} --kind codex --pane {pane}', pane=None)
        self.serve()
        self.assertEqual(self.check(pane=None, session='host-1'), [self.gap('helper-1', 'w1:p7')])

    def test_only_the_coordinator_that_launched_a_worker_is_held_for_it(self):
        # Rule 2: a launch belongs to the Herdr pane that ran it, else to the host session; no identity, no owner.
        self.launch('herdr agent start builder-1 --kind codex --pane w1:p5', pane='w1:p1', session='host-1')
        self.launch('herdr agent start builder-2 --kind codex --pane w1:p5', pane=None, session='host-1')
        self.launch('herdr agent start builder-3 --kind codex --pane w1:p5', pane=None, session=None)
        self.serve()
        self.assertEqual(self.check(pane='w1:p1'), [self.gap('builder-1', 'w1:p5')])
        self.assertEqual(self.check(pane='w1:p9', session='host-1'), [])
        self.assertEqual(self.check(pane=None, session='host-1'), [self.gap('builder-2', 'w1:p5')])
        self.assertEqual(self.check(pane=None, session='host-2'), [])
        self.assertEqual(self.check(pane=None), [])

    def test_launches_and_registrations_count_however_long_ago_their_run_was_active(self):
        # Rule 2: neither the launch log nor a run's registrations age out with the gate's one-day filter.
        log, stale = self.repo / '.scratch/herdr-launches.jsonl', time.time() - 2 * 24 * 3600
        self.launch('herdr agent start builder-1 --kind codex --pane w1:p5', pane=None)
        self.register('builder-1', 'ticket-1/1')
        self.launch('herdr agent start builder-2 --kind codex --pane w1:p6', pane=None)
        self.serve()
        for path in (self.state, log):
            os.utime(path, (stale, stale))
        self.assertEqual(self.check(pane=None, session='host-1'), [self.gap('builder-2', 'w1:p6')])

    @unittest.skipUnless(shutil.which('node'), 'Node.js runs the Pi extension')
    def test_pi_holds_the_run_that_launched_an_unregistered_worker(self):
        # Rule 2 on Pi: the settle check runs as this Pi session, so the launch its tool_call logged is named.
        settled = self.pi("""
await handlers.tool_call({ type: 'tool_call', toolCallId: '1', toolName: 'bash',
  input: { command: 'herdr agent start builder-1 --kind codex --pane w1:p5' } }, ctx);
console.log(JSON.stringify(await handlers.agent_before_settle(
  { type: 'agent_before_settle', outcome: 'completed', entries: [], continue: false }, ctx) ?? null));
""")
        self.assertTrue(settled['continue'])
        self.assertIn(f"- {self.gap('builder-1', 'w1:p5')}\n", settled['entries'][0]['content'])
        self.assertIn('workers/prepare.md', settled['entries'][0]['content'])


if __name__ == '__main__':
    unittest.main()
