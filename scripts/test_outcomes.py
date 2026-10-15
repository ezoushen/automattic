#!/usr/bin/env python3
"""Exercise the machine-wide outcome ledger through the lifecycle and outcomes CLIs."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import decision_journal
import decisions


LIFECYCLE = Path(__file__).with_name('worker-lifecycle.py')
OUTCOMES = Path(__file__).with_name('outcomes.py')


class OutcomeLedger(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='automattic outcomes ')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.enterContext(patch.dict(os.environ, {'XDG_STATE_HOME': str(self.root / 'state')}))
        self.state = self.root / 'workers.sqlite'

    def run_script(self, script, *args, code=0):
        process = subprocess.run([sys.executable, '-B', str(script), *args], capture_output=True, text=True)
        self.assertEqual(process.returncode, code, process.stdout + process.stderr)
        return json.loads(process.stdout) if process.stdout else process.stderr

    def record(self, kind, attempt, **fields):
        path = self.root / 'event.json'
        path.write_text(json.dumps(dict(kind=kind, attempt=attempt, **fields)))
        return self.run_script(LIFECYCLE, 'record', '--state', str(self.state), '--input', str(path))

    def attempt(self, attempt, role='implementer', candidate='sonnet', status='completed', **closure):
        """Register, run and collect one attempt; close it with the given fields when any are given."""
        execution = self.root / f'{attempt.replace("/", "-")}.execution.json'
        execution.write_text(json.dumps({'harness': 'claude', 'role': role, 'candidate': candidate,
                                         'settings': {'model': candidate, 'effort': 'high'}}))
        number = len(list(self.root.glob('*.execution.json')))
        self.record('register', attempt, assignment=attempt.split('/')[0], repo=str(self.root),
                    worktree=str(self.root), head='head-1', execution=str(execution), runtime='claude',
                    worker=f'pane-{number}', native_session=f'native-{number}', owned=True)
        self.record('startup', attempt, observed={'runtime': 'claude', 'model': candidate, 'effort': 'high'},
                    evidence=['native.jsonl:1'])
        self.record('submitted', attempt, evidence=['native.jsonl:2'])
        report = self.root / f'{attempt.replace("/", "-")}.md'
        report.write_text(f'Report for {attempt}\n')
        self.record('result', attempt, status=status, head='head-1', report=str(report), evidence=['checks.log'])
        for receipt in self.run_script(LIFECYCLE, 'status', '--state', str(self.state))['pending']:
            self.run_script(LIFECYCLE, 'ack', '--state', str(self.state), '--event-id', str(receipt['id']))
        if closure:
            self.record('closed', attempt, evidence=['native session exited'], **closure)

    def summary(self, *args):
        return self.run_script(OUTCOMES, 'summary', *args)['roles']

    def test_lifecycle_outcomes_reach_the_ledger_and_count_acceptance_for_implementers(self):
        accepted = {'decision': 'accepted', 'commit': 'merge-1', 'evidence': ['git log merge-1']}
        self.attempt('t1/1', acceptance=accepted)
        self.attempt('t2/1', acceptance={'decision': 'declined', 'reason': 'criteria unmet'})
        self.attempt('t3/1', acceptance={'decision': 'deferred', 'reason': 'gate running'})
        self.attempt('t4/1', candidate='glm', status='failed', acceptance={'decision': 'deferred', 'reason': 'n/a'})
        self.attempt('t5/1', acceptance=accepted)
        self.run_script(LIFECYCLE, 'attribute', '--state', str(self.state), '--attempt', 't5/1', '--kind', 'revert',
                        '--count', '1', '--evidence', 'revert commit r-1')
        self.attempt('r1/1', role='spec-reviewer', candidate='opus')
        self.attempt('r2/1', role='spec-reviewer', candidate='opus', status='blocked')
        self.assertEqual(self.summary(), {
            'implementer': {'sonnet': {'successes': 1, 'failures': 2, 'pending': 1},
                            'glm': {'successes': 0, 'failures': 1, 'pending': 0}},
            'spec-reviewer': {'opus': {'successes': 1, 'failures': 1, 'pending': 0}}})
        # A later acceptance settles the deferred attempt.
        self.record('accepted', 't3/1', commit='merge-3', evidence=['git log merge-3'])
        self.assertEqual(self.summary('--role', 'implementer')['implementer']['sonnet'],
                         {'successes': 2, 'failures': 2, 'pending': 0})

    def test_past_decision_journals_import_once(self):
        journal = self.root / 'decisions.jsonl'
        options = {f'option_{index}': json.dumps({'candidate': name, 'model': name, 'runtime': 'claude'})
                   for index, name in enumerate(('sonnet', 'haiku'))}

        def transport(backend, payload):
            qid, question = next(iter(payload['questions'].items()))
            return {'model': backend['model'], 'answers': {qid: {
                'type': 'choice', 'choice': 'option_0',
                'probabilities': {key: float(key == 'option_0') for key in question['criteria']}}}}
        policy = {'enabled': ['worker-selection'], 'backend': {
            'protocol': 'systemone', 'endpoint': 'http://localhost:1241/v1/systemone', 'model': 'test-model'}}
        for assignment, role, chosen, status, metrics in (
                ('t1/1', 'implementer', None, 'succeeded', {}),
                ('t2/1', 'implementer', 'option_1', 'failed', {}),
                ('t3/1', 'implementer', None, 'succeeded', {'reverts': 1}),
                ('t4/1', 'e2e-runner', None, None, {}),
                # The lifecycle writes its own attempts to the ledger; their journal copies are not imported.
                ('t5/1', 'implementer', 'lifecycle', 'succeeded', {})):
            trace = decision_journal.trace_config(journal, self.root, assignment)
            result = decisions.decide(policy, {'family': 'worker-selection', 'state': f'Role: {role}\n',
                                               'instruction': 'Choose a worker.', 'options': options},
                                      trace=trace, transport=transport)
            did = result['decision_id']
            lifecycle = chosen == 'lifecycle'
            chosen = None if lifecycle else chosen
            decision_journal.record(journal, {'event': 'action', 'decision_id': did,
                                              'actor': 'worker-lifecycle' if lifecycle else 'host',
                                              'disposition': 'overridden' if chosen else 'accepted',
                                              'choice': chosen or 'option_0', 'reason': 'host choice'})
            if status:
                decision_journal.record(journal, {'event': 'outcome', 'decision_id': did, 'status': status,
                                                  'evidence': ['report.md'], 'metrics': metrics})
        self.assertEqual(self.run_script(OUTCOMES, 'import', str(journal)), {'imported': 4, 'already': 0})
        self.assertEqual(self.run_script(OUTCOMES, 'import', str(journal)), {'imported': 0, 'already': 4})
        self.assertEqual(self.summary(), {
            'implementer': {'sonnet': {'successes': 1, 'failures': 1, 'pending': 0},
                            'haiku': {'successes': 0, 'failures': 1, 'pending': 0}},
            'e2e-runner': {'sonnet': {'successes': 0, 'failures': 0, 'pending': 1}}})


    def test_lifecycle_states_import_once_and_a_damaged_source_does_not_stop_the_rest(self):
        self.attempt('t1/1', acceptance={'decision': 'accepted', 'commit': 'm', 'evidence': ['git log m']})
        self.attempt('t2/1', candidate='glm', status='failed', acceptance={'decision': 'deferred', 'reason': 'n/a'})
        damaged = self.root / 'damaged-decisions.jsonl'
        damaged.write_text('{"event": "decision"\n')
        os.environ['XDG_STATE_HOME'] = str(self.root / 'other-state')
        result = self.run_script(OUTCOMES, 'import', str(damaged), str(self.state), code=1)
        self.assertEqual((result['imported'], result['already']), (2, 0))
        self.assertEqual(list(result['errors']), [str(damaged)])
        self.assertEqual(self.summary(), {'implementer': {
            'sonnet': {'successes': 1, 'failures': 0, 'pending': 0},
            'glm': {'successes': 0, 'failures': 1, 'pending': 0}}})
        self.assertEqual(self.run_script(OUTCOMES, 'import', str(self.state)), {'imported': 0, 'already': 2})


if __name__ == '__main__':
    unittest.main()
