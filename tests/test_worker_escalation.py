#!/usr/bin/env python3
"""Escalations and design holds pause dependent work until a ruling."""

import json
import sys
import unittest

from lifecycle_case import WorkerLifecycleCase


class Escalation(WorkerLifecycleCase):
    def test_possible_breach_requires_human_source_and_unchanged_ruling_criteria(self):
        self.register()
        self.ready()
        self.escalate()
        source = self.root / 'ruling.md'
        source.write_text('Controlled ruling source fixture, not actual human E2E.\n')
        fields = dict(decision='Preserve API; investigate compatible approach', criteria=str(self.root / 'criteria.md'),
                      ruling_source=str(source), evidence=['ruling and canonical criteria'])
        self.record('ruling', code=2, authority='host', source_kind='host-investigation', **fields)
        self.record('ruling', code=2, authority='human', source_kind='phase-decision', **fields)
        self.cli('gate', '--attempt', 'ticket-1/1', '--stage', 'work', code=1)
        self.record('ruling', authority='human', source_kind='user-message', **fields)
        self.assertTrue(self.cli('gate', '--attempt', 'ticket-1/1', '--stage', 'work')['complete'])
        (self.root / 'criteria.md').write_text('Unauthorized subsequent criterion change\n')
        gate = self.cli('gate', '--attempt', 'ticket-1/1', '--stage', 'work', code=1)
        self.assertIn('approved criteria integrity', gate['missing'])

    def test_within_agreement_uncertainty_preserves_phase_opt_in(self):
        for i, enabled in enumerate(([], ['alignment'])):
            execution = json.loads(self.execution.read_text())
            execution['decision_policy'] = {'enabled': enabled}
            self.execution.write_text(json.dumps(execution))
            attempt = f'ticket-{i}/1'
            self.register(attempt, f'ticket-{i}', f'native-{i}', f'pane-{i}')
            self.ready(attempt)
            result = self.escalate('within-agreement', attempt)
            self.assertEqual(result['consultation_enabled'], bool(enabled))
            self.cli('gate', '--attempt', attempt, '--stage', 'work', code=1)
            source = self.root / 'host-investigation.md'
            source.write_text('Host checked a compatible implementation; decision backend is advisory.\n')
            self.record('ruling', attempt, authority='host', decision='Use compatible implementation',
                criteria=str(self.root / 'criteria.md'), ruling_source=str(source),
                source_kind='host-investigation', evidence=['checked investigation and accepted criteria'])
            self.assertTrue(self.cli('gate', '--attempt', attempt, '--stage', 'work')['complete'])

    def test_possible_breach_upgrades_uncertainty_and_delivers_early(self):
        self.register()
        self.ready()
        self.escalate('within-agreement')
        marker = self.root / 'parent.json'
        notify = {'argv': [sys.executable, '-c',
            f'import sys; open({str(marker)!r}, "w").write(sys.argv[1])', '{receipt}'], 'timeout': 2}
        result = self.escalate('possible-breach', notify=notify)
        message = json.loads(marker.read_text())
        self.assertEqual(message['event_id'], result['event_id'])
        self.assertEqual(message['kind'], 'hold')
        self.assertEqual(message['receipt']['risk'], 'possible-breach')
        self.assertEqual(self.cli('status')['holds'][0]['risk'], 'possible-breach')
        self.cli('gate', '--attempt', 'ticket-1/1', '--stage', 'work', code=1)

    def test_design_hold_blocks_only_dependent_work_and_cannot_be_downgraded(self):
        self.register()
        self.ready()
        self.escalate()
        self.record('hold', code=2, risk='within-agreement', reason='Another model thinks it is safe',
                    brief=str(self.root / 'decision.md'), evidence=['model preference'])
        self.register('ticket-2/1', 'ticket-2', 'native-2', 'pane-2')
        native = self.root / 'independent.jsonl'
        native.write_text(json.dumps({'type': 'assistant', 'sessionId': 'native-2',
            'cwd': str(self.root), 'effort': 'high', 'message': {'model': 'sonnet'}}) + '\n')
        request = self.root / 'independent-submit.json'
        request.write_text(json.dumps({'native': str(native), 'timeout': 2,
            'argv': [sys.executable, '-c', 'from pathlib import Path; Path("independent-work").touch()']}))
        self.cli('submit', '--attempt', 'ticket-2/1', '--input', str(request))
        self.assertTrue((self.root / 'independent-work').exists())
        self.cli('gate', '--attempt', 'ticket-1/1', '--stage', 'work', code=1)

    def test_escalation_can_pause_work_without_creating_a_request_file(self):
        self.register()
        self.ready()
        criteria = self.root / 'criteria.md'
        criteria.write_text('Preserve the public API\n')
        brief = self.root / 'pending brief.md'
        result = self.cli('escalate', '--attempt', 'ticket-1/1', '--risk', 'possible-breach',
            '--criteria', str(criteria), '--brief', str(brief), '--reason', 'API compatibility is uncertain',
            '--evidence', 'native progress')
        self.assertEqual(result['risk'], 'possible-breach')
        self.assertFalse(brief.exists())
        self.assertEqual(self.cli('status')['holds'][0]['canonical_criteria'], str(criteria.resolve()))
        self.cli('gate', '--attempt', 'ticket-1/1', '--stage', 'work', code=1)

    def test_collection_preserves_pending_design_escalation(self):
        self.register()
        self.ready()
        self.record('hold', reason='Possible agreement breach', brief=str(self.root / 'brief.md'),
                    evidence=['worker blocker'])
        report = self.root / 'report.md'
        report.write_text('Blocked on the human agreement ruling\n')
        request = self.root / 'collect.json'
        request.write_text(json.dumps({'status': 'blocked', 'head': 'head-1', 'report': str(report),
            'evidence': ['blocked report'], 'disposition': {'kind': 'retain',
            'reason': 'Human ruling remains pending', 'next_use': 'Resume only after ruling',
            'evidence': ['brief and governing contract']}}))
        self.cli('collect', '--attempt', 'ticket-1/1', '--input', str(request))
        status = self.cli('status')
        self.assertEqual([r['kind'] for r in status['pending']], ['hold'])
        self.assertEqual(status['holds'][0]['assignment'], 'ticket-1')

    def test_design_hold_requires_ruling_and_updated_criteria_before_resume(self):
        self.register()
        self.ready()
        brief = self.root / 'decision-brief.md'
        self.record('hold', reason='Public API conflicts with accepted ADR', brief=str(brief),
                    evidence=['diff.kt:42'])
        self.cli('gate', '--attempt', 'ticket-1/1', '--stage', 'work', code=1)
        self.record('ruling', code=2, authority='user', decision='Accept revised API', evidence=['user message'])
        self.record('ruling', code=2, authority='user', decision='Accept revised API', criteria='ticket@revision-2',
                    evidence=['user message'])
        brief.write_text('Current ADR; conflicting API; alternatives; recommendation; reserved user decision\n')
        self.record('ruling', authority='user', decision='Accept revised API', criteria='ticket updated@revision-2',
                    evidence=['user message', 'canonical ticket revision-2'])
        self.assertTrue(self.cli('gate', '--attempt', 'ticket-1/1', '--stage', 'work')['complete'])
        self.collect()

    def test_design_hold_survives_closing_a_blocked_worker(self):
        self.register()
        self.ready()
        brief = self.root / 'decision.md'
        brief.write_text('API alternatives and reserved user decision\n')
        self.record('hold', reason='User API ruling needed', brief=str(brief), evidence=['ADR:4'])
        report = self.root / 'blocked.md'
        report.write_text('Blocked on API ruling\n')
        self.record('result', status='blocked', head='head-1', report=str(report), evidence=['decision brief'])
        self.acknowledge()
        self.record('closed', evidence=['native closure confirmed'])
        self.assertEqual(self.cli('status')['holds'][0]['assignment'], 'ticket-1')
        self.record('ruling', authority='user', decision='Accept option B', criteria='ticket@revision-2',
                    evidence=['user message', 'canonical ticket revision-2'])
        self.assertEqual(self.cli('status')['holds'], [])




if __name__ == '__main__':
    unittest.main()
