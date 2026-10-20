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
        env = {key: value for key, value in os.environ.items()
               if not key.startswith('HERDR_') and key != 'AUTOMATTIC_WORKER'}
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

    def gap(self, agent, pane):
        return f"{self.repo / '.scratch/herdr-launches.jsonl'}: {agent} (pane {pane}): launched without a registered attempt"


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

    def test_an_unreadable_launch_log_line_is_named_and_hides_no_other_gap(self):
        # Review 6: a torn or hand-broken line is reported by number and ignored for matching; the lifecycle gaps and
        # the readable launches still show.
        log = self.repo / '.scratch/herdr-launches.jsonl'
        self.launch('herdr agent start builder-1 --kind codex --pane w1:p5')
        with log.open('a') as stream:
            stream.write('{"time": "2026-10-2\n{"agent": "builder-9"}\n')
        self.launch('herdr agent start builder-2 --kind codex --pane w1:p6')
        self.assertEqual(self.check(), [f'{self.state}: ticket-1/1: no armed wait', self.gap('builder-1', 'w1:p5'),
                                        self.gap('builder-2', 'w1:p6'),
                                        f'{log}: launch log line 2 is unreadable; fix or remove it',
                                        f'{log}: launch log line 3 is unreadable; fix or remove it'])

    def test_a_line_with_malformed_fields_is_named_like_an_unreadable_one(self):
        # Re-review 3: valid JSON whose fields have the wrong shape (the probe's empty coordinator, a bad time, a
        # number for a name or cwd, a dismissal without its host session) is named and ignored for matching.
        log = self.repo / '.scratch/herdr-launches.jsonl'
        self.launch('herdr agent start builder-1 --kind codex --pane w1:p5')
        at, coordinator = '2026-10-20T10:00:00Z', {'pane': 'w1:p1', 'session': None}
        bad = [{'time': 'x', 'agent': 'b', 'pane': 'w1:p9', 'coordinator': {}},
               {'time': 'yesterday', 'agent': 'b', 'pane': 'w1:p9', 'coordinator': coordinator},
               {'time': at, 'agent': 7, 'pane': 'w1:p9', 'coordinator': coordinator},
               {'time': at, 'agent': 'b', 'pane': 'w1:p9', 'coordinator': coordinator, 'cwd': 5},
               {'time': at, 'dismissed': {'pane': 'w1:p5'}, 'by': {'pane': 'w1:p1'}, 'reason': 'probe'}]
        with log.open('a') as stream:
            stream.writelines(json.dumps(record) + '\n' for record in bad)
        self.assertEqual(self.check(session='host-1'), [
            f'{self.state}: ticket-1/1: no armed wait', self.gap('builder-1', 'w1:p5'),
            *(f'{log}: launch log line {number} is unreadable; fix or remove it' for number in range(2, 7))])

    def test_a_checkout_without_worktrees_never_asks_herdr(self):
        # Review 4: a Herdr session in a repository with no .worktrees/ has no ticket worker to look for, so a broken
        # Herdr neither slows nor holds it; its lifecycle gaps still show.
        self.serve(fail='connection refused')
        self.assertEqual(self.check(), [f'{self.state}: ticket-1/1: no armed wait'])

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
        # A session is a worker exactly when its launch marked it, not because of its cwd.
        self.assertIsNone(self.stop(cwd=worktree, pane=None, env={'AUTOMATTIC_WORKER': 'effort/ticket-2'}))
        self.assertEqual(self.stop(cwd=worktree, pane=None)['decision'], 'block')
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

    def register(self, worker, attempt, native_session=None, pane='w1:p1'):
        """Register `worker` for an attempt in the run's workers.sqlite, as prepare.md has the coordinator in
        Herdr pane `pane` (None: outside Herdr) do."""
        self.lifecycle('register', attempt, pane, assignment=attempt.split('/')[0], repo=str(self.repo),
                       worktree=str(self.worktree), head='head-1', execution=str(self.execution), runtime='claude',
                       worker=worker, native_session=native_session or f'native-{attempt}', owned=True,
                       packet=str(support.assignment_file(self.execution.parent, 'ticket')))

    @staticmethod
    def agent(name, pane, cwd, workspace='w1'):
        """A live agent as `herdr agent list` reports it."""
        return {'agent': 'codex', 'agent_status': 'idle', 'name': name, 'pane_id': pane, 'tab_id': f'{workspace}:t9',
                'workspace_id': workspace, 'cwd': str(cwd)}

    @staticmethod
    def live(name, pane, cwd):
        return f'Herdr agent {name} (pane {pane}) runs in {cwd} without a registered attempt'

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
        # Rule 1: time, agent name, pane, coordinator (its Herdr pane and host session, each when known) and the
        # pane's cwd as the named Herdr server reports it; a command that only mentions a launch records nothing.
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
            {'agent': 'builder-1', 'pane': 'w1:p5', 'coordinator': {'pane': 'w1:p1', 'session': 'host-1'},
             'cwd': str(self.worktree)},
            {'agent': 'reviewer-2', 'pane': 'w1:p6', 'coordinator': {'pane': None, 'session': 'host-1'}}])

    def test_one_command_with_many_launches_stays_inside_the_hook_timeout(self):
        # Review 7: the Herdr lookups of one hook run share a budget inside the hosts' hook timeout, so a hung
        # Herdr still leaves every launch logged (cwd unknown) before the host kills the hook.
        limit = min(hook['timeout'] for path in ('hooks/hooks.json', 'hosts/codex/hooks.json')
                    for entry in json.loads((ROOT / path).read_text())['hooks']['PreToolUse']
                    for hook in entry['hooks'] if hook['command'].endswith('hooks/herdr_launch.py"'))
        self.serve(hang=True)
        started = time.monotonic()
        self.launch(' && '.join(f'herdr agent start b-{index} --kind codex --pane w1:p{index}' for index in range(1, 6)))
        self.assertLess(time.monotonic() - started, limit - 2)
        self.assertEqual([{key: value for key, value in record.items() if key not in ('time', 'coordinator')}
                          for record in self.logged()],
                         [{'agent': f'b-{index}', 'pane': f'w1:p{index}'} for index in range(1, 6)])

    def test_launches_behind_wrappers_and_shell_strings_are_logged(self):
        # Review 5: `timeout`, `env` with its options, `--session=S` and a shell's `-c` string still run a launch.
        self.serve(panes={'s1': {pane: {'pane_id': pane, 'cwd': str(self.worktree)} for pane in ('w1:p14', 'w1:p16')}})
        for command in ('timeout 60 herdr agent start a-1 --kind codex --pane w1:p11',
                        'timeout -s KILL -k 5 60 herdr agent start a-2 --kind codex --pane w1:p12',
                        'env -u HERDR_PANE_ID -i FOO=1 herdr agent start a-3 --kind codex --pane w1:p13',
                        'herdr --session=s1 agent start a-4 --kind codex --pane w1:p14',
                        'sh -c "herdr agent start a-5 --kind codex --pane w1:p15"',
                        "bash -lc 'cd /tmp && herdr --session s1 agent start a-6 --kind codex --pane w1:p16'",
                        'bash -c "timeout 30 herdr agent start a-7 --kind codex --pane w1:p17" && echo done'):
            self.launch(command, pane=None)
        self.assertEqual([(record['agent'], record['pane'], record.get('cwd')) for record in self.logged()], [
            ('a-1', 'w1:p11', None), ('a-2', 'w1:p12', None), ('a-3', 'w1:p13', None),
            ('a-4', 'w1:p14', str(self.worktree)), ('a-5', 'w1:p15', None), ('a-6', 'w1:p16', str(self.worktree)),
            ('a-7', 'w1:p17', None)])

    def test_logging_never_blocks_the_command_even_when_herdr_or_the_log_fails(self):
        # Rule 1: a hung Herdr still leaves a record with the cwd unknown; an unwritable log only loses the record.
        self.serve(hang=True)
        started = time.monotonic()
        self.launch('herdr agent start builder-1 --kind codex --pane w1:p5')
        self.assertLess(time.monotonic() - started, 10)
        self.assertEqual([{key: value for key, value in record.items() if key != 'time'} for record in self.logged()],
                         [{'agent': 'builder-1', 'pane': 'w1:p5', 'coordinator': {'pane': 'w1:p1', 'session': 'host-1'}}])
        (self.repo / '.scratch/herdr-launches.jsonl').unlink()
        (self.repo / '.scratch/herdr-launches.jsonl').mkdir()
        self.serve()
        self.launch('herdr agent start builder-2 --kind codex --pane w1:p5')

    @unittest.skipUnless(shutil.which('node'), 'Node.js runs the Pi extension')
    def test_pi_logs_launches_from_bash_and_bg_run_without_blocking_them(self):
        # Rule 1 on Pi: its tool_call covers bash and bg_run; the coordinator's session is Pi's session ID.
        verdicts = self.pi("""
const call = (toolName, command) => handlers.tool_call({ type: 'tool_call', toolCallId: toolName, toolName,
  input: { command, name: 'launch' } }, ctx);
console.log(JSON.stringify([await call('bash', 'herdr agent start builder-1 --kind codex --pane w1:p5'),
  await call('bg_run', 'herdr agent start builder-2 --kind pi --pane w1:p6')]));
""")
        self.assertEqual(verdicts, [None, None])
        self.assertEqual([{key: value for key, value in record.items() if key != 'time'} for record in self.logged()], [
            {'agent': 'builder-1', 'pane': 'w1:p5', 'coordinator': {'pane': None, 'session': 'pi-1'},
             'cwd': str(self.worktree)},
            {'agent': 'builder-2', 'pane': 'w1:p6', 'coordinator': {'pane': None, 'session': 'pi-1'}}])

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
        self.register('w1:p5', 'ticket-1/1', pane=None)
        self.assertEqual(self.check(pane=None, session='host-1'), [self.gap('builder-2', 'w1:p6')])
        self.register('builder-2', 'ticket-2/1', pane=None)
        self.assertEqual(self.check(pane=None, session='host-1'), [])
        self.assertIsNone(self.stop(pane=None, session='host-1'))

    def dismiss(self, *args, pane=None):
        """Run the launch hook's `dismiss` command from the ticket worktree, in Herdr pane `pane` or outside Herdr."""
        return subprocess.run([sys.executable, str(LAUNCH), 'dismiss', *args], cwd=self.worktree, capture_output=True,
                              text=True, env=self.env(pane), timeout=20)

    def test_a_dismissal_clears_only_the_launches_of_the_coordinator_that_dismissed(self):
        # Review 2: a dismissal records who dismissed (pane and host session) and accounts only for that
        # coordinator's launches; with no identity it could account for nothing, so it is refused.
        self.launch('herdr agent start builder-1 --kind codex --pane w1:p5', pane=None, session='host-1')
        self.launch('herdr agent start builder-1 --kind codex --pane w1:p6', pane=None, session='host-2')
        self.launch('herdr agent start builder-1 --kind codex --pane w1:p7', pane='w1:p1', session='host-3')
        self.serve()
        self.assertIn(f'herdr_launch.py dismiss --pane <pane> --session host-1 --reason <why>',
                      self.stop(pane=None, session='host-1')['reason'])
        self.assertEqual(self.dismiss('--name', 'builder-1', '--session', 'host-2', '--reason', 'probe').returncode, 0)
        self.assertEqual(self.logged()[-1]['by'], {'pane': None, 'session': 'host-2'})
        self.assertEqual(self.dismiss('--pane', 'w1:p7', '--reason', 'probe', pane='w1:p1').returncode, 0)
        self.assertEqual(self.check(pane=None, session='host-1'), [self.gap('builder-1', 'w1:p5')])
        self.assertEqual(self.check(pane=None, session='host-2'), [])
        self.assertEqual(self.check(session='host-3'), [])
        refused = self.dismiss('--name', 'builder-1', '--reason', 'probe')
        self.assertEqual(refused.returncode, 2)
        self.assertIn('--session', refused.stderr)

    def test_a_dismissal_also_accounts_for_a_live_agent_of_the_coordinator_that_dismissed(self):
        # Review 3: a live agent that needs no attempt (a probe left running) is dismissed the same way.
        self.serve(agents=[self.agent('probe-1', 'w1:p5', self.worktree), self.agent('probe-2', 'w1:p6', self.worktree)])
        self.assertEqual(self.dismiss('--name', 'probe-1', '--reason', 'probe', pane='w1:p1').returncode, 0)
        self.assertEqual(self.dismiss('--pane', 'w1:p6', '--reason', 'probe', pane='w1:p9').returncode, 0)
        self.assertEqual(self.check(session='host-1'), [self.live('probe-2', 'w1:p6', self.worktree)])

    def test_a_dismissal_with_a_reason_accounts_for_a_launch_logged_before_it(self):
        # Decision 1: a failed, denied or probe launch stays a gap until a dismissal with a reason accounts for it;
        # a later launch of the same pane or name is a new launch.
        self.launch('herdr agent start builder-1 --kind codex --pane w1:p5', pane=None)
        self.launch('herdr agent start builder-2 --kind codex --pane w1:p6', pane=None)
        self.serve()
        self.assertIn('herdr_launch.py dismiss', self.stop(pane=None, session='host-1')['reason'])
        result = self.dismiss('--pane', 'w1:p5', '--session', 'host-1', '--reason',
                              'agent_not_ready; the user closed the pane')
        self.assertEqual((result.returncode, result.stderr), (0, ''))
        self.assertEqual(self.check(pane=None, session='host-1'), [self.gap('builder-2', 'w1:p6')])
        self.assertEqual(self.dismiss('--name', 'builder-2', '--session', 'host-1', '--reason', 'probe').returncode, 0)
        self.assertEqual(self.check(pane=None, session='host-1'), [])
        self.launch('herdr agent start builder-1 --kind codex --pane w1:p5', pane=None)
        self.assertEqual(self.check(pane=None, session='host-1'), [self.gap('builder-1', 'w1:p5')])

    def test_a_dismissal_without_a_reason_is_refused_and_changes_nothing(self):
        # Decision 1: accounting for a launch needs a stated reason.
        self.launch('herdr agent start builder-1 --kind codex --pane w1:p5', pane=None)
        logged = self.logged()
        for reason in ([], ['--reason', ''], ['--reason', '  ']):
            result = self.dismiss('--pane', 'w1:p5', '--session', 'host-1', *reason)
            self.assertEqual(result.returncode, 2, reason)
            self.assertIn('--reason', result.stderr)
        self.assertEqual(self.logged(), logged)
        self.assertEqual(self.check(pane=None, session='host-1'), [self.gap('builder-1', 'w1:p5')])

    def test_only_the_launching_pane_clears_a_herdr_launch_and_a_later_registration_only_one_outside_herdr(self):
        # Re-review 2: a launch made inside Herdr is cleared only by an attempt whose recorded coordinator is that
        # pane; an attempt with no recorded coordinator, registered at or after it, clears only a launch made outside
        # Herdr. Review probes: another run's old registration, and an unrelated later one outside Herdr.
        def run(slug):
            (self.repo / f'.scratch/{slug}/reports').mkdir(parents=True, exist_ok=True)
            return self.repo / f'.scratch/{slug}/reports/workers.sqlite'
        self.state = run('old-run')
        self.register('builder-1', 'old-1/1', pane='w1:p9')
        self.register('builder-6', 'old-6/1', pane=None)
        time.sleep(1.1)  # The log keeps whole seconds: the next launches come strictly later.
        for index in range(1, 5):
            self.launch(f'herdr agent start builder-{index} --kind codex --pane w1:p{index + 4}')
        for index in (5, 6):
            self.launch(f'herdr agent start builder-{index} --kind codex --pane w1:p{index + 4}', pane=None)
        self.state = run('effort')
        self.register('builder-2', 'ticket-2/1', pane='w1:p9')
        self.register('builder-3', 'ticket-3/1', pane='w1:p1')
        self.register('builder-5', 'ticket-5/1', pane=None)
        self.state = run('other-run')
        self.register('builder-4', 'other-4/1', native_session='other-native', pane=None)
        self.serve()
        self.assertEqual(self.check(session='host-1'), [self.gap(f'builder-{index}', f'w1:p{index + 4}')
                                                        for index in (1, 2, 4)])
        self.assertEqual(self.check(pane=None, session='host-1'), [self.gap('builder-6', 'w1:p10')])

    def test_a_session_pane_name_handle_clears_a_launch_matching_its_pane_or_its_name(self):
        # Decision 2: the lifecycle also accepts `<session>/<pane>/<name>` as a worker handle.
        self.serve(panes={'default': {pane: {'pane_id': pane, 'cwd': str(self.worktree)}
                                      for pane in ('w1:p5', 'w1:p6', 'w1:p7')}})
        for agent, pane in (('builder-1', 'w1:p5'), ('builder-2', 'w1:p6'), ('builder-3', 'w1:p7')):
            self.launch(f'herdr agent start {agent} --kind codex --pane {pane}', pane=None)
        self.serve()
        self.register('default/w1:p5/renamed-1', 'ticket-1/1', pane=None)
        self.register('s2/w1:p9/builder-2', 'ticket-2/1', pane=None)
        self.register('default/w1:p8/builder-9', 'ticket-3/1', pane=None)
        self.assertEqual(self.check(pane=None, session='host-1'), [self.gap('builder-3', 'w1:p7')])

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

    def test_a_reused_pane_with_another_host_session_inherits_no_launches(self):
        # Decision 4: when the launch and the stopping session both carry a host session, pane and session must both
        # match; the pane alone decides only when one side has no session (a restarted Herdr may reuse pane ids).
        self.launch('herdr agent start builder-1 --kind codex --pane w1:p5', pane='w1:p1', session='old-1')
        self.launch('herdr agent start builder-2 --kind codex --pane w1:p5', pane='w1:p1', session=None)
        self.serve()
        both = [self.gap('builder-1', 'w1:p5'), self.gap('builder-2', 'w1:p5')]
        self.assertEqual(self.check(pane='w1:p1', session='new-1'), [self.gap('builder-2', 'w1:p5')])
        self.assertEqual(self.check(pane='w1:p1', session='old-1'), both)
        self.assertEqual(self.check(pane='w1:p1'), both)
        self.assertEqual(self.check(pane='w1:p2', session='old-1'), [])

    def test_launches_and_registrations_count_however_long_ago_their_run_was_active(self):
        # Rule 2: neither the launch log nor a run's registrations age out with the gate's one-day filter.
        log, stale = self.repo / '.scratch/herdr-launches.jsonl', time.time() - 2 * 24 * 3600
        self.launch('herdr agent start builder-1 --kind codex --pane w1:p5', pane=None)
        self.register('builder-1', 'ticket-1/1', pane=None)
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
        self.assertIn('herdr_launch.py dismiss --pane <pane> --session pi-1 --reason <why>',
                      settled['entries'][0]['content'])

    def test_a_live_agent_in_a_worktree_is_a_gap_until_an_attempt_registers_it(self):
        # Rule 3: an agent nobody logged (started by hand, or before the hook) still holds its workspace's coordinator.
        other = self.repo / '.worktrees/ticket-2'
        self.serve(agents=[self.agent('builder-1', 'w1:p5', self.worktree), self.agent('builder-2', 'w1:p6', other)])
        self.assertEqual(self.check(), [self.live('builder-1', 'w1:p5', self.worktree),
                                        self.live('builder-2', 'w1:p6', other)])
        decision = self.stop()
        self.assertEqual(decision['decision'], 'block')
        self.assertIn(f"- {self.live('builder-1', 'w1:p5', self.worktree)}\n", decision['reason'])
        self.register('w1:p5', 'ticket-1/1')
        self.register('builder-2', 'ticket-2/1')
        self.assertEqual(self.check(), [])

    def test_only_other_live_agents_in_the_coordinators_workspace_and_worktrees_count(self):
        # Rule 3: other workspaces, the coordinator's own pane and agents outside .worktrees/ are not its workers; a
        # session outside Herdr has no workspace to check; a logged launch that is still live is named once.
        self.launch('herdr agent start builder-1 --kind codex --pane w1:p5')
        self.serve(agents=[self.agent('elsewhere-1', 'w2:p5', self.worktree, workspace='w2'),
                           self.agent('coordinator', 'w1:p1', self.worktree),
                           self.agent('e2e-1', 'w1:p7', self.repo),
                           self.agent('builder-1', 'w1:p5', self.worktree)])
        self.assertEqual(self.check(), [self.gap('builder-1', 'w1:p5')])
        self.assertEqual(self.check(pane=None, session='host-1'), [])

    def test_a_marked_worker_is_held_neither_for_itself_nor_its_siblings_wherever_it_runs(self):
        # Rule 4: a session is a worker exactly when AUTOMATTIC_WORKER is set; its launches and siblings hold only
        # its coordinator. Includes a native worker that inherited its coordinator's HERDR_PANE_ID (review probe).
        sibling, marked = self.repo / '.worktrees/ticket-2', {'AUTOMATTIC_WORKER': 'effort/ticket-1'}
        self.launch('herdr agent start builder-1 --kind codex --pane w1:p5', session='coord-1')
        workers = (('w1:p5', 'builder-session', self.worktree), ('w1:p7', 'other-session', self.repo),
                   ('w1:p1', 'worker-1', self.worktree), (None, 'worker-2', self.repo))
        for pane, session, cwd in workers:
            self.launch('herdr agent start helper-1 --kind codex --pane w1:p8', cwd=cwd, pane=pane, session=session,
                        env=marked)
        self.serve(agents=[self.agent('builder-1', 'w1:p5', self.worktree), self.agent('builder-2', 'w1:p6', sibling)])
        for pane, session, cwd in workers:
            self.assertEqual(self.check(cwd=cwd, pane=pane, session=session, env=marked), [], (pane, session))
            self.assertIsNone(self.stop(cwd=cwd, pane=pane, session=session, env=marked))
        self.assertEqual(self.check(session='coord-1'), [self.gap('builder-1', 'w1:p5'),
                                                         self.live('builder-2', 'w1:p6', sibling)])
        if shutil.which('node'):  # Pi's settle check inherits the marker from its process environment.
            self.assertIsNone(self.pi("""
console.log(JSON.stringify((await handlers.agent_before_settle(
  { type: 'agent_before_settle', outcome: 'completed', entries: [], continue: false }, ctx)) ?? null));
""", pane='w1:p5', env=marked))

    def test_an_unmarked_session_in_a_reused_or_once_registered_pane_is_still_held(self):
        # Rule 4 (review probes): pane history says nothing about who runs there now. A launch into another Herdr
        # server's w1:p1, an old run's attempt for w1:p1 and a dismissed failed launch into w1:p7 leave the
        # coordinators now in those panes held for their own unregistered launches and live agents.
        self.launch('herdr --session s2 agent start remote-1 --kind codex --pane w1:p1', pane=None, session='host-9')
        self.state = self.repo / '.scratch/old-run/reports/workers.sqlite'
        self.state.parent.mkdir(parents=True)
        self.register('w1:p1', 'old-1/1', pane='w1:p0')
        self.launch('herdr agent start builder-0 --kind codex --pane w1:p7', session='coord-1')
        self.assertEqual(self.dismiss('--pane', 'w1:p7', '--session', 'coord-1', '--reason', 'failed at trust dialog',
                                      pane='w1:p1').returncode, 0)
        self.launch('herdr agent start builder-1 --kind codex --pane w1:p5', session='host-1')
        self.launch('herdr agent start builder-3 --kind codex --pane w1:p9', pane='w1:p7', session='coord-7')
        self.serve(agents=[self.agent('builder-2', 'w1:p6', self.worktree)])
        live = self.live('builder-2', 'w1:p6', self.worktree)
        self.assertEqual(self.check(session='host-1'), [self.gap('builder-1', 'w1:p5'), live])
        self.assertEqual(self.check(pane='w1:p7', session='coord-7'), [self.gap('builder-3', 'w1:p9'), live])

    def test_a_marked_worker_of_a_coordinator_in_another_checkout_is_not_held(self):
        # Rule 4 (review probe): the coordinator in this checkout launched and registered both workers in another
        # checkout's worktrees; neither worker has a launch or attempt there, but the marker exempts them.
        other = Path(self.tmp.name).resolve() / 'other'
        subprocess.run(['git', 'init', '-q', str(other)], check=True)
        first, second = other / '.worktrees/t1', other / '.worktrees/t2'
        first.mkdir(parents=True)
        second.mkdir(parents=True)
        self.serve(panes={'default': {'w1:p5': {'pane_id': 'w1:p5', 'cwd': str(first)},
                                      'w1:p6': {'pane_id': 'w1:p6', 'cwd': str(second)}}})
        self.launch('herdr agent start builder-1 --kind codex --pane w1:p5; '
                    'herdr agent start builder-2 --kind codex --pane w1:p6')
        self.register('w1:p5', 'ticket-1/1')
        self.register('w1:p6', 'ticket-2/1')
        self.serve(agents=[self.agent('builder-1', 'w1:p5', first), self.agent('builder-2', 'w1:p6', second)])
        self.assertEqual(self.check(cwd=first, pane='w1:p5', session='worker-session',
                                    env={'AUTOMATTIC_WORKER': 'effort/ticket-1'}), [])
        self.assertEqual(self.check(session='host-1'), [])

    def test_a_coordinator_inside_a_worktree_is_still_held(self):
        # Rule 4: an unmarked session is a coordinator wherever it works, so cd'ing into .worktrees/ keeps both checks.
        inside = self.repo / '.worktrees/coord'
        inside.mkdir()
        self.launch('herdr agent start builder-1 --kind codex --pane w1:p5', cwd=inside)
        self.launch('herdr agent start builder-3 --kind codex --pane w1:p9', cwd=inside, pane=None, session='host-2')
        self.serve(agents=[self.agent('builder-2', 'w1:p6', self.worktree)])
        self.assertEqual(self.check(cwd=inside, session='host-1'), [self.gap('builder-1', 'w1:p5'),
                                                                    self.live('builder-2', 'w1:p6', self.worktree)])
        self.assertEqual(self.check(cwd=inside, pane=None, session='host-2'), [self.gap('builder-3', 'w1:p9')])

    def test_a_herdr_failure_or_timeout_is_a_named_gap_that_holds_once(self):
        # Rule 5: a check that cannot run is a named gap, never a pass, and Stop is still held only once.
        self.serve(fail='connection refused')
        gap = ('could not check Herdr workers: herdr agent list exited 1: '
               '{"error": {"code": "server_unavailable", "message": "connection refused"}}')
        self.assertEqual(self.check(), [gap])
        decision = self.stop()
        self.assertEqual(decision['decision'], 'block')
        self.assertIn(f'- {gap}\n', decision['reason'])
        self.assertIsNone(self.stop(active=True))
        self.assertIsNone(self.stop(env={'AUTOMATTIC_YIELD_HOOK': 'off'}))
        # A session outside Herdr has no workspace to check, so a broken Herdr is no gap there.
        self.assertEqual(self.check(pane=None, session='host-1'), [])
        self.serve(hang=True)
        [gap] = self.check()
        self.assertRegex(gap, r"^could not check Herdr workers: .*'herdr', 'agent', 'list'.* timed out after 5 seconds$")

    def test_a_git_failure_is_a_named_gap_not_a_pass(self):
        # Rule 5: when git cannot name the session's checkout the gate says so; outside any repository is no checkout.
        broken = Path(self.tmp.name) / 'broken-git'
        broken.mkdir()
        (broken / 'git').write_text('#!/bin/sh\necho "fatal: unable to read index" >&2\nexit 128\n')
        (broken / 'git').chmod(0o700)
        env = {'PATH': f"{broken}{os.pathsep}{self.env()['PATH']}"}
        gap = 'could not check workers: git rev-parse exited 128: fatal: unable to read index'
        self.assertEqual(self.check(env=env), [gap])
        self.assertIn(f'- {gap}\n', self.stop(env=env)['reason'])
        self.assertIsNone(self.stop(env=env, active=True))
        outside = Path(self.tmp.name) / 'elsewhere'
        outside.mkdir()
        self.assertEqual(self.check(cwd=outside), [])

    @unittest.skipUnless(shutil.which('node'), 'Node.js runs the Pi extension')
    def test_pi_surfaces_a_check_that_could_not_run_and_continues_once(self):
        # Rule 5 on Pi: when the yield gate itself cannot run, the settle hook names the failure, once per run.
        broken = Path(self.tmp.name) / 'broken-python'
        broken.mkdir()
        (broken / 'python3').write_text('#!/bin/sh\necho "python3: simulated crash" >&2\nexit 1\n')
        (broken / 'python3').chmod(0o700)
        first, repeated = self.pi("""
const settle = async () => (await handlers.agent_before_settle(
  { type: 'agent_before_settle', outcome: 'completed', entries: [], continue: false }, ctx)) ?? null;
console.log(JSON.stringify([await settle(), await settle()]));
""", pane='w1:p1', env={'PATH': f"{broken}{os.pathsep}{self.env()['PATH']}"})
        self.assertTrue(first['continue'])
        self.assertRegex(first['entries'][0]['content'],
                         r'\n- could not check workers: Command failed: python3 \S+/hooks/yield_gate\.py check .+ pi-1\n'
                         r'python3: simulated crash\n')
        self.assertIsNone(repeated)


if __name__ == '__main__':
    unittest.main()
