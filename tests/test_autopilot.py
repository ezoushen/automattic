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
        state = text.split('## State', 1)[1]
        for key in ('confirmed:', 'session:', 'auto-merge:', 'phase:', 'terminal:', 'resume:'):
            self.assertIn(key, state)
        self.assertIn('.scratch/<slug>/autopilot.md', prose(SKILL))

    def test_the_card_is_workflow_state_that_a_rule_about_project_files_does_not_forbid(self):
        # Seen live on Codex: "no new files" in the goal kept the card out of .scratch/ and it lived only in chat.
        self.assertIn('a principle about the project\'s files never keeps them out of `.scratch/`', prose(SKILL))

    def test_the_goal_form_runs_aligns_interview_before_the_card(self):
        start = ' '.join(SKILL.read_text().split('## Start', 1)[1].split('\n## ', 1)[0].split())
        self.assertIn('**`autopilot <goal>`:** run [align](../align/SKILL.md) on the goal, with its interview', start)

    def test_the_user_confirms_the_card_once_and_is_asked_nothing_after(self):
        text = prose(SKILL)
        self.assertIn('asks the user to confirm it once', text)
        self.assertIn('No phase after align starts before that confirmation', text)
        self.assertIn('After confirmation, ask the user nothing', text)
        self.assertIn('Record the confirmation on the card', text)
        # Seen live on Codex: an unconfirmed card was marked `waiting-on-user`, which hides it from the bootstrap trigger.
        self.assertIn('Waiting for this confirmation is not a terminal state: `terminal:` stays empty', text)

    def test_the_card_is_re_read_after_compaction(self):
        bootstrap = prose(ROOT / 'bootstrap.md')
        self.assertIn('An autopilot run card with no terminal state', bootstrap)
        self.assertIn('that this conversation created or took over', bootstrap)
        self.assertIn('unconfirmed card starts no phase', bootstrap)
        self.assertIn('](skills/autopilot/SKILL.md)', bootstrap)


class ComposedPhases(unittest.TestCase):
    def test_the_confirmed_card_stands_for_the_checks_the_phases_ask_of_the_user(self):
        text = prose(SKILL)
        self.assertIn("stands for the user's check of newly cut and split tickets", text)
        self.assertIn('Candidate ADRs the user has not approved are not written', text)
        self.assertIn('approved ones are written as dispatch says', text)

    def test_each_phase_runs_with_the_grants_the_loop_needs(self):
        run = SKILL.read_text().split('## Run', 1)[1].split('\n## ', 1)[0]
        self.assertRegex(run, r'1\. \[refine\]\(\.\./refine/SKILL\.md\) the brief into tickets')
        self.assertRegex(run, r'\[dispatch\]\(\.\./dispatch/SKILL\.md\)[^\n]*`--autofix`')
        self.assertRegex(' '.join(run.split()), r'\[pr\]\(\.\./pr/SKILL\.md\).*push the effort branch and open the PR')

    def test_without_a_pr_host_the_run_ends_at_local_delivery_instead_of_publishing(self):
        run = ' '.join(SKILL.read_text().split('## Run', 1)[1].split('\n## ', 1)[0].split())
        self.assertIn('In a repository with no PR host, publish nothing', run)
        self.assertIn('end `delivered-local`', run)

    def test_the_card_lists_every_pause(self):
        pauses = ' '.join(CARD.read_text().split('## Pause list', 1)[1].split('\n## ', 1)[0].split()).lower()
        for pause in ('login or permission prompts', 'credentials', 'spending money', 'deleting data',
                      'production changes', 'merging without `--auto-merge`', 'a missing approval',
                      'weakening a verify', 'narrowing a user decision'):
            self.assertIn(pause, pauses)

    def test_an_effort_run_directly_on_main_ends_at_local_delivery(self):
        local = next(line for line in SKILL.read_text().split('## Stop', 1)[1].split('\n- ') if line.startswith('`delivered-local`'))
        self.assertIn('ran directly on `main`', ' '.join(local.split()))

    def test_choices_reserved_to_the_user_by_the_phases_are_never_decided(self):
        text = prose(SKILL)
        self.assertIn('The pause list is never decided', text)
        self.assertIn("weakening an acceptance criterion's Verify", text)
        self.assertIn('narrowing a decision the user made', text)


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
        self.assertIn('for a provider this run uses', text)
        self.assertIn('finish the step in progress, commit passing work and end `paused-allowance`', text)


class Flags(unittest.TestCase):
    def test_auto_merge_merges_only_through_the_normal_path(self):
        text = prose(SKILL)
        merged = next(line for line in SKILL.read_text().splitlines() if line.startswith('- `merged`'))
        self.assertIn('only with `--auto-merge`', merged)
        self.assertIn("merges only through the repository's normal path", text)
        self.assertIn('never by admin override or self-approval', text)

    def test_take_over_reuses_the_session_and_asks_only_what_is_unsettled(self):
        text = prose(SKILL)
        self.assertIn('`autopilot --take-over`', text)
        self.assertIn('reuses accepted decisions, tickets and reports', text)
        self.assertIn('asks only the align questions still unsettled', text)
        self.assertIn('A confirmed card whose goal, criteria and grants are unchanged is not confirmed again', text)
        self.assertIn('a card that ended `waiting-on-user` or `paused-allowance` resumes once its cause is gone', text)
        self.assertIn('moves its terminal state to `history:`, clears `terminal:` and restores the phase it stopped in', text)
        self.assertIn('history:', CARD.read_text().split('## State', 1)[1])

    def test_late_questions_are_decided_reversibly_and_reported_first(self):
        text = prose(SKILL)
        self.assertIn('ends `blocked`', text)
        self.assertIn('split tickets also fail twice', text)
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
