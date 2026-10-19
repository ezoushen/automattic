#!/usr/bin/env python3
"""Every question to the user carries the context needed to answer it, as /huh's re-pitch does."""
import unittest

import support

ROOT = support.ROOT


def prose(path):
    return ' '.join((ROOT / path).read_text().split())


class QuestionContext(unittest.TestCase):
    def test_explain_owns_asking_with_context(self):
        section = prose('runtime/explain/ask.md')
        for rule in ('Every question to the user, and every decision listed for them',
                     'start at the first fact they may not know',
                     'state an earlier decision by its content',
                     'define an internal name where it first appears',
                     'never a ticket or decision ID in place of what it means',
                     'answer without asking what the question refers to'):
            self.assertIn(rule, section)
        self.assertIn('[ask with context](ask.md)', prose('runtime/explain/explain.md'))
        self.assertIn('](explain.md#re-pitch-what-lost-the-reader)', section)

    def test_every_place_that_asks_the_user_applies_it(self):
        for path, link in (('runtime/interview/question-filter.md', '../explain/ask.md'),
                           ('runtime/interview/record.md', '../explain/ask.md'),
                           ('runtime/workers/design-hold.md', '../explain/ask.md'),
                           ('skills/dispatch/iteration.md', '../../runtime/explain/ask.md'),
                           ('skills/dispatch/handoff.md', '../../runtime/explain/ask.md'),
                           ('skills/review/coverage.md', '../../runtime/explain/ask.md')):
            with self.subTest(path=path):
                self.assertIn(f']({link})', prose(path))
        iteration = prose('skills/dispatch/iteration.md')
        self.assertIn('send the user one request covering all of them, [with context](../../runtime/explain/ask.md)', iteration)


if __name__ == '__main__':
    unittest.main()
