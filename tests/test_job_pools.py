#!/usr/bin/env python3
"""A job can carry its own pool and profile entry; within a layer it wins over its agent's entry."""
import unittest

from router_case import RouterCase, models


class JobPools(RouterCase):
    def listed(self, job, **kwargs):
        result = self.resolve(job=job, list_candidates=True, **kwargs)
        return dict(result, candidates=list(result['candidates']))

    def test_a_job_entry_replaces_its_agents_pool_for_that_job_only(self):
        self.data['jobs'] = {'repair': {'candidates': ['sol']}}
        self.save()
        repair, ticket = self.listed('repair'), self.listed('ticket')
        self.assertEqual(repair['candidates'], ['sol'])
        self.assertTrue(repair['route_source'].endswith(':jobs.repair'), repair['route_source'])
        self.assertEqual(ticket['candidates'], ['luna', 'sol', 'opus'])
        self.assertTrue(ticket['route_source'].endswith(':agents.builder'), ticket['route_source'])

    def test_a_higher_layer_wins_before_a_job_entry_does(self):
        self.data['jobs'] = {'repair': {'candidates': ['sol']}}
        self.save()
        models.save_session(self.root, 'run', {'agents': {'builder': {'candidates': ['opus']}}})
        self.assertEqual(self.listed('repair', session_id='run')['candidates'], ['opus'])
        models.save_session(self.root, 'run', {'jobs': {'repair': {'candidates': ['luna']}},
                                               'agents': {'builder': {'candidates': ['opus']}}})
        self.assertEqual(self.listed('repair', session_id='run')['candidates'], ['luna'])
        self.assertEqual(self.listed('ticket', session_id='run')['candidates'], ['opus'])

    def test_a_profile_can_pin_a_job_apart_from_its_agent(self):
        self.data['profiles'] = {'balanced': {'builder': {'codex': {'candidate': 'luna'}},
                                              'repair': {'codex': {'candidate': 'sol'}}}}
        self.data['router'] = {'type': 'profile', 'profile': 'balanced'}
        self.save()
        self.assertEqual(self.resolve(job='repair', target_runtime='codex')['candidate'], 'sol')
        self.assertEqual(self.resolve(job='ticket', target_runtime='codex')['candidate'], 'luna')

    def test_an_agent_profile_entry_fits_a_narrower_job_pool(self):
        self.data['jobs'] = {'repair': {'candidates': ['sol']}}
        self.data['profiles'] = {'balanced': {'builder': {'codex': {'candidate': 'luna'}}}}
        self.data['router'] = {'type': 'profile', 'profile': 'balanced'}
        self.save()
        # luna is outside the repair pool, so the agent's pin does not apply to repair; ticket keeps it.
        self.assertEqual(self.resolve(job='repair', target_runtime='codex')['candidate'], 'sol')
        self.assertEqual(self.resolve(job='ticket', target_runtime='codex')['candidate'], 'luna')
        # A pin written for the job itself must belong to the job's pool.
        self.data['profiles']['balanced']['repair'] = {'codex': {'candidate': 'luna'}}
        self.save()
        with self.assertRaisesRegex(ValueError, "'luna' is outside the pool at .*jobs.repair"):
            self.resolve(job='repair', target_runtime='codex')

    def test_unknown_jobs_and_another_agents_job_are_rejected(self):
        for data in ({'jobs': {'implement': {'candidates': ['sol']}}},
                     {'profiles': {'balanced': {'implement': {'codex': {'candidate': 'sol'}}}}}):
            with self.subTest(data=data):
                with self.assertRaises(ValueError):
                    models.validate_execution_config(data, 'test')
        self.data['jobs'] = {'diff-review': {'candidates': ['sol']}}
        self.save()
        with self.assertRaisesRegex(ValueError, "Job 'diff-review' is done by reviewer, not builder"):
            self.resolve(job='diff-review')

if __name__ == '__main__':
    unittest.main()
