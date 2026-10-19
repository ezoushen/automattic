#!/usr/bin/env python3
"""Tickets are cut by one slicing doc of our own, which refine and dispatch's split step both read."""
import unittest

import support

ROOT = support.ROOT
SLICING = ROOT / 'runtime/board/slicing.md'


def prose(path):
    return ' '.join(path.read_text().split())


class Slicing(unittest.TestCase):
    def test_the_slicing_doc_states_each_rule(self):
        text = prose(SLICING)
        for rule in ('Cut thin end-to-end slices', 'each verifiable on its own',
                     'sized for one fresh context window',
                     'Preparatory refactors come first',
                     'expand → migrate in batches → contract',
                     'Batches that cannot stay green alone share the effort branch and end in the spec E2E',
                     'Each ticket lists what blocks it',
                     'Weigh handoff cost before splitting adjacent outcomes',
                     'Separate the experiment that decides value from the automation that depends on it, and run it first',
                     'put a baseline using existing tools first, then a representative trial before wider application',
                     'Define the metric, comparable workload conditions and success criterion',
                     'keep a supported no-change outcome when the change adds no value',
                     'the later work is blocked by it and stays deferred scope until the result is accepted',
                     'Tickets sharing a device, serving lane or mutable fixture share a reservation',
                     'A cross-effort edge waits for the prerequisite effort to finish and merge into main'):
            with self.subTest(rule=rule):
                self.assertIn(rule, text)
        for rule in ('Preparatory refactors and wide mechanical changes are the exceptions to end-to-end slices',
                     'Expand, each migrate batch and contract are tickets',
                     'each batch is blocked by expand and contract is blocked by every batch',
                     'batches sized by blast radius'):
            with self.subTest(rule=rule):
                self.assertIn(rule, text)
        self.assertIn('[Slicing tickets](slicing.md)', prose(ROOT / 'runtime/board/board.md'))

    def test_refine_split_work_and_the_map_read_the_doc_not_matts(self):
        readers = {'skills/refine/SKILL.md': '](../../runtime/board/slicing.md)',
                   'skills/dispatch/split-work.md': '](../../runtime/board/slicing.md)',
                   'skills/brief/pipeline.md': '](../../runtime/board/slicing.md)'}
        for name, link in readers.items():
            text = prose(ROOT / name)
            with self.subTest(doc=name):
                self.assertIn(link, text)
                for gone in ('mattpocock-skills:to-tickets', 'mattpocock-skills:to-spec', 'spec.md'):
                    self.assertNotIn(gone, text)
        self.assertNotIn('](../refine/', prose(ROOT / 'skills/dispatch/split-work.md'))
        refine = prose(ROOT / 'skills/refine/SKILL.md')
        self.assertIn("Dispatch's split step cuts already-selected work by the same slicing rules", refine)
        self.assertNotIn('Dispatch also uses it to split', refine)
        self.assertLess(len((ROOT / 'skills/refine/SKILL.md').read_bytes()), 12 * 1024)

    def test_a_split_child_meets_the_bar_a_refined_ticket_meets(self):
        text = prose(ROOT / 'skills/dispatch/split-work.md')
        for rule in ('Each child meets the bar a refined ticket meets',
                     'a `Verify` line naming the command or test and who observes it (`code`, `agent` or `user`)',
                     'a check that cannot pass while the criterion is broken',
                     'normal variation cannot swamp',
                     'An edge the parent\'s brief does not settle is a ledger row with a hinge',
                     '[`refinement` checkpoint](../../runtime/decisions/checkpoint-command.md)',
                     'a builder with an empty context can build it',
                     '`ticket`, `status`, `blocked_by` (always present, `[]` when nothing gates it), `touches`, `devices`, `model` and `worker`',
                     'next_tickets.py" --repo "<repo>" <slug> --check'):
            with self.subTest(rule=rule):
                self.assertIn(rule, text)


if __name__ == '__main__':
    unittest.main()
