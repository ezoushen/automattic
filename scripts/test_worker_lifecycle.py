#!/usr/bin/env python3
"""Exercise worker receipts through the CLI and real local wait processes."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import signal
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

import decision_journal
import decisions


SCRIPT = Path(__file__).with_name('worker-lifecycle.py')


class WorkerLifecycle(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='automattic worker ')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        # Outcomes go to a ledger under the state home; keep the user's ledger out of tests.
        self.enterContext(patch.dict(os.environ, {'XDG_STATE_HOME': str(self.root / 'state')}))
        self.state = self.root / 'workers.sqlite'
        self.execution = self.root / 'execution.json'
        self.execution.write_text(json.dumps({'harness': 'claude', 'role': 'implementer',
                                             'settings': {'model': 'sonnet', 'effort': 'high'}}))

    def cli(self, action, *args, code=0):
        process = subprocess.run([sys.executable, '-B', str(SCRIPT), action,
                                  '--state', str(self.state), *args], capture_output=True, text=True,
                                 env=getattr(self, 'native_env', None))
        self.assertEqual(process.returncode, code, process.stdout + process.stderr)
        return json.loads(process.stdout) if process.stdout else process.stderr

    def record(self, kind, attempt='ticket-1/1', code=0, **fields):
        path = self.root / 'event.json'
        path.write_text(json.dumps(dict(kind=kind, attempt=attempt, **fields)))
        return self.cli('record', '--input', str(path), code=code)

    def register(self, attempt='ticket-1/1', assignment='ticket-1', session='native-1',
                 worker='pane-1', code=0, owned=True, runtime='claude', **fields):
        return self.record('register', attempt, code=code, assignment=assignment,
                           repo=str(self.root), worktree=str(self.root), head='head-1',
                           execution=str(self.execution), runtime=runtime,
                           worker=worker, native_session=session, owned=owned, **fields)

    def ready(self, attempt='ticket-1/1'):
        self.record('startup', attempt, observed={'runtime': 'claude', 'model': 'sonnet',
                                                'effort': 'high'}, evidence=['native.jsonl:1'])
        self.record('submitted', attempt, evidence=['native.jsonl:2:accepted prompt'])

    def watch(self, attempt='ticket-1/1', script='print("idle")', code=0, timeout=2):
        path = self.root / 'wait.json'
        path.write_text(json.dumps({'argv': [sys.executable, '-c', script], 'timeout': timeout}))
        return self.cli('watch', '--attempt', attempt, '--input', str(path), code=code)

    def collect(self, attempt='ticket-1/1', report=None):
        if report is None:
            report = self.root / (attempt.replace('/', '-') + '.md')
            report.write_text('Verified assignment report at head-1\n')
        self.record('result', attempt, status='completed', head='head-1', report=str(report),
                    evidence=['checks.log@head-1'])
        return report

    def acknowledge(self):
        for receipt in self.cli('status')['pending']:
            self.cli('ack', '--event-id', str(receipt['id']))

    def routed(self, assignment='ticket-1/route', runtime='claude'):
        """Journal a recommended worker-selection decision and register its resolved route."""
        self.journal = self.root / 'decisions.jsonl'
        option = json.dumps({'candidate': 'sonnet', 'model': 'sonnet', 'runtime': runtime, 'thinking': 'high'})

        def transport(backend, payload):
            qid, question = next(iter(payload['questions'].items()))
            return {'model': backend['model'], 'answers': {qid: {
                'type': 'choice', 'choice': 'option_0',
                'probabilities': {key: float(key == 'option_0') for key in question['criteria']}}}}
        policy = {'enabled': ['worker-selection'], 'backend': {
            'protocol': 'systemone', 'endpoint': 'http://localhost:1241/v1/systemone', 'model': 'test-model'}}
        trace = decision_journal.trace_config(self.journal, self.root, assignment)
        result = decisions.decide(policy, {'family': 'worker-selection', 'state': 'Role: implementer\n',
                                           'instruction': 'Choose a worker.', 'options': {'option_0': option}},
                                  trace=trace, transport=transport)
        execution = json.loads(self.execution.read_text())
        execution.update(selection_source='decision-model',
                         decision_model=dict(result, journal=str(self.journal)))
        self.execution.write_text(json.dumps(execution))
        return result['decision_id']

    def system_one(self):
        """Serve a local System One endpoint that answers each question's first option."""
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                payload = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                qid, question = next(iter(payload['questions'].items()))
                choice = next(iter(question['criteria']))
                body = json.dumps({'model': payload['model'], 'answers': {qid: {
                    'type': 'choice', 'choice': choice,
                    'probabilities': {key: float(key == choice) for key in question['criteria']}}}}).encode()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        self.native_env = dict(os.environ, XDG_STATE_HOME=str(self.root / 'state'))
        return {'protocol': 'systemone', 'model': 'local/test',
                'endpoint': f'http://127.0.0.1:{server.server_port}/v1/systemone'}

    def annotations(self, decision_id):
        return [row for row in decision_journal.read(self.journal)
                if row['decision_id'] == decision_id and row['event'] != 'decision']

    def escalate(self, risk='possible-breach', attempt='ticket-1/1', **fields):
        criteria = self.root / 'criteria.md'
        if not criteria.exists():
            criteria.write_text('Accepted: preserve public API; compatible engineering is authorized.\n')
        brief = self.root / 'decision.md'
        brief.write_text('Evidence, alternatives and recommendation; dependent work paused.\n')
        request = self.root / 'escalate.json'
        request.write_text(json.dumps(dict(risk=risk, reason='Model uncertain about compatibility',
            brief=str(brief), criteria=str(criteria), evidence=['native blocker report'], **fields)))
        return self.cli('escalate', '--attempt', attempt, '--input', str(request))

    def test_possible_breach_requires_human_source_and_unchanged_ruling_criteria(self):
        self.register()
        self.ready()
        self.escalate()
        source = self.root / 'ruling.md'
        source.write_text('Controlled ruling source fixture, not actual human E2E.\n')
        fields = dict(decision='Preserve API; investigate compatible approach', criteria=str(self.root / 'criteria.md'),
                      ruling_source=str(source), evidence=['ruling and canonical criteria'])
        self.record('ruling', code=2, authority='host', source_kind='host-investigation', **fields)
        self.record('ruling', code=2, authority='human', source_kind='phase-decision', **fields)
        self.cli('gate', '--attempt', 'ticket-1/1', '--stage', 'work', code=1)
        self.record('ruling', authority='human', source_kind='user-message', **fields)
        self.assertTrue(self.cli('gate', '--attempt', 'ticket-1/1', '--stage', 'work')['complete'])
        (self.root / 'criteria.md').write_text('Unauthorized subsequent criterion change\n')
        gate = self.cli('gate', '--attempt', 'ticket-1/1', '--stage', 'work', code=1)
        self.assertIn('approved criteria integrity', gate['missing'])

    def test_within_agreement_uncertainty_preserves_phase_opt_in(self):
        for i, enabled in enumerate(([], ['alignment'])):
            execution = json.loads(self.execution.read_text())
            execution['decision_policy'] = {'enabled': enabled}
            self.execution.write_text(json.dumps(execution))
            attempt = f'ticket-{i}/1'
            self.register(attempt, f'ticket-{i}', f'native-{i}', f'pane-{i}')
            self.ready(attempt)
            result = self.escalate('within-agreement', attempt)
            self.assertEqual(result['consultation_enabled'], bool(enabled))
            self.cli('gate', '--attempt', attempt, '--stage', 'work', code=1)
            source = self.root / 'host-investigation.md'
            source.write_text('Host checked a compatible implementation; decision backend is advisory.\n')
            self.record('ruling', attempt, authority='host', decision='Use compatible implementation',
                criteria=str(self.root / 'criteria.md'), ruling_source=str(source),
                source_kind='host-investigation', evidence=['checked investigation and accepted criteria'])
            self.assertTrue(self.cli('gate', '--attempt', attempt, '--stage', 'work')['complete'])

    def test_possible_breach_upgrades_uncertainty_and_delivers_early(self):
        self.register()
        self.ready()
        self.escalate('within-agreement')
        marker = self.root / 'parent.json'
        notify = {'argv': [sys.executable, '-c',
            f'import sys; open({str(marker)!r}, "w").write(sys.argv[1])', '{receipt}'], 'timeout': 2}
        result = self.escalate('possible-breach', notify=notify)
        message = json.loads(marker.read_text())
        self.assertEqual(message['event_id'], result['event_id'])
        self.assertEqual(message['kind'], 'hold')
        self.assertEqual(message['receipt']['risk'], 'possible-breach')
        self.assertEqual(self.cli('status')['holds'][0]['risk'], 'possible-breach')
        self.cli('gate', '--attempt', 'ticket-1/1', '--stage', 'work', code=1)

    def test_design_hold_blocks_only_dependent_work_and_cannot_be_downgraded(self):
        self.register()
        self.ready()
        self.escalate()
        self.record('hold', code=2, risk='within-agreement', reason='Another model thinks it is safe',
                    brief=str(self.root / 'decision.md'), evidence=['model preference'])
        self.register('ticket-2/1', 'ticket-2', 'native-2', 'pane-2')
        native = self.root / 'independent.jsonl'
        native.write_text(json.dumps({'type': 'assistant', 'sessionId': 'native-2',
            'cwd': str(self.root), 'effort': 'high', 'message': {'model': 'sonnet'}}) + '\n')
        request = self.root / 'independent-submit.json'
        request.write_text(json.dumps({'native': str(native), 'timeout': 2,
            'argv': [sys.executable, '-c', 'from pathlib import Path; Path("independent-work").touch()']}))
        self.cli('submit', '--attempt', 'ticket-2/1', '--input', str(request))
        self.assertTrue((self.root / 'independent-work').exists())
        self.cli('gate', '--attempt', 'ticket-1/1', '--stage', 'work', code=1)

    def test_escalation_can_pause_work_without_creating_a_request_file(self):
        self.register()
        self.ready()
        criteria = self.root / 'criteria.md'
        criteria.write_text('Preserve the public API\n')
        brief = self.root / 'pending brief.md'
        result = self.cli('escalate', '--attempt', 'ticket-1/1', '--risk', 'possible-breach',
            '--criteria', str(criteria), '--brief', str(brief), '--reason', 'API compatibility is uncertain',
            '--evidence', 'native progress')
        self.assertEqual(result['risk'], 'possible-breach')
        self.assertFalse(brief.exists())
        self.assertEqual(self.cli('status')['holds'][0]['canonical_criteria'], str(criteria.resolve()))
        self.cli('gate', '--attempt', 'ticket-1/1', '--stage', 'work', code=1)

    def test_terminal_receipt_delivers_once_and_survives_parent_downtime(self):
        self.register()
        self.ready()
        marker = self.root / 'parent-events.jsonl'
        unavailable = self.root / 'parent-down'
        unavailable.touch()
        # The parent accepts the channel check while arming, then goes down before the receipt.
        notify = {'argv': [sys.executable, '-c',
            'import json,pathlib,sys; '
            'sys.exit(0) if json.loads(sys.argv[1])["kind"] == "channel-check" else None; '
            f'sys.exit(7) if pathlib.Path({str(unavailable)!r}).exists() else None; '
            f'p=pathlib.Path({str(marker)!r}); p.open("a").write(sys.argv[1]+"\\n")',
            '{receipt}'], 'timeout': 2}
        request = self.root / 'wait.json'
        request.write_text(json.dumps({'argv': [sys.executable, '-c', 'print("settled")'],
                                       'timeout': 2, 'notify': notify}))
        receipt = self.cli('watch', '--attempt', 'ticket-1/1', '--input', str(request))
        queued = self.cli('status')['pending'][0]
        self.assertEqual(queued['payload']['delivery']['state'], 'failed')
        self.assertEqual(queued['payload']['delivery']['exit_code'], 7)
        self.assertFalse(marker.exists())
        unavailable.unlink()
        retry = self.root / 'retry.json'
        retry.write_text(json.dumps({'retry': True, 'evidence': ['same parent resumed; failed delivery inspected']}))
        delivered = self.cli('deliver', '--event-id', str(receipt['event_id']), '--input', str(retry))
        self.assertEqual(delivered['state'], 'sent')
        self.cli('deliver', '--event-id', str(receipt['event_id']), '--input', str(retry))
        events = [json.loads(line) for line in marker.read_text().splitlines()]
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]['attempt'], 'ticket-1/1')
        self.assertEqual(events[0]['assignment'], 'ticket-1')
        self.assertEqual(events[0]['event_id'], receipt['event_id'])
        self.assertEqual(events[0]['kind'], 'wait-finished')
        self.assertEqual(len(self.cli('status')['pending']), 1)
        self.cli('ack', '--event-id', str(receipt['event_id']))
        self.assertEqual(self.cli('status')['pending'], [])

    def test_yield_gate_requires_a_wake_path_for_every_live_worker(self):
        self.register()
        self.ready()
        gate = self.cli('gate', '--stage', 'yield', code=1)
        self.assertEqual(gate['missing'], ['ticket-1/1: no armed wait'])
        self.assertEqual(self.cli('status')['yield'], gate)
        receipt = self.watch()
        gate = self.cli('gate', '--stage', 'yield', code=1)
        self.assertEqual(gate['missing'], [f"ticket-1/1: receipt {receipt['event_id']} was not delivered"])
        self.record('reconciled', evidence=['native worker idle with its report'])
        self.collect()
        self.acknowledge()
        self.assertEqual(self.cli('gate', '--stage', 'yield'), {'complete': True, 'missing': []})

    def test_yield_gate_needs_a_rearm_after_a_wake_is_reconciled(self):
        self.register()
        self.ready()
        parent = self.root / 'parent.jsonl'
        request = self.root / 'wait.json'
        request.write_text(json.dumps({'argv': [sys.executable, '-c', 'print("idle")'], 'timeout': 2,
            'notify': {'argv': [sys.executable, '-c',
                                f'import sys; open({str(parent)!r}, "a").write(sys.argv[1] + "\\n")', '{receipt}'],
                       'timeout': 2}}))
        self.cli('watch', '--attempt', 'ticket-1/1', '--input', str(request))
        # A delivered wake will reach the host: no gap yet.
        self.assertEqual(self.cli('gate', '--stage', 'yield'), {'complete': True, 'missing': []})
        self.record('reconciled', evidence=['native worker still running tests'])
        gate = self.cli('gate', '--stage', 'yield', code=1)
        self.assertEqual(gate['missing'], ['ticket-1/1: no armed wait'])

    def test_yield_gate_rejects_waits_that_cannot_wake_the_host(self):
        self.register()
        self.ready()
        pidfile = self.root / 'wait.pid'
        command = self.root / 'wait.json'
        command.write_text(json.dumps({'argv': [sys.executable, '-c',
            f'import os,time; open({str(pidfile)!r}, "w").write(str(os.getpid())); time.sleep(30)'], 'timeout': 40}))
        watcher = subprocess.Popen([sys.executable, '-B', str(SCRIPT), 'watch', '--state', str(self.state),
                                    '--attempt', 'ticket-1/1', '--input', str(command)], stdout=subprocess.PIPE, text=True)
        try:
            deadline = time.monotonic() + 5
            while not pidfile.exists() and time.monotonic() < deadline:
                time.sleep(.02)
            self.assertTrue(pidfile.exists())
            gate = self.cli('gate', '--stage', 'yield', code=1)
            self.assertEqual(gate['missing'], ['ticket-1/1: wait has no wake channel'])
            watcher.kill()
            watcher.communicate(timeout=5)
            gate = self.cli('gate', '--stage', 'yield', code=1)
            self.assertEqual(gate['missing'], ['ticket-1/1: wait process lost'])
        finally:
            if watcher.poll() is None:
                watcher.kill()
                watcher.communicate()
            if pidfile.exists():
                try:
                    os.killpg(int(pidfile.read_text()), signal.SIGKILL)
                except ProcessLookupError:
                    pass

    def test_watch_checks_a_new_wake_channel_before_running_the_wait(self):
        self.register()
        self.ready()
        invoked = self.root / 'invoked'
        request = self.root / 'wait.json'
        request.write_text(json.dumps({'argv': [sys.executable, '-c',
            f'from pathlib import Path; Path({str(invoked)!r}).touch()'], 'timeout': 2,
            'notify': {'argv': [sys.executable, '-c', 'import sys; sys.exit(2)', '{receipt}'], 'timeout': 2}}))
        error = self.cli('watch', '--attempt', 'ticket-1/1', '--input', str(request), code=2)
        self.assertIn('Wake channel failed its check (exit 2', error)
        self.assertFalse(invoked.exists())
        self.assertNotIn('monitor', self.cli('status')['attempts'][0])
        parent = self.root / 'parent.jsonl'
        notify = {'argv': [sys.executable, '-c',
            f'import sys; open({str(parent)!r}, "a").write(sys.argv[1] + "\\n")', '{receipt}'], 'timeout': 2}
        request.write_text(json.dumps({'argv': [sys.executable, '-c', 'print("idle")'], 'timeout': 2,
                                       'notify': notify}))
        first = self.cli('watch', '--attempt', 'ticket-1/1', '--input', str(request))
        self.assertEqual(first['delivery']['state'], 'sent')
        self.record('reconciled', evidence=['native worker still running'])
        self.cli('watch', '--attempt', 'ticket-1/1', '--input', str(request))
        messages = [json.loads(line) for line in parent.read_text().splitlines()]
        self.assertEqual([m['kind'] for m in messages], ['channel-check', 'wait-finished', 'wait-finished'])
        self.assertIn('No action needed', messages[0]['instruction'])
        self.assertEqual({r['kind'] for r in self.cli('status')['pending']}, {'wait-finished'})

    def test_lifecycle_records_the_routed_decision_through_its_outcome(self):
        decision_id = self.routed()
        self.register()
        self.assertEqual([(row['event'], row['disposition'], row['choice']) for row in self.annotations(decision_id)],
                         [('action', 'accepted', 'option_0')])
        self.ready()
        execution = self.annotations(decision_id)[-1]
        self.assertEqual((execution['event'], execution['requested'], execution['observed'], execution['revision']),
                         ('execution', {'model': 'sonnet', 'effort': 'high', 'runtime': 'claude'},
                          {'runtime': 'claude', 'model': 'sonnet', 'effort': 'high'}, 'head-1'))
        self.watch()
        self.record('reconciled', evidence=['native worker idle with its report'])
        report = self.collect()
        outcome = self.annotations(decision_id)[-1]
        self.assertEqual((outcome['event'], outcome['status'], outcome['revision']), ('outcome', 'succeeded', 'head-1'))
        self.assertEqual(outcome['evidence'], [str(report), 'checks.log@head-1'])
        self.assertGreaterEqual(outcome['metrics']['worker_seconds'], 0)
        self.assertTrue(decision_journal.check(self.journal, decision_id, 'completion', 'head-1')['complete'])

    def test_journal_capture_failure_is_reported_without_blocking_the_worker(self):
        decision_id = self.routed(runtime='executor-defined')
        self.register()
        result = self.record('startup', observed={'runtime': 'claude', 'model': 'sonnet', 'effort': 'high'},
                             evidence=['native.jsonl:1'])
        self.assertTrue(result['verified'])
        self.assertIn('not recorded: Requested settings must match', result['journal']['execution'])
        self.assertEqual([row['event'] for row in self.annotations(decision_id)], ['action'])

    def test_later_quality_signals_update_the_routed_outcome(self):
        decision_id = self.routed()
        self.register()
        self.ready()
        self.watch()
        self.record('reconciled', evidence=['native worker idle with its report'])
        self.collect()
        self.cli('attribute', '--attempt', 'ticket-1/1', '--kind', 'review-defect', '--count', '2',
                 '--evidence', 'spec-review.md#F-01')
        self.register('ticket-1/repair-1', 'ticket-1-repair', 'native-2', 'pane-2', repairs='ticket-1/1')
        self.cli('attribute', '--attempt', 'ticket-1/1', '--kind', 'revert', '--evidence', 'revert of head-1')
        outcome = self.annotations(decision_id)[-1]
        self.assertEqual((outcome['event'], outcome['status'], outcome['revision']), ('outcome', 'failed', 'head-1'))
        self.assertEqual({key: value for key, value in outcome['metrics'].items() if key != 'worker_seconds'},
                         {'review_defects': 2, 'repair_rounds': 1, 'reverts': 1})
        self.assertIn('spec-review.md#F-01', outcome['evidence'])
        self.register('ticket-2/1', 'ticket-2', 'native-3', 'pane-3')
        error = self.cli('attribute', '--attempt', 'ticket-2/1', '--kind', 'owner-defect',
                         '--evidence', 'owner report', code=2)
        self.assertIn('collected attempt', error)
        self.register('ticket-3/1', 'ticket-3', 'native-4', 'pane-4', repairs='ticket-2/1', code=2)

    def test_acceptance_is_recorded_once_on_a_completed_collected_attempt(self):
        self.register()
        self.ready()
        error = self.record('accepted', commit='merge-1', evidence=['git log merge-1'], code=2)
        self.assertIn('completed result', error)
        self.watch()
        self.record('reconciled', evidence=['native worker idle with its report'])
        self.collect()
        self.acknowledge()
        self.record('closed', evidence=['native session exited'], acceptance={'decision': 'deferred', 'reason': 'acceptance checks pending'})
        self.assertIn('commit', self.record('accepted', 'ticket-1/1', evidence=['log'], code=2))
        self.record('accepted', commit='merge-1', evidence=['git log merge-1'])
        accepted = self.cli('status')['attempts'][0]['accepted']
        self.assertEqual((accepted['commit'], accepted['evidence']), ('merge-1', ['git log merge-1']))
        self.assertIn('already accepted', self.record('accepted', commit='merge-2', evidence=['log'], code=2))

    def test_closing_a_completed_implementer_settles_its_acceptance(self):
        self.register()
        self.ready()
        self.collect()
        self.acknowledge()
        error = self.record('closed', evidence=['native session exited'], code=2)
        self.assertIn('acceptance', error)
        self.assertIn('Settle acceptance', self.record(
            'closed', evidence=['native session exited'], acceptance={'decision': 'deferred'}, code=2))
        self.record('closed', evidence=['native session exited'],
                    acceptance={'decision': 'accepted', 'commit': 'merge-1', 'evidence': ['git log merge-1']})
        attempt = self.cli('status')['attempts'][0]
        self.assertEqual(attempt['accepted']['commit'], 'merge-1')
        self.assertEqual(attempt['attention'], [])
        # Acceptance can wait for checks; until then the attempt asks for it.
        self.register('ticket-2/1', 'ticket-2', 'native-2', 'pane-2')
        self.ready('ticket-2/1')
        self.collect('ticket-2/1')
        self.acknowledge()
        self.record('closed', 'ticket-2/1', evidence=['native session exited'],
                    acceptance={'decision': 'deferred', 'reason': 'integration gate still running'})
        deferred = self.cli('status', '--attempt', 'ticket-2/1')['attempts'][0]
        self.assertIn('record acceptance or decline', deferred['attention'])
        self.record('accepted', 'ticket-2/1', commit='merge-2', evidence=['git log merge-2'])
        self.assertEqual(self.cli('status', '--attempt', 'ticket-2/1')['attempts'][0]['attention'], [])
        # A declined attempt is settled and cannot be accepted later.
        self.register('ticket-3/1', 'ticket-3', 'native-3', 'pane-3')
        self.ready('ticket-3/1')
        self.collect('ticket-3/1')
        self.acknowledge()
        self.record('closed', 'ticket-3/1', evidence=['native session exited'],
                    acceptance={'decision': 'declined', 'reason': 'criteria 2 unmet; replaced by attempt 2'})
        declined = self.cli('status', '--attempt', 'ticket-3/1')['attempts'][0]
        self.assertEqual((declined['declined']['reason'], declined['attention']),
                         ('criteria 2 unmet; replaced by attempt 2', []))
        self.assertIn('declined', self.record('accepted', 'ticket-3/1', commit='m', evidence=['log'], code=2))

    def test_other_roles_close_without_an_acceptance_decision(self):
        self.execution.write_text(json.dumps({'harness': 'claude', 'role': 'spec-reviewer',
                                             'settings': {'model': 'sonnet', 'effort': 'high'}}))
        self.register()
        self.ready()
        self.collect()
        self.acknowledge()
        self.record('closed', evidence=['native session exited'])
        self.assertEqual(self.cli('status')['attempts'][0]['attention'], [])

    def test_each_notified_wake_is_triaged_in_shadow_and_a_direct_collection_labels_it(self):
        execution = json.loads(self.execution.read_text())
        execution['decision_policy'] = {'enabled': ['wake-triage'], 'backend': self.system_one()}
        self.execution.write_text(json.dumps(execution))
        journal = self.root / 'decisions.jsonl'
        self.register(journal=str(journal))
        self.ready()
        report = self.root / 'report.md'
        report.write_text('Implemented at head-1; all checks pass.\n')
        parent = self.root / 'parent.jsonl'
        request = self.root / 'wait.json'
        request.write_text(json.dumps({'argv': [sys.executable, '-c', 'print("idle")'], 'timeout': 2,
            'notify': {'argv': [sys.executable, '-c',
                                f'import sys; open({str(parent)!r}, "a").write(sys.argv[1] + "\\n")', '{receipt}'],
                       'timeout': 2},
            'capture': [sys.executable, '-c', 'print("Implemented; report written. All checks pass.")']}))
        receipt = self.cli('watch', '--attempt', 'ticket-1/1', '--input', str(request))
        triage = self.cli('status')['pending'][0]['payload']['triage']
        self.assertEqual(triage['status'], 'recorded')
        decision = [row for row in decision_journal.read(journal) if row['event'] == 'decision'][0]
        self.assertEqual(decision['decision_id'], triage['decision_id'])
        self.assertEqual(decision['request']['family'], 'wake-triage')
        self.assertEqual(decision['assignment'], f"ticket-1/1/wake-{receipt['event_id']}")
        self.assertIn('All checks pass.', decision['request']['state'])
        # The host is woken with the receipt alone; the label stays hidden.
        self.assertNotIn('triage', parent.read_text())
        self.record('reconciled', evidence=['native worker idle with its report'])
        self.collect(report=report)
        assessment = [row for row in decision_journal.read(journal) if row['event'] == 'assessment'][0]
        self.assertEqual((assessment['expected'], assessment['source'], assessment['evidence']),
                         (['done'], 'objective', [str(report)]))

    def test_a_report_written_after_the_wake_does_not_label_it_done(self):
        execution = json.loads(self.execution.read_text())
        execution['decision_policy'] = {'enabled': ['wake-triage'], 'backend': self.system_one()}
        self.execution.write_text(json.dumps(execution))
        journal = self.root / 'decisions.jsonl'
        self.register(journal=str(journal))
        self.ready()
        request = self.root / 'wait.json'
        request.write_text(json.dumps({'argv': [sys.executable, '-c', 'print("idle")'], 'timeout': 2,
            'notify': {'argv': [sys.executable, '-c', 'pass', '{receipt}'], 'timeout': 2},
            'capture': [sys.executable, '-c', 'print("Running tests... 12/40")']}))
        self.cli('watch', '--attempt', 'ticket-1/1', '--input', str(request))
        self.record('reconciled', evidence=['native worker still running tests'])
        time.sleep(1.1)
        self.collect()
        self.assertEqual([row['event'] for row in decision_journal.read(journal)], ['decision'])

    def test_an_invalid_wait_is_refused_before_its_channel_is_checked(self):
        self.register()
        parent = self.root / 'parent.jsonl'
        request = self.root / 'wait.json'
        request.write_text(json.dumps({'argv': [sys.executable, '-c', 'print("idle")'], 'timeout': 2,
            'notify': {'argv': [sys.executable, '-c',
                                f'import sys; open({str(parent)!r}, "a").write(sys.argv[1])', '{receipt}'],
                       'timeout': 2}}))
        error = self.cli('watch', '--attempt', 'ticket-1/1', '--input', str(request), code=2)
        self.assertIn('Wait requires a verified, unfinished worker', error)
        self.assertFalse(parent.exists())

    def test_a_channel_whose_latest_delivery_failed_is_checked_again(self):
        self.register()
        self.ready()
        parent = self.root / 'parent.jsonl'
        argv = [sys.executable, '-c', f'import sys; open({str(parent)!r}, "a").write(sys.argv[1] + "\\n")', '{receipt}']
        self.cli('status')
        db = sqlite3.connect(self.state)
        # Recorded out of order: the later-numbered delivery finished first.
        for finished_at, state in ((145, 'failed'), (100, 'sent')):
            db.execute('INSERT INTO events (attempt, kind, payload, acknowledged) VALUES (?, ?, ?, 1)',
                       ('ticket-1/1', 'wait-finished', json.dumps({'notify': {'argv': argv, 'timeout': 2},
                        'delivery': {'state': state, 'finished_at': finished_at}, 'recorded_at': finished_at})))
        db.commit()
        db.close()
        request = self.root / 'wait.json'
        request.write_text(json.dumps({'argv': [sys.executable, '-c', 'print("idle")'], 'timeout': 2,
                                       'notify': {'argv': argv, 'timeout': 2}}))
        self.cli('watch', '--attempt', 'ticket-1/1', '--input', str(request))
        kinds = [json.loads(line)['kind'] for line in parent.read_text().splitlines()]
        self.assertEqual(kinds, ['channel-check', 'wait-finished'])

    def test_long_wait_requires_completion_channel_before_command_invocation(self):
        self.register()
        self.ready()
        marker = self.root / 'invoked'
        request = self.root / 'wait.json'
        request.write_text(json.dumps({'argv': [sys.executable, '-c',
            f'from pathlib import Path; Path({str(marker)!r}).touch()'], 'timeout': 61}))
        self.cli('watch', '--attempt', 'ticket-1/1', '--input', str(request), code=2)
        self.assertFalse(marker.exists())
        self.assertNotIn('monitor', self.cli('status')['attempts'][0])

    def test_delivery_timeout_is_durable_without_changing_worker_receipt(self):
        self.register()
        self.ready()
        request = self.root / 'wait.json'
        request.write_text(json.dumps({'argv': [sys.executable, '-c', 'print("settled")'],
            'timeout': 2, 'notify': {'argv': [sys.executable, '-c',
                'import json,sys,time; json.loads(sys.argv[1])["kind"] == "channel-check" or time.sleep(30)',
                '{receipt}'], 'timeout': .1}}))
        receipt = self.cli('watch', '--attempt', 'ticket-1/1', '--input', str(request))
        self.assertEqual(receipt['exit_code'], 0)
        pending = self.cli('status')['pending'][0]
        self.assertEqual(pending['payload']['delivery']['exit_code'], 124)
        self.assertEqual(pending['payload']['delivery']['state'], 'failed')

    def test_lost_delivery_owner_requires_callback_teardown_before_retry(self):
        self.register()
        self.ready()
        pidfile = self.root / 'notification-pid'
        request = self.root / 'wait.json'
        request.write_text(json.dumps({'argv': [sys.executable, '-c', 'print("settled")'],
            'timeout': 2, 'notify': {'argv': [sys.executable, '-c',
                'import json,sys; json.loads(sys.argv[1])["kind"] == "channel-check" and sys.exit(); '
                f'import os,time; open({str(pidfile)!r}, "w").write(str(os.getpid())); time.sleep(30)',
                '{receipt}'], 'timeout': 40}}))
        watcher = subprocess.Popen([sys.executable, '-B', str(SCRIPT), 'watch', '--state', str(self.state),
                                    '--attempt', 'ticket-1/1', '--input', str(request)],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        callback_pid = None
        try:
            deadline = time.monotonic() + 5
            while not pidfile.exists() and time.monotonic() < deadline:
                time.sleep(.02)
            self.assertTrue(pidfile.exists())
            callback_pid = int(pidfile.read_text())
            watcher.kill()
            watcher.communicate(timeout=5)
            queued = self.cli('status')['pending'][0]
            self.assertEqual(queued['payload']['delivery']['state'], 'sending')
            retry = self.root / 'retry.json'
            retry.write_text(json.dumps({'retry': True, 'evidence': ['lost owner inspected']}))
            error = self.cli('deliver', '--event-id', str(queued['id']), '--input', str(retry), code=2)
            self.assertIn('Owned notification process', error)
        finally:
            if callback_pid:
                try:
                    os.killpg(callback_pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            if watcher.poll() is None:
                watcher.kill()
                watcher.communicate(timeout=5)

    def test_old_attempt_cannot_retire_an_unfinished_continuation(self):
        self.register()
        self.ready()
        self.collect()
        self.acknowledge()
        self.record('retain', reason='same-assignment recheck', next_use='recheck', evidence=['report'])
        self.register('ticket-1/2')
        self.herdr_fixture()
        request = self.root / 'retire.json'
        request.write_text(json.dumps({'session': 'fixture-session', 'pane': 'pane-1',
                                       'jobs_evidence': ['owned jobs inspected']}))
        error = self.cli('retire', '--attempt', 'ticket-1/1', '--input', str(request), code=2)
        self.assertIn('final registered attempt', error)
        self.assertFalse((self.root / 'native-closed').exists())

    def test_retirement_resolves_moved_caller_identity(self):
        self.register()
        self.ready()
        self.collect()
        self.acknowledge()
        self.herdr_fixture(caller='pane-1')
        self.native_env['HERDR_PANE_ID'] = 'old-caller-id'
        request = self.root / 'retire.json'
        request.write_text(json.dumps({'session': 'fixture-session', 'pane': 'pane-1',
                                       'jobs_evidence': ['owned jobs inspected']}))
        error = self.cli('retire', '--attempt', 'ticket-1/1', '--input', str(request), code=2)
        self.assertIn('Caller pane', error)
        self.assertFalse((self.root / 'native-closed').exists())

    def herdr_fixture(self, native_session='native-1', verify_error='pane_not_found', caller=None):
        directory = self.root / 'bin'
        directory.mkdir(exist_ok=True)
        executable = directory / 'herdr'
        executable.write_text('#!' + sys.executable + '\n' + f'''
import json,sys
from pathlib import Path
marker=Path({str(self.root / 'native-closed')!r})
args=sys.argv[1:]
assert args[:2]==['--session','fixture-session']
if args[2:]==['pane','current','--current']:
    if {caller!r} is None:
        print(json.dumps({{'error':{{'code':'pane_not_found'}}}}),file=sys.stderr);sys.exit(1)
    print(json.dumps({{'result':{{'pane':{{'pane_id':{caller!r}}}}}}}))
elif args[2:]==['agent','get','pane-1']:
    if marker.exists():
        print(json.dumps({{'error':{{'code':'agent_not_found'}}}}),file=sys.stderr);sys.exit(1)
    print(json.dumps({{'result':{{'agent':{{'agent':'claude','pane_id':'pane-1','agent_status':'idle',
        'agent_session':{{'kind':'id','value':{native_session!r}}}}}}}}}))
elif args[2:]==['pane','close','pane-1']:
    marker.write_text(marker.read_text()+'closed'+chr(10) if marker.exists() else 'closed'+chr(10))
    print(json.dumps({{'result':{{'type':'ok'}}}}))
elif args[2:]==['pane','get','pane-1']:
    if marker.exists():
        print(json.dumps({{'error':{{'code':{verify_error!r}}}}}),file=sys.stderr);sys.exit(1)
    print(json.dumps({{'result':{{'pane':{{'pane_id':'pane-1'}}}}}}))
else: sys.exit(3)
''')
        executable.chmod(0o700)
        self.native_env = dict(os.environ, PATH=str(directory) + os.pathsep + os.environ['PATH'],
                               HERDR_PANE_ID='caller-pane')

    def test_collect_persists_and_acknowledges_result_then_confirms_native_retirement(self):
        self.register()
        self.ready()
        self.watch()
        self.record('reconciled', evidence=['owned wait stopped and native report inspected'])
        self.herdr_fixture()
        report = self.root / 'report.md'
        report.write_text('Completed assignment at head-1\n')
        request = self.root / 'collect.json'
        request.write_text(json.dumps({'status': 'completed', 'head': 'head-1', 'report': str(report),
            'evidence': ['current report checked'], 'disposition': {'kind': 'retire',
            'session': 'fixture-session', 'pane': 'pane-1', 'jobs_evidence': ['owned jobs stopped'],
            'acceptance': {'decision': 'deferred', 'reason': 'acceptance checks pending'}}}))
        self.cli('collect', '--attempt', 'ticket-1/1', '--input', str(request))
        self.assertTrue((self.root / 'native-closed').is_file())
        status = self.cli('status')
        self.assertTrue(status['attempts'][0]['closed'])
        self.assertEqual(status['pending'], [])
        self.assertTrue(report.is_file())

    def test_retiring_a_completed_implementer_settles_acceptance_before_closing_the_pane(self):
        self.register()
        self.ready()
        self.collect()
        self.acknowledge()
        self.herdr_fixture()
        request = self.root / 'retire.json'
        retire = {'session': 'fixture-session', 'pane': 'pane-1', 'jobs_evidence': ['owned jobs stopped']}
        request.write_text(json.dumps(retire))
        self.assertIn('acceptance', self.cli('retire', '--attempt', 'ticket-1/1', '--input', str(request), code=2))
        self.assertFalse((self.root / 'native-closed').exists())
        request.write_text(json.dumps(dict(retire, acceptance={
            'decision': 'accepted', 'commit': 'merge-1', 'evidence': ['topic fast-forwarded to merge-1']})))
        self.cli('retire', '--attempt', 'ticket-1/1', '--input', str(request))
        attempt = self.cli('status')['attempts'][0]
        self.assertEqual((attempt['accepted']['commit'], attempt['closed']['acceptance']['decision']),
                         ('merge-1', 'accepted'))

    def test_collect_rejects_missing_disposition_before_recording_result(self):
        self.register()
        self.ready()
        report = self.root / 'report.md'
        report.write_text('Completed at head-1\n')
        request = self.root / 'collect.json'
        request.write_text(json.dumps({'status': 'completed', 'head': 'head-1', 'report': str(report),
                                       'evidence': ['checked report']}))
        self.cli('collect', '--attempt', 'ticket-1/1', '--input', str(request), code=2)
        self.assertNotIn('result', self.cli('status')['attempts'][0])

    def test_retirement_rejects_user_owned_and_caller_panes(self):
        self.register(owned=False)
        self.ready()
        self.collect()
        self.acknowledge()
        self.herdr_fixture()
        request = self.root / 'retire.json'
        request.write_text(json.dumps({'session': 'fixture-session', 'pane': 'pane-1',
                                       'jobs_evidence': ['owned jobs inspected']}))
        self.cli('retire', '--attempt', 'ticket-1/1', '--input', str(request), code=2)
        self.assertFalse((self.root / 'native-closed').exists())
        self.register('ticket-2/1', 'ticket-2', 'native-2', 'pane-2')
        self.ready('ticket-2/1')
        self.collect('ticket-2/1')
        self.acknowledge()
        self.native_env['HERDR_PANE_ID'] = 'pane-1'
        self.cli('retire', '--attempt', 'ticket-2/1', '--input', str(request), code=2)
        self.assertFalse((self.root / 'native-closed').exists())

    def test_retirement_rejects_a_replaced_native_conversation(self):
        self.register()
        self.ready()
        self.collect()
        self.acknowledge()
        self.herdr_fixture(native_session='different-native-session')
        request = self.root / 'retire.json'
        request.write_text(json.dumps({'session': 'fixture-session', 'pane': 'pane-1',
                                       'jobs_evidence': ['owned jobs inspected'], 'acceptance': {'decision': 'deferred', 'reason': 'acceptance checks pending'}}))
        error = self.cli('retire', '--attempt', 'ticket-1/1', '--input', str(request), code=2)
        self.assertIn('conversation no longer matches', error)
        self.assertFalse((self.root / 'native-closed').exists())

    def test_collection_preserves_pending_design_escalation(self):
        self.register()
        self.ready()
        self.record('hold', reason='Possible agreement breach', brief=str(self.root / 'brief.md'),
                    evidence=['worker blocker'])
        report = self.root / 'report.md'
        report.write_text('Blocked on the human agreement ruling\n')
        request = self.root / 'collect.json'
        request.write_text(json.dumps({'status': 'blocked', 'head': 'head-1', 'report': str(report),
            'evidence': ['blocked report'], 'disposition': {'kind': 'retain',
            'reason': 'Human ruling remains pending', 'next_use': 'Resume only after ruling',
            'evidence': ['brief and governing contract']}}))
        self.cli('collect', '--attempt', 'ticket-1/1', '--input', str(request))
        status = self.cli('status')
        self.assertEqual([r['kind'] for r in status['pending']], ['hold'])
        self.assertEqual(status['holds'][0]['assignment'], 'ticket-1')

    def test_native_closure_recovery_preserves_report_and_does_not_close_twice(self):
        self.register()
        self.ready()
        self.herdr_fixture(verify_error='server_unavailable')
        report = self.root / 'report.md'
        report.write_text('Completed at head-1\n')
        request = self.root / 'collect.json'
        request.write_text(json.dumps({'status': 'completed', 'head': 'head-1', 'report': str(report),
            'evidence': ['checked report'], 'disposition': {'kind': 'retire',
            'session': 'fixture-session', 'pane': 'pane-1', 'jobs_evidence': ['owned jobs stopped'],
            'acceptance': {'decision': 'deferred', 'reason': 'acceptance checks pending'}}}))
        self.cli('collect', '--attempt', 'ticket-1/1', '--input', str(request), code=2)
        status = self.cli('status')
        self.assertIn('result', status['attempts'][0])
        self.assertNotIn('closed', status['attempts'][0])
        self.assertEqual(status['attempts'][0]['retirement_requested']['pane'], 'pane-1')
        self.herdr_fixture()
        self.cli('collect', '--attempt', 'ticket-1/1', '--input', str(request))
        self.cli('collect', '--attempt', 'ticket-1/1', '--input', str(request))
        self.assertEqual((self.root / 'native-closed').read_text(), 'closed\n')

    def test_final_retirement_releases_worker_handle_of_earlier_retained_attempts(self):
        self.register()
        self.ready()
        self.collect()
        self.acknowledge()
        self.record('retain', reason='Same-assignment recheck needed', next_use='final recheck',
                    evidence=['review report'])
        self.register('ticket-1/2')
        self.ready('ticket-1/2')
        self.collect('ticket-1/2')
        self.acknowledge()
        self.herdr_fixture()
        request = self.root / 'retire.json'
        request.write_text(json.dumps({'session': 'fixture-session', 'pane': 'pane-1',
                                       'jobs_evidence': ['final same-assignment use, jobs stopped'],
                                       'acceptance': {'decision': 'deferred', 'reason': 'acceptance checks pending'}}))
        self.cli('retire', '--attempt', 'ticket-1/2', '--input', str(request))
        status = self.cli('status')
        self.assertEqual(status['attempts'][0]['native_closed_by'], 'ticket-1/2')
        self.cli('retire', '--attempt', 'ticket-1/1', '--input', str(request))
        self.assertEqual((self.root / 'native-closed').read_text(), 'closed\n')
        self.register('ticket-2/1', 'ticket-2', 'native-2', 'pane-1')
        self.register('ticket-3/1', 'ticket-3', 'native-1', 'different-pane', code=2)

    def test_submit_reads_native_settings_before_running_the_productive_command(self):
        self.register()
        native = self.root / 'native.jsonl'
        native.write_text(json.dumps({'type': 'assistant', 'sessionId': 'native-1',
                                     'isSidechain': False, 'cwd': str(self.root),
                                     'effort': 'high', 'perTurnEffort': 'high',
                                     'message': {'model': 'sonnet'}}) + '\n')
        marker = self.root / 'productive-work'
        request = self.root / 'submit.json'
        request.write_text(json.dumps({'native': str(native), 'timeout': 2,
                                      'argv': [sys.executable, '-c',
                                               'from pathlib import Path; Path("productive-work").write_text("ran")']}))
        result = self.cli('submit', '--attempt', 'ticket-1/1', '--input', str(request))
        self.assertEqual(result['exit_code'], 0)
        self.assertTrue(marker.is_file())
        attempt = self.cli('status')['attempts'][0]
        self.assertEqual(attempt['observed'], {'runtime': 'claude', 'model': 'sonnet', 'effort': 'high'})
        self.assertEqual(self.cli('status')['pending'][0]['kind'], 'wait-finished')

    def test_submit_allows_claude_to_work_in_a_checkout_subdirectory(self):
        self.register()
        child = self.root / '.scratch' / 'reports'
        child.mkdir(parents=True)
        native = self.root / 'native.jsonl'
        native.write_text(json.dumps({'type': 'assistant', 'sessionId': 'native-1',
            'cwd': str(child), 'perTurnEffort': 'high', 'message': {'model': 'sonnet'}}) + '\n')
        request = self.root / 'submit.json'
        request.write_text(json.dumps({'native': str(native), 'timeout': 2,
            'argv': [sys.executable, '-c', 'from pathlib import Path; Path("productive-work").touch()']}))
        self.cli('submit', '--attempt', 'ticket-1/1', '--input', str(request))
        self.assertTrue((self.root / 'productive-work').exists())

    def test_submit_rejects_nested_claude_repository_boundaries(self):
        self.register()
        nested = self.root / 'other-project'
        child = nested / 'src'
        child.mkdir(parents=True)
        native = self.root / 'native.jsonl'
        native.write_text(json.dumps({'type': 'assistant', 'sessionId': 'native-1',
            'cwd': str(child), 'perTurnEffort': 'high', 'message': {'model': 'sonnet'}}) + '\n')
        request = self.root / 'submit.json'
        request.write_text(json.dumps({'native': str(native), 'timeout': 2,
            'argv': [sys.executable, '-c', 'from pathlib import Path; Path("productive-work").touch()']}))
        boundary = nested / '.git'
        for kind in ('directory', 'worktree-file'):
            with self.subTest(kind=kind):
                if kind == 'directory':
                    boundary.mkdir()
                else:
                    boundary.write_text('gitdir: /another/worktree\n')
                self.cli('submit', '--attempt', 'ticket-1/1', '--input', str(request), code=2)
                self.assertFalse((self.root / 'productive-work').exists())
                if kind == 'directory':
                    boundary.rmdir()
                else:
                    boundary.unlink()

    def test_submit_reads_codex_session_and_latest_turn_controls(self):
        self.execution.write_text(json.dumps({'harness': 'codex', 'role': 'implementer',
                                             'settings': {'model': 'gpt-6.1-sol', 'effort': 'high'}}))
        self.register(runtime='codex')
        native = self.root / 'native.jsonl'
        rows = [{'type': 'session_meta', 'payload': {'id': 'native-1', 'cwd': str(self.root)}},
                {'type': 'turn_context', 'payload': {'model': 'gpt-6.1-sol', 'effort': 'medium', 'cwd': str(self.root)}},
                {'type': 'turn_context', 'payload': {'model': 'gpt-6.1-sol', 'effort': 'high', 'cwd': str(self.root)}}]
        native.write_text(''.join(json.dumps(row) + '\n' for row in rows))
        request = self.root / 'submit.json'
        request.write_text(json.dumps({'native': str(native), 'timeout': 2,
                                      'argv': [sys.executable, '-c', 'print("accepted")']}))
        self.cli('submit', '--attempt', 'ticket-1/1', '--input', str(request))
        self.assertEqual(self.cli('status')['attempts'][0]['observed'],
                         {'runtime': 'codex', 'model': 'gpt-6.1-sol', 'effort': 'high'})

    def test_submit_reads_pi_controls_from_active_branch(self):
        self.execution.write_text(json.dumps({'harness': 'pi', 'role': 'implementer',
                                             'settings': {'model': 'dgx/glm-5.3-flash', 'effort': 'high'}}))
        self.register(runtime='pi')
        native = self.root / 'native.jsonl'
        rows = [{'type': 'session', 'id': 'native-1', 'cwd': str(self.root)},
                {'type': 'model_change', 'id': 'model', 'parentId': None,
                 'provider': 'dgx', 'modelId': 'glm-5.3-flash'},
                {'type': 'thinking_level_change', 'id': 'high', 'parentId': 'model', 'thinkingLevel': 'high'},
                {'type': 'thinking_level_change', 'id': 'abandoned', 'parentId': 'high', 'thinkingLevel': 'low'},
                {'type': 'message', 'id': 'active', 'parentId': 'high',
                 'message': {'role': 'assistant', 'provider': 'dgx', 'model': 'glm-5.3-flash'}}]
        native.write_text(''.join(json.dumps(row) + '\n' for row in rows))
        request = self.root / 'submit.json'
        request.write_text(json.dumps({'native': str(native), 'timeout': 2,
                                      'argv': [sys.executable, '-c', 'print("accepted")']}))
        self.cli('submit', '--attempt', 'ticket-1/1', '--input', str(request))
        self.assertEqual(self.cli('status')['attempts'][0]['observed'],
                         {'runtime': 'pi', 'model': 'dgx/glm-5.3-flash', 'effort': 'high'})

    def test_submit_refuses_pi_provider_error_until_a_successful_probe(self):
        self.execution.write_text(json.dumps({'harness': 'pi', 'role': 'implementer',
            'settings': {'model': 'dgx/glm-5.3-flash', 'effort': 'high'}}))
        self.register(runtime='pi')
        native = self.root / 'native.jsonl'
        rows = [{'type': 'session', 'id': 'native-1', 'cwd': str(self.root)},
                {'type': 'model_change', 'id': 'model', 'parentId': None,
                 'provider': 'dgx', 'modelId': 'glm-5.3-flash'},
                {'type': 'thinking_level_change', 'id': 'high', 'parentId': 'model',
                 'thinkingLevel': 'high'},
                {'type': 'message', 'id': 'failed', 'parentId': 'high', 'message': {
                    'role': 'assistant', 'provider': 'dgx', 'model': 'glm-5.3-flash',
                    'stopReason': 'error', 'errorMessage': 'Connection error.'}}]
        native.write_text(''.join(json.dumps(row) + '\n' for row in rows))
        request = self.root / 'submit.json'
        request.write_text(json.dumps({'native': str(native), 'timeout': 2,
            'argv': [sys.executable, '-c', 'from pathlib import Path; Path("productive-work").touch()']}))
        error = self.cli('submit', '--attempt', 'ticket-1/1', '--input', str(request), code=2)
        self.assertIn('failed native response', error)
        self.assertFalse((self.root / 'productive-work').exists())
        rows.append({'type': 'message', 'id': 'ready', 'parentId': 'failed', 'message': {
            'role': 'assistant', 'provider': 'dgx', 'model': 'glm-5.3-flash', 'stopReason': 'stop'}})
        native.write_text(''.join(json.dumps(row) + '\n' for row in rows))
        self.cli('submit', '--attempt', 'ticket-1/1', '--input', str(request))
        self.assertTrue((self.root / 'productive-work').exists())

    def test_submit_reads_opencode_assistant_controls_instead_of_requested_defaults(self):
        self.execution.write_text(json.dumps({'harness': 'opencode', 'role': 'implementer',
                                             'settings': {'model': 'opencode/muse-spark-1.3-contributor-free',
                                                          'effort': 'high'}}))
        self.register(runtime='opencode')
        native = self.root / 'native.json'
        native.write_text(json.dumps({'info': {'id': 'native-1', 'directory': str(self.root),
                                               'model': {'modelID': 'different-default'}},
            'messages': [{'info': {'role': 'assistant', 'sessionID': 'native-1',
                                  'providerID': 'opencode', 'modelID': 'muse-spark-1.3-contributor-free',
                                  'variant': 'high'}}]}))
        request = self.root / 'submit.json'
        request.write_text(json.dumps({'native': str(native), 'timeout': 2,
                                      'argv': [sys.executable, '-c', 'print("accepted")']}))
        self.cli('submit', '--attempt', 'ticket-1/1', '--input', str(request))
        self.assertEqual(self.cli('status')['attempts'][0]['observed'],
                         {'runtime': 'opencode', 'model': 'opencode/muse-spark-1.3-contributor-free',
                          'effort': 'high'})

    def test_submit_refuses_opencode_tool_error_until_a_clean_new_probe(self):
        self.execution.write_text(json.dumps({'harness': 'opencode', 'role': 'implementer',
            'settings': {'model': 'opencode/muse-spark-1.3-contributor-free'}}))
        self.register(runtime='opencode')
        native = self.root / 'native-export.json'
        assistant = {'role': 'assistant', 'sessionID': 'native-1',
            'providerID': 'opencode', 'modelID': 'muse-spark-1.3-contributor-free'}
        data = {'info': {'id': 'native-1', 'directory': str(self.root)}, 'messages': [
            {'info': {'role': 'user', 'sessionID': 'native-1'}},
            {'info': assistant, 'parts': [{'type': 'tool', 'state': {'status': 'error',
                'error': 'The user rejected permission to use this specific tool call.'}}]},
            {'info': assistant, 'parts': [{'type': 'text', 'text': 'Required read was denied.'}]}]}
        native.write_text(json.dumps(data))
        request = self.root / 'submit.json'
        request.write_text(json.dumps({'native': str(native), 'timeout': 2,
            'argv': [sys.executable, '-c', 'from pathlib import Path; Path("productive-work").touch()']}))
        self.cli('submit', '--attempt', 'ticket-1/1', '--input', str(request), code=2)
        self.assertFalse((self.root / 'productive-work').exists())
        # A later successful startup probe does not inherit the earlier tool failure.
        data['messages'].extend([{'info': {'role': 'user', 'sessionID': 'native-1'}},
            {'info': assistant, 'parts': [{'type': 'tool', 'state': {'status': 'completed'}}]}])
        native.write_text(json.dumps(data))
        self.cli('submit', '--attempt', 'ticket-1/1', '--input', str(request))
        self.assertTrue((self.root / 'productive-work').exists())

    def test_submit_refuses_opencode_provider_error_even_when_settings_match(self):
        self.execution.write_text(json.dumps({'harness': 'opencode', 'role': 'implementer',
                                             'settings': {'model': 'opencode/muse-spark-1.3-contributor-free'}}))
        self.register(runtime='opencode')
        native = self.root / 'native.json'
        native.write_text(json.dumps({'info': {'id': 'native-1', 'directory': str(self.root)},
            'messages': [{'info': {'role': 'assistant', 'sessionID': 'native-1',
                                  'providerID': 'opencode', 'modelID': 'muse-spark-1.3-contributor-free',
                                  'error': {'name': 'APIError', 'data': {'statusCode': 403}}}}]}))
        request = self.root / 'submit.json'
        request.write_text(json.dumps({'native': str(native), 'timeout': 2,
                                      'argv': [sys.executable, '-c',
                                               'from pathlib import Path; Path("productive-work").touch()']}))
        error = self.cli('submit', '--attempt', 'ticket-1/1', '--input', str(request), code=2)
        self.assertIn('failed native response', error)
        self.assertFalse((self.root / 'productive-work').exists())

    def test_submit_refuses_wrong_unknown_and_unbound_native_controls(self):
        self.register()
        native = self.root / 'native.jsonl'
        marker = self.root / 'productive-work'
        request = self.root / 'submit.json'
        request.write_text(json.dumps({'native': str(native), 'timeout': 2,
                                      'argv': [sys.executable, '-c',
                                               'from pathlib import Path; Path("productive-work").touch()']}))
        good = {'type': 'assistant', 'sessionId': 'native-1', 'cwd': str(self.root),
                'message': {'model': 'sonnet'}, 'effort': 'high'}
        invalid = [dict(good, message={'model': 'opus'}), dict(good, perTurnEffort='medium'),
                   dict(good, effort=None), dict(good, sessionId='different-session'),
                   dict(good, cwd=str(self.root / 'different-worktree')),
                   dict(good, isSidechain=True), dict(good, message='unsupported schema')]
        for row in invalid:
            with self.subTest(row=row):
                native.write_text(json.dumps(row) + '\n')
                self.cli('submit', '--attempt', 'ticket-1/1', '--input', str(request), code=2)
                self.assertFalse(marker.exists())
        native.write_text(json.dumps(good))
        self.cli('submit', '--attempt', 'ticket-1/1', '--input', str(request), code=2)
        self.assertFalse(marker.exists())

    def test_submit_accepts_only_explicit_model_alias_evidence(self):
        self.register()
        native = self.root / 'native.jsonl'
        native.write_text(json.dumps({'type': 'assistant', 'sessionId': 'native-1', 'cwd': str(self.root),
                                     'message': {'model': 'claude-sonnet-native'}, 'effort': 'high'}) + '\n')
        request = self.root / 'submit.json'
        data = {'native': str(native), 'timeout': 2,
                'argv': [sys.executable, '-c', 'print("accepted")']}
        request.write_text(json.dumps(data))
        self.cli('submit', '--attempt', 'ticket-1/1', '--input', str(request), code=2)
        data['model_alias_evidence'] = ['installed binding: sonnet = claude-sonnet-native']
        request.write_text(json.dumps(data))
        native.write_text(json.dumps({'type': 'assistant', 'sessionId': 'native-1', 'cwd': str(self.root),
                                     'message': {'model': 'claude-sonnet-native'}, 'effort': 'medium'}) + '\n')
        self.cli('submit', '--attempt', 'ticket-1/1', '--input', str(request), code=2)
        native.write_text(json.dumps({'type': 'assistant', 'sessionId': 'native-1', 'cwd': str(self.root),
                                     'message': {'model': 'claude-sonnet-native'}, 'effort': 'high'}) + '\n')
        self.cli('submit', '--attempt', 'ticket-1/1', '--input', str(request))
        self.assertTrue(self.cli('status')['attempts'][0]['verified'])

    def test_submit_leaves_unrequested_native_controls_inherited(self):
        self.execution.write_text(json.dumps({'harness': 'claude', 'role': 'implementer', 'settings': {}}))
        self.register()
        native = self.root / 'native.jsonl'
        native.write_text(json.dumps({'type': 'assistant', 'sessionId': 'native-1', 'cwd': str(self.root),
                                     'message': {'model': 'claude-opus-native'}}) + '\n')
        request = self.root / 'submit.json'
        request.write_text(json.dumps({'native': str(native), 'timeout': 2,
                                      'argv': [sys.executable, '-c', 'print("accepted")']}))
        self.cli('submit', '--attempt', 'ticket-1/1', '--input', str(request))
        attempt = self.cli('status')['attempts'][0]
        self.assertEqual(attempt['requested'], {'runtime': 'claude'})
        self.assertEqual(attempt['observed'], {'runtime': 'claude', 'model': 'claude-opus-native'})

    def test_submit_cannot_duplicate_productive_work_after_reconciliation(self):
        self.register()
        native = self.root / 'native.jsonl'
        native.write_text(json.dumps({'type': 'assistant', 'sessionId': 'native-1', 'cwd': str(self.root),
                                     'message': {'model': 'sonnet'}, 'effort': 'high'}) + '\n')
        request = self.root / 'submit.json'
        request.write_text(json.dumps({'native': str(native), 'timeout': 2,
                                      'argv': [sys.executable, '-c',
                                               'from pathlib import Path; p=Path("count"); p.write_text(p.read_text()+"x" if p.exists() else "x")']}))
        self.cli('submit', '--attempt', 'ticket-1/1', '--input', str(request))
        self.record('reconciled', evidence=['native state inspected; wait finished'])
        self.cli('submit', '--attempt', 'ticket-1/1', '--input', str(request), code=2)
        self.assertEqual((self.root / 'count').read_text(), 'x')

    def test_submit_blocks_an_active_design_hold(self):
        self.register()
        native = self.root / 'native.jsonl'
        native.write_text(json.dumps({'type': 'assistant', 'sessionId': 'native-1', 'cwd': str(self.root),
                                     'message': {'model': 'sonnet'}, 'effort': 'high'}) + '\n')
        self.record('hold', reason='Possible agreement breach', brief=str(self.root / 'brief.md'),
                    evidence=['worker uncertainty signal'])
        request = self.root / 'submit.json'
        request.write_text(json.dumps({'native': str(native), 'timeout': 2,
                                      'argv': [sys.executable, '-c',
                                               'from pathlib import Path; Path("productive-work").touch()']}))
        self.cli('submit', '--attempt', 'ticket-1/1', '--input', str(request), code=2)
        self.assertFalse((self.root / 'productive-work').exists())

    def test_wait_failure_survives_restart_until_acknowledged(self):
        self.register()
        self.ready()
        self.watch(script='import sys; print("provider overloaded", file=sys.stderr); sys.exit(7)', code=7)
        first = self.cli('status')
        self.assertEqual(first['pending'][0]['kind'], 'wait-finished')
        self.assertEqual(first['pending'][0]['payload']['exit_code'], 7)
        log = Path(first['pending'][0]['payload']['log'])
        self.assertIn('provider overloaded', log.read_text())
        self.assertEqual(self.cli('status')['pending'], first['pending'])
        self.assertIn('reconcile wait with native worker and report', first['attempts'][0]['attention'])
        self.cli('ack', '--event-id', str(first['pending'][0]['id']))
        self.assertEqual(self.cli('status')['pending'], [])
        self.assertTrue(log.is_file())

    def test_model_or_effort_mismatch_blocks_work_and_acceptance(self):
        for observed in ({'runtime': 'claude', 'model': 'opus', 'effort': 'high'},
                         {'runtime': 'claude', 'model': 'sonnet', 'effort': 'medium'},
                         {'runtime': 'claude', 'model': 'sonnet'},
                         {'runtime': 'codex', 'model': 'sonnet', 'effort': 'high'}):
            if not self.state.exists():
                self.register()
            result = self.record('startup', observed=observed, evidence=['native.jsonl:1'])
            self.assertFalse(result['verified'])
            gate = self.cli('gate', '--attempt', 'ticket-1/1', '--stage', 'work', code=1)
            self.assertIn('runtime settings verification', gate['missing'])
            self.record('submitted', code=2, evidence=['accepted prompt'])
            self.watch(code=2)
        self.ready()
        self.collect()
        self.assertTrue(self.cli('gate', '--attempt', 'ticket-1/1', '--stage', 'accept',
                                 '--revision', 'head-1')['complete'])
        self.cli('gate', '--attempt', 'ticket-1/1', '--stage', 'accept', '--revision', 'head-2', code=1)

    def test_native_alias_requires_binding_evidence_and_inherited_controls_stay_omitted(self):
        self.register()
        observed = {'runtime': 'claude', 'model': 'claude-sonnet-native', 'effort': 'high'}
        self.assertFalse(self.record('startup', observed=observed, evidence=['native.jsonl:1'])['verified'])
        self.assertTrue(self.record('startup', observed=observed, evidence=['native.jsonl:1'],
                                   model_alias_evidence=['installed catalog binds sonnet to claude-sonnet-native'])['verified'])
        self.execution.write_text(json.dumps({'harness': 'claude', 'role': 'implementer', 'settings': {}}))
        self.register('ticket-2/1', 'ticket-2', 'native-2', 'pane-2')
        self.record('startup', 'ticket-2/1', observed={'runtime': 'claude'}, evidence=['native.jsonl:2'])
        self.assertEqual(self.cli('status')['attempts'][1]['requested'], {'runtime': 'claude'})

    def test_stale_idle_is_a_wait_receipt_and_requires_prompt_and_report(self):
        self.register()
        self.record('startup', observed={'runtime': 'claude', 'model': 'sonnet', 'effort': 'high'},
                    evidence=['native.jsonl:1'])
        self.watch()
        self.cli('gate', '--attempt', 'ticket-1/1', '--stage', 'accept', '--revision', 'head-1', code=1)
        report = self.root / 'report.md'
        report.write_text('An older report\n')
        self.record('result', code=2, status='completed', head='head-1', report=str(report), evidence=['older report'])
        self.record('reconciled', evidence=['native idle, prompt not received'])
        self.record('result', code=2, status='completed', head='head-1', report=str(report), evidence=['older report'])
        self.record('submitted', evidence=['accepted prompt with working activity'])
        self.record('submitted', code=2, evidence=['duplicate prompt'])
        self.watch()
        self.watch(code=2)
        self.record('reconciled', evidence=['native completed this assignment at head-1'])
        self.collect()

    def test_new_ticket_or_role_rejects_reused_native_session(self):
        self.register()
        self.ready()
        self.collect()
        self.record('retain', code=2, reason='Pending repair', next_use='same-ticket repair recheck', evidence=['phase report'])
        self.acknowledge()
        self.record('retain', reason='Pending repair', next_use='same-ticket repair recheck', evidence=['phase report'])
        self.register('ticket-2/1', 'ticket-2', 'native-1', 'pane-2', code=2)
        self.execution.write_text(json.dumps({'harness': 'claude', 'role': 'spec-reviewer', 'settings': {}}))
        self.register('ticket-1/review', 'ticket-1', 'native-1', 'pane-2', code=2)
        self.execution.write_text(json.dumps({'harness': 'claude', 'role': 'implementer',
                                             'settings': {'model': 'sonnet', 'effort': 'high'}}))
        self.register('ticket-1/2')
        self.assertFalse(self.cli('status')['attempts'][1]['verified'])

    def test_design_hold_requires_ruling_and_updated_criteria_before_resume(self):
        self.register()
        self.ready()
        brief = self.root / 'decision-brief.md'
        self.record('hold', reason='Public API conflicts with accepted ADR', brief=str(brief),
                    evidence=['diff.kt:42'])
        self.cli('gate', '--attempt', 'ticket-1/1', '--stage', 'work', code=1)
        self.record('ruling', code=2, authority='user', decision='Accept revised API', evidence=['user message'])
        self.record('ruling', code=2, authority='user', decision='Accept revised API', criteria='ticket@revision-2',
                    evidence=['user message'])
        brief.write_text('Current ADR; conflicting API; alternatives; recommendation; reserved user decision\n')
        self.record('ruling', authority='user', decision='Accept revised API', criteria='ticket updated@revision-2',
                    evidence=['user message', 'canonical ticket revision-2'])
        self.assertTrue(self.cli('gate', '--attempt', 'ticket-1/1', '--stage', 'work')['complete'])
        self.collect()

    def test_report_must_survive_retirement_and_gate_checks_closed_worker(self):
        self.register()
        self.ready()
        report = self.collect()
        self.acknowledge()
        report.unlink()
        self.cli('gate', '--attempt', 'ticket-1/1', '--stage', 'accept', '--revision', 'head-1', code=1)
        self.record('closed', code=2, evidence=['native pane closure confirmed'])
        report.write_text('Different report content\n')
        self.cli('gate', '--attempt', 'ticket-1/1', '--stage', 'accept', '--revision', 'head-1', code=1)
        self.record('closed', code=2, evidence=['native pane closure confirmed'])
        report.write_text('Verified assignment report at head-1\n')
        self.record('closed', evidence=['native pane closure confirmed'], acceptance={'decision': 'deferred', 'reason': 'acceptance checks pending'})
        self.cli('gate', '--attempt', 'ticket-1/1', '--stage', 'work', code=1)

    def test_existing_user_worker_cannot_be_recorded_as_closed(self):
        self.register(owned=False)
        self.ready()
        self.collect()
        self.acknowledge()
        error = self.record('closed', code=2, evidence=['claimed pane closure'])
        self.assertIn('not a cleanup target', error)
        self.record('retain', reason='User-owned worker', next_use='Return control to owner', evidence=['ownership receipt'])

    def test_design_hold_survives_closing_a_blocked_worker(self):
        self.register()
        self.ready()
        brief = self.root / 'decision.md'
        brief.write_text('API alternatives and reserved user decision\n')
        self.record('hold', reason='User API ruling needed', brief=str(brief), evidence=['ADR:4'])
        report = self.root / 'blocked.md'
        report.write_text('Blocked on API ruling\n')
        self.record('result', status='blocked', head='head-1', report=str(report), evidence=['decision brief'])
        self.acknowledge()
        self.record('closed', evidence=['native closure confirmed'])
        self.assertEqual(self.cli('status')['holds'][0]['assignment'], 'ticket-1')
        self.record('ruling', authority='user', decision='Accept option B', criteria='ticket@revision-2',
                    evidence=['user message', 'canonical ticket revision-2'])
        self.assertEqual(self.cli('status')['holds'], [])

    def test_independent_waits_do_not_mask_first_completion(self):
        self.register()
        self.ready()
        self.register('ticket-2/1', 'ticket-2', 'native-2', 'pane-2')
        self.ready('ticket-2/1')
        command = self.root / 'slow-wait.json'
        release = self.root / 'release-slow-wait'
        command.write_text(json.dumps({'argv': [sys.executable, '-c',
            f'import time,pathlib\nwhile not pathlib.Path({str(release)!r}).exists(): time.sleep(.02)'], 'timeout': 10}))
        slow = subprocess.Popen([sys.executable, '-B', str(SCRIPT), 'watch', '--state', str(self.state),
                                 '--attempt', 'ticket-1/1', '--input', str(command)], stdout=subprocess.PIPE, text=True)
        try:
            self.watch('ticket-2/1')
            self.assertIsNone(slow.poll())
            receipts = self.cli('status')['pending']
            self.assertEqual([r['attempt'] for r in receipts], ['ticket-2/1'])
            release.write_text('first receipt collected\n')
            slow.communicate(timeout=6)
            self.assertEqual(slow.returncode, 0)
            self.assertEqual({r['attempt'] for r in self.cli('status')['pending']}, {'ticket-1/1', 'ticket-2/1'})
        finally:
            if slow.poll() is None:
                slow.terminate()
                slow.communicate(timeout=5)

    def test_timeout_retains_receipt_and_stops_owned_wait_process(self):
        self.register()
        self.ready()
        pidfile = self.root / 'wait.pid'
        receipt = self.watch(script=f'import os,time; open({str(pidfile)!r}, "w").write(str(os.getpid())); time.sleep(30)',
                             timeout=.15, code=124)
        self.assertEqual(receipt['reason'], 'timeout')
        with self.assertRaises(ProcessLookupError):
            os.kill(int(pidfile.read_text()), 0)
        self.assertEqual(self.cli('status')['pending'][0]['payload']['exit_code'], 124)

    def test_lost_monitor_requires_reconciliation_and_cancelled_wait_keeps_receipt(self):
        self.register()
        self.ready()
        marker = self.root / 'waiting'
        command = self.root / 'wait.json'
        command.write_text(json.dumps({'argv': [sys.executable, '-c',
                                                f'import time; open({str(marker)!r}, "w").write("ready"); time.sleep(30)'],
                                       'timeout': 40}))
        watcher = subprocess.Popen([sys.executable, '-B', str(SCRIPT), 'watch', '--state', str(self.state),
                                    '--attempt', 'ticket-1/1', '--input', str(command)], stdout=subprocess.PIPE, text=True)
        try:
            deadline = time.monotonic() + 5
            while not marker.exists() and time.monotonic() < deadline:
                time.sleep(.02)
            self.assertTrue(marker.exists())
            self.watch(code=2)
            self.record('reconciled', code=2, evidence=['wait still owned'])
            watcher.send_signal(signal.SIGTERM)
            watcher.communicate(timeout=5)
            self.assertEqual(watcher.returncode, 130)
            self.assertEqual(self.cli('status')['pending'][0]['payload']['reason'], 'interrupted')
            self.record('reconciled', evidence=['native worker still running; old wait stopped'])
            self.watch()
        finally:
            if watcher.poll() is None:
                watcher.kill()
                watcher.communicate()

    def test_abrupt_monitor_loss_blocks_rearm_until_owned_wait_is_stopped(self):
        self.register()
        self.ready()
        pidfile = self.root / 'wait.pid'
        command = self.root / 'wait.json'
        command.write_text(json.dumps({'argv': [sys.executable, '-c',
            f'import os,time; open({str(pidfile)!r}, "w").write(str(os.getpid())); time.sleep(30)'], 'timeout': 40}))
        watcher = subprocess.Popen([sys.executable, '-B', str(SCRIPT), 'watch', '--state', str(self.state),
                                    '--attempt', 'ticket-1/1', '--input', str(command)], stdout=subprocess.PIPE, text=True)
        wait_pid = None
        try:
            deadline = time.monotonic() + 5
            while not pidfile.exists() and time.monotonic() < deadline:
                time.sleep(.02)
            self.assertTrue(pidfile.exists())
            wait_pid = int(pidfile.read_text())
            watcher.kill()
            watcher.communicate(timeout=5)
            attempt = self.cli('status')['attempts'][0]
            self.assertEqual(attempt['monitor']['wait_pid'], wait_pid)
            self.assertIn('reconcile wait with native worker and report', attempt['attention'])
            self.watch(code=2)
            self.record('reconciled', code=2, evidence=['native running, local wait still alive'])
            os.killpg(wait_pid, signal.SIGKILL)
            deadline = time.monotonic() + 3
            while subprocess.run(['ps', '-p', str(wait_pid), '-o', 'stat='], capture_output=True,
                                 text=True).stdout.strip().strip('Z') and time.monotonic() < deadline:
                time.sleep(.02)
            self.record('reconciled', evidence=['native running, lost wait stopped'])
            self.watch()
        finally:
            if watcher.poll() is None:
                watcher.kill()
                watcher.communicate()
            if wait_pid is not None:
                try:
                    os.killpg(wait_pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass


if __name__ == '__main__':
    unittest.main()
