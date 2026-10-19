#!/usr/bin/env python3
"""Our grilling asks the user about principles; the agent decides implementation detail."""
import subprocess
import unittest

import support

ROOT = support.ROOT
GRILLING = ROOT / 'runtime/interview/grilling.md'


def prose(path):
    return ' '.join(path.read_text().split())


class Grilling(unittest.TestCase):
    def test_the_tree_is_worked_principles_first_in_small_rounds(self):
        text = prose(GRILLING)
        for rule in ('Map the plan as a design tree', 'A question waits until the decisions it depends on are settled',
                     'goal and principles, then what may change or must keep working, then the behavior the user would notice',
                     '[question filter](question-filter.md)', 'one or two questions per round',
                     'a recommendation that "yes" accepts',
                     'Finding facts is the agent\'s job', 'without blocking the questions that do not depend on them',
                     'until the user confirms a shared understanding'):
            self.assertIn(rule, text)

    def test_implementation_detail_is_decided_by_the_agent_at_every_depth(self):
        text = prose(GRILLING)
        for rule in ('Never ask the user about implementation detail',
                     'decide it within the principles, record it in the ledger',
                     "list it among the agent's decisions the user may veto",
                     'Exhaustive depth, on an explicit request, only raises the number of questions per round'):
            self.assertIn(rule, text)
        align = prose(ROOT / 'skills/align/SKILL.md')
        self.assertNotIn('relax the round', align)
        self.assertNotIn('question-count/detail limit', align)

    def test_every_entry_point_uses_our_grilling(self):
        self.assertIn('[grilling](../../runtime/interview/grilling.md)', prose(ROOT / 'skills/align/SKILL.md'))
        self.assertIn('[grilling](runtime/interview/grilling.md)', prose(ROOT / 'bootstrap.md'))
        self.assertIn('[grilling](../../runtime/interview/grilling.md)', prose(ROOT / 'skills/brief/pipeline.md'))

    def test_no_doc_names_matts_grilling(self):
        found = subprocess.run(
            ['git', 'grep', '-n', '-I', '-E', r'mattpocock-skills:grilling|exhaustive interview|exhaustive frontier|'
             r"grilling's internal|Matt's .*grilling", '--', '.', ':!journals', ':!tests/test_grilling.py'],
            cwd=ROOT, capture_output=True, text=True).stdout
        self.assertEqual('', found)


if __name__ == '__main__':
    unittest.main()
