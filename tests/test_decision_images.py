#!/usr/bin/env python3
"""Image evidence integration with local fixtures and deterministic transports."""

import base64
import copy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from PIL import Image
from jsonschema import Draft202012Validator

import support

import decisions
import decision_journal as commands
import journal_store as journal


class DecisionImages(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.image = self.root / 'actual.png'
        Image.new('RGB', (12, 8), 'red').save(self.image)
        self.request = {'family': 'review-triage', 'state': 'After resize at revision abc; expected red.',
                        'instruction': 'Choose the next investigation.',
                        'options': {'investigate': 'Investigate the mismatch.', 'capture': 'Verify the capture.'},
                        'images': [{'path': str(self.image), 'label': 'Actual after resize'}]}
        self.policy = {'enabled': ['review-triage'], 'backend': {
            'protocol': 'systemone', 'endpoint': 'http://localhost:1241/v1/systemone', 'model': 'test-model'}}
        self.path = self.root / 'decisions.jsonl'
        self.trace = journal.trace_config(self.path, self.root, 'triage/abc', 'session-1')
        self.calls = []

    def transport(self, backend, payload):
        self.calls.append(copy.deepcopy(payload))
        qid, question = next(iter(payload['questions'].items()))
        return {'model': backend['model'], 'answers': {qid: {
            'type': 'choice', 'choice': 'investigate',
            'probabilities': {key: float(key == 'investigate') for key in question['criteria']}}}}

    def checkpoint(self):
        return decisions.checkpoint(self.policy, 'review-triage', self.request,
                                    trace=self.trace, transport=self.transport)

    def cases(self, result):
        return [{'decision_id': result['decision_id'], 'expected': ['investigate'],
                 'evidence': 'Independent assessment at abc', 'instruction': 'Which investigation fits?'}]

    def test_schema_and_validator_accept_ordered_image_references(self):
        schema = json.loads((decisions.ROOT / 'schemas/decision.schema.json').read_text())
        Draft202012Validator(schema).validate(self.request)
        decisions.validate_request(self.request)
        for images in ([], self.request['images'] * 5, [{'path': 'actual.png', 'label': 'Actual'}],
                       [{'path': str(self.image), 'label': ' '}],
                       [{'path': str(self.image), 'label': 'Actual', 'unknown': True}]):
            with self.subTest(images=images):
                invalid = dict(self.request, images=images)
                self.assertFalse(Draft202012Validator(schema).is_valid(invalid))
                with self.assertRaises(ValueError):
                    decisions.validate_request(invalid)

    def test_wire_contains_exact_images_labels_and_no_local_paths(self):
        other = self.root / 'expected.jpg'
        Image.new('RGB', (8, 12), 'blue').save(other)
        self.request['images'].insert(0, {'path': str(other), 'label': 'Expected appearance'})
        result = self.checkpoint()
        self.assertEqual(result['status'], 'recommended')
        payload = self.calls[0]
        self.assertEqual([base64.b64decode(url.split(',', 1)[1]) for url in payload['images']],
                         [other.read_bytes(), self.image.read_bytes()])
        self.assertLess(payload['state'].index('1. Expected appearance'),
                        payload['state'].index('2. Actual after resize'))
        self.assertNotIn(str(self.root), json.dumps(payload))
        self.assertIn('visual_calibration_coverage', [w['code'] for w in result['warnings']])

    def test_resume_deduplicates_assets_and_changed_bytes_require_new_identity(self):
        first = self.checkpoint()
        before = self.path.read_bytes()
        second = self.checkpoint()
        self.assertTrue(second['reused'])
        self.assertEqual(first['decision_id'], second['decision_id'])
        self.assertEqual(before, self.path.read_bytes())
        assets = list(self.root.glob('decisions.jsonl.assets/*'))
        self.assertEqual(len(assets), 1)
        self.assertEqual(assets[0].read_bytes(), self.image.read_bytes())
        Image.new('RGB', (12, 8), 'blue').save(self.image)
        with self.assertRaisesRegex(ValueError, 'identity'):
            self.checkpoint()
        self.assertEqual(len(self.calls), 1)

    def test_unchanged_resume_rejects_tampered_retained_assets(self):
        self.checkpoint()
        next(self.root.glob('decisions.jsonl.assets/*')).write_bytes(b'wrong bytes')
        with self.assertRaises(ValueError):
            self.checkpoint()
        self.assertEqual(len(self.calls), 1)

    def test_capture_gap_reuses_same_images_but_rejects_changed_images(self):
        with patch.object(journal, 'append_checkpoint', side_effect=OSError('Disk unavailable')):
            first = self.checkpoint()
        self.assertFalse(first['checkpoint_recorded'])
        result = self.checkpoint()
        self.assertTrue(result['reused'])
        self.assertEqual(result['decision_id'], first['decision_id'])
        self.assertEqual(len(self.calls), 1)
        self.path.write_text(self.path.read_text().splitlines()[0] + '\n')
        Image.new('RGB', (12, 8), 'blue').save(self.image)
        with self.assertRaisesRegex(ValueError, 'identity'):
            self.checkpoint()
        self.assertEqual(len(self.calls), 1)

    def test_repeated_images_retain_one_asset_and_snapshot_submitted_bytes(self):
        original = self.image.read_bytes()
        self.request['images'].append({'path': str(self.image), 'label': 'Second view of the same capture'})

        def changing_source(backend, payload):
            Image.new('RGB', (12, 8), 'blue').save(self.image)
            return self.transport(backend, payload)

        result = decisions.decide(self.policy, self.request, trace=self.trace, transport=changing_source)
        self.assertEqual(result['status'], 'recommended')
        assets = list(self.root.glob('decisions.jsonl.assets/*'))
        self.assertEqual(len(assets), 1)
        self.assertEqual(assets[0].read_bytes(), original)
        self.assertNotEqual(self.image.read_bytes(), original)

    def test_replay_uses_retained_assets_without_original_files_or_base64_logs(self):
        result = self.checkpoint()
        original = copy.deepcopy(self.calls[0])
        self.image.unlink()
        before = self.path.read_bytes()
        report = commands.replay(self.path, self.cases(result), self.policy['backend'], transport=self.transport)
        self.assertTrue(report['complete'])
        self.assertEqual(self.calls[1], original)
        self.assertEqual(before, self.path.read_bytes())
        for payload in self.calls[1:]:
            self.assertEqual(payload['images'], original['images'])
        self.assertNotIn('data:image', before.decode())
        self.assertNotIn('data:image', json.dumps(report))
        self.assertEqual(report['results'][0]['request_hash'], journal.read(self.path)[0]['request_hash'])
        self.assertEqual(journal.inspect(self.path)['decisions'][0]['images'][0]['label'], 'Actual after resize')

    def test_replay_preflights_all_asset_integrity_before_any_call(self):
        first = self.checkpoint()
        self.trace['assignment'] = 'triage/next'
        Image.new('RGB', (12, 8), 'blue').save(self.image)
        second = self.checkpoint()
        assets = sorted(self.root.glob('decisions.jsonl.assets/*'))
        for corruption in ('changed', 'missing'):
            with self.subTest(corruption=corruption):
                saved = assets[0].read_bytes()
                if corruption == 'changed':
                    assets[0].write_bytes(b'wrong bytes')
                else:
                    assets[0].unlink()
                count = len(self.calls)
                with self.assertRaises((OSError, ValueError)):
                    commands.replay(self.path, self.cases(first) + self.cases(second),
                                   self.policy['backend'], transport=self.transport)
                self.assertEqual(len(self.calls), count)
                assets[0].write_bytes(saved)

    def test_corrupt_animated_and_oversized_images_fall_back_before_transport(self):
        for mode in ('corrupt', 'animation', 'dimension', 'pixels', 'bytes'):
            with self.subTest(mode=mode):
                if mode == 'corrupt':
                    self.image.write_bytes(b'not an image')
                elif mode == 'animation':
                    Image.new('RGB', (12, 8), 'red').save(self.image, format='PNG', save_all=True,
                        append_images=[Image.new('RGB', (12, 8), 'blue')])
                elif mode == 'dimension':
                    Image.new('RGB', (4097, 1), 'red').save(self.image)
                elif mode == 'pixels':
                    Image.new('RGB', (2049, 2048), 'red').save(self.image)
                else:
                    with self.image.open('wb') as stream:
                        stream.truncate(7 * 1024 * 1024)
                result = decisions.decide(self.policy, self.request, transport=self.transport)
                self.assertEqual(result['status'], 'host_required')
                self.assertIn('image', result['error'].lower())
                self.assertEqual(self.calls, [])

    def test_combined_encoded_budget_is_checked_before_transport(self):
        Image.new('RGB', (1200, 1000), 'red').save(self.image, compress_level=0)
        self.request['images'] *= 2
        result = decisions.decide(self.policy, self.request, transport=self.transport)
        self.assertEqual(result['status'], 'host_required')
        self.assertIn('8 MiB', result['error'])
        self.assertEqual(self.calls, [])

    def test_nonregular_image_is_rejected_without_waiting_for_a_writer(self):
        self.image.unlink()
        os.mkfifo(self.image)
        result = decisions.decide(self.policy, self.request, transport=self.transport)
        self.assertEqual(result['status'], 'host_required')
        self.assertIn('regular file', result['error'])
        self.assertEqual(self.calls, [])

    def test_evaluation_batch_budget_preflights_replay_and_calibration(self):
        first = self.checkpoint()
        self.trace['assignment'] = 'triage/next'
        second = self.checkpoint()
        suite_path = self.root / 'suite.json'
        suite_path.write_text(json.dumps({'kind': 'adjudicated', 'cases': [
            {'id': str(i), 'request': self.request, 'expected': ['investigate'], 'evidence': 'Human assessment.'}
            for i in range(2)]}))
        self.policy['calibration'] = {'suite': str(suite_path), 'baseline': str(self.root / 'baseline.json')}
        with patch('decision_images.MAX_EVALUATION_BYTES', len(self.calls[0]['images'][0])):
            with self.assertRaisesRegex(ValueError, 'narrow the cases'):
                decisions.benchmark(self.policy, transport=self.transport)
            with self.assertRaisesRegex(ValueError, 'narrow the cases'):
                commands.replay(self.path, self.cases(first) + self.cases(second),
                               self.policy['backend'], transport=self.transport)
        self.assertEqual(len(self.calls), 2)

    def test_text_only_payload_and_recording_do_not_require_pillow(self):
        self.request.pop('images')
        original_import = __import__

        def without_pillow(name, *args, **kwargs):
            if name.startswith('PIL'):
                raise ImportError('Pillow unavailable')
            return original_import(name, *args, **kwargs)

        with patch('builtins.__import__', side_effect=without_pillow):
            result = self.checkpoint()
        self.assertEqual(result['status'], 'recommended')
        expected = {'model': 'test-model', 'state': self.request['state'], 'questions': {
            'review-triage': {'type': 'choice', 'instructions': self.request['instruction'],
                             'criteria': dict(self.request['options'], abstain='Evidence is insufficient to recommend a listed option.')}}}
        self.assertEqual(self.calls, [expected])
        self.assertEqual(journal.read(self.path)[0]['payload'], expected)
        self.assertFalse(list(self.root.glob('decisions.jsonl.assets/*')))

    def test_missing_decoder_records_visible_fallback_with_original_references(self):
        original_import = __import__

        def without_pillow(name, *args, **kwargs):
            if name.startswith('PIL'):
                raise ImportError('Pillow unavailable')
            return original_import(name, *args, **kwargs)

        with patch('builtins.__import__', side_effect=without_pillow):
            result = self.checkpoint()
        self.assertEqual(result['status'], 'host_required')
        self.assertFalse(result['checkpoint_recorded'])
        self.assertIn('requirements.txt', result['error'])
        self.assertEqual(self.calls, [])
        self.assertEqual(journal.read(self.path)[0]['request']['images'], self.request['images'])
        self.assertEqual(journal.inspect(self.path)['count'], 1)

    def test_disabled_family_does_not_read_missing_image(self):
        self.image.unlink()
        self.policy['enabled'] = []
        with patch('builtins.__import__', side_effect=AssertionError('Image decoder must stay unloaded')):
            result = decisions.decide(self.policy, self.request, transport=self.transport)
        self.assertEqual(result['status'], 'host_required')
        self.assertEqual(self.calls, [])

    def test_visual_calibration_preflights_all_cases_and_hashes_image_contents(self):
        suite_path = self.root / 'suite.json'
        missing = dict(self.request, images=[{'path': str(self.root / 'missing.png'), 'label': 'Missing'}])
        cases = [{'id': 'first', 'request': self.request, 'expected': ['investigate'], 'evidence': 'Human assessment.'},
                 {'id': 'missing', 'request': missing, 'expected': ['abstain'], 'evidence': 'Capture absent.'}]
        suite_path.write_text(json.dumps({'kind': 'adjudicated', 'cases': cases}))
        baseline_path = self.root / 'baseline.json'
        self.policy['calibration'] = {'suite': str(suite_path), 'baseline': str(baseline_path)}
        with self.assertRaises((OSError, ValueError)):
            decisions.benchmark(self.policy, transport=self.transport)
        self.assertEqual(self.calls, [])
        suite_path.write_text(json.dumps({'kind': 'adjudicated', 'cases': cases[:1]}))
        baseline = decisions.benchmark(self.policy, transport=self.transport)
        self.assertTrue(baseline['complete'])
        decisions.write_json(baseline_path, baseline)
        self.assertEqual(decisions.calibration_status(self.policy), [])
        Image.new('RGB', (12, 8), 'blue').save(self.image)
        self.assertEqual(decisions.calibration_status(self.policy)[0]['code'], 'calibration_stale')

    def test_http_transports_large_images_but_keeps_text_limit_and_422_evidence(self):
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                owner.calls.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
                self.send_response(422)
                self.end_headers()
                self.wfile.write(b'{"error":"language-only backend"}')

            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        self.policy['backend']['endpoint'] = f'http://127.0.0.1:{server.server_port}/v1/systemone'
        Image.frombytes('RGB', (200, 200), bytes(range(256)) * 468 + bytes(range(192))).save(self.image, compress_level=0)
        result = decisions.decide(self.policy, self.request, trace=self.trace)
        self.assertEqual(result['status'], 'host_required')
        self.assertIn('422', result['error'])
        self.assertEqual(len(self.calls), 1)
        self.assertGreater(len(self.calls[0]['images'][0]), 65536)
        self.assertTrue(list(self.root.glob('decisions.jsonl.assets/*')))
        self.assertNotIn('data:image', self.path.read_text())
        oversized = copy.deepcopy(self.calls[0])
        oversized['state'] = 'x' * 65536
        with self.assertRaisesRegex(ValueError, '64 KiB'):
            decisions.systemone_request(self.policy['backend'], oversized)
        self.assertEqual(len(self.calls), 1)


if __name__ == '__main__':
    unittest.main()
