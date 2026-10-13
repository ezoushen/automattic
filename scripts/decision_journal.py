#!/usr/bin/env python3
"""Local decision evidence, offline inspection and explicit prompt replay."""

import argparse
import copy
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import time
import uuid

import decision_images

EVENTS = {'decision', 'action', 'execution', 'outcome', 'assessment', 'checkpoint'}
CATEGORIES = {'context', 'prompt', 'options', 'model', 'host', 'execution', 'none', 'unknown'}
# Who established an assessment label: a rerun/later observed state, an independent reviewer, or the host.
SOURCES = ('objective', 'independent', 'host')
SHADOW_FAMILIES = ('failure-cause', 'wake-triage')


def text(value):
    return isinstance(value, str) and bool(value.strip())


def trace_config(path, repo, assignment, session=None):
    if path is None:
        if assignment is not None:
            raise ValueError('--assignment-id requires --journal')
        return None
    path = Path(path).expanduser()
    if not path.is_absolute() or not text(assignment):
        raise ValueError('Recording requires an absolute --journal and a nonempty --assignment-id')
    return {'path': str(path), 'repo': str(Path(repo).resolve()),
            'assignment': assignment, 'session': session}


def _read(stream):
    rows = []
    for number, line in enumerate(stream, 1):
        if not line.endswith('\n'):
            raise ValueError(f'Incomplete journal line {number}; preserve and repair it before appending')
        row = json.loads(line)
        if (not isinstance(row, dict) or row.get('version') != 1
                or row.get('event') not in EVENTS
                or not text(row.get('checkpoint_id' if row.get('event') == 'checkpoint' else 'decision_id'))):
            raise ValueError(f'Invalid journal event on line {number}')
        if row['event'] == 'checkpoint':
            if (row.get('status') not in ('consulted', 'skipped')
                    or not all(text(row.get(key)) for key in ('family', 'repo', 'assignment', 'input_hash'))
                    or (row['status'] == 'consulted' and not text(row.get('decision_id')))):
                raise ValueError(f'Invalid checkpoint on line {number}')
            if row['status'] == 'skipped' and (
                    row.get('skip_reason') not in ('disabled', 'settled', 'required-action', 'human-reserved')
                    or not text(row.get('reason')) or not isinstance(row.get('evidence'), list)
                    or not all(text(item) for item in row['evidence'])
                    or (row['skip_reason'] != 'disabled' and not row['evidence'])):
                raise ValueError(f'Invalid skipped checkpoint on line {number}')
        rows.append(row)
    return rows


def read(path):
    with Path(path).open() as stream:
        fcntl.flock(stream, fcntl.LOCK_SH)
        return _read(stream)


def _append(path, event, validate):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = dict(event, version=1, at=time.time())
    encoded = json.dumps(data, allow_nan=False) + '\n'
    with os.fdopen(os.open(path, os.O_CREAT | os.O_RDWR, 0o600), 'r+') as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        rows = _read(stream)
        validate(rows)
        stream.seek(0, os.SEEK_END)
        stream.write(encoded)
    return data


