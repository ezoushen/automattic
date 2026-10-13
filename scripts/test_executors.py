#!/usr/bin/env python3
"""Built-in executor validation, selection and real subprocess handoff in temporary workspaces."""

import importlib.util
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
from unittest.mock import patch

from jsonschema import Draft202012Validator


def load(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


models, bash = load('agent-models'), load('bash-executor')


def instance(kind='subagent', config=None, policy=None):
    value = {'executor': {'type': kind, 'config': config or {}}}
    if policy is not None:
        value['models'] = policy
    return value


def fails(operation):
    try:
        operation()
    except ValueError:
        return
    raise AssertionError('Expected validation failure')


def check_profiles():
    with tempfile.TemporaryDirectory(prefix='automattic profiles ') as tmp:
        root = Path(tmp)
        user = root / 'user.json'
        data = {'agents': {'spec-reviewer': instance()}, 'profiles': {'balanced': {}}}
        user.write_text(json.dumps(data))
        cli = [sys.executable, '-B', str(models.ROOT / 'scripts/agent-models.py'), '--repo', str(root),
               '--user-executors', str(user), '--user-config', str(root/'absent-models.json'),
               '--harness', 'claude', '--role', 'spec-reviewer', '--config-profile', 'balanced']
        with patch.dict(os.environ, {'AUTOMATTIC_PROFILE': '', 'AUTOMATTIC_SESSION': '', 'HERDR_ENV': ''}):
            result = subprocess.run(cli + ['--route'], capture_output=True, text=True, check=True)
            resolved = json.loads(result.stdout)
            assert resolved['config_profile'] == 'balanced'
            assert resolved['router'] == {'type': 'profile', 'profile': 'balanced'}
            assert resolved['executor'] == 'native'
            assert subprocess.run(cli, capture_output=True).returncode != 0
            result = subprocess.run(cli[:-1] + ['missing', '--route'], capture_output=True, text=True)
            assert result.returncode != 0 and 'Unknown routing profile' in result.stderr
        for invalid in ({'profiles': {'': {}}}, {'profiles': {'balanced': {'unknown': {}}}},
                        {'profiles': {'balanced': {'agents': {}}}}):
            fails(lambda invalid=invalid: models.validate_execution_config(invalid, 'test'))
    print('routing profiles: CLI selection, empty overrides and migration validation: ok')


def check():
    for path in (models.ROOT / 'schemas').rglob('*.schema.json'):
        Draft202012Validator.check_schema(json.loads(path.read_text()))
    with tempfile.TemporaryDirectory(prefix='automattic executors ') as tmp, \
            patch.dict(os.environ, {'AUTOMATTIC_PROFILE': '', 'HERDR_ENV': ''}):
        root = Path(tmp)
        user = root / 'user/executors.json'
        project = root / '.automattic/executors.json'
        preferences = root / 'user/models.json'

        def resolve(host='claude', role='spec-reviewer', choice=None, adaptive_thinking=None, **task):
            return models.resolve_execution(root, preferences, user, host, role, task, choice,
                                            adaptive_thinking=adaptive_thinking)

        for host in models.HARNESSES:
            for role in models.ROLES:
                result = resolve(host, role)
                assert result['executor'] == 'native' and result['native_dispatch']
        assert list(root.iterdir()) == []
        fails(lambda: resolve(adaptive_thinking='high'))
        user.parent.mkdir()
        project.parent.mkdir()
        preferences.write_text(json.dumps({'claude': {'spec-reviewer': {'model': 'legacy-model'}}}))
        native = instance()
        for host in models.HARNESSES:
            omitted = resolve(host, choice={'executor': {'type': 'subagent'}})
            assert omitted == resolve(host, choice=native)
        skill = instance('skill', {'skill': 'herdr', 'instruction': 'Run the assigned review with Codex.'})
        named = instance('subagent', {'agent': 'codex:codex-rescue'})
        program = instance('bash', {'argv': ['bash', '/some/worker.sh']})
        for value in (native, skill, named, program):
            result = resolve(choice=value)
            assert result['settings'] == {} and result['model_mode'] == 'inherit'
            assert Path(result['executor_guide']).is_file()
            assert result['native_dispatch'] == (value == native)
            assert result['harness'] == ('claude' if value == native else None)
        for host in models.HARNESSES:
            for role in models.ROLES:
                for policy, expected in (
                    ({'mode': 'inherit'}, {}),
                    ({'mode': 'override', 'model': 'chosen-model'}, {'model': 'chosen-model'}),
                    ({'mode': 'override', 'thinking': 'high'}, {'effort': 'high'}),
                ):
                    user.write_text(json.dumps({'agents': {role: instance(policy=policy)}}))
                    result = resolve(host, role)
                    assert result['settings'] == expected
                    if host not in ('claude', 'opencode'):
                        continue
                    profile = models.native_profile(result)
                    if not expected:
                        assert profile is None
                    else:
                        content = profile['content']
                        thinking_field = 'effort' if host == 'claude' else 'variant'
                        assert ('\nmodel:' in content) == ('model' in expected)
                        assert (f'\n{thinking_field}:' in content) == ('effort' in expected)
        # Arbitrary installed names are data, not a provider allowlist.
        assert resolve(choice=instance('skill', {'skill': 'my-plugin:delegate', 'instruction': 'Run it'}))['executor'] == 'skill'

        user.write_text(json.dumps({'agents': {'spec-reviewer': skill}}))
        before = user.read_bytes()
        project.write_text(json.dumps({'agents': {'spec-reviewer': native}}))
        assert resolve()['native_dispatch'] and resolve()['settings'] == {}
        project.write_text(json.dumps({'agents': {'spec-reviewer': None}}))
        assert resolve()['settings'] == {'model': 'legacy-model'}
        project.write_text('{}')
        assert resolve()['executor'] == 'skill'
        assert resolve(role='repair')['executor'] == 'native'

        preferences.write_text('{invalid unused legacy preferences')
        assert resolve()['settings'] == {}
        override = dict(skill, models={'mode': 'override', 'model': 'chosen-model', 'thinking': 'high'})
        result = resolve(choice=override)
        assert result['settings'] == {'model': 'chosen-model', 'effort': 'high'}
        assert result['sources']['effort'] == 'task choice.models.thinking'
        assert resolve(choice=override, effort='low')['settings']['effort'] == 'low'
        fails(lambda: resolve(choice=override, adaptive_thinking='xhigh'))
        fails(lambda: resolve(choice=skill, adaptive_thinking='high'))
        for executor in (native, named, skill, program):
            adaptive = dict(executor, models=dict(override['models'], allow_thinking_override=True))
            for host in models.HARNESSES:
                result = resolve(host, choice=adaptive, adaptive_thinking='xhigh')
                assert result['settings'] == {'model': 'chosen-model', 'effort': 'xhigh'}
                assert result['thinking_baseline'] == 'high'
                assert result['sources']['effort'] == 'adaptive thinking'
                assert result['executor_config'] == executor['executor']['config']
                assert resolve(host, choice=adaptive)['settings']['effort'] == 'high'
            fails(lambda: resolve(choice=adaptive, adaptive_thinking='xhigh', effort='low'))
            fails(lambda: resolve(choice=adaptive, adaptive_thinking='native'))
            fails(lambda: resolve(choice=adaptive, adaptive_thinking='bad label'))
        locked = dict(override, models=dict(override['models'], allow_thinking_override=False))
        fails(lambda: resolve(choice=locked, adaptive_thinking='xhigh'))
        assert resolve(choice=locked, effort='low')['settings']['effort'] == 'low'
        defaults = instance(policy={'mode': 'override', 'allow_thinking_override': True})
        assert resolve(choice=defaults)['settings'] == {}
        assert resolve(choice=defaults, adaptive_thinking='high')['settings'] == {'effort': 'high'}
        assert resolve(choice=override, effort='runtime-specific')['settings']['effort'] == 'runtime-specific'
        assert resolve(choice=override, model=None)['settings'] == {'effort': 'high'}
        assert resolve(choice=dict(skill, models={'mode': 'override'}))['settings'] == {}
        assert user.read_bytes() == before
        fails(lambda: resolve(choice=skill, model='unrequested'))

        invalid = [
            {'executor': {'type': 'unknown', 'config': {}}},
            {'executor': {'type': 'subagent', 'config': None}},
            {'executor': {'type': 'skill'}},
            {'executor': {'type': 'bash'}},
            instance('subagent', {'agent': ''}),
            instance('subagent', {'model': 'misplaced'}),
            instance('skill', {'skill': 'herdr'}),
            instance('skill', {'skill': 'herdr', 'instruction': '  '}),
            instance('skill', {'skill': 'herdr', 'instruction': 'run', 'destination': 'codex'}),
            instance('bash', {'argv': []}),
            instance('bash', {'argv': ['']}),
            instance('bash', {'argv': ['bash', '\0']}),
            instance('bash', {'argv': 'bash worker.sh'}),
            dict(native, models={'mode': 'inherit', 'thinking': 'high'}),
            dict(native, models={'mode': 'override', 'effort': 'high'}),
            dict(native, models={'mode': 'override', 'model': False}),
            dict(native, models={'mode': 'override', 'allow_thinking_override': 'true'}),
            dict(native, models={'mode': 'inherit', 'allow_thinking_override': True}),
            dict(native, models={'mode': 'override', 'thinking': 'bad\nlabel'}),
            dict(native, models={'mode': 'override', 'model': 'bad\n'}),
            instance('subagent', {'agent': 'bad\n'}),
            dict(native, models={'model': 'no-mode'}),
            dict(native, surprise=True),
        ]
        for value in invalid:
            fails(lambda value=value: resolve(choice=value))
        for data in ([], {'agents': {'unknown-role': native}}, {'schema': {}},
                     {'executors': {}}, {'routes': {'spec-reviewer': {'executor': 'herdr'}}}):
            fails(lambda data=data: models.validate_execution_config(data, 'test'))
        # An editor's $schema value cannot replace bundled validation or trigger a fetch.
        models.validate_execution_config({'$schema': 'https://invalid.example/schema', 'agents': {'repair': native}}, 'test')
        project.write_text('{broken')
        fails(resolve)
        project.write_text('{}')

        cli = [sys.executable, '-B', str(models.ROOT / 'scripts/agent-models.py'),
               '--repo', str(root), '--user-config', str(preferences), '--user-executors', str(user),
               '--harness', 'claude', '--role', 'spec-reviewer', '--route']
        result = subprocess.run(cli + ['--route-choice', json.dumps(override), '--thinking', 'low'],
                                capture_output=True, text=True, check=True)
        assert json.loads(result.stdout)['settings']['effort'] == 'low'
        result = subprocess.run(cli + ['--route-choice', json.dumps(adaptive), '--adaptive-thinking', 'xhigh'],
                                capture_output=True, text=True, check=True)
        assert json.loads(result.stdout)['settings']['effort'] == 'xhigh'
        assert subprocess.run(cli + ['--route-choice', json.dumps(locked), '--adaptive-thinking', 'xhigh'],
                              capture_output=True).returncode != 0
        assert subprocess.run([arg for arg in cli if arg != '--route'] + ['--adaptive-thinking', 'high'],
                              capture_output=True).returncode != 0
        for value in (skill, named, program):
            assert subprocess.run(cli + ['--route-choice', json.dumps(value), '--profile'],
                                  capture_output=True).returncode != 0
        selected_native = dict(native, models={'mode': 'override', 'model': 'opus', 'thinking': 'high'})
        result = subprocess.run(cli + ['--route-choice', json.dumps(selected_native), '--profile'],
                                capture_output=True, text=True, check=True)
        assert 'effort: "high"' in json.loads(result.stdout)['native_profile']['content']
        assert subprocess.run(cli + ['--route-choice', 'null'], capture_output=True).returncode != 0

        worker = root / 'worker.py'
        worker.write_text('''import json, os, pathlib, sys
request = json.load(sys.stdin)
pathlib.Path('received.json').write_text(json.dumps({'request': request, 'cwd': os.getcwd(), 'args': sys.argv[1:]}))
assignment_id = request['assignment']['assignment_id']
mode = sys.argv[1]
if mode == 'exit': sys.exit(7)
if mode == 'malformed': print('not json'); sys.exit()
print(json.dumps({'assignment_id': 'wrong' if mode == 'mismatch' else assignment_id,
                  'status': mode if mode in ('blocked', 'failed', 'unknown') else 'completed',
                  'report': '' if mode == 'empty' else 'Evidence collected', 'run_id': 'fixture-1'}))
''')
        launcher = root / 'worker.sh'
        launcher.write_text(f'exec {shlex.quote(sys.executable)} {shlex.quote(str(worker))} "$@"\n')
        assignment = {'assignment_id': 'review-1', 'head': 'pinned-sha', 'worktree': str(root),
                      'role_file': str(models.ROOT / 'roles/spec-reviewer.md'),
                      'prompt': 'Literal $(touch unexpected); `touch unexpected`'}

        def execution(mode='completed', policy=None):
            return resolve(choice=instance('bash', {'argv': ['bash', str(launcher), mode, assignment['prompt']]}, policy))

        for policy in ({'mode': 'inherit'}, override['models']):
            outcome = bash.run(execution(policy=policy), assignment)
            assert outcome['status'] == 'completed'
            received = json.loads((root / 'received.json').read_text())
            assert received['request'] == {'assignment': assignment, 'models': policy}
            assert Path(received['cwd']).resolve() == root.resolve() and received['args'][1] == assignment['prompt']
            assert not (root / 'unexpected').exists()
        adapted = resolve(choice=instance('bash', {'argv': ['bash', str(launcher), 'completed']},
                                          dict(override['models'], allow_thinking_override=True)),
                          adaptive_thinking='xhigh')
        assert bash.run(adapted, assignment)['status'] == 'completed'
        received = json.loads((root / 'received.json').read_text())
        assert received['request']['models'] == dict(override['models'], thinking='xhigh')
        for mode in ('blocked', 'failed', 'unknown'):
            assert bash.run(execution(mode), assignment)['status'] == mode
        for mode in ('exit', 'malformed', 'mismatch', 'empty'):
            fails(lambda mode=mode: bash.run(execution(mode), assignment))
        fails(lambda: bash.run(execution(), {**assignment, 'worktree': 'relative'}))
        result_path, assignment_path = root / 'execution.json', root / 'assignment.json'
        result_path.write_text(json.dumps(execution()))
        assignment_path.write_text(json.dumps(assignment))
        result = subprocess.run([sys.executable, '-B', str(models.ROOT / 'scripts/bash-executor.py'),
                                 '--execution', str(result_path), '--assignment', str(assignment_path)],
                                capture_output=True, text=True, check=True)
        assert json.loads(result.stdout)['assignment_id'] == 'review-1'
    print('executors: bundled schemas, instance precedence, model policy, native profiles and Bash handoff: ok')


if __name__ == '__main__':
    check_profiles()
    check()
