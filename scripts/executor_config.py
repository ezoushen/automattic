"""Read and validate executor configuration and per-session overrides; imports no routing or decision code."""
import hashlib
import json
import os
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[1]
EFFORTS = ('none', 'off', 'minimal', 'low', 'medium', 'high', 'xhigh', 'max', 'ultra')


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


def validate_execution_config(data, location):
    """Validate only bundled schemas; configuration never loads code or remote schemas."""
    if isinstance(data, dict) and ({'routes', 'executors'} & data.keys()):
        raise ValueError(f'{location}: legacy executor packages/routes require explicit migration '
                         'to agents.<agent>.executor.type/config; see runtime/config/troubleshooting.md')
    if isinstance(data, dict) and isinstance(data.get('models'), dict):
        for name, definition in data['models'].items():
            if isinstance(definition, dict) and ({'model', 'executors'} & definition.keys()):
                raise ValueError(f'{location}: models.{name} requires runtime bindings; move the model ID '
                                 f'to models.{name}.runtimes.<runtime>.id and launch routes to top-level runtimes; '
                                 'see runtime/config/catalog.md')
    if isinstance(data, dict):
        profiles = data.get('profiles', {})
        agents = data.get('agents', {})
        if isinstance(profiles, dict) and any(isinstance(profile, dict) and 'agents' in profile
                                             for profile in profiles.values()):
            raise ValueError(f'{location}: migrate profile agents to shared agents; profiles now contain '
                             'profiles.<name>.<agent>.<worker-runtime>.candidate/thinking')
        if isinstance(agents, dict) and any(isinstance(entry, dict) and 'candidates' in entry and 'default' in entry
                                           for entry in agents.values()):
            raise ValueError(f'{location}: migrate pool defaults to sparse routing profiles; '
                             'agents define candidates only; see runtime/config/troubleshooting.md')
    validate_schema(data, location, 'executors.schema.json')
    calibration = data.get('decisions', {}).get('calibration')
    if calibration and Path(calibration['suite']).resolve() == Path(calibration['baseline']).resolve():
        raise ValueError(f'{location}: calibration suite and baseline must be different files')
    groups = [data.get('agents', {}), data.get('jobs', {})]
    policies = [binding for definition in data.get('models', {}).values()
                for binding in definition['runtimes'].values()]
    for runtime, definition in data.get('runtimes', {}).items():
        for caller, executor in definition['executors'].items():
            if (executor['type'] == 'subagent' and not executor.get('config', {}).get('agent')
                    and caller != runtime):
                raise ValueError(f'{location}: runtime {runtime!r} requires a named bridge or external '
                                 f'executor from {caller!r}; an unnamed subagent runs in its caller')
    for agents in groups:
        for agent, entry in agents.items():
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
                         'after installing requirements.txt; see runtime/config/executors.md') from error
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
    return state / 'zloop/sessions' / f'{digest}.json'


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
