#!/usr/bin/env python3
"""Usage accounting through the read-only command line interface."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import support


SCRIPT = support.script('claude_usage.py')


class ClaudeUsage(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()

    def response(self, identity, stamp, output, **extra):
        return {'type': 'assistant', 'timestamp': stamp, 'cwd': '/work/ticket-13',
                'requestId': 'req-' + identity,
                'message': {'id': identity, 'model': 'test-model', 'usage': {
                    'input_tokens': 3, 'cache_creation_input_tokens': 5,
                    'cache_read_input_tokens': 100, 'output_tokens': output,
                    'output_tokens_details': {'thinking_tokens': 2}}}, **extra}

    def write(self, relative, records):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(''.join(json.dumps(row) + '\n' for row in records))
        return path

    def run_report(self, *args):
        result = subprocess.run([sys.executable, str(SCRIPT), '--root', str(self.root),
                                 '--since', '2026-09-27T18:00:00+08:00',
                                 '--until', '2026-09-28T01:00:00+08:00', *args],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_streams_workers_and_external_sessions_reconcile_without_credit_estimates(self):
        streamed = self.response('a', '2026-09-27T10:00:00Z', 10)
        parent = self.write('project/parent.jsonl', [streamed,
            self.response('a', '2026-09-27T10:00:01Z', 20)])
        self.write('project/parent/subagents/agent-one.jsonl', [
            self.response('b', '2026-09-27T11:00:00Z', 30)])
        self.write('other/copied.jsonl', [streamed])
        self.write('project/external.jsonl', [self.response('c', '2026-09-27T12:00:00Z', 40)])
        before = parent.read_bytes()
        result = self.run_report('--session', 'parent', '--related-worktree', '/work/ticket-13')
        self.assertEqual(result['total']['responses'], 3)
        self.assertEqual(result['total']['output_tokens'], 90)
        self.assertEqual(result['total']['thinking_tokens'], 6)
        self.assertEqual(result['native_family']['output_tokens'], 50)
        self.assertEqual(result['worktree_associated']['output_tokens'], 40)
        self.assertEqual(result['total']['cache_read_input_tokens'], 300)
        self.assertEqual(result['quality']['cross_file_duplicate_ids'], ['a'])
        self.assertIsNone(result['subscription_credits'])
        self.assertEqual(parent.read_bytes(), before)

    def test_window_uses_first_block_and_excludes_updates_after_cutoff(self):
        self.write('project/parent.jsonl', [
            self.response('before', '2026-09-27T17:59:59+08:00', 10),
            self.response('before', '2026-09-27T18:00:01+08:00', 20),
            self.response('inside', '2026-09-28T00:59:59+08:00', 30),
            self.response('inside', '2026-09-28T01:00:01+08:00', 100),
            self.response('at-end', '2026-09-28T01:00:00+08:00', 50)])
        result = self.run_report()
        self.assertEqual(result['total']['responses'], 1)
        self.assertEqual(result['total']['output_tokens'], 30)
        self.assertEqual(list(result['hours']), ['2026-09-28T00:00:00+08:00'])

    def test_partial_tail_and_bad_usage_are_reported_without_losing_valid_usage(self):
        invalid = self.response('invalid', '2026-09-27T10:00:00Z', -1)
        synthetic = self.response('synthetic', '2026-09-27T10:00:00Z', 500)
        synthetic['message']['model'] = '<synthetic>'
        path = self.write('project/parent.jsonl', [
            self.response('valid', '2026-09-27T10:00:00Z', 10), invalid, synthetic])
        with path.open('a') as stream:
            stream.write('{"type":')
        result = self.run_report()
        self.assertEqual(result['total']['output_tokens'], 10)
        self.assertEqual(result['quality']['invalid_usage'], [{'path': str(path), 'line': 2}])
        self.assertEqual(result['quality']['parse_errors'], [{'path': str(path), 'line': 4}])

    def test_ambiguous_timezone_fails_before_scanning(self):
        result = subprocess.run([sys.executable, str(SCRIPT), '--since', '2026-09-27T18:00:00',
                                 '--until', '2026-09-28T01:00:00+08:00'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn('explicit UTC offset', result.stderr)
        self.assertEqual(result.stdout, '')


if __name__ == '__main__':
    unittest.main()
