#!/usr/bin/env python3
"""Decision evidence, offline inspection and bounded prompt experiments."""

import copy
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import decisions
import decision_journal as journal


class DecisionJournal(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.path = self.root / 'decisions.jsonl'
        self.trace = journal.trace_config(self.path, self.root, 'ticket-1/attempt-1', 'session-1')
        self.policy = {'enabled': ['recovery'], 'backend': {
            'protocol': 'systemone', 'endpoint': 'http://localhost:1241/v1/systemone',
            'model': 'test-model', 'revision': 'weights-1', 'instruction': 'Keep the existing scope.'}}
        self.request = {'family': 'recovery', 'state': 'Fixture missing before tests ran.',
                        'instruction': 'Choose the action supported by the evidence.',
                        'options': {'repair-environment': 'Restore the fixture.',
                                    'reselect-worker': 'Change worker.'}}
        self.calls = []

    def transport(self, backend, payload):
        self.calls.append(copy.deepcopy(payload))
        qid, question = next(iter(payload['questions'].items()))
        choice = next(iter(question['criteria']))
        return {'model': backend['model'], 'answers': {qid: {
            'type': 'choice', 'choice': choice,
            'probabilities': {key: float(key == choice) for key in question['criteria']},
            'confidence': .7}}, 'usage': {'input_tokens': 20, 'output_tokens': 0}}

    def decide(self, transport=None):
        return decisions.decide(self.policy, self.request, trace=self.trace,
                                transport=transport or self.transport)

    def cases(self, result):
        return [{'decision_id': result['decision_id'], 'expected': ['repair-environment'],
                 'evidence': 'Independent fixture check: report.md#fixture',
                 'instruction': 'Which action addresses the observed failure?'}]

    def worker_decision(self):
        self.policy['enabled'] = ['worker-selection']
        self.request.update(family='worker-selection', options={'option_0': json.dumps({
            'candidate': 'opus', 'model': 'claude-opus-5-5', 'runtime': 'claude', 'thinking': 'high'})})
        return self.decide()['decision_id']

    def accept_worker(self, did):
        journal.record(self.path, {'event': 'action', 'decision_id': did, 'actor': 'host',
                                  'disposition': 'accepted', 'choice': 'option_0', 'reason': 'Contract risk.'})

    def execution(self, did, **observed):
        return {'event': 'execution', 'decision_id': did,
                'requested': {'runtime': 'claude', 'model': 'claude-opus-5-5', 'effort': 'high'},
                'observed': observed, 'evidence': ['worker.jsonl:11']}

    def cli(self, action, did, *args, code=0):
        result = subprocess.run([sys.executable, '-B', str(Path(journal.__file__)), action,
                                 '--journal', str(self.path), '--decision-id', did, *args],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        return json.loads(result.stdout) if result.stdout else result.stderr

    def scorecard_trial(self, case_id, verdict='accepted', metrics=None):
        did = self.worker_decision()
        self.accept_worker(did)
        journal.record(self.path, dict(self.execution(
            did, runtime='claude', model='claude-opus-5-5', effort='high'), revision='base-1'))
        journal.record(self.path, {'event': 'outcome', 'decision_id': did,
                                  'revision': 'head-1', 'status': 'succeeded' if verdict == 'accepted' else 'failed',
                                  'evidence': ['checks.md@head-1'], 'metrics': metrics or {}})
        return {'case_id': case_id, 'decision_id': did, 'revision': 'head-1',
                'worker': 'worker-' + did, 'reviewer': 'independent-reviewer',
                'verdict': verdict, 'category': 'none' if verdict == 'accepted' else 'implementation',
                'evidence': ['review.md@head-1']}

    def scorecard_manifest(self, trials):
        return {'task_family': 'implementation', 'rubric': 'rubric.md@v1', 'mode': 'controlled',
                'context_policy': 'fresh',
                'candidates': [{'runtime': 'claude', 'model': 'claude-opus-5-5', 'effort': 'high'}],
                'cases': [{'case_id': name, 'input_revision': 'base-1', 'acceptance': 'gates.md@v1'}
                          for name in ('case-a', 'case-b')], 'trials': trials}

    def scorecard_cli(self, manifest, code=0):
        cases_path = self.root / 'scorecard.json'
        cases_path.write_text(json.dumps(manifest))
        result = subprocess.run([sys.executable, '-B', str(Path(journal.__file__)), 'scorecard',
                                 '--journal', str(self.path), '--cases', str(cases_path)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        return json.loads(result.stdout) if result.stdout else result.stderr

    def test_scorecard_cli_grades_checked_cases_and_preserves_missing_usage(self):
        trials = [self.scorecard_trial('case-a', metrics={'verified_completion_seconds': 42}),
                  self.scorecard_trial('case-b', verdict='rejected')]
        before = self.path.read_bytes()
        report = self.scorecard_cli(self.scorecard_manifest(trials))
        candidate = report['candidates'][0]
        self.assertEqual(candidate['quality_score'], 50)
        self.assertEqual((candidate['graded_count'], candidate['accepted_count']), (2, 1))
        self.assertEqual(candidate['case_counts'], {'case-a': 1, 'case-b': 1})
        self.assertEqual(candidate['metrics']['verified_completion_seconds'], {'count': 1, 'mean': 42})
        self.assertNotIn('cache_read_tokens', candidate['metrics'])
        self.assertEqual(report['excluded'], [])
        self.assertEqual(self.path.read_bytes(), before)

    def test_scorecard_cli_labels_historical_observations_and_rejects_ambiguous_mode(self):
        manifest = self.scorecard_manifest([self.scorecard_trial('case-a')])
        manifest['mode'] = 'historical'
        report = self.scorecard_cli(manifest)
        self.assertEqual(report['mode'], 'historical')
        self.assertIsNone(report['candidates'][0]['quality_score'])
        manifest.pop('mode')
        self.assertIn('controlled or historical', self.scorecard_cli(manifest, code=2))

    def test_scorecard_cli_keeps_cache_context_policies_in_separate_cohorts(self):
        manifest = self.scorecard_manifest([self.scorecard_trial('case-a')])
        manifest['context_policy'] = 'same-assignment-continuation'
        self.assertEqual(self.scorecard_cli(manifest)['context_policy'], 'same-assignment-continuation')
        manifest['context_policy'] = 'cross-ticket-reuse'
        self.assertIn('context policy', self.scorecard_cli(manifest, code=2))

    def test_scorecard_cli_requires_case_coverage_and_keeps_unmeasured_candidates_ungraded(self):
        manifest = self.scorecard_manifest([self.scorecard_trial('case-a')])
        manifest['candidates'].append({'runtime': 'codex', 'model': 'gpt-6-sol', 'effort': 'high'})
        report = self.scorecard_cli(manifest)
        measured, unmeasured = report['candidates']
        self.assertEqual((measured['graded_count'], measured['quality_score']), (1, None))
        self.assertEqual((unmeasured['graded_count'], unmeasured['quality_score']), (0, None))
        self.assertEqual(unmeasured['metrics'], {})

    def test_scorecard_cli_grades_models_without_an_effort_control(self):
        controls = {'runtime': 'claude', 'model': 'claude-haiku-4-5-20251001'}
        self.policy['enabled'] = ['worker-selection']
        self.request.update(family='worker-selection', options={'option_0': json.dumps(
            dict(controls, candidate='haiku'))})
        did = self.decide()['decision_id']
        self.accept_worker(did)
        trial = {'case_id': 'case-a', 'decision_id': did, 'revision': 'head-1',
                 'worker': 'haiku-worker', 'reviewer': 'independent-reviewer',
                 'verdict': 'accepted', 'category': 'none',
                 'evidence': ['independent-review.md']}
        journal.record(self.path, {'event': 'execution', 'decision_id': did,
                                  'requested': controls, 'observed': controls,
                                  'revision': 'base-1', 'evidence': ['haiku-native.jsonl']})
        journal.record(self.path, {'event': 'outcome', 'decision_id': did,
                                  'revision': 'head-1', 'status': 'succeeded',
                                  'evidence': ['independent-review.md']})
        manifest = self.scorecard_manifest([trial])
        manifest['candidates'] = [dict(controls, effort=None)]
        report = self.scorecard_cli(manifest)
        self.assertEqual(report['excluded'], [])
        self.assertEqual(report['candidates'][0]['accepted_count'], 1)

    def test_scorecard_cli_does_not_treat_missing_requested_effort_as_no_control(self):
        trial = self.scorecard_trial('case-a')
        did = trial['decision_id']
        journal.record(self.path, dict(self.execution(
            did, runtime='claude', model='claude-opus-5-5'), revision='base-1'))
        journal.record(self.path, {'event': 'outcome', 'decision_id': did,
                                  'revision': 'head-1', 'status': 'succeeded',
                                  'evidence': ['independent-review.md']})
        manifest = self.scorecard_manifest([trial])
        manifest['candidates'][0]['effort'] = None
        report = self.scorecard_cli(manifest)
        self.assertEqual(report['excluded'][0]['reason'], 'settings-unverified')
        self.assertEqual(report['candidates'][0]['graded_count'], 0)

    def test_scorecard_cli_does_not_inflate_quality_by_repeating_the_easy_case(self):
        trials = [self.scorecard_trial('case-a') for _ in range(3)]
        trials.append(self.scorecard_trial('case-b', verdict='rejected'))
        candidate = self.scorecard_cli(self.scorecard_manifest(trials))['candidates'][0]
        self.assertEqual(candidate['quality_score'], 50)
        self.assertEqual(candidate['graded_count'], 4)
        self.assertEqual(candidate['case_counts'], {'case-a': 3, 'case-b': 1})

    def test_scorecard_cli_excludes_mismatched_unknown_and_stale_execution_evidence(self):
        for changed, reason in (({'effort': 'medium'}, 'settings-unverified'),
                                ({'model': None}, 'settings-unverified'),
                                ({'revision': 'different-input'}, 'input-mismatch'),
                                ({'resume': True}, 'incomplete-outcome')):
            with self.subTest(changed=changed):
                trial = self.scorecard_trial('case-a')
                observed = {'runtime': 'claude', 'model': 'claude-opus-5-5', 'effort': 'high'}
                observed.update({k: v for k, v in changed.items() if k in observed})
                observed = {k: v for k, v in observed.items() if v is not None}
                journal.record(self.path, dict(self.execution(trial['decision_id'], **observed),
                                               revision=changed.get('revision', 'base-1')))
                if not changed.get('resume'):
                    journal.record(self.path, {'event': 'outcome', 'decision_id': trial['decision_id'],
                                              'revision': 'head-1', 'status': 'succeeded',
                                              'evidence': ['checks.md@head-1']})
                report = self.scorecard_cli(self.scorecard_manifest([trial]))
                self.assertEqual(report['excluded'][0]['reason'], reason)
                self.assertEqual(report['candidates'][0]['graded_count'], 0)

    def test_scorecard_cli_retains_operational_failures_without_counting_them_as_model_defects(self):
        for category in ('provider', 'environment', 'unknown'):
            with self.subTest(category=category):
                trial = self.scorecard_trial('case-a', verdict='rejected',
                                            metrics={'host_recovery_seconds': 30})
                trial['category'] = category
                report = self.scorecard_cli(self.scorecard_manifest([trial]))
                self.assertEqual(report['excluded'][0]['reason'], category)
                self.assertEqual(report['candidates'][0]['graded_count'], 0)
                self.assertEqual(report['results'][0]['outcome']['metrics'], {'host_recovery_seconds': 30})

    def test_scorecard_cli_requires_independent_revision_bound_reviews(self):
        for change, reason in (({'revision': 'unreviewed-head'}, 'incomplete-outcome'),
                               ({'reviewer': None}, 'review-not-independent'),
                               ({'verdict': 'rejected', 'category': 'implementation'}, 'verdict-conflict'),
                               ({'verdict': 'unknown', 'category': 'unknown'}, 'unreviewed')):
            with self.subTest(change=change):
                trial = self.scorecard_trial('case-a')
                trial.update(change)
                if trial['reviewer'] is None:
                    trial['reviewer'] = trial['worker']
                report = self.scorecard_cli(self.scorecard_manifest([trial]))
                self.assertEqual(report['excluded'][0]['reason'], reason)
                self.assertEqual(report['candidates'][0]['graded_count'], 0)

    def test_scorecard_cli_rejects_duplicate_trials_and_missing_predeclared_evidence(self):
        trial = self.scorecard_trial('case-a')
        manifest = self.scorecard_manifest([trial])
        duplicate = copy.deepcopy(manifest)
        duplicate['trials'].append(dict(trial))
        self.assertIn('unique decisions', self.scorecard_cli(duplicate, code=2))
        for field, value in (('rubric', ''), ('cases', [])):
            with self.subTest(field=field):
                invalid = dict(manifest, **{field: value})
                self.scorecard_cli(invalid, code=2)
        invalid = copy.deepcopy(manifest)
        invalid['trials'][0]['evidence'] = []
        self.assertIn('review evidence', self.scorecard_cli(invalid, code=2))

    def test_skipped_checkpoint_cannot_clear_a_handoff_without_reason_and_evidence(self):
        with self.assertRaises(ValueError):
            journal.append_checkpoint(self.trace, 'recovery', 'input-hash',
                                      skip='settled', reason='Accepted plan determines the action.')
        journal.append_checkpoint(self.trace, 'recovery', 'input-hash', skip='settled',
                                  reason='Accepted plan determines the action.', evidence=['plan.md@head-a'])
        row = journal.read(self.path)[0]
        for field, value in (('reason', ''), ('evidence', []), ('skip_reason', 'host-prefers')):
            with self.subTest(field=field):
                self.path.write_text(json.dumps(dict(row, **{field: value})) + '\n')
                with self.assertRaises(ValueError):
                    journal.check_checkpoint(self.path, self.trace, 'recovery', 'completion')

    def test_cli_worker_handoffs_require_each_annotation_without_inference(self):
        did = self.worker_decision()
        self.assertEqual(self.cli('check', did, '--stage', 'launch', code=1)['missing_evidence'], ['action'])
        self.cli('action', did, '--actor', 'host', '--disposition', 'accepted',
                 '--choice', 'option_0', '--reason', 'Contract risk.')
        self.assertTrue(self.cli('check', did, '--stage', 'launch')['complete'])
        self.assertEqual(self.cli('check', did, '--stage', 'startup', code=1)['missing_evidence'], ['execution'])
        self.cli('execution', did, '--requested-runtime', 'claude', '--requested-model', 'claude-opus-5-5',
                 '--requested-effort', 'high', '--observed-runtime', 'claude',
                 '--observed-model', 'claude-opus-5-5', '--observed-effort', 'high',
                 '--evidence', 'worker.jsonl:11')
        self.assertEqual(self.cli('check', did, '--stage', 'startup')['execution_status'], 'matched')
        self.assertEqual(self.cli('check', did, '--stage', 'completion', code=1)['missing_evidence'], ['outcome'])
        self.cli('outcome', did, '--status', 'succeeded', '--evidence', 'report.md@abc#tests')
        self.assertEqual(self.cli('check', did, '--stage', 'completion', '--revision', 'abc',
                                 code=1)['missing_evidence'], ['outcome'])
        before = self.path.read_bytes()
        self.assertTrue(self.cli('check', did, '--stage', 'completion')['complete'])
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(len(self.calls), 1)

    def test_cli_recording_reports_its_handoff_check(self):
        did = self.worker_decision()
        action = self.cli('action', did, '--actor', 'host', '--disposition', 'accepted',
                          '--reason', 'Contract risk.')
        self.assertEqual(action['handoff'], self.cli('check', did, '--stage', 'launch'))
        self.assertTrue(action['handoff']['complete'])
        execution = self.cli('execution', did, '--requested-runtime', 'claude', '--requested-model',
                             'claude-opus-5-5', '--requested-effort', 'high', '--observed-runtime', 'claude',
                             '--observed-model', 'claude-opus-5-5', '--observed-effort', 'high',
                             '--evidence', 'worker.jsonl:11', '--revision', 'base-1')
        self.assertEqual(execution['handoff']['stage'], 'startup')
        self.assertEqual(execution['handoff']['execution_status'], 'matched')
        outcome = self.cli('outcome', did, '--status', 'succeeded', '--evidence', 'report.md@head-1#tests',
                           '--revision', 'head-1')
        self.assertEqual(outcome['handoff'], self.cli('check', did, '--stage', 'completion', '--revision', 'head-1'))
        self.assertTrue(outcome['handoff']['complete'])

    def test_cli_execution_derives_requested_settings_from_the_recorded_choice(self):
        did = self.worker_decision()
        self.accept_worker(did)
        execution = self.cli('execution', did, '--observed-runtime', 'claude', '--observed-model',
                             'claude-opus-5-5', '--observed-effort', 'medium', '--evidence', 'worker.jsonl:11')
        self.assertEqual(execution['requested'], {'runtime': 'claude', 'model': 'claude-opus-5-5', 'effort': 'high'})
        self.assertEqual(execution['handoff']['execution_status'], 'mismatch')

    def test_cli_execution_without_a_recorded_action_still_fails(self):
        did = self.worker_decision()
        before = self.path.read_bytes()
        self.cli('execution', did, '--observed-runtime', 'claude', '--evidence', 'worker.jsonl:11', code=2)
        self.assertEqual(self.path.read_bytes(), before)

    def test_cli_recording_exits_1_for_an_incomplete_handoff_after_recording(self):
        did = self.worker_decision()
        self.accept_worker(did)
        outcome = self.cli('outcome', did, '--status', 'failed', '--evidence', 'report.md#blocked', code=1)
        self.assertEqual(outcome['handoff']['missing_evidence'], ['execution'])
        self.assertFalse(outcome['handoff']['complete'])
        self.assertEqual(journal.inspect(self.path, did)['outcome']['status'], 'failed')

    def test_cli_execution_names_flags_when_settings_cannot_be_derived(self):
        did = self.worker_decision()
        journal.record(self.path, {'event': 'action', 'decision_id': did, 'actor': 'host',
                                  'disposition': 'fallback', 'choice': 'host-replacement',
                                  'reason': 'Replacement resolution outside the options.'})
        message = self.cli('execution', did, '--observed-runtime', 'claude', '--evidence', 'worker.jsonl:11', code=2)
        self.assertIn('--requested-runtime', message)

    def by_label(self, backend, payload):
        """An order-independent backend: always option_0, so both worker-selection passes agree."""
        answer = type(self).transport(self, backend, payload)
        question = next(iter(answer['answers'].values()))
        question.update(choice='option_0', probabilities={key: float(key == 'option_0') for key in question['probabilities']})
        return answer

    def test_shadow_auto_accept_is_journaled_but_not_returned(self):
        self.transport = self.by_label
        self.policy['shadow_auto_accept'] = {'min_confidence': 0.6}
        self.policy['enabled'] = ['worker-selection']
        self.request.update(family='worker-selection', options={'option_0': '{}', 'option_1': '{}'})
        returned = self.decide()
        self.assertNotIn('shadow_auto_accept', returned)
        trace = journal.trace_config(self.path, self.root, 'ticket-1/phase', 'session-1')
        for _ in range(2):  # first consultation, then resume from the journal
            phase = decisions.checkpoint(self.policy, 'worker-selection', self.request, trace=trace,
                                         transport=self.transport)
            self.assertNotIn('shadow_auto_accept', phase)
        self.policy['shadow_auto_accept'] = {'min_confidence': 0.8}
        self.trace = journal.trace_config(self.path, self.root, 'ticket-1/attempt-2', 'session-1')
        self.decide()
        summaries = journal.inspect(self.path)['decisions']
        self.assertEqual([row['shadow_auto_accept'] for row in summaries], [True, True, False])

    def test_shadow_auto_accept_is_unknown_without_provider_confidence(self):
        self.policy.update(shadow_auto_accept={'min_confidence': 0}, enabled=['worker-selection'])
        self.request.update(family='worker-selection', options={'option_0': '{}', 'option_1': '{}'})

        def no_confidence(backend, payload):
            answer = self.transport(backend, payload)
            next(iter(answer['answers'].values())).pop('confidence')
            return answer
        self.decide(no_confidence)
        self.assertIsNone(journal.inspect(self.path)['decisions'][0]['shadow_auto_accept'])

    def test_shadow_auto_accept_ignores_other_families_and_unconfigured_policy(self):
        self.decide()
        self.policy['shadow_auto_accept'] = {'min_confidence': 0.1}
        self.trace = journal.trace_config(self.path, self.root, 'ticket-1/attempt-2', 'session-1')
        self.decide()
        self.assertEqual([row['shadow_auto_accept'] for row in journal.inspect(self.path)['decisions']],
                         [None, None])

    def shadow_decisions(self, confidences, family='failure-cause'):
        """Journal one hidden label per confidence; the fake backend always answers 'environment'."""
        self.policy['enabled'] = [family]
        self.request = decisions.failure_request(self.failed_summary()) if family == 'failure-cause' else \
            decisions.wake_request(self.capture())
        ids = []
        for index, confidence in enumerate(confidences):
            self.trace = journal.trace_config(self.path, self.root, f'shadow/{index}', 'session-1')

            def answer(backend, payload, confidence=confidence):
                result = self.transport(backend, payload)
                next(iter(result['answers'].values())).update(confidence=confidence)
                return result
            ids.append(self.decide(answer)['decision_id'])
        return ids

    def failed_summary(self):
        log = self.root / 'check.log'
        log.write_text('E   ModuleNotFoundError: yaml\n')
        summary = self.root / 'check.json'
        summary.write_text(json.dumps({'exit_code': 1, 'exit_source': 'command', 'log': str(log)}))
        return summary

    def capture(self):
        path = self.root / 'pane.txt'
        path.write_text('Running tests...')
        return path

    def assess(self, did, expected, source, category='unknown'):
        return self.cli('assessment', did, '--actor', 'reviewer', '--expected', expected, '--source', source,
                        '--category', category, '--evidence', 'rerun.log#1', '--reason', 'Rerun established it.')

    def test_assessment_records_its_label_source(self):
        did = self.shadow_decisions([0.9])[0]
        self.cli('assessment', did, '--actor', 'host', '--expected', 'environment',
                 '--evidence', 'x.log', '--reason', 'r', code=2)
        self.assertEqual(self.assess(did, 'environment', 'objective')['source'], 'objective')
        with self.assertRaisesRegex(ValueError, 'source'):
            journal.record(self.path, {'event': 'assessment', 'decision_id': did, 'actor': 'a', 'reason': 'r',
                                      'expected': ['environment'], 'category': 'none',
                                      'evidence': ['x'], 'source': 'guess'})

    def test_reliability_reports_bins_confusion_sources_and_excludes_outages(self):
        ids = self.shadow_decisions([0.3, 0.6, 0.9, 0.95])
        self.assess(ids[0], 'flaky', 'host', 'context')
        self.assess(ids[1], 'environment', 'host')
        self.assess(ids[2], 'environment', 'objective')
        self.assess(ids[3], 'missing-context', 'independent', 'model')

        def outage(backend, payload):
            raise TimeoutError('timed out')
        self.trace = journal.trace_config(self.path, self.root, 'shadow/outage', 'session-1')
        self.cli('assessment', self.decide(outage)['decision_id'], '--actor', 'host', '--expected', 'environment',
                 '--source', 'host', '--evidence', 'x', '--reason', 'r')
        default = journal.reliability([self.path])['families']['failure-cause']
        self.assertEqual((default['assessed'], default['excluded_by_source']), (2, 2))
        report = journal.reliability([self.path], sources=list(journal.SOURCES))['families']['failure-cause']
        self.assertEqual((report['assessed'], report['unavailable'], report['unassessed']), (4, 1, 0))
        self.assertEqual(report['accuracy'], 0.5)
        self.assertEqual(report['by_source'], {'host': {'count': 2, 'accuracy': 0.5},
                                               'independent': {'count': 1, 'accuracy': 0.0},
                                               'objective': {'count': 1, 'accuracy': 1.0}})
        self.assertEqual([(b['count'], b['accuracy'], b['mean_confidence']) for b in report['confidence_bins']],
                         [(0, None, None), (1, 0.0, 0.3), (0, None, None), (1, 1.0, 0.6), (2, 0.5, 0.925)])
        self.assertEqual(report['no_confidence'], 0)
        self.assertEqual(report['confusion'], {'flaky': {'environment': 1}, 'environment': {'environment': 2},
                                               'missing-context': {'environment': 1}})
        self.assertEqual(report['wrong_by_category'], {'context': 1, 'model': 1})
        self.assertEqual(list(report['by_week'].values())[0]['count'], 4)
        trusted = journal.reliability([self.path], sources=['objective', 'independent'])['families']['failure-cause']
        self.assertEqual((trusted['assessed'], trusted['accuracy']), (2, 0.5))

    def test_reliability_cli_reads_several_journals(self):
        ids = self.shadow_decisions([0.9])
        self.assess(ids[0], 'environment', 'objective')
        other = self.root / 'other.jsonl'
        self.path, first = other, self.path
        self.assess(self.shadow_decisions([0.9], 'wake-triage')[0], 'working', 'objective')
        result = subprocess.run([sys.executable, '-B', str(Path(journal.__file__)), 'reliability',
                                 '--journal', str(first), '--also', str(other)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(set(json.loads(result.stdout)['families']), {'failure-cause', 'wake-triage'})

    def test_export_suite_keeps_only_trusted_text_labels(self):
        ids = self.shadow_decisions([0.9, 0.9, 0.9])
        self.assess(ids[0], 'environment', 'objective')
        self.assess(ids[1], 'flaky', 'host')
        self.assess(ids[2], 'missing-context', 'independent')
        output = self.root / 'suite.json'
        report = journal.export_suite([self.path], output)
        self.assertEqual((report['cases'], report['excluded']['host']), (2, 1))
        suite = decisions.load_suite(output)
        self.assertEqual(suite['kind'], 'adjudicated')
        self.assertEqual({tuple(case['expected']) for case in suite['cases']},
                         {('environment',), ('missing-context',)})
        self.assertIn('rerun.log#1', suite['cases'][0]['evidence'])
        with self.assertRaises(FileExistsError):
            journal.export_suite([self.path], output)

    def test_repeated_journals_count_once_and_filtered_sources_stay_distinct(self):
        ids = self.shadow_decisions([0.9, 0.9])
        self.assess(ids[0], 'environment', 'objective')
        self.assess(ids[1], 'environment', 'host')
        twice = journal.reliability([self.path, self.path], sources=['objective'])['families']['failure-cause']
        self.assertEqual((twice['assessed'], twice['excluded_by_source'], twice['unassessed']), (1, 1, 0))
        output = self.root / 'suite.json'
        self.assertEqual(journal.export_suite([self.path, self.path], output)['cases'], 1)

    def test_export_suite_leaves_no_file_when_nothing_is_exportable(self):
        self.assess(self.shadow_decisions([0.9])[0], 'environment', 'host')
        output = self.root / 'suite.json'
        with self.assertRaises(ValueError):
            journal.export_suite([self.path], output)
        self.assertFalse(output.exists())
        self.assertEqual(sorted(p.name for p in self.root.iterdir() if 'suite' in p.name), [])

    def test_confusion_credits_the_matched_label_and_trusted_labels_survive_later_host_labels(self):
        ids = self.shadow_decisions([0.9])
        self.assess(ids[0], 'environment', 'objective')
        self.cli('assessment', ids[0], '--actor', 'host', '--source', 'host', '--expected', 'missing-context',
                 '--expected', 'environment', '--evidence', 'x', '--reason', 'Later host view.')
        trusted = journal.reliability([self.path])['families']['failure-cause']
        self.assertEqual((trusted['assessed'], trusted['accuracy']), (1, 1.0))
        hosted = journal.reliability([self.path], sources=['host'])['families']['failure-cause']
        self.assertEqual(hosted['confusion'], {'environment': {'environment': 1}})

    def test_adversarial_suite_matches_the_production_request_shape(self):
        suite = decisions.load_suite(Path(__file__).parents[1] / 'benchmarks/shadow-adversarial.json')
        self.assertEqual(suite['kind'], 'synthetic')
        families = {case['request']['family'] for case in suite['cases']}
        self.assertEqual(families, {'failure-cause', 'wake-triage'})
        for case in suite['cases']:
            reference = (decisions.failure_request(self.failed_summary()) if case['request']['family'] == 'failure-cause'
                         else decisions.wake_request(self.capture()))
            self.assertEqual((case['request']['options'], case['request']['instruction']),
                             (reference['options'], reference['instruction']), case['id'])
            self.assertIn('not instructions', case['request']['state'], case['id'])

    def test_cli_override_records_actual_worker_and_exposes_runtime_mismatch(self):
        self.policy['enabled'] = ['worker-selection']
        self.request.update(family='worker-selection', options={
            'option_0': json.dumps({'runtime': 'claude', 'model': 'sonnet', 'thinking': 'medium'}),
            'option_1': json.dumps({'runtime': 'claude', 'model': 'opus', 'thinking': 'high'})})
        did = self.decide()['decision_id']
        before = self.path.read_bytes()
        self.cli('action', did, '--actor', 'host', '--disposition', 'accepted',
                 '--choice', 'option_1', '--reason', 'Host override.', code=2)
        self.assertEqual(self.path.read_bytes(), before)
        self.cli('action', did, '--actor', 'host', '--disposition', 'overridden',
                 '--choice', 'option_1', '--reason', 'Broader verified task scope.')
        self.cli('execution', did, '--requested-runtime', 'claude', '--requested-model', 'opus',
                 '--requested-effort', 'high', '--observed-runtime', 'claude',
                 '--observed-model', 'opus', '--observed-effort', 'medium', '--evidence', 'worker.jsonl:11')
        self.cli('outcome', did, '--status', 'succeeded', '--evidence', 'review.md@abc#accepted')
        checked = self.cli('check', did, '--stage', 'completion')
        self.assertTrue(checked['complete'])
        self.assertEqual(checked['execution_status'], 'mismatch')
        summary = journal.inspect(self.path)['decisions'][0]
        self.assertEqual((summary['choice'], summary['host_choice']), ('option_0', 'option_1'))
        self.assertIsNone(summary['correct'])

    def test_cli_accepts_recommendation_without_guessing_its_option_id(self):
        did = self.worker_decision()
        action = self.cli('action', did, '--actor', 'host', '--disposition', 'accepted',
                          '--reason', 'Verified constraints.')
        self.assertEqual(action['choice'], 'option_0')
        self.assertEqual(len(self.calls), 1)
        replacement = self.worker_decision()
        self.cli('action', replacement, '--actor', 'host', '--disposition', 'overridden',
                 '--reason', 'Different task fit.', code=2)

    def test_completion_cannot_reuse_outcome_before_a_resumed_execution(self):
        did = self.worker_decision()
        self.accept_worker(did)
        execution = self.execution(did, runtime='claude', model='claude-opus-5-5', effort='high')
        journal.record(self.path, execution)
        journal.record(self.path, {'event': 'outcome', 'decision_id': did,
                                  'status': 'succeeded', 'evidence': ['report.md@old']})
        journal.record(self.path, execution)
        checked = journal.check(self.path, did, 'completion')
        self.assertEqual(checked['missing_evidence'], ['outcome'])
        self.assertEqual(checked['outcome'], 'unknown')
        summary = journal.inspect(self.path)['decisions'][0]
        self.assertEqual(summary['missing_evidence'], ['outcome'])
        self.assertEqual(summary['outcome'], 'unknown')
        self.assertEqual(journal.inspect(self.path, did)['outcome']['status'], 'succeeded')

    def test_cli_binds_completion_to_current_revision_without_new_inference(self):
        did = self.worker_decision()
        self.accept_worker(did)
        args = ('--requested-runtime', 'claude', '--requested-model', 'claude-opus-5-5',
                '--requested-effort', 'high', '--evidence', 'worker.jsonl:11')
        self.cli('execution', did, *args, '--revision', 'head-1')
        self.cli('outcome', did, '--status', 'succeeded', '--revision', 'head-1',
                 '--evidence', 'report.md@head-1')
        self.assertTrue(self.cli('check', did, '--stage', 'completion', '--revision', 'head-1')['complete'])
        self.assertEqual(self.cli('check', did, '--stage', 'completion', '--revision', 'head-2',
                                 code=1)['missing_evidence'], ['outcome'])
        self.cli('check', did, '--stage', 'startup', '--revision', 'head-2', code=1)
        self.cli('execution', did, *args, '--revision', 'head-2')
        self.cli('check', did, '--stage', 'completion', '--revision', 'head-2', code=1)
        self.cli('outcome', did, '--status', 'unknown', '--revision', 'head-2',
                 '--evidence', 'report.md@head-2#blocked')
        self.assertTrue(self.cli('check', did, '--stage', 'completion', '--revision', 'head-2')['complete'])
        self.assertEqual(len(self.calls), 1)

    def test_implementation_outcome_can_cover_a_new_head_after_worker_changes_code(self):
        did = self.worker_decision()
        self.accept_worker(did)
        journal.record(self.path, dict(self.execution(did, runtime='claude'), revision='base'))
        journal.record(self.path, {'event': 'outcome', 'decision_id': did, 'revision': 'implemented-head',
                                  'status': 'succeeded', 'evidence': ['report.md@implemented-head']})
        self.assertTrue(journal.check(self.path, did, 'completion', 'implemented-head')['complete'])

    def test_verified_alias_preserves_ids_and_does_not_hide_effort_or_runtime_mismatch(self):
        did = self.worker_decision()
        self.accept_worker(did)
        event = self.execution(did, runtime='claude', model='opus', effort='high')
        journal.record(self.path, event)
        self.assertEqual(journal.check(self.path, did, 'startup')['execution_status'], 'mismatch')
        for invalid in ([], '', ['']):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                journal.record(self.path, dict(event, model_alias_evidence=invalid))
        event['model_alias_evidence'] = ['native-provider-binding.json@head-1']
        journal.record(self.path, event)
        self.assertEqual(journal.check(self.path, did, 'startup')['execution_status'], 'matched')
        self.assertEqual(journal.inspect(self.path, did)['execution']['observed']['model'], 'opus')
        for control, value in (('runtime', 'codex'), ('effort', 'medium')):
            journal.record(self.path, dict(event, observed=dict(event['observed'], **{control: value})))
            self.assertEqual(journal.check(self.path, did, 'startup')['execution_status'], 'mismatch')

    def test_cli_alias_binding_is_explicit_and_legacy_record_accepts_revision(self):
        did = self.worker_decision()
        self.accept_worker(did)
        self.cli('execution', did, '--requested-runtime', 'claude', '--requested-model', 'claude-opus-5-5',
                 '--requested-effort', 'high', '--observed-runtime', 'claude', '--observed-model', 'opus',
                 '--observed-effort', 'high', '--evidence', 'worker.jsonl:11',
                 '--model-alias-evidence', 'provider-binding.json@abc', '--revision', 'abc')
        self.assertEqual(self.cli('check', did, '--stage', 'startup', '--revision', 'abc')['execution_status'], 'matched')
        event_path = self.root / 'outcome.json'
        event_path.write_text(json.dumps({'event': 'outcome', 'decision_id': did, 'revision': 'abc',
                                         'status': 'failed', 'evidence': ['report.md@abc#invalid-run'],
                                         'metrics': {'host_recovery_seconds': 42}}))
        result = subprocess.run([sys.executable, '-B', str(Path(journal.__file__)), 'record',
                                 '--journal', str(self.path), '--event', str(event_path)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.cli('check', did, '--stage', 'completion', '--revision', 'abc')['outcome'], 'failed')
        self.assertEqual(journal.inspect(self.path, did)['outcome']['metrics'], {'host_recovery_seconds': 42})
        self.assertEqual(len(self.calls), 1)

    def test_cli_preserves_unknowns_and_checks_only_the_selected_decision(self):
        did = self.worker_decision()
        self.worker_decision()
        self.cli('action', did, '--actor', 'host', '--disposition', 'accepted',
                 '--choice', 'option_0', '--reason', 'Contract risk.')
        self.cli('execution', did, '--requested-runtime', 'claude', '--requested-model', 'claude-opus-5-5',
                 '--requested-effort', 'high', '--evidence', 'report.md#metadata-unavailable')
        self.cli('outcome', did, '--status', 'unknown', '--evidence', 'report.md#blocked')
        checked = self.cli('check', did, '--stage', 'completion')
        self.assertEqual((checked['execution_status'], checked['outcome']), ('unverified', 'unknown'))
        self.assertEqual(journal.inspect(self.path, did)['execution']['observed'], {})
        self.cli('check', 'unknown-id', '--stage', 'completion', code=2)

    def test_cli_nonworker_and_legacy_record_keep_existing_contracts(self):
        did = self.decide()['decision_id']
        event_path = self.root / 'event.json'
        event_path.write_text(json.dumps({'event': 'action', 'decision_id': did, 'actor': 'host',
                                         'disposition': 'accepted', 'choice': 'repair-environment',
                                         'reason': 'Verified missing fixture.'}))
        legacy = subprocess.run([sys.executable, '-B', str(Path(journal.__file__)), 'record',
                                 '--journal', str(self.path), '--event', str(event_path)],
                                capture_output=True, text=True)
        self.assertEqual(legacy.returncode, 0, legacy.stderr)
        before = self.path.read_bytes()
        self.cli('outcome', did, '--status', 'succeeded', code=2)
        self.cli('check', did, '--stage', 'launch', '--reason', 'Wrong command.', code=2)
        self.assertEqual(self.path.read_bytes(), before)
        self.cli('outcome', did, '--status', 'failed', '--evidence', 'report.md#fixture-failure')
        self.assertTrue(self.cli('check', did, '--stage', 'completion')['complete'])

    def test_worker_execution_distinguishes_requested_effort_from_runtime(self):
        did = self.worker_decision()
        self.accept_worker(did)
        journal.record(self.path, self.execution(did, runtime='claude', model='claude-opus-5-5', effort='medium'))
        summary = journal.inspect(self.path)['decisions'][0]
        self.assertEqual(summary['execution_status'], 'mismatch')
        self.assertEqual(summary['execution']['requested']['effort'], 'high')
        self.assertEqual(summary['execution']['observed']['effort'], 'medium')
        self.assertEqual(summary['missing_evidence'], ['outcome'])
        self.assertIsNone(summary['correct'])
        self.assertEqual(len(self.calls), 1)

    def test_execution_requires_action_evidence_and_original_requested_settings(self):
        did = self.worker_decision()
        event = self.execution(did, runtime='claude', model='claude-opus-5-5', effort='high')
        with self.assertRaisesRegex(ValueError, 'action'):
            journal.record(self.path, event)
        self.accept_worker(did)
        for invalid in (dict(event, evidence=[]), dict(event, observed={'effort': 4}),
                        dict(event, requested=dict(event['requested'], effort='medium'))):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                journal.record(self.path, invalid)
        journal.record(self.path, event)
        self.assertEqual(journal.inspect(self.path)['decisions'][0]['execution_status'], 'matched')

    def test_missing_effort_remains_unverified_and_missing_annotations_are_visible(self):
        did = self.worker_decision()
        summary = journal.inspect(self.path)['decisions'][0]
        self.assertEqual(summary['missing_evidence'], ['action', 'execution', 'outcome'])
        self.assertEqual(summary['execution_status'], 'unverified')
        self.accept_worker(did)
        journal.record(self.path, self.execution(did, runtime='claude', model='claude-opus-5-5'))
        self.assertEqual(journal.inspect(self.path)['decisions'][0]['execution_status'], 'unverified')
        journal.record(self.path, self.execution(did, runtime='claude', model='claude-opus-5-5', effort='high'))
        self.assertEqual(journal.inspect(self.path)['decisions'][0]['execution_status'], 'matched')

    def test_inventory_preserves_calibration_warnings(self):
        self.decide()
        rows = journal.read(self.path)
        rows[0]['result']['warnings'] = [{'code': 'calibration_stale', 'message': 'Configuration changed.'}]
        self.path.write_text(''.join(json.dumps(row) + '\n' for row in rows))
        self.assertEqual(journal.inspect(self.path)['decisions'][0]['warnings'], rows[0]['result']['warnings'])

    def test_records_exact_composed_request_once_and_keeps_scores_distinct(self):
        result = self.decide()
        self.assertEqual(len(self.calls), 1)
        record = journal.inspect(self.path, result['decision_id'])['decision']
        self.assertEqual(record['payload'], self.calls[0])
        self.assertIn('Keep the existing scope.', record['payload']['questions']['recovery']['instructions'])
        self.assertEqual(record['response']['usage']['input_tokens'], 20)
        self.assertEqual(record['result']['confidence'], .7)
        self.assertEqual(record['result']['probabilities']['repair-environment'], 1)
        self.assertEqual(record['assignment'], 'ticket-1/attempt-1')
        self.assertEqual(record['session'], 'session-1')
        self.assertEqual(os.stat(self.path).st_mode & 0o777, 0o600)

    def test_offline_annotations_link_actions_and_outcomes_without_inventing_labels(self):
        result = self.decide()
        did = result['decision_id']
        journal.record(self.path, {'event': 'action', 'decision_id': did, 'actor': 'host',
                                  'disposition': 'overridden', 'choice': 'reselect-worker',
                                  'reason': 'Host assessed additional evidence.'})
        journal.record(self.path, {'event': 'outcome', 'decision_id': did,
                                  'status': 'succeeded', 'evidence': ['report.md#tests'],
                                  'metrics': {'seconds': 42, 'input_tokens': 120}})
        before = self.path.read_bytes()
        with patch.object(decisions, 'systemone_request', side_effect=AssertionError('offline')):
            summary = journal.inspect(self.path)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(len(self.calls), 1)
        self.assertIsNone(summary['decisions'][0]['correct'])
        self.assertEqual(summary['decisions'][0]['outcome'], 'succeeded')
        journal.record(self.path, {'event': 'assessment', 'decision_id': did, 'actor': 'reviewer',
                                  'expected': ['repair-environment'], 'category': 'host',
                                  'evidence': ['report.md#fixture'], 'reason': 'Fixture was the cause.'})
        self.assertTrue(journal.inspect(self.path)['decisions'][0]['correct'])

    def test_rejects_unknown_ids_false_acceptance_and_unlinked_outcomes(self):
        did = self.decide()['decision_id']
        events = [
            {'event': 'outcome', 'decision_id': 'missing', 'status': 'unknown', 'evidence': []},
            {'event': 'outcome', 'decision_id': did, 'status': 'succeeded', 'evidence': ['test']},
            {'event': 'action', 'decision_id': did, 'actor': 'host', 'disposition': 'accepted',
             'choice': 'reselect-worker', 'reason': 'Mismatch'},
            {'event': 'assessment', 'decision_id': did, 'actor': 'reviewer', 'expected': ['publish'],
             'category': 'model', 'evidence': ['test'], 'reason': 'Outside original options'},
        ]
        before = self.path.read_bytes()
        for event in events:
            with self.subTest(event=event), self.assertRaises(ValueError):
                journal.record(self.path, event)
        self.assertEqual(self.path.read_bytes(), before)

    def test_timeout_and_invalid_answer_are_recorded_without_retry(self):
        def failed(backend, payload):
            raise TimeoutError('unavailable')
        result = self.decide(failed)
        record = journal.inspect(self.path, result['decision_id'])['decision']
        self.assertIsNone(record['response'])
        self.assertIn('unavailable', record['result']['error'])
        self.assertIsNotNone(record['payload'])
        result = self.decide(lambda *_: {'model': 'wrong-model'})
        record = journal.inspect(self.path, result['decision_id'])['decision']
        self.assertEqual(record['response'], {'model': 'wrong-model'})
        self.assertEqual(record['result']['status'], 'host_required')
        result = self.decide(lambda *_: ['invalid', 'response'])
        self.assertIsNone(journal.inspect(self.path)['decisions'][-1]['usage'])

    def test_concurrent_decisions_remain_complete_and_distinct(self):
        with ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(lambda _: self.decide(), range(12)))
        self.assertEqual(journal.inspect(self.path)['count'], 12)
        self.assertEqual(len({result['decision_id'] for result in results}), 12)

    def test_partial_journal_is_reported_without_destroying_existing_evidence(self):
        self.path.write_text('{"unfinished":')
        result = self.decide()
        self.assertIn('journal_unavailable', [x['code'] for x in result['warnings']])
        self.assertEqual(self.path.read_text(), '{"unfinished":')

    def test_journal_failure_does_not_repeat_or_discard_a_valid_recommendation(self):
        with patch.object(journal, 'append_decision', side_effect=OSError('disk full')):
            result = self.decide()
        self.assertEqual(result['choice'], 'repair-environment')
        self.assertIn('journal_unavailable', [x['code'] for x in result['warnings']])
        self.assertEqual(len(self.calls), 1)

    def test_replay_changes_wording_or_order_with_stable_ids_and_no_state_writes(self):
        result = self.decide()
        before = self.path.read_bytes()
        self.calls.clear()
        report = journal.replay(self.path, self.cases(result), self.policy['backend'], transport=self.transport)
        self.assertEqual(len(self.calls), 3)
        self.assertEqual([x['variant'] for x in report['results']], ['original', 'reversed', 'paraphrase'])
        self.assertEqual([x['correct'] for x in report['results']], [True, False, True])
        self.assertTrue(report['results'][1]['changed'])
        self.assertEqual(self.calls[0]['state'], self.calls[2]['state'])
        self.assertIn('Keep the existing scope.', self.calls[2]['questions']['recovery']['instructions'])
        self.assertEqual(self.path.read_bytes(), before)
        self.assertTrue(report['complete'])

    def test_replay_preflights_all_cases_and_budget_before_any_inference(self):
        result = self.decide()
        self.calls.clear()
        cases = self.cases(result)
        for bad_cases, backend, max_calls in [
            (cases, self.policy['backend'], 2),
            (cases, dict(self.policy['backend'], model='different-model'), 12),
            (cases + [dict(cases[0], decision_id='missing')], self.policy['backend'], 12),
            ([dict(cases[0], expected=['invented'])], self.policy['backend'], 12),
        ]:
            with self.assertRaises(ValueError):
                journal.replay(self.path, bad_cases, backend, transport=self.transport, max_calls=max_calls)
        self.assertEqual(self.calls, [])

    def test_replay_stops_at_time_budget_and_never_retries_errors(self):
        result = self.decide()
        self.calls.clear()
        tick = [0]
        def slow(backend, payload):
            tick[0] += 2
            self.calls.append(payload)
            raise TimeoutError('timeout')
        with patch('time.monotonic', side_effect=lambda: tick[0]):
            report = journal.replay(self.path, self.cases(result), self.policy['backend'],
                                    transport=slow, budget_seconds=1)
        self.assertEqual(len(self.calls), 1)
        self.assertFalse(report['complete'])
        self.assertFalse(report['results'][0]['correct'])


if __name__ == '__main__':
    unittest.main()
