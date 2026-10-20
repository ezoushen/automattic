#!/usr/bin/env python3
"""Each Herdr worker lives in a tab of its own: registration asks Herdr where it is; retire confirms the tab closed."""

import json
import threading
import time
import unittest

from lifecycle_case import WorkerLifecycleCase
import support


class HerdrTabs(WorkerLifecycleCase):
    def herdr_route(self):
        """Resolve the worker through the Herdr skill, as the resolver does for a Herdr route."""
        execution = json.loads(self.execution.read_text())
        execution.update(harness=None, target_runtime='claude', executor='skill', executor_context='herdr',
                         executor_config={'skill': 'herdr', 'instruction': 'Run one worker.'})
        self.execution.write_text(json.dumps(execution))

    def collected(self):
        """Collect the registered worker's result and return a retirement request for its pane."""
        self.ready()
        self.collect()
        self.acknowledge()
        request = self.root / 'retire.json'
        request.write_text(json.dumps({'session': 'fixture-session', 'pane': 'pane-1',
                                       'jobs_evidence': ['owned jobs stopped'],
                                       'acceptance': {'decision': 'deferred', 'reason': 'acceptance checks pending'}}))
        return request

    def test_registration_records_where_herdr_itself_places_the_worker(self):
        # Rule: register looks the worker up in Herdr and keeps Herdr's pane, tab, workspace and agent name.
        # The input names only the agent; the pane, tab and workspace can only have come from Herdr.
        self.herdr_route()
        self.herdr_fixture()
        self.register(worker='builder-1', herdr={'session': 'fixture-session'})
        self.assertEqual(self.cli('status')['attempts'][0]['herdr'],
                         {'session': 'fixture-session', 'workspace_id': 'ws-1', 'tab_id': 'tab-1',
                          'pane_id': 'pane-1', 'name': 'builder-1'})

    def test_registration_splits_a_session_pane_name_handle_and_asks_that_session(self):
        # Rule: a `session/pane/name` handle needs no herdr.session; its pane is looked up in its own session,
        # and Herdr must confirm the agent name it gives.
        self.herdr_route()
        self.herdr_fixture()
        error = self.register(worker='fixture-session/pane-1/builder-2', code=2)
        self.assertIn('name builder-2', error)
        self.assertIn('Herdr reports builder-1', error)
        self.register(worker='fixture-session/pane-1/builder-1')
        self.assertEqual(self.cli('status')['attempts'][0]['herdr'],
                         {'session': 'fixture-session', 'workspace_id': 'ws-1', 'tab_id': 'tab-1',
                          'pane_id': 'pane-1', 'name': 'builder-1'})

    def test_a_herdr_that_does_not_answer_holds_no_state_lock_and_is_refused_within_five_seconds(self):
        # Rule: Herdr is asked before the state's write lock is taken and waited on about 5 s per call, so a hung
        # Herdr blocks no other writer, and the registration still fails closed with a named reason.
        self.herdr_fixture(hang=True)
        started, outcome = time.monotonic(), {}

        def register():
            outcome['error'] = self.register(worker='builder-1', herdr={'session': 'fixture-session'}, code=2)
            outcome['seconds'] = time.monotonic() - started
        waiting = threading.Thread(target=register)
        waiting.start()
        while not (self.root / 'herdr-hung').exists() and time.monotonic() - started < 5:
            time.sleep(0.05)
        before = time.monotonic()
        self.register('native/1', 'native', 'native-0', worker='ghost')
        self.assertLess(time.monotonic() - before, 3)
        waiting.join(30)
        self.assertIn('Herdr did not answer agent get builder-1 within 5 s', outcome['error'])
        self.assertLess(outcome['seconds'], 9)
        self.assertEqual([row['attempt'] for row in self.cli('status')['attempts']], ['native/1'])

    def test_registration_refuses_a_tab_or_pane_that_herdr_contradicts(self):
        # Rule: a tab_id or pane_id the registration supplies must be Herdr's; the refusal names both values.
        self.herdr_route()
        self.herdr_fixture()
        for key, claimed, actual in (('tab_id', 'tab-9', 'tab-1'), ('pane_id', 'pane-9', 'pane-1')):
            with self.subTest(key=key):
                error = self.register(worker='builder-1', herdr={'session': 'fixture-session', key: claimed}, code=2)
                self.assertIn(f'{key} {claimed}', error)
                self.assertIn(f'Herdr reports {actual}', error)
                self.assertEqual(self.cli('status')['attempts'], [])
        self.register(worker='builder-1', herdr={'session': 'fixture-session', 'tab_id': 'tab-1', 'pane_id': 'pane-1'})

    def test_registration_fails_closed_when_herdr_cannot_confirm_a_herdr_worker(self):
        # Rule: a Herdr worker that Herdr cannot find, or whose Herdr session is not given, is refused;
        # a worker not launched through Herdr is never looked up. Herdr here knows only builder-1.
        self.herdr_fixture()
        self.register('native/1', 'native', 'native-0', worker='ghost')
        self.herdr_route()
        error = self.register(worker='phantom', herdr={'session': 'fixture-session'}, code=2)
        self.assertIn('Herdr cannot confirm worker phantom in session fixture-session: agent_not_found', error)
        error = self.register(worker='builder-1', code=2)
        self.assertIn('A Herdr worker registers with herdr.session', error)
        error = self.register(worker=None, herdr={'session': 'fixture-session'}, code=2)
        self.assertIn('Registration requires worker', error)
        self.assertEqual([row['attempt'] for row in self.cli('status')['attempts']], ['native/1'])

    def test_a_registration_that_names_a_herdr_session_is_checked_whatever_its_route(self):
        # Rule: a recorded Herdr identity always comes from Herdr, so a claimed one is checked even when the
        # saved route does not go through Herdr.
        self.herdr_fixture()
        error = self.register(worker='builder-1', herdr={'session': 'fixture-session', 'tab_id': 'tab-9'}, code=2)
        self.assertIn('tab_id tab-9', error)
        self.assertIn('Herdr reports tab-1', error)
        self.assertEqual(self.cli('status')['attempts'], [])

    def test_registration_refuses_a_worker_that_shares_its_tab(self):
        # Rule: one worker per tab. A worker whose tab holds more than one pane is refused, naming the rule
        # and the recipe; a tab holding only the worker's pane registers (the first test).
        self.herdr_route()
        self.herdr_fixture(tab_panes=2)
        error = self.register(worker='builder-1', herdr={'session': 'fixture-session'}, code=2)
        self.assertIn('One worker per tab: tab-1 holds 2 panes', error)
        self.assertIn('herdr tab create --workspace <coordinator workspace> --cwd <worktree> --label '
                      '"<slug>/<assignment> <role>" --env AUTOMATTIC_WORKER=<slug>/<assignment> --no-focus', error)
        self.assertEqual(self.cli('status')['attempts'], [])

    def test_registration_fails_closed_when_herdr_cannot_report_the_workers_tab(self):
        # Rule: one worker per tab is confirmed by Herdr; when its tab cannot be read, registration is refused.
        self.herdr_route()
        self.herdr_fixture(tab_panes=None)
        error = self.register(worker='builder-1', herdr={'session': 'fixture-session'}, code=2)
        self.assertIn('Herdr cannot confirm tab tab-1: server_unavailable', error)
        self.assertEqual(self.cli('status')['attempts'], [])

    def test_registration_refuses_a_worker_in_the_coordinators_own_tab(self):
        # Rule: one worker per tab, and never the coordinator's: the tab Herdr gave the coordinator (HERDR_TAB_ID)
        # or the tab its pane is in now. Each refusal names the rule and the recipe.
        self.herdr_route()
        for case, caller in (('HERDR_TAB_ID', None), ('pane moved since', 'caller-pane')):
            with self.subTest(case=case):
                self.herdr_fixture(caller=caller, caller_tab='tab-1')
                if caller is None:
                    self.native_env['HERDR_TAB_ID'] = 'tab-1'
                error = self.register(worker='builder-1', herdr={'session': 'fixture-session'}, code=2)
                self.assertIn("One worker per tab: tab-1 is the coordinator's own tab", error)
                self.assertIn('herdr tab create --workspace <coordinator workspace> --cwd <worktree>', error)
                self.assertEqual(self.cli('status')['attempts'], [])

    def test_retirement_records_closure_only_once_the_workers_tab_is_gone(self):
        # Rule: after the pane is confirmed gone, retire asks Herdr for the worker's tab and records closure only
        # on tab_not_found; a tab that survives (another pane joined it) is reported with what to do, and closure
        # is not recorded.
        self.herdr_route()
        self.herdr_fixture()
        self.register(worker='builder-1', herdr={'session': 'fixture-session'})
        request = self.collected()
        for answer, panes in (('"pane_count": 1', 1), ('"code": "server_unavailable"', None)):
            with self.subTest(answer=answer):
                self.herdr_fixture(tab_survives=True, tab_panes=panes)
                error = self.cli('retire', '--attempt', 'ticket-1/1', '--input', str(request), code=2)
                self.assertIn('Tab tab-1 is not confirmed closed after its worker pane closed', error)
                self.assertIn(answer, error)
                self.assertIn('close the remaining panes or the tab, then retire again', error)
                attempt = self.cli('status')['attempts'][0]
                self.assertNotIn('closed', attempt)
                self.assertIn('reconcile native retirement', attempt['attention'])
        self.herdr_fixture()
        self.assertTrue(self.cli('retire', '--attempt', 'ticket-1/1', '--input', str(request))['closed'])
        self.assertIn('closed', self.cli('status')['attempts'][0])
        self.assertEqual((self.root / 'native-closed').read_text(), 'closed\n')

    def test_retirement_checks_the_tab_recorded_at_registration(self):
        # Rule: retire confirms the tab recorded at registration, even when Herdr now reports the pane in another.
        self.herdr_route()
        self.herdr_fixture()
        self.register(worker='builder-1', herdr={'session': 'fixture-session'})
        request = self.collected()
        self.herdr_fixture(agent_tab='tab-2', tab_survives=True)
        error = self.cli('retire', '--attempt', 'ticket-1/1', '--input', str(request), code=2)
        self.assertIn('Tab tab-1 is not confirmed closed after its worker pane closed', error)
        self.herdr_fixture(agent_tab='tab-2')
        self.assertTrue(self.cli('retire', '--attempt', 'ticket-1/1', '--input', str(request))['closed'])

    def test_an_attempt_with_no_recorded_tab_retires_on_the_pane_rule_alone(self):
        # Rule: an attempt registered without a Herdr identity (before tabs were recorded) records closure on
        # pane_not_found alone, even though Herdr would say the pane's tab survives.
        self.register()
        request = self.collected()
        self.herdr_fixture(tab_survives=True)
        self.assertTrue(self.cli('retire', '--attempt', 'ticket-1/1', '--input', str(request))['closed'])
        self.assertIn('closed', self.cli('status')['attempts'][0])

    def test_a_resumed_retirement_with_no_recorded_tab_finishes_on_the_pane_rule_alone(self):
        # Rule: a retirement of such an attempt that was interrupted after the pane closed finishes on
        # pane_not_found alone when it resumes.
        self.register()
        request = self.collected()
        self.herdr_fixture(verify_error='server_unavailable', tab_survives=True)
        self.cli('retire', '--attempt', 'ticket-1/1', '--input', str(request), code=2)
        self.assertNotIn('closed', self.cli('status')['attempts'][0])
        self.herdr_fixture(tab_survives=True)
        self.assertTrue(self.cli('retire', '--attempt', 'ticket-1/1', '--input', str(request))['closed'])
        self.assertEqual((self.root / 'native-closed').read_text(), 'closed\n')


