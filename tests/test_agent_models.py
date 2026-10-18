#!/usr/bin/env python3
"""Preference precedence and native profile loading, isolated from personal settings."""

import json
import os
import socket
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

import support


SCRIPT = support.script('agent_models.py')
models = support.load_script('agent_models.py', 'agent_models')


class Preferences(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix='automattic models ')
        self.addCleanup(tmp.cleanup)
        environment = patch.dict(os.environ, {'AUTOMATTIC_PROFILE': '', 'HERDR_ENV': ''})
        environment.start()
        self.addCleanup(environment.stop)
        self.root = Path(tmp.name)
        self.user = self.root / 'user/models.json'
        self.project = self.root / '.automattic/models.json'

    def resolve(self, harness='codex', role='spec-reviewer', **task):
        return models.resolve(self.root, self.user, harness, role, task)

    def write_layers(self):
        self.user.parent.mkdir()
        self.project.parent.mkdir()
        self.user.write_text(json.dumps({'codex': {
            'defaults': {'model': 'personal-model', 'effort': 'low'},
            'spec-reviewer': {'effort': 'high'}}}))
        self.project.write_text(json.dumps({'codex': {
            'defaults': {'effort': 'medium'},
            'spec-reviewer': {'model': 'project-model'}}}))

    def test_reads_without_configuration_return_nothing_and_write_nothing(self):
        for harness in models.HARNESSES:
            for role in models.ROLES:
                result = self.resolve(harness, role)
                assert result['settings'] == result['sources'] == {}
                if harness in ('claude', 'opencode'):
                    assert models.native_profile(result) is None
            assert models.resolve_execution(self.root, self.user, self.root / 'executors.json', harness,
                                            'spec-reviewer', {})['executor'] == 'native'
        assert list(self.root.iterdir()) == []  # Reads do not opt the user in.

    def test_task_project_and_user_layers_take_precedence(self):
        self.write_layers()
        before = (self.user.read_bytes(), self.project.read_bytes())
        result = self.resolve()
        assert result['settings'] == {'model': 'project-model', 'effort': 'medium'}
        assert result['sources']['effort'] == f'{self.project}:codex.defaults'
        assert self.resolve(model='task-model')['settings'] == {'model': 'task-model', 'effort': 'medium'}
        assert self.resolve(model=None)['settings'] == {'effort': 'medium'}
        assert self.resolve(model=None)['sources']['model'] == 'task'
        assert self.resolve('pi')['settings'] == {}
        assert self.resolve(role='repair')['settings'] == {'model': 'personal-model', 'effort': 'medium'}
        assert before == (self.user.read_bytes(), self.project.read_bytes())

        self.project.write_text(json.dumps({'codex': {'spec-reviewer': {'model': None, 'effort': None}}}))
        assert self.resolve()['settings'] == {}
        self.project.write_text('{}')  # Removing the override exposes the user layer.
        assert self.resolve()['settings'] == {'model': 'personal-model', 'effort': 'high'}

    def test_invalid_configuration_is_rejected_and_left_unchanged(self):
        self.project.parent.mkdir()
        for data in ('{broken', '[]', '{"claud": {}}', '{"codex":{"reviewer":{}}}',
                     '{"pi":{"repair":{"thinking":"high"}}}',
                     '{"claude":{"repair":{"model":false}}}',
                     '{"codex":{"repair":{"effort":"magic"}}}',
                     '{"pi":{"repair":{"model":"bad\\nmodel"}}}'):
            self.project.write_text(data)
            with self.assertRaises(ValueError, msg=data):
                self.resolve()
            assert self.project.read_text() == data

    def test_claude_profiles_carry_role_tools_and_requested_settings(self):
        for role in models.ROLES:
            _, header, _ = (models.ROOT / 'agents' / f'{role}.md').read_text().split('---', 2)
            assert not any(line.startswith(('model:', 'effort:')) for line in header.splitlines())
            result = self.resolve('claude', role, model='opus', effort='high')
            profile = models.native_profile(result)
            text = profile['content']
            assert 'model: "opus"' in text and 'effort: "high"' in text
            assert 'role_file' in text
            for line in (models.ROOT / 'agents' / f'{role}.md').read_text().splitlines():
                if line.startswith(('tools: ', 'disallowedTools: ')):
                    key, value = line.split(': ', 1)
                    assert f'{key}: {json.dumps(value)}' in text
            assert profile == models.native_profile(result)
            assert profile['name'] != models.native_profile(self.resolve('claude', role, effort='low'))['name']
            model_only = models.native_profile(self.resolve('claude', role, model='opus'))['content']
            assert 'model: "opus"' in model_only and '\neffort:' not in model_only
            effort_only = models.native_profile(self.resolve('claude', role, effort='high'))['content']
            assert 'effort: "high"' in effort_only and '\nmodel:' not in effort_only
        assert 'maxTurns: 40' in models.native_profile(self.resolve('claude', 'reproducer', effort='high'))['content']
        with self.assertRaises(ValueError, msg='Claude accepted ultra'):
            models.native_profile(self.resolve('claude', effort='ultra'))

    def test_opencode_profile_maps_effort_to_variant(self):
        profile = models.native_profile(self.resolve('opencode', model='openai/gpt-5', effort='high'))
        assert 'mode: "subagent"' in profile['content'] and 'variant: "high"' in profile['content']
        assert 'model:' not in models.native_profile(self.resolve('opencode', effort='high'))['content']

    def test_cli_rejects_profile_without_route_and_malformed_arguments(self):
        self.write_layers()
        self.project.write_text('{}')
        args = [sys.executable, '-B', str(SCRIPT), '--repo', str(self.root), '--user-config', str(self.user),
                '--harness', 'codex', '--role', 'spec-reviewer']
        cli = subprocess.run(args + ['--model', 'native'], capture_output=True, text=True, check=True)
        assert json.loads(cli.stdout)['settings'] == {'effort': 'high'}
        assert subprocess.run(args + ['--profile'], capture_output=True).returncode != 0
        for value in ('Assignment prose instead of a file path.', 'long assignment ' * 30, str(self.root)):
            failed = subprocess.run(args + ['--route', '--user-executors', str(self.root / 'missing.json'),
                                            '--assignment', value], capture_output=True, text=True)
            assert failed.returncode == 2, failed.stdout + failed.stderr
            assert '--assignment requires a readable UTF-8 text file path' in failed.stderr, failed.stderr
        for flag, values in (('--eligible-candidates', ('luna,sol', '"sol"', 'null')),
                             ('--eligible-thinking', ('opus=medium', '["medium"]')),
                             ('--route-choice', ('native', 'null'))):
            for value in values:
                failed = subprocess.run(args + ['--route', '--user-executors', str(self.root / 'missing.json'),
                                                flag, value], capture_output=True, text=True)
                assert failed.returncode == 2, failed.stdout + failed.stderr
                assert flag + ' expects inline JSON, for example' in failed.stderr, failed.stderr


