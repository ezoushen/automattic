#!/usr/bin/env python3
"""The standards module holds criteria only: each kind has four sections and links no job or flow."""
import re
import unittest

import support

ROOT = support.ROOT
STANDARDS = ROOT / 'standards'
KIND_SECTIONS = ['Signal', 'Proof', 'Repair', 'Not a finding']
LINK = re.compile(r'\]\(([^)\s#]+)(?:#[^)\s]*)?\)')
CODE_COMMENTS_DESCRIPTION = ('description: "Write code comments and API docs when adding or changing source '
                             'documentation, or when behavior changes its contract. Not PR review comments."')


class Standards(unittest.TestCase):
    def kinds(self):
        return sorted((STANDARDS / 'kinds').glob('*.md'))

    def test_the_kinds_are_the_two_built_in_ones(self):
        self.assertEqual([path.stem for path in self.kinds()], ['misleading-comments', 'tautological-tests'])

    def test_each_kind_has_exactly_the_four_sections(self):
        for path in self.kinds():
            with self.subTest(kind=path.name):
                headings = [line[3:].strip() for line in path.read_text().splitlines() if line.startswith('## ')]
                self.assertEqual(headings, KIND_SECTIONS)

    def test_a_kind_links_no_job_or_flow(self):
        for path in self.kinds():
            for target in LINK.findall(path.read_text()):
                with self.subTest(kind=path.name, target=target):
                    resolved = (path.parent / target).resolve().relative_to(ROOT)
                    self.assertNotIn(resolved.parts[0], {'skills', 'agents', 'bootstrap.md'})
                    self.assertNotIn('jobs', resolved.parts)

    def test_the_four_standards_exist(self):
        for name in ('code-comments.md', 'code-comments-sources.md', 'documentation.md', 'pr.md'):
            self.assertTrue((STANDARDS / name).is_file(), name)

    def test_the_code_comments_skill_is_a_thin_entry_with_its_description_unchanged(self):
        skill = (ROOT / 'skills/code-comments/SKILL.md').read_text()
        self.assertIn(CODE_COMMENTS_DESCRIPTION, skill)
        self.assertIn('](../../standards/code-comments.md)', skill)
        self.assertLess(len(skill), 1200)
        self.assertFalse((ROOT / 'skills/code-comments/references').exists())

    def test_housekeeping_points_at_the_documentation_standard(self):
        skill = (ROOT / 'skills/housekeeping/SKILL.md').read_text()
        self.assertIn('](../../standards/documentation.md)', skill)
        self.assertNotIn('A dated correction appended below stale guidance', skill)


if __name__ == '__main__':
    unittest.main()
