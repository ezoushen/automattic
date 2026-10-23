#!/usr/bin/env python3
"""The standards module holds criteria only: each kind has four sections and links no job or flow."""
import re
import unittest

import support

ROOT = support.ROOT
STANDARDS = ROOT / 'standards'
KIND_SECTIONS = ['Signal', 'Proof', 'Repair', 'Not a finding']
LINK = re.compile(r'\]\(([^)\s#]+)(?:#[^)\s]*)?\)')


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

    def test_agent_docs_stay_language_neutral(self):
        extension = re.compile(r'`\.(?:py|pyi|js|jsx|mjs|cjs|ts|tsx|mts|cts|sh|bash|zsh|sql|go|rs|swift|kt|java|cs|c|cpp|h|rb|php)`')
        docs = [ROOT / 'bootstrap.md'] + [path for folder in ('skills', 'runtime', 'standards', 'agents', 'hosts')
                                          for path in sorted((ROOT / folder).rglob('*.md'))]
        for path in docs:
            with self.subTest(doc=str(path.relative_to(ROOT))):
                text = path.read_text()
                self.assertIsNone(extension.search(text))
                self.assertNotIn('comment_audit', text)
        self.assertFalse((ROOT / 'scripts/comment_audit.py').exists())

    def test_comment_detection_reads_the_diff_in_each_files_language(self):
        for name in ('skills/remediate/SKILL.md', 'skills/review/jobs/diff-review.md'):
            text = ' '.join((ROOT / name).read_text().split())
            with self.subTest(doc=name):
                self.assertIn('git diff -U0', text)
                self.assertIn("in each file's language", text)
                self.assertIn('reading each added line in its file', text)
        remediate = ' '.join((ROOT / 'skills/remediate/SKILL.md').read_text().split())
        self.assertIn('untracked files are outside the diff', remediate)

    def test_a_scan_counts_its_items_and_asks_before_it_samples(self):
        # A per-item proof too large for the workers is the user's cost decision, not a silent sample.
        remediate = ' '.join((ROOT / 'skills/remediate/SKILL.md').read_text().split())
        self.assertIn("count the items the kind's Proof covers one by one", remediate)
        self.assertIn('size the audit partitions by that count', remediate)
        self.assertIn('[ask the user](../../runtime/ask/ask.md) before detection', remediate)
        self.assertIn("in place of those steps without the user's agreement", remediate)

    def test_coverage_is_counted_per_item_and_a_generated_verdict_covers_nothing(self):
        # A file can be "inventoried" while most of its tests were never read.
        remediate = ' '.join((ROOT / 'skills/remediate/SKILL.md').read_text().split())
        self.assertIn("reconcile the inventory against the workers' coverage item by item", remediate)
        self.assertIn('a test without its checklist, or a comment block not read against its code, '
                      'is uncovered, not clean', remediate)
        self.assertIn('A generated or default verdict covers nothing.', remediate)
        audit = ' '.join((ROOT / 'skills/remediate/jobs/audit.md').read_text().split())
        self.assertIn("every item the kind's Proof covers has a recorded observation", audit)
        self.assertIn('how many have a recorded observation; a generated or default verdict is not one', audit)

    def test_comment_signal_names_the_claims_that_go_stale_first(self):
        kind = ' '.join((STANDARDS / 'kinds/misleading-comments.md').read_text().split())
        signal = kind[kind.index('## Signal'):kind.index('## Proof')]
        self.assertIn('Numbers, counts and absolute words (all, every, only, never) go stale first', signal)

    def test_the_three_standards_exist(self):
        for name in ('code-comments.md', 'documentation.md', 'pr.md'):
            self.assertTrue((STANDARDS / name).is_file(), name)

    def test_the_comment_rules_have_no_separate_sources_file(self):
        self.assertFalse((STANDARDS / 'code-comments-sources.md').exists())
        self.assertNotIn('code-comments-sources', (STANDARDS / 'code-comments.md').read_text())

    def test_the_comment_rules_reach_writers_and_reviewers_as_a_core_skill_not_a_skill_folder(self):
        import agent_defs
        agents = agent_defs.load(ROOT)['agents']
        for name in ('builder', 'reviewer'):
            self.assertIn('standards/code-comments.md', agents[name]['core_skills'], name)
        self.assertFalse((ROOT / 'skills/code-comments').exists())

    def test_housekeeping_points_at_the_documentation_standard(self):
        skill = (ROOT / 'skills/housekeeping/SKILL.md').read_text()
        self.assertIn('](../../standards/documentation.md)', skill)
        self.assertNotIn('A dated correction appended below stale guidance', skill)


if __name__ == '__main__':
    unittest.main()
