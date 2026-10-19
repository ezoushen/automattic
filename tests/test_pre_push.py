#!/usr/bin/env python3
"""pre-push: the full checks on each pushed commit, in a temporary worktree."""
from pathlib import Path
import subprocess
import unittest

from hook_case import IDENTITY, HookRepo
from test_doc_checker import GUIDE, git


class PrePush(HookRepo):
    """Which commits are checked, where, and what stops a push."""

    def test_a_push_runs_the_suite_on_the_pushed_commit_in_a_clean_separate_tree(self):
        self.assertEqual(self.commit().returncode, 0)
        pushed = git(self.root, 'rev-parse', 'HEAD').strip()
        (self.root / 'shared/guide.md').write_text(GUIDE + '\nUncommitted [edit](nowhere.md).\n')
        (self.root / 'scratch.txt').write_text('untracked\n')
        result = self.push('main')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        [run] = self.suite_runs()
        commit, rest = run.split(' ', 1)
        directory, dirty = rest.rsplit(' ', 1)
        self.assertEqual(commit, pushed)
        self.assertNotEqual(Path(directory), self.root.resolve())
        self.assertEqual(dirty, '0', 'the suite sees only the pushed commit')
        self.assertFalse(Path(directory).parent.exists(), 'the temporary tree and its directory are removed')
        self.assertEqual(len(git(self.root, 'worktree', 'list').splitlines()), 1)
        self.assertEqual(self.remote_head(), pushed)

    def test_a_failing_suite_or_doc_error_at_the_pushed_commit_blocks_the_push(self):
        self.assertEqual(self.commit().returncode, 0)
        self.status.write_text('1')
        failed = self.push('main')
        self.assertNotEqual(failed.returncode, 0)
        self.assertIn('pre-push', failed.stderr)
        self.assertIsNone(self.remote_head())
        self.status.write_text('0')
        (self.root / 'shared/guide.md').write_text(GUIDE + '\nSee [the old guide](old.md).\n')
        self.assertEqual(self.commit('--no-verify').returncode, 0)
        (self.root / 'shared/guide.md').write_text(GUIDE)  # fixed on disk, not committed
        blocked = self.push('main')
        self.assertNotEqual(blocked.returncode, 0)
        self.assertIn('shared/guide.md:7: error link', blocked.stdout + blocked.stderr)
        self.assertIsNone(self.remote_head())
        self.assertEqual(len(git(self.root, 'worktree', 'list').splitlines()), 1)

    def test_every_pushed_commit_is_tested_once_and_a_deletion_runs_nothing(self):
        self.assertEqual(self.commit().returncode, 0)
        git(self.root, 'branch', 'same')
        git(self.root, 'checkout', '-q', '-b', 'topic')
        (self.root / 'shared/guide.md').write_text(GUIDE + '\nMore text.\n')
        self.assertEqual(self.commit().returncode, 0)
        git(self.root, 'checkout', '-q', 'main')
        result = self.push('main', 'same', 'topic')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        tested = sorted(run.split()[0] for run in self.suite_runs())
        expected = sorted(git(self.root, 'rev-parse', ref).strip() for ref in ('main', 'topic'))
        self.assertEqual(tested, expected)
        deleted = self.push('--delete', 'topic')
        self.assertEqual(deleted.returncode, 0, deleted.stdout + deleted.stderr)
        self.assertEqual(len(self.suite_runs()), 2)


    def test_a_failure_on_any_pushed_ref_stops_the_push(self):
        self.assertEqual(self.commit().returncode, 0)
        git(self.root, 'checkout', '-q', '-b', 'topic')
        (self.root / 'shared/guide.md').write_text(GUIDE + '\nMore text.\n')
        self.assertEqual(self.commit().returncode, 0)
        git(self.root, 'checkout', '-q', 'main')
        self.fail_at.write_text(git(self.root, 'rev-parse', 'main').strip())
        result = self.push('main', 'topic')
        self.assertNotEqual(result.returncode, 0)
        self.assertIsNone(self.remote_head('main'))
        self.assertIsNone(self.remote_head('topic'))

    def test_commits_the_remote_has_are_not_retested_and_tags_count_once(self):
        self.assertEqual(self.commit().returncode, 0)
        self.assertEqual(self.push('main').returncode, 0)
        self.assertEqual(len(self.suite_runs()), 1)
        self.assertEqual(self.push('main').returncode, 0)
        git(self.root, *IDENTITY, 'tag', '-a', 'v1', '-m', 'release')
        git(self.root, 'tag', 'light')
        tags = self.push('--tags')
        self.assertEqual(tags.returncode, 0, tags.stdout + tags.stderr)
        self.assertEqual(len(self.suite_runs()), 2, 'one run for the tagged commit, none for the up-to-date main')

    def test_a_pushed_commit_without_the_checks_is_pushed_with_a_warning(self):
        self.assertEqual(self.commit().returncode, 0)
        git(self.root, 'rm', '-rq', '.agents', 'tests/run_all.py')
        old = subprocess.run(['git', '-C', str(self.root), *IDENTITY, 'commit', '-qm', 'old', '--no-verify'],
                             capture_output=True, text=True)
        self.assertEqual(old.returncode, 0, old.stderr)
        result = self.push('main')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('no doc checker', result.stderr)
        self.assertIn('no test suite', result.stderr)

    def test_a_deletion_runs_nothing_in_a_sha256_repository(self):
        repo = self.base / 'sha256'
        git(self.base, 'init', '-q', '--object-format=sha256', '-b', 'main', str(repo))
        git(repo, 'config', 'core.hooksPath', str(self.root / '.githooks'))
        (repo / 'file.txt').write_text('x\n')
        git(repo, 'add', '-A')
        git(repo, *IDENTITY, 'commit', '-qm', 'c', '--no-verify')
        remote = self.base / 'sha256.git'
        git(self.base, 'init', '-q', '--bare', '--object-format=sha256', str(remote))
        git(repo, 'push', '-q', '--no-verify', str(remote), 'main:topic')
        deleted = subprocess.run(['git', '-C', str(repo), 'push', '-q', str(remote), '--delete', 'topic'],
                                 capture_output=True, text=True)
        self.assertEqual(deleted.returncode, 0, deleted.stdout + deleted.stderr)
        self.assertNotIn('checking', deleted.stderr)


if __name__ == '__main__':
    unittest.main()
