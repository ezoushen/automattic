#!/usr/bin/env python3
"""Integration regressions; all repositories and state are temporary."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

PLUGIN = Path(__file__).resolve().parent.parent
SCRIPT = PLUGIN / 'scripts/next-tickets.py'


def run(*args, cwd=None, ok=True, input=None):
    p = subprocess.run(args, cwd=cwd, text=True, input=input, capture_output=True)
    if ok:
        assert p.returncode == 0, (args, p.stdout, p.stderr)
    return p


def write_ticket(repo, name, status='ready', deps=(), area=None):
    slug, nn = name.split('/')
    path = repo / '.scratch' / slug / 'issues' / f'{nn}-task.md'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f'---\nticket: {name}\nstatus: {status}\nblocked_by: [{", ".join(deps)}]\ntouches: [{area or name}]\ndevices: []\nmodel: standard\nimplementer:\n---\n# Task\n')
    return path


def check_scheduler():
    with tempfile.TemporaryDirectory(prefix='automattic check ') as tmp:
        repo = Path(tmp) / 'repo'
        repo.mkdir()
        def git(*args):
            return run('git', '-C', str(repo), *args).stdout.strip()
        git('init', '-b', 'main')
        git('config', 'user.name', 'Test')
        git('config', 'user.email', 'test@example.invalid')
        git('commit', '--allow-empty', '-m', 'base')
        def cli(*args, ok=True):
            return run(sys.executable, '-B', str(SCRIPT), '--repo', str(repo), *args, cwd=tmp, ok=ok)
        def names(*args):
            return [x['ticket'] for x in json.loads(cli(*args).stdout)]
        a = write_ticket(repo, 'a/01')
        b = write_ticket(repo, 'b/01')
        assert names('a') == ['a/01']
        assert 'b/01' not in cli('a', '--board').stdout
        assert cli('missing', ok=False).returncode != 0
        assert cli('--unknown', ok=False).returncode != 0
        assert cli('--board', '--counts', ok=False).returncode != 0
        assert cli('a', '--set', 'b/01', 'status=done', ok=False).returncode != 0
        assert 'status: ready' in b.read_text()
        write_ticket(repo, 'b/01', 'implementing', area='shared')
        write_ticket(repo, 'a/01', area='shared')
        assert names('a') == []  # Scope must still see other efforts' area locks.
        write_ticket(repo, 'a/01')
        assert names('a', '--max-live', '1') == []
        write_ticket(repo, 'b/01', deps=['a/01'])
        write_ticket(repo, 'a/01', deps=['b/01'])
        assert 'cycle' in cli('--check', ok=False).stderr.lower()
        write_ticket(repo, 'a/01', deps=['a/01'])
        assert cli('--check', ok=False).returncode != 0
        write_ticket(repo, 'a/01', 'done')
        review_base = git('rev-parse', 'main')
        git('checkout', '-b', 'feat/a')
        (repo / 'prerequisite.txt').write_text('dependency code\n')
        git('add', 'prerequisite.txt')
        git('commit', '-m', 'dependency')
        git('checkout', 'main')
        git('branch', 'feat/b')  # Existing downstream branch predates the dependency.
        assert names('b') == []
        git('merge', '--no-edit', 'feat/a')
        assert names('b') == []
        git('checkout', 'feat/b')
        git('merge', '--no-edit', 'main')
        git('checkout', 'main')
        assert names('b') == []  # Implemented and merged is not reviewed and verified.
        source_report = repo / '.scratch/a/reports/spec-review.md'
        source_report.parent.mkdir(parents=True)
        reviewed_head = git('rev-parse', 'feat/a')
        evidence = (f'---\nreview_status: clean\ndocumentation_status: passed\nreview_head: {reviewed_head}\n'
                    f'review_base: {review_base}\nreview_diff_base: {review_base}\n'
                    f'e2e_status: passed\ne2e_head: {reviewed_head}\n'
                    f'review_by: automattic-spec-reviewer/agent-1\ne2e_by: automattic-e2e-runner/agent-2\n---\n')
        source_report.write_text(evidence)
        cli('a', '--delivery')
        for valid, invalid in [('review_status: clean', 'review_status: findings'),
                               ('documentation_status: passed\n', ''),
                               ('documentation_status: passed', 'documentation_status: findings'),
                               ('documentation_status: passed', 'documentation_status: incomplete'),
                               ('e2e_status: passed', 'e2e_status: not-run'),
                               (f'e2e_head: {reviewed_head}', f'e2e_head: {review_base}'),
                               (f'review_head: {reviewed_head}', f'review_head: {review_base}'),
                               (f'review_diff_base: {review_base}', f'review_diff_base: {reviewed_head}'),
                               # Status without the run that produced it is not delivery evidence.
                               ('review_by: automattic-spec-reviewer/agent-1\n', ''),
                               ('e2e_by: automattic-e2e-runner/agent-2', 'e2e_by: orchestrator'),
                               ('review_by: automattic-spec-reviewer/agent-1', 'review_by: host'),
                               ('review_by: automattic-spec-reviewer/agent-1', 'review_by: none')]:
            source_report.write_text(evidence.replace(valid, invalid))
            assert cli('a', '--delivery', ok=False).returncode != 0
            assert names('b') == []
        source_report.write_text(evidence)
        assert names('b') == ['b/01']
        write_ticket(repo, 'a/02', 'implementing')
        assert names('b') == []  # An unfinished prerequisite effort still holds the wave.
        write_ticket(repo, 'a/02', 'done')
        changed = cli('b', '--set', 'b/01', 'status=implementing', '--counts')
        assert '1 live' in changed.stdout and '0 done' in changed.stdout
        assert cli('--set', 'b/01', 'status=bogus', ok=False).returncode != 0
        assert cli('--set', 'b/01', 'implementer=x\nstatus: done', ok=False).returncode != 0
        # Acceptance requires a real branch descendant and a report in the main checkout.
        base = git('rev-parse', 'feat/b')
        git('checkout', '-b', 'feat/b-01', 'feat/b')
        git('commit', '--allow-empty', '-m', 'ticket')
        git('checkout', 'main')
        reports = repo / '.scratch/b/reports'
        reports.mkdir()
        report = reports / '01.md'
        report.write_text(f'base: {base}\n## Implemented\n- [x] done\n')
        cli('b', '--accept', 'b/01')
        report.write_text('# empty\n')
        assert cli('b', '--accept', 'b/01', ok=False).returncode != 0
        # No ticket is silently dropped or allowed to overwrite another id.
        duplicate = b.with_name('02-duplicate.md')
        duplicate.write_text(b.read_text())
        assert cli('--check', ok=False).returncode != 0
        duplicate.unlink()
        write_ticket(repo, 'a/02', deps=['b/01'])
        assert 'cycle' in cli('--check', ok=False).stderr.lower()  # effort-level cycle
        assert not (repo / 'scripts').exists()


def check_package():
    import re
    portable = json.loads((PLUGIN / 'plugin.json').read_text())
    claude = json.loads((PLUGIN / '.claude-plugin/plugin.json').read_text())
    assert portable['name'] == claude['name'] == 'automattic'
    codex = json.loads((PLUGIN / '.codex-plugin/plugin.json').read_text())
    assert portable['version'] == claude['version'] == codex['version']
    assert codex['skills'] == './skills/'
    assert codex['hooks'] == './harnesses/codex/hooks.json'
    assert portable['extensions']['com.openai']['hooks'] == './harnesses/codex/hooks.json'
    # Codex 0.162 reads a root manifest declaring the Agent Plugins $schema as that format and drops
    # .codex-plugin hooks, so a copied install would register none.
    assert '$schema' not in portable, 'root plugin.json must not declare $schema'
    for path in (PLUGIN / 'skills').glob('*/SKILL.md'):
        implicit = path.parent.name in {'code-comments', 'housekeeping', 'model-routing', 'decision'}
        if not implicit:
            assert 'runtime bootstrap' in path.read_text(), path
            assert 'disable-model-invocation: true' in path.read_text(), path
        else:
            assert 'disable-model-invocation: true' not in path.read_text(), path
        ui = (path.parent / 'agents/openai.yaml').read_text()
        assert f'policy:\n  allow_implicit_invocation: {str(implicit).lower()}\n' in ui, path
    for path in (PLUGIN / 'agents').glob('*.md'):
        assert (PLUGIN / 'roles' / path.name).is_file()
        body = path.read_text().split('---', 2)[2]
        assert 'role_file' in body and len(body.split()) < 60, path
    for folder in ('skills', 'harnesses', 'roles', 'addons'):
        for path in (PLUGIN / folder).rglob('*.md'):
            for link in re.findall(r'\]\(([^)]+)\)', path.read_text()):
                if '://' not in link and '<' not in link:
                    assert (path.parent / link.split('#')[0]).exists(), (path, link)
    for harness, relative in (('claude', 'hooks/hooks.json'), ('codex', 'harnesses/codex/hooks.json')):
        config = json.loads((PLUGIN / relative).read_text())['hooks']
        expected = {'SessionStart', 'PreToolUse', 'Stop'} if harness == 'claude' else {'SessionStart', 'Stop'}
        assert set(config) == expected, (harness, config)
        assert config['Stop'][0]['hooks'][0]['command'].endswith(f'hooks/yield-gate.py" {harness}'), config
        if harness == 'claude':
            guard = config['PreToolUse'][0]
            assert guard['matcher'] == 'Agent|Task' and guard['hooks'][0]['command'].endswith('hooks/agent-model.py"')
            guards = {entry['matcher']: entry['hooks'][0]['command'] for entry in config['PreToolUse']}
            assert guards.get('Bash', '').endswith('hooks/pr-body.py"'), guards
        hook = config['SessionStart'][0]['hooks'][0]
        command = hook['command'].replace('${CLAUDE_PLUGIN_ROOT}', str(PLUGIN)).replace('${PLUGIN_ROOT}', str(PLUGIN))
        import shlex
        result = run(*shlex.split(command), input='{}')
        context = json.loads(result.stdout)['hookSpecificOutput']['additionalContext']
        assert f'harness: {harness}' in context
        assert str(PLUGIN / 'harnesses' / harness / 'adapter.md') in context
        other = 'codex' if harness == 'claude' else 'claude'
        assert f'/harnesses/{other}/' not in context
        for herdr in ('', '0', '1'):
            result = subprocess.run(shlex.split(command), input='{}', text=True,
                                    capture_output=True, check=True,
                                    env=dict(os.environ, HERDR_ENV=herdr))
            context = json.loads(result.stdout)['hookSpecificOutput']['additionalContext']
            assert (str(PLUGIN / 'harnesses/herdr.md') in context) == (herdr == '1')
            assert str(PLUGIN / 'harnesses' / harness / 'adapter.md') in context
            assert f'/harnesses/{other}/' not in context


def check_remediate_catalog():
    import re
    path = PLUGIN / 'skills/remediate/SKILL.md'
    source = path.read_text()
    metadata = source.split('---', 2)[1]
    assert re.search(r'^name: remediate$', metadata, re.M)
    assert re.search(r'^disable-model-invocation: true$', metadata, re.M)
    hint = re.search(r'^argument-hint: (.+)$', metadata, re.M).group(1)
    assert '[goal]' in hint and '[scope]' in hint, hint
    ui = (path.parent / 'agents/openai.yaml').read_text()
    assert 'allow_implicit_invocation: false' in ui
    assert '$automattic:remediate' in ui
    for host in ('claude', 'codex', 'pi', 'opencode'):
        assert (PLUGIN / 'harnesses' / host / 'adapter.md').is_file()
    assert json.loads((PLUGIN / '.codex-plugin/plugin.json').read_text())['skills'] == './skills/'
    for kind in ('tautological-tests', 'misleading-comments'):
        definition = path.parent / 'kinds' / f'{kind}.md'
        assert definition.is_file()
        assert f'kinds/{kind}.md' in source
    assert 'mattpocock' not in source.lower()


def check_build_lock():
    with tempfile.TemporaryDirectory(prefix='automattic mutex ') as tmp:
        env = dict(os.environ, BUILD_LOCK=str(Path(tmp) / 'build.lock'), BUILD_LOCK_TIMEOUT='0')
        wrapper = str(PLUGIN / 'scripts/build-lock.sh')
        # The exec'd build holds the descriptor: a contender must fail until it exits.
        holder = subprocess.Popen(['bash', wrapper, sys.executable, '-c',
                                   'import time; print("locked", flush=True); time.sleep(0.5)'],
                                  env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            assert holder.stdout.readline().strip() == 'locked'
            contender = subprocess.run(['bash', wrapper, 'true'], env=env, capture_output=True, text=True)
            assert contender.returncode != 0 and 'still held' in contender.stderr
            assert holder.wait(timeout=5) == 0
            done = subprocess.run(['bash', wrapper, 'true'], env=env, capture_output=True, text=True)
            assert done.returncode == 0, done.stderr
            failed = subprocess.run(['bash', wrapper, 'sh', '-c', 'exit 7'], env=env, capture_output=True)
            assert failed.returncode == 7
        finally:
            if holder.poll() is None:
                holder.kill()
                holder.wait()


def check_native():
    import selectors
    import time
    from test_claude_effort import check_native_effort
    check_native_effort()
    run('claude', 'plugin', 'validate', '--strict', str(PLUGIN))
    inventory = run('claude', '--plugin-dir', str(PLUGIN), 'plugin', 'details', 'automattic').stdout
    skill_count = len(list((PLUGIN / 'skills').glob('*/SKILL.md')))
    hook_events = len(json.loads((PLUGIN / 'hooks/hooks.json').read_text())['hooks'])
    for expected in (f'Skills ({skill_count})', 'Agents (5)', f'Hooks ({hook_events})'):
        assert expected in inventory, inventory
    # Source inventory does not resolve installed-plugin dependencies.
    installed = json.loads(run('claude', 'plugin', 'list', '--json').stdout)
    current = [entry for entry in installed
               if entry['id'].startswith('automattic@')
               and Path(entry['installPath']).resolve() == PLUGIN]
    for entry in current:
        assert entry.get('enabled') and not entry.get('errors'), entry
    if current:
        print('Claude installed development plugin: enabled, no loading errors')
    else:
        print('Claude installed development plugin: not present; source inventory only')
    server = subprocess.Popen(['codex', 'app-server', '--stdio'], stdin=subprocess.PIPE,
                              stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    selector = selectors.DefaultSelector()
    selector.register(server.stdout, selectors.EVENT_READ)
    def request(identifier, method, params):
        server.stdin.write(json.dumps({'id': identifier, 'method': method, 'params': params}) + '\n')
        server.stdin.flush()
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if selector.select(timeout=1):
                line = server.stdout.readline()
                assert line, 'Codex server exited before responding'
                response = json.loads(line)
                if response.get('id') == identifier:
                    assert 'error' not in response, response
                    return response['result']
        raise AssertionError(f'Codex timed out: {method}')
    try:
        request(1, 'initialize', {'clientInfo': {'name': 'automattic-validation', 'version': '0.3.0'},
                                  'capabilities': {'experimentalApi': True}})
        plugin = request(2, 'plugin/read', {'marketplacePath': str(PLUGIN / '.agents/plugins/marketplace.json'),
                                           'pluginName': 'automattic'})['plugin']
        assert {s['name'] for s in plugin['skills']} == {f'automattic:{p.name}' for p in (PLUGIN / 'skills').iterdir()}
        assert all(Path(s['path']).is_relative_to(PLUGIN / 'skills') for s in plugin['skills'])
        for skill in plugin['skills']:
            interface = skill.get('interface') or {}
            assert 25 <= len(interface.get('shortDescription') or '') <= 64, skill['name']
            assert f"${skill['name']}" in (interface.get('defaultPrompt') or ''), skill['name']
        assert plugin['summary']['localVersion'] == json.loads((PLUGIN / 'plugin.json').read_text())['version']
        print(f'native readers: Claude {skill_count} skills / 5 agents / {hook_events} hook events; Codex {skill_count} shared skills')
    finally:
        selector.close()
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait()


def check_pi_native():
    import shutil
    executable = shutil.which('pi')
    assert executable, 'Pi must be installed for --native-pi'
    cli = Path(executable).resolve()
    if cli.name == 'mise':  # A mise shim resolves to mise itself; ask it for the real CLI.
        cli = Path(run('mise', 'which', 'pi').stdout.strip()).resolve()
    package = next((parent for parent in cli.parents
                    if (parent / 'package.json').is_file()
                    and json.loads((parent / 'package.json').read_text()).get('name', '').endswith('/pi-coding-agent')), None)
    assert package, 'Cannot locate the installed Pi SDK from its CLI'
    print(run('node', str(PLUGIN / 'scripts/test_pi_adapter.mjs'),
              str(package / 'dist/index.js')).stdout.strip())


if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix='automattic cross harness state ') as state:
        os.environ.update(XDG_STATE_HOME=str(Path(state) / 'state'),
                          XDG_CONFIG_HOME=str(Path(state) / 'config'),
                          CODEX_HOME=str(Path(state) / 'codex'))
        check_scheduler()
        check_package()
        check_remediate_catalog()
        check_build_lock()
        run(sys.executable, '-B', str(PLUGIN / 'scripts/test_run_check.py'))
        print('cross-harness regressions: ok (scheduler, hooks, package, remediate, build lock, check runner)')
        if '--native' in sys.argv:
            check_native()
        if '--native-pi' in sys.argv:
            check_pi_native()
