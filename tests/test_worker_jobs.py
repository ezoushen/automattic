#!/usr/bin/env python3
"""A registered attempt carries its agent and job: independence, required report sections, read-only work."""
import json
import subprocess
import unittest

from lifecycle_case import WorkerLifecycleCase


class Jobs(WorkerLifecycleCase):
    def use(self, agent, job):
        self.execution.write_text(json.dumps({'harness': 'claude', 'agent': agent, 'job': job,
                                             'settings': {'model': 'sonnet', 'effort': 'high'}}))

    def test_registration_needs_a_known_job_done_by_its_agent(self):
        self.execution.write_text(json.dumps({'harness': 'claude', 'agent': 'builder',
                                             'settings': {'model': 'sonnet', 'effort': 'high'}}))
        self.assertIn('known job', self.register(code=2))
        self.use('reviewer', 'ticket')
        self.assertIn('Job ticket is done by builder', self.register(code=2))
        self.use('builder', 'ticket')
        self.register()

    def test_registration_checks_the_assignment_sent_to_the_worker(self):
        self.assertIn('requires packet', self.register(packet=str(self.root / 'absent.txt'), code=2))
        packet = self.root / 'partial.txt'
        packet.write_text('\n'.join(line for line in self.packet().read_text().splitlines()
                                    if not line.startswith(('brief:', 'agent_file:'))))
        self.assertIn('The ticket assignment lacks agent_file, brief', self.register(packet=str(packet), code=2))
        self.register()

    def test_a_kept_worker_cannot_decide_a_finding_it_raised(self):
        self.use('reviewer', 'diff-review')
        self.register('review-1/1', 'review-1')
        self.ready('review-1/1')
        report = self.root / 'review.md'
        report.write_text('## Coverage\n\n## Review round 1\n')
        self.record('result', 'review-1/1', status='completed', head='head-1', report=str(report),
                    evidence=['review.md'])
        self.acknowledge()
        self.record('retain', 'review-1/1', reason='Disputed finding', next_use='recheck', evidence=['review.md'])
        self.use('reviewer', 'reproduce')
        self.assertIn('independent of diff-review', self.register('review-1/reproduce', 'review-1', code=2))
        # The same job again, as when the reviewer rechecks a repair, keeps its worker.
        self.use('reviewer', 'diff-review')
        self.register('review-1/2', 'review-1')
        # A fresh worker may decide it.
        self.use('reviewer', 'reproduce')
        self.register('review-1/reproduce', 'review-1', session='native-2', worker='pane-2')

    def test_acceptance_waits_for_the_job_report_sections(self):
        self.register()
        self.ready()
        report = self.root / 'report.md'
        report.write_text('Done; see the commits.\n')
        self.collect(report=report)
        gate = self.cli('gate', '--attempt', 'ticket-1/1', '--stage', 'accept', '--revision', 'head-1', code=1)
        self.assertEqual(gate['missing'], ['job report sections ## Implemented'])
        self.assertIn('requires the job report sections ## Implemented',
                      self.record('accepted', commit='merge-1', evidence=['git log'], code=2))
        self.acknowledge()
        closing = {'decision': 'accepted', 'commit': 'merge-1', 'evidence': ['git log']}
        self.assertIn('requires the job report sections', self.record('closed', evidence=['pane closed'],
                                                                      acceptance=closing, code=2))
        self.use('builder', 'ticket')
        self.register('ticket-2/1', 'ticket-2', 'native-2', 'pane-2')
        self.ready('ticket-2/1')
        self.collect('ticket-2/1')  # The helper's report has its Implemented section.
        self.assertTrue(self.cli('gate', '--attempt', 'ticket-2/1', '--stage', 'accept',
                                 '--revision', 'head-1')['complete'])

    def test_a_section_is_a_real_heading_outside_code(self):
        for number, (text, ok) in enumerate((('## Implementedness\n', False),
                                              ('```\n## Implemented\n```\n', False),
                                              ('````md\n```\n## Implemented\n```\n````\n', False),
                                              ('```\n```python\n## Implemented\n```\n', False),
                                              ('```\nexample\n```\n## Implemented\n', True),
                                              ('Text\r\n## Implemented\r\nDone\r\n', True)), 1):
            with self.subTest(text=text):
                attempt = f'ticket-{number}/1'
                self.use('builder', 'ticket')
                self.register(attempt, f'ticket-{number}', f'native-{number}', f'pane-{number}')
                self.ready(attempt)
                report = self.root / f'report-{number}.md'
                report.write_bytes(text.encode())
                self.collect(attempt, report=report)
                self.cli('gate', '--attempt', attempt, '--stage', 'accept', '--revision', 'head-1', code=0 if ok else 1)

    def test_a_read_only_agent_must_leave_tracked_files_and_head_unchanged(self):
        git = lambda *args: subprocess.run(['git', '-C', str(self.root), *args], check=True,
                                           capture_output=True, text=True).stdout.strip()
        git('init', '-q')
        (self.root / 'code.py').write_text('x = 1\n')
        git('add', 'code.py')
        git('-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-qm', 'base')
        head = git('rev-parse', 'HEAD')
        report = self.root / 'review.md'
        report.write_text('## Coverage\n\n## Review round 1\n')
        self.use('reviewer', 'diff-review')
        for attempt, session, edit in (('review-1/1', 'native-1', 'edit'), ('review-2/1', 'native-2', 'commit'),
                                       ('review-3/1', 'native-3', None), ('review-4/1', 'native-4', 'dirty'),
                                       ('review-5/1', 'native-5', 'dirty-edit')):
            if edit in ('dirty', 'dirty-edit'):
                # A snapshot check can start from a dirty tree; only the worker's own changes count.
                (self.root / 'code.py').write_text('x = 3\n')
            self.record('register', attempt, assignment=attempt.split('/')[0], repo=str(self.root),
                        worktree=str(self.root), head=head, execution=str(self.execution), runtime='claude',
                        worker='pane-' + session, native_session=session, owned=True, packet=str(self.packet()))
            self.ready(attempt)
            if edit in ('edit', 'commit', 'dirty-edit'):
                (self.root / 'code.py').write_text('x = 2\n')
            if edit == 'commit':
                git('-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-qam', 'reviewer edit')
            self.record('result', attempt, status='completed', head=head, report=str(report), evidence=['review.md'])
            changed = edit in ('edit', 'commit', 'dirty-edit')
            gate = self.cli('gate', '--attempt', attempt, '--stage', 'accept', '--revision', head, code=1 if changed else 0)
            if changed:
                self.assertEqual(gate['missing'], ['unchanged worktree for a read-only agent'])
                git('reset', '-q', '--hard', head)
            else:
                self.assertTrue(gate['complete'])


    def test_a_read_only_agent_outside_a_git_checkout_cannot_be_verified(self):
        self.use('reviewer', 'diff-review')
        self.register('review-1/1', 'review-1')
        self.ready('review-1/1')
        report = self.root / 'review.md'
        report.write_text('## Coverage\n\n## Review round 1\n')
        self.record('result', 'review-1/1', status='completed', head='head-1', report=str(report), evidence=['r'])
        gate = self.cli('gate', '--attempt', 'review-1/1', '--stage', 'accept', '--revision', 'head-1', code=1)
        self.assertEqual(gate['missing'], ['unchanged worktree for a read-only agent'])


if __name__ == '__main__':
    unittest.main()
