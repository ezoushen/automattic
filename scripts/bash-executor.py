#!/usr/bin/env python3
"""Run an explicitly selected Bash executor with a structured assignment on stdin."""

import argparse
import importlib.util
import json
from pathlib import Path
import subprocess


spec = importlib.util.spec_from_file_location('agent_models', Path(__file__).with_name('agent-models.py'))
models = importlib.util.module_from_spec(spec)
spec.loader.exec_module(models)


def run(execution, assignment):
    if execution.get('executor_type') != 'bash':
        raise ValueError('Expected a resolved bash executor')
    policy = {'mode': execution['model_mode']}
    for source, target in (('model', 'model'), ('effort', 'thinking')):
        if source in execution['settings']:
            policy[target] = execution['settings'][source]
    models.validate_execution_config({'agents': {execution['role']: {
        'executor': {'type': 'bash', 'config': execution['executor_config']},
        'models': policy}}}, 'execution')
    for field in ('assignment_id', 'worktree', 'role_file', 'head', 'prompt'):
        if not isinstance(assignment.get(field), str) or not assignment[field].strip():
            raise ValueError(f'assignment.{field} must be a nonempty string')
    worktree, role_file = Path(assignment['worktree']), Path(assignment['role_file'])
    if not worktree.is_absolute() or not worktree.is_dir():
        raise ValueError('assignment.worktree must be an existing absolute directory')
    if not role_file.is_absolute() or not role_file.is_file():
        raise ValueError('assignment.role_file must be an existing absolute file')
    request = {'assignment': assignment, 'models': policy}
    # argv remains literal: prompts and model selections travel through stdin, never shell expansion.
    process = subprocess.run(execution['executor_config']['argv'], cwd=worktree,
                             input=json.dumps(request), text=True, stdout=subprocess.PIPE)
    if process.returncode:
        raise ValueError(f'Executor exited with status {process.returncode}; reconcile before retrying')
    try:
        outcome = json.loads(process.stdout)
    except ValueError as error:
        raise ValueError('Executor returned invalid JSON; reconcile before retrying') from error
    if not isinstance(outcome, dict) or outcome.get('assignment_id') != assignment['assignment_id']:
        raise ValueError('Executor returned a missing or mismatched assignment ID')
    if outcome.get('status') not in ('completed', 'blocked', 'failed', 'unknown'):
        raise ValueError('Executor did not return a terminal or uncertain execution status')
    if not isinstance(outcome.get('report'), str) or not outcome['report'].strip():
        raise ValueError('Executor returned no report or explanation')
    return outcome


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execution', type=Path, required=True, help='saved resolver JSON')
    parser.add_argument('--assignment', type=Path, required=True, help='assignment JSON')
    args = parser.parse_args()
    try:
        outcome = run(json.loads(args.execution.read_text()), json.loads(args.assignment.read_text()))
        print(json.dumps(outcome, indent=2))
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        parser.exit(2, f'{error}\n')


if __name__ == '__main__':
    main()
