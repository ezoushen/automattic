#!/usr/bin/env python3
"""Routing decisions, sparse worker-runtime profiles and selection boundaries."""

import importlib.util
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch


spec = importlib.util.spec_from_file_location('models', Path(__file__).with_name('agent-models.py'))
models = importlib.util.module_from_spec(spec)
spec.loader.exec_module(models)


class Router(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='automattic router ')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.user = self.root / 'user.json'
        self.project = self.root / '.automattic/executors.json'
        self.project.parent.mkdir()
        env = patch.dict(os.environ, {'HERDR_ENV': '1', 'AUTOMATTIC_PROFILE': '',
                                     'AUTOMATTIC_SESSION': '', 'XDG_STATE_HOME': str(self.root / 'state'),
                                     'CODEX_HOME': str(self.root / 'codex-home')})
        env.start()
        self.addCleanup(env.stop)
        self.data = {
            'models': {},
            'runtimes': {runtime: {'executors': {
                runtime: {'type': 'subagent'},
                'herdr': {'type': 'skill', 'config': {'skill': 'herdr', 'instruction': 'Run one worker.'}}
            }} for runtime in ('codex', 'claude')},
            'agents': {'implementer': {'candidates': ['luna', 'sol', 'opus']}},
        }
        for name, runtime, default, allowed in (
            ('luna', 'codex', 'xhigh', ['xhigh', 'max']),
            ('sol', 'codex', 'medium', ['medium', 'high']),
            ('opus', 'claude', 'medium', ['medium', 'high']),
        ):
            self.data['models'][name] = {'description': name, 'runtimes': {runtime: {
                'id': runtime + '/' + name, 'thinking': {'default': default, 'allowed': allowed}}}}
        self.save()

    def save(self):
        self.user.write_text(json.dumps(self.data))

    def resolve(self, host='claude', **kwargs):
        if 'eligible_candidates' in kwargs and 'excluded_candidates' not in kwargs:
            # Tests narrow pools for setup; production callers must state their own reasons.
            configured = self.data['agents']['implementer'].get('candidates', [])
            kwargs['excluded_candidates'] = {name: 'Not under test.' for name in configured
                                             if name not in (kwargs['eligible_candidates'] or configured)}
        return models.resolve_execution(self.root, self.root / 'absent.json', self.user,
                                        host, 'implementer', kwargs.pop('task', {}), **kwargs)

    def profile(self, value):
        self.data['profiles'] = {'balanced': {'implementer': value}}
        self.data['router'] = {'type': 'profile', 'profile': 'balanced'}
        self.save()

    def choose(self, name, **values):
        return dict(candidate=name, reason='Assignment fits.', **values)

    def decision_router(self, reply=None):
        self.requests = []
        requests = self.requests

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                payload = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                requests.append(payload)
                criteria = payload['questions']['worker']['criteria']
                answer = {'type': 'choice', 'choice': next(iter(criteria)),
                          'probabilities': {key: float(i == 0) for i, key in enumerate(criteria)},
                          'confidence': 1.0}
                result = {'model': payload['model'], 'answers': {'worker': answer}}
                if reply:
                    reply(result)
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps(result).encode())

            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        self.data['router'] = {'type': 'decision-model', 'protocol': 'systemone',
                               'endpoint': f'http://127.0.0.1:{server.server_port}/v1/systemone',
                               'model': 'local/OpenJev-27B-Splash', 'timeout_seconds': 1}
        self.save()

    def test_decision_model_selects_only_preflighted_model_effort_pairs(self):
        self.decision_router()
        result = self.resolve(assignment='Implement the agreed bounded fix.',
                              eligible_candidates=['sol', 'opus'], target_runtime='codex')
        self.assertEqual(result['candidate'], 'sol')
        self.assertEqual(result['settings'], {'model': 'codex/sol', 'effort': 'medium'})
        self.assertEqual(result['selection_source'], 'decision-model')
        self.assertEqual(result['executor_context'], 'herdr')
        self.assertEqual(len(self.requests), 2)  # one decision, scored in both option orders
        options = result['decision_model']['options']
        self.assertEqual(list(options.values()), [
            {'candidate': 'sol', 'thinking': 'medium'}, {'candidate': 'sol', 'thinking': 'high'}])
        self.assertIn('codex/sol', str(self.requests[0]))
        self.assertNotIn('Run one worker.', str(self.requests[0]))
        self.assertNotIn(str(self.root), str(self.requests[0]))

    def test_host_narrowed_pool_needs_a_reason_for_each_excluded_candidate(self):
        self.decision_router()
        with self.assertRaisesRegex(ValueError, 'reason.*luna'):
            self.resolve(assignment='Implement the agreed bounded fix.', eligible_candidates=['sol', 'opus'],
                         excluded_candidates=None)
        with self.assertRaisesRegex(ValueError, 'reason'):
            self.resolve(assignment='Implement the agreed bounded fix.', eligible_candidates=['sol', 'opus'],
                         excluded_candidates={'luna': ' '})
        with self.assertRaisesRegex(ValueError, 'nova.*configured: luna, opus, sol'):
            self.resolve(assignment='Implement the agreed bounded fix.', eligible_candidates=['sol', 'opus'],
                         excluded_candidates={'luna': 'Quota exhausted.', 'nova': 'Not configured.'})
        self.assertEqual(self.requests, [])
        result = self.resolve(assignment='Implement the agreed bounded fix.', eligible_candidates=['sol', 'opus'],
                              excluded_candidates={'luna': 'Codex xhigh quota exhausted today.'})
        self.assertEqual(result['selection_source'], 'decision-model')
        # The configured pool and each exclusion reason travel with the decision request.
        self.assertIn('luna: Codex xhigh quota exhausted today.', self.requests[0]['state'])
        # Preflight removing every thinking level is its own reason.
        self.resolve(assignment='Implement the agreed bounded fix.', eligible_thinking={'luna': []})
        self.assertIn('luna: no eligible thinking level after runtime preflight', self.requests[-1]['state'])

    def test_worker_selection_sees_earlier_outcomes_for_the_role(self):
        self.decision_router()
        journal = self.root / 'decisions.jsonl'
        record = models.decisions.decision_journal.record
        first = self.resolve(assignment='Implement ticket 1.', journal=journal, assignment_id='t1/attempt-1')
        did = first['decision_model']['decision_id']
        record(journal, {'event': 'action', 'decision_id': did, 'actor': 'host', 'disposition': 'accepted',
                         'choice': first['decision_model']['choice'], 'reason': 'Fits.'})
        record(journal, {'event': 'execution', 'decision_id': did,
                         'requested': {'runtime': 'codex', 'model': 'codex/luna', 'effort': 'xhigh'},
                         'observed': {'runtime': 'codex', 'model': 'codex/luna', 'effort': 'xhigh'},
                         'evidence': ['rollout'], 'revision': 'abc'})
        record(journal, {'event': 'outcome', 'decision_id': did, 'status': 'failed',
                         'evidence': ['reports/1.md'], 'revision': 'abc'})
        self.resolve(assignment='Implement ticket 2.', journal=journal, assignment_id='t2/attempt-1')
        third = self.resolve(assignment='Implement ticket 3.', journal=journal, assignment_id='t3/attempt-1')
        state = self.requests[-1]['state']
        self.assertIn('Earlier implementer outcomes in this journal', state)
        self.assertIn('codex/luna xhigh: 1 failed', state)
        warnings = [w['code'] for w in third['decision_warnings']]
        self.assertIn('missing_outcomes', warnings)

    def test_worker_selection_sees_quality_signals_attributed_to_earlier_work(self):
        self.decision_router()
        journal = self.root / 'decisions.jsonl'
        record = models.decisions.decision_journal.record
        first = self.resolve(assignment='Implement ticket 1.', journal=journal, assignment_id='t1/attempt-1')
        did = first['decision_model']['decision_id']
        record(journal, {'event': 'action', 'decision_id': did, 'actor': 'worker-lifecycle', 'disposition': 'accepted',
                         'choice': first['decision_model']['choice'], 'reason': 'Registered.'})
        record(journal, {'event': 'execution', 'decision_id': did,
                         'requested': {'runtime': 'codex', 'model': 'codex/luna', 'effort': 'xhigh'},
                         'observed': {'runtime': 'codex', 'model': 'codex/luna', 'effort': 'xhigh'},
                         'evidence': ['rollout'], 'revision': 'abc'})
        for metrics in ({'worker_seconds': 30}, {'worker_seconds': 30, 'review_defects': 2, 'repair_rounds': 1}):
            record(journal, {'event': 'outcome', 'decision_id': did, 'status': 'succeeded', 'metrics': metrics,
                             'evidence': ['reports/1.md'], 'revision': 'abc'})
        self.resolve(assignment='Implement ticket 2.', journal=journal, assignment_id='t2/attempt-1')
        self.assertIn('- codex/luna xhigh: 1 succeeded; review defects: 2, repair rounds: 1\n',
                      self.requests[-1]['state'])

    def test_resume_reuses_its_decision_after_other_assignments_record_outcomes(self):
        self.decision_router()
        journal = self.root / 'decisions.jsonl'
        record = models.decisions.decision_journal.record
        first = self.resolve(assignment='Implement ticket 1.', journal=journal, assignment_id='a/1')
        other = self.resolve(assignment='Implement ticket 2.', journal=journal, assignment_id='b/1')
        did = other['decision_model']['decision_id']
        record(journal, {'event': 'action', 'decision_id': did, 'actor': 'host', 'disposition': 'accepted',
                         'choice': other['decision_model']['choice'], 'reason': 'Fits.'})
        record(journal, {'event': 'execution', 'decision_id': did,
                         'requested': {'runtime': 'codex', 'model': 'codex/luna', 'effort': 'xhigh'},
                         'observed': {'runtime': 'codex', 'model': 'codex/luna', 'effort': 'xhigh'},
                         'evidence': ['rollout'], 'revision': 'abc'})
        record(journal, {'event': 'outcome', 'decision_id': did, 'status': 'succeeded',
                         'evidence': ['reports/2.md'], 'revision': 'abc'})
        resumed = self.resolve(assignment='Implement ticket 1.', journal=journal, assignment_id='a/1')
        self.assertTrue(resumed['decision_model']['reused'])
        self.assertEqual(resumed['decision_model']['decision_id'], first['decision_model']['decision_id'])

    def test_resume_after_failure_reuses_its_decision(self):
        self.decision_router()
        journal = self.root / 'decisions.jsonl'
        record = models.decisions.decision_journal.record
        first = self.resolve(assignment='Implement ticket 1.', journal=journal, assignment_id='t1/attempt-1')
        did = first['decision_model']['decision_id']
        record(journal, {'event': 'action', 'decision_id': did, 'actor': 'host', 'disposition': 'accepted',
                         'choice': first['decision_model']['choice'], 'reason': 'Fits.'})
        record(journal, {'event': 'execution', 'decision_id': did,
                         'requested': {'runtime': 'codex', 'model': 'codex/luna', 'effort': 'xhigh'},
                         'observed': {'runtime': 'codex', 'model': 'codex/luna', 'effort': 'xhigh'},
                         'evidence': ['rollout'], 'revision': 'abc'})
        record(journal, {'event': 'outcome', 'decision_id': did, 'status': 'failed',
                         'evidence': ['reports/1.md'], 'revision': 'abc'})
        retry = dict(assignment='Implement ticket 1.', journal=journal, assignment_id='t1/attempt-2',
                     after_failure='Attempt 1 failed review.')
        second = self.resolve(**retry)
        resumed = self.resolve(**retry)
        self.assertTrue(resumed['decision_model']['reused'])
        self.assertEqual(resumed['decision_model']['decision_id'], second['decision_model']['decision_id'])

    def test_worker_decision_is_recorded_once_with_semantic_option_mapping(self):
        self.decision_router()
        journal = self.root / 'decisions.jsonl'
        result = self.resolve(assignment='Implement the agreed bounded fix.',
                              eligible_candidates=['sol'], target_runtime='codex',
                              journal=journal, assignment_id='ticket-2/attempt-1')
        recorded = models.decisions.decision_journal.inspect(
            journal, result['decision_model']['decision_id'])['decision']
        self.assertEqual(len(self.requests), 2)  # one decision, scored in both option orders
        self.assertEqual(recorded['payload'], self.requests[0])
        option = json.loads(recorded['request']['options'][recorded['result']['choice']])
        self.assertEqual(option['candidate'], result['candidate'])
        self.assertEqual(option['thinking'], result['settings']['effort'])
        self.assertEqual(recorded['assignment'], 'ticket-2/attempt-1')
        resumed = self.resolve(assignment='Implement the agreed bounded fix.',
                               eligible_candidates=['sol'], target_runtime='codex',
                               journal=journal, assignment_id='ticket-2/attempt-1')
        self.assertEqual(resumed['decision_model']['decision_id'], result['decision_model']['decision_id'])
        self.assertTrue(resumed['decision_model']['reused'])
        self.assertEqual(len(self.requests), 2)  # one decision, scored in both option orders
        trace = models.decisions.decision_journal.trace_config(journal, self.root, 'ticket-2/attempt-1')
        check = models.decisions.decision_journal.check_checkpoint(journal, trace, 'worker-selection', 'launch')
        self.assertEqual(check['checkpoint_id'], result['decision_model']['checkpoint_id'])
        self.assertEqual(check['missing_evidence'], ['action'])

    def test_single_permitted_option_is_settled_without_consultation(self):
        self.decision_router()
        journal = self.root / 'decisions.jsonl'
        result = self.resolve(assignment='Implement the agreed bounded fix.',
                              eligible_candidates=['sol'], eligible_thinking={'sol': ['high']},
                              target_runtime='codex', journal=journal, assignment_id='ticket-3/attempt-1')
        self.assertEqual(self.requests, [])
        self.assertEqual(result['candidate'], 'sol')
        self.assertEqual(result['settings'], {'model': 'codex/sol', 'effort': 'high'})
        self.assertEqual(result['selection_source'], 'sole-option')
        self.assertEqual(result['decision_model']['checkpoint_status'], 'skipped')
        self.assertNotIn('decision_id', result['decision_model'])
        self.assertEqual(result['decision_model']['proposer'], 'resolver')
        trace = models.decisions.decision_journal.trace_config(journal, self.root, 'ticket-3/attempt-1')
        check = models.decisions.decision_journal.check_checkpoint(
            journal, trace, 'worker-selection', 'completion')
        self.assertEqual(check['checkpoint_id'], result['decision_model']['checkpoint_id'])
        self.assertEqual(check['missing_evidence'], [])
        resumed = self.resolve(assignment='Implement the agreed bounded fix.',
                               eligible_candidates=['sol'], eligible_thinking={'sol': ['high']},
                               target_runtime='codex', journal=journal, assignment_id='ticket-3/attempt-1')
        self.assertTrue(resumed['decision_model']['reused'])
        self.assertEqual(resumed['decision_model']['checkpoint_id'], result['decision_model']['checkpoint_id'])
        self.assertEqual(self.requests, [])

    def test_decision_journal_cli_records_inspects_and_replays_without_changing_inputs(self):
        self.decision_router()
        directory = Path(__file__).parent
        journal = self.root / 'decisions.jsonl'
        request = self.root / 'request.json'
        request.write_text(json.dumps({'family': 'worker-selection', 'state': 'Bounded edit.',
                                       'instruction': 'Choose the adequate worker.',
                                       'options': {'small': 'Bounded changes.', 'large': 'Complex changes.'}}))
        def cli(script, *args):
            return subprocess.run([sys.executable, '-B', str(directory / script), *map(str, args)],
                                  capture_output=True, text=True)
        result = cli('decisions.py', 'decide', '--repo', self.root, '--user-executors', self.user,
                     '--request', request, '--journal', journal, '--assignment-id', 'edit/1')
        self.assertEqual(result.returncode, 0, result.stderr)
        did = json.loads(result.stdout)['decision_id']
        event = self.root / 'action.json'
        event.write_text(json.dumps({'event': 'action', 'decision_id': did, 'actor': 'host',
                                     'disposition': 'accepted', 'choice': 'small', 'reason': 'Bounded change.'}))
        result = cli('decision_journal.py', 'record', '--journal', journal, '--event', event)
        self.assertEqual(result.returncode, 0, result.stderr)
        result = cli('decision_journal.py', 'inspect', '--journal', journal)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['decisions'][0]['host_choice'], 'small')
        self.assertEqual(len(self.requests), 2)  # one decision, scored in both option orders
        inputs = {p: p.read_bytes() for p in (journal, self.user, request)}
        cases = self.root / 'cases.json'
        cases.write_text(json.dumps([{'decision_id': did, 'expected': ['small'],
                                     'evidence': 'Reviewer verified scope.', 'instruction': 'Pick the lightest adequate worker.'}]))
        output = self.root / 'replay.json'
        args = ('replay', '--journal', journal, '--repo', self.root, '--user-executors', self.user,
                '--cases', cases, '--output', output)
        result = cli('decision_journal.py', *args)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(self.requests), 5)  # replays send each recorded variant once
        report = json.loads(output.read_text())
        self.assertEqual(report['variants']['original']['accuracy'], 1)
        self.assertEqual(report['variants']['reversed']['accuracy'], 0)
        self.assertEqual(report['results'][0]['payload'], self.requests[0])
        self.assertEqual(inputs, {p: p.read_bytes() for p in inputs})
        result = cli('decision_journal.py', *args)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(self.requests), 5)

    def test_shared_decisions_config_preserves_routing_and_disabled_family_is_offline(self):
        self.decision_router()
        self.data['decisions'] = {'backend': {key: value for key, value in self.data['router'].items()
                                            if key != 'type'},
                                  'enabled': ['worker-selection', 'recovery']}
        self.data['router'] = {'type': 'decision-model'}
        self.save()
        self.assertEqual(self.resolve(assignment='Fix the constant.')['candidate'], 'luna')
        self.assertEqual(len(self.requests), 2)  # one decision, scored in both option orders
        self.data['decisions']['enabled'] = ['recovery']
        self.save()
        result = self.resolve(assignment='Fix the constant.')
        self.assertEqual(result['status'], 'selection_required')
        self.assertEqual(result['selection_router'], models.DEFAULT_ROUTER)
        self.assertEqual(len(self.requests), 2)  # one decision, scored in both option orders

    def test_decision_config_rejects_bad_calibration_and_unknown_family(self):
        backend = {'protocol': 'systemone', 'endpoint': 'http://localhost:1241/v1/systemone', 'model': 'test'}
        for extra in ({'enabled': ['unknown']}, {'enabled': ['recovery', 'recovery']},
                      {'calibration': {'suite': 'relative.json', 'baseline': '/tmp/base.json'}},
                      {'calibration': {'suite': '/tmp/cases.json', 'baseline': '/tmp/base.json', 'check_every': 0}},
                      {'calibration': {'suite': '/tmp/cases.json', 'baseline': '/tmp/cases.json'}},
                      {'calibration': {'suite': '/tmp/cases.json', 'baseline': '/tmp/base.json', 'max_accuracy_drop': 2}}):
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                models.validate_execution_config({'decisions': {'backend': backend, 'enabled': ['recovery'], **extra}}, 'test')
    def test_decision_model_can_select_higher_permitted_effort(self):
        def reply(result):
            answer = result['answers']['worker']
            keys = list(answer['probabilities'])
            answer.update(choice='option_1', probabilities={key: float(key == 'option_1') for key in keys})
        self.decision_router(reply)
        result = self.resolve(assignment='Diagnose a subtle contract failure.', eligible_candidates=['sol'])
        self.assertEqual(result['settings']['effort'], 'high')

    def test_native_profile_availability_filters_effort_before_routing(self):
        self.decision_router()
        result = self.resolve(assignment='Complete the accepted fix; preserve remaining allowance.',
                              eligible_candidates=['opus'], eligible_thinking={'opus': ['medium']})
        self.assertEqual(result['settings']['effort'], 'medium')
        self.assertEqual(list(result['decision_model']['options'].values()),
                         [{'candidate': 'opus', 'thinking': 'medium'}])
        self.assertEqual(result['eligible_thinking'], {'opus': ['medium']})

    def test_profile_discovery_failure_recovers_with_verified_session_effort_not_null(self):
        self.decision_router()
        with self.assertRaisesRegex(ValueError, 'exceeds configured thinking'):
            self.resolve(assignment='Concurrency repair.', eligible_candidates=['opus'],
                         eligible_thinking={'opus': [None]})
        self.assertEqual(self.requests, [])
        result = self.resolve(assignment='Concurrency repair; native session effort verified medium.',
                              eligible_candidates=['opus'], eligible_thinking={'opus': ['medium']})
        self.assertEqual(result['settings'], {'model': 'claude/opus', 'effort': 'medium'})
        self.assertEqual(self.requests, [])
        self.assertEqual(list(result['decision_model']['options'].values()),
                         [{'candidate': 'opus', 'thinking': 'medium'}])

    def test_preflight_blocks_unavailable_pins_profiles_and_host_recommendations(self):
        self.profile({'claude': {'candidate': 'opus', 'thinking': 'high'}})
        for override in ({}, {'candidate': 'opus', 'task': {'effort': 'high'}},
                         {'selection': self.choose('opus', thinking='high')}):
            with self.subTest(override=override), self.assertRaisesRegex(ValueError, 'runtime preflight'):
                self.resolve(target_runtime='claude', eligible_thinking={'opus': ['medium']}, **override)
        result = self.resolve(target_runtime='claude', eligible_thinking={'opus': ['medium']},
                              candidate='opus', task={'effort': 'medium'})
        self.assertEqual(result['settings']['effort'], 'medium')

    def test_preflight_exhaustion_and_invalid_levels_do_not_call_router(self):
        self.decision_router()
        for levels in ({'opus': []}, {'opus': ['ultra']}, {'unknown': ['medium']},
                       {'opus': ['medium', 'medium']}, {'opus': [{}]}):
            with self.subTest(levels=levels), self.assertRaises(ValueError):
                self.resolve(assignment='Fix the constant.', eligible_candidates=['opus'], eligible_thinking=levels)
        blocked = self.resolve(assignment='Fix the constant.', eligible_candidates=['opus'],
                               eligible_thinking={'opus': ['medium']}, task={'effort': 'high'})
        self.assertEqual(blocked['status'], 'selection_required')
        self.assertNotIn('settings', blocked)
        self.assertEqual(self.requests, [])

    def test_preflight_cli_rejects_unavailable_profile_without_rendering(self):
        self.profile({'claude': {'candidate': 'opus', 'thinking': 'high'}})
        result = subprocess.run([sys.executable, str(Path(models.__file__)), '--route', '--profile',
                                 '--repo', str(self.root), '--user-executors', str(self.user),
                                 '--harness', 'claude', '--role', 'implementer', '--target-runtime', 'claude',
                                 '--eligible-thinking', '{"opus":["medium"]}'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn('runtime preflight', result.stderr)
        self.assertEqual(result.stdout, '')


    def test_decision_model_preserves_explicit_pins_and_inspection_is_offline(self):
        self.decision_router()
        for kwargs in ({'list_candidates': True}, {}, {'candidate': 'sol'},
                       {'selection': self.choose('sol')},
                       {'choice': {'executor': {'type': 'subagent'}}}):
            with self.subTest(kwargs=kwargs):
                self.resolve(**kwargs, **({} if not kwargs or kwargs.get('list_candidates')
                                         else {'assignment': 'Some task.'}))
        self.assertEqual(self.requests, [])
        self.data['agents']['implementer'] = {'model': 'sol'}
        self.save()
        self.resolve(assignment='Some task.')
        self.assertEqual(self.requests, [])

    def test_decision_model_effort_pin_filters_before_query(self):
        self.decision_router()
        result = self.resolve(assignment='Follow the explicit effort setting.', task={'effort': 'high'})
        self.assertEqual(result['settings']['effort'], 'high')
        self.assertEqual({value['candidate'] for value in result['decision_model']['options'].values()},
                         {'sol', 'opus'})
        self.assertEqual({value['thinking'] for value in result['decision_model']['options'].values()}, {'high'})
        blocked = self.resolve(assignment='No matching effort.', task={'effort': 'ultra'})
        self.assertEqual(blocked['status'], 'selection_required')
        self.assertIn('No permitted', blocked['selection_error'])
        self.assertNotIn('settings', blocked)
        self.assertEqual(len(self.requests), 2)  # one decision, scored in both option orders

    def test_decision_model_does_not_invent_effort_for_inherited_or_fixed_models(self):
        self.decision_router()
        self.data['agents']['implementer'] = {'candidates': {
            'inherit': {'executor': {'type': 'subagent'}},
            'haiku': {'executor': {'type': 'subagent'}, 'models': {'mode': 'override', 'model': 'haiku'}},
            'fixed': {'executor': {'type': 'subagent'}, 'models': {
                'mode': 'override', 'model': 'fixed', 'thinking': 'medium', 'allow_thinking_override': True}}
        }}
        self.save()
        result = self.resolve(assignment='Complete a small edit.')
        self.assertEqual(result['decision_model']['options'], {
            'option_0': {'candidate': 'inherit'}, 'option_1': {'candidate': 'haiku'},
            'option_2': {'candidate': 'fixed', 'thinking': 'medium'}})

    def test_decision_model_abstention_and_invalid_answers_fall_back_to_host(self):
        self.decision_router()
        cases = [
            {},
            {'type': 'choice', 'choice': 'outside', 'probabilities': {}},
            {'type': 'choice', 'choice': 'option_0', 'probabilities': {'option_0': float('nan')}},
        ]
        for answer in cases:
            with self.subTest(answer=answer), patch.object(models, 'systemone_request', return_value={
                    'model': self.data['router']['model'], 'answers': {'worker': answer}}):
                result = self.resolve(assignment='Route this assignment.', eligible_candidates=['sol'])
                self.assertEqual(result['status'], 'selection_required')
                self.assertEqual(result['selection_router'], models.DEFAULT_ROUTER)
                self.assertIn('selection_error', result)
                self.assertNotIn('settings', result)
        def abstain(result):
            answer = result['answers']['worker']
            answer.update(choice='abstain', probabilities={key: float(key == 'abstain')
                                                         for key in answer['probabilities']})
        self.decision_router(abstain)
        result = self.resolve(assignment='Task is underspecified.')
        self.assertEqual(result['status'], 'selection_required')
        self.assertEqual(result['selection_router'], models.DEFAULT_ROUTER)
        self.assertEqual(result['decision_model']['choice'], 'abstain')
        self.assertNotIn('settings', result)
        final = self.resolve(selection=self.choose('sol'), assignment='Task is underspecified.')
        self.assertEqual(final['candidate'], 'sol')
        self.assertEqual(len(self.requests), 2)  # one decision, scored in both option orders

    def fallback_router(self):
        def abstain(result):
            answer = result['answers']['worker']
            answer.update(choice='abstain', probabilities={key: float(key == 'abstain')
                                                         for key in answer['probabilities']})
        self.decision_router(abstain)
        self.data['profiles'] = {'balanced': {'implementer': {'codex': {'candidate': 'sol', 'thinking': 'high'}}}}
        self.data['router']['fallback_profile'] = 'balanced'
        self.save()

    def test_decision_failure_uses_the_configured_fallback_profile(self):
        self.fallback_router()
        result = self.resolve(assignment='Underspecified task.', target_runtime='codex')
        self.assertEqual(len(self.requests), 2)  # one decision, scored in both option orders
        self.assertEqual(result['candidate'], 'sol')
        self.assertEqual(result['settings'], {'model': 'codex/sol', 'effort': 'high'})
        self.assertEqual(result['selection_source'], 'fallback-profile')
        self.assertEqual(result['decision_model']['choice'], 'abstain')
        self.assertIn('selection_error', result)

    def test_rule_first_router_consults_only_after_a_failure_or_without_a_rule(self):
        self.decision_router()
        self.data['profiles'] = {'balanced': {'implementer': {'codex': {'candidate': 'sol', 'thinking': 'high'}}}}
        self.data['router'].update(fallback_profile='balanced', consult='after-failure')
        self.save()
        journal = self.root / 'decisions.jsonl'
        routine = self.resolve(assignment='Implement ticket 1.', target_runtime='codex',
                               journal=journal, assignment_id='t1/attempt-1')
        self.assertEqual((routine['candidate'], routine['settings']), ('sol', {'model': 'codex/sol', 'effort': 'high'}))
        self.assertEqual(routine['selection_source'], 'rule-profile')
        self.assertEqual(self.requests, [])
        self.assertFalse(journal.exists())
        retry = self.resolve(assignment='Implement ticket 1.', target_runtime='codex', journal=journal,
                             assignment_id='t1/attempt-2', after_failure='Attempt 1 failed review: F-01 reproduced.')
        self.assertEqual(retry['selection_source'], 'decision-model')
        self.assertIn('Earlier attempt failed: Attempt 1 failed review: F-01 reproduced.', self.requests[0]['state'])
        # Without a rule for this worker runtime, the router is consulted as before.
        self.requests.clear()
        unruled = self.resolve(assignment='Implement ticket 2.', target_runtime='claude')
        self.assertEqual(unruled['selection_source'], 'decision-model')
        self.assertEqual(len(self.requests), 2)  # one decision, scored in both option orders
        # A rule that cannot apply to this assignment leaves the choice to the router.
        pinned = self.resolve(assignment='Implement ticket 2.', target_runtime='codex', task={'model': 'codex/luna'})
        self.assertEqual((pinned['candidate'], pinned['selection_source']), ('luna', 'decision-model'))
        self.data['router'].pop('fallback_profile')
        self.save()
        with self.assertRaisesRegex(ValueError, 'fallback_profile'):
            self.resolve(assignment='Implement ticket 3.', target_runtime='codex')

    def test_partial_fallback_profile_still_returns_host_selection(self):
        self.fallback_router()
        self.data['profiles']['balanced']['implementer']['codex'] = {'thinking': 'high'}
        self.save()
        result = self.resolve(assignment='Underspecified task.', target_runtime='codex')
        self.assertEqual(result['status'], 'selection_required')
        self.assertEqual(result['selection_router'], models.DEFAULT_ROUTER)
        self.assertNotIn('settings', result)

    def test_fallback_profile_is_not_backend_configuration(self):
        self.fallback_router()
        self.resolve(assignment='Underspecified task.', target_runtime='codex')
        self.assertNotIn('fallback_profile', json.dumps(self.requests))
        policy = models.decisions.effective_policy([(None, {'router': self.data['router']})], self.data['router'])
        self.assertNotIn('fallback_profile', policy['backend'])

    def test_fallback_profile_warns_and_never_absorbs_journal_integrity_errors(self):
        self.fallback_router()
        result = self.resolve(assignment='Underspecified task.', target_runtime='codex')
        self.assertIn('decision_fallback', [item['code'] for item in result['decision_warnings']])
        journal = self.root / 'decisions.jsonl'
        self.resolve(assignment='First summary.', target_runtime='codex', journal=journal, assignment_id='t/1')
        changed = self.resolve(assignment='Changed summary.', target_runtime='codex',
                               journal=journal, assignment_id='t/1')
        self.assertEqual(changed['status'], 'selection_required')
        self.assertNotIn('settings', changed)

    def test_unknown_fallback_profile_is_a_configuration_error(self):
        self.fallback_router()
        self.data['router']['fallback_profile'] = 'missing'
        self.save()
        with self.assertRaisesRegex(ValueError, 'missing'):
            self.resolve(assignment='Underspecified task.', target_runtime='codex')
        self.assertEqual(self.requests, [])

    def test_decision_model_timeout_does_not_consume_worker_attempts_or_retry(self):
        self.decision_router()
        with patch.object(models, 'systemone_request', side_effect=TimeoutError('timed out')) as request:
            result = self.resolve(assignment='Implement the fix.')
        self.assertEqual(request.call_count, 1)
        self.assertEqual(result['status'], 'selection_required')
        self.assertEqual(result['selection_router'], models.DEFAULT_ROUTER)
        self.assertNotIn('settings', result)

    def test_decision_model_rejects_empty_pool_without_network(self):
        self.decision_router()
        for kwargs in ({'eligible_candidates': []}, {'candidate': 'sol', 'eligible_candidates': ['luna']}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                self.resolve(assignment='Implement the fix.', **kwargs)
        self.assertEqual(self.requests, [])

    def test_decision_router_schema_rejects_invalid_protocol_endpoint_and_timeout(self):
        self.decision_router()
        for change in ({'protocol': 'chat'}, {'endpoint': 'file:///tmp/a'},
                       {'timeout_seconds': 0}, {'timeout_seconds': 61}, {'model': ''}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                models.validate_execution_config({'router': dict(self.data['router'], **change)}, 'fixture')

    def test_decision_router_cli_uses_assignment_and_rejects_inspection_mix(self):
        self.decision_router()
        assignment = self.root / 'assignment.txt'
        assignment.write_text('Implement the exact supplied fix and run its regression test.')
        command = [sys.executable, '-B', str(models.ROOT / 'scripts/agent-models.py'),
                   '--repo', str(self.root), '--harness', 'codex', '--role', 'implementer',
                   '--route', '--user-executors', str(self.user), '--assignment', str(assignment),
                   '--eligible-candidates', '["sol"]']
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn('--excluded-candidates', result.stderr)
        command += ['--excluded-candidates', '{"luna": "Quota exhausted.", "opus": "Wrong runtime."}']
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['selection_source'], 'decision-model')
        result = subprocess.run(command + ['--list-candidates'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(len(self.requests), 2)  # one decision, scored in both option orders

    def test_decision_router_respects_runtime_availability_without_herdr(self):
        self.decision_router()
        with patch.dict(os.environ, {'HERDR_ENV': ''}):
            result = self.resolve(host='codex', assignment='Implement the supplied fix.')
        self.assertEqual({entry['candidate'] for entry in result['decision_model']['options'].values()},
                         {'luna', 'sol'})

    def test_decision_router_model_pin_and_explicit_profile_bypass(self):
        self.decision_router()
        result = self.resolve(assignment='Implement the fix.', task={'model': 'codex/sol'})
        self.assertEqual({entry['candidate'] for entry in result['decision_model']['options'].values()}, {'sol'})
        self.data['profiles'] = {'fixed': {'implementer': {'codex': {'candidate': 'sol'}}}}
        self.save()
        result = self.resolve(assignment='Some task.', config_profile='fixed', target_runtime='codex')
        self.assertEqual(result['selection_source'], 'profile')
        self.assertEqual(len(self.requests), 2)  # one decision, scored in both option orders

    def test_missing_selection_returns_options_without_launch_settings(self):
        result = self.resolve()
        self.assertEqual(result['status'], 'selection_required')
        self.assertEqual(result['router'], {'type': 'skill', 'skill': 'automattic:model-routing'})
        self.assertEqual(set(result['candidates']), {'luna', 'sol', 'opus'})
        self.assertNotIn('settings', result)
        self.assertNotIn('executor', result)
        self.assertNotIn('default', result['candidate_pool'])

    def test_custom_skill_is_inspectable_and_accepts_normalized_decision(self):
        self.data['router'] = {'type': 'skill', 'skill': 'my:jev-router', 'instruction': 'Prefer native work.'}
        self.save()
        before = self.user.read_bytes()
        self.assertEqual(self.resolve(list_candidates=True)['router'], self.data['router'])
        self.assertEqual(self.resolve()['status'], 'selection_required')
        result = self.resolve(selection=self.choose('sol', thinking='high'))
        self.assertEqual(result['settings'], {'model': 'codex/sol', 'effort': 'high'})
        self.assertEqual(self.user.read_bytes(), before)

    def test_profile_uses_worker_runtime_not_caller(self):
        self.profile({'codex': {'candidate': 'sol', 'thinking': 'high'},
                      'claude': {'candidate': 'opus'}})
        result = self.resolve(target_runtime='codex')
        self.assertEqual(result['candidate'], 'sol')
        self.assertEqual(result['target_runtime'], 'codex')
        self.assertEqual(result['executor_context'], 'herdr')
        self.assertEqual(result['settings']['effort'], 'high')
        self.assertEqual(result['selection_source'], 'profile')
        result = self.resolve(host='codex', target_runtime='claude')
        self.assertEqual(result['candidate'], 'opus')

    def test_runtime_can_come_from_selection_without_extra_router_call(self):
        self.profile({'codex': {'candidate': 'sol'}})
        result = self.resolve(selection=self.choose('luna'))
        self.assertEqual(result['candidate'], 'sol')
        self.assertEqual(result['target_runtime'], 'codex')
        self.assertEqual(result['settings']['effort'], 'medium')

    def test_sparse_profiles_preserve_unspecified_selection_fields(self):
        self.profile({'codex': {'thinking': 'high'}})
        result = self.resolve(selection=self.choose('sol'))
        self.assertEqual(result['candidate'], 'sol')
        self.assertEqual(result['settings']['effort'], 'high')
        self.assertEqual(self.resolve(target_runtime='codex')['status'], 'selection_required')
        self.profile({'codex': {'candidate': 'sol'}})
        self.assertEqual(self.resolve(selection=self.choose('sol', thinking='high'))['settings']['effort'], 'high')
        self.profile({'codex': {}})
        self.assertEqual(self.resolve(selection=self.choose('luna', thinking='max'))['settings']['effort'], 'max')
        result = self.resolve(selection=self.choose('opus', thinking='high'))
        self.assertEqual(result['settings'], {'model': 'claude/opus', 'effort': 'high'})

    def test_profile_does_not_guess_runtime_or_create_routes(self):
        self.profile({'codex': {'candidate': 'sol'}, 'claude': {'candidate': 'opus'}})
        self.assertEqual(self.resolve()['status'], 'selection_required')
        with patch.dict(os.environ, {'HERDR_ENV': ''}):
            with self.assertRaisesRegex(ValueError, 'eligible'):
                self.resolve(target_runtime='codex')
            self.assertEqual(self.resolve()['candidate'], 'opus')

    def test_explicit_user_pins_win_over_profile(self):
        self.profile({'codex': {'candidate': 'sol', 'thinking': 'high'}})
        result = self.resolve(candidate='luna', task={'effort': 'max'}, selection='invalid')
        self.assertEqual(result['settings'], {'model': 'codex/luna', 'effort': 'max'})
        self.assertEqual(result['selection_source'], 'user')
        self.assertEqual(self.resolve(candidate='luna')['settings']['effort'], 'xhigh')

    def test_invalid_selection_never_launches_hidden_default(self):
        for decision in ('invalid', self.choose('outside'), self.choose('sol', thinking='max')):
            with self.subTest(decision=decision):
                result = self.resolve(selection=decision)
                self.assertEqual(result['status'], 'selection_required')
                self.assertIn('selection_error', result)
                self.assertNotIn('settings', result)
        with self.assertRaisesRegex(ValueError, 'No suitable'):
            self.resolve(selection={'candidate': None, 'reason': 'No candidate meets task needs.'})

    def test_profile_availability_recovery_does_not_repeat_unavailable_model(self):
        self.profile({'codex': {'candidate': 'sol'}})
        result = self.resolve(target_runtime='codex', eligible_candidates=['luna'])
        self.assertEqual(result['status'], 'selection_required')
        self.assertEqual(result['fallback_from'], 'sol')
        result = self.resolve(target_runtime='codex', eligible_candidates=['luna'], selection=self.choose('luna'))
        self.assertEqual(result['candidate'], 'luna')
        self.assertEqual(result['fallback_from'], 'sol')
        self.data['agents']['implementer']['fallback'] = False
        self.save()
        with self.assertRaisesRegex(ValueError, 'fallback'):
            self.resolve(target_runtime='codex', eligible_candidates=['luna'], selection=self.choose('luna'))

    def test_pins_no_candidates_and_unknown_eligibility_block(self):
        with self.assertRaisesRegex(ValueError, 'not eligible'):
            self.resolve(candidate='sol', eligible_candidates=['luna'])
        with self.assertRaisesRegex(ValueError, 'eligible'):
            self.resolve(eligible_candidates=[])
        with self.assertRaises(ValueError):
            self.resolve(eligible_candidates=['outside'])
        with self.assertRaises(ValueError):
            self.resolve(candidate='sol', target_runtime='claude')

    def test_profile_reference_and_runtime_mismatch_are_errors(self):
        for value in ({'codex': {'candidate': 'opus'}}, {'codex': {'candidate': 'outside'}},
                      {'codex': {'candidate': 'sol', 'thinking': 'max'}}):
            with self.subTest(value=value):
                self.profile(value)
                with self.assertRaises(ValueError):
                    self.resolve(list_candidates=True)
        self.data['router']['profile'] = 'missing'
        self.save()
        with self.assertRaisesRegex(ValueError, 'Unknown.*profile'):
            self.resolve()

    def test_profile_thinking_must_fit_final_candidate(self):
        self.profile({'codex': {'thinking': 'high'}})
        result = self.resolve(selection=self.choose('luna'))
        self.assertEqual(result['status'], 'selection_required')
        self.assertIn('selection_error', result)
        self.assertNotIn('settings', result)

    def test_profile_selection_is_explicit_not_host_or_herdr_name(self):
        self.data['profiles'] = {'herdr': {'implementer': {'codex': {'candidate': 'sol'}}}}
        self.save()
        self.assertEqual(self.resolve()['router']['type'], 'skill')
        self.assertEqual(self.resolve(config_profile='herdr', target_runtime='codex')['candidate'], 'sol')
        with patch.dict(os.environ, {'AUTOMATTIC_PROFILE': 'herdr'}):
            self.assertEqual(self.resolve(target_runtime='codex')['candidate'], 'sol')

    def test_router_and_profile_layering_and_session_resume(self):
        self.profile({'codex': {'candidate': 'sol'}})
        self.project.write_text(json.dumps({'profiles': {'balanced': {'implementer': {
            'codex': {'candidate': 'luna'}}}}}))
        self.assertEqual(self.resolve(target_runtime='codex')['candidate'], 'luna')
        models.save_session(self.root, 'one', {'router': {'type': 'skill', 'skill': 'my:router'}})
        self.assertEqual(self.resolve(session_id='one')['router']['skill'], 'my:router')
        self.assertEqual(self.resolve(session_id='two', target_runtime='codex')['candidate'], 'luna')
        models.reset_session(self.root, 'one')
        self.assertEqual(self.resolve(session_id='one', target_runtime='codex')['candidate'], 'luna')

    def test_old_profiles_and_pool_defaults_have_migration_diagnostics(self):
        for config in ({'agents': {'implementer': {'default': 'sol', 'candidates': ['sol']}}},
                       {'profiles': {'codex': {'agents': {}}}}):
            with self.subTest(config=config), self.assertRaisesRegex(ValueError, 'migrat'):
                models.validate_execution_config(config, 'fixture')

    def test_schema_rejects_unknown_router_fields_and_profile_wrappers(self):
        for router in ({'type': 'fixed'}, {'type': 'skill'}, {'type': 'profile'},
                       {'type': 'skill', 'skill': 'route', 'profile': 'balanced'}):
            with self.subTest(router=router), self.assertRaises(ValueError):
                models.validate_execution_config({'router': router}, 'fixture')
        with self.assertRaises(ValueError):
            models.validate_execution_config({'profiles': {'balanced': {'choices': {}}}}, 'fixture')

    def test_malformed_config_sections_report_validation_errors(self):
        for key in ('profiles', 'agents'):
            for value in (None, [], 'invalid'):
                with self.subTest(key=key, value=value), self.assertRaisesRegex(ValueError, 'fixture'):
                    models.validate_execution_config({key: value}, 'fixture')

    def test_profile_preserves_target_when_candidate_has_multiple_bindings(self):
        self.data['models']['opus']['runtimes']['codex'] = {'id': 'codex/opus'}
        self.profile({'codex': {'candidate': 'opus'}})
        result = self.resolve(selection=self.choose('sol'))
        self.assertEqual(result['candidate'], 'opus')
        self.assertEqual(result['target_runtime'], 'codex')
        self.assertEqual(result['settings'], {'model': 'codex/opus'})

    def test_target_runtime_applies_to_fixed_catalog_references(self):
        self.data['models']['opus']['runtimes']['codex'] = {'id': 'codex/opus'}
        self.data['agents']['implementer'] = {'model': 'opus'}
        self.save()
        self.assertEqual(self.resolve(target_runtime='codex')['settings'], {'model': 'codex/opus'})

    def test_runtime_pin_requires_declared_catalog_bindings(self):
        native = {'executor': {'type': 'subagent'}}
        external = {'executor': {'type': 'skill', 'config': {
            'skill': 'custom:worker', 'instruction': 'Run the assignment.'}}}
        for entry in (None, native, {'candidates': {'native': native}},
                      {'candidates': {'external': external}}):
            with self.subTest(entry=entry):
                self.data['agents']['implementer'] = entry
                self.save()
                with self.assertRaisesRegex(ValueError, 'target runtime requires'):
                    self.resolve(target_runtime='codex')

    def test_invalid_structured_router_output_is_recoverable(self):
        for name in ([], {}, 123):
            with self.subTest(name=name):
                self.assertEqual(self.resolve(selection=self.choose(name))['status'], 'selection_required')

    def test_profile_recovery_releases_unavailable_candidates_thinking(self):
        self.profile({'codex': {'candidate': 'sol', 'thinking': 'high'}})
        result = self.resolve(target_runtime='codex', eligible_candidates=['luna'],
                              selection=self.choose('luna', thinking='max'))
        self.assertEqual(result['settings'], {'model': 'codex/luna', 'effort': 'max'})

    def test_pending_selection_cannot_render_native_launch_profile(self):
        import subprocess
        import sys
        result = subprocess.run([sys.executable, '-B', str(models.ROOT / 'scripts/agent-models.py'),
                                 '--repo', str(self.root), '--user-executors', str(self.user),
                                 '--harness', 'claude', '--role', 'implementer', '--route', '--profile'],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn('Select a candidate', result.stderr)

    def test_inspection_filter_survives_profile_runtime_selection(self):
        self.profile({'codex': {'candidate': 'sol'}})
        listing = self.resolve(list_candidates=True)
        result = self.resolve(eligible_candidates=list(listing['candidates']), selection=self.choose('sol'))
        self.assertEqual(result['candidate'], 'sol')
        self.assertEqual(result['target_runtime'], 'codex')

    def test_excluded_recommendation_does_not_pin_runtime_during_recovery(self):
        self.profile({'codex': {'candidate': 'sol'}})
        result = self.resolve(eligible_candidates=['opus'], selection=self.choose('sol'))
        self.assertEqual(result['status'], 'selection_required')
        self.assertEqual(result['eligible_candidates'], ['opus'])
        result = self.resolve(eligible_candidates=['opus'], selection=self.choose('opus'))
        self.assertEqual(result['candidate'], 'opus')


    def free_and_local(self):
        """Add a training endpoint and a local model to the implementer pool."""
        for name, cost, data in (('muse', 'free', 'trains'), ('glm', 'local', 'local')):
            self.data['models'][name] = {'description': name, 'cost': cost, 'data': data,
                                         'runtimes': {'codex': {'id': 'codex/' + name}}}
        for name in ('luna', 'sol'):
            self.data['models'][name]['cost'] = 'subscription'
        self.data['agents']['implementer']['candidates'] += ['muse', 'glm']
        self.save()

    def test_training_endpoints_are_unavailable_unless_a_config_layer_allows_them(self):
        self.free_and_local()
        listed = self.resolve(list_candidates=True)
        self.assertIn('trains on prompts', listed['unavailable_candidates']['muse'])
        self.assertNotIn('muse', listed['candidates'])
        self.assertIn('glm', listed['candidates'])
        with self.assertRaisesRegex(ValueError, 'not eligible'):
            self.resolve(candidate='muse')
        self.project.write_text(json.dumps({'allow_training': True}))
        self.assertEqual(self.resolve(candidate='muse')['candidate'], 'muse')
        self.data['models']['muse']['cost'] = 'cheap'
        self.save()
        with self.assertRaises(ValueError):
            self.resolve(list_candidates=True)

    def test_each_route_reports_a_cost_aware_shadow_choice_without_changing_it(self):
        self.free_and_local()
        import outcomes
        for index in range(9):
            # Attempts registered without a candidate name are known by their model ID.
            outcomes.put(f'seed#sol-{index}', {'role': 'implementer', 'candidate': 'codex/sol' if index else 'sol',
                                               'status': 'succeeded', 'accepted': True})
        outcomes.put('seed#glm-0', {'role': 'implementer', 'candidate': 'glm', 'status': 'failed'})
        self.profile({'codex': {'candidate': 'sol'}})
        result = self.resolve(target_runtime='codex', assignment='Implement ticket 1.')
        self.assertEqual((result['candidate'], result['selection_source']), ('sol', 'profile'))
        shadow = result['shadow_selection']
        # Every reachable candidate competes, whatever runtime the route was pinned to; muse stays behind
        # the training boundary, and a host's reasoned exclusion still applies.
        self.assertEqual(set(shadow['candidates']), {'luna', 'sol', 'opus', 'glm'})
        narrowed = self.resolve(target_runtime='codex', assignment='Implement ticket 1.',
                                eligible_candidates=['sol', 'luna', 'opus'])['shadow_selection']
        self.assertEqual(set(narrowed['candidates']), {'luna', 'sol', 'opus'})
        sol, glm = shadow['candidates']['sol'], shadow['candidates']['glm']
        self.assertEqual((sol['cost'], sol['successes'], sol['failures'], sol['mean']), ('subscription', 9, 0, 0.909))
        self.assertEqual((glm['cost'], glm['successes'], glm['failures'], glm['mean']), ('local', 0, 1, 0.333))
        self.assertAlmostEqual(sol['utility'], sol['sample'] - shadow['cost_weight'], places=3)
        self.assertAlmostEqual(glm['utility'], glm['sample'], places=3)
        self.assertEqual(shadow['choice'], max(shadow['candidates'], key=lambda n: shadow['candidates'][n]['utility']))
        self.assertEqual(shadow['agrees'], shadow['choice'] == 'sol')
        # The same assignment draws the same samples; another assignment draws its own.
        self.assertEqual(self.resolve(target_runtime='codex', assignment='Implement ticket 1.')['shadow_selection'], shadow)
        samples = {self.resolve(target_runtime='codex', assignment=f'Implement ticket {n}.')['shadow_selection']['candidates']
                   ['glm']['sample'] for n in range(2, 8)}
        self.assertGreater(len(samples), 1)


    def test_shadow_cost_weight_follows_each_providers_allowance_pressure(self):
        self.free_and_local()
        codex = self.root / 'codex-home'
        rollout = codex / 'sessions/2026/10/15/rollout-a.jsonl'
        rollout.parent.mkdir(parents=True)
        now = __import__('time').time()
        rollout.write_text(json.dumps({'type': 'event_msg', 'payload': {'type': 'token_count', 'rate_limits': {
            'limit_id': 'codex', 'primary': {'used_percent': 95.0, 'window_minutes': 300,
                                             'resets_at': now + 600}}}}) + '\n')
        claude = self.root / 'state/automattic/claude-allowance.json'
        claude.parent.mkdir(parents=True)
        claude.write_text(json.dumps({'recorded_at': now, 'rate_limits': {
            'five_hour': {'used_percentage': 10, 'resets_at': now + 600}}}))
        self.profile({'codex': {'candidate': 'sol'}})
        self.data['models']['opus']['cost'] = 'subscription'
        self.save()
        with patch.dict(os.environ, {'CODEX_HOME': str(codex)}):
            shadow = self.resolve(target_runtime='codex', assignment='Implement ticket 1.')['shadow_selection']
        self.assertEqual(shadow['allowance'], {'claude': 'normal', 'codex': 'critical'})
        weights = {name: round(value['sample'] - value['utility'], 3) for name, value in shadow['candidates'].items()}
        self.assertEqual(weights, {'sol': 1.0, 'luna': 1.0, 'opus': 0.15, 'glm': 0.0})


    def test_a_full_local_backend_makes_its_candidates_unavailable_and_routes_carry_the_lease(self):
        self.free_and_local()
        self.data['models']['glm']['backend'] = 'dgx'
        self.data['capacity'] = {'dgx': {'slots': 1, 'health': 'http://127.0.0.1:9/health'}}
        self.save()
        self.assertIn('dgx is unhealthy', self.resolve(list_candidates=True)['unavailable_candidates']['glm'])
        del self.data['capacity']['dgx']['health']
        self.save()
        route = self.resolve(candidate='glm')
        self.assertEqual((route['backend'], route['capacity']['slots']), ('dgx', 1))
        import capacity
        state = self.root / 'effort/workers.sqlite'
        state.parent.mkdir()
        import sqlite3
        with sqlite3.connect(state) as db:
            db.execute('CREATE TABLE attempts (id TEXT PRIMARY KEY, data TEXT NOT NULL)')
            db.execute('INSERT INTO attempts VALUES (?, ?)', ('t1/1', json.dumps({'attempt': 't1/1'})))
        db = capacity.connect()
        db.execute('INSERT INTO leases VALUES (?, ?, ?, ?)', (str(state), 't1/1', 'dgx', 0))
        db.close()
        listed = self.resolve(list_candidates=True)
        self.assertIn('dgx is at capacity (1/1)', listed['unavailable_candidates']['glm'])
        with self.assertRaisesRegex(ValueError, 'not eligible'):
            self.resolve(candidate='glm')
        # A role pinned to the model fails the same way.
        self.data['agents']['implementer'] = {'model': 'glm'}
        self.save()
        with self.assertRaisesRegex(ValueError, 'dgx is at capacity'):
            self.resolve()
        self.data['capacity']['dgx']['slots'] = 2
        self.save()
        self.assertEqual(self.resolve()['backend'], 'dgx')
        self.data['capacity']['dgx']['slots'] = 0
        self.save()
        with self.assertRaises(ValueError):
            self.resolve(list_candidates=True)


if __name__ == '__main__':
    unittest.main()
