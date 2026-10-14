#!/usr/bin/env python3
"""Report an effort's recorded token use per accepted ticket from lifecycle state and native transcripts."""

import argparse
from datetime import datetime
import json
from pathlib import Path
import re
import shlex
import sqlite3


FIELDS = ('responses', 'input', 'cache_write', 'cache_read', 'output')
YIELD_GATE = 'These lifecycle workers could finish without waking you'
SHELL_TOOLS = {'Bash', 'bash', 'exec_command', 'shell', 'shell_command'}
TOOL_ACTIVITIES = {'read': {'Read', 'Grep', 'Glob', 'LS', 'read', 'grep', 'find', 'ls'},
                   'edit': {'Edit', 'Write', 'MultiEdit', 'NotebookEdit', 'edit', 'write', 'apply_patch'},
                   'agent': {'Agent', 'Task', 'SendMessage'}}
READ_COMMANDS = {'cat', 'sed', 'head', 'tail', 'rg', 'grep', 'ls', 'find', 'wc', 'jq'}
SCRIPTS = {'run-check.py': 'check', 'agent-models.py': 'routing', 'decisions.py': 'routing',
           'decision_journal.py': 'routing'}
OPTION_VALUES = {'git': {'-C', '-c', '--git-dir', '--work-tree'}, 'herdr': {'--session'}}


def timestamp(value):
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('timestamps require an explicit UTC offset')
    return parsed


def total(responses):
    sums = dict.fromkeys(FIELDS, 0)
    for response in responses:
        sums['responses'] += 1
        for field in FIELDS[1:]:
            sums[field] += response[field]
    return sums


def trigger(text):
    """What started a host turn: a wake receipt or notification, the yield hook, or the user."""
    text = text.strip()
    if YIELD_GATE in text:
        return 'yield-hook'
    if text.startswith(('<task-notification>', '<background-task-notification>')):
        return 'wake'
    try:
        receipt = json.loads(text)
    except ValueError:
        return 'user'
    return 'wake' if isinstance(receipt, dict) and 'event_id' in receipt and receipt.get('kind') in (
        'wait-finished', 'hold') else 'user'


def words(command):
    try:
        return shlex.split(command, comments=True)
    except ValueError:
        return command.split('#')[0].split()


