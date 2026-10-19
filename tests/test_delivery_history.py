#!/usr/bin/env python3
"""Delivering an effort turns its lasting ledger decisions into ADRs whose numbers never collide on main."""
import unittest

import support

ROOT = support.ROOT


def prose(path):
    return ' '.join((ROOT / path).read_text().split())


class DeliveryHistory(unittest.TestCase):
    def test_the_adr_doc_says_how_an_effort_delivers_its_decisions(self):
        text = prose('runtime/domain/adr.md')
        for rule in ('list each ledger row that qualifies as a candidate ADR',
                     'write only the candidates the user approves into the effort branch',
                     'before its review head is pinned',
                     'Do not wait for the answer',
                     'candidates still unanswered wait among the actions only the user can take',
                     'an approved candidate written later returns that change to review and E2E',
                     'merge the verified `main` tip into the effort branch and run the ADR number check',
                     'renumber the effort\'s ADR to the next free number and update every reference to it',
                     'scripts/adr_numbers.py --repo <repo> --ref <effort branch> --against <main tip>',
                     'Fetch first', "each `main` the effort lands on: the local one and, once fetched, the remote's",
                     'Commit the approved ADRs before the check',
                     'Run it once for each ADR folder', 'checks only `NNNN-slug.md` names',
                     'records an evidenced skip', 'A merge or renumbering after the review head is pinned returns to review and E2E',
                     'a duplicate number fails the delivery gate'):
            self.assertIn(rule, text)

    def test_each_delivery_step_applies_it(self):
        link = '../../runtime/domain/adr.md#deliver-an-efforts-decisions'
        handoff = prose('skills/dispatch/handoff.md')
        self.assertIn(f'candidate ADRs]({link})', handoff)
        self.assertLess(handoff.index('candidate ADRs]'), handoff.index('before pinning the review head'))
        before_pin = handoff[:handoff.index('before pinning the review head')]
        self.assertIn('commit the approved ones', before_pin)
        self.assertLess(before_pin.index('commit the approved ones'), before_pin.index('run the ADR number check'))
        self.assertIn('the ADRs the effort adds', prose('skills/pr/SKILL.md'))
        board = prose('runtime/board/board.md')
        self.assertIn('[ADR number check](../domain/adr.md#deliver-an-efforts-decisions) passes on the effort branch',
                      board)
        self.assertIn('its delivery report lists the candidate ADRs', prose('skills/dispatch/modes.md'))


if __name__ == '__main__':
    unittest.main()
