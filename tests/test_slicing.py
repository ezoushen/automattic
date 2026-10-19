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
                     'The experiment that decides value precedes the automation that depends on it',
                     'Tickets sharing a device, serving lane or mutable fixture share a reservation',
                     'A cross-effort edge waits for the prerequisite effort to finish and merge into main'):
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
        self.assertNotIn('](../refine/SKILL.md)', prose(ROOT / 'skills/dispatch/split-work.md'))
        refine = prose(ROOT / 'skills/refine/SKILL.md')
        self.assertIn("Dispatch's split step cuts already-selected work by the same slicing rules", refine)
        self.assertNotIn('Dispatch also uses it to split', refine)
        self.assertLess(len((ROOT / 'skills/refine/SKILL.md').read_bytes()), 12 * 1024)


if __name__ == '__main__':
    unittest.main()
