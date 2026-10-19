#!/usr/bin/env python3
"""A throwaway prototype answers one design question and records its verdict, under align's own job."""
import unittest

import support
import agent_defs

ROOT = support.ROOT
JOB = 'skills/align/jobs/prototype.md'


def prose(path):
    return ' '.join((ROOT / path).read_text().split())


class Prototype(unittest.TestCase):
    def test_the_job_names_its_agent_inputs_finish_line_and_return(self):
        job = agent_defs.load(ROOT)['jobs']['prototype']
        self.assertEqual(job['agent'], 'builder')
        self.assertEqual(job['inputs'], ['question', 'worktree', 'branch', 'report'])
        self.assertEqual(job['returns'], ['## Verdict'])
        text = prose(JOB)
        for heading in ('## Inputs', '## Finish line', '## Return'):
            self.assertIn(heading, text)

    def test_the_job_states_each_rule(self):
        text = prose(JOB).lower()
        for rule in ('throwaway code that answers one question',
                     'does the logic hold, or what should it look like',
                     'clearly marked as a prototype',
                     'trivial to run',
                     'no persistence',
                     'commit it only to the throwaway branch',
                     'the verdict and the question it settled go to the ledger',
                     'when it qualifies, an adr'):
            with self.subTest(rule=rule):
                self.assertIn(rule, text)

    def test_the_job_is_language_neutral(self):
        text = prose(JOB).lower()
        for tool in ('pnpm', 'npm', 'bun ', 'python ', 'html file', 'url search param'):
            with self.subTest(tool=tool):
                self.assertNotIn(tool, text)

    def test_align_and_the_pipeline_map_use_the_job(self):
        for path, link in (('skills/align/SKILL.md', 'jobs/prototype.md'),
                           ('skills/brief/pipeline.md', '../align/jobs/prototype.md')):
            with self.subTest(path=path):
                text = prose(path)
                self.assertIn(f']({link})', text)
                self.assertNotIn('mattpocock-skills:prototype', text)
                self.assertNotRegex(text, r"Matt(?: Pocock)?'s `prototype`")


if __name__ == '__main__':
    unittest.main()
