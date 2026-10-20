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
# The package's skill names in its known releases, except those named by a plain word (research, tdd, handoff and
# the like).
SKILLS = ('ask-matt', 'chief-of-staff', 'claude-handoff', 'codebase-design', 'diagnosing-bugs', 'domain-modeling',
          'git-guardrails-claude-code', 'grill-me', 'grill-with-docs', 'implement-spec',
          'improve-codebase-architecture', 'loop-me', 'migrate-to-shoehorn', 'resolving-merge-conflicts',
          'scaffold-exercises', 'setup-pre-commit', 'setup-ts-deep-modules', 'to-prd', 'to-questionnaire', 'to-spec',
          'to-tickets', 'wait-what', 'wayfinder', 'writing-beats', 'writing-for-agents', 'writing-fragments',
          'writing-shape')
EXTERNAL = re.compile(r'mattpocock|(?<![a-z])matt(?![a-z])|pocock|(?<![\w-])(?:%s)(?![\w-])' % '|'.join(map(re.escape, SKILLS)),
                      re.IGNORECASE)


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

    def test_the_guard_catches_the_name_inside_an_identifier_but_not_inside_a_word(self):
        self.assertIsNotNone(EXTERNAL.search('def test_matt_skills(self):'))
        self.assertIsNotNone(EXTERNAL.search('MATT_SKILLS = 1'))
        self.assertIsNone(EXTERNAL.search('the output format matters'))

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
        for path in ('bootstrap.md', 'runtime/workers/before-launch.md', 'runtime/workers/README.md',
                     'runtime/resources/capacity.md', 'hosts/claude/session.md', 'hosts/codex/session.md',
                     'hosts/pi/session.md', 'hosts/opencode/session.md', 'docs/installation.md'):
            with self.subTest(path=path):
                text = prose(path)
                self.assertNotRegex(text, r'(?i)dependency identity|dependency skills|resolve [^.]{0,40}dependenc'
                                          r'|plugin dependency|skill dependency')

    def test_a_situational_skill_keeps_its_invocation_policy(self):
        self.assertIn("Honor each skill's invocation policy in the host's catalog: never read a skill's body to get "
                      "around an invocation that is denied or reserved for the user.", prose('runtime/workers/skills.md'))

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
