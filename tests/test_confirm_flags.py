#!/usr/bin/env python3
"""Run confirmation of suspected masked-rule flags in temporary worktrees of a fixture repository."""

import difflib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import support


APP = '''def check(x):
    if x < 0:
        raise ValueError('negative')
    if x < 10:
        raise ValueError('small')
    return x


def size(x):
    if x > 100:
        raise ValueError('too big')
    return x
'''
EXPECTS_ANY_ERROR = '''import sys
import app
try:
    app.{call}
except ValueError:
    sys.exit(0)
sys.exit(1)
'''


def delete_line(text):
    """A unified diff, with context, that replaces the one app.py line containing text by `pass`."""
    lines = APP.splitlines(keepends=True)
    index = next(i for i, line in enumerate(lines) if text in line)
    changed = lines[:index] + [lines[index][:len(lines[index]) - len(lines[index].lstrip())] + 'pass\n'] + lines[index + 1:]
    return ''.join(difflib.unified_diff(lines, changed, 'a/app.py', 'b/app.py'))


class ConfirmFlags(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name) / 'repo'
        self.repo.mkdir()
        (self.repo / 'app.py').write_text(APP)
        (self.repo / 'test_negative.py').write_text(EXPECTS_ANY_ERROR.format(call='check(-1)'))
        (self.repo / 'test_big.py').write_text(EXPECTS_ANY_ERROR.format(call='size(101)'))
        (self.repo / 'test_broken.py').write_text('raise SystemExit(3)\n')
        for args in (['init', '-q'], ['add', '.'], ['-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-qm', 'fixture']):
            subprocess.run(['git', '-C', str(self.repo), *args], check=True)

    def confirm(self, flags, *args, code=0):
        path = Path(self.tmp.name) / 'flags.json'
        path.write_text(json.dumps(flags))
        result = subprocess.run([sys.executable, '-B', str(support.script('confirm-flags.py')), '--repo', str(self.repo),
                                 '--input', str(path), *args], capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        return {row['id']: row for row in json.loads(result.stdout)['results']} if code == 0 else result.stderr

    def flag(self, name, test, removed):
        return {'id': name, 'command': [sys.executable, '-B', test], 'diff': delete_line(removed)}

    def test_a_backup_rule_confirms_and_a_lone_rule_dismisses(self):
        results = self.confirm([self.flag('masked', 'test_negative.py', "raise ValueError('negative')"),
                                self.flag('protected', 'test_big.py', "raise ValueError('too big')")])
        # With the negative check gone, the "small" check still raises the ValueError the test accepts.
        self.assertEqual(results['masked']['status'], 'confirmed')
        self.assertEqual(results['protected']['status'], 'dismissed')
        self.assertEqual((self.repo / 'app.py').read_text(), APP)
        worktrees = subprocess.run(['git', '-C', str(self.repo), 'worktree', 'list'], capture_output=True, text=True).stdout
        self.assertEqual(len(worktrees.strip().splitlines()), 1, worktrees)

    def test_unprovable_flags_stay_unverified(self):
        results = self.confirm([
            {**self.flag('baseline', 'test_broken.py', "raise ValueError('negative')")},
            {**self.flag('bad-diff', 'test_negative.py', "raise ValueError('negative')"), 'diff': '--- a/app.py\n+++ b/app.py\n@@ -1 +1 @@\n-nope\n+x\n'},
            {'id': 'slow', 'command': [sys.executable, '-c', 'import time; time.sleep(5)'], 'diff': delete_line('too big')}],
            '--timeout', '1')
        self.assertEqual({key: row['status'] for key, row in results.items()},
                         {'baseline': 'unverified', 'bad-diff': 'unverified', 'slow': 'unverified'})
        self.assertIn('baseline', results['baseline']['reason'])
        self.assertIn('apply', results['bad-diff']['reason'])
        self.assertIn('timed out', results['slow']['reason'])

    def test_malformed_input_is_rejected_before_any_run(self):
        for bad in ([{'id': 'x', 'command': 'python t.py', 'diff': delete_line('too big')}],
                    [{'id': 'x', 'command': ['python'], 'diff': ''}], {'flags': []},
                    [self.flag('dup', 'test_big.py', 'too big'), self.flag('dup', 'test_big.py', 'too big')]):
            self.confirm(bad, code=2)
        worktrees = subprocess.run(['git', '-C', str(self.repo), 'worktree', 'list'], capture_output=True, text=True).stdout
        self.assertEqual(len(worktrees.strip().splitlines()), 1)


if __name__ == '__main__':
    unittest.main()
