#!/usr/bin/env python3
"""Read local Claude JSONL usage over an explicit time window; never estimate credits."""

import argparse
from collections import Counter, defaultdict
from datetime import datetime
import hashlib
import json
from pathlib import Path


FIELDS = ('input_tokens', 'cache_creation_input_tokens', 'cache_read_input_tokens', 'output_tokens')


def timestamp(value):
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('timestamps require an explicit UTC offset')
    return parsed


def aggregate(records):
    total = dict.fromkeys(('responses', *FIELDS, 'thinking_tokens'), 0)
    models, contexts = Counter(), []
    for record in records:
        total['responses'] += 1
        models[record['model']] += 1
        for field in FIELDS:
            total[field] += record['usage'].get(field, 0)
        total['thinking_tokens'] += record['usage'].get('output_tokens_details', {}).get('thinking_tokens', 0)
        contexts.append(sum(record['usage'].get(field, 0) for field in FIELDS[:3]))
    contexts.sort()
    return dict(total, models=dict(models), mean_context=round(sum(contexts) / len(contexts)) if contexts else 0,
                p95_context=contexts[min(len(contexts) - 1, int(len(contexts) * .95))] if contexts else 0)


def scan(root, since, until):
    messages, sources = {}, {}
    quality = {'parse_errors': [], 'invalid_usage': [], 'missing_id_or_usage': 0,
               'invalid_timestamps': [], 'repeated_blocks': 0, 'usage_decreases': 0,
               'conflicting_response_ids': []}
    cross_file = set()
    for path in sorted(root.rglob('*.jsonl')):
        source = str(path)
        worker = path.parent.name == 'subagents'
        family = path.parent.parent.name if worker else path.stem
        size, digest, cwd = path.stat().st_size, hashlib.sha256(), None
        # Freeze each file's byte prefix so an active writer cannot prolong the scan.
        with path.open('rb') as stream:
            remaining, line_no = size, 0
            while remaining:
                raw = stream.readline(remaining)
                if not raw:
                    break
                remaining -= len(raw)
                digest.update(raw)
                line_no += 1
                try:
                    obj = json.loads(raw)
                except (ValueError, UnicodeDecodeError):
                    quality['parse_errors'].append({'path': source, 'line': line_no})
                    continue
                if not isinstance(obj, dict):
                    quality['parse_errors'].append({'path': source, 'line': line_no})
                    continue
                cwd = obj.get('cwd') or cwd
                if obj.get('type') != 'assistant':
                    continue
                msg = obj.get('message') or {}
                if not isinstance(msg, dict) or msg.get('model') == '<synthetic>':
                    continue
                try:
                    stamp = timestamp(obj.get('timestamp', ''))
                except (ValueError, AttributeError, TypeError):
                    quality['invalid_timestamps'].append({'path': source, 'line': line_no})
                    continue
                if stamp >= until:
                    continue
                usage, identity = msg.get('usage'), msg.get('id')
                if not isinstance(identity, str) or not identity or not usage:
                    if stamp >= since:
                        quality['missing_id_or_usage'] += 1
                    continue
                details = (usage.get('output_tokens_details') or {}) if isinstance(usage, dict) else {}
                if (not isinstance(usage, dict) or not isinstance(details, dict)
                        or any(type(value) is not int or value < 0 for value in
                               [*(usage.get(field, 0) for field in FIELDS), details.get('thinking_tokens', 0)])):
                    if stamp >= since:
                        quality['invalid_usage'].append({'path': source, 'line': line_no})
                    continue
                usage = dict(usage, output_tokens_details=details)
                record = dict(time=stamp, path=source, line=line_no, family=family,
                              kind='subagent' if worker else 'session', cwd=cwd,
                              model=msg.get('model') or 'unknown', usage=usage,
                              request_id=obj.get('requestId'))
                if identity in messages:
                    old = messages[identity]
                    first = min(old['time'], stamp)
                    if first >= since:
                        quality['repeated_blocks'] += 1
                        if old['path'] != source:
                            cross_file.add(identity)
                        if old['model'] != record['model'] or old['request_id'] != record['request_id']:
                            quality['conflicting_response_ids'].append(identity)
                        if usage.get('output_tokens', 0) < old['usage'].get('output_tokens', 0):
                            quality['usage_decreases'] += 1
                    # Streaming blocks are cumulative. Keep one observed usage snapshot.
                    if usage.get('output_tokens', 0) > old['usage'].get('output_tokens', 0):
                        messages[identity] = record
                    messages[identity]['time'] = first
                else:
                    messages[identity] = record
        sources[source] = {'bytes': size - remaining, 'sha256': digest.hexdigest()}
    quality['cross_file_duplicate_ids'] = sorted(cross_file)
    return messages.values(), sources, quality


