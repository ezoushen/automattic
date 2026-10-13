"""Read session-bound native settings without exposing conversation contents."""

import hashlib
import json
from pathlib import Path


def observe(path, runtime, session, worktree):
    """Return observed controls and the source prefix identity; unknown controls stay absent."""
    path = Path(path)
    if not path.is_absolute():
        raise ValueError('Native evidence path must be absolute')
    if runtime == 'opencode':
        raw = path.read_bytes()
        exported = json.loads(raw)
        if not isinstance(exported, dict) or not isinstance(exported.get('info'), dict):
            raise ValueError('Unsupported native export schema')
        info = exported['info']
        if not isinstance(exported.get('messages'), list) or any(
                not isinstance(item, dict) or not isinstance(item.get('info'), dict)
                for item in exported['messages']):
            raise ValueError('Unsupported native message schema')
        latest = next((item['info'] for item in reversed(exported['messages'])
                       if item['info'].get('role') == 'assistant'), None)
        if info.get('id') != session or latest is None or latest.get('sessionID') != session:
            raise ValueError('Native evidence does not belong to the registered session')
        if latest.get('error'):
            raise ValueError('OpenCode has a failed native response; inspect the provider before work')
        turn = exported['messages']
        for index in range(len(turn) - 1, -1, -1):
            if turn[index]['info'].get('role') == 'user':
                turn = turn[index + 1:]
                break
        if any(part.get('type') == 'tool' and part.get('state', {}).get('status') == 'error'
               for item in turn if item['info'].get('role') == 'assistant'
               for part in item.get('parts', [])):
            raise ValueError('OpenCode startup has a failed tool call; inspect it before work')
        if not isinstance(info.get('directory'), str) or Path(info['directory']).resolve() != Path(worktree).resolve():
            raise ValueError('Native evidence worktree does not match the assignment')
        model = latest.get('modelID')
        provider = latest.get('providerID')
        settings = {'runtime': runtime, 'model': provider + '/' + model if provider and model else None,
                    'effort': latest.get('variant')}
        settings = {key: value for key, value in settings.items() if isinstance(value, str) and value.strip()}
        return {'observed': settings, 'session': session, 'worktree': str(Path(worktree).resolve()),
                'source': str(path), 'source_bytes': len(raw), 'source_sha256': hashlib.sha256(raw).hexdigest()}
    if runtime not in ('claude', 'codex', 'pi'):
        raise ValueError('Unsupported native evidence runtime')
    digest, size, latest, header = hashlib.sha256(), 0, None, None
    entries = {}
    with path.open('rb') as stream:
        for line in stream:
            if not line.endswith(b'\n'):
                raise ValueError('Native evidence has an incomplete record; retry observation before work')
            digest.update(line)
            size += len(line)
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError('Native evidence record must be an object')
            if runtime == 'claude' and row.get('type') == 'assistant' and not row.get('isSidechain'):
                if not isinstance(row.get('message'), dict):
                    raise ValueError('Unsupported native assistant schema')
                latest = row
            elif runtime == 'codex' and row.get('type') == 'session_meta':
                header = row['payload']
                if not isinstance(header, dict):
                    raise ValueError('Unsupported native session schema')
            elif runtime == 'codex' and row.get('type') == 'turn_context':
                latest = row['payload']
                if not isinstance(latest, dict):
                    raise ValueError('Unsupported native turn schema')
            elif runtime == 'pi':
                if row.get('type') == 'session':
                    header = row
                else:
                    if not isinstance(row.get('message', {}), dict):
                        raise ValueError('Unsupported native message schema')
                    # Retain branch links and settings only, never message contents.
                    latest = {key: row.get(key) for key in ('id', 'parentId', 'type', 'provider',
                                                           'modelId', 'thinkingLevel')}
                    latest['message'] = {key: row.get('message', {}).get(key)
                                         for key in ('role', 'provider', 'model', 'stopReason')}
                    if not isinstance(latest['id'], str) or latest['id'] in entries:
                        raise ValueError('Invalid native branch entry identity')
                    entries[latest['id']] = latest
    if runtime == 'pi':
        branch, visited, current = [], set(), latest
        while current:
            if current['id'] in visited:
                raise ValueError('Native branch contains a cycle')
            visited.add(current['id'])
            branch.append(current)
            parent = current['parentId']
            if parent is not None and parent not in entries:
                raise ValueError('Native branch parent is missing')
            current = entries.get(parent)
        latest = dict(header or {})
        for entry in reversed(branch):
            if entry['type'] == 'thinking_level_change':
                latest['effort'] = entry['thinkingLevel']
            elif entry['type'] == 'model_change':
                latest['model'] = entry['provider'] + '/' + entry['modelId']
            elif entry['type'] == 'message' and entry['message']['role'] == 'assistant':
                message = entry['message']
                latest['model'] = message['provider'] + '/' + message['model']
                latest['response_failed'] = message['stopReason'] == 'error'
        if latest.get('response_failed'):
            raise ValueError('Pi has a failed native response; inspect the provider before work')
    identity = latest.get('sessionId') if runtime == 'claude' and latest else (header or {}).get('id')
    if latest is None or identity != session:
        raise ValueError('Native evidence does not belong to the registered session')
    if not isinstance(latest.get('cwd'), str):
        raise ValueError('Native evidence worktree does not match the assignment')
    current, assigned = Path(latest['cwd']).resolve(), Path(worktree).resolve()
    if current != assigned:
        if runtime != 'claude' or assigned not in current.parents or not current.is_dir():
            raise ValueError('Native evidence worktree does not match the assignment')
        # Claude updates cwd while navigating; a nested checkout is a different assignment.
        for directory in (current, *current.parents):
            if directory == assigned:
                break
            if (directory / '.git').exists():
                raise ValueError('Native evidence belongs to a nested repository')
    if header and (not isinstance(header.get('cwd'), str)
                   or Path(header['cwd']).resolve() != Path(worktree).resolve()):
        raise ValueError('Native evidence session worktree does not match the assignment')
    effort = latest.get('perTurnEffort') if runtime == 'claude' else None
    if effort is None:
        effort = latest.get('effort')
    model = latest.get('message', {}).get('model') if runtime == 'claude' else latest.get('model')
    settings = {'runtime': runtime, 'model': model, 'effort': effort}
    settings = {key: value for key, value in settings.items() if isinstance(value, str) and value.strip()}
    return {'observed': settings, 'session': session, 'worktree': str(Path(worktree).resolve()),
            'source': str(path), 'source_bytes': size, 'source_sha256': digest.hexdigest()}
