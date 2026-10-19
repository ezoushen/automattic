#!/usr/bin/env python3
"""Dispatch runs each ticket inline or delegated, and both follow one ticket contract."""
import subprocess
import unittest

import support

ROOT = support.ROOT
DISPATCH = ROOT / 'skills/dispatch'
MODES = DISPATCH / 'modes.md'


def prose(path):
    return ' '.join(path.read_text().split())


class TicketModes(unittest.TestCase):
    def test_the_orchestrator_chooses_how_each_ticket_runs_and_records_why(self):
        text = prose(MODES)
        for rule in ('**Inline:** the orchestrator implements the ticket itself in the effort worktree, on the effort branch',
                     '**Delegated:** a builder implements it in its own worktree and branch',
                     'Default to inline for sequential, well-understood tickets whose context the session already holds',
                     'Delegate tickets that can run in parallel, need a clean context, carry high risk or would crowd',
                     "The user's instruction on how a ticket runs wins",
                     'Record the mode and its reason in the run report'):
            self.assertIn(rule, text)
        self.assertIn('[how a ticket runs](modes.md)', prose(DISPATCH / 'iteration.md'))

    def test_an_inline_ticket_keeps_the_ticket_contract_and_its_report_names_the_branch(self):
        text = prose(MODES)
        for kept in ('follows the [ticket job](jobs/ticket.md) itself', '`branch: <effort branch>`',
                     '`worker=inline`', 'the integrated review is its independent check'):
            self.assertIn(kept, text)
        job = prose(DISPATCH / 'jobs/ticket.md')
        self.assertIn('For an inline ticket the orchestrator follows this job itself', job)
        self.assertIn('the branch the report records', prose(ROOT / 'runtime/board/board.md'))

    def test_the_builder_agent_is_unchanged(self):
        diff = subprocess.run(['git', '-C', str(ROOT), 'diff', '--quiet', 'main', '--', 'agents/builder.md'])
        self.assertEqual(diff.returncode, 0)

    def test_an_effort_gets_its_own_branch_unless_the_user_says_main(self):
        text = prose(MODES)
        for rule in ('Every effort gets a dedicated branch by default',
                     'Only an explicit user instruction to work directly on main makes `main` the effort branch',
                     'record that instruction and the starting commit in the run report',
                     'delegated tickets merge into `main` under that instruction', 'Never push'):
            self.assertIn(rule, text)
        self.assertIn('[directly on main](modes.md#directly-on-main)', prose(DISPATCH / 'iteration.md'))

    def test_an_effort_on_main_is_reviewed_from_its_starting_commit_and_has_no_pr(self):
        self.assertIn('review covers the starting commit to the current `main`', prose(MODES))
        self.assertIn('`effort_branch: main`', prose(MODES))
        self.assertIn('`effort_branch: main`', prose(ROOT / 'skills/review/report.md'))
        self.assertIn('An effort the user ran directly on `main` has no branch to publish', prose(ROOT / 'skills/pr/SKILL.md'))

    def test_the_map_and_readme_name_both_modes(self):
        self.assertIn('inline by the orchestrator or by a fresh builder in its own worktree',
                      prose(ROOT / 'skills/brief/pipeline.md'))
        self.assertIn('inline or in builder worktrees', prose(ROOT / 'README.md'))


if __name__ == '__main__':
    unittest.main()