def ordered_hash(value):
    return hashlib.sha256(json.dumps(value, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def append_decision(trace, backend, request, result, capture, fingerprint):
    did = str(uuid.uuid4())
    payload = capture['payload']
    event = dict(event='decision', decision_id=did,
                 **{key: value for key, value in trace.items() if key != 'path'},
                 backend=backend, request=request, result=result, **capture,
                 fingerprint=fingerprint, request_hash=ordered_hash(payload),
                 prompt_hash=ordered_hash(payload['questions']) if payload else None)
    event['payload'] = decision_images.retain(trace['path'], payload, request.get('images', []))
    if payload and 'images' in payload:
        event['image_preprocessing'] = {'client': 'original-bytes', 'server': 'unknown'}
    _append(trace['path'], event, lambda rows: None)
    return did


def restore_payload(path, decision):
    payload = decision_images.restore(path, decision['payload'])
    if not isinstance(payload, dict) or ordered_hash(payload) != decision['request_hash']:
        raise ValueError('Replay requires an intact captured request')
    return payload


def _find(rows, did):
    matches = [row for row in rows if row.get('decision_id') == did]
    decisions = [row for row in matches if row['event'] == 'decision']
    if len(decisions) != 1:
        raise ValueError(f'Expected one recorded decision for {did!r}')
    return decisions[0], {row['event']: row for row in matches}


def _current_annotations(rows, did, revision=None):
    """An outcome must follow the latest execution and cover the requested revision."""
    decision, latest = _find(rows, did)
    positions = {row['event']: index for index, row in enumerate(rows) if row.get('decision_id') == did}
    if positions.get('outcome', -1) < positions.get('execution', -1):
        latest.pop('outcome', None)
    if revision is not None:
        if not text(revision):
            raise ValueError('Revision must be a nonempty identity')
        if latest.get('outcome', {}).get('revision') != revision:
            latest.pop('outcome', None)
    return decision, latest


def _labels(expected, decision):
    allowed = set(decision['request']['options']) | {'abstain'}
    if (not isinstance(expected, list) or not expected or not all(text(x) for x in expected)
            or len(set(expected)) != len(expected) or not set(expected) <= allowed):
        raise ValueError('Expected labels must name original choices or abstain')


def execution_status(event):
    """Compare only requested controls; missing runtime evidence stays unverified."""
    if not event:
        return 'unverified'
    requested, observed = event['requested'], event['observed']
    if any(key in observed and observed[key] != value
           and not (key == 'model' and event.get('model_alias_evidence'))
           for key, value in requested.items()):
        return 'mismatch'
    return 'matched' if requested.keys() <= observed.keys() else 'unverified'


def find_checkpoint(rows, trace, family):
    matches = [row for row in rows if row['event'] == 'checkpoint' and row['family'] == family
               and all(row.get(key) == trace.get(key) for key in ('repo', 'session', 'assignment'))]
    if len(matches) > 1:
        raise ValueError('Duplicate phase checkpoint identity')
    return matches[0] if matches else None


def append_checkpoint(trace, family, input_hash, *, decision_id=None, skip=None, reason=None, evidence=None):
    event = dict(event='checkpoint', checkpoint_id=str(uuid.uuid4()), family=family,
                 input_hash=input_hash, status='consulted' if decision_id else 'skipped',
                 **{key: value for key, value in trace.items() if key != 'path'})
    if decision_id:
        event['decision_id'] = decision_id
    else:
        event.update(skip_reason=skip, reason=reason, evidence=evidence or [])

    def validate(rows):
        if find_checkpoint(rows, trace, family):
            raise ValueError('Checkpoint already recorded; reuse it or start a new assignment')
        if decision_id:
            decision, _ = _find(rows, decision_id)
            if decision['request']['family'] != family or any(
                    decision.get(key) != trace.get(key) for key in ('repo', 'session', 'assignment')):
                raise ValueError('Checkpoint decision must match its family and assignment')
        elif (skip not in ('disabled', 'settled', 'required-action', 'human-reserved') or not text(reason)
              or not isinstance(event['evidence'], list) or not all(text(item) for item in event['evidence'])
              or (skip != 'disabled' and not event['evidence'])):
            raise ValueError('A skipped checkpoint requires a supported reason and evidence')
    return _append(trace['path'], event, validate)


def requested_settings(option):
    """Launch settings named by a structured worker-selection option."""
    try:
        option = json.loads(option)
    except (TypeError, ValueError):
        raise ValueError('Execution requires a structured worker option') from None
    if not isinstance(option, dict):
        raise ValueError('Execution requires a structured worker option')
    return {key: option[source] for key, source in
            (('runtime', 'runtime'), ('model', 'model'), ('effort', 'thinking'))
            if option.get(source) is not None}


def record(path, event):
    """Append host action, runtime evidence, outcome or independent assessment."""
    if not Path(path).is_file():
        raise ValueError('Annotations require an existing decision journal')
    def validate(rows):
        kind = event.get('event')
        fields = {
            'action': {'actor', 'disposition', 'choice', 'reason'},
            'execution': {'requested', 'observed', 'evidence', 'revision', 'model_alias_evidence'},
            'outcome': {'status', 'evidence', 'metrics', 'revision'},
            'assessment': {'actor', 'expected', 'category', 'evidence', 'reason', 'source'},
        }
        if kind not in fields or set(event) - fields[kind] - {'event', 'decision_id'}:
            raise ValueError('Invalid annotation event or fields')
        decision, latest = _find(rows, event.get('decision_id'))
        if 'revision' in event and not text(event['revision']):
            raise ValueError('Revision must be a nonempty identity')
        if kind in ('action', 'assessment') and not all(text(event.get(k)) for k in ('actor', 'reason')):
            raise ValueError('An action or assessment requires actor and reason')
        if kind == 'action':
            if 'action' in latest:
                raise ValueError('Action already recorded; changed evidence/action needs a new decision')
            if event.get('disposition') not in ('accepted', 'overridden', 'fallback') or not text(event.get('choice')):
                raise ValueError('Action requires disposition and actual choice')
            result = decision['result']
            if event['disposition'] == 'accepted' and (
                    result['status'] != 'recommended' or event['choice'] != result['choice']):
                raise ValueError('Acceptance must match the valid recommendation')
        else:
            evidence = event.get('evidence')
            if not isinstance(evidence, list) or not all(text(x) for x in evidence):
                raise ValueError('Evidence must be a list of references')
            if kind == 'execution':
                if decision['request']['family'] != 'worker-selection' or 'action' not in latest:
                    raise ValueError('Execution requires a worker-selection action')
                if not evidence:
                    raise ValueError('Execution requires runtime evidence')
                for field in ('requested', 'observed'):
                    settings = event.get(field)
                    if (not isinstance(settings, dict) or set(settings) - {'runtime', 'model', 'effort'}
                            or any(not text(value) for value in settings.values())):
                        raise ValueError('Execution settings accept runtime, model and effort strings')
                if not text(event['requested'].get('runtime')):
                    raise ValueError('Requested execution requires a runtime')
                if 'model_alias_evidence' in event:
                    aliases = event['model_alias_evidence']
                    if (not isinstance(aliases, list) or not aliases or not all(text(x) for x in aliases)
                            or not all(text(event[field].get('model')) for field in ('requested', 'observed'))):
                        raise ValueError('A model alias requires both identifiers and verified binding evidence')
                choice = decision['request']['options'].get(latest['action']['choice'])
                if choice is not None:
                    if event['requested'] != requested_settings(choice):
                        raise ValueError('Requested settings must match the recorded host choice')
                previous = latest.get('execution')
                if previous and previous['requested'] != event['requested']:
                    raise ValueError('Changed requested settings need a new decision')
            elif kind == 'outcome':
                if 'action' not in latest:
                    raise ValueError('Record the actual host action before its outcome')
                if event.get('status') not in ('succeeded', 'failed', 'unknown'):
                    raise ValueError('Outcome requires succeeded, failed or unknown')
                if event['status'] != 'unknown' and not evidence:
                    raise ValueError('A known outcome requires verification evidence')
                metrics = event.get('metrics', {})
                if not isinstance(metrics, dict) or any(
                        not text(k) or type(v) not in (int, float) or not math.isfinite(v) or v < 0
                        for k, v in metrics.items()):
                    raise ValueError('Metrics must be measured, finite, nonnegative numbers')
            else:
                _labels(event.get('expected'), decision)
                if not evidence or event.get('category') not in CATEGORIES:
                    raise ValueError('Assessment requires evidence and a supported failure category')
                if 'source' in event and event['source'] not in SOURCES:
                    raise ValueError('Assessment source must be objective, independent or host')
    return _append(path, event, validate)


def inspect(path, decision_id=None):
    rows = read(path)
    if decision_id:
        _, latest = _find(rows, decision_id)
        return latest
    summaries = []
    for decision in (row for row in rows if row['event'] == 'decision'):
        _, latest = _current_annotations(rows, decision['decision_id'])
        result = decision['result']
        assessment = latest.get('assessment')
        action = latest.get('action', {})
        execution = latest.get('execution')
        family = decision['request']['family']
        required = (['action', 'execution', 'outcome'] if family == 'worker-selection'
                    else ['assessment'] if family in ('failure-cause', 'wake-triage') else ['action', 'outcome'])
        summaries.append({
            'decision_id': decision['decision_id'], 'assignment': decision['assignment'],
            'family': decision['request']['family'], 'model': decision['backend']['model'],
            'prompt_hash': decision['prompt_hash'], 'choice': result['choice'],
            'status': result['status'], 'error': result.get('error'),
            'selected_probability': result.get('probabilities', {}).get(result['choice']),
            'provider_confidence': result.get('confidence'), 'seconds': decision['seconds'],
            'shadow_auto_accept': result.get('shadow_auto_accept'),
            'usage': decision['response'].get('usage') if isinstance(decision.get('response'), dict) else None,
            **({'images': decision['payload']['images']} if (decision.get('payload') or {}).get('images') else {}),
            'disposition': action.get('disposition'), 'host_choice': action.get('choice'),
            'execution': execution,
            'execution_status': execution_status(execution),
            'missing_evidence': [kind for kind in required if kind not in latest],
            'warnings': result.get('warnings', []),
            'outcome': latest.get('outcome', {}).get('status', 'unknown'),
            'category': assessment['category'] if assessment else None,
            # A failed call is an unavailable answer, not a wrong one.
            'correct': result['choice'] in assessment['expected']
                       if assessment and 'error' not in result else None})
    checkpoints = [_checkpoint_check(rows, row, 'completion')
                   for row in rows if row['event'] == 'checkpoint']
    return {'count': len(summaries), 'decisions': summaries, 'checkpoints': checkpoints}


def _check(rows, decision_id, stage, revision=None):
    if stage not in ('launch', 'startup', 'completion'):
        raise ValueError('Check stage must be launch, startup or completion')
    decision, latest = _current_annotations(rows, decision_id, revision)
    if decision['request']['family'] in ('failure-cause', 'wake-triage'):
        # Shadow labels have no host action; completion needs the independent assessment.
        missing = ['assessment'] if stage == 'completion' and 'assessment' not in latest else []
        return {'decision_id': decision_id, 'stage': stage, 'complete': not missing,
                'missing_evidence': missing, 'execution_status': None,
                'outcome': latest.get('outcome', {}).get('status', 'unknown')}
    worker = decision['request']['family'] == 'worker-selection'
    if worker and stage == 'startup' and revision is not None:
        if latest.get('execution', {}).get('revision') != revision:
            latest.pop('execution', None)
    required = ['action']
    if worker and stage != 'launch':
        required.append('execution')
    if stage == 'completion':
        required.append('outcome')
    missing = [kind for kind in required if kind not in latest]
    return {'decision_id': decision_id, 'stage': stage, 'complete': not missing,
            'missing_evidence': missing,
            'execution_status': execution_status(latest.get('execution')) if worker else None,
            'outcome': latest.get('outcome', {}).get('status', 'unknown')}


def check(path, decision_id, stage, revision=None):
    return _check(read(path), decision_id, stage, revision)


def _assessed(paths, sources=None):
    """Yield (decision, latest assessment or None, excluded by source) once per shadow decision."""
    seen = set()
    for path in paths:
        rows = read(path)
        for decision in (row for row in rows if row['event'] == 'decision'):
            if decision['request']['family'] not in SHADOW_FAMILIES or decision['decision_id'] in seen:
                continue
            seen.add(decision['decision_id'])
            assessments = [row for row in rows if row['event'] == 'assessment'
                           and row['decision_id'] == decision['decision_id']]
            # The latest label from an included source; a later host label cannot erase a trusted one.
            allowed = [row for row in assessments if sources is None or row.get('source', 'host') in sources]
            yield decision, allowed[-1] if allowed else None, bool(assessments) and not allowed


def reliability(paths, sources=('objective', 'independent')):
    """Offline agreement report for shadow labels; outages are unavailable, never wrong.

    Host labels are excluded unless requested: agreement with the host is not correctness.
    """
    def rate(rows):
        return {'count': len(rows), 'accuracy': sum(ok for *_, ok in rows) / len(rows) if rows else None}
    families = {}
    for decision, assessment, excluded in _assessed(paths, sources):
        family = families.setdefault(decision['request']['family'],
                                     {'rows': [], 'unavailable': 0, 'unassessed': 0, 'excluded_by_source': 0})
        result = decision['result']
        if 'error' in result:
            family['unavailable'] += 1
        elif excluded:
            family['excluded_by_source'] += 1
        elif assessment is None:
            family['unassessed'] += 1
        else:
            family['rows'].append((decision, assessment, result['choice'] in assessment['expected']))
    report = {}
    for name, family in sorted(families.items()):
        rows = family['rows']
        bins = []
        for index in range(5):
            # Integer bin indexes avoid float edges double-counting 0.6; confidence 1.0 joins the top bin.
            group = [row for row in rows if 'confidence' in row[0]['result']
                     and min(int(row[0]['result']['confidence'] * 5), 4) == index]
            confidences = [row[0]['result']['confidence'] for row in group]
            bins.append(dict(range=[index / 5, (index + 1) / 5], **rate(group),
                             mean_confidence=round(sum(confidences) / len(confidences), 4) if group else None))
        groups = {}
        for key, select in (('by_source', lambda d, a: a.get('source', 'host')),
                            ('by_repo', lambda d, a: d['repo']),
                            ('by_week', lambda d, a: time.strftime('%G-W%V', time.gmtime(d['at'])))):
            values = {}
            for row in rows:
                values.setdefault(select(*row[:2]), []).append(row)
            groups[key] = {value: rate(items) for value, items in sorted(values.items())}
        confusion, wrong = {}, {}
        for decision, assessment, ok in rows:
            # Credit the label actually matched; otherwise the primary expected label.
            cell = confusion.setdefault(decision['result']['choice'] if ok else assessment['expected'][0], {})
            cell[decision['result']['choice']] = cell.get(decision['result']['choice'], 0) + 1
            if not ok:
                wrong[assessment['category']] = wrong.get(assessment['category'], 0) + 1
        report[name] = {'assessed': len(rows), 'unavailable': family['unavailable'],
                        'unassessed': family['unassessed'], 'excluded_by_source': family['excluded_by_source'],
                        'accuracy': rate(rows)['accuracy'],
                        'no_confidence': sum('confidence' not in row[0]['result'] for row in rows),
                        'confidence_bins': bins, 'confusion': confusion,
                        'wrong_by_category': dict(sorted(wrong.items())), **groups}
    return {'sources': list(sources) if sources is not None else list(SOURCES), 'families': report}


def export_suite(paths, output, sources=('objective', 'independent')):
    """Write trusted shadow assessments as an adjudicated calibration suite; host labels are excluded."""
    import decisions
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


def scorecard(path, manifest):
    """Summarize independently reviewed worker trials without inference or routing changes."""
    if not isinstance(manifest, dict) or not all(text(manifest.get(k)) for k in ('task_family', 'rubric')):
        raise ValueError('Scorecard requires a task family and predeclared rubric reference')
    if manifest.get('mode') not in ('controlled', 'historical'):
        raise ValueError('Scorecard mode must be controlled or historical; keep their trials separate')
    if manifest.get('context_policy') not in ('fresh', 'same-assignment-continuation'):
        raise ValueError('Scorecard context policy must be fresh or same-assignment-continuation')
    cases = manifest.get('cases')
    candidates = manifest.get('candidates')
    trials = manifest.get('trials')
    if not isinstance(cases, list) or not cases or not isinstance(candidates, list) or not candidates or not isinstance(trials, list):
        raise ValueError('Scorecard requires nonempty cases/candidates and a trials list')
    controls = ('runtime', 'model', 'effort')
    case_map = {}
    for case in cases:
        if not isinstance(case, dict) or not all(text(case.get(k)) for k in ('case_id', 'input_revision', 'acceptance')):
            raise ValueError('Each case requires an ID, pinned input revision and acceptance reference')
        if case['case_id'] in case_map:
            raise ValueError('Case IDs must be unique')
        case_map[case['case_id']] = case
    groups = {}
    for settings in candidates:
        if (not isinstance(settings, dict) or set(settings) != set(controls)
                or not all(text(settings[k]) for k in ('runtime', 'model'))
                or settings['effort'] is not None and not text(settings['effort'])):
            raise ValueError('Candidates require actual runtime, model and effort (null for no control)')
        key = tuple(settings[k] for k in controls)
        if key in groups:
            raise ValueError('Candidates must be unique')
        groups[key] = dict(settings=settings, graded_count=0, accepted_count=0,
                           case_counts={case_id: 0 for case_id in case_map}, metrics={})
    rows = read(path)
    seen, excluded, results = set(), [], []
    for trial in trials:
        if not isinstance(trial, dict) or not all(text(trial.get(k)) for k in
                ('case_id', 'decision_id', 'revision', 'worker', 'reviewer')):
            raise ValueError('Trials require case, decision, checked revision, worker and reviewer identities')
        if trial['case_id'] not in case_map or trial['decision_id'] in seen:
            raise ValueError('Trials must reference declared cases and unique decisions')
        seen.add(trial['decision_id'])
        verdict, category = trial.get('verdict'), trial.get('category')
        if verdict not in ('accepted', 'rejected', 'unknown') or category not in ('none', 'implementation', 'environment', 'provider', 'unknown'):
            raise ValueError('Trials require a supported verdict and failure category')
        evidence = trial.get('evidence')
        if not isinstance(evidence, list) or not evidence or not all(text(ref) for ref in evidence):
            raise ValueError('Trials require independent review evidence references')
        decision, latest = _current_annotations(rows, trial['decision_id'], trial['revision'])
        execution, outcome = latest.get('execution', {}), latest.get('outcome', {})
        checked = _check(rows, trial['decision_id'], 'completion', trial['revision'])
        observed = execution.get('observed', {})
        key = tuple(observed.get(k) for k in controls)
        reason = None
        if decision['request']['family'] != 'worker-selection':
            reason = 'not-worker-selection'
        elif trial['worker'] == trial['reviewer']:
            reason = 'review-not-independent'
        elif not checked['complete'] or outcome.get('status') == 'unknown':
            reason = 'incomplete-outcome'
        elif execution_status(execution) != 'matched' or not all(text(observed.get(k)) for k in ('runtime', 'model')):
            reason = 'settings-unverified'
        elif execution.get('revision') != case_map[trial['case_id']]['input_revision']:
            reason = 'input-mismatch'
        elif key not in groups:
            reason = 'undeclared-candidate'
        elif verdict == 'unknown' or category in ('environment', 'provider', 'unknown'):
            reason = category if verdict != 'unknown' else 'unreviewed'
        elif (verdict == 'accepted') != (outcome['status'] == 'succeeded') or category != ('none' if verdict == 'accepted' else 'implementation'):
            reason = 'verdict-conflict'
        result = dict(trial, execution=execution, outcome=outcome, excluded_reason=reason)
        results.append(result)
        if reason:
            excluded.append({'decision_id': trial['decision_id'], 'case_id': trial['case_id'], 'reason': reason})
            continue
        group = groups[key]
        group['graded_count'] += 1
        group['accepted_count'] += verdict == 'accepted'
        group['case_counts'][trial['case_id']] += 1
        if verdict == 'accepted':
            for name, value in outcome.get('metrics', {}).items():
                group['metrics'].setdefault(name, []).append(value)
    for key, group in groups.items():
        group['quality_score'] = None
        if all(group['case_counts'].values()):
            rates = [sum(r['verdict'] == 'accepted' for r in results if not r['excluded_reason']
                         and r['case_id'] == case_id and tuple(r['execution']['observed'].get(k) for k in controls) == key)
                     / count for case_id, count in group['case_counts'].items()]
            group['quality_score'] = 100 * sum(rates) / len(rates)
        group['metrics'] = {name: {'count': len(values), 'mean': sum(values) / len(values)}
                            for name, values in group['metrics'].items()}
    return {'task_family': manifest['task_family'], 'rubric': manifest['rubric'], 'mode': manifest['mode'], 'cases': cases,
            'context_policy': manifest['context_policy'],
            'manifest_hash': ordered_hash(manifest), 'journal_hash': ordered_hash(rows),
            'candidates': list(groups.values()), 'excluded': excluded, 'results': results}


def _checkpoint_check(rows, event, stage, revision=None):
    result = {'checkpoint_id': event['checkpoint_id'], 'checkpoint_status': event['status'],
              'family': event['family'], 'assignment': event['assignment'],
              'repo': event['repo'], 'session': event.get('session'),
              'skip_reason': event.get('skip_reason'), 'reason': event.get('reason'),
              'evidence': event.get('evidence', [])}
    if event['status'] == 'consulted':
        result.update(_check(rows, event['decision_id'], stage, revision))
    else:
        result.update(stage=stage, complete=True, missing_evidence=[])
    return result


def check_checkpoint(path, trace, family, stage, revision=None):
    import decisions
    if family not in decisions.FAMILIES or stage not in ('launch', 'startup', 'completion'):
        raise ValueError('A checkpoint check requires a supported family and stage')
    rows = read(path) if Path(path).is_file() else []
    event = find_checkpoint(rows, trace, family)
    if event is None:
        return {'family': family, 'assignment': trace['assignment'], 'stage': stage,
                'checkpoint_status': 'missing', 'complete': False, 'missing_evidence': ['checkpoint']}
    return _checkpoint_check(rows, event, stage, revision)


def replay(path, cases, backend, *, transport=None, max_calls=12, budget_seconds=30):
    """Compare wording and order under saved evidence; never execute recommended actions."""
    import decisions
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
                               for name in ('decisions.py', 'decision_journal.py', 'decision_images.py')},
            'planned_calls': len(plan), 'calls': len(results),
            'complete': len(results) == len(plan) and all('error' not in r['result'] for r in results),
            'seconds': round(time.monotonic() - started, 4), 'results': results}


def main():
    import decisions
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
    parser.add_argument('--user-executors', type=Path, default=Path.home() / '.config/automattic/executors.json')
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
                    import decisions
                    session = args.session or os.environ.get('AUTOMATTIC_SESSION')
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
            import decisions
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
