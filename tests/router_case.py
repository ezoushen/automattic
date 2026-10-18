"""Shared fixture for the test_router_*.py files: a temporary repository and routing configuration."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

import support


models = support.load_script('agent_models.py', 'models')


class RouterCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='automattic router ')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.user = self.root / 'user.json'
        self.project = self.root / '.automattic/executors.json'
        self.project.parent.mkdir()
        env = patch.dict(os.environ, {'HERDR_ENV': '1', 'AUTOMATTIC_PROFILE': '',
                                     'AUTOMATTIC_SESSION': '', 'XDG_STATE_HOME': str(self.root / 'state'),
                                     'CODEX_HOME': str(self.root / 'codex-home')})
        env.start()
        self.addCleanup(env.stop)
        self.data = {
            'models': {},
            'runtimes': {runtime: {'executors': {
                runtime: {'type': 'subagent'},
                'herdr': {'type': 'skill', 'config': {'skill': 'herdr', 'instruction': 'Run one worker.'}}
            }} for runtime in ('codex', 'claude')},
            'agents': {'builder': {'candidates': ['luna', 'sol', 'opus']}},
        }
        for name, runtime, default, allowed in (
            ('luna', 'codex', 'xhigh', ['xhigh', 'max']),
            ('sol', 'codex', 'medium', ['medium', 'high']),
            ('opus', 'claude', 'medium', ['medium', 'high']),
        ):
            self.data['models'][name] = {'description': name, 'runtimes': {runtime: {
                'id': runtime + '/' + name, 'thinking': {'default': default, 'allowed': allowed}}}}
        self.save()

    def save(self):
        self.user.write_text(json.dumps(self.data))

    def resolve(self, host='claude', **kwargs):
        if 'eligible_candidates' in kwargs and 'excluded_candidates' not in kwargs:
            # Tests narrow pools for setup; production callers must state their own reasons.
            configured = self.data['agents']['builder'].get('candidates', [])
            kwargs['excluded_candidates'] = {name: 'Not under test.' for name in configured
                                             if name not in (kwargs['eligible_candidates'] or configured)}
        return models.resolve_execution(self.root, self.root / 'absent.json', self.user,
                                        host, 'builder', kwargs.pop('task', {}), job=kwargs.pop('job', 'ticket'),
                                        **kwargs)

    def profile(self, value):
        self.data['profiles'] = {'balanced': {'builder': value}}
        self.data['router'] = {'type': 'profile', 'profile': 'balanced'}
        self.save()

    def choose(self, name, **values):
        return dict(candidate=name, reason='Assignment fits.', **values)

    def decision_router(self, reply=None):
        self.requests = []
        requests = self.requests

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                payload = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                requests.append(payload)
                criteria = payload['questions']['worker']['criteria']
                answer = {'type': 'choice', 'choice': next(iter(criteria)),
                          'probabilities': {key: float(i == 0) for i, key in enumerate(criteria)},
                          'confidence': 1.0}
                result = {'model': payload['model'], 'answers': {'worker': answer}}
                if reply:
                    reply(result)
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps(result).encode())

            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        self.data['router'] = {'type': 'decision-model', 'protocol': 'systemone',
                               'endpoint': f'http://127.0.0.1:{server.server_port}/v1/systemone',
                               'model': 'local/OpenJev-27B-Splash', 'timeout_seconds': 1}
        self.save()

    def fallback_router(self):
        def abstain(result):
            answer = result['answers']['worker']
            answer.update(choice='abstain', probabilities={key: float(key == 'abstain')
                                                         for key in answer['probabilities']})
        self.decision_router(abstain)
        self.data['profiles'] = {'balanced': {'builder': {'codex': {'candidate': 'sol', 'thinking': 'high'}}}}
        self.data['router']['fallback_profile'] = 'balanced'
        self.save()

    def free_and_local(self):
        """Add a training endpoint and a local model to the builder pool."""
        for name, cost, data in (('muse', 'free', 'trains'), ('glm', 'local', 'local')):
            self.data['models'][name] = {'description': name, 'cost': cost, 'data': data,
                                         'runtimes': {'codex': {'id': 'codex/' + name}}}
        for name in ('luna', 'sol'):
            self.data['models'][name]['cost'] = 'subscription'
        self.data['agents']['builder']['candidates'] += ['muse', 'glm']
        self.save()
