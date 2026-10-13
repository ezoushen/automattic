#!/usr/bin/env python3
"""The Agent PreToolUse hook requires an explicit model unless the subagent definition pins one."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HOOK = Path(__file__).resolve().parents[1] / 'hooks' / 'agent-model.py'


class AgentModelHook(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.cwd = self.home / 'project'
        (self.cwd / '.claude/agents').mkdir(parents=True)
        (self.home / '.claude/agents').mkdir(parents=True)

    def agent(self, directory, name, model=None):
        front = f'model: {model}\n' if model else ''
        (directory / f'{name}.md').write_text(f'---\nname: {name}\n{front}---\nBody\n')

    def run_hook(self, tool_input, tool='Agent', env=None):
        payload = {'hook_event_name': 'PreToolUse', 'tool_name': tool, 'tool_input': tool_input,
                   'cwd': str(self.cwd)}
        result = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(payload), capture_output=True,
                                text=True, env=dict(os.environ, HOME=str(self.home), **(env or {})), timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)['hookSpecificOutput'] if result.stdout.strip() else None

    def test_explicit_model_is_allowed(self):
        self.assertIsNone(self.run_hook({'subagent_type': 'general-purpose', 'model': 'sonnet', 'prompt': 'x'}))

    def test_helper_without_model_is_denied_with_guidance(self):
        for subagent in ('general-purpose', 'Explore', 'Plan', None):
            with self.subTest(subagent=subagent):
                tool_input = {'prompt': 'x'} if subagent is None else {'subagent_type': subagent, 'prompt': 'x'}
                decision = self.run_hook(tool_input)
                self.assertEqual(decision['permissionDecision'], 'deny')
                for word in ('model', 'haiku', 'sonnet', 'opus'):
                    self.assertIn(word, decision['permissionDecisionReason'])

    def test_legacy_task_tool_name_is_checked_too(self):
        self.assertEqual(self.run_hook({'subagent_type': 'Explore'}, tool='Task')['permissionDecision'], 'deny')
        self.assertIsNone(self.run_hook({'command': 'ls'}, tool='Bash'))

    def test_fork_and_definitions_that_pin_a_model_are_allowed(self):
        self.agent(self.home / '.claude/agents', 'automattic-implementer-0123456789ab', 'sonnet')
        self.agent(self.cwd / '.claude/agents', 'project-reviewer', 'opus')
        for subagent in ('fork', 'automattic-implementer-0123456789ab', 'project-reviewer'):
            with self.subTest(subagent=subagent):
                self.assertIsNone(self.run_hook({'subagent_type': subagent, 'prompt': 'role_file: /r.md'}))

    def test_inherit_or_unpinned_definition_is_denied(self):
        self.agent(self.home / '.claude/agents', 'inheriting', 'inherit')
        self.agent(self.home / '.claude/agents', 'unpinned')
        for subagent in ('inheriting', 'unpinned'):
            with self.subTest(subagent=subagent):
                self.assertEqual(self.run_hook({'subagent_type': subagent})['permissionDecision'], 'deny')

    def test_plugin_agent_definitions_are_resolved_from_the_plugin_cache(self):
        agents = self.home / '.claude/plugins/cache/market/toolkit/1.0.0/agents'
        agents.mkdir(parents=True)
        self.agent(agents, 'code-reviewer', 'sonnet')
        self.agent(agents, 'silent', None)
        self.assertIsNone(self.run_hook({'subagent_type': 'toolkit:code-reviewer'}))
        self.assertEqual(self.run_hook({'subagent_type': 'toolkit:silent'})['permissionDecision'], 'deny')

    def test_bundled_automattic_role_without_model_is_denied(self):
        self.assertEqual(self.run_hook({'subagent_type': 'automattic:implementer'})['permissionDecision'], 'deny')

    def test_automattic_role_launch_needs_its_role_file(self):
        self.agent(self.home / '.claude/agents', 'automattic-implementer-0123456789ab', 'sonnet')
        for subagent, model in (('automattic:implementer', 'sonnet'), ('automattic-implementer-0123456789ab', None)):
            with self.subTest(subagent=subagent):
                launch = {'subagent_type': subagent, 'prompt': 'Implement ticket 3.', **({'model': model} if model else {})}
                decision = self.run_hook(launch)
                self.assertEqual(decision['permissionDecision'], 'deny')
                self.assertIn('role_file', decision['permissionDecisionReason'])
                launch['prompt'] = 'role_file: /plugin/roles/implementer.md\nImplement ticket 3.'
                self.assertIsNone(self.run_hook(launch))

    def test_generated_profile_whose_tools_drifted_from_its_role_is_denied(self):
        current = 'Read, Edit, Write, Bash, Grep, Glob, Skill, SendMessage, Monitor, TaskStop'
        for name, tools in (('automattic-implementer-0123456789ab', 'Read, Edit, Write, Bash, Grep, Glob, Skill'),
                            ('automattic-implementer-ba9876543210', current)):
            (self.home / '.claude/agents' / f'{name}.md').write_text(
                f'---\nname: {name}\ndescription: "x"\ntools: "{tools}"\nmodel: "sonnet"\n---\nBody\n')
        launch = {'subagent_type': 'automattic-implementer-0123456789ab', 'prompt': 'role_file: /r.md'}
        decision = self.run_hook(launch)
        self.assertEqual(decision['permissionDecision'], 'deny')
        for word in ('Monitor', 'SendMessage', 'TaskStop', 'agent-models.py'):
            self.assertIn(word, decision['permissionDecisionReason'])
        self.assertIsNone(self.run_hook(dict(launch, subagent_type='automattic-implementer-ba9876543210')))

    def test_opt_out_and_malformed_input_never_block(self):
        self.assertIsNone(self.run_hook({'subagent_type': 'Explore'}, env={'AUTOMATTIC_AGENT_MODEL_HOOK': 'off'}))
        result = subprocess.run([sys.executable, str(HOOK)], input='not json', capture_output=True, text=True,
                                timeout=10)
        self.assertEqual((result.returncode, result.stdout), (0, ''))


if __name__ == '__main__':
    unittest.main()
