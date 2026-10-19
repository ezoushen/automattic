#!/usr/bin/env python3
"""Each command's procedure lives in the flow named after it, shared flows sit below their users, and the
jobs load from the flow that owns them. Direction, size and naming are the doc checker's rules; this checks
what lives where."""
import re
import unittest

import support

ROOT = support.ROOT
FLOWS = ROOT / 'flows'
LINK = re.compile(r'\]\(([^)\s#]+)(?:#[^)\s]*)?\)')
COMMANDS = ('align', 'refine', 'dispatch', 'review', 'pr', 'remediate', 'setup', 'brief')
# a procedure each merged or moved command must still carry, by the doc that now holds it
HOLDS = {
    'flows/align/align.md': ('## Settle the mandate', '## Establish the design', '## Save the current alignment'),
    'flows/interview/authority.md': ('A decision the user reserved is always theirs.',),
    'flows/interview/question-filter.md': ('**Material fork:** ask only if plausible answers change the goal',),
    'flows/interview/record.md': ('`## Standing directives` section in the ledger',),
    'flows/refine/refine.md': ("Matt Pocock's `/mattpocock-skills:to-tickets` breaks a spec",),
    'flows/refine/ticket-template.md': ('# NN: <title, a behaviour not a component>',),
    'flows/dispatch/dispatch.md': ('# dispatch',),
    'flows/dispatch/iteration.md': ('## One iteration',),
    'flows/dispatch/handoff.md': ('## Review handoff',),
    'flows/housekeeping/housekeeping.md': ('## Remove disposable residue',),
    'flows/pr/pr.md': ('## Repository approval path',),
    'flows/review/review.md': ('# Shared review procedure',),
    'flows/review/walkthrough.md': ('## Continue into review when requested',),
    'flows/remediate/remediate.md': ('## Arguments',),
    'flows/setup/setup.md': ('## Direct changes', 'No arguments means read-only inspection'),
    'flows/setup/tour.md': ('## Explain the actual setup', '## Discuss one useful topic at a time'),
    'flows/brief/brief.md': ('## Brief the human', '## Show the pipeline map'),
    'flows/brief/pipeline.md': ('## The outer loop', '## Failure modes and where the loop catches them'),
    'flows/board/board.md': ('## Local Markdown board',),
}
JOBS = {'diff-review': ('reviewer', 'review'), 'repair': ('builder', 'review'), 'reproduce': ('reviewer', 'review'),
        'e2e-gate': ('verifier', 'review'), 'audit': ('reviewer', 'remediate'), 'ticket': ('builder', 'dispatch'),
        'merge-conflict': ('builder', 'dispatch')}


def targets(path):
    for target in LINK.findall(path.read_text()):
        if not re.match(r'[a-z]+:', target):
            yield (path.parent / target).resolve().relative_to(ROOT)


class Flows(unittest.TestCase):
    def test_every_command_reads_first_the_procedure_in_the_flow_named_after_it(self):
        for command in COMMANDS:
            with self.subTest(command=command):
                text = (ROOT / 'skills' / command / 'SKILL.md').read_text()
                declaration = re.search(r'^First read:.*$', text, re.M).group(0)
                self.assertIn(f'](../../flows/{command}/{command}.md)', declaration)

    def test_each_procedure_is_in_its_new_home(self):
        for name, markers in HOLDS.items():
            text = ' '.join((ROOT / name).read_text().split())
            for marker in markers:
                with self.subTest(doc=name, marker=marker):
                    self.assertIn(marker, text)

    def test_every_job_loads_from_its_owning_flow_with_its_agent(self):
        import agent_defs
        jobs = agent_defs.load(ROOT)['jobs']
        self.assertEqual(sorted(jobs), sorted(JOBS))
        for name, (agent, owner) in JOBS.items():
            with self.subTest(job=name):
                self.assertEqual(jobs[name]['agent'], agent)
                self.assertEqual(jobs[name]['path'], str(FLOWS / owner / 'jobs' / f'{name}.md'))
        self.assertEqual(agent_defs.problems(ROOT), [])

    def test_the_builder_packet_names_the_ticket_job_where_it_lives(self):
        self.assertIn('job_file: <plugin_root>/flows/dispatch/jobs/ticket.md', (FLOWS / 'dispatch/iteration.md').read_text())

    def test_the_board_does_not_link_the_review_flow_or_carry_the_split_rule(self):
        for path in (FLOWS / 'board').rglob('*.md'):
            self.assertNotIn('too large for one worker', path.read_text(), path)
            for target in targets(path):
                self.assertNotEqual(target.parts[:2], ('flows', 'review'), path)

    def test_the_pipeline_map_links_every_flow(self):
        linked = {target.parts[1] for target in targets(FLOWS / 'brief/pipeline.md') if target.parts[0] == 'flows'}
        self.assertEqual(linked, {path.name for path in FLOWS.iterdir() if path.is_dir()})


if __name__ == '__main__':
    unittest.main()
