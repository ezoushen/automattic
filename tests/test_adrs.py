#!/usr/bin/env python3
"""A decision that passes the three tests is offered as an ADR, written on the user's yes, and binds later work."""
import subprocess
import unittest

import support

ROOT = support.ROOT
ADR = ROOT / 'runtime/domain/adr.md'


def prose(path):
    return ' '.join((ROOT / path).read_text().split())


class Adrs(unittest.TestCase):
    def test_the_adr_doc_states_matts_format_and_process(self):
        text = prose(ADR)
        for rule in ('`docs/adr/NNNN-slug.md`', 'the highest existing number plus one',
                     'Create `docs/adr/` lazily', 'a title and one to three sentences',
                     'Status, Considered Options and Consequences only when they add something',
                     '**Hard to reverse:**', '**Surprising without context:**', '**A real trade-off:**',
                     'All three must hold', 'Offer the ADR to the user and write it only after their yes',
                     'a new ADR that supersedes it', '`superseded by ADR-NNNN`',
                     'Never rewrite an accepted ADR', "A project's existing decision-record convention wins"):
            self.assertIn(rule, text)

    def test_each_phase_offers_reads_or_holds_on_adrs(self):
        self.assertIn('offer an [ADR](../domain/adr.md)', prose('runtime/interview/grilling.md'))
        self.assertIn('accepted [ADRs](../../runtime/domain/adr.md) in the area', prose('skills/align/SKILL.md'))
        ticket = prose('skills/dispatch/jobs/ticket.md')
        self.assertIn('accepted [ADRs](../../../runtime/domain/adr.md) in the area', ticket)
        self.assertIn('An accepted ADR that looks outdated is flagged to the orchestrator, not silently followed',
                      ticket)
        self.assertIn('A change that contradicts an accepted ADR', prose('skills/review/method.md'))
        self.assertIn('a conflict with an accepted [ADR](../domain/adr.md)', prose('runtime/workers/design-hold.md'))

    def test_no_doc_names_matts_domain_modeling(self):
        found = subprocess.run(
            ['git', 'grep', '-n', '-I', 'domain-modeling', '--', '.', ':!journals', ':!tests/test_adrs.py'],
            cwd=ROOT, capture_output=True, text=True).stdout
        self.assertEqual('', found)


if __name__ == '__main__':
    unittest.main()
