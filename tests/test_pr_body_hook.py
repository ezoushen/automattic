#!/usr/bin/env python3
"""The Bash PreToolUse hook lints a PR description before `gh pr create` or `gh pr edit` publishes it."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import support

HOOK = support.HOOKS / 'pr-body.py'
GOOD = '## Why\n\nLookups fall back to the shipped bundle when the feed is empty.\n'


class PrBodyHook(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cwd = Path(self.tmp.name)

    def body(self, text, name='pr.md'):
        path = self.cwd / name
        path.write_text(text)
        return path

    def run_hook(self, command, tool='Bash', env=None):
        payload = {'hook_event_name': 'PreToolUse', 'tool_name': tool, 'tool_input': {'command': command},
                   'cwd': str(self.cwd)}
        result = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(payload), capture_output=True,
                                text=True, env=dict(os.environ, **(env or {})), timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)['hookSpecificOutput'] if result.stdout.strip() else None

    def assert_denied(self, command, *words):
        decision = self.run_hook(command)
        self.assertIsNotNone(decision, command)
        self.assertEqual(decision['permissionDecision'], 'deny')
        for word in ('writing.md',) + words:
            self.assertIn(word, decision['permissionDecisionReason'])

    def test_inline_body_is_denied(self):
        for command in ('gh pr create --title "fix: x y z" --body "hi"', 'gh pr edit 12 -b "hi"',
                        'gh pr create --fill', 'cd repo && gh pr edit 3 --body="hi"',
                        'cd repo\ngh pr edit 3 --body hi',
                        'gh pr create --title "fix: x y z" --body "$(cat <<\'EOF\'\n## Why\n\nIt broke.\nEOF\n)"',
                        'git log -3\ngh pr edit 3 --body "uses x << y\nmore"',
                        "python3 -c 'x = 1 << shift'\ngh pr edit 3 --body x",
                        'for n in 3 4; do gh pr edit $n --body "x"; done', 'if true; then gh pr edit 3 -b x; fi',
                        '{ gh pr edit 3 --body x; }', 'env GH_TOKEN=x gh pr create --body x',
                        'command gh pr edit 3 --body x', 'time gh pr edit 3 --body x'):
            with self.subTest(command=command):
                self.assert_denied(command, '--body-file')

    def test_clean_body_file_is_allowed(self):
        path = self.body(GOOD)
        self.assertIsNone(self.run_hook(f'gh pr create --title "fix: fall back to the bundle" --body-file {path}'))
        self.assertIsNone(self.run_hook(f'gh pr edit 12 -F {path}'))

    def test_lint_errors_in_the_body_file_are_denied(self):
        path = self.body(GOOD + '\nEvidence: /Users/me/notes.md\n')
        self.assert_denied(f'gh pr edit 12 --body-file {path}', 'private path')

    def test_relative_body_file_resolves_against_the_hook_cwd(self):
        self.body(GOOD + '\nSee .scratch/x/report.md\n', 'bad.md')
        self.assert_denied('gh pr edit 12 --body-file bad.md', 'private path')

    def test_titles_follow_the_repository_convention_not_the_hook(self):
        path = self.body(GOOD)
        self.assertIsNone(self.run_hook('gh pr edit 12 --title "Add plural support"'))
        self.assertIsNone(self.run_hook(f'gh pr create --title "Add plural support" --body-file {path}'))

    def test_variables_set_earlier_in_the_command_resolve(self):
        self.body(GOOD)
        self.body(GOOD + '\nSee .scratch/x/report.md\n', 'bad.md')
        for command in (f'S={self.cwd}; gh pr edit 12 --body-file $S/pr.md',
                        f'export S="{self.cwd}" && gh pr edit 12 --body-file "${{S}}/pr.md"'):
            with self.subTest(command=command):
                self.assertIsNone(self.run_hook(command))
        self.assert_denied(f'S={self.cwd}\ngh pr edit 12 -F $S/bad.md', 'private path')

    def test_relative_body_file_follows_cd_in_the_command(self):
        (self.cwd / 'repo').mkdir()
        self.body(GOOD, 'repo/pr.md')
        self.body(GOOD + '\nSee .scratch/x/report.md\n', 'repo/bad.md')
        self.assertIsNone(self.run_hook('cd repo && gh pr edit 12 --body-file pr.md'))
        self.body(GOOD, 'top.md')
        self.assertIsNone(self.run_hook('(cd repo && ls) && gh pr edit 12 --body-file top.md'))
        self.assertIsNone(self.run_hook('(cd repo && gh pr edit 12 --body-file pr.md)'))
        self.assert_denied(f'R={self.cwd}/repo; cd "$R"; gh pr edit 12 --body-file bad.md', 'private path')
        self.assert_denied('cd "$UNSET_DIR" && gh pr edit 12 --body-file pr.md', 'literal')

    def test_body_file_written_by_a_heredoc_in_the_same_command_is_linted(self):
        write = f"S={self.cwd}; cat > $S/new.md <<'EOF'\n{{}}EOF\ngh pr create --title 'fix: a b c' --body-file $S/new.md"
        self.assertIsNone(self.run_hook(write.format(GOOD)))
        self.assert_denied(write.format(GOOD + 'See /Users/me/x.md\n'), 'private path')

    def test_heredoc_on_stdin_is_linted(self):
        stdin = "gh pr edit 12 --body-file - <<'EOF'\n{}EOF"
        self.assertIsNone(self.run_hook(stdin.format(GOOD)))
        self.assert_denied(stdin.format(GOOD + 'See /Users/me/x.md\n'), 'private path')

    def test_body_file_changed_earlier_in_the_command_is_unresolvable(self):
        self.body(GOOD)
        for command in ("printf 'x' >> pr.md && gh pr edit 3 --body-file pr.md",
                        "cat >> pr.md <<'EOF'\nmore\nEOF\ngh pr edit 3 -F pr.md",
                        "sed -i '' 's/a/b/' pr.md && gh pr edit 3 --body-file pr.md",
                        "python3 - pr.md <<'EOF'\nprint(1)\nEOF\ngh pr edit 3 --body-file pr.md"):
            with self.subTest(command=command):
                self.assert_denied(command, 'literal')
        self.assertIsNone(self.run_hook('python3 lint-pr-body.py pr.md && gh pr edit 3 --body-file pr.md'))

    def test_unresolvable_body_file_is_denied(self):
        for command in ('S=/tmp/x; gh pr edit 12 --body-file $S/pr.md', 'gh pr edit 12 --body-file missing.md'):
            with self.subTest(command=command):
                self.assert_denied(command, 'literal')

    def test_other_commands_are_allowed(self):
        for command in ('gh pr view 12 --json body', 'gh pr checks 12 --watch', 'gh pr merge 12 --merge',
                        'gh pr edit 12 --add-label ready', 'echo "gh pr create --body x" > notes.txt'):
            with self.subTest(command=command):
                self.assertIsNone(self.run_hook(command))
        self.assertIsNone(self.run_hook('gh pr create --body x', tool='Read'))

    def test_opt_out_and_malformed_input_never_block(self):
        self.assertIsNone(self.run_hook('gh pr create --body x', env={'AUTOMATTIC_PR_HOOK': 'off'}))
        result = subprocess.run([sys.executable, str(HOOK)], input='not json', capture_output=True, text=True,
                                timeout=10)
        self.assertEqual((result.returncode, result.stdout), (0, ''))


if __name__ == '__main__':
    unittest.main()
