#!/usr/bin/env python3
"""Agents share one language-neutral module-design vocabulary from our own standard, not Matt's codebase-design."""
import re
import subprocess
import unittest

import support

ROOT = support.ROOT
DESIGN = ROOT / 'standards/design.md'


def prose(path):
    return ' '.join(path.read_text().split())


class DesignStandard(unittest.TestCase):
    def test_each_term_has_a_definition(self):
        text = prose(DESIGN)
        for term, meaning in (
                ('Module', 'anything with an interface and an implementation'),
                ('Interface', 'everything a caller must know to use the module correctly'),
                ('Implementation', 'what is inside the module, behind its interface'),
                ('Depth', 'how much behavior a caller or test can exercise per unit of interface it must learn'),
                ('Seam', 'a place where behavior can be changed without editing that place'),
                ('Adapter', 'a concrete thing that satisfies an interface at a seam'),
                ('Leverage', 'what callers gain from depth'),
                ('Locality', 'what maintainers gain from depth')):
            with self.subTest(term=term):
                self.assertIn(f'**{term}:** {meaning}', text)

    def test_the_interface_covers_more_than_its_operations(self):
        self.assertIn('invariants, ordering constraints, error modes, required configuration and performance limits',
                      prose(DESIGN))

    def test_the_deletion_test_tells_a_pass_through_from_a_module_that_earns_its_place(self):
        text = prose(DESIGN)
        self.assertIn('**The deletion test.** Imagine deleting the module.', text)
        self.assertIn('If its complexity vanishes, it was a pass-through', text)
        self.assertIn('if the complexity reappears across its callers, it earns its place', text)

    def test_a_seam_needs_two_adapters(self):
        text = prose(DESIGN)
        self.assertIn('**One adapter is a hypothetical seam, two a real one.**', text)
        self.assertIn('a seam with one adapter is only indirection', text)

    def test_tests_cross_the_interface_callers_use(self):
        text = prose(DESIGN)
        self.assertIn('**The interface is the test surface.**', text)
        self.assertIn('Tests cross the same seam as callers and assert what is observable there, not internal state',
                      text)
        self.assertIn('a test that must reach past the interface means the module has the wrong shape', text)

    def test_the_standard_has_no_code_in_any_language(self):
        text = DESIGN.read_text()
        self.assertNotIn('```', text)
        self.assertIsNone(re.search(r'`[^`]*[(){};=][^`]*`', text), 'inline code sample')

    def test_align_designs_with_our_standard(self):
        align = prose(ROOT / 'skills/align/SKILL.md')
        self.assertIn('[module design](../../standards/design.md)', align)
        self.assertIn('[module design](../../standards/design.md)', prose(ROOT / 'skills/review/SKILL.md'))

    def test_no_doc_names_matts_codebase_design(self):
        found = subprocess.run(
            ['git', 'grep', '-n', '-I', 'codebase-design', '--', '.', ':!journals', ':!tests/test_design_standard.py'],
            cwd=ROOT, capture_output=True, text=True)
        self.assertIn(found.returncode, (0, 1), found.stderr)
        self.assertEqual('', found.stdout)


if __name__ == '__main__':
    unittest.main()
