#!/usr/bin/env python3
"""huh re-pitches what lost the user; the shared explain doc replaces the show-me addon."""
import subprocess
import unittest

import support

ROOT = support.ROOT
HUH = ROOT / 'skills/huh/SKILL.md'
EXPLAIN = ROOT / 'runtime/explain/explain.md'


class Huh(unittest.TestCase):
    def test_huh_is_a_short_manual_command_over_the_explain_doc(self):
        text = HUH.read_text()
        self.assertIn('disable-model-invocation: true', text)
        first_read = next(line for line in text.splitlines() if line.startswith('First read:'))
        self.assertIn('](../../runtime/explain/explain.md)', first_read)
        # A re-pitch launches nothing, so it skips the session bootstrap, and a short trigger keeps the answer short.
        self.assertNotIn('bootstrap', text)
        self.assertLess(len(text.encode()), 1500)

    def test_the_explain_doc_starts_from_what_the_reader_missed(self):
        text = EXPLAIN.read_text()
        for phrase in ('missing context first', 'text picture', 'ticket or decision ID',
                       'only when the user asks'):
            self.assertIn(phrase, text)

    def test_every_explaining_command_reads_the_explain_doc(self):
        for name in ('skills/brief/SKILL.md', 'skills/review/walkthrough.md', 'skills/setup/tour.md'):
            self.assertIn('../../runtime/explain/explain.md', (ROOT / name).read_text(), name)

    def test_no_show_me_dependency_remains(self):
        self.assertFalse((ROOT / 'addons').exists())
        tracked = subprocess.run(['git', 'grep', '-l', '-i', 'show-me', '--', '.', ':!tests/test_huh.py'],
                                 cwd=ROOT, capture_output=True, text=True).stdout.split()
        self.assertEqual(tracked, [])


if __name__ == '__main__':
    unittest.main()
