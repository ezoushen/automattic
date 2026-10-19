#!/usr/bin/env python3
"""huh re-pitches what lost the user; the shared explain doc replaces the show-me addon."""
import subprocess
import unittest

import support

ROOT = support.ROOT
HUH = ROOT / 'skills/huh/SKILL.md'
EXPLAIN = ROOT / 'runtime/explain/explain.md'


def prose(path):
    return ' '.join(path.read_text().split())


class Huh(unittest.TestCase):
    def test_huh_is_a_short_manual_command_over_the_explain_doc(self):
        text = prose(HUH)
        self.assertIn('disable-model-invocation: true', text)
        first_read = next(line for line in HUH.read_text().splitlines() if line.startswith('First read:'))
        self.assertIn('](../../runtime/explain/explain.md)', first_read)
        # A re-pitch launches nothing, so it overrides the session hook's read-the-bootstrap hint, and a short
        # trigger keeps the answer short.
        self.assertIn('Skip the runtime bootstrap and the host session part', text)
        self.assertLess(len(text.encode()), 1500)

    def test_the_explain_doc_starts_from_what_the_reader_missed(self):
        text = prose(EXPLAIN)
        for phrase in ('missing context first', 'no longer than the message it replaces', 'ticket or decision ID',
                       'only when the user asks'):
            self.assertIn(phrase, text)

    def test_the_explain_doc_keeps_every_view_and_draws_text_where_diagrams_do_not_render(self):
        text = prose(EXPLAIN)
        for view in ('pseudocode', 'call tree', 'component tree', 'file tree', 'sequence', '`diff`', 'whole block',
                     'hide ownership or order', 'real labels and data', 'desktop and mobile', 'preview'):
            self.assertIn(view, text)
        self.assertIn('Draw with text pictures by default', text)
        self.assertIn("only where the reader's surface renders it", text)

    def test_the_pipeline_map_names_huh(self):
        self.assertIn('`/automattic:huh`', (ROOT / 'skills/brief/pipeline.md').read_text())

    def test_every_explaining_command_reads_the_explain_doc(self):
        for name in ('skills/brief/SKILL.md', 'skills/review/walkthrough.md', 'skills/setup/tour.md'):
            self.assertIn('../../runtime/explain/explain.md', (ROOT / name).read_text(), name)

    def test_no_show_me_dependency_remains(self):
        self.assertFalse((ROOT / 'addons').exists())
        scan = subprocess.run(['git', 'grep', '-l', '-i', '-e', 'show-me', '-e', 'addons/', '--', '.',
                               ':!tests/test_huh.py', ':!tests/test_pi_adapter.mjs'],
                              cwd=ROOT, capture_output=True, text=True)
        # git grep exits 1 for no match; any other code is a failed scan, not a clean one.
        self.assertEqual((scan.returncode, scan.stdout), (1, ''), scan.stderr)


if __name__ == '__main__':
    unittest.main()
