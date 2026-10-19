#!/usr/bin/env python3
"""Research reads primary sources and measures the real consumers, under the plugin's own procedure."""
import unittest

import support

ROOT = support.ROOT
DOC = 'runtime/research/research.md'


def prose(path):
    return ' '.join((ROOT / path).read_text().split())


class Research(unittest.TestCase):
    def test_the_research_doc_states_each_rule(self):
        text = prose(DOC).lower()
        for rule in ('read primary sources',
                     'cite every claim to the source that owns it',
                     'save the findings where the project already keeps such notes',
                     'run it as a background worker',
                     'measure every real consumer, not one',
                     'settle every available fact before asking the user to choose',
                     'no separate fact-checker is mandatory'):
            with self.subTest(rule=rule):
                self.assertIn(rule, text)

    def test_align_review_and_the_pipeline_map_use_it(self):
        for path, link in (('skills/align/SKILL.md', '../../runtime/research/research.md'),
                           ('skills/review/SKILL.md', '../../runtime/research/research.md'),
                           ('skills/brief/pipeline.md', '../../runtime/research/research.md')):
            with self.subTest(path=path):
                text = prose(path)
                self.assertIn(f']({link})', text)
                self.assertNotIn('mattpocock-skills:research', text)
                self.assertNotRegex(text, r"Matt(?: Pocock)?'s `research`|Use `research`")

    def test_the_pipeline_map_sends_a_defect_to_diagnosis(self):
        text = prose('skills/brief/pipeline.md')
        self.assertIn('](../../runtime/diagnose/diagnose.md)', text)
        self.assertNotIn('mattpocock-skills:diagnosing-bugs', text)


if __name__ == '__main__':
    unittest.main()
