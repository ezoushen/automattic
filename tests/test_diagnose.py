#!/usr/bin/env python3
"""Diagnosis builds a failing loop before any theory, under the plugin's own procedure."""
import unittest

import support

ROOT = support.ROOT
DOC = 'runtime/diagnose/diagnose.md'


def prose(path):
    return ' '.join((ROOT / path).read_text().split())


class Diagnose(unittest.TestCase):
    def test_the_diagnose_doc_states_each_rule(self):
        text = prose(DOC).lower()
        for rule in ('build one fast, repeatable command that fails on this bug, before any theory',
                     'shrink it to the smallest case that still fails',
                     'rank 3–5 falsifiable hypotheses before testing any',
                     'the failing case is kept as the regression test',
                     'redact every secret before showing a command, its output or a captured artifact',
                     "ask the user before touching their devices",
                     'diagnose only, never repair',
                     'one reproducer per finding'):
            with self.subTest(rule=rule):
                self.assertIn(rule, text)

    def test_the_diagnose_doc_names_no_language_specific_tooling(self):
        text = prose(DOC).lower()
        for tool in ('pytest', 'jest', 'playwright', 'puppeteer', 'curl', 'npm', 'git bisect', 'performance.now'):
            with self.subTest(tool=tool):
                self.assertNotIn(tool, text)

    def test_the_reproduce_job_and_the_blocked_ticket_step_use_it(self):
        for path, link in (('skills/review/jobs/reproduce.md', '../../../runtime/diagnose/diagnose.md'),
                           ('skills/dispatch/iteration.md', '../../runtime/diagnose/diagnose.md')):
            with self.subTest(path=path):
                text = prose(path)
                self.assertIn(f']({link})', text)
                self.assertNotIn('diagnosing-bugs', text)
        self.assertIn('diagnose defects under [diagnosis](../../runtime/diagnose/diagnose.md)',
                      prose('skills/dispatch/iteration.md'))


if __name__ == '__main__':
    unittest.main()
