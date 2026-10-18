#!/usr/bin/env python3
"""The repository's git hooks: fast checks on commit, the full suite on the commits being pushed."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

import support
from test_doc_checker import CHECKER, CONFIG, GUIDE, SKILL, git

IDENTITY = ['-c', 'user.name=t', '-c', 'user.email=t@t', '-c', 'commit.gpgsign=false']


class GitHooks(unittest.TestCase):
    """Real commits and pushes in a temporary repository with the shipped hooks and a stub suite."""

    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix='git hooks ')
        self.addCleanup(directory.cleanup)
        self.base = Path(directory.name)
        self.root = self.base / 'repo'
        self.runs = self.base / 'suite-runs'
        self.status = self.base / 'suite-status'
        self.fail = self.base / 'suite-fails-at'
        skill = self.root / '.agents/skills/writing-agent-docs'
        skill.mkdir(parents=True)
        (skill / 'check_docs.py').write_text(CHECKER.read_text())
        (skill / 'config.json').write_text(json.dumps(CONFIG))
        for hook in ('pre-commit', 'pre-push'):
            path = self.root / '.githooks' / hook
            path.parent.mkdir(exist_ok=True)
            path.write_text((support.ROOT / '.githooks' / hook).read_text())
            path.chmod(0o755)
        suite = self.root / 'scripts/test-all.sh'
        suite.parent.mkdir()
        # Records the commit and directory it ran in; exits with the status file's value.
        suite.write_text('#!/usr/bin/env bash\ncat >/dev/null\n'
                         f'echo "$(git rev-parse HEAD) $(pwd -P) $(git status --porcelain | wc -l)" >> "{self.runs}"\n'
                         f'[ "$(git rev-parse HEAD)" = "$(cat "{self.fail}" 2>/dev/null)" ] && exit 1\n'
                         f'exit "$(cat "{self.status}" 2>/dev/null || echo 0)"\n')
        suite.chmod(0o755)
        for name, text in {'README.md': '# Project\n\nSee [tool](skills/tool/SKILL.md).\n',
                           'skills/tool/SKILL.md': SKILL.format(name='tool', description='Runs the tool.'),
                           'shared/guide.md': GUIDE, 'scripts/run.py': "GUIDE = 'shared/guide.md'\n"}.items():
            (self.root / name).parent.mkdir(parents=True, exist_ok=True)
            (self.root / name).write_text(text)
        git(self.root, 'init', '-q', '-b', 'main')
        git(self.root, 'config', 'core.hooksPath', '.githooks')
        self.remote = self.base / 'remote.git'
        git(self.base, 'init', '-q', '--bare', str(self.remote))
        git(self.root, 'remote', 'add', 'origin', str(self.remote))

    def commit(self, *flags):
        git(self.root, 'add', '-A')
        return subprocess.run(['git', '-C', str(self.root), *IDENTITY, 'commit', '-qm', 'change', *flags],
                              capture_output=True, text=True)

    def push(self, *args):
        return subprocess.run(['git', '-C', str(self.root), 'push', '-q', 'origin', *args],
                              capture_output=True, text=True)

    def suite_runs(self):
        return self.runs.read_text().splitlines() if self.runs.exists() else []

    def remote_head(self, ref='main'):
        result = subprocess.run(['git', '-C', str(self.remote), 'rev-parse', '-q', '--verify', ref],
                                capture_output=True, text=True)
        return result.stdout.strip() or None

    # pre-commit

    def test_a_commit_runs_the_doc_check_but_not_the_suite(self):
        first = self.commit()
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        self.assertEqual(self.suite_runs(), [])
        (self.root / 'shared/guide.md').write_text(GUIDE + '\nSee [the old guide](old.md).\n')
        rejected = self.commit()
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn('shared/guide.md:7: error link', rejected.stdout + rejected.stderr)
        (self.root / 'shared/guide.md').write_text(GUIDE + '\nBefore August 2025, use the old API.\n')
        warned = self.commit()
        self.assertEqual(warned.returncode, 0, warned.stdout + warned.stderr)
        self.assertIn('warning dated', warned.stdout + warned.stderr)

    def test_the_first_commit_checks_the_whole_tree(self):
        (self.root / 'shared/lost.md').write_text('# Lost\n')
        rejected = self.commit()
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn('shared/lost.md:1: error orphan', rejected.stdout + rejected.stderr)

    def test_a_commit_judges_only_changed_docs_and_blocks_on_invalid_checker_input(self):
        (self.root / 'shared/big.md').write_text('# Big\n\n' + 'x' * 2100 + '\n')
        (self.root / 'README.md').write_text('# Project\n\nSee [tool](skills/tool/SKILL.md), [big](shared/big.md).\n')
        self.assertEqual(self.commit('--no-verify').returncode, 0)
        (self.root / 'shared/guide.md').write_text(GUIDE + '\nMore text.\n')
        unrelated = self.commit()
        self.assertEqual(unrelated.returncode, 0, unrelated.stdout + unrelated.stderr)
        (self.root / '.agents/skills/writing-agent-docs/config.json').write_text('{not json')
        broken = self.commit()
        self.assertNotEqual(broken.returncode, 0)
        self.assertIn('check_docs.py:', broken.stderr)

    def test_a_commit_with_a_python_or_shell_syntax_error_is_rejected(self):
        self.assertEqual(self.commit().returncode, 0)
        cases = {'scripts/bad.py': 'def broken(:\n', 'scripts/bad.sh': 'if then fi\n',
                 'scripts/tool': '#!/usr/bin/env bash\nif then fi\n'}
        for name, text in cases.items():
            with self.subTest(name=name):
                (self.root / name).write_text(text)
                rejected = self.commit()
                self.assertNotEqual(rejected.returncode, 0, name)
                self.assertIn(name, rejected.stdout + rejected.stderr)
                (self.root / name).unlink()
                git(self.root, 'add', '-A')

    def test_the_syntax_check_judges_the_staged_content_and_accepts_any_valid_python(self):
        self.assertEqual(self.commit().returncode, 0)
        bad = self.root / 'scripts/bad.py'
        bad.write_text('def broken(:\n')
        git(self.root, 'add', 'scripts/bad.py')
        bad.write_text('x = 1\n')  # fixed on disk only
        staged_broken = subprocess.run(['git', '-C', str(self.root), *IDENTITY, 'commit', '-qm', 'c'],
                                       capture_output=True, text=True)
        self.assertNotEqual(staged_broken.returncode, 0)
        self.assertIn('scripts/bad.py', staged_broken.stdout + staged_broken.stderr)
        git(self.root, 'add', 'scripts/bad.py')
        bad.write_text('def broken(:\n')  # broken on disk only
        staged_fine = subprocess.run(['git', '-C', str(self.root), *IDENTITY, 'commit', '-qm', 'c'],
                                     capture_output=True, text=True)
        self.assertEqual(staged_fine.returncode, 0, staged_fine.stdout + staged_fine.stderr)
        bad.write_text('x = 1\n')
        (self.root / 'scripts/bom.py').write_bytes(b'\xef\xbb\xbfx = 1\n')
        (self.root / 'scripts/latin.py').write_bytes(b'# -*- coding: latin-1 -*-\nNAME = "caf\xe9"\n')
        encoded = self.commit()
        self.assertEqual(encoded.returncode, 0, encoded.stdout + encoded.stderr)

    # pre-push

    def test_a_push_runs_the_suite_on_the_pushed_commit_in_a_clean_separate_tree(self):
        self.assertEqual(self.commit().returncode, 0)
        pushed = git(self.root, 'rev-parse', 'HEAD').strip()
        (self.root / 'shared/guide.md').write_text(GUIDE + '\nUncommitted [edit](nowhere.md).\n')
        (self.root / 'scratch.txt').write_text('untracked\n')
        result = self.push('main')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        [run] = self.suite_runs()
        commit, directory, dirty = run.split()
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
        self.fail.write_text(git(self.root, 'rev-parse', 'main').strip())
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
        git(self.root, 'rm', '-rq', '.agents', 'scripts/test-all.sh')
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
