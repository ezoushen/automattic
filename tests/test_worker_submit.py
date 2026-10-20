#!/usr/bin/env python3
"""Worker submission verifies native model and effort before productive work."""

import json
import sys
import unittest

from lifecycle_case import WorkerLifecycleCase


class Submission(WorkerLifecycleCase):
    def test_submit_reads_native_settings_before_running_the_productive_command(self):
        self.register()
        native = self.root / 'native.jsonl'
        native.write_text(json.dumps({'type': 'assistant', 'sessionId': 'native-1',
                                     'isSidechain': False, 'cwd': str(self.root),
                                     'effort': 'high', 'perTurnEffort': 'high',
                                     'message': {'model': 'sonnet'}}) + '\n')
        marker = self.root / 'productive-work'
        request = self.root / 'submit.json'
        request.write_text(json.dumps({'native': str(native), 'timeout': 2,
                                      'argv': [sys.executable, '-c',
                                               'from pathlib import Path; Path("productive-work").write_text("ran")']}))
        result = self.cli('submit', '--attempt', 'ticket-1/1', '--input', str(request))
        self.assertEqual(result['exit_code'], 0)
        self.assertTrue(marker.is_file())
        attempt = self.cli('status')['attempts'][0]
        self.assertEqual(attempt['observed'], {'runtime': 'claude', 'model': 'sonnet', 'effort': 'high'})
        self.assertEqual(self.cli('status')['pending'][0]['kind'], 'wait-finished')

    def test_submit_allows_claude_to_work_in_a_checkout_subdirectory(self):
        self.register()
        child = self.root / '.scratch' / 'reports'
        child.mkdir(parents=True)
        native = self.root / 'native.jsonl'
        native.write_text(json.dumps({'type': 'assistant', 'sessionId': 'native-1',
            'cwd': str(child), 'perTurnEffort': 'high', 'message': {'model': 'sonnet'}}) + '\n')
        request = self.root / 'submit.json'
        request.write_text(json.dumps({'native': str(native), 'timeout': 2,
            'argv': [sys.executable, '-c', 'from pathlib import Path; Path("productive-work").touch()']}))
        self.cli('submit', '--attempt', 'ticket-1/1', '--input', str(request))
        self.assertTrue((self.root / 'productive-work').exists())

    def test_submit_rejects_nested_claude_repository_boundaries(self):
        self.register()
        nested = self.root / 'other-project'
        child = nested / 'src'
        child.mkdir(parents=True)
        native = self.root / 'native.jsonl'
        native.write_text(json.dumps({'type': 'assistant', 'sessionId': 'native-1',
            'cwd': str(child), 'perTurnEffort': 'high', 'message': {'model': 'sonnet'}}) + '\n')
        request = self.root / 'submit.json'
        request.write_text(json.dumps({'native': str(native), 'timeout': 2,
            'argv': [sys.executable, '-c', 'from pathlib import Path; Path("productive-work").touch()']}))
        boundary = nested / '.git'
        for kind in ('directory', 'worktree-file'):
            with self.subTest(kind=kind):
                if kind == 'directory':
                    boundary.mkdir()
                else:
                    boundary.write_text('gitdir: /another/worktree\n')
                self.cli('submit', '--attempt', 'ticket-1/1', '--input', str(request), code=2)
                self.assertFalse((self.root / 'productive-work').exists())
                if kind == 'directory':
                    boundary.rmdir()
                else:
                    boundary.unlink()

    def test_submit_reads_codex_session_and_latest_turn_controls(self):
        self.execution.write_text(json.dumps({'harness': 'codex', 'agent': 'builder', 'job': 'ticket',
                                             'settings': {'model': 'gpt-6.1-sol', 'effort': 'high'}}))
        self.register(runtime='codex')
        native = self.root / 'native.jsonl'
        rows = [{'type': 'session_meta', 'payload': {'id': 'native-1', 'cwd': str(self.root)}},
                {'type': 'turn_context', 'payload': {'model': 'gpt-6.1-sol', 'effort': 'medium', 'cwd': str(self.root)}},
                {'type': 'turn_context', 'payload': {'model': 'gpt-6.1-sol', 'effort': 'high', 'cwd': str(self.root)}}]
        native.write_text(''.join(json.dumps(row) + '\n' for row in rows))
        request = self.root / 'submit.json'
        request.write_text(json.dumps({'native': str(native), 'timeout': 2,
                                      'argv': [sys.executable, '-c', 'print("accepted")']}))
        self.cli('submit', '--attempt', 'ticket-1/1', '--input', str(request))
        self.assertEqual(self.cli('status')['attempts'][0]['observed'],
                         {'runtime': 'codex', 'model': 'gpt-6.1-sol', 'effort': 'high'})

    def submit_scoped(self, request_code=0):
        """Submit the productive-work marker command with the native record at native.jsonl."""
        request = self.root / 'submit.json'
        request.write_text(json.dumps({'native': str(self.root / 'native.jsonl'), 'timeout': 2,
            'argv': [sys.executable, '-c', 'from pathlib import Path; Path("productive-work").touch()']}))
        return self.cli('submit', '--attempt', 'ticket-1/1', '--input', str(request), code=request_code)

    def assert_scope_refused(self):
        """A record whose write scope differs from the launch, or lacks it, blocks work unverified."""
        self.assertIn('verified', self.submit_scoped(2))
        self.assertFalse(self.cli('status')['attempts'][0]['verified'])
        self.assertFalse((self.root / 'productive-work').exists())

    def test_submit_refuses_codex_work_until_the_rollout_shows_the_launch_sandbox_and_approval(self):
        # Rule: submit verifies the write scope from the native record; a different or missing control blocks work.
        self.execution.write_text(json.dumps({'target_runtime': 'codex', 'agent': 'builder', 'job': 'ticket',
            'settings': {'model': 'gpt-6.1-sol', 'effort': 'high'},
            'launch': {'writes': 'worktree', 'verify': {'sandbox': 'workspace-write', 'approval': 'never'}}}))
        self.register(runtime='codex')
        turn = {'model': 'gpt-6.1-sol', 'effort': 'high', 'cwd': str(self.root), 'approval_policy': 'never',
                'sandbox_policy': {'type': 'workspace-write', 'writable_roots': [str(self.root)]}}

        def rollout(**changes):
            context = {key: value for key, value in dict(turn, **changes).items() if value is not None}
            (self.root / 'native.jsonl').write_text(''.join(json.dumps(row) + '\n' for row in (
                {'type': 'session_meta', 'payload': {'id': 'native-1', 'cwd': str(self.root)}},
                {'type': 'turn_context', 'payload': context})))
        for case, changes in (('user default', {'sandbox_policy': {'type': 'danger-full-access'}}),
                              ('other scope', {'sandbox_policy': {'type': 'read-only'}}),
                              ('asks for approval', {'approval_policy': 'on-request'}),
                              ('no sandbox recorded', {'sandbox_policy': None}),
                              ('no approval recorded', {'approval_policy': None})):
            with self.subTest(case=case):
                rollout(**changes)
                self.assert_scope_refused()
        rollout()
        self.submit_scoped()
        self.assertTrue((self.root / 'productive-work').exists())
        self.assertEqual(self.cli('status')['attempts'][0]['observed'], {
            'runtime': 'codex', 'model': 'gpt-6.1-sol', 'effort': 'high', 'sandbox': 'workspace-write',
            'approval': 'never'})

    def test_submit_refuses_claude_work_until_the_transcript_shows_dont_ask_mode(self):
        # Rule: a TUI transcript has no tool list, so its latest permission-mode row is the write-scope evidence.
        execution = json.loads(self.execution.read_text())
        execution['launch'] = {'writes': 'worktree', 'verify': {'permission_mode': 'dontAsk'}}
        self.execution.write_text(json.dumps(execution))
        self.register()
        assistant = {'type': 'assistant', 'sessionId': 'native-1', 'isSidechain': False, 'cwd': str(self.root),
                     'perTurnEffort': 'high', 'message': {'model': 'sonnet'}}

        def transcript(*modes):
            rows = [{'type': 'permission-mode', 'permissionMode': mode, 'sessionId': 'native-1'} for mode in modes]
            (self.root / 'native.jsonl').write_text(''.join(json.dumps(row) + '\n' for row in [*rows, assistant]))
        for case, modes in (('user default', ('auto',)), ('changed after launch', ('dontAsk', 'bypassPermissions')),
                            ('no mode recorded', ())):
            with self.subTest(case=case):
                transcript(*modes)
                self.assert_scope_refused()
        transcript('dontAsk', 'dontAsk')
        self.submit_scoped()
        self.assertTrue((self.root / 'productive-work').exists())
        self.assertEqual(self.cli('status')['attempts'][0]['observed'], {
            'runtime': 'claude', 'model': 'sonnet', 'effort': 'high', 'permission_mode': 'dontAsk'})

    def pi_session(self, *tool_changes, checkpoint=None):
        """A Pi session file whose active branch carries one system message per (added, removed) tool-name change,
        then, when given, a compaction whose system message checkpoints these tool names."""
        rows = [{'type': 'session', 'id': 'native-1', 'cwd': str(self.root)},
                {'type': 'model_change', 'id': 'model', 'parentId': None, 'provider': 'dgx', 'modelId': 'glm-5.3-flash'},
                {'type': 'thinking_level_change', 'id': 'e0', 'parentId': 'model', 'thinkingLevel': 'high'}]
        for index, (added, removed) in enumerate(tool_changes, 1):
            message = {'role': 'system', 'content': '', 'sections': {}}
            message.update({'toolsAdded': [{'name': name, 'description': name, 'parameters': {}} for name in added]}
                           if added else {}, **({'toolsRemoved': [{'name': name} for name in removed]} if removed else {}))
            rows.append({'type': 'message', 'id': f'e{index}', 'parentId': f'e{index - 1}', 'message': message})
        if checkpoint is not None:
            rows.append({'type': 'compaction', 'id': 'compacted', 'parentId': rows[-1]['id'], 'summary': 'Earlier work.',
                         'firstKeptEntryId': 'compacted', 'tokensBefore': 50000, 'systemMessage': {
                             'role': 'system', 'content': '', 'toolsAdded': [{'name': name} for name in checkpoint]}})
        rows.append({'type': 'message', 'id': 'reply', 'parentId': rows[-1]['id'],
                     'message': {'role': 'assistant', 'provider': 'dgx', 'model': 'glm-5.3-flash', 'stopReason': 'stop'}})
        (self.root / 'native.jsonl').write_text(''.join(json.dumps(row) + '\n' for row in rows))

    def test_submit_refuses_pi_work_until_the_session_offers_exactly_the_launch_tools(self):
        # Rule: the tools a Pi session offers replay from its system messages (toolsAdded, then toolsRemoved) and
        # must be exactly the launch's allowlist; an extra tool, such as an extension shell, blocks work.
        self.execution.write_text(json.dumps({'target_runtime': 'pi', 'agent': 'reviewer', 'job': 'diff-review',
            'settings': {'model': 'dgx/glm-5.3-flash', 'effort': 'high'},
            'launch': {'writes': 'none', 'verify': {'tools': ['find', 'grep', 'ls', 'read']}}}))
        self.register(runtime='pi')
        read_only = ['read', 'grep', 'find', 'ls']
        for case, changes in (('user default', [(['read', 'bash', 'edit', 'write', 'bg_run', 'subagent'], [])]),
                              ('tool added later', [(read_only, []), (['bg_run'], [])]),
                              ('no tool record', [])):
            with self.subTest(case=case):
                self.pi_session(*changes)
                self.assert_scope_refused()
        self.pi_session((read_only + ['bg_run'], []), ([], ['bg_run']))
        self.submit_scoped()
        self.assertTrue((self.root / 'productive-work').exists())
        self.assertEqual(self.cli('status')['attempts'][0]['observed'], {
            'runtime': 'pi', 'model': 'dgx/glm-5.3-flash', 'effort': 'high', 'tools': ['find', 'grep', 'ls', 'read']})

    def test_submit_reads_pi_tools_from_the_latest_compaction_checkpoint(self):
        # Rule (boundary): a compaction stores a complete tool checkpoint, so the tools offered after it replace
        # whatever earlier system messages declared.
        self.execution.write_text(json.dumps({'target_runtime': 'pi', 'agent': 'reviewer', 'job': 'diff-review',
            'settings': {'model': 'dgx/glm-5.3-flash', 'effort': 'high'},
            'launch': {'writes': 'none', 'verify': {'tools': ['find', 'grep', 'ls', 'read']}}}))
        self.register(runtime='pi')
        read_only = ['read', 'grep', 'find', 'ls']
        self.pi_session((read_only, []), checkpoint=read_only + ['write'])
        self.assert_scope_refused()
        self.pi_session((read_only + ['bash', 'edit', 'write'], []), checkpoint=read_only)
        self.submit_scoped()
        self.assertTrue((self.root / 'productive-work').exists())
        self.assertEqual(self.cli('status')['attempts'][0]['observed']['tools'], ['find', 'grep', 'ls', 'read'])

    def test_submit_reads_pi_controls_from_active_branch(self):
        self.execution.write_text(json.dumps({'harness': 'pi', 'agent': 'builder', 'job': 'ticket',
                                             'settings': {'model': 'dgx/glm-5.3-flash', 'effort': 'high'}}))
        self.register(runtime='pi')
        native = self.root / 'native.jsonl'
        rows = [{'type': 'session', 'id': 'native-1', 'cwd': str(self.root)},
                {'type': 'model_change', 'id': 'model', 'parentId': None,
                 'provider': 'dgx', 'modelId': 'glm-5.3-flash'},
                {'type': 'thinking_level_change', 'id': 'high', 'parentId': 'model', 'thinkingLevel': 'high'},
                {'type': 'thinking_level_change', 'id': 'abandoned', 'parentId': 'high', 'thinkingLevel': 'low'},
                {'type': 'message', 'id': 'active', 'parentId': 'high',
                 'message': {'role': 'assistant', 'provider': 'dgx', 'model': 'glm-5.3-flash'}}]
        native.write_text(''.join(json.dumps(row) + '\n' for row in rows))
        request = self.root / 'submit.json'
        request.write_text(json.dumps({'native': str(native), 'timeout': 2,
                                      'argv': [sys.executable, '-c', 'print("accepted")']}))
        self.cli('submit', '--attempt', 'ticket-1/1', '--input', str(request))
        self.assertEqual(self.cli('status')['attempts'][0]['observed'],
                         {'runtime': 'pi', 'model': 'dgx/glm-5.3-flash', 'effort': 'high'})

    def test_submit_refuses_pi_provider_error_until_a_successful_probe(self):
        self.execution.write_text(json.dumps({'harness': 'pi', 'agent': 'builder', 'job': 'ticket',
            'settings': {'model': 'dgx/glm-5.3-flash', 'effort': 'high'}}))
        self.register(runtime='pi')
        native = self.root / 'native.jsonl'
        rows = [{'type': 'session', 'id': 'native-1', 'cwd': str(self.root)},
                {'type': 'model_change', 'id': 'model', 'parentId': None,
                 'provider': 'dgx', 'modelId': 'glm-5.3-flash'},
                {'type': 'thinking_level_change', 'id': 'high', 'parentId': 'model',
                 'thinkingLevel': 'high'},
                {'type': 'message', 'id': 'failed', 'parentId': 'high', 'message': {
                    'role': 'assistant', 'provider': 'dgx', 'model': 'glm-5.3-flash',
                    'stopReason': 'error', 'errorMessage': 'Connection error.'}}]
        native.write_text(''.join(json.dumps(row) + '\n' for row in rows))
        request = self.root / 'submit.json'
        request.write_text(json.dumps({'native': str(native), 'timeout': 2,
            'argv': [sys.executable, '-c', 'from pathlib import Path; Path("productive-work").touch()']}))
        error = self.cli('submit', '--attempt', 'ticket-1/1', '--input', str(request), code=2)
        self.assertIn('failed native response', error)
        self.assertFalse((self.root / 'productive-work').exists())
        rows.append({'type': 'message', 'id': 'ready', 'parentId': 'failed', 'message': {
            'role': 'assistant', 'provider': 'dgx', 'model': 'glm-5.3-flash', 'stopReason': 'stop'}})
        native.write_text(''.join(json.dumps(row) + '\n' for row in rows))
        self.cli('submit', '--attempt', 'ticket-1/1', '--input', str(request))
        self.assertTrue((self.root / 'productive-work').exists())

    def test_submit_reads_opencode_assistant_controls_instead_of_requested_defaults(self):
        self.execution.write_text(json.dumps({'harness': 'opencode', 'agent': 'builder', 'job': 'ticket',
                                             'settings': {'model': 'opencode/muse-spark-1.3-contributor-free',
                                                          'effort': 'high'}}))
        self.register(runtime='opencode')
        native = self.root / 'native.json'
        native.write_text(json.dumps({'info': {'id': 'native-1', 'directory': str(self.root),
                                               'model': {'modelID': 'different-default'}},
            'messages': [{'info': {'role': 'assistant', 'sessionID': 'native-1',
                                  'providerID': 'opencode', 'modelID': 'muse-spark-1.3-contributor-free',
                                  'variant': 'high'}}]}))
        request = self.root / 'submit.json'
        request.write_text(json.dumps({'native': str(native), 'timeout': 2,
                                      'argv': [sys.executable, '-c', 'print("accepted")']}))
        self.cli('submit', '--attempt', 'ticket-1/1', '--input', str(request))
        self.assertEqual(self.cli('status')['attempts'][0]['observed'],
                         {'runtime': 'opencode', 'model': 'opencode/muse-spark-1.3-contributor-free',
                          'effort': 'high'})

    def test_submit_refuses_opencode_tool_error_until_a_clean_new_probe(self):
        self.execution.write_text(json.dumps({'harness': 'opencode', 'agent': 'builder', 'job': 'ticket',
            'settings': {'model': 'opencode/muse-spark-1.3-contributor-free'}}))
        self.register(runtime='opencode')
        native = self.root / 'native-export.json'
        assistant = {'role': 'assistant', 'sessionID': 'native-1',
            'providerID': 'opencode', 'modelID': 'muse-spark-1.3-contributor-free'}
        data = {'info': {'id': 'native-1', 'directory': str(self.root)}, 'messages': [
            {'info': {'role': 'user', 'sessionID': 'native-1'}},
            {'info': assistant, 'parts': [{'type': 'tool', 'state': {'status': 'error',
                'error': 'The user rejected permission to use this specific tool call.'}}]},
            {'info': assistant, 'parts': [{'type': 'text', 'text': 'Required read was denied.'}]}]}
        native.write_text(json.dumps(data))
        request = self.root / 'submit.json'
        request.write_text(json.dumps({'native': str(native), 'timeout': 2,
            'argv': [sys.executable, '-c', 'from pathlib import Path; Path("productive-work").touch()']}))
        self.cli('submit', '--attempt', 'ticket-1/1', '--input', str(request), code=2)
        self.assertFalse((self.root / 'productive-work').exists())
        # A later successful startup probe does not inherit the earlier tool failure.
        data['messages'].extend([{'info': {'role': 'user', 'sessionID': 'native-1'}},
            {'info': assistant, 'parts': [{'type': 'tool', 'state': {'status': 'completed'}}]}])
        native.write_text(json.dumps(data))
        self.cli('submit', '--attempt', 'ticket-1/1', '--input', str(request))
        self.assertTrue((self.root / 'productive-work').exists())

    def test_submit_reads_opencode_2_export_controls(self):
        self.execution.write_text(json.dumps({'harness': 'opencode', 'agent': 'builder', 'job': 'ticket',
            'settings': {'model': 'opencode/deepseek-v4.1-flash-free', 'effort': 'high'}}))
        self.register(runtime='opencode')
        self.submit_opencode_v2(self.opencode_v2_export([{'type': 'text', 'text': 'ready'}]))
        self.assertEqual(self.cli('status')['attempts'][0]['observed'],
                         {'runtime': 'opencode', 'model': 'opencode/deepseek-v4.1-flash-free', 'effort': 'high'})
        self.assertTrue((self.root / 'productive-work').exists())

    def test_submit_refuses_opencode_2_tool_error_and_foreign_session(self):
        self.execution.write_text(json.dumps({'harness': 'opencode', 'agent': 'builder', 'job': 'ticket',
            'settings': {'model': 'opencode/deepseek-v4.1-flash-free'}}))
        self.register(runtime='opencode')
        failed = {'type': 'tool', 'name': 'read', 'state': {'status': 'error', 'error': {'message': 'denied'}}}
        ready = [{'type': 'text', 'text': 'ready'}]
        for content, options, reason in ((([failed], [{'type': 'text', 'text': 'Read was denied.'}]), {},
                                          'failed tool call'),
                                         ((ready,), {'session': 'other'}, 'registered session'),
                                         ((ready,), {'directory': '/elsewhere'}, 'worktree')):
            native = self.opencode_v2_export(*content, **options)
            self.assertIn(reason, self.submit_opencode_v2(native, code=2))
            self.assertFalse((self.root / 'productive-work').exists())

    def test_submit_refuses_opencode_work_until_the_export_shows_the_launch_deny_rules(self):
        # Rule: the session's permissions in its export must be exactly the launch's rules; with the last matching
        # rule winning, a missing deny or a later allow widens the scope.
        def deny(*actions):
            return [{'action': action, 'resource': '*', 'effect': 'deny'} for action in actions]
        rules = deny('edit', 'shell', 'subagent')
        self.execution.write_text(json.dumps({'target_runtime': 'opencode', 'agent': 'reviewer', 'job': 'diff-review',
            'settings': {'model': 'opencode/deepseek-v4.1-flash-free', 'effort': 'high'},
            'launch': {'writes': 'none', 'verify': {'permissions': rules}}}))
        self.register(runtime='opencode')
        ready = [{'type': 'text', 'text': 'ready'}]
        for case, permissions in (('none recorded', None), ('subagent allowed', deny('edit', 'shell')),
                                  ('allowed again later', rules + [{'action': 'edit', 'resource': '*', 'effect': 'allow'}])):
            with self.subTest(case=case):
                self.assertIn('verified', self.submit_opencode_v2(self.opencode_v2_export(ready, permissions=permissions),
                                                                  code=2))
                self.assertFalse(self.cli('status')['attempts'][0]['verified'])
                self.assertFalse((self.root / 'productive-work').exists())
        self.submit_opencode_v2(self.opencode_v2_export(ready, permissions=rules))
        self.assertTrue((self.root / 'productive-work').exists())
        self.assertEqual(self.cli('status')['attempts'][0]['observed'], {
            'runtime': 'opencode', 'model': 'opencode/deepseek-v4.1-flash-free', 'effort': 'high',
            'permissions': rules})

    def test_submit_records_submitted_when_the_activity_gated_prompt_succeeds(self):
        self.register()
        native = self.root / 'native.jsonl'
        native.write_text(json.dumps({'type': 'assistant', 'sessionId': 'native-1', 'cwd': str(self.root),
                                      'message': {'model': 'sonnet'}, 'effort': 'high'}) + '\n')
        request = self.root / 'submit.json'
        request.write_text(json.dumps({'native': str(native), 'timeout': 2,
                                      'argv': [sys.executable, '-c', 'print("prompted")']}))
        self.cli('submit', '--attempt', 'ticket-1/1', '--input', str(request))
        self.acknowledge()
        self.record('reconciled', evidence=['native.jsonl:3:idle after prompt'])
        # Completion requires an accepted prompt; the host recorded nothing by hand.
        self.collect()
        self.assertEqual(self.cli('status')['attempts'][0]['result']['status'], 'completed')

    def test_submit_leaves_a_failed_prompt_unsubmitted_for_inspection(self):
        self.register()
        native = self.root / 'native.jsonl'
        native.write_text(json.dumps({'type': 'assistant', 'sessionId': 'native-1', 'cwd': str(self.root),
                                      'message': {'model': 'sonnet'}, 'effort': 'high'}) + '\n')
        request = self.root / 'submit.json'
        request.write_text(json.dumps({'native': str(native), 'timeout': 2,
                                      'argv': [sys.executable, '-c', 'raise SystemExit(1)']}))
        self.cli('submit', '--attempt', 'ticket-1/1', '--input', str(request), code=1)
        self.assertNotIn('submitted', self.cli('status')['attempts'][0])
        # The host inspects the worker and records acceptance itself.
        self.record('submitted', evidence=['native.jsonl:2:accepted prompt'])

    def test_submit_refuses_opencode_provider_error_even_when_settings_match(self):
        self.execution.write_text(json.dumps({'harness': 'opencode', 'agent': 'builder', 'job': 'ticket',
                                             'settings': {'model': 'opencode/muse-spark-1.3-contributor-free'}}))
        self.register(runtime='opencode')
        native = self.root / 'native.json'
        native.write_text(json.dumps({'info': {'id': 'native-1', 'directory': str(self.root)},
            'messages': [{'info': {'role': 'assistant', 'sessionID': 'native-1',
                                  'providerID': 'opencode', 'modelID': 'muse-spark-1.3-contributor-free',
                                  'error': {'name': 'APIError', 'data': {'statusCode': 403}}}}]}))
        request = self.root / 'submit.json'
        request.write_text(json.dumps({'native': str(native), 'timeout': 2,
                                      'argv': [sys.executable, '-c',
                                               'from pathlib import Path; Path("productive-work").touch()']}))
        error = self.cli('submit', '--attempt', 'ticket-1/1', '--input', str(request), code=2)
        self.assertIn('failed native response', error)
        self.assertFalse((self.root / 'productive-work').exists())

    def test_submit_refuses_wrong_unknown_and_unbound_native_controls(self):
        self.register()
        native = self.root / 'native.jsonl'
        marker = self.root / 'productive-work'
        request = self.root / 'submit.json'
        request.write_text(json.dumps({'native': str(native), 'timeout': 2,
                                      'argv': [sys.executable, '-c',
                                               'from pathlib import Path; Path("productive-work").touch()']}))
        good = {'type': 'assistant', 'sessionId': 'native-1', 'cwd': str(self.root),
                'message': {'model': 'sonnet'}, 'effort': 'high'}
        invalid = [dict(good, message={'model': 'opus'}), dict(good, perTurnEffort='medium'),
                   dict(good, effort=None), dict(good, sessionId='different-session'),
                   dict(good, cwd=str(self.root / 'different-worktree')),
                   dict(good, isSidechain=True), dict(good, message='unsupported schema')]
        for row in invalid:
            with self.subTest(row=row):
                native.write_text(json.dumps(row) + '\n')
                self.cli('submit', '--attempt', 'ticket-1/1', '--input', str(request), code=2)
                self.assertFalse(marker.exists())
        native.write_text(json.dumps(good))
        self.cli('submit', '--attempt', 'ticket-1/1', '--input', str(request), code=2)
        self.assertFalse(marker.exists())

    def test_submit_accepts_only_explicit_model_alias_evidence(self):
        self.register()
        native = self.root / 'native.jsonl'
        native.write_text(json.dumps({'type': 'assistant', 'sessionId': 'native-1', 'cwd': str(self.root),
                                     'message': {'model': 'claude-sonnet-native'}, 'effort': 'high'}) + '\n')
        request = self.root / 'submit.json'
        data = {'native': str(native), 'timeout': 2,
                'argv': [sys.executable, '-c', 'print("accepted")']}
        request.write_text(json.dumps(data))
        self.cli('submit', '--attempt', 'ticket-1/1', '--input', str(request), code=2)
        data['model_alias_evidence'] = ['installed binding: sonnet = claude-sonnet-native']
        request.write_text(json.dumps(data))
        native.write_text(json.dumps({'type': 'assistant', 'sessionId': 'native-1', 'cwd': str(self.root),
                                     'message': {'model': 'claude-sonnet-native'}, 'effort': 'medium'}) + '\n')
        self.cli('submit', '--attempt', 'ticket-1/1', '--input', str(request), code=2)
        native.write_text(json.dumps({'type': 'assistant', 'sessionId': 'native-1', 'cwd': str(self.root),
                                     'message': {'model': 'claude-sonnet-native'}, 'effort': 'high'}) + '\n')
        self.cli('submit', '--attempt', 'ticket-1/1', '--input', str(request))
        self.assertTrue(self.cli('status')['attempts'][0]['verified'])

    def test_submit_leaves_unrequested_native_controls_inherited(self):
        self.execution.write_text(json.dumps({'harness': 'claude', 'agent': 'builder', 'job': 'ticket', 'settings': {}}))
        self.register()
        native = self.root / 'native.jsonl'
        native.write_text(json.dumps({'type': 'assistant', 'sessionId': 'native-1', 'cwd': str(self.root),
                                     'message': {'model': 'claude-opus-native'}}) + '\n')
        request = self.root / 'submit.json'
        request.write_text(json.dumps({'native': str(native), 'timeout': 2,
                                      'argv': [sys.executable, '-c', 'print("accepted")']}))
        self.cli('submit', '--attempt', 'ticket-1/1', '--input', str(request))
        attempt = self.cli('status')['attempts'][0]
        self.assertEqual(attempt['requested'], {'runtime': 'claude'})
        self.assertEqual(attempt['observed'], {'runtime': 'claude', 'model': 'claude-opus-native'})

    def test_submit_cannot_duplicate_productive_work_after_reconciliation(self):
        self.register()
        native = self.root / 'native.jsonl'
        native.write_text(json.dumps({'type': 'assistant', 'sessionId': 'native-1', 'cwd': str(self.root),
                                     'message': {'model': 'sonnet'}, 'effort': 'high'}) + '\n')
        request = self.root / 'submit.json'
        request.write_text(json.dumps({'native': str(native), 'timeout': 2,
                                      'argv': [sys.executable, '-c',
                                               'from pathlib import Path; p=Path("count"); p.write_text(p.read_text()+"x" if p.exists() else "x")']}))
        self.cli('submit', '--attempt', 'ticket-1/1', '--input', str(request))
        self.record('reconciled', evidence=['native state inspected; wait finished'])
        self.cli('submit', '--attempt', 'ticket-1/1', '--input', str(request), code=2)
        self.assertEqual((self.root / 'count').read_text(), 'x')

    def test_submit_blocks_an_active_design_hold(self):
        self.register()
        native = self.root / 'native.jsonl'
        native.write_text(json.dumps({'type': 'assistant', 'sessionId': 'native-1', 'cwd': str(self.root),
                                     'message': {'model': 'sonnet'}, 'effort': 'high'}) + '\n')
        self.record('hold', reason='Possible agreement breach', brief=str(self.root / 'brief.md'),
                    evidence=['worker uncertainty signal'])
        request = self.root / 'submit.json'
        request.write_text(json.dumps({'native': str(native), 'timeout': 2,
                                      'argv': [sys.executable, '-c',
                                               'from pathlib import Path; Path("productive-work").touch()']}))
        self.cli('submit', '--attempt', 'ticket-1/1', '--input', str(request), code=2)
        self.assertFalse((self.root / 'productive-work').exists())

    def test_model_or_effort_mismatch_blocks_work_and_acceptance(self):
        for observed in ({'runtime': 'claude', 'model': 'opus', 'effort': 'high'},
                         {'runtime': 'claude', 'model': 'sonnet', 'effort': 'medium'},
                         {'runtime': 'claude', 'model': 'sonnet'},
                         {'runtime': 'codex', 'model': 'sonnet', 'effort': 'high'}):
            if not self.state.exists():
                self.register()
            result = self.record('startup', observed=observed, evidence=['native.jsonl:1'])
            self.assertFalse(result['verified'])
            gate = self.cli('gate', '--attempt', 'ticket-1/1', '--stage', 'work', code=1)
            self.assertIn('runtime settings verification', gate['missing'])
            self.record('submitted', code=2, evidence=['accepted prompt'])
            self.watch(code=2)
        self.ready()
        self.collect()
        self.assertTrue(self.cli('gate', '--attempt', 'ticket-1/1', '--stage', 'accept',
                                 '--revision', 'head-1')['complete'])
        self.cli('gate', '--attempt', 'ticket-1/1', '--stage', 'accept', '--revision', 'head-2', code=1)

    def test_native_alias_requires_binding_evidence_and_inherited_controls_stay_omitted(self):
        self.register()
        observed = {'runtime': 'claude', 'model': 'claude-sonnet-native', 'effort': 'high'}
        self.assertFalse(self.record('startup', observed=observed, evidence=['native.jsonl:1'])['verified'])
        self.assertTrue(self.record('startup', observed=observed, evidence=['native.jsonl:1'],
                                   model_alias_evidence=['installed catalog binds sonnet to claude-sonnet-native'])['verified'])
        self.execution.write_text(json.dumps({'harness': 'claude', 'agent': 'builder', 'job': 'ticket', 'settings': {}}))
        self.register('ticket-2/1', 'ticket-2', 'native-2', 'pane-2')
        self.record('startup', 'ticket-2/1', observed={'runtime': 'claude'}, evidence=['native.jsonl:2'])
        self.assertEqual(self.cli('status')['attempts'][1]['requested'], {'runtime': 'claude'})

    def test_new_ticket_or_role_rejects_reused_native_session(self):
        self.register()
        self.ready()
        self.collect()
        self.record('retain', code=2, reason='Pending repair', next_use='same-ticket repair recheck', evidence=['phase report'])
        self.acknowledge()
        self.record('retain', reason='Pending repair', next_use='same-ticket repair recheck', evidence=['phase report'])
        self.register('ticket-2/1', 'ticket-2', 'native-1', 'pane-2', code=2)
        self.execution.write_text(json.dumps({'harness': 'claude', 'agent': 'reviewer', 'job': 'diff-review', 'settings': {}}))
        self.register('ticket-1/review', 'ticket-1', 'native-1', 'pane-2', code=2)
        self.execution.write_text(json.dumps({'harness': 'claude', 'agent': 'builder', 'job': 'ticket',
                                             'settings': {'model': 'sonnet', 'effort': 'high'}}))
        self.register('ticket-1/2')
        self.assertFalse(self.cli('status')['attempts'][1]['verified'])




if __name__ == '__main__':
    unittest.main()
