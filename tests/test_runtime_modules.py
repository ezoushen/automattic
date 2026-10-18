#!/usr/bin/env python3
"""The runtime holds six modules in a fixed order; its docs link only down, and the skills over them stay thin."""
import re
import unittest

import support

ROOT = support.ROOT
RUNTIME = ROOT / 'runtime'
ORDER = ['workers', 'checks', 'routing', 'resources', 'decisions', 'config']
LINK = re.compile(r'\]\(([^)\s#]+)(?:#[^)\s]*)?\)')


class RuntimeModules(unittest.TestCase):
    def test_the_runtime_folder_holds_exactly_the_six_modules(self):
        self.assertEqual(sorted(path.name for path in RUNTIME.iterdir()), sorted(ORDER))

    def test_the_old_runtime_folders_are_gone(self):
        for old in ('workers', 'routing', 'decisions', 'checks'):
            self.assertFalse((ROOT / 'harnesses' / old).exists(), old)

    def test_a_runtime_doc_links_only_its_own_or_a_later_module(self):
        for path in sorted(RUNTIME.rglob('*.md')):
            own = ORDER.index(path.relative_to(RUNTIME).parts[0])
            for target in LINK.findall(path.read_text()):
                if re.match(r'[a-z]+:', target):
                    continue
                with self.subTest(doc=str(path.relative_to(ROOT)), target=target):
                    resolved = (path.parent / target).resolve().relative_to(ROOT)
                    self.assertNotIn(resolved.parts[0], {'skills', 'flows', 'agents', 'standards', 'hosts',
                                                         'harnesses', 'bootstrap.md', 'addons'})
                    if resolved.parts[0] == 'runtime':
                        self.assertGreaterEqual(ORDER.index(resolved.parts[1]), own)

    def test_recovery_joins_the_workers_and_the_configuration_format_joins_config(self):
        for name in ('workers/recovery.md', 'config/catalog.md', 'config/routers.md', 'config/session.md',
                     'config/executors.md', 'resources/resources.md', 'resources/retire-worktree.md'):
            self.assertTrue((RUNTIME / name).is_file(), name)
        for name in ('procedure.md', 'apply.md', 'reset-and-validate.md', 'troubleshooting.md',
                     'legacy-preferences.md'):
            self.assertTrue((ROOT / 'flows/setup' / name).is_file(), name)

    def test_the_decision_and_routing_skills_are_thin_entries_over_runtime(self):
        for skill, target in (('decision', 'runtime/decisions/workflow.md'),
                              ('model-routing', 'runtime/routing/select.md')):
            text = (ROOT / 'skills' / skill / 'SKILL.md').read_text()
            self.assertIn(f'](../../{target})', text)
            self.assertLess(len(text), 900, skill)
            self.assertTrue((ROOT / target).is_file(), target)

    def test_housekeeping_keeps_a_pointer_to_worktree_retirement(self):
        text = (ROOT / 'flows/delivery/housekeeping.md').read_text()
        self.assertIn('## Retire a worktree\n\nFollow [worktree retirement](../../runtime/resources/retire-worktree.md).', text)
        self.assertNotIn('git -C <checkout> status --porcelain --ignored', text)
        self.assertIn('git -C <checkout> status --porcelain --ignored', (RUNTIME / 'resources/retire-worktree.md').read_text())


if __name__ == '__main__':
    unittest.main()
