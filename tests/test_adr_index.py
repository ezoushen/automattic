#!/usr/bin/env python3
"""The ADR check holds the current-state index to the files and every supersede link to both ends."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

import support

SCRIPT = support.script('adr_numbers.py')

INDEX = """# Decisions

## Accepted
{accepted}

## Superseded
{superseded}

## Deprecated
{deprecated}
"""


def check(repo, *args):
    result = subprocess.run(['python3', str(SCRIPT), '--repo', str(repo), *args], capture_output=True, text=True)
    return result.returncode, json.loads(result.stdout) if result.stdout.strip() else None


class AdrIndex(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        subprocess.run(['git', '-C', str(self.repo), 'init', '-q'], check=True)
        self.folder = self.repo / 'docs/adr'
        self.folder.mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def adr(self, name, status=None, supersedes=None):
        head = ''
        if status or supersedes:
            head = '---\n' + (f'status: {status}\n' if status else '') + \
                   (f'supersedes: {supersedes}\n' if supersedes else '') + '---\n'
        (self.folder / name).write_text(head + '# A decision\n\nWe decided it because of a reason.\n')

    def index(self, accepted=(), superseded=(), deprecated=()):
        lines = lambda names: '\n'.join(f'- [{n[:4]}]({n}) A decision: the rule in one line' for n in names)
        (self.folder / 'README.md').write_text(INDEX.format(accepted=lines(accepted), superseded=lines(superseded),
                                                            deprecated=lines(deprecated)))

    def consistent(self):
        self.adr('0001-sync-api.md', status='superseded by ADR-0003')
        self.adr('0002-cents.md')
        self.adr('0003-async-api.md', status='accepted', supersedes='ADR-0001')
        self.adr('0004-old-cache.md', status='deprecated')
        self.index(accepted=['0002-cents.md', '0003-async-api.md'], superseded=['0001-sync-api.md'],
                   deprecated=['0004-old-cache.md'])

    def test_a_consistent_index_passes(self):
        self.consistent()
        code, out = check(self.repo, '--require-index')
        self.assertEqual(0, code, out)
        self.assertEqual([], out['index_problems'])

    def test_an_absent_folder_passes_even_when_an_index_is_required(self):
        code, out = check(self.repo, '--dir', 'docs/none', '--require-index')
        self.assertEqual(0, code, out)

    def test_an_accepted_adr_missing_from_the_index_fails(self):
        self.consistent()
        self.adr('0005-new-rule.md')
        code, out = check(self.repo)
        self.assertEqual(1, code)
        self.assertEqual(['0005-new-rule.md: accepted but not listed under Accepted'], out['index_problems'])

    def test_an_index_entry_without_its_file_fails(self):
        self.consistent()
        (self.folder / '0002-cents.md').unlink()
        code, out = check(self.repo)
        self.assertEqual(1, code)
        self.assertEqual(['0002-cents.md: listed in the index but no such file'], out['index_problems'])

    def test_a_superseded_adr_still_listed_as_accepted_fails(self):
        self.consistent()
        self.index(accepted=['0001-sync-api.md', '0002-cents.md', '0003-async-api.md'],
                   superseded=['0001-sync-api.md'], deprecated=['0004-old-cache.md'])
        code, out = check(self.repo)
        self.assertEqual(1, code)
        self.assertEqual(['0001-sync-api.md: superseded by ADR-0003 but also listed under Accepted'],
                         out['index_problems'])

    def test_a_supersede_link_without_its_counterpart_fails_in_both_directions(self):
        self.consistent()
        self.adr('0003-async-api.md', status='accepted')
        code, out = check(self.repo)
        self.assertEqual(1, code)
        self.assertEqual(['0001-sync-api.md: superseded by ADR-0003, which does not name it in supersedes'],
                         out['index_problems'])
        self.consistent()
        self.adr('0001-sync-api.md')
        self.index(accepted=['0001-sync-api.md', '0002-cents.md', '0003-async-api.md'],
                   deprecated=['0004-old-cache.md'])
        code, out = check(self.repo)
        self.assertEqual(1, code)
        self.assertEqual(['0003-async-api.md: supersedes ADR-0001, which is not superseded by ADR-0003'],
                         out['index_problems'])

    def test_an_unknown_status_fails(self):
        self.consistent()
        self.adr('0002-cents.md', status='proposed')
        code, out = check(self.repo)
        self.assertEqual(1, code)
        self.assertIn('0002-cents.md: unknown status proposed', out['index_problems'])

    def test_a_missing_index_fails_only_when_required(self):
        self.adr('0001-a.md')
        self.assertEqual(0, check(self.repo)[0])
        code, out = check(self.repo, '--require-index')
        self.assertEqual(1, code)
        self.assertEqual(['docs/adr/README.md: no index'], out['index_problems'])


if __name__ == '__main__':
    unittest.main()
