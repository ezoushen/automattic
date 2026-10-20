#!/usr/bin/env python3
"""A registered attempt carries its agent and job: independence, required report sections, read-only work."""
import json
import sqlite3
import subprocess
import unittest

from lifecycle_case import WorkerLifecycleCase


class Jobs(WorkerLifecycleCase):
    def use(self, agent, job):
        self.execution.write_text(json.dumps({'harness': 'claude', 'agent': agent, 'job': job,
                                             'settings': {'model': 'sonnet', 'effort': 'high'}}))

    def checkout(self, files=None):
        """A Git checkout of one commit, kept apart from the files the fixture writes under the root."""
        self.worktree = self.root / 'checkout'
        self.worktree.mkdir()
        self.git('init', '-q')
        return self.commit('base', files or {'code.py': 'x = 1\n'})

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.worktree), *args], check=True,
                              capture_output=True, text=True).stdout.strip()

    def commit(self, message, files):
        for name, content in files.items():
            (self.worktree / name).write_text(content)
        self.git('add', '-A')
        self.git('-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-qm', message)
        return self.git('rev-parse', 'HEAD')

    def review(self, head, attempt='review-1/1', session='native-1'):
        """Register and ready a read-only reviewer attempt in the checkout, and write its report."""
        self.use('reviewer', 'diff-review')
        self.record('register', attempt, assignment=attempt.split('/')[0], repo=str(self.worktree),
                    worktree=str(self.worktree), head=head, execution=str(self.execution), runtime='claude',
                    worker='pane-' + session, native_session=session, owned=True, packet=str(self.packet()))
        self.ready(attempt)
        report = self.root / 'review.md'
        report.write_text('## Coverage\n\n## Review round 1\n')
        return report

    def test_an_untracked_file_a_read_only_agent_edits_is_a_change(self):
        head = self.checkout()
        (self.worktree / 'before.txt').write_text('there before the agent started\n')
        report = self.review(head)
        (self.worktree / 'before.txt').write_text('rewritten by the agent\n')
        self.record('result', 'review-1/1', status='completed', head=head, report=str(report), evidence=['review.md'])
        gate = self.cli('gate', '--attempt', 'review-1/1', '--stage', 'accept', '--revision', head, code=1)
        self.assertEqual(gate['missing'],
                         ['unchanged worktree for a read-only agent (an untracked file changed: before.txt)'])

    def test_an_untracked_file_a_read_only_agent_deletes_is_a_change(self):
        head = self.checkout()
        (self.worktree / 'before.txt').write_text('there before the agent started\n')
        report = self.review(head)
        (self.worktree / 'before.txt').unlink()
        self.record('result', 'review-1/1', status='completed', head=head, report=str(report), evidence=['review.md'])
        gate = self.cli('gate', '--attempt', 'review-1/1', '--stage', 'accept', '--revision', head, code=1)
        self.assertEqual(gate['missing'],
                         ['unchanged worktree for a read-only agent (an untracked file was deleted: before.txt)'])

    def test_untracked_symlinks_and_a_nested_repository_are_held_to_their_registered_state(self):
        head = self.checkout()
        (self.worktree / 'target').mkdir()
        (self.worktree / 'link').symlink_to('target')
        (self.worktree / 'dangling').symlink_to('absent')
        self.git('init', '-q', 'nested')
        report = self.review(head)
        self.record('result', 'review-1/1', status='completed', head=head, report=str(report), evidence=['review.md'])
        self.assertTrue(self.cli('gate', '--attempt', 'review-1/1', '--stage', 'accept', '--revision', head)['complete'])

    def forget_untracked(self, attempt):
        """Make a registration read as one made before the snapshot listed untracked files."""
        with sqlite3.connect(self.state) as db:
            data = json.loads(db.execute('SELECT data FROM attempts WHERE id = ?', (attempt,)).fetchone()[0])
            del data['worktree_baseline']['untracked']
            db.execute('UPDATE attempts SET data = ? WHERE id = ?', (json.dumps(data), attempt))

    def collect_request(self, head, report):
        request = self.root / 'collect.json'
        request.write_text(json.dumps({
            'status': 'completed', 'head': head, 'report': str(report), 'evidence': ['review.md'],
            'disposition': {'kind': 'retain', 'reason': 'recheck', 'next_use': 'recheck', 'evidence': ['review.md']}}))
        return str(request)

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
        head = self.checkout()
        for attempt, session, edit in (('review-1/1', 'native-1', 'edit'), ('review-2/1', 'native-2', 'commit'),
                                       ('review-3/1', 'native-3', None), ('review-4/1', 'native-4', 'dirty'),
                                       ('review-5/1', 'native-5', 'dirty-edit')):
            if edit in ('dirty', 'dirty-edit'):
                # A snapshot check can start from a dirty tree; only the worker's own changes count.
                (self.worktree / 'code.py').write_text('x = 3\n')
            report = self.review(head, attempt, session)
            if edit in ('edit', 'commit', 'dirty-edit'):
                (self.worktree / 'code.py').write_text('x = 2\n')
            if edit == 'commit':
                self.git('-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-qam', 'reviewer edit')
            self.record('result', attempt, status='completed', head=head, report=str(report), evidence=['review.md'])
            changed = edit in ('edit', 'commit', 'dirty-edit')
            gate = self.cli('gate', '--attempt', attempt, '--stage', 'accept', '--revision', head, code=1 if changed else 0)
            if changed:
                reason = (f'HEAD moved from {head} to {self.git("rev-parse", "HEAD")}' if edit == 'commit'
                          else 'tracked files differ from their state at registration')
                self.assertEqual(gate['missing'], [f'unchanged worktree for a read-only agent ({reason})'])
                self.git('reset', '-q', '--hard', head)
            else:
                self.assertTrue(gate['complete'])

    def test_an_untracked_file_a_read_only_agent_adds_fails_the_accept_gate(self):
        head = self.checkout()
        report = self.review(head)
        (self.worktree / 'notes.txt').write_text('scratch\n')
        self.record('result', 'review-1/1', status='completed', head=head, report=str(report), evidence=['review.md'])
        gate = self.cli('gate', '--attempt', 'review-1/1', '--stage', 'accept', '--revision', head, code=1)
        self.assertEqual(gate['missing'],
                         ['unchanged worktree for a read-only agent (an untracked file appeared: notes.txt)'])

    def test_a_gitignored_file_created_after_registration_is_not_a_change(self):
        head = self.checkout({'code.py': 'x = 1\n', '.gitignore': '*.log\n'})
        report = self.review(head)
        (self.worktree / 'run.log').write_text('output\n')
        self.record('result', 'review-1/1', status='completed', head=head, report=str(report), evidence=['review.md'])
        gate = self.cli('gate', '--attempt', 'review-1/1', '--stage', 'accept', '--revision', head)
        self.assertTrue(gate['complete'])

    def test_untracked_files_present_at_registration_are_not_a_change(self):
        head = self.checkout()
        (self.worktree / 'before.txt').write_text('there before the agent started\n')
        for attempt, session, added in (('review-1/1', 'native-1', None), ('review-2/1', 'native-2', 'notes.txt')):
            report = self.review(head, attempt, session)
            if added:
                (self.worktree / added).write_text('scratch\n')
            self.record('result', attempt, status='completed', head=head, report=str(report), evidence=['review.md'])
            gate = self.cli('gate', '--attempt', attempt, '--stage', 'accept', '--revision', head,
                            code=1 if added else 0)
            if added:
                self.assertEqual(gate['missing'],
                                 [f'unchanged worktree for a read-only agent (an untracked file appeared: {added})'])
            else:
                self.assertTrue(gate['complete'])

    def test_collect_refuses_a_read_only_attempt_whose_worktree_changed(self):
        head = self.checkout()
        for number, change in enumerate(('commit', 'edit', 'untracked'), 1):
            with self.subTest(change=change):
                attempt = f'review-{number}/1'
                report = self.review(head, attempt, f'native-{number}')
                if change == 'untracked':
                    (self.worktree / 'notes.txt').write_text('scratch\n')
                else:
                    (self.worktree / 'code.py').write_text('x = 2\n')
                if change == 'commit':
                    self.git('-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-qam', 'reviewer edit')
                reason = {'commit': f'HEAD moved from {head} to {self.git("rev-parse", "HEAD")}',
                          'edit': 'tracked files differ from their state at registration',
                          'untracked': 'an untracked file appeared: notes.txt'}[change]
                request = self.collect_request(head, report)
                error = self.cli('collect', '--attempt', attempt, '--input', request, code=2)
                self.assertIn(f'Collection requires an unchanged worktree for a read-only agent ({reason})', error)
                self.assertNotIn('result', self.cli('status', '--attempt', attempt)['attempts'][0])
                # Once the worktree is as registered, the same result collects.
                self.git('reset', '-q', '--hard', head)
                self.git('clean', '-fdq')
                self.cli('collect', '--attempt', attempt, '--input', request)
                self.assertTrue(self.cli('gate', '--attempt', attempt, '--stage', 'accept', '--revision', head)['complete'])

    def test_collect_accepts_a_read_only_attempt_whose_worktree_is_as_registered(self):
        head = self.checkout({'code.py': 'x = 1\n', '.gitignore': '*.log\n'})
        # Dirty and untracked at registration, and an ignored file made later: none of it is the agent's change.
        (self.worktree / 'code.py').write_text('x = 3\n')
        (self.worktree / 'before.txt').write_text('there before the agent started\n')
        report = self.review(head)
        (self.worktree / 'run.log').write_text('output\n')
        self.cli('collect', '--attempt', 'review-1/1', '--input', self.collect_request(head, report))
        self.assertTrue(self.cli('gate', '--attempt', 'review-1/1', '--stage', 'accept', '--revision', head)['complete'])

    def test_collect_refuses_a_read_only_attempt_it_cannot_verify(self):
        self.use('reviewer', 'diff-review')
        self.register('review-1/1', 'review-1')
        self.ready('review-1/1')
        report = self.root / 'review.md'
        report.write_text('## Coverage\n\n## Review round 1\n')
        error = self.cli('collect', '--attempt', 'review-1/1', '--input', self.collect_request('head-1', report), code=2)
        self.assertIn('Collection requires an unchanged worktree for a read-only agent (not a readable Git checkout '
                      'at registration; read-only work cannot be verified)', error)

    def test_a_registration_without_untracked_files_does_not_count_a_new_untracked_file(self):
        head = self.checkout()
        report = self.review(head)
        self.forget_untracked('review-1/1')
        (self.worktree / 'notes.txt').write_text('scratch\n')
        self.cli('collect', '--attempt', 'review-1/1', '--input', self.collect_request(head, report))
        self.assertTrue(self.cli('gate', '--attempt', 'review-1/1', '--stage', 'accept', '--revision', head)['complete'])

    def test_a_registration_without_untracked_files_still_catches_head_and_tracked_changes_and_says_so(self):
        head = self.checkout()
        for number, change in enumerate(('commit', 'edit'), 1):
            with self.subTest(change=change):
                attempt = f'review-{number}/1'
                report = self.review(head, attempt, f'native-{number}')
                self.forget_untracked(attempt)
                (self.worktree / 'code.py').write_text('x = 2\n')
                if change == 'commit':
                    self.git('-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-qam', 'reviewer edit')
                reason = (f'HEAD moved from {head} to {self.git("rev-parse", "HEAD")}' if change == 'commit'
                          else 'tracked files differ from their state at registration')
                error = self.cli('collect', '--attempt', attempt, '--input', self.collect_request(head, report), code=2)
                self.assertIn('Collection requires an unchanged worktree for a read-only agent '
                              f'({reason}; untracked files were not recorded at registration)', error)
                self.git('reset', '-q', '--hard', head)

    def test_a_read_only_agent_outside_a_git_checkout_cannot_be_verified(self):
        self.use('reviewer', 'diff-review')
        self.register('review-1/1', 'review-1')
        self.ready('review-1/1')
        report = self.root / 'review.md'
        report.write_text('## Coverage\n\n## Review round 1\n')
        self.record('result', 'review-1/1', status='completed', head='head-1', report=str(report), evidence=['r'])
        gate = self.cli('gate', '--attempt', 'review-1/1', '--stage', 'accept', '--revision', 'head-1', code=1)
        self.assertEqual(gate['missing'], ['unchanged worktree for a read-only agent (not a readable Git checkout '
                                           'at registration; read-only work cannot be verified)'])


if __name__ == '__main__':
    unittest.main()
