#!/usr/bin/env python3
"""The plugin installs and runs on its own: no manifest, doc or test depends on an external skill package."""
import json
import re
import subprocess
import unittest

import support

ROOT = support.ROOT
# Journals and accepted decisions are history: they may say where a method came from.
HISTORY = ('journals/', 'docs/adr/')
EXTERNAL = re.compile(r'mattpocock|\bmatt\b', re.IGNORECASE)


def prose(path):
    return ' '.join((ROOT / path).read_text().split())


def files():
    listed = subprocess.run(['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'],
                            cwd=ROOT, capture_output=True, text=True, check=True).stdout
    return [name for name in listed.split('\0') if name and (ROOT / name).is_file()]


class Standalone(unittest.TestCase):
    def test_no_file_outside_history_names_the_external_package(self):
        found = []
        for name in files():
            if name.startswith(HISTORY) or name == 'tests/test_standalone.py':
                continue
            try:
                text = (ROOT / name).read_text()
            except UnicodeDecodeError:
                continue
            found += [f'{name}:{number}' for number, line in enumerate(text.splitlines(), 1) if EXTERNAL.search(line)]
        self.assertEqual(found, [])

    def test_the_manifests_declare_no_dependency(self):
        claude = json.loads((ROOT / '.claude-plugin/plugin.json').read_text())
        marketplace = json.loads((ROOT / '.claude-plugin/marketplace.json').read_text())
        portable = json.loads((ROOT / 'plugin.json').read_text())
        self.assertNotIn('dependencies', claude)
        self.assertNotIn('allowCrossMarketplaceDependenciesOn', marketplace)
        for manifest in (claude, portable):
            self.assertEqual(manifest['description'], claude['description'])
            self.assertNotIn('on top of', manifest['description'])

    def test_no_session_or_launch_doc_resolves_an_external_package(self):
        for path in ('bootstrap.md', 'runtime/workers/before-launch.md', 'hosts/claude/session.md',
                     'hosts/codex/session.md', 'hosts/pi/session.md', 'hosts/opencode/session.md',
                     'docs/installation.md'):
            with self.subTest(path=path):
                text = prose(path)
                self.assertNotRegex(text, r'(?i)dependency identity|dependency skills|resolve (?:a |its )?dependenc'
                                          r'|plugin dependency|skill dependency')

    def test_the_pipeline_map_names_our_methods_underneath(self):
        text = (ROOT / 'skills/brief/pipeline.md').read_text()
        section = re.search(r'^## Our methods underneath\n(.+?)^## ', text, re.M | re.S).group(1)
        for link in ('../../standards/tdd.md', '../../standards/design.md', '../../runtime/board/slicing.md',
                     '../../runtime/research/research.md', '../../runtime/diagnose/diagnose.md',
                     '../align/jobs/prototype.md', '../review/method.md'):
            with self.subTest(link=link):
                self.assertIn(f']({link})', section)
        self.assertIn('- [Our methods underneath](#our-methods-underneath)', text)


if __name__ == '__main__':
    unittest.main()
