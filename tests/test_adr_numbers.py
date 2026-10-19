#!/usr/bin/env python3
"""The ADR number check names duplicated numbers and the next free one, in a tree or at a Git ref."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

import support

SCRIPT = support.script('adr_numbers.py')


def git(repo, *args):
    subprocess.run(['git', '-C', str(repo), *args], check=True, capture_output=True, text=True)


def check(repo, *args):
    result = subprocess.run(['python3', str(SCRIPT), '--repo', str(repo), *args], capture_output=True, text=True)
    return result.returncode, json.loads(result.stdout) if result.stdout.strip() else None, result.stderr


class AdrNumbers(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        git(self.repo, 'init', '-q', '-b', 'main')
        git(self.repo, 'config', 'user.email', 't@example.com')
        git(self.repo, 'config', 'user.name', 't')

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, *names, folder='docs/adr'):
        for name in names:
            path = self.repo / folder / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('# decision\n')

    def test_distinct_numbers_pass_and_name_the_next_free_number(self):
        self.write('0001-event-sourced-orders.md', '0002-postgres-write-model.md', 'README.md')
        code, out, _ = check(self.repo)
        self.assertEqual(0, code)
        self.assertEqual({}, out['duplicates'])
        self.assertEqual('0003', out['next'])

    def test_a_duplicated_number_fails_and_lists_each_file(self):
        self.write('0001-orders.md', '0002-billing.md', '0002-ticket-modes.md')
        code, out, _ = check(self.repo)
        self.assertEqual(1, code)
        self.assertEqual({'0002': ['0002-billing.md', '0002-ticket-modes.md']}, out['duplicates'])
        self.assertEqual('0003', out['next'])

    def test_an_absent_folder_passes_with_the_first_number(self):
        code, out, _ = check(self.repo)
        self.assertEqual(0, code)
        self.assertEqual('0001', out['next'])

    def test_a_project_location_is_checked_instead_of_the_default(self):
        self.write('0004-a.md', '0004-b.md', folder='docs/decisions')
        self.assertEqual(0, check(self.repo)[0])
        code, out, _ = check(self.repo, '--dir', 'docs/decisions')
        self.assertEqual(1, code)
        self.assertEqual(['0004'], list(out['duplicates']))
        self.assertEqual('0005', out['next'])

    def test_a_ref_is_read_from_git_not_the_working_tree(self):
        self.write('0001-a.md')
        git(self.repo, 'add', '-A')
        git(self.repo, 'commit', '-q', '-m', 'one')
        git(self.repo, 'checkout', '-q', '-b', 'feat/x')
        self.write('0001-b.md')
        git(self.repo, 'add', '-A')
        git(self.repo, 'commit', '-q', '-m', 'two')
        git(self.repo, 'checkout', '-q', 'main')
        self.assertEqual(0, check(self.repo)[0])
        code, out, _ = check(self.repo, '--ref', 'feat/x')
        self.assertEqual(1, code)
        self.assertEqual({'0001': ['0001-a.md', '0001-b.md']}, out['duplicates'])

    def commit(self, message):
        git(self.repo, 'add', '-A')
        git(self.repo, 'commit', '-q', '-m', message)

    def test_a_non_ascii_slug_at_a_ref_still_counts(self):
        self.write('0001-a.md', '0001-決策.md')
        self.commit('two')
        code, out, _ = check(self.repo, '--ref', 'HEAD')
        self.assertEqual(1, code)
        self.assertEqual({'0001': ['0001-a.md', '0001-決策.md']}, out['duplicates'])

    def test_a_missing_repository_is_invalid_input(self):
        code, out, _ = check(self.repo / 'missing')
        self.assertEqual(2, code)
        self.assertIsNone(out)

    def test_against_main_finds_a_number_main_claimed_after_the_branch_left(self):
        self.write('0001-a.md')
        self.commit('one')
        git(self.repo, 'checkout', '-q', '-b', 'feat/x')
        self.write('0002-ticket-modes.md')
        self.commit('effort')
        git(self.repo, 'checkout', '-q', 'main')
        self.write('0002-billing.md')
        self.commit('main moved')
        self.assertEqual(0, check(self.repo, '--ref', 'feat/x')[0])
        code, out, _ = check(self.repo, '--ref', 'feat/x', '--against', 'main')
        self.assertEqual(1, code)
        self.assertEqual({'0002': ['0002-billing.md', '0002-ticket-modes.md']}, out['duplicates'])
        self.assertEqual('0003', out['next'])

    def test_against_main_ignores_the_files_both_sides_share(self):
        self.write('0001-a.md')
        self.commit('one')
        git(self.repo, 'checkout', '-q', '-b', 'feat/x')
        self.write('0002-b.md')
        self.commit('effort')
        code, out, _ = check(self.repo, '--ref', 'feat/x', '--against', 'main')
        self.assertEqual(0, code)
        self.assertEqual('0003', out['next'])

    def test_an_unknown_ref_is_invalid_input(self):
        code, out, err = check(self.repo, '--ref', 'no-such-branch')
        self.assertEqual(2, code)
        self.assertIsNone(out)
        self.assertIn('no-such-branch', err)


if __name__ == '__main__':
    unittest.main()