def report(root, since, until, session=None, worktrees=()):
    records, sources, quality = scan(root, since, until)
    selected, native, associated = [], [], []
    worktrees = {str(path.resolve()) for path in worktrees}
    for record in records:
        if record['time'] < since:
            continue
        is_native = session is not None and record['family'] == session
        is_related = record['cwd'] and str(Path(record['cwd']).resolve()) in worktrees
        if session is not None and not (is_native or is_related):
            continue
        selected.append(record)
        if is_native:
            native.append(record)
        elif is_related:
            associated.append(record)
    families, files, hours = defaultdict(list), defaultdict(list), defaultdict(list)
    for record in selected:
        families[record['family']].append(record)
        files[record['path']].append(record)
        hours[record['time'].astimezone(since.tzinfo).replace(minute=0, second=0, microsecond=0).isoformat()].append(record)
    family_totals = {name: aggregate(rows) for name, rows in families.items()}
    return {'since': since.isoformat(), 'until_exclusive': until.isoformat(), 'session': session,
            'total': aggregate(selected), 'native_family': aggregate(native) if session else None,
            'worktree_associated': aggregate(associated), 'subscription_credits': None,
            'limitations': ['Local recorded usage only; not billed credits or subscription percentage.',
                            'Thinking is included in output; cached input is reported separately.',
                            'Worktree association does not establish parentage, hook identity or account.',
                            'Earliest block assigns the window; usage snapshots stop at the cutoff.',
                            'Cross-file duplicate attribution requires review; totals count each ID once.'],
            'families': dict(sorted(family_totals.items(), key=lambda item: item[1]['output_tokens'], reverse=True)),
            'hours': {hour: aggregate(rows) for hour, rows in sorted(hours.items())},
            'files': {name: dict(aggregate(rows), family=rows[0]['family'], kind=rows[0]['kind'],
                                cwds=sorted({row['cwd'] for row in rows if row['cwd']}),
                                first=min(row['time'] for row in rows).isoformat(),
                                last=max(row['time'] for row in rows).isoformat(), **sources[name])
                      for name, rows in files.items()}, 'quality': quality}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path.home() / '.claude/projects')
    parser.add_argument('--since', required=True, help='inclusive ISO timestamp with timezone')
    parser.add_argument('--until', required=True, help='exclusive ISO timestamp with timezone')
    parser.add_argument('--session', help='parent session ID; includes its native subagents')
    parser.add_argument('--related-worktree', type=Path, action='append', default=[],
                        help='also include exact cwd matches, separately attributed; repeatable with --session')
    args = parser.parse_args()
    try:
        since, until = timestamp(args.since), timestamp(args.until)
        if since >= until:
            raise ValueError('--since must precede --until')
        if not args.root.expanduser().is_dir():
            raise ValueError('--root must be an existing transcript directory')
        if args.related_worktree and not args.session:
            raise ValueError('--related-worktree requires --session')
        print(json.dumps(report(args.root.expanduser().resolve(), since, until,
                                args.session, args.related_worktree), indent=2))
    except (OSError, ValueError) as error:
        parser.exit(2, f'{error}\n')


if __name__ == '__main__':
    main()
