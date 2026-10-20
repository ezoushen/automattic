#!/usr/bin/env python3
"""A resolved route to a worker runtime carries that runtime's native launch controls for the agent's write scope.

Expected flags and native values are the verified ones in the retro's startup-controls notes, never the resolver's.
"""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import support


SCRIPT = support.script('agent_models.py')


class LaunchControls(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix='automattic launch ')
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.user = self.root / 'executors.json'
        herdr = {'type': 'skill', 'config': {'skill': 'herdr', 'instruction': 'Run one worker.'}}
        self.data = {'runtimes': {runtime: {'executors': {'herdr': herdr, runtime: {'type': 'subagent'}}}
                                  for runtime in ('claude', 'codex', 'opencode', 'pi')},
                     'models': {}, 'agents': {}}
        for name, runtime, model in (('opus', 'claude', 'claude-opus-5-5'), ('sol', 'codex', 'gpt-6.1-sol'),
                                     ('flash', 'opencode', 'opencode/deepseek-v4.1-flash-free'),
                                     ('glm', 'pi', 'dgx/glm-5.3-flash')):
            self.data['models'][name] = {'description': name, 'runtimes': {runtime: {
                'id': model, 'thinking': {'default': 'high', 'allowed': ['high']}}}}

    def route(self, model, job, host='claude'):
        """The --route output for a job whose agent uses this model, from a host Herdr bridges to it."""
        self.data['agents'] = {'builder': {'model': model}, 'reviewer': {'model': model}}
        self.user.write_text(json.dumps(self.data))
        process = subprocess.run([sys.executable, '-B', str(SCRIPT), '--repo', str(self.root), '--harness', host,
                                  '--job', job, '--route', '--user-executors', str(self.user),
                                  '--user-config', str(self.root / 'absent.json')],
                                 capture_output=True, text=True,
                                 env=support.isolated_env(self.root, HERDR_ENV='1', AUTOMATTIC_PROFILE='',
                                                          AUTOMATTIC_SESSION=''))
        self.assertEqual(process.returncode, 0, process.stderr)
        return json.loads(process.stdout)

    def test_codex_route_sets_the_sandbox_for_the_write_scope_and_never_asks(self):
        # Rule: read-only for `writes: none`, workspace-write for `worktree`, approval never, model and effort explicit.
        for job, writes, sandbox in (('diff-review', 'none', 'read-only'), ('ticket', 'worktree', 'workspace-write')):
            with self.subTest(job=job):
                self.assertEqual(self.route('sol', job)['launch'], {
                    'writes': writes,
                    'argv': ['-s', sandbox, '-a', 'never', '-m', 'gpt-6.1-sol', '-c', 'model_reasoning_effort="high"'],
                    'verify': {'sandbox': sandbox, 'approval': 'never'}})
        # A native child of the same runtime takes no launch flags; its agent profile restricts it.
        self.assertNotIn('launch', self.route('sol', 'diff-review', host='codex'))

    def test_claude_route_allows_only_the_agents_tools_and_keeps_a_read_only_shell_out_of_the_worktree(self):
        # Rule: dontAsk with the agent's tools as the allowlist; `writes: none` denies every editing tool and, since
        # its shell stays, edits under the worktree it starts in.
        self.assertEqual(self.route('opus', 'diff-review', host='codex')['launch'], {
            'writes': 'none',
            'argv': ['--permission-mode', 'dontAsk',
                     '--allowedTools', 'Read,Grep,Glob,Bash,Skill,SendMessage,Monitor,TaskStop',
                     '--disallowedTools', 'Edit,Write,NotebookEdit',
                     '--settings', '{"permissions":{"deny":["Edit(./**)"]}}',
                     '--model', 'claude-opus-5-5', '--effort', 'high'],
            'verify': {'permission_mode': 'dontAsk'}})
        self.assertEqual(self.route('opus', 'ticket', host='codex')['launch'], {
            'writes': 'worktree',
            'argv': ['--permission-mode', 'dontAsk',
                     '--allowedTools', 'Read,Edit,Write,Bash,Grep,Glob,Skill,SendMessage,Monitor,TaskStop',
                     '--model', 'claude-opus-5-5', '--effort', 'high'],
            'verify': {'permission_mode': 'dontAsk'}})

    def test_pi_route_offers_an_explicit_tool_allowlist_for_the_write_scope(self):
        # Rule: `--tools` is an allowlist (an exclude list leaks bg_run); read-only tools for `none`, the full
        # built-in set for `worktree`; provider, model and thinking explicit.
        for job, writes, tools, offered in (
                ('diff-review', 'none', 'read,grep,find,ls', ['find', 'grep', 'ls', 'read']),
                ('ticket', 'worktree', 'read,bash,edit,write,grep,find,ls',
                 ['bash', 'edit', 'find', 'grep', 'ls', 'read', 'write'])):
            with self.subTest(job=job):
                self.assertEqual(self.route('glm', job)['launch'], {
                    'writes': writes,
                    'argv': ['--tools', tools, '--provider', 'dgx', '--model', 'glm-5.3-flash', '--thinking', 'high'],
                    'verify': {'tools': offered}})

    def test_opencode_route_creates_its_session_with_deny_rules_for_the_write_scope(self):
        # Rule: the TUI has no --agent or -m, so the session is created through the API with its model, variant and
        # permissions; `none` denies edit, shell and subagent, `worktree` denies subagent (a denied agent still
        # writes through the general subagent).
        def deny(*actions):
            return [{'action': action, 'resource': '*', 'effect': 'deny'} for action in actions]
        for job, writes, rules in (('diff-review', 'none', deny('edit', 'shell', 'subagent')),
                                   ('ticket', 'worktree', deny('subagent'))):
            with self.subTest(job=job):
                self.assertEqual(self.route('flash', job)['launch'], {
                    'writes': writes,
                    'api': {'method': 'POST', 'path': '/api/session', 'body': {
                        'agent': 'build',
                        'model': {'providerID': 'opencode', 'id': 'deepseek-v4.1-flash-free', 'variant': 'high'},
                        'permissions': rules}},
                    'verify': {'permissions': rules}})


if __name__ == '__main__':
    unittest.main()
