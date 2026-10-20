#!/usr/bin/env python3
"""This repository records its own binding decisions as ADRs with a checked index."""
import json
import subprocess
import unittest

import support

ROOT = support.ROOT


class RepoAdrs(unittest.TestCase):
    def test_the_repositorys_adrs_pass_the_check_with_an_index(self):
        result = subprocess.run(['python3', str(support.script('adr_numbers.py')), '--repo', str(ROOT),
                                 '--index'], capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        out = json.loads(result.stdout)
        self.assertEqual('0010', out['next'])
        index = (ROOT / 'docs/adr/README.md').read_text()
        accepted = index[index.index('## Accepted'):index.index('## Superseded')]
        for name in ('0001-adr-numbers-are-checked-on-main.md', '0002-grilling-asks-principles-only.md',
                     '0003-adrs-record-what-others-follow.md', '0004-adrs-are-superseded-never-rewritten.md',
                     '0005-the-adr-index-is-the-current-state.md', '0006-adr-statuses-have-no-proposed.md',
                     '0007-builders-work-test-first-from-our-own-standard.md',
                     '0008-builders-refactor-after-green-within-the-ticket.md',
                     '0009-the-framework-depends-on-no-external-skill-package.md'):
            self.assertIn(f']({name})', accepted)

    def test_adr_0004_states_the_repair_exception(self):
        text = ' '.join((ROOT / 'docs/adr/0004-adrs-are-superseded-never-rewritten.md').read_text().split())
        self.assertIn('apart from repairing a broken status or supersede link', text)

    def test_each_matt_replacement_adr_states_its_rule(self):
        rules = {
            '0007-builders-work-test-first-from-our-own-standard.md':
                'Every builder works test-first from the [TDD standard](../../standards/tdd.md)',
            '0008-builders-refactor-after-green-within-the-ticket.md':
                "refactors the ticket's own code within the ticket's scope",
            '0009-the-framework-depends-on-no-external-skill-package.md':
                'The framework depends on no external skill package',
        }
        for name, rule in rules.items():
            with self.subTest(adr=name):
                self.assertIn(rule, ' '.join((ROOT / 'docs/adr' / name).read_text().split()))

    def test_contributors_are_told_to_read_the_index_first(self):
        text = ' '.join((ROOT / 'docs/development.md').read_text().split())
        self.assertIn('[decision index](adr/README.md) before an architectural change', text)
        self.assertIn('only accepted ADRs bind', text)


if __name__ == '__main__':
    unittest.main()