def check_opencode_profile(root, env, name):
    """Read the loaded profile from an isolated OpenCode 2 service (no model calls)."""
    def opencode(*args):
        return subprocess.run(['opencode', *args], cwd=root, env=env, capture_output=True, text=True, timeout=60)
    # The CLI talks to a background service on a fixed port the user's own service already holds.
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0))
        port = probe.getsockname()[1]
    assert opencode('service', 'set', 'port', str(port)).returncode == 0
    try:
        # A directory's first request can answer before its agents load; built-in `build` marks loaded.
        for _ in range(20):
            result = opencode('api', 'GET', '/api/agent', '-H', f'x-opencode-directory:{root}')
            assert result.returncode == 0, result.stdout + result.stderr
            agents = {agent['id']: agent for agent in json.loads(result.stdout)['data']}
            if 'build' in agents:
                break
            time.sleep(0.5)
        assert name in agents, (name, sorted(agents))
        loaded = agents[name]
        assert loaded['model'] == {'providerID': 'openai', 'id': 'gpt-5', 'variant': 'high'}, loaded
        assert loaded['mode'] == 'subagent' and 'role_file' in loaded['system']
    finally:
        opencode('service', 'stop')


@unittest.skipUnless(os.environ.get('AUTOMATTIC_NATIVE') == '1', 'set AUTOMATTIC_NATIVE=1 to check installed CLIs')
class NativeProfiles(unittest.TestCase):
    def test_claude_validates_and_opencode_loads_generated_profiles(self):
        with tempfile.TemporaryDirectory(prefix='automattic native models ') as tmp:
            root = Path(tmp)
            env = dict(os.environ)
            for key, directory in [('CLAUDE_CONFIG_DIR', 'claude-config'), ('XDG_CONFIG_HOME', 'config'),
                                   ('XDG_CACHE_HOME', 'cache'), ('XDG_DATA_HOME', 'data'),
                                   ('XDG_STATE_HOME', 'state')]:
                env[key] = str(root / directory)
                Path(env[key]).mkdir()
            for harness in ('claude', 'opencode'):
                for role in models.ROLES:
                    settings = {'model': 'opus' if harness == 'claude' else 'openai/gpt-5', 'effort': 'high'}
                    profile = models.native_profile({'harness': harness, 'role': role, 'settings': settings})
                    path = root / profile['path']
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(profile['content'])
                    if harness == 'claude':
                        for partial in ({'model': 'opus'}, {'effort': 'high'}):
                            profile = models.native_profile({'harness': harness, 'role': role, 'settings': partial})
                            (root / profile['path']).write_text(profile['content'])
                    if harness == 'opencode':
                        check_opencode_profile(root, env, profile['name'])
            result = subprocess.run(['claude', 'plugin', 'validate', '--strict', str(root / '.claude/agents')],
                                    cwd=root, env=env, capture_output=True, text=True, timeout=30)
            assert result.returncode == 0, result.stdout + result.stderr


if __name__ == '__main__':
    unittest.main()