def command_activity(command):
    tokens = words(command)
    for index, token in enumerate(tokens):
        if token.endswith('worker-lifecycle.py'):
            return 'lifecycle:' + (tokens[index + 1] if index + 1 < len(tokens) else '?')
        if Path(token).name in SCRIPTS:
            return SCRIPTS[Path(token).name]
    for segment in re.split(r'&&|\|\||;|\||\n', command):
        tokens = [token for token in words(segment) if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*=.*', token)]
        if not tokens or tokens[0] == 'cd':
            continue
        program, rest, skip = Path(tokens[0]).name, [], False
        for token in tokens[1:]:
            if skip:
                skip = False
            elif token in OPTION_VALUES.get(program, ()):
                skip = True
            elif not token.startswith('-'):
                rest.append(token)
        if program == 'git' and rest:
            return f'git:{rest[0]}'
        if program == 'herdr' and rest:
            return 'herdr:' + ' '.join(rest[:2])
        return 'read' if program in READ_COMMANDS else f'command:{program}'
    return 'command'


def activity(calls):
    """A response's activity is its first tool call; a response without one is a reply."""
    if not calls:
        return 'reply'
    name, command = calls[0]
    if command is not None:
        return command_activity(command)
    return next((label for label, names in TOOL_ACTIVITIES.items() if name in names), f'tool:{name}')


def shell_command(name, arguments):
    if name not in SHELL_TOOLS or not isinstance(arguments, dict):
        return None
    command = arguments.get('command', arguments.get('cmd'))
    return shlex.join(command) if isinstance(command, list) else str(command or '')


def text_of(content):
    if isinstance(content, str):
        return content
    if not isinstance(content, list) or any(block.get('type') == 'tool_result' for block in content):
        return None
    texts = [block.get('text', '') for block in content if block.get('type') in ('text', 'input_text')]
    return '\n'.join(texts) if texts else None


def claude_responses(path):
    """One entry per response ID; streamed blocks repeat usage, so keep the largest output snapshot."""
    responses, cause = {}, 'user'
    for line in path.read_text().splitlines():
        entry = json.loads(line)
        message = entry.get('message') or {}
        if entry.get('type') == 'user':
            text = text_of(message.get('content'))
            cause = trigger(text) if text is not None else cause
            continue
        usage = message.get('usage')
        if entry.get('type') != 'assistant' or not usage or message.get('model') == '<synthetic>':
            continue
        calls = [(block['name'], shell_command(block['name'], block.get('input')))
                 for block in message.get('content', []) if block.get('type') == 'tool_use']
        response = {'input': usage.get('input_tokens', 0), 'cache_write': usage.get('cache_creation_input_tokens', 0),
                    'cache_read': usage.get('cache_read_input_tokens', 0), 'output': usage.get('output_tokens', 0)}
        previous = responses.get(message['id'])
        if previous is None:
            responses[message['id']] = dict(response, time=entry.get('timestamp'), trigger=cause, calls=calls)
        else:
            previous['calls'] += calls
            if response['output'] > previous['output']:
                previous.update(response)
    return list(responses.values())


def codex_responses(path):
    """Codex repeats a token count without a new response; only a growing total marks one."""
    responses, previous, cause, calls = [], None, 'user', []
    for line in path.read_text().splitlines():
        entry = json.loads(line)
        payload = entry.get('payload') or {}
        if entry.get('type') == 'response_item':
            if payload.get('type') == 'message' and payload.get('role') == 'user':
                text = text_of(payload.get('content'))
                cause = trigger(text) if text is not None else cause
            elif payload.get('type') in ('function_call', 'custom_tool_call'):
                try:
                    arguments = json.loads(payload.get('arguments') or '{}')
                except ValueError:
                    arguments = {}
                calls.append((payload.get('name'), shell_command(payload.get('name'), arguments)))
            continue
        info = payload.get('info') or {}
        if entry.get('type') != 'event_msg' or payload.get('type') != 'token_count' or not info:
            continue
        if info['total_token_usage'] == previous:
            continue
        previous, usage = info['total_token_usage'], info['last_token_usage']
        cached, written = usage.get('cached_input_tokens', 0), usage.get('cache_write_input_tokens', 0)
        responses.append({'input': max(0, usage.get('input_tokens', 0) - cached - written),
                          'cache_write': written, 'cache_read': cached, 'output': usage.get('output_tokens', 0),
                          'time': entry.get('timestamp'), 'trigger': cause, 'calls': calls})
        calls = []
    return responses


def pi_responses(path):
    """Pi records usage on each assistant message entry, including abandoned branches, which were still paid for."""
    responses, cause = {}, 'user'
    for line in path.read_text().splitlines():
        entry = json.loads(line)
        message = entry.get('message') or {}
        if entry.get('type') == 'custom_message':
            cause = 'yield-hook' if entry.get('customType') == 'automattic_yield_gate' else trigger(
                str(entry.get('content', '')))
            continue
        if entry.get('type') != 'message':
            continue
        if message.get('role') == 'user':
            text = text_of(message.get('content'))
            cause = trigger(text) if text is not None else cause
            continue
        usage = message.get('usage')
        if message.get('role') == 'assistant' and usage:
            calls = [(block.get('name'), shell_command(block.get('name'), block.get('arguments')))
                     for block in message.get('content', []) if block.get('type') == 'toolCall']
            responses[entry['id']] = {'input': usage.get('input', 0), 'cache_write': usage.get('cacheWrite', 0),
                                      'cache_read': usage.get('cacheRead', 0), 'output': usage.get('output', 0),
                                      'time': entry.get('timestamp'), 'trigger': cause, 'calls': calls}
    return list(responses.values())


READERS = {'claude': (claude_responses, lambda root, session: [*root.glob(f'*/{session}.jsonl')]),
           'codex': (codex_responses, lambda root, session: [*root.glob(f'**/rollout-*-{session}.jsonl')]),
           'pi': (pi_responses, lambda root, session: [*root.glob(f'*/*_{session}.jsonl')])}


def host_reader(path):
    with path.open() as stream:
        first = json.loads(stream.readline() or '{}')
    return {'session': pi_responses, 'session_meta': codex_responses}.get(first.get('type'), claude_responses)


def grouped(responses, key):
    groups = {}
    for response in responses:
        groups.setdefault(key(response), []).append(response)
    return {name: total(rows) for name, rows in sorted(groups.items(), key=lambda item: -total(item[1])['output'])}


def report(state, roots, hosts=(), since=None, until=None):
    db = sqlite3.connect(f'file:{state}?mode=ro', uri=True)
    attempts = [json.loads(row[0]) for row in db.execute('SELECT data FROM attempts ORDER BY id')]
    seen, workers, missing = set(), {}, []
    for saved in attempts:
        key = (saved['runtime'], saved['native_session'])
        if key in seen:
            continue  # A retained session serves later attempts of the same assignment and role.
        seen.add(key)
        gap = {key: saved[key] for key in ('attempt', 'runtime', 'native_session')}
        if saved['runtime'] not in READERS:
            missing.append(dict(gap, reason='unsupported runtime'))
            continue
        read, find = READERS[saved['runtime']]
        paths = find(roots[saved['runtime']], saved['native_session'])
        if not paths:
            missing.append(dict(gap, reason='no transcript found'))
        responses = [response for path in paths for response in read(path)]
        workers.setdefault((saved['assignment'], saved['role']), []).extend(responses)
    by_assignment, by_role = {}, {}
    for (assignment, role), responses in workers.items():
        by_assignment.setdefault(assignment, []).extend(responses)
        by_role.setdefault(role, []).extend(responses)
    host = [response for path in hosts for response in host_reader(path)(path)
            if response['time'] and since <= timestamp(response['time']) < until]
    reverted = {row[0] for row in db.execute("SELECT attempt FROM events WHERE kind = 'attribution' "
                                             "AND json_extract(payload, '$.kind') = 'revert'")}
    accepted = sorted({saved['assignment'] for saved in attempts if saved.get('accepted')
                       and saved['role'] == 'implementer' and saved['attempt'] not in reverted})
    worker_responses = [response for responses in workers.values() for response in responses]
    spend = total(worker_responses + host)
    return {'state': str(state), 'accepted_tickets': accepted, 'total': spend,
            'per_accepted_ticket': {key: value / len(accepted) for key, value in spend.items()} if accepted else None,
            'workers': {'total': total(worker_responses),
                        'by_assignment': {key: total(value) for key, value in sorted(by_assignment.items())},
                        'by_role': {key: total(value) for key, value in sorted(by_role.items())}},
            'host': {'files': [str(path) for path in hosts], 'since': since and since.isoformat(),
                     'until_exclusive': until and until.isoformat(), 'total': total(host),
                     'by_trigger': grouped(host, lambda response: response['trigger']),
                     'by_activity': grouped(host, lambda response: activity(response['calls']))},
            'coverage': {'missing': missing}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state', type=Path, required=True, help="the effort's workers.sqlite")
    parser.add_argument('--host', type=Path, action='append', default=[],
                        help='a coordinator transcript (Claude, Codex or Pi); repeatable, needs --since/--until')
    parser.add_argument('--since', help='inclusive ISO timestamp with timezone for host responses')
    parser.add_argument('--until', help='exclusive ISO timestamp with timezone for host responses')
    parser.add_argument('--claude-root', type=Path, default=Path.home() / '.claude/projects')
    parser.add_argument('--codex-root', type=Path, default=Path.home() / '.codex/sessions')
    parser.add_argument('--pi-root', type=Path, default=Path.home() / '.pi/agent/sessions')
    args = parser.parse_args()
    roots = {'claude': args.claude_root, 'codex': args.codex_root, 'pi': args.pi_root}
    try:
        since = until = None
        if args.host:
            if not (args.since and args.until):
                raise ValueError('--host requires --since and --until')
            since, until = timestamp(args.since), timestamp(args.until)
        print(json.dumps(report(args.state, roots, args.host, since, until), indent=2))
    except (OSError, ValueError, sqlite3.Error) as error:
        parser.exit(2, f'{error}\n')


if __name__ == '__main__':
    main()
