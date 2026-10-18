#!/usr/bin/env python3
"""The README, the pipeline map and the agent-docs skill describe the layers and how to extend them."""
import re
import unittest

import support

ROOT = support.ROOT
README = (ROOT / 'README.md').read_text()
SKILL = (ROOT / '.agents/skills/writing-agent-docs/SKILL.md').read_text()
PIPELINE = (ROOT / 'skills/pipeline/SKILL.md').read_text()
TOP = ('skills', 'flows', 'runtime', 'hosts', 'standards', 'agents', 'hooks', 'scripts', 'schemas', 'addons',
       'benchmarks', 'docs', 'bootstrap.md')
# Codex runtime method names, not repository paths.
CODEX_RPC = ('skills/list', 'hooks/list')
EXTENSIONS = ('host', 'executor', 'agent', 'job', 'kind', 'standard', 'flow')


class ArchitectureDocs(unittest.TestCase):
    def test_every_repository_path_the_readme_names_exists(self):
        for name in sorted(set(re.findall(r'`((?:%s)(?:/[\w./-]*)?)`' % '|'.join(TOP), README))):
            if name in CODEX_RPC:
                continue
            with self.subTest(path=name):
                self.assertTrue((ROOT / name).exists(), name)

    def test_the_readme_has_no_retired_layout(self):
        self.assertNotIn('harnesses', README)

    def test_the_readme_layout_names_every_top_level_folder_and_the_layer_order(self):
        for name in ('flows/delivery', 'flows/review', 'flows/remediation', 'standards/', 'runtime/', 'hosts/', 'bootstrap.md'):
            self.assertIn(f'`{name}', README, name)
        self.assertIn('writing-agent-docs/SKILL.md', README)

    def test_the_readme_links_the_skill_instead_of_repeating_the_rules(self):
        self.assertIn('](.agents/skills/writing-agent-docs/SKILL.md#extend-the-architecture)', README)
        self.assertIsNone(re.search(r'\]\([^)]*journals/', README + SKILL))

    def test_the_skill_says_how_to_add_each_kind_of_module(self):
        section = SKILL.split('## Extend the architecture', 1)[1].split('\n## ', 1)[0]
        for kind in EXTENSIONS:
            self.assertRegex(section, r'(?i)\badd an? %s\b' % kind)
        for word in ('strict', 'room', 'architecture.json'):
            self.assertIn(word, section.lower())

    def test_the_skill_contents_list_the_new_section(self):
        self.assertIn('- [Extend the architecture](#extend-the-architecture)', SKILL)

    def test_the_pipeline_map_links_every_flow(self):
        for flow in sorted(path.name for path in (ROOT / 'flows').iterdir() if path.is_dir()):
            self.assertRegex(PIPELINE, r'\]\(\.\./\.\./flows/%s/' % flow, flow)

    def test_no_recorded_debt_remains(self):
        import json
        base = ROOT / '.agents/skills/writing-agent-docs'
        self.assertEqual(json.loads((base / 'config.json').read_text())['debt'], {})
        self.assertTrue(all(not value for value in json.loads((base / 'architecture.json').read_text())['debt'].values()))


if __name__ == '__main__':
    unittest.main()
