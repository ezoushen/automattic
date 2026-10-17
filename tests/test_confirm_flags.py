#!/usr/bin/env python3
"""Run confirmation of suspected masked-rule flags in temporary worktrees of a fixture repository."""

import difflib
import json
import signal
from pathlib import Path
import subprocess
import sys
import tempfile
import time
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
print('ASSERTION FAILED: no ValueError')
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
        (self.repo / 'test_slow_when_patched.py').write_text(
            "import pathlib, time\nif 'SLOW' in pathlib.Path('app.py').read_text():\n    time.sleep(30)\n")
        (self.repo / '.confirm-flag.diff').write_text('keep')
        (self.repo / 'test_keeps_tracked_file.py').write_text(
            "import pathlib, sys\nsys.exit(pathlib.Path('.confirm-flag.diff').read_text() != 'keep')\n")
        for args in (['init', '-q'], ['add', '.'], ['-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-qm', 'fixture']):
            subprocess.run(['git', '-C', str(self.repo), *args], check=True)

    def confirm(self, flags, *args, code=0):
        path = Path(self.tmp.name) / 'flags.json'
        path.write_text(json.dumps(flags))
        result = subprocess.run([sys.executable, '-B', str(support.script('confirm-flags.py')), '--repo', str(self.repo),
                                 '--input', str(path), *args], capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        return {row['id']: row for row in json.loads(result.stdout)['results']} if code == 0 else result.stderr

    def flag(self, name, test, removed, **extra):
        return {'id': name, 'command': [sys.executable, '-B', test], 'diff': delete_line(removed), **extra}

    def worktrees(self):
        listed = subprocess.run(['git', '-C', str(self.repo), 'worktree', 'list'], capture_output=True, text=True).stdout
        return listed.strip().splitlines()

    def test_a_backup_rule_confirms_and_a_lone_rule_dismisses(self):
        results = self.confirm([self.flag('masked', 'test_negative.py', "raise ValueError('negative')"),
                                self.flag('protected', 'test_big.py', "raise ValueError('too big')",
                                          fails_with='ASSERTION FAILED')])
        # With the negative check gone, the "small" check still raises the ValueError the test accepts.
        self.assertEqual(results['masked']['status'], 'confirmed')
        self.assertEqual(results['protected']['status'], 'dismissed')
        self.assertEqual((self.repo / 'app.py').read_text(), APP)
        self.assertEqual(len(self.worktrees()), 1, self.worktrees())

    def test_a_failure_without_the_expected_text_is_left_for_the_agent(self):
        broken = dict(self.flag('import-error', 'test_big.py', 'too big', fails_with='ASSERTION FAILED'),
                      diff=''.join(difflib.unified_diff(APP.splitlines(True), APP.replace('def size', 'def sized').splitlines(True),
                                                        'a/app.py', 'b/app.py')))
        results = self.confirm([broken, self.flag('no-marker', 'test_big.py', "raise ValueError('too big')")])
        self.assertEqual({key: row['status'] for key, row in results.items()}, {'import-error': 'failed', 'no-marker': 'failed'})
        self.assertIn('AttributeError', results['import-error']['output_tail'])

    def test_the_failure_text_is_found_even_before_a_long_output_tail(self):
        (self.repo / 'test_verbose.py').write_text(
            "import sys, app\ntry:\n    app.size(101)\nexcept ValueError:\n    sys.exit(0)\n"
            "print('ASSERTION FAILED')\nprint('x' * 5000)\nsys.exit(1)\n")
        subprocess.run(['git', '-C', str(self.repo), 'add', '.'], check=True)
        subprocess.run(['git', '-C', str(self.repo), '-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-qm', 'verbose'],
                       check=True)
        results = self.confirm([self.flag('verbose', 'test_verbose.py', "raise ValueError('too big')",
                                          fails_with='ASSERTION FAILED')])
        self.assertEqual(results['verbose']['status'], 'dismissed')

    def test_only_the_supplied_diff_changes_the_worktree(self):
        results = self.confirm([{'id': 'tracked', 'command': [sys.executable, '-B', 'test_keeps_tracked_file.py'],
                                 'diff': delete_line('too big')}])
        self.assertEqual(results['tracked']['status'], 'confirmed')

    def test_a_timeout_after_a_passing_baseline_is_unverified_and_stops_descendants(self):
        marker = Path(self.tmp.name) / 'descendant-alive'
        spawn = ('import subprocess, sys, time; subprocess.Popen([sys.executable, "-c", '
                 f'"import time, pathlib; time.sleep(2); pathlib.Path(%r).write_text(\'x\')"]); time.sleep(30)' % str(marker))
        diff = ''.join(difflib.unified_diff(APP.splitlines(True), (APP + '# SLOW\n').splitlines(True), 'a/app.py', 'b/app.py'))
        results = self.confirm([{'id': 'slow', 'command': [sys.executable, '-B', 'test_slow_when_patched.py'], 'diff': diff},
                                {'id': 'spawner', 'command': [sys.executable, '-c', spawn], 'diff': delete_line('too big')}],
                               '--timeout', '1')
        self.assertEqual((results['slow']['status'], results['slow']['exit']), ('unverified', None))
        self.assertIn('timed out', results['slow']['reason'])
        time.sleep(3)
        self.assertFalse(marker.exists(), 'a descendant of a timed-out command kept running')

    def test_a_missing_executable_is_unverified_without_losing_other_results(self):
        results = self.confirm([{'id': 'missing', 'command': ['/nonexistent/runner'], 'diff': delete_line('too big')},
                                self.flag('masked', 'test_negative.py', "raise ValueError('negative')")])
        self.assertEqual((results['missing']['status'], results['masked']['status']), ('unverified', 'confirmed'))

    def test_termination_stops_runs_and_removes_worktrees(self):
        path = Path(self.tmp.name) / 'flags.json'
        path.write_text(json.dumps([{'id': 'hang', 'command': [sys.executable, '-c', 'import time; time.sleep(60)'],
                                     'diff': delete_line('too big')}]))
        process = subprocess.Popen([sys.executable, '-B', str(support.script('confirm-flags.py')), '--repo', str(self.repo),
                                    '--input', str(path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        deadline = time.monotonic() + 10
        while len(self.worktrees()) < 2 and time.monotonic() < deadline:
            time.sleep(.1)
        process.send_signal(signal.SIGTERM)
        self.assertNotEqual(process.wait(timeout=20), 0)
        process.stdout.close(); process.stderr.close()
        self.assertEqual(len(self.worktrees()), 1, self.worktrees())

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
