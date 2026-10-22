#!/usr/bin/env python3
"""Local decision evidence, offline inspection and explicit prompt replay."""

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import time
import uuid

import decision_images
import decisions
from journal_store import (CATEGORIES, SOURCES, _assessed, _find, _labels, check, check_checkpoint, inspect, ordered_hash,
                           read, record, reliability, requested_settings, restore_payload, scorecard, text,
                           trace_config)


def export_suite(paths, output, sources=('objective', 'independent')):
    """Write trusted shadow assessments as an adjudicated calibration suite; host labels are excluded."""
    cases, excluded = [], {'host': 0, 'unassessed': 0, 'unavailable': 0, 'images': 0}
    for decision, assessment, _ in _assessed(paths):
        if 'error' in decision['result']:
            excluded['unavailable'] += 1
        elif assessment is None:
            excluded['unassessed'] += 1
        elif assessment.get('source', 'host') not in sources:
            excluded['host'] += 1
        elif 'images' in decision['request']:
            excluded['images'] += 1
        else:
            cases.append({'id': decision['decision_id'], 'request': decision['request'],
                          'expected': assessment['expected'],
                          'evidence': f"{assessment['source']} label by {assessment['actor']}: "
                                      f"{assessment['reason']} ({', '.join(assessment['evidence'])})"})
    if not 1 <= len(cases) <= 200:
        raise ValueError(f'An adjudicated suite needs 1–200 trusted cases; found {len(cases)}')
    # Validate a private temporary file, then publish it without replacing an existing suite.
    output = Path(output)
    temporary = output.with_name(f'.{output.name}.{uuid.uuid4().hex}')
    try:
        with os.fdopen(os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as stream:
            json.dump({'kind': 'adjudicated', 'cases': cases}, stream, indent=2, allow_nan=False)
            stream.write('\n')
        decisions.load_suite(temporary)
        os.link(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)
    return {'output': str(Path(output).resolve()), 'cases': len(cases), 'excluded': excluded}


def replay(path, cases, backend, *, transport=None, max_calls=12, budget_seconds=30):
    """Compare wording and order under saved evidence; never execute recommended actions."""
    if (not isinstance(cases, list) or not cases or type(max_calls) is not int or not 1 <= max_calls <= 60
            or type(budget_seconds) not in (int, float) or not 0 < budget_seconds <= 300):
        raise ValueError('Replay requires cases, 1–60 max calls and a 0–300 second budget')
    rows, plan, seen, image_bytes = read(path), [], set(), 0
    for case in cases:
        if (not isinstance(case, dict) or set(case) - {'decision_id', 'expected', 'evidence', 'instruction'}
                or not text(case.get('decision_id')) or not text(case.get('evidence'))):
            raise ValueError('Each replay case requires decision_id, expected and label evidence')
        did = case['decision_id']
        if did in seen:
            raise ValueError('Duplicate replay decision')
        seen.add(did)
        decision, _ = _find(rows, did)
        _labels(case.get('expected'), decision)
        for key in ('protocol', 'model', 'revision', 'instruction'):
            if backend.get(key) != decision['backend'].get(key):
                raise ValueError(f'Prompt replay requires the recorded backend {key}')
        request = decision['request']
        payload = restore_payload(path, decision)
        image_bytes += sum(len(url) for url in payload.get('images', []))
        if image_bytes > decision_images.MAX_EVALUATION_BYTES:
            raise ValueError('Image evaluation exceeds 32 MiB encoded; narrow the cases')
        variants = [('original', request)]
        if len(request['options']) > 1:
            variants.append(('reversed', dict(request, options=dict(reversed(list(request['options'].items()))))))
        if 'instruction' in case:
            variants.append(('paraphrase', dict(request, instruction=case['instruction'])))
        for name, variant in variants:
            decisions.validate_request(variant)
            wire = copy.deepcopy(payload)
            question = next(iter(wire['questions'].values()))
            if name == 'reversed':
                criteria = question['criteria']
                question['criteria'] = {key: criteria[key] for key in variant['options']}
                question['criteria']['abstain'] = criteria['abstain']
            elif name == 'paraphrase':
                original_instruction = request['instruction']
                if not question['instructions'].startswith(original_instruction):
                    raise ValueError('Captured instruction cannot be separated from shared preferences')
                question['instructions'] = variant['instruction'] + question['instructions'][len(original_instruction):]
            plan.append((case, decision, name, variant, wire))
    if len(plan) > max_calls:
        raise ValueError(f'Replay needs {len(plan)} calls; limit is {max_calls}. Narrow the cases.')
    started, results, originals = time.monotonic(), [], {}
    for case, decision, name, request, wire in plan:
        remaining = budget_seconds - (time.monotonic() - started)
        if remaining <= 0:
            break
        current_backend = dict(backend, timeout_seconds=min(backend.get('timeout_seconds', 20), remaining))
        answer, capture = decisions.evaluate(current_backend, request, transport=transport, wire_payload=wire)
        if 'images' in wire:
            capture['payload'] = dict(capture['payload'], images=decision['payload']['images'])
        did = case['decision_id']
        if name == 'original':
            originals[did] = answer
        original = originals[did]
        valid_pair = 'error' not in answer and 'error' not in original
        results.append(dict(decision_id=did, assignment=decision['assignment'],
                            family=request['family'], variant=name, expected=case['expected'],
                            source_request_hash=decision['request_hash'], request_hash=ordered_hash(wire),
                            evidence=case['evidence'], result=answer, **capture,
                            correct='error' not in answer and answer['choice'] in case['expected'],
                            changed=answer['choice'] != original['choice'] if valid_pair else None))
    variants = {}
    for name in ('original', 'reversed', 'paraphrase'):
        values = [row for row in results if row['variant'] == name]
        if values:
            variants[name] = {'count': len(values), 'accuracy': sum(r['correct'] for r in values) / len(values),
                              'errors': sum('error' in r['result'] for r in values),
                              'changed': sum(r['changed'] is True for r in values)}
    return {'version': 1, 'backend': backend, 'created_at': time.time(), 'variants': variants,
            'implementation': {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                               for name in ('decisions.py', 'decision_journal.py', 'decision_images.py', 'journal_store.py')},
            'planned_calls': len(plan), 'calls': len(results),
            'complete': len(results) == len(plan) and all('error' not in r['result'] for r in results),
            'seconds': round(time.monotonic() - started, 4), 'results': results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('inspect', 'record', 'action', 'execution', 'outcome', 'assessment',
                                           'check', 'replay', 'scorecard', 'reliability', 'export-suite'))
    parser.add_argument('--journal', type=Path, required=True)
    parser.add_argument('--decision-id', help='decision to inspect, annotate or check')
    parser.add_argument('--event', type=Path, help='record: path to annotation JSON, not inline JSON')
    action = parser.add_argument_group('action: record the actual host choice')
    action.add_argument('--actor')
    action.add_argument('--disposition', choices=('accepted', 'overridden', 'fallback'))
    action.add_argument('--choice', help='actual host choice; accepted defaults to the valid recommendation')
    action.add_argument('--reason')
    execution = parser.add_argument_group('execution: requested settings and observed native metadata')
    for source in ('requested', 'observed'):
        for control in ('runtime', 'model', 'effort'):
            execution.add_argument(f'--{source}-{control}')
    parser.add_argument('--evidence', action='append', help='execution/outcome: evidence reference; repeatable')
    parser.add_argument('--model-alias-evidence', action='append',
                        help='execution: verified binding between requested and observed model IDs')
    parser.add_argument('--revision', help='execution/outcome/check: full checked revision or immutable input identity')
    parser.add_argument('--status', choices=('succeeded', 'failed', 'unknown'), help='outcome: verified task result')
    parser.add_argument('--expected', action='append', help='assessment: independently established label; repeatable')
    parser.add_argument('--category', choices=sorted(CATEGORIES),
                        help='assessment: decision failure category; defaults to unknown')
    parser.add_argument('--stage', choices=('launch', 'startup', 'completion'), help='check: required annotations at this handoff')
    parser.add_argument('--family', choices=decisions.PHASE_FAMILIES, help='check: expected phase checkpoint')
    parser.add_argument('--assignment-id', help='check: expected phase identity; use with --family and --repo')
    parser.add_argument('--cases', type=Path, help='reviewed replay cases array or worker scorecard manifest')
    parser.add_argument('--repo', type=Path, help='replay/check: canonical project scope')
    parser.add_argument('--user-executors', type=Path, default=Path.home() / '.config/zloop/executors.json')
    parser.add_argument('--session')
    parser.add_argument('--output', type=Path, help='new replay report or export-suite file')
    parser.add_argument('--source', action='append', choices=SOURCES,
                        help='assessment: label source (once); reliability/export-suite: sources to include')
    parser.add_argument('--also', type=Path, action='append', default=[],
                        help='reliability/export-suite: additional journal; repeatable')
    parser.add_argument('--max-calls', type=int, default=12)
    parser.add_argument('--budget-seconds', type=float, default=30)
    args = parser.parse_args()
    try:
        direct_fields = {
            'action': ('actor', 'disposition', 'choice', 'reason'),
            'execution': ('requested_runtime', 'requested_model', 'requested_effort',
                          'observed_runtime', 'observed_model', 'observed_effort', 'evidence',
                          'revision', 'model_alias_evidence'),
            'outcome': ('status', 'evidence', 'revision'),
            'assessment': ('actor', 'expected', 'category', 'evidence', 'reason', 'source'),
            'check': ('stage', 'revision', 'family', 'assignment_id'),
        }
        supplied = {field for fields in direct_fields.values() for field in fields
                    if getattr(args, field) is not None}
        unexpected = supplied - set(direct_fields.get(args.action, ())) - (
            {'source'} if args.action in ('reliability', 'export-suite') else set())
        if unexpected:
            raise ValueError(f'{args.action} does not accept: ' + ', '.join(sorted(unexpected)))
        if args.action in direct_fields:
            phase_check = args.action == 'check' and (args.family is not None or args.assignment_id is not None)
            if phase_check:
                if not args.family or not args.assignment_id or not args.repo or args.decision_id:
                    raise ValueError('Phase check requires --repo, --family and --assignment-id, not --decision-id')
            elif not text(args.decision_id) or args.repo or args.session:
                raise ValueError(f'{args.action} requires --decision-id and its own fields, not record/replay inputs')
            if any((args.event, args.cases, args.output)):
                raise ValueError('Direct annotations/checks do not accept record/replay inputs')
            if args.action == 'check':
                if phase_check:
                    session = args.session or os.environ.get('ZLOOP_SESSION')
                    trace = trace_config(args.journal, args.repo, args.assignment_id, session)
                    if args.stage is None:
                        raise ValueError('Phase check requires --stage')
                    policy, _ = decisions.load_policy(args.repo, args.user_executors, session)
                    rows = read(args.journal) if Path(args.journal).is_file() else []
                    # The journal wins over current configuration; a record under any session blocks "disabled".
                    recorded = any(row['event'] == 'checkpoint' and row['family'] == args.family
                                   and row['assignment'] == trace['assignment'] and row['repo'] == trace['repo']
                                   for row in rows)
                    if not recorded and 'backend' in policy and args.family not in policy['enabled']:
                        result = {'family': args.family, 'assignment': args.assignment_id, 'stage': args.stage,
                                  'checkpoint_status': 'disabled', 'complete': True, 'missing_evidence': []}
                    else:
                        result = check_checkpoint(args.journal, trace, args.family, args.stage, args.revision)
                else:
                    result = check(args.journal, args.decision_id, args.stage, args.revision)
            else:
                event = {'event': args.action, 'decision_id': args.decision_id}
                if args.action == 'execution':
                    for source in ('requested', 'observed'):
                        event[source] = {control: getattr(args, f'{source}_{control}')
                                         for control in ('runtime', 'model', 'effort')
                                         if getattr(args, f'{source}_{control}') is not None}
                    if not event['requested']:
                        # Requested settings must equal the recorded host choice; derive them.
                        decision, latest = _find(read(args.journal), args.decision_id)
                        if 'action' in latest:
                            choice = decision['request']['options'].get(latest['action']['choice'])
                            if choice is not None:
                                event['requested'] = requested_settings(choice)
                        if not event['requested']:
                            raise ValueError('Requested settings cannot be derived from the recorded action; '
                                             'pass --requested-runtime and any configured model/effort flags')
                    event['evidence'] = args.evidence or []
                    if args.model_alias_evidence is not None:
                        event['model_alias_evidence'] = args.model_alias_evidence
                else:
                    event.update({field: getattr(args, field) for field in direct_fields[args.action]
                                  if getattr(args, field) is not None})
                    if args.action == 'action' and args.disposition == 'accepted' and args.choice is None:
                        decision, _ = _find(read(args.journal), args.decision_id)
                        event['choice'] = decision['result']['choice']
                    if args.action == 'outcome':
                        event['evidence'] = args.evidence or []
                    if args.action == 'assessment':
                        if not args.source or len(args.source) != 1:
                            raise ValueError('assessment requires one --source objective|independent|host')
                        event.update(source=args.source[0])
                        event.setdefault('category', 'unknown')
                        event.setdefault('evidence', [])
                if args.revision is not None:
                    event['revision'] = args.revision
                result = record(args.journal, event)
                # The read-only handoff check for this boundary; recording already succeeded.
                stage = {'action': 'launch', 'execution': 'startup', 'outcome': 'completion',
                         'assessment': 'completion'}[args.action]
                result = dict(result, handoff=check(args.journal, args.decision_id, stage, args.revision))
        elif args.action == 'inspect':
            if args.event or args.cases or args.output:
                raise ValueError('Inspection accepts --decision-id, not record/replay inputs')
            result = inspect(args.journal, args.decision_id)
        elif args.action == 'record':
            if not args.event or args.decision_id or args.cases or args.output:
                raise ValueError('Recording requires only --journal and --event')
            result = record(args.journal, json.loads(args.event.read_text()))
        elif args.action in ('reliability', 'export-suite'):
            if any((args.event, args.cases, args.decision_id, args.repo, args.session)):
                raise ValueError(f'{args.action} accepts --journal, --also, --source and --output only')
            paths = [args.journal, *args.also]
            if args.action == 'reliability':
                if args.output:
                    raise ValueError('reliability prints its report; --output is for export-suite')
                result = reliability(paths, tuple(args.source or ('objective', 'independent')))
            else:
                if not args.output or (args.source and 'host' in args.source):
                    raise ValueError('export-suite requires --output and excludes host labels')
                result = export_suite(paths, args.output, tuple(args.source or ('objective', 'independent')))
        elif args.action == 'scorecard':
            if not args.cases or any((args.event, args.output, args.decision_id, args.repo, args.session)):
                raise ValueError('Scorecard requires only --journal and --cases')
            result = scorecard(args.journal, json.loads(args.cases.read_text()))
        else:
            if not args.repo or not args.cases or not args.output or args.event or args.decision_id:
                raise ValueError('Replay requires --repo, --cases and --output')
            if args.output.exists() or not args.output.parent.is_dir():
                raise ValueError('Choose a new output file in an existing directory')
            policy, _ = decisions.load_policy(args.repo, args.user_executors, args.session)
            report = replay(args.journal, json.loads(args.cases.read_text()), policy['backend'],
                            max_calls=args.max_calls, budget_seconds=args.budget_seconds)
            with os.fdopen(os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as stream:
                json.dump(report, stream, indent=2, allow_nan=False)
                stream.write('\n')
            result = {key: value for key, value in report.items() if key != 'results'}
            result['report'] = str(args.output.resolve())
        print(json.dumps(result, indent=2))
        if args.action == 'check' and not result['complete']:
            parser.exit(1)
        if 'handoff' in result and not result['handoff']['complete']:
            parser.exit(1)  # Recorded; the handoff still lacks the listed evidence.
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(2, f'{error}\n')


if __name__ == '__main__':
    main()