class TabRecipe(unittest.TestCase):
    def test_the_herdr_guide_starts_each_worker_in_a_tab_of_its_own_then_registers_it(self):
        # Rule: the Herdr guide holds the recipe (tab create with the AUTOMATTIC_WORKER marker, agent start in its
        # root pane, register) instead of a split of the caller's pane; the shared attempt doc names the
        # registration field but not the Herdr recipe.
        guide = ' '.join((support.ROOT / 'hosts/herdr.md').read_text().split())
        position = 0
        for step in ('never as a split of your pane',
                     'herdr tab create --workspace <coordinator workspace> --cwd <worktree> '
                     '--label "<slug>/<assignment> <role>" --env AUTOMATTIC_WORKER=<slug>/<assignment> --no-focus',
                     'herdr agent start <name> --kind <kind> --pane <returned root pane> -- <launch args>',
                     'register it', 'Retirement closes the pane, which closes the tab'):
            position = guide.find(step, position)
            self.assertNotEqual(position, -1, f'{step!r} in order in hosts/herdr.md')
        shared = (support.ROOT / 'runtime/workers/prepare.md').read_text()
        self.assertIn('"herdr": {"session"', shared)
        self.assertNotIn('herdr tab create', shared)
        for text in (guide, shared):
            self.assertNotIn('pane split', text)


if __name__ == '__main__':
    unittest.main()
