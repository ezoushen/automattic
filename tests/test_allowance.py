#!/usr/bin/env python3
"""Exercise the subscription allowance reader through its CLI."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import support


SCRIPT = support.script('allowance.py')
NOW = 1792000000  # A fixed clock for every reading.


class Allowance(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='automattic allowance ')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.enterContext(patch.dict(os.environ, {'XDG_STATE_HOME': str(self.root / 'state')}))
        self.codex = self.root / 'codex'
        self.codex.mkdir()

    def run_script(self, *args, stdin='', code=0):
        process = subprocess.run([sys.executable, '-B', str(SCRIPT), *args], input=stdin,
                                 capture_output=True, text=True)
        self.assertEqual(process.returncode, code, process.stdout + process.stderr)
        return json.loads(process.stdout) if process.stdout.strip() else process.stderr

    def status(self, now=NOW):
        return self.run_script('status', '--codex-root', str(self.codex), '--now', str(now))

    def rollout(self, name, mtime, *windows, limit_id='codex'):
        path = self.codex / '2026/10/15' / f'rollout-{name}.jsonl'
        path.parent.mkdir(parents=True, exist_ok=True)
        primary, secondary = (list(windows) + [None, None])[:2]
        line = {'timestamp': '2026-10-15T00:00:00Z', 'type': 'event_msg', 'payload': {
            'type': 'token_count', 'info': None, 'rate_limits': {
                'limit_id': limit_id, 'primary': primary, 'secondary': secondary, 'plan_type': 'pro'}}}
        other = {'timestamp': '2026-10-15T00:00:01Z', 'type': 'event_msg', 'payload': {'type': 'agent_message'}}
        path.write_text(json.dumps(line) + '\n' + json.dumps(other) + '\n')
        os.utime(path, (mtime, mtime))

    def window(self, used, minutes, remaining_minutes):
        return {'used_percent': used, 'window_minutes': minutes, 'resets_at': NOW + remaining_minutes * 60}

    def test_codex_windows_come_from_the_newest_rollout_with_a_projection(self):
        self.rollout('old', NOW - 7200, self.window(99.0, 300, 100))
        # Five-hour window half gone at 30% used; weekly window three quarters gone at 70%.
        self.rollout('new', NOW - 60, self.window(30.0, 300, 150), self.window(70.0, 10080, 2520))
        codex = self.status()['providers']['codex']
        self.assertEqual(codex['age_seconds'], 60)
        five, week = codex['windows']
        self.assertEqual((five['window_minutes'], five['used_percent'], five['elapsed'], five['projected_percent']),
                         (300, 30.0, 0.5, 60.0))
        self.assertEqual((week['used_percent'], week['elapsed'], week['projected_percent']), (70.0, 0.75, 93.3))
        self.assertEqual(codex['level'], 'critical')
        self.assertEqual(self.status()['providers']['claude'], {'level': 'unknown', 'reason': 'no reading'})

    def test_early_projection_is_not_trusted_and_a_reset_window_is_dropped(self):
        # 20% used a tenth of the way in would project to 200%; too early to count.
        self.rollout('a', NOW - 10, self.window(20.0, 10080, 9072), self.window(95.0, 300, -5))
        codex = self.status()['providers']['codex']
        self.assertEqual(len(codex['windows']), 1)
        self.assertEqual((codex['windows'][0]['projected_percent'], codex['level']), (None, 'normal'))

    def test_claude_readings_come_from_the_status_line_snapshot(self):
        line = {'model': {'id': 'claude-opus-5-5'}, 'rate_limits': {
            'five_hour': {'used_percentage': 82, 'resets_at': NOW + 900},
            'seven_day': {'used_percentage': 40, 'resets_at': NOW + 3 * 86400}}}
        self.assertEqual(self.run_script('record-claude', '--now', str(NOW - 30), stdin=json.dumps(line)), '')
        claude = self.status()['providers']['claude']
        self.assertEqual(claude['age_seconds'], 30)
        self.assertEqual([window['window_minutes'] for window in claude['windows']], [300, 10080])
        self.assertEqual(claude['level'], 'elevated')
        # Status-line input without limits, or unreadable input, leaves the snapshot alone and never fails.
        self.run_script('record-claude', '--now', str(NOW), stdin=json.dumps({'model': {}}))
        self.run_script('record-claude', '--now', str(NOW), stdin='not json')
        self.assertEqual(self.status()['providers']['claude']['age_seconds'], 30)

    def test_levels_hold_until_use_falls_well_below_and_a_dwell_passes(self):
        def level(used, now):
            self.rollout(f'r{now}', now, self.window(used, 300, 280))
            return self.status(now)['providers']['codex']['level']
        self.assertEqual(level(50.0, NOW), 'normal')
        self.assertEqual(level(82.0, NOW + 60), 'elevated')
        self.assertEqual(level(70.0, NOW + 120), 'elevated')  # above the 65% exit
        self.assertEqual(level(91.0, NOW + 180), 'critical')
        self.assertEqual(level(85.0, NOW + 240), 'critical')  # above the 80% exit
        self.assertEqual(level(60.0, NOW + 300), 'critical')  # within the five-minute dwell
        self.assertEqual(level(60.0, NOW + 600), 'normal')


    def test_a_stale_reading_counts_only_what_was_already_used(self):
        # Use never falls before a reset, so an old reading is a floor; its rate is no longer known.
        self.rollout('old', NOW - 3600, self.window(50.0, 10080, 2520), self.window(85.0, 300, 60))
        codex = self.status()['providers']['codex']
        self.assertTrue(codex['stale'])
        self.assertEqual([w['projected_percent'] for w in codex['windows']], [None, None])
        self.assertEqual(codex['level'], 'elevated')
        self.rollout('fresh', NOW - 60, self.window(50.0, 10080, 2520))
        self.assertFalse(self.status()['providers']['codex']['stale'])

    def test_codex_home_sets_where_rollouts_are_read(self):
        self.rollout('a', NOW - 10, self.window(95.0, 300, 10))
        process = subprocess.run([sys.executable, '-B', str(SCRIPT), 'status', '--now', str(NOW)],
                                 capture_output=True, text=True, env=dict(os.environ, CODEX_HOME=str(self.root / 'h')))
        self.assertEqual(json.loads(process.stdout)['providers']['codex']['level'], 'unknown')
        (self.root / 'h').mkdir()
        self.codex.rename(self.root / 'h/sessions')
        process = subprocess.run([sys.executable, '-B', str(SCRIPT), 'status', '--now', str(NOW)],
                                 capture_output=True, text=True, env=dict(os.environ, CODEX_HOME=str(self.root / 'h')))
        self.assertEqual(json.loads(process.stdout)['providers']['codex']['level'], 'critical')


if __name__ == '__main__':
    unittest.main()
