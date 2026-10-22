#!/usr/bin/env python3
"""Codex reads agents/openai.yaml, not the SKILL.md flag Claude Code, Pi and OpenCode read, so a skill reserved for the
user must say so in both places and a model-invocable one must say so in neither."""
import re
import unittest

import support

SKILLS = support.ROOT / 'skills'
# The phase skills the user types; a worker never invokes them on its own.
RESERVED = {'align', 'autopilot', 'brief', 'dispatch', 'huh', 'pr', 'refine', 'remediate', 'review', 'setup'}


def reserved_by_skill_file(skill):
    header = skill.read_text().split('---', 2)[1]
    return bool(re.search(r'^disable-model-invocation: true$', header, re.M))


class SkillInvocation(unittest.TestCase):
    def test_the_reserved_skills_are_the_ones_the_user_types(self):
        # Rule: both host controls are derived from this list below, so pin it from outside the files.
        found = {skill.parent.name for skill in SKILLS.glob('*/SKILL.md') if reserved_by_skill_file(skill)}
        self.assertEqual(found, RESERVED)

    def test_codex_allows_implicit_invocation_exactly_where_the_skill_file_does(self):
        # Rule: every skill has agents/openai.yaml; `false` where SKILL.md sets disable-model-invocation, else `true`.
        for skill in sorted(SKILLS.glob('*/SKILL.md')):
            name = skill.parent.name
            with self.subTest(skill=name):
                policy = skill.parent / 'agents/openai.yaml'
                self.assertTrue(policy.is_file(), f'{name} has no agents/openai.yaml')
                found = re.search(r'^policy:\n  allow_implicit_invocation: (\w+)$', policy.read_text(), re.M)
                self.assertIsNotNone(found, f'{name}: no policy.allow_implicit_invocation')
                self.assertEqual(found.group(1), 'false' if reserved_by_skill_file(skill) else 'true')


if __name__ == '__main__':
    unittest.main()
