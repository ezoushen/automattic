#!/usr/bin/env python3
"""Resolve worker choices; session state is written only by explicit save/reset options."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import sqlite3
import tempfile
import time
import allowance
import capacity
import decisions
import outcomes

from decisions import systemone_request


ROOT = Path(__file__).resolve().parents[1]
HARNESSES = ('claude', 'codex', 'pi', 'opencode')
ROLES = tuple(sorted(path.stem for path in (ROOT / 'roles').glob('*.md')))
EFFORTS = ('none', 'off', 'minimal', 'low', 'medium', 'high', 'xhigh', 'max', 'ultra')
DEFAULT_ROUTER = {'type': 'skill', 'skill': 'automattic:model-routing'}


def validate_execution_config(data, location):
    """Validate only bundled schemas; configuration never loads code or remote schemas."""
    if isinstance(data, dict) and ({'routes', 'executors'} & data.keys()):
        raise ValueError(f'{location}: legacy executor packages/routes require explicit migration '
                         'to agents.<role>.executor.type/config; see harnesses/executors.md')
    if isinstance(data, dict) and isinstance(data.get('models'), dict):
        for name, definition in data['models'].items():
            if isinstance(definition, dict) and ({'model', 'executors'} & definition.keys()):
                raise ValueError(f'{location}: models.{name} requires runtime bindings; move the model ID '
                                 f'to models.{name}.runtimes.<runtime>.id and launch routes to top-level runtimes; '
                                 'see harnesses/selection.md')
    if isinstance(data, dict):
        profiles = data.get('profiles', {})
        agents = data.get('agents', {})
        if isinstance(profiles, dict) and any(isinstance(profile, dict) and 'agents' in profile
                                             for profile in profiles.values()):
            raise ValueError(f'{location}: migrate profile agents to shared agents; profiles now contain '
                             'profiles.<name>.<role>.<worker-runtime>.candidate/thinking')
        if isinstance(agents, dict) and any(isinstance(entry, dict) and 'candidates' in entry and 'default' in entry
                                           for entry in agents.values()):
            raise ValueError(f'{location}: migrate pool defaults to sparse routing profiles; '
                             'agents define candidates only; see harnesses/selection.md')
    validate_schema(data, location, 'executors.schema.json')
    calibration = data.get('decisions', {}).get('calibration')
    if calibration and Path(calibration['suite']).resolve() == Path(calibration['baseline']).resolve():
        raise ValueError(f'{location}: calibration suite and baseline must be different files')
    groups = [data.get('agents', {})]
    policies = [binding for definition in data.get('models', {}).values()
                for binding in definition['runtimes'].values()]
    for runtime, definition in data.get('runtimes', {}).items():
        for caller, executor in definition['executors'].items():
            if (executor['type'] == 'subagent' and not executor.get('config', {}).get('agent')
                    and caller != runtime):
                raise ValueError(f'{location}: runtime {runtime!r} requires a named bridge or external '
                                 f'executor from {caller!r}; an unnamed subagent runs in its caller')
    for agents in groups:
        for role, entry in agents.items():
            if entry is None:
                continue
            if 'candidates' in entry:
                instances = entry['candidates'].values() if isinstance(entry['candidates'], dict) else []
            else:
                instances = [entry]
            for instance in instances:
                policies.append(instance.get('models', {}))
    for policy in policies:
        thinking = policy.get('thinking')
        if isinstance(thinking, dict) and thinking['default'] not in thinking['allowed']:
            raise ValueError(f'{location}: default thinking must belong to allowed')


def validate_schema(data, location, name):
    try:
        from jsonschema import Draft202012Validator
        from jsonschema.exceptions import best_match
        from referencing import Registry, Resource
    except ImportError as error:
        raise ValueError('Executor configuration requires jsonschema. Use the plugin .venv/bin/python '
                         'after installing requirements.txt; see harnesses/executors.md') from error
    schema_root = ROOT / 'schemas'
    registry = Registry().with_resources(
        (path.as_uri(), Resource.from_contents(json.loads(path.read_text())))
        for path in schema_root.rglob('*.schema.json'))
    path = schema_root / name
    schema = json.loads(path.read_text())
    schema['$id'] = path.as_uri()
    error = best_match(Draft202012Validator(schema, registry=registry).iter_errors(data))
    if error:
        pointer = '.'.join(str(part) for part in error.absolute_path)
        raise ValueError(f'{location}{"." + pointer if pointer else ""}: {error.message}')


def read_executors(path):
    if not path.exists():
        return {}
    data = json.loads(path.read_text())
    validate_execution_config(data, str(path))
    return data


def session_path(repo, session_id):
    validate_settings({'model': session_id}, 'session', runtime_labels=True)
    if session_id is None:
        raise ValueError('A root session ID is required')
    identity = json.dumps([str(repo.resolve()), session_id])
    digest = hashlib.sha256(identity.encode()).hexdigest()
    state = Path(os.environ.get('XDG_STATE_HOME') or Path.home() / '.local/state').expanduser()
    if not state.is_absolute():
        raise ValueError('XDG_STATE_HOME must be an absolute directory for session state')
    return state / 'automattic/sessions' / f'{digest}.json'


def read_session(repo, session_id):
    path = session_path(repo, session_id)
    if not path.exists():
        return {}
    record = json.loads(path.read_text())
    if (not isinstance(record, dict) or set(record) != {'repo', 'session_id', 'config'}
            or record['repo'] != str(repo.resolve()) or record['session_id'] != session_id):
        raise ValueError(f'{path}: session identity does not match repository/root session')
    validate_execution_config(record['config'], str(path))
    return record['config']


def save_session(repo, session_id, config):
    """Replace this session's complete override configuration after validation."""
    validate_execution_config(config, 'session configuration')
    read_session(repo, session_id)
    path = session_path(repo, session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {'repo': str(repo.resolve()), 'session_id': session_id, 'config': config}
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(json.dumps(record, indent=2) + '\n')
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return path


def reset_session(repo, session_id):
    read_session(repo, session_id)
    path = session_path(repo, session_id)
    path.unlink(missing_ok=True)
    return path


def check_thinking(policy, value, *, automatic=False):
    baseline = policy.get('thinking')
    if isinstance(baseline, dict):
        if value not in baseline['allowed']:
            raise ValueError(f'thinking {value!r} is outside allowed {baseline["allowed"]}')
    elif automatic and (policy.get('mode', 'inherit') != 'override'
                        or (value != baseline and not policy.get('allow_thinking_override', False))):
        raise ValueError('agent does not allow this automatic thinking override')


QUALITY_SIGNALS = {'review_defects': 'review defects', 'repair_rounds': 'repair rounds',
                   'reverts': 'reverts', 'owner_defects': 'owner-found defects'}


def outcome_history(trace, role):
    """Summarize earlier worker outcomes in this journal: per actual model/effort for the role, plus gaps."""
    path = Path(trace['path']) if trace else None
    if path is None or not path.is_file():
        return [], 0
    rows = decisions.decision_journal.read(path)
    latest = {}
    for row in rows:
        if row['event'] in ('execution', 'outcome'):
            latest.setdefault(row['decision_id'], {})[row['event']] = row
    counts, signals, missing = {}, {}, 0
    for row in rows:
        if row['event'] != 'decision' or row['request'].get('family') != 'worker-selection':
            continue
        if row.get('assignment') == trace.get('assignment'):
            continue
        events = latest.get(row['decision_id'], {})
        if 'outcome' not in events:
            missing += 1
        if not row['request'].get('state', '').startswith(f'Role: {role}\n') or 'execution' not in events:
            continue
        observed = events['execution'].get('observed') or {}
        key = ' '.join(str(observed[k]) for k in ('model', 'effort') if observed.get(k))
        status = events.get('outcome', {}).get('status', 'no outcome')
        counts.setdefault(key, {}).setdefault(status, 0)
        counts[key][status] += 1
        # Quality signals attributed after acceptance; elapsed time is not one.
        for metric, value in events.get('outcome', {}).get('metrics', {}).items():
            if metric in QUALITY_SIGNALS:
                signals.setdefault(key, {}).setdefault(metric, 0)
                signals[key][metric] += value
    lines = []
    for key, statuses in sorted(counts.items()):
        quality = [f'{QUALITY_SIGNALS[metric]}: {value:g}' for metric, value in signals.get(key, {}).items() if value]
        lines.append(f'- {key}: ' + ', '.join(f'{n} {status}' for status, n in sorted(statuses.items()))
                     + ('; ' + ', '.join(quality) if quality else ''))
    return lines, missing


def recorded_state(trace):
    """The request state of this assignment's earlier worker-selection decision, if any."""
    path = Path(trace['path']) if trace else None
    if path is None or not path.is_file():
        return None
    for row in decisions.decision_journal.read(path):
        if (row['event'] == 'decision' and row['request'].get('family') == 'worker-selection'
                and all(row.get(key) == trace.get(key) for key in ('repo', 'session', 'assignment'))):
            return row['request'].get('state', '')
    return None


def decision_model_selection(router, candidates, definitions, role, host, assignment, task, *, decision_policy=None, context=None, eligible_thinking=None, trace=None, excluded=None, failure=None):
    """Score permitted model/effort pairs together; the service never supplies launch settings."""
    if not isinstance(assignment, str) or not assignment.strip() or len(assignment) > 16000:
        raise ValueError('Decision model requires a nonempty assignment of at most 16000 characters')
    options, criteria = {}, {}
    for name, instance in candidates.items():
        policy = instance.get('models', {'mode': 'inherit'})
        baseline = policy.get('thinking')
        if policy['mode'] == 'inherit' and task:
            continue
        if 'model' in task and task['model'] != policy.get('model'):
            continue
        levels = baseline['allowed'] if isinstance(baseline, dict) else [baseline]
        if 'effort' in task:
            try:
                check_thinking(policy, task['effort'])
            except ValueError:
                continue
            levels = [task['effort']]
        for level in levels:
            if name in (eligible_thinking or {}) and level not in eligible_thinking[name]:
                continue
            key = f'option_{len(options)}'
            options[key] = {'candidate': name, **({'thinking': level} if level is not None else {})}
            route = definitions.get(name, {})
            criteria[key] = json.dumps({
                **options[key], 'model': policy.get('model', 'inherited'),
                'runtime': route.get('target_runtime', 'executor-defined'),
                'route': route.get('executor_context', instance['executor']['type']),
                'task_fit': instance.get('description', 'No task-fit description configured.')})
    if not options:
        raise ValueError('No permitted model/thinking pairs remain for the explicit task settings')
    if len(options) > 254:
        raise ValueError('System One permits at most 254 worker options plus abstention; narrow the eligible pool')
    decision_policy = decision_policy or {'backend': {key: value for key, value in router.items()
                                                      if key not in decisions.ROUTING_KEYS},
                        'enabled': ['worker-selection']}
    if len(options) == 1:
        # Nothing to choose: settle without inference and keep the phase accounted for.
        reason = 'Only one permitted model/thinking option remains.'
        record = {'status': 'skipped', 'family': 'worker-selection', 'choice': None, 'warnings': [],
                  'skip_reason': 'settled', 'reason': reason}
        if trace is not None:
            record = decisions.checkpoint(decision_policy, 'worker-selection', None, context=context, trace=trace,
                                          skip='settled', reason=reason,
                                          evidence=['agent-models:option_0 ' + criteria['option_0']])
        record['proposer'] = 'resolver'
        record['options'] = options
        return dict(options['option_0'], reason=reason), record
    instructions = ('Choose one worker and thinking setting to complete the assignment efficiently. '
                    'Use the supplied task-fit descriptions and evidence, considering correctness, '
                    'repair/review cost and runtime startup. Honor the assignment\'s user priorities, '
                    'including remaining allowance and optional work. For well-understood work with '
                    'reliable failure checks, prefer the lightest adequate pair. Do not infer subscription '
                    'credits from token counts or treat synthetic scores as measured completion quality. '
                    'Avoid guessing model capabilities. '
                    'Abstain if the evidence is insufficient.')
    history, missing = outcome_history(trace, role)
    heading = f'Earlier {role} outcomes in this journal (actual model and effort):\n'
    history = heading + '\n'.join(history) + '\n' if history else ''
    previous = recorded_state(trace)
    if previous is not None:
        # A resume reuses the history its decision first saw, so the checkpoint key stays stable.
        history = previous[previous.index(heading):previous.index('Assignment:\n')] if heading in previous else ''
    state = f'Role: {role}\nCaller: {host}\n'
    if failure:
        # Before the history, which a resume reuses from the first request.
        state += f'Earlier attempt failed: {failure}\n'
    if excluded:
        state += 'Configured candidates excluded by the host:\n' + ''.join(
            f'- {name}: {reason}\n' for name, reason in excluded.items())
    state += history
    request = {'family': 'worker-selection',
               'state': state + f'Assignment:\n{assignment}',
               'instruction': instructions, 'options': criteria}
    if trace is None:
        record = decisions.decide(decision_policy, request, context=context, transport=systemone_request)
    else:
        record = decisions.checkpoint(decision_policy, 'worker-selection', request, context=context,
                                      transport=systemone_request, trace=trace)
    record['options'] = options
    if missing:
        record.setdefault('warnings', []).append({'code': 'missing_outcomes', 'message': (
            f'{missing} earlier worker decision(s) in this journal have no outcome; record them with '
            'decision_journal.py outcome when their work is accepted or rejected.')})
    if record['status'] != 'recommended':
        return None, record
    return dict(options[record['choice']],
                reason=f'System One selected {record["choice"]} using {record["model"]}.'), record


# Shadow scoring: what a worker spends, as a weight against its chance of acceptance. A subscription's
# weight rises with its provider's allowance pressure; an unknown reading keeps the base weight.
COSTS = {'subscription': 1.0, 'free': 0.0, 'local': 0.0}
COST_WEIGHT = 0.15
PRESSURE_WEIGHTS = {'normal': COST_WEIGHT, 'elevated': 0.4, 'critical': 1.0}


def allowance_levels():
    """Each subscription provider's pressure level; a reader failure leaves every provider unknown."""
    try:
        readings = allowance.status(allowance.codex_sessions(), time.time(), persist=False)['providers']  # Routing stays read-only.
        return {name: value['level'] for name, value in readings.items()}
    except (OSError, ValueError, KeyError) as error:
        return {'error': str(error)}
TRAINING = 'Model trains on prompts; this repository does not allow training endpoints (allow_training)'


def shadow_selection(names, catalog, role, seed, levels=None):
    """What a cost-aware policy would choose: per candidate, a Thompson sample of its acceptance rate in this
    role's recorded outcomes, less the cost weight for subscription spend. It never changes the route."""
    try:
        counts = outcomes.summary(role).get(role, {})
    except (OSError, ValueError, sqlite3.Error) as error:
        return {'status': 'unavailable', 'error': str(error)}
    scored = {}
    for name in names:
        definition = catalog[name][0] if name in catalog else {}
        # Attempts registered without a candidate name are known by their model ID.
        known = {name} | {binding['id'] for binding in definition.get('runtimes', {}).values()}
        successes = sum(counts.get(key, {}).get('successes', 0) for key in known)
        failures = sum(counts.get(key, {}).get('failures', 0) for key in known)
        cost = definition.get('cost')
        draw = random.Random(f'{seed}|{name}').betavariate(1 + successes, 1 + failures)
        scored[name] = {'cost': cost or 'unknown', 'successes': successes, 'failures': failures,
                        'mean': round((1 + successes) / (2 + successes + failures), 3), 'sample': round(draw, 3),
                        'utility': round(draw - weight(names[name], levels or {}) * COSTS.get(cost, 1.0), 3)}
    choice = max(scored, key=lambda name: scored[name]['utility']) if scored else None
    return {'policy': 'thompson-cost-v1', 'cost_weight': COST_WEIGHT, 'allowance': levels or {},
            'candidates': scored, 'choice': choice}


def backend_unavailable(definition, backends, checked=None):
    """Why a model's local backend cannot take a worker now (no free slot, unhealthy, short of memory), or None.
    `checked` keeps each backend's answer for the rest of one route."""
    backend = definition.get('backend')
    if backend not in backends:
        return None
    if checked is not None:
        if backend not in checked:
            checked[backend] = backend_unavailable(definition, backends)
        return checked[backend]
    try:
        held = capacity.in_use(backend)
        slots = backends[backend]['slots']
        if held >= slots:
            return f'Backend {backend} is at capacity ({held}/{slots})'
        capacity.check(backend, backends[backend])
    except ValueError as error:
        return str(error)
    except (OSError, sqlite3.Error):
        return None  # The lease is still checked when the worker registers.
    return None


def weight(runtime, levels):
    return PRESSURE_WEIGHTS.get(levels.get(runtime), COST_WEIGHT)


def select_candidate(pool, candidate, recommendation, eligible_candidates, task,
                     *, overrides=None, definitions=None, target_runtime=None, configured_candidates=None):
    """Validate a recommendation or pin; never infer runtime support from model names."""
    candidates = pool['candidates']
    eligible = list(candidates) if eligible_candidates is None else eligible_candidates
    if (not isinstance(eligible, list) or any(not isinstance(name, str) or name not in candidates
                                              for name in eligible) or len(set(eligible)) != len(eligible)):
        raise ValueError('eligible candidates must be a unique list of configured candidate IDs')
    info = {'eligible_candidates': eligible}
    pinned = candidate is not None
    thinking = None
    if not eligible:
        if pinned:
            raise ValueError(f'candidate {candidate!r} is not eligible; explicit choice prevents fallback')
        raise ValueError('No eligible candidates remain; configured alternatives are exhausted')
    if candidate is not None:
        source, reason = 'user', 'Explicit candidate choice.'
        if candidate not in eligible:
            raise ValueError(f'candidate {candidate!r} is not eligible; explicit choice prevents fallback')
    elif recommendation is not None:
        try:
            if isinstance(recommendation, str):
                recommendation = json.loads(recommendation)
            validate_schema(recommendation, 'selection', 'selection.schema.json')
            if recommendation['candidate'] is not None:
                if recommendation['candidate'] not in eligible:
                    raise ValueError('recommended candidate is not eligible')
        except ValueError as error:
            if (isinstance(recommendation, dict) and isinstance(recommendation.get('candidate'), str)
                    and recommendation['candidate'] in (configured_candidates or candidates)
                    and recommendation['candidate'] not in eligible and not pool.get('fallback', True)):
                raise ValueError('Selected candidate is not eligible; policy prevents fallback') from error
            info['selection_error'] = str(error)
            return None, None, dict(info, status='selection_required')
        else:
            if recommendation['candidate'] is None:
                raise ValueError('No suitable candidate: ' + recommendation['reason'])
            candidate, source, reason = recommendation['candidate'], 'selector', recommendation['reason']
            thinking = recommendation.get('thinking')
    else:
        source, reason = 'sole-candidate', 'Only one eligible candidate remains.'
    definitions = definitions or {}
    runtime = target_runtime or definitions.get(candidate, {}).get('target_runtime')
    if runtime is None:
        possible = {definitions.get(name, {}).get('target_runtime') for name in eligible}
        if len(possible) == 1:
            runtime = possible.pop()
    override = (overrides or {}).get(runtime, {}) if not pinned else {}
    if 'candidate' in override:
        preferred = override['candidate']
        if preferred not in eligible:
            if not pool.get('fallback', True):
                raise ValueError(f'profile candidate {preferred!r} is not eligible; policy prevents fallback')
            info['fallback_from'] = preferred
            override = {}
            if candidate is None:
                return None, None, dict(info, status='selection_required')
        else:
            candidate, source, reason = preferred, 'profile', f'Configured choice for worker runtime {runtime}.'
    if candidate is None:
        if len(eligible) != 1:
            return None, None, dict(info, status='selection_required')
        candidate = eligible[0]
    if 'thinking' in override:
        thinking = override['thinking']
        info['profile_thinking'] = thinking
    instance = candidates[candidate]
    policy = instance.get('models', {'mode': 'inherit'})
    if thinking is not None and 'effort' not in task:
        try:
            check_thinking(policy, thinking, automatic=True)
        except ValueError as error:
            return None, None, dict(info, status='selection_required', selection_error=str(error))
        if thinking == policy.get('thinking'):
            thinking = None
    else:
        thinking = None
    if 'model' in task and task['model'] != policy.get('model'):
        raise ValueError('task model conflicts with candidate; select a candidate or an explicit --route-choice')
    info.update(candidate=candidate, selection_source=source, selection_reason=reason)
    return instance, thinking, info


def expand_executor_type(instance, executor_types):
    """Resolve a named skill usage while leaving assignment and model policy intact."""
    name = instance['executor']['type']
    if name in ('subagent', 'skill', 'bash'):
        return instance, {}
    if name not in executor_types:
        raise ValueError(f'Unknown executor type {name!r}; define it in executor_types')
    definition, source = executor_types[name]
    return dict(instance, executor=definition), {
        'configured_executor_type': name, 'executor_definition_source': source}


def expand_model(name, catalog, runtimes, host, target_runtime=None):
    """Resolve a model's runtime binding and a launch route available to this caller."""
    if name not in catalog:
        raise ValueError(f'Unknown model definition {name!r}')
    definition, source = catalog[name]
    bindings = definition['runtimes']
    for runtime in bindings:
        if runtime not in runtimes:
            raise ValueError(f'Unknown runtime configuration {runtime!r} for model {name!r}')
    ordered = ([host] if host in bindings else []) + [runtime for runtime in bindings if runtime != host]
    if target_runtime is not None:
        ordered = [runtime for runtime in ordered if runtime == target_runtime]
    for runtime in ordered:
        runtime_definition, runtime_source = runtimes[runtime]
        executors = runtime_definition['executors']
        context = host if host in executors else 'herdr' if os.environ.get('HERDR_ENV') == '1' else None
        if context not in executors:
            continue
        binding = bindings[runtime]
        policy = {key: binding[key] for key in ('thinking', 'allow_thinking_override') if key in binding}
        instance = {'executor': executors[context], 'description': definition['description'],
                    'models': dict(policy, mode='override', model=binding['id'])}
        return instance, {'executor_context': context, 'target_runtime': runtime,
                          'model_definition_source': source,
                          'model_binding_source': source + '.runtimes.' + runtime,
                          'executor_source': runtime_source + '.executors.' + context}
    return None, f'No configured route from {host!r} to model runtimes {ordered} in this environment'


def resolve_execution(repo, user_config, user_executors, host, role, task, choice=None, config_profile=None,
                      adaptive_thinking=None, *, session_id=None, candidate=None, selection=None,
                      eligible_candidates=None, list_candidates=False, target_runtime=None, assignment=None,
                      eligible_thinking=None, journal=None, assignment_id=None, excluded_candidates=None,
                      after_failure=None):
    layers = [(path, read_executors(path))
              for path in (user_executors, repo / '.automattic/executors.json')]
    session_id = session_id if session_id is not None else os.environ.get('AUTOMATTIC_SESSION') or None
    trace = decisions.decision_journal.trace_config(journal, repo, assignment_id, session_id)
    session = {}
    if session_id is not None:
        path = session_path(repo, session_id)
        layers.append((path, read_session(repo, session_id)))
        session = {'session': {'id': session_id, 'repo': str(repo.resolve()), 'path': str(path)}}
    profiles = {name: (value, f'{path}:profiles.{name}')
                for path, data in layers for name, value in data.get('profiles', {}).items()}
    router, router_source = DEFAULT_ROUTER, 'built-in'
    for path, data in layers:
        if 'router' in data:
            router, router_source = data['router'], f'{path}:router'
    decision_policy = decisions.effective_policy(layers, router)
    decision_context = decisions.decision_context(layers)
    profile = config_profile if config_profile is not None else os.environ.get('AUTOMATTIC_PROFILE') or None
    if profile is not None:
        router = {'type': 'profile', 'profile': profile}
        router_source = 'argument' if config_profile is not None else 'environment'
    profile = router.get('profile')
    for name in (profile, router.get('fallback_profile')):
        if name is not None and name not in profiles:
            raise ValueError(f'Unknown routing profile {name!r}; define it in executors.json')
    overrides = profiles[profile][0].get(role, {}) if profile is not None else {}
    metadata = {'config_profile': profile, 'profile_source': profiles[profile][1] if profile else None,
                'router': router, 'router_source': router_source, 'profile_overrides': overrides,
                'decision_policy': decision_policy, **session}
    catalog = {name: (definition, f'{path}:models.{name}')
               for path, data in layers for name, definition in data.get('models', {}).items()}
    allow_training, backends, checked = False, {}, {}
    for _, data in layers:
        allow_training = data.get('allow_training', allow_training)
        backends.update(data.get('capacity', {}))
    runtimes = {name: (definition, f'{path}:runtimes.{name}')
                for path, data in layers for name, definition in data.get('runtimes', {}).items()}
    executor_types = {name: (definition, f'{path}:executor_types.{name}')
                      for path, data in layers for name, definition in data.get('executor_types', {}).items()}
    instance, source = None, None
    for path, data in layers:
        if role in data.get('agents', {}):
            instance = data['agents'][role]
            source = f'{path}:agents.{role}'
    if choice is not None:
        validate_execution_config({'agents': {role: choice}}, 'task choice')
        if 'executor' not in choice:
            raise ValueError('task choice requires a complete single agent instance')
        instance, source = choice, 'task choice'
    pooled = instance is not None and 'candidates' in instance
    configured_candidates = list(instance['candidates']) if pooled else []
    definitions = {}
    if target_runtime is not None and target_runtime not in HARNESSES:
        raise ValueError(f'Unknown target runtime {target_runtime!r}')
    if target_runtime is not None and not (instance is not None and (
            'model' in instance or (pooled and isinstance(instance['candidates'], list)))):
        raise ValueError('An explicit target runtime requires a catalog model reference or pool; '
                         'complete executor instances determine their own destination')
    if pooled:
        if eligible_candidates is not None and (
                not isinstance(eligible_candidates, list)
                or any(not isinstance(name, str) or name not in configured_candidates for name in eligible_candidates)
                or len(set(eligible_candidates)) != len(eligible_candidates)):
            raise ValueError('eligible candidates must be a unique list of configured candidate IDs')
        for runtime, override in overrides.items():
            name = override.get('candidate')
            if name is None:
                continue
            if name not in instance['candidates']:
                raise ValueError(f'Profile candidate {name!r} is outside the {role} pool')
            if isinstance(instance['candidates'], list):
                if name not in catalog or runtime not in catalog[name][0]['runtimes']:
                    raise ValueError(f'Profile candidate {name!r} has no {runtime!r} binding')
                binding = catalog[name][0]['runtimes'][runtime]
                if 'thinking' in override:
                    check_thinking(dict(binding, mode='override'), override['thinking'], automatic=True)
        if isinstance(instance['candidates'], list) and overrides and target_runtime is None:
            baseline = candidate
            if baseline is None:
                try:
                    value = json.loads(selection) if isinstance(selection, str) else selection
                    baseline = value.get('candidate') if isinstance(value, dict) else None
                except ValueError:
                    pass
            if baseline in instance['candidates'] and (eligible_candidates is None or baseline in eligible_candidates):
                resolved, detail = expand_model(baseline, catalog, runtimes, host)
                if resolved is not None:
                    target_runtime = detail['target_runtime']
    if pooled and isinstance(instance['candidates'], list):
        expanded, unavailable = {}, {}
        for name in instance['candidates']:
            if name in catalog and catalog[name][0].get('data') == 'trains' and not allow_training:
                unavailable[name] = TRAINING
                continue
            full = backend_unavailable(catalog[name][0] if name in catalog else {}, backends, checked)
            if full:
                unavailable[name] = full
                continue
            resolved, detail = expand_model(name, catalog, runtimes, host, target_runtime)
            if resolved is None:
                unavailable[name] = detail
            else:
                expanded[name], definitions[name] = resolved, detail
                backend = catalog[name][0].get('backend')
                if backend in backends:
                    # The lifecycle takes this backend's lease when the worker registers.
                    definitions[name].update(backend=backend, capacity=backends[backend])
        metadata['unavailable_candidates'] = unavailable
        metadata['candidate_routes'] = definitions
        instance = dict(instance, candidates=expanded)
    elif instance is not None and 'model' in instance:
        name = instance['model']
        if name in catalog and catalog[name][0].get('data') == 'trains' and not allow_training:
            raise ValueError(f'Model {name!r}: {TRAINING}')
        full = backend_unavailable(catalog[name][0] if name in catalog else {}, backends, checked)
        if full:
            raise ValueError(f'Model {name!r}: {full}')
        instance, detail = expand_model(name, catalog, runtimes, host, target_runtime)
        if instance is None:
            raise ValueError(f'Model {name!r}: {detail}')
        metadata.update(detail)
        backend = catalog[name][0].get('backend')
        if backend in backends:
            metadata.update(backend=backend, capacity=backends[backend])
    if pooled:
        expanded = {}
        for name, value in instance['candidates'].items():
            expanded[name], detail = expand_executor_type(value, executor_types)
            if (expanded[name]['executor']['type'] == 'subagent'
                    and not expanded[name]['executor'].get('config', {}).get('agent')):
                definitions.setdefault(name, {}).setdefault('target_runtime', host)
            if detail:
                definitions.setdefault(name, {}).update(detail)
        instance = dict(instance, candidates=expanded)
        if definitions:
            metadata['candidate_routes'] = definitions
    elif instance is not None:
        instance, detail = expand_executor_type(instance, executor_types)
        metadata.update(detail)
    if eligible_thinking is not None:
        if not pooled or not isinstance(eligible_thinking, dict):
            raise ValueError('eligible thinking requires a candidate pool and a JSON candidate-to-levels object')
        for name, levels in eligible_thinking.items():
            if (name not in configured_candidates or not isinstance(levels, list)
                    or any(level is not None and (not isinstance(level, str) or not level) for level in levels)
                    or len(set(levels)) != len(levels)):
                raise ValueError('eligible thinking requires configured candidate IDs and unique levels')
            if name in instance['candidates']:
                baseline = instance['candidates'][name].get('models', {}).get('thinking')
                permitted = baseline['allowed'] if isinstance(baseline, dict) else [baseline]
                if any(level not in permitted for level in levels):
                    raise ValueError(f'eligible thinking for {name!r} exceeds configured thinking choices')
        metadata['eligible_thinking'] = eligible_thinking
        eligible_candidates = [name for name in (eligible_candidates if eligible_candidates is not None
                                                 else instance['candidates'])
                               if name not in eligible_thinking or eligible_thinking[name]]
    if list_candidates:
        return dict(metadata, host_harness=host, role=role, route_source=source,
                    candidates=instance['candidates'] if pooled else {},
                    instance=None if pooled else instance)
    if pooled:
        metadata['candidate_pool'] = instance
        pool = instance
        # Shadow scoring weighs every reachable candidate the host did not exclude, whatever the route's runtime.
        competing = {}
        for name in configured_candidates:
            if ((eligible_candidates is None or name in eligible_candidates) and name in catalog
                    and (catalog[name][0].get('data') != 'trains' or allow_training)
                    and not backend_unavailable(catalog[name][0], backends, checked)):
                reachable, route = expand_model(name, catalog, runtimes, host)
                if reachable is not None:
                    competing[name] = route['target_runtime']
        if eligible_candidates is not None:
            eligible_candidates = [name for name in eligible_candidates if name in pool['candidates']]
        decision_requested = (router['type'] == 'decision-model' and assignment is not None
                              and candidate is None and selection is None)
        if decision_requested and router.get('consult') == 'after-failure' and after_failure is None:
            # Rule first: the configured profile settles routine routes; System One sees failures.
            rule_profile = router.get('fallback_profile')
            if rule_profile is None:
                raise ValueError('router consult "after-failure" needs a fallback_profile as its rule route')
            rule = profiles[rule_profile][0].get(role, {})
            try:
                settled = select_candidate(pool, None, None, eligible_candidates, task, overrides=rule,
                                           definitions=definitions, target_runtime=target_runtime,
                                           configured_candidates=configured_candidates)[2]
            except ValueError:
                settled = {}  # The rule cannot route this assignment; consult as usual.
            if settled.get('selection_source') == 'profile':
                overrides, decision_requested = rule, False
                metadata.update(config_profile=rule_profile, profile_source=profiles[rule_profile][1],
                                profile_overrides=rule, rule_route=True)
        if decision_requested:
            if adaptive_thinking is not None:
                raise ValueError('Use decision-model thinking selection or --adaptive-thinking, not both')
            eligible = list(pool['candidates']) if eligible_candidates is None else eligible_candidates
            if not eligible:
                raise ValueError('No eligible candidates remain; configured alternatives are exhausted')
            if excluded_candidates is not None and not (isinstance(excluded_candidates, dict) and all(
                    name in configured_candidates for name in excluded_candidates)):
                unknown = sorted(set(excluded_candidates) - set(configured_candidates)) \
                    if isinstance(excluded_candidates, dict) else []
                raise ValueError('excluded candidates must map configured candidate IDs to reasons'
                                 + (f'; unknown: {", ".join(unknown)}' if unknown else '')
                                 + f'; configured: {", ".join(sorted(configured_candidates))}')
            excluded = {}
            for name in pool['candidates']:
                if name in eligible:
                    continue
                if (eligible_thinking or {}).get(name) == []:
                    excluded[name] = 'no eligible thinking level after runtime preflight'
                elif isinstance((excluded_candidates or {}).get(name), str) and excluded_candidates[name].strip():
                    excluded[name] = excluded_candidates[name].strip()
            unexplained = [name for name in pool['candidates'] if name not in eligible and name not in excluded]
            if unexplained:
                raise ValueError('Give a reason for each configured candidate you exclude from this decision '
                                 '(--excluded-candidates \'{"<id>": "<reason>"}\'): ' + ', '.join(unexplained))
            validate_settings(task, 'task', runtime_labels=True)
            try:
                selection, record = decision_model_selection(
                    router, {name: pool['candidates'][name] for name in eligible}, definitions,
                    role, host, assignment, task, decision_policy=decision_policy, context=decision_context,
                    eligible_thinking=eligible_thinking, trace=trace, excluded=excluded, failure=after_failure)
                metadata['decision_model'] = record
                metadata['decision_warnings'] = record['warnings']
                if selection is None:
                    raise ValueError(record.get('error', 'Decision model abstained; use host judgment'))
            except (OSError, ValueError) as error:
                fallback = router.get('fallback_profile')
                # Only a backend outage/abstention/invalid answer falls back; configuration or journal errors do not.
                if fallback is None or 'decision_model' not in metadata:
                    return dict(metadata, status='selection_required', selection_error=str(error),
                                host_harness=host, role=role, route_source=source,
                                eligible_candidates=eligible, candidates=pool['candidates'],
                                selection_router=DEFAULT_ROUTER)
                # Deterministic recovery: apply the configured profile before asking the host.
                overrides = profiles[fallback][0].get(role, {})
                metadata.update(config_profile=fallback, profile_source=profiles[fallback][1],
                                profile_overrides=overrides, selection_error=str(error))
                metadata['decision_warnings'] = metadata['decision_warnings'] + [{
                    'code': 'decision_fallback',
                    'message': f'Decision backend did not select ({error}); applied fallback profile {fallback!r}.'}]
                decision_requested, selection = False, None
        instance, recommended_thinking, info = select_candidate(
            pool, candidate, selection, eligible_candidates, task,
            overrides=overrides, definitions=definitions, target_runtime=target_runtime,
            configured_candidates=configured_candidates)
        metadata.update(info)
        if info.get('status') == 'selection_required':
            return dict(metadata, host_harness=host, role=role, route_source=source,
                        candidates=pool['candidates'],
                        selection_router=DEFAULT_ROUTER if router['type'] == 'profile'
                        or 'selection_error' in info or 'selection_error' in metadata else router)
        metadata.update(definitions.get(info['candidate'], {}))
        if 'selection_error' in metadata and metadata.get('selection_source') == 'profile':
            metadata['selection_source'] = 'fallback-profile'
        if metadata.pop('rule_route', False):
            metadata['selection_source'] = 'rule-profile'
        if decision_requested:
            metadata['selection_source'] = ('sole-option' if metadata['decision_model']['status'] == 'skipped'
                                            else 'decision-model')
        if isinstance(configured_candidates, list) and configured_candidates:
            shadow = shadow_selection(competing, catalog, role,
                                      f'{role}|{assignment_id or assignment or ""}', allowance_levels())
            if shadow.get('choice') is not None:
                shadow['agrees'] = shadow['choice'] == info['candidate']
            metadata['shadow_selection'] = shadow
        source += '.candidates.' + info['candidate']
        if recommended_thinking is not None:
            if adaptive_thinking is not None:
                raise ValueError('use selection thinking or adaptive thinking, not both')
            adaptive_thinking = recommended_thinking
    elif choice is None and any(value is not None for value in (candidate, selection, eligible_candidates)):
        raise ValueError('candidate selection requires a configured candidate pool')
    if instance is None:
        if adaptive_thinking is not None:
            raise ValueError('adaptive thinking requires an agent with allow_thinking_override: true')
        result = resolve(repo, user_config, host, role, task)
        result.update(host_harness=host, executor='native', executor_type='subagent',
                      executor_config={}, native_dispatch=True, model_mode='existing',
                      route_source=source, allow_thinking_override=False, **metadata,
                      executor_guide=str(ROOT / 'harnesses/executors/subagent.md'))
        return result
    executor = instance['executor']
    kind, config = executor['type'], executor.get('config', {})
    native = kind == 'subagent' and not config.get('agent')
    policy = instance.get('models', {'mode': 'inherit'})
    mode = policy['mode']
    validate_settings(task, 'task', runtime_labels=True)
    if mode == 'inherit' and task:
        raise ValueError('inherit conflicts with task model/thinking; choose override mode explicitly')
    thinking = policy.get('thinking')
    bounded = isinstance(thinking, dict)
    allow_thinking_override = bounded or policy.get('allow_thinking_override', False)
    if bounded and 'model' in task and task['model'] != policy.get('model'):
        raise ValueError('task model conflicts with bounded thinking; use an explicit --route-choice')
    if bounded and 'effort' in task:
        check_thinking(policy, task['effort'])
    if adaptive_thinking is not None:
        if not allow_thinking_override:
            raise ValueError('agent does not allow automatic thinking overrides')
        if 'effort' in task:
            raise ValueError('explicit user thinking takes precedence; omit adaptive thinking')
        validate_settings({'effort': adaptive_thinking}, 'adaptive thinking', runtime_labels=True)
        if adaptive_thinking == 'native':
            raise ValueError('adaptive thinking requires a runtime label, not native')
        check_thinking(policy, adaptive_thinking, automatic=True)
    settings = {}
    sources = {}
    if mode == 'override':
        for field, key in (('model', 'model'), ('thinking', 'effort')):
            if field in policy:
                settings[key] = thinking['default'] if field == 'thinking' and bounded else policy[field]
                sources[key] = (metadata['model_binding_source'] + '.' + ('id' if field == 'model' else field)
                                if 'model_binding_source' in metadata else source + '.models.' + field)
        for key, value in task.items():
            if value is None:
                settings.pop(key, None)
            else:
                settings[key] = value
            sources[key] = 'task'
    if adaptive_thinking is not None:
        settings['effort'] = adaptive_thinking
        sources['effort'] = 'adaptive thinking'
    selected = metadata.get('candidate')
    if selected in (eligible_thinking or {}) and settings.get('effort') not in eligible_thinking[selected]:
        raise ValueError(f'candidate {selected!r} thinking {settings.get("effort")!r} failed runtime preflight; '
                         'choose an eligible setting or verify registration before retrying')
    # Named delegates and skills can forward to another runtime; the host is not the destination.
    return {'harness': host if native else None, 'host_harness': host, 'role': role,
            'settings': settings, 'sources': sources, 'files': [],
            'executor': 'native' if native else kind, 'executor_type': kind,
            'executor_config': config, 'native_dispatch': native, 'model_mode': mode,
            'allow_thinking_override': allow_thinking_override,
            'thinking_baseline': thinking['default'] if bounded else thinking,
            **({'thinking_allowed': thinking['allowed']} if bounded else {}),
            'route_source': source, **metadata,
            'executor_guide': str(ROOT / 'harnesses/executors' / f'{kind}.md')}


def validate_settings(settings, location, *, runtime_labels=False):
    if not isinstance(settings, dict) or set(settings) - {'model', 'effort'}:
        raise ValueError(f'{location}: expected model/effort object')
    for key, value in settings.items():
        if value is None:
            continue
        if not isinstance(value, str) or not value or any(c.isspace() or ord(c) < 32 for c in value):
            raise ValueError(f'{location}.{key}: expected nonempty identifier or null')
        if key == 'effort' and not runtime_labels and value not in EFFORTS:
            raise ValueError(f'{location}.effort: unknown level {value!r}')


def read_config(path):
    if not path.exists():
        return {}
    data = json.loads(path.read_text())
    if not isinstance(data, dict) or set(data) - set(HARNESSES):
        raise ValueError(f'{path}: expected harness keys {HARNESSES}')
    for harness, roles in data.items():
        if not isinstance(roles, dict) or set(roles) - set(ROLES + ('defaults',)):
            raise ValueError(f'{path}:{harness}: unknown role or invalid object')
        for role, settings in roles.items():
            validate_settings(settings, f'{path}:{harness}.{role}')
    return data


def resolve(repo, user_config, harness, role, task):
    settings, sources = {}, {}
    files = (user_config, repo / '.automattic/models.json')
    layers = []
    for path in files:
        data = read_config(path).get(harness, {})
        for key in ('defaults', role):
            layers.append((data.get(key, {}), f'{path}:{harness}.{key}'))
    validate_settings(task, 'task', runtime_labels=True)
    layers.append((task, 'task'))
    for values, source in layers:
        for key, value in values.items():
            if value is None:
                settings.pop(key, None)
            else:
                settings[key] = value
            sources[key] = source
    return {'harness': harness, 'role': role, 'settings': settings,
            'sources': sources, 'files': [str(path) for path in files]}


def native_profile(result):
    harness, role, settings = result['harness'], result['role'], result['settings']
    if harness not in ('claude', 'opencode'):
        raise ValueError('--profile is only for Claude and OpenCode')
    if not settings:
        return None
    if harness == 'claude':
        _, header, body = (ROOT / 'agents' / f'{role}.md').read_text().split('---', 2)
        fields = dict(line.split(': ', 1) for line in header.strip().splitlines())
        fields.pop('name')
        if 'maxTurns' in fields:
            fields['maxTurns'] = int(fields['maxTurns'])
        fields.update(settings)
        if 'effort' in settings and settings['effort'] not in ('low', 'medium', 'high', 'xhigh', 'max'):
            raise ValueError('Claude does not support this effort level')
        folder = '.claude/agents'
    else:
        fields = {'description': f'Automattic {role}; use for assigned shared-role work.',
                  'mode': 'subagent'}
        if 'model' in settings:
            fields['model'] = settings['model']
        if 'effort' in settings:
            fields['variant'] = settings['effort']
        body = ('\n\nRead the absolute `adapter` and `role_file` in your assignment.\n'
                'Verify the supplied worktree and follow the shared role.\n')
        folder = '.opencode/agents'
    # JSON strings are YAML scalars, including model IDs with punctuation.
    header = '\n'.join(f'{key}: {json.dumps(value)}' for key, value in fields.items())
    digest = hashlib.sha256((header + body).encode()).hexdigest()[:12]
    name = f'automattic-{role}-{digest}'
    content = (f'---\nname: {name}\n{header}\n---\n'
               '<!-- Generated by Automattic agent-models.py; settings snapshot. -->' + body)
    return {'name': name, 'path': f'{folder}/{name}.md', 'content': content}


def json_argument(value, flag, kind, example):
    if value is None:
        return None
    try:
        parsed = json.loads(value)
    except ValueError:
        raise ValueError(f'{flag} expects inline JSON, for example {example}') from None
    if not isinstance(parsed, kind):
        raise ValueError(f'{flag} expects inline JSON, for example {example}')
    return parsed


def assignment_text(path):
    try:
        return path.expanduser().read_text(encoding='utf-8')
    except (OSError, UnicodeError):
        raise ValueError('--assignment requires a readable UTF-8 text file path, not inline prose; '
                         'write the brief to a file and pass --assignment /absolute/path/assignment.txt') from None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', required=True, type=Path,
                        help='canonical project checkout, not the worker worktree')
    parser.add_argument('--user-config', type=Path,
                        default=Path.home() / '.config/automattic/models.json')
    parser.add_argument('--harness', required=True, choices=HARNESSES)
    parser.add_argument('--role', required=True, choices=ROLES)
    parser.add_argument('--model', help='explicit task override; native masks saved overrides')
    parser.add_argument('--thinking', '--effort', dest='effort',
                        help='explicit thinking label within bounds; native removes an unbounded override')
    parser.add_argument('--adaptive-thinking', help='agent-chosen thinking label; requires --route and opt-in')
    parser.add_argument('--profile', action='store_true', help='also render a native profile; no writes')
    parser.add_argument('--config-profile', help='select a named configuration profile; requires --route')
    parser.add_argument('--target-runtime', choices=HARNESSES,
                        help='worker runtime for catalog selection/profile lookup; requires --route')
    parser.add_argument('--route', action='store_true', help='resolve the worker executor and model policy')
    parser.add_argument('--user-executors', type=Path,
                        default=Path.home() / '.config/automattic/executors.json')
    parser.add_argument('--route-choice', help='complete JSON agent instance for this assignment only; requires --route')
    parser.add_argument('--candidate', help='explicit user pin to a configured candidate; requires --route')
    parser.add_argument('--selection', help='JSON candidate/thinking/reason recommendation; requires --route')
    parser.add_argument('--assignment', type=Path, metavar='PATH',
                        help='compact assignment text file for the decision-model router; requires --route')
    parser.add_argument('--eligible-candidates', help='inline JSON array of candidate IDs, e.g. ["luna","sol"]')
    parser.add_argument('--excluded-candidates',
                        help='JSON object giving a reason for each configured candidate left out of --eligible-candidates')
    parser.add_argument('--eligible-thinking',
                        help='JSON candidate-to-thinking-level lists from runtime preflight; null means inherited')
    parser.add_argument('--session', help='root session ID; defaults to AUTOMATTIC_SESSION, requires --route')
    parser.add_argument('--after-failure', metavar='EVIDENCE',
                        help='retry after a failed attempt: consult the decision model with this failure evidence')
    parser.add_argument('--journal', type=Path, help='absolute session journal for decision-model calls')
    parser.add_argument('--assignment-id', help='stable assignment/attempt identity; required with --journal')
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument('--list-candidates', action='store_true', help='inspect the effective pool without selecting')
    actions.add_argument('--save-session', type=Path, help='replace session overrides from a validated config JSON file')
    actions.add_argument('--reset-session', action='store_true', help='remove only this session override record')
    args = parser.parse_args()
    try:
        repo = args.repo.resolve()
        if not repo.is_dir():
            raise ValueError(f'project directory does not exist: {repo}')
        task = {key: None if value == 'native' else value
                for key, value in {'model': args.model, 'effort': args.effort}.items()
                if value is not None}
        user_config = args.user_config.expanduser().resolve()
        pool_options = (args.candidate, args.selection, args.eligible_candidates, args.eligible_thinking,
                        args.session, args.assignment, args.excluded_candidates, args.after_failure)
        session_action = args.save_session is not None or args.reset_session
        if (args.journal or args.assignment_id) and (not args.route or args.list_candidates or session_action):
            raise ValueError('Decision recording requires --route and cannot be used for inspection/session edits')
        if (any(value is not None for value in pool_options) or args.list_candidates or session_action) and not args.route:
            raise ValueError('candidate and session options require --route')
        if (args.list_candidates or session_action) and (args.profile or args.route_choice or task
                or args.assignment is not None or args.adaptive_thinking is not None
                or any(value is not None for value in pool_options[:4])):
            raise ValueError('inspection/session edits cannot be combined with launch overrides or --profile')
        if session_action:
            session_id = args.session if args.session is not None else os.environ.get('AUTOMATTIC_SESSION') or None
            if session_id is None:
                raise ValueError('session edits require --session or AUTOMATTIC_SESSION')
            if args.save_session is not None:
                config = json.loads(args.save_session.expanduser().read_text())
                path = save_session(repo, session_id, config)
            else:
                path = reset_session(repo, session_id)
                config = {}
            print(json.dumps({'session': {'id': session_id, 'repo': str(repo), 'path': str(path)},
                              'config': config}, indent=2))
            return
        if args.route_choice and not args.route:
            raise ValueError('--route-choice requires --route')
        if args.config_profile is not None and not args.route:
            raise ValueError('--config-profile requires --route')
        if args.target_runtime is not None and not args.route:
            raise ValueError('--target-runtime requires --route')
        if args.adaptive_thinking is not None and not args.route:
            raise ValueError('--adaptive-thinking requires --route')
        if args.route:
            choice = json_argument(args.route_choice, '--route-choice', dict,
                                   '\'{"executor":{"type":"subagent"}}\'')
            result = resolve_execution(repo, user_config, args.user_executors.expanduser().resolve(),
                                       args.harness, args.role, task, choice, args.config_profile,
                                       args.adaptive_thinking, session_id=args.session, candidate=args.candidate,
                                       selection=args.selection,
                                       eligible_candidates=json_argument(args.eligible_candidates, '--eligible-candidates', list,
                                                                         '\'["luna","sol"]\''),
                                       eligible_thinking=json_argument(args.eligible_thinking, '--eligible-thinking', dict,
                                                                       '\'{"opus":["medium"]}\''),
                                       list_candidates=args.list_candidates, target_runtime=args.target_runtime,
                                       assignment=assignment_text(args.assignment) if args.assignment else None,
                                       journal=args.journal, assignment_id=args.assignment_id,
                                       after_failure=args.after_failure,
                                       excluded_candidates=json_argument(args.excluded_candidates, '--excluded-candidates',
                                                                         dict, '\'{"luna":"quota exhausted"}\''))
        else:
            result = resolve(repo, user_config, args.harness, args.role, task)
        if args.profile:
            if result.get('status') == 'selection_required':
                raise ValueError('Select a candidate before rendering a native profile')
            if result.get('executor', 'native') != 'native':
                raise ValueError('external executors own their launch settings; do not use native child profiles')
            result['native_profile'] = native_profile(result)
        print(json.dumps(result, indent=2))
    except (OSError, ValueError) as error:
        parser.exit(2, f'{error}\n')


if __name__ == '__main__':
    main()
