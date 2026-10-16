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
HOOK = ROOT / 'hooks' / 'yield-gate.py'
LIFECYCLE = ROOT / 'scripts' / 'worker-lifecycle.py'


class YieldGateHook(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='automattic yield ')
        self.addCleanup(self.tmp.cleanup)
        # Outcomes go to a ledger under the state home; keep the user's ledger out of tests.
        self.enterContext(patch.dict(os.environ, {'XDG_STATE_HOME': str(Path(self.tmp.name) / 'state')}))
        self.repo = Path(self.tmp.name).resolve() / 'project'
        self.repo.mkdir()
        subprocess.run(['git', 'init', '-q', str(self.repo)], check=True)
        self.state = self.repo / '.scratch/effort/reports/workers.sqlite'
        execution = self.repo / '.scratch/effort/reports/execution.json'
        execution.parent.mkdir(parents=True)
        execution.write_text(json.dumps({'role': 'implementer', 'settings': {'model': 'sonnet'}}))
        self.lifecycle('register', assignment='ticket-1', repo=str(self.repo), worktree=str(self.repo),
                       head='head-1', execution=str(execution), runtime='claude', worker='pane-1',
                       native_session='native-1', owned=True)
        self.lifecycle('startup', observed={'runtime': 'claude', 'model': 'sonnet'}, evidence=['native.jsonl:1'])
        self.lifecycle('submitted', evidence=['native.jsonl:2:accepted prompt'])

    def env(self, pane='w1:p1', **values):
        """The environment of a session in Herdr pane `pane`, or outside Herdr when None."""
        env = {key: value for key, value in os.environ.items() if key != 'HERDR_PANE_ID'}
        return dict(env, **({'HERDR_PANE_ID': pane} if pane else {}), **values)

    def lifecycle(self, kind, attempt='ticket-1/1', pane='w1:p1', **fields):
        event = self.state.parent / 'event.json'
        event.write_text(json.dumps(dict(kind=kind, attempt=attempt, **fields)))
        subprocess.run([sys.executable, '-B', str(LIFECYCLE), 'record', '--state', str(self.state),
                        '--input', str(event)], check=True, capture_output=True, env=self.env(pane))

    def stop(self, cwd=None, active=False, env=None, pane='w1:p1', host='claude'):
        payload = {'hook_event_name': 'Stop', 'cwd': str(cwd or self.repo), 'stop_hook_active': active}
        result = subprocess.run([sys.executable, str(HOOK), host], input=json.dumps(payload),
                                capture_output=True, text=True, env=self.env(pane, **(env or {})), timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout) if result.stdout.strip() else None

    def test_a_live_worker_without_a_wake_path_blocks_the_stop_once(self):
        decision = self.stop(cwd=self.repo / '.scratch')
        self.assertEqual(decision['decision'], 'block')
        self.assertIn('ticket-1/1: no armed wait', decision['reason'])
        self.assertIn(str(self.state), decision['reason'])
        self.assertIn('worker-lifecycle.md', decision['reason'])
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
                       worker='pane-2', native_session='native-2', owned=True)
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
const bootstrap = await import({json.dumps((ROOT / 'harnesses/pi/bootstrap.ts').as_uri())});
const handlers = {{}};
bootstrap.default({{ on: (event, handler) => {{ handlers[event] = handler; }} }});
const settle = (outcome) => handlers.agent_before_settle(
  {{ type: 'agent_before_settle', outcome, entries: [], continue: false }}, {{ cwd: {json.dumps(str(self.repo))} }});
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


if __name__ == '__main__':
    unittest.main()
