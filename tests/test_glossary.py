#!/usr/bin/env python3
"""Domain terms settle into the repository's GLOSSARY.md, and every phase uses them."""
import subprocess
import unittest

import support

ROOT = support.ROOT
GLOSSARY = ROOT / 'runtime/domain/glossary.md'


def prose(path):
    return ' '.join((ROOT / path).read_text().split())


class Glossary(unittest.TestCase):
    def test_the_glossary_doc_states_the_format_and_upkeep(self):
        text = prose(GLOSSARY)
        for rule in ('`GLOSSARY.md` at the repository root',
                     '`GLOSSARY-MAP.md` at the root lists the contexts, where each glossary lives and how the contexts relate',
                     '`_Avoid_:`', 'one or two sentences saying what the term is, not what it does',
                     'Only terms specific to this domain', 'no implementation detail',
                     'Create it lazily, when the first term settles',
                     'update it the moment a term settles, never in a batch',
                     "A project's existing glossary convention wins"):
            self.assertIn(rule, text)

    def test_each_phase_writes_or_reads_the_glossary_for_its_part(self):
        link = '](../domain/glossary.md)'
        self.assertIn('add the term to the [glossary' + link + ' the moment it settles',
                      prose('runtime/interview/grilling.md'))
        self.assertIn('[glossary' + link, prose('runtime/interview/authority.md'))
        self.assertIn('[glossary' + link, prose('runtime/interview/record.md'))
        self.assertIn("Use the glossary's terms and avoid its `_Avoid_` words", prose('runtime/explain/explain.md'))
        jobs = '](../../../runtime/domain/glossary.md)'
        for job in ('skills/dispatch/jobs/ticket.md', 'skills/review/jobs/repair.md'):
            with self.subTest(job=job):
                text = prose(job)
                self.assertIn(jobs, text)
                self.assertIn('in the same commit that introduces or changes it', text)
        self.assertIn('a term used against its glossary definition, or one of its `_Avoid_` words',
                      prose('skills/review/method.md'))
        for skill in ('skills/align/SKILL.md', 'skills/refine/SKILL.md'):
            self.assertIn('](../../runtime/domain/glossary.md)', prose(skill))

    def test_no_doc_names_the_old_glossary_file_or_matts_skill_for_terms(self):
        found = subprocess.run(
            ['git', 'grep', '-n', '-I', '-E', r'CONTEXT\.md|domain-modeling` when (needed|terminology)',
             '--', '.', ':!journals', ':!tests/test_glossary.py'],
            cwd=ROOT, capture_output=True, text=True).stdout
        self.assertEqual('', found)


if __name__ == '__main__':
    unittest.main()
