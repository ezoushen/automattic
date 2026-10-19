#!/usr/bin/env python3
"""Rule-first routing and the configured fallback when the decision model fails."""

import json
import unittest

from router_case import RouterCase, models


class Fallbacks(RouterCase):
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
        self.data['profiles'] = {'balanced': {'builder': {'codex': {'candidate': 'sol', 'thinking': 'high'}}}}
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

    def test_rule_first_router_settles_a_cross_runtime_pool_by_the_host_runtime(self):
        self.decision_router()
        self.data['profiles'] = {'balanced': {'builder': {'codex': {'candidate': 'sol'},
                                                              'claude': {'candidate': 'opus'}}}}
        self.data['router'].update(fallback_profile='balanced', consult='after-failure')
        self.save()
        routine = self.resolve(host='claude', assignment='Implement ticket 1.')
        self.assertEqual((routine['candidate'], routine['selection_source']), ('opus', 'rule-profile'))
        from_codex = self.resolve(host='codex', assignment='Implement ticket 1.')
        self.assertEqual((from_codex['candidate'], from_codex['selection_source']), ('sol', 'rule-profile'))
        self.assertEqual(self.requests, [])
        # With the host runtime's choice excluded, the remaining runtime's rule applies.
        narrowed = self.resolve(host='claude', assignment='Implement ticket 1.',
                                excluded_candidates={'opus': 'Claude weekly allowance critical.'})
        self.assertEqual((narrowed['candidate'], narrowed['selection_source']), ('sol', 'rule-profile'))
        self.assertEqual(self.requests, [])
        # Another runtime without a rule entry in the pool: the one eligible rule entry still settles it.
        self.data['runtimes']['pi'] = {'executors': {'herdr': {'type': 'skill', 'config': {
            'skill': 'herdr', 'instruction': 'Run one worker.'}}}}
        self.data['models']['glm'] = {'description': 'glm', 'runtimes': {'pi': {'id': 'dgx/glm'}}}
        self.data['agents']['builder']['candidates'].append('glm')
        self.save()
        mixed = self.resolve(host='claude', assignment='Implement ticket 1.',
                             excluded_candidates={'opus': 'Claude weekly allowance critical.'})
        self.assertEqual((mixed['candidate'], mixed['selection_source']), ('sol', 'rule-profile'))
        self.assertEqual(self.requests, [])
        # A rule entry applies only where its candidate actually routes to that runtime.
        self.data['models']['sol']['runtimes']['claude'] = {'id': 'claude/sol'}
        self.save()
        rerouted = self.resolve(host='claude', assignment='Implement ticket 1.',
                                excluded_candidates={'opus': 'Claude weekly allowance critical.'})
        self.assertNotEqual(rerouted['selection_source'], 'rule-profile')

    def test_partial_fallback_profile_still_returns_host_selection(self):
        self.fallback_router()
        self.data['profiles']['balanced']['builder']['codex'] = {'thinking': 'high'}
        self.save()
        result = self.resolve(assignment='Underspecified task.', target_runtime='codex')
        self.assertEqual(result['status'], 'selection_required')
        self.assertEqual(result['selection_router'], {'type': 'host'})
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




if __name__ == '__main__':
    unittest.main()
