#!/usr/bin/env python3
"""A Claude PreToolUse hook keeps an Automattic `writes: none` subagent's writes inside the reports."""
import json
from pathlib import Path
from shlex import quote
import subprocess
import sys
import tempfile
import unittest

import support

HOOK = support.HOOKS / 'read_only_writes.py'
LIFECYCLE = support.ROOT / 'scripts' / 'worker_lifecycle.py'


class ReadOnlyWrites(unittest.TestCase):
    """A main checkout with a ticket worktree; the coordinator's cwd is the worktree, as a subagent's payload shows."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix='automattic read-only ')
        self.addCleanup(tmp.cleanup)
        self.main = Path(tmp.name).resolve() / 'project'
        self.main.mkdir()
        git = ['git', '-C', str(self.main), '-c', 'user.name=t', '-c', 'user.email=t@t', '-c', 'commit.gpgsign=false']
        subprocess.run(['git', 'init', '-q', str(self.main)], check=True)
        subprocess.run(git + ['commit', '-q', '--allow-empty', '-m', 'init'], check=True)
        self.worktree = self.main / '.worktrees/review-1'
        subprocess.run(git + ['worktree', 'add', '-q', '--detach', str(self.worktree)], check=True)
        self.reports = self.main / '.scratch/effort/reports'
        self.reports.mkdir(parents=True)

    def run_hook(self, tool, tool_input, agent='automattic:reviewer', cwd=None, agent_id='a1'):
        """The hook's decision for one tool call a subagent of type `agent` (None: the main session) makes."""
        payload = {'hook_event_name': 'PreToolUse', 'tool_name': tool, 'tool_input': tool_input,
                   'cwd': str(cwd or self.worktree), 'session_id': 'host-1',
                   **({'agent_type': agent, 'agent_id': agent_id} if agent else {})}
        result = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(payload), capture_output=True,
                                text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)['hookSpecificOutput'] if result.stdout.strip() else None

    def assert_denied(self, decision, path, agent='automattic:reviewer'):
        self.assertIsNotNone(decision, path)
        self.assertEqual(decision['permissionDecision'], 'deny')
        reason = decision['permissionDecisionReason']
        for words in (agent, 'writes: none', str(path), f'{self.main}/.scratch/<slug>/reports/'):
            self.assertIn(words, reason)

    def test_a_read_only_agent_edits_only_files_under_the_main_checkouts_reports(self):
        # Rule (T11): Edit, Write and NotebookEdit from a `writes: none` agent (reviewer, verifier, under its plugin
        # name or a generated profile) are denied outside <main>/.scratch/<slug>/reports/; its report is allowed.
        inside = self.worktree / 'src/app.py'
        report = self.reports / '03.md'
        notebook = self.worktree / 'n.ipynb'
        elsewhere = Path('/private/var/tmp/automattic-probe.txt')
        for agent in ('automattic:reviewer', 'automattic:verifier', 'automattic-reviewer-0123456789ab'):
            with self.subTest(agent=agent):
                self.assert_denied(self.run_hook('Edit', {'file_path': str(inside), 'old_string': 'a',
                                                          'new_string': 'b'}, agent), inside, agent)
                self.assert_denied(self.run_hook('Write', {'file_path': str(elsewhere), 'content': 'x'}, agent),
                                   elsewhere, agent)
                self.assert_denied(self.run_hook('NotebookEdit', {'notebook_path': str(notebook), 'new_source': 'x'},
                                                 agent), notebook, agent)
                # The reports directory itself, and a look-alike path that only starts with it, are not a report.
                lookalike = self.main / '.scratch/effort/reports-old/03.md'
                self.assert_denied(self.run_hook('Write', {'file_path': str(lookalike), 'content': 'x'}, agent),
                                   lookalike, agent)
                escape = f'{self.reports}/../../../src/app.py'
                self.assert_denied(self.run_hook('Edit', {'file_path': escape, 'old_string': 'a', 'new_string': 'b'},
                                                 agent), self.main / 'src/app.py', agent)
                self.assertIsNone(self.run_hook('Edit', {'file_path': str(report), 'old_string': 'a',
                                                         'new_string': 'b'}, agent))
                self.assertIsNone(self.run_hook('Write', {'file_path': str(self.reports / 'notes/run.log'),
                                                          'content': 'x'}, agent))

    def register(self, native_session, worktree):
        """Register a reviewer attempt for `worktree` whose native session is `native_session`, as the coordinator
        registers a Claude subagent by its agentId."""
        execution = self.reports / 'execution.json'
        execution.write_text(json.dumps({'agent': 'reviewer', 'job': 'reproduce', 'settings': {'model': 'sonnet'}}))
        event = self.reports / 'register.json'
        event.write_text(json.dumps({
            'kind': 'register', 'attempt': f'review-{native_session}/1', 'assignment': f'review-{native_session}',
            'repo': str(self.main), 'worktree': str(worktree), 'head': 'head-1', 'execution': str(execution),
            'runtime': 'claude', 'worker': native_session, 'native_session': native_session, 'owned': True,
            'packet': str(support.assignment_file(self.reports, 'reproduce'))}))
        subprocess.run([sys.executable, '-B', str(LIFECYCLE), 'record', '--state', str(self.reports / 'workers.sqlite'),
                        '--input', str(event)], check=True, capture_output=True)

    def test_a_registered_read_only_agent_also_writes_in_its_own_worktree_only(self):
        # Rule (T11, coordinator's decision): a reviewer keeps its temporary experiment edits, which collection's
        # restored-worktree check guards, so the attempt whose native_session is the subagent's agent_id adds its
        # registered worktree; another worktree and the main checkout stay denied, and an agent with no registered
        # attempt gets the reports only.
        other = self.main / '.worktrees/review-2'
        subprocess.run(['git', '-C', str(self.main), 'worktree', 'add', '-q', '--detach', str(other)], check=True)
        self.register('a1', self.worktree)
        self.register('a2', other)
        mine, theirs, tracked = self.worktree / 'src/app.py', other / 'src/app.py', self.main / 'src/app.py'
        edit = {'old_string': 'a', 'new_string': 'b'}
        self.assertIsNone(self.run_hook('Edit', {'file_path': str(mine), **edit}))
        self.assertIsNone(self.run_hook('Bash', {'command': 'echo x > src/app.py'}))
        self.assertIsNone(self.run_hook('Edit', {'file_path': str(self.reports / '03.md'), **edit}))
        for path in (tracked, theirs):
            decision = self.run_hook('Edit', {'file_path': str(path), **edit})
            self.assert_denied(decision, path)
            self.assertIn(f'its registered worktree {self.worktree}', decision['permissionDecisionReason'])
        self.assert_denied(self.run_hook('Bash', {'command': f'echo x > {quote(str(tracked))}'}), tracked)
        unregistered = self.run_hook('Edit', {'file_path': str(mine), **edit}, agent_id='a3')
        self.assert_denied(unregistered, mine)
        self.assertNotIn('registered worktree', unregistered['permissionDecisionReason'])

    def test_a_read_only_agents_shell_redirects_and_tee_only_into_the_reports(self):
        # Rule (T11): a Bash command from a `writes: none` agent that clearly writes a literal path by `>`, `>>`,
        # `&>` or `tee` outside the reports is denied; relative paths follow the command's own `cd`.
        app, log = self.worktree / 'src/app.py', self.worktree / 'out.log'
        denied = {
            'echo x > src/app.py': app,
            f'echo x >> {quote(str(app))}': app,
            'make test 2>/dev/null | tee out.log': log,
            'tee -a out.log < /dev/null': log,
            f'cd {quote(str(self.worktree / "src"))} && echo x >app.py': app,
            'npm test &> out.log': log,
            f'cat <<EOF > {quote(str(app))}\nx\nEOF': app,
            f'git -C {quote(str(self.worktree))} status; echo x > "{app}"': app,
        }
        for command, path in denied.items():
            with self.subTest(command=command):
                self.assert_denied(self.run_hook('Bash', {'command': command}), path)

    def test_a_shell_command_that_writes_no_clear_path_outside_the_reports_runs(self):
        # Rule (T11), the conservative side: devices, fd copies, the reports, quoted or heredoc `>`, comparisons
        # and paths only known at run time are not flagged (hosts/claude/workers.md lists what stays uncaught).
        allowed = [
            'make test > /dev/null 2>&1',
            'ls missing 2>/dev/null >&2',
            f'echo x > {quote(str(self.reports / "03.md"))}',
            f'make test | tee -a {quote(str(self.reports / "run.log"))}',
            f'cd {quote(str(self.reports))} && echo x > 03.md',
            'grep -n ">" src/app.py',
            "awk '{ print > \"out\" }' src/app.py",
            f'cat <<\'EOF\' > {quote(str(self.reports / "03.md"))}\nexpected a > b\nEOF',
            '(( count > 3 )) && echo many',
            '[[ b > a ]] && echo later',
            'echo x > "$OUT"',
            'echo x > $(mktemp)',
            "python3 -c \"open('src/app.py', 'w')\"",
            'git status --short',
        ]
        for command in allowed:
            with self.subTest(command=command):
                self.assertIsNone(self.run_hook('Bash', {'command': command}))

    def test_writers_other_agents_and_the_main_session_are_not_checked(self):
        # Rule (T11): only `writes: none` Automattic agents are held to their reports.
        inside = {'file_path': str(self.worktree / 'src/app.py'), 'content': 'x'}
        for agent in ('automattic:builder', 'automattic-builder-0123456789ab', 'general-purpose', 'reviewer', None):
            with self.subTest(agent=agent):
                self.assertIsNone(self.run_hook('Write', inside, agent))
                self.assertIsNone(self.run_hook('Bash', {'command': 'echo x > src/app.py'}, agent))

    def test_claude_runs_the_check_before_every_file_and_shell_tool(self):
        # Rule (T11): hooks/hooks.json registers the check as a PreToolUse hook for Edit, Write, NotebookEdit and Bash;
        # the registered command itself denies a reviewer's write into its worktree.
        config = json.loads((support.HOOKS / 'hooks.json').read_text())['hooks']['PreToolUse']
        commands = {tool: [hook['command'] for entry in config if tool in entry['matcher'].split('|')
                           for hook in entry['hooks'] if hook['command'].endswith('hooks/read_only_writes.py"')]
                    for tool in ('Edit', 'Write', 'NotebookEdit', 'Bash')}
        for tool, found in commands.items():
            self.assertEqual(len(found), 1, (tool, commands))
        tool_inputs = {'Edit': {'file_path': 'src/app.py', 'old_string': 'a', 'new_string': 'b'},
                       'Write': {'file_path': 'src/app.py', 'content': 'x'},
                       'NotebookEdit': {'notebook_path': 'n.ipynb', 'new_source': 'x'},
                       'Bash': {'command': 'echo x > src/app.py'}}
        for tool, [command] in commands.items():
            payload = {'hook_event_name': 'PreToolUse', 'tool_name': tool, 'tool_input': tool_inputs[tool],
                       'cwd': str(self.worktree), 'agent_type': 'automattic:reviewer', 'agent_id': 'a1'}
            result = subprocess.run(command.replace('${CLAUDE_PLUGIN_ROOT}', str(support.ROOT)), shell=True,
                                    input=json.dumps(payload), capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)['hookSpecificOutput']['permissionDecision'], 'deny', tool)


if __name__ == '__main__':
    unittest.main()
