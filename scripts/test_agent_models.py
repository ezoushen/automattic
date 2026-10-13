#!/usr/bin/env python3
"""Preference precedence and native profile loading, isolated from personal settings."""

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch


SCRIPT = Path(__file__).with_name('agent-models.py')
spec = importlib.util.spec_from_file_location('agent_models', SCRIPT)
models = importlib.util.module_from_spec(spec)
spec.loader.exec_module(models)


def check():
    with tempfile.TemporaryDirectory(prefix='automattic models ') as tmp, \
            patch.dict(os.environ, {'AUTOMATTIC_PROFILE': '', 'HERDR_ENV': ''}):
        root = Path(tmp)
        user = root / 'user/models.json'
        project = root / '.automattic/models.json'

        def resolve(harness='codex', role='spec-reviewer', **task):
            return models.resolve(root, user, harness, role, task)

        for harness in models.HARNESSES:
            for role in models.ROLES:
                result = resolve(harness, role)
                assert result['settings'] == result['sources'] == {}
                if harness in ('claude', 'opencode'):
                    assert models.native_profile(result) is None
            assert models.resolve_execution(root, user, root / 'executors.json', harness,
                                            'spec-reviewer', {})['executor'] == 'native'
        assert list(root.iterdir()) == []  # Reads do not opt the user in.

        user.parent.mkdir()
        project.parent.mkdir()
        user.write_text(json.dumps({'codex': {
            'defaults': {'model': 'personal-model', 'effort': 'low'},
            'spec-reviewer': {'effort': 'high'}}}))
        project.write_text(json.dumps({'codex': {
            'defaults': {'effort': 'medium'},
            'spec-reviewer': {'model': 'project-model'}}}))
        before = (user.read_bytes(), project.read_bytes())
        result = resolve()
        assert result['settings'] == {'model': 'project-model', 'effort': 'medium'}
        assert result['sources']['effort'] == f'{project}:codex.defaults'
        assert resolve(model='task-model')['settings'] == {'model': 'task-model', 'effort': 'medium'}
        assert resolve(model=None)['settings'] == {'effort': 'medium'}
        assert resolve(model=None)['sources']['model'] == 'task'
        assert resolve('pi')['settings'] == {}
        assert resolve(role='repair')['settings'] == {'model': 'personal-model', 'effort': 'medium'}
        assert before == (user.read_bytes(), project.read_bytes())

        project.write_text(json.dumps({'codex': {'spec-reviewer': {'model': None, 'effort': None}}}))
        assert resolve()['settings'] == {}
        project.write_text('{}')  # Removing the override exposes the user layer.
        assert resolve()['settings'] == {'model': 'personal-model', 'effort': 'high'}

        for data in ('{broken', '[]', '{"claud": {}}', '{"codex":{"reviewer":{}}}',
                     '{"pi":{"repair":{"thinking":"high"}}}',
                     '{"claude":{"repair":{"model":false}}}',
                     '{"codex":{"repair":{"effort":"magic"}}}',
                     '{"pi":{"repair":{"model":"bad\\nmodel"}}}'):
            project.write_text(data)
            try:
                resolve()
            except ValueError:
                pass
            else:
                raise AssertionError(data)
            assert project.read_text() == data
        project.write_text('{}')

        for role in models.ROLES:
            _, header, _ = (models.ROOT / 'agents' / f'{role}.md').read_text().split('---', 2)
            assert not any(line.startswith(('model:', 'effort:')) for line in header.splitlines())
            result = resolve('claude', role, model='opus', effort='high')
            profile = models.native_profile(result)
            text = profile['content']
            assert 'model: "opus"' in text and 'effort: "high"' in text
            assert 'role_file' in text
            for line in (models.ROOT / 'agents' / f'{role}.md').read_text().splitlines():
                if line.startswith(('tools: ', 'disallowedTools: ')):
                    key, value = line.split(': ', 1)
                    assert f'{key}: {json.dumps(value)}' in text
            assert profile == models.native_profile(result)
            assert profile['name'] != models.native_profile(resolve('claude', role, effort='low'))['name']
            model_only = models.native_profile(resolve('claude', role, model='opus'))['content']
            assert 'model: "opus"' in model_only and '\neffort:' not in model_only
            effort_only = models.native_profile(resolve('claude', role, effort='high'))['content']
            assert 'effort: "high"' in effort_only and '\nmodel:' not in effort_only
        assert 'maxTurns: 40' in models.native_profile(resolve('claude', 'reproducer', effort='high'))['content']
        try:
            models.native_profile(resolve('claude', effort='ultra'))
        except ValueError:
            pass
        else:
            raise AssertionError('Claude accepted ultra')

        profile = models.native_profile(resolve('opencode', model='openai/gpt-5', effort='high'))
        assert 'mode: "subagent"' in profile['content'] and 'variant: "high"' in profile['content']
        assert 'model:' not in models.native_profile(resolve('opencode', effort='high'))['content']

        args = [sys.executable, '-B', str(SCRIPT), '--repo', str(root), '--user-config', str(user),
                '--harness', 'codex', '--role', 'spec-reviewer']
        cli = subprocess.run(args + ['--model', 'native'], capture_output=True, text=True, check=True)
        assert json.loads(cli.stdout)['settings'] == {'effort': 'high'}
        assert subprocess.run(args + ['--profile'], capture_output=True).returncode != 0
        for value in ('Assignment prose instead of a file path.', 'long assignment ' * 30, str(root)):
            failed = subprocess.run(args + ['--route', '--user-executors', str(root / 'missing.json'),
                                            '--assignment', value], capture_output=True, text=True)
            assert failed.returncode == 2, failed.stdout + failed.stderr
            assert '--assignment requires a readable UTF-8 text file path' in failed.stderr, failed.stderr
        for flag, values in (('--eligible-candidates', ('luna,sol', '"sol"', 'null')),
                             ('--eligible-thinking', ('opus=medium', '["medium"]')),
                             ('--route-choice', ('native', 'null'))):
            for value in values:
                failed = subprocess.run(args + ['--route', '--user-executors', str(root / 'missing.json'),
                                                flag, value], capture_output=True, text=True)
                assert failed.returncode == 2, failed.stdout + failed.stderr
                assert flag + ' expects inline JSON, for example' in failed.stderr, failed.stderr

    print('worker preferences: no opt-in writes, precedence, reset, validation, profiles: ok')


def check_native():
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
                    result = subprocess.run(['opencode', '--pure', 'debug', 'agent', profile['name']],
                                            cwd=root, env=env, capture_output=True, text=True, timeout=30)
                    assert result.returncode == 0, result.stderr
                    loaded = json.loads(result.stdout)
                    assert loaded['model'] == {'providerID': 'openai', 'modelID': 'gpt-5'}
                    assert loaded['variant'] == 'high' and loaded['mode'] == 'subagent'
                    assert 'role_file' in loaded['prompt']
        result = subprocess.run(['claude', 'plugin', 'validate', '--strict', str(root / '.claude/agents')],
                                cwd=root, env=env, capture_output=True, text=True, timeout=30)
        assert result.returncode == 0, result.stdout + result.stderr
    print('native profiles: Claude validation and OpenCode model/variant loading: ok (no model calls)')


if __name__ == '__main__':
    check()
    if '--native' in sys.argv:
        check_native()
