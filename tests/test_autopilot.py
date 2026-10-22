#!/usr/bin/env python3
"""autopilot asks its questions once, confirms a run card, then runs the rest of the loop alone until one stated
terminal state; it never decides an action on the pause list and merges only through the repository's normal path."""
import json
import re
import unittest

import support

ROOT = support.ROOT
SKILL = ROOT / 'skills/autopilot/SKILL.md'
CARD = ROOT / 'skills/autopilot/run-card.md'
# The terminal states and the pause list agreed in .scratch/autopilot/alignment.md (WHAT 4) and ledger U1.
STATES = ('`delivered`', '`delivered-local`', '`merged`', '`waiting-on-user`', '`paused-allowance`', '`blocked`')
PAUSES = ('login or permission prompt', 'credentials', 'spending money', 'deleting data', 'production change',
          'merging without `--auto-merge`', 'missing approval')


def prose(path):
    return ' '.join(path.read_text().split())


class RunCard(unittest.TestCase):
    def test_the_card_holds_every_field_the_stop_condition_needs(self):
        text = CARD.read_text()
        for field in ('## Goal', '## Acceptance criteria', '## Stop condition', '## Granted actions',
                      '## Pause list', '## Assumptions', '## State'):
            self.assertIn(field, text)
        self.assertIn('.scratch/<slug>/autopilot.md', prose(SKILL))

    def test_the_user_confirms_the_card_once_and_is_asked_nothing_after(self):
        text = prose(SKILL)
        self.assertIn('asks the user to confirm it once', text)
        self.assertIn('No phase after align starts before that confirmation', text)
        self.assertIn('After confirmation, ask the user nothing', text)

    def test_the_card_is_re_read_after_compaction(self):
        bootstrap = prose(ROOT / 'bootstrap.md')
        self.assertIn('An autopilot run card with no terminal state', bootstrap)
        self.assertIn('](skills/autopilot/SKILL.md)', bootstrap)


class StopCondition(unittest.TestCase):
    def test_each_run_ends_in_exactly_one_named_state_with_evidence(self):
        stop = SKILL.read_text().split('## Stop', 1)[1]
        listed = re.findall(r'^- (`[a-z-]+`):', stop, re.M)
        self.assertEqual(sorted(listed), sorted(STATES))
        self.assertIn('exactly one terminal state, with its evidence', prose(SKILL))

    def test_delivered_needs_passing_evidence_for_every_acceptance_criterion(self):
        self.assertIn('Never record `delivered` while any acceptance criterion lacks passing evidence', prose(SKILL))

    def test_a_pause_list_action_ends_the_run_waiting_on_the_user_instead_of_being_decided(self):
        text = prose(SKILL)
        for pause in PAUSES:
            self.assertIn(pause, text)
        self.assertIn('ends `waiting-on-user` instead of deciding it', text)

    def test_low_allowance_pauses_after_the_step_in_progress(self):
        text = prose(SKILL)
        self.assertIn('scripts/allowance.py" status', text)
        self.assertIn('`critical`', text)
        self.assertIn('finish the step in progress, commit passing work and end `paused-allowance`', text)


class Flags(unittest.TestCase):
    def test_auto_merge_merges_only_through_the_normal_path(self):
        text = prose(SKILL)
        self.assertIn("merges only through the repository's normal path", text)
        self.assertIn('never by admin override or self-approval', text)

    def test_take_over_reuses_the_session_and_asks_only_what_is_unsettled(self):
        text = prose(SKILL)
        self.assertIn('`autopilot --take-over`', text)
        self.assertIn('reuses accepted decisions, tickets and reports', text)
        self.assertIn('asks only the align questions still unsettled', text)

    def test_late_questions_are_decided_reversibly_and_reported_first(self):
        text = prose(SKILL)
        self.assertIn('prefer the reversible direction', text)
        self.assertIn('record its basis and reversibility in the ledger', text)
        self.assertIn('The final report leads with the open assumptions', text)


class Registration(unittest.TestCase):
    def test_only_the_user_starts_it_on_every_harness(self):
        self.assertIn('disable-model-invocation: true', SKILL.read_text())
        policy = (ROOT / 'skills/autopilot/agents/openai.yaml').read_text()
        self.assertRegex(policy, r'(?m)^policy:\n  allow_implicit_invocation: false$')

    def test_decisions_follow_the_engineering_standard(self):
        first_read = re.search(r'^First read:.*?(?:\n\n|\Z)', SKILL.read_text(), re.M | re.S).group(0)
        self.assertIn('](../../standards/engineering.md)', first_read)

    def test_the_command_is_listed_where_users_and_the_doc_checker_look(self):
        self.assertRegex((ROOT / 'README.md').read_text(), r'(?m)^\| `autopilot` \|')
        self.assertIn('[`/zloop:autopilot`](../autopilot/SKILL.md)', (ROOT / 'skills/brief/pipeline.md').read_text())
        architecture = json.loads((ROOT / '.agents/skills/writing-agent-docs/architecture.json').read_text())
        self.assertEqual(architecture['modules']['autopilot']['docs'], ['skills/autopilot/**/*.md'])
        level = next(i for i, names in enumerate(architecture['levels']) if 'autopilot' in names)
        for phase in ('align', 'refine', 'dispatch', 'review', 'pr'):
            below = next(i for i, names in enumerate(architecture['levels']) if phase in names)
            self.assertLess(level, below, f'autopilot must sit above {phase} to link it')


if __name__ == '__main__':
    unittest.main()
