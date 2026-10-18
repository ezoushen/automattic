#!/usr/bin/env python3
"""Board, planning and setup are flows: planning links only board and lower, board links nothing in planning,
and the skills that others depended on are thin entries over them."""
import json
import re
import unittest

import support

ROOT = support.ROOT
FLOWS = ROOT / 'flows'
LINK = re.compile(r'\]\(([^)\s#]+)(?:#[^)\s]*)?\)')
ARCHITECTURE = json.loads((ROOT / '.agents/skills/writing-agent-docs/architecture.json').read_text())
# the flows a flow doc may link: its own and the ones the architecture puts below it
ALLOWED = {'planning': {'planning', 'board'}, 'board': {'board'}, 'setup': {'setup'}}
BELOW = {'planning': {'board', 'runtime', 'standards', 'hosts', 'agents', 'addons'},
         'board': {'runtime', 'standards', 'hosts', 'agents', 'addons'},
         'setup': {'runtime', 'standards', 'hosts', 'agents', 'addons'}}
MOVED = {
    'flows/planning/authority.md': 'A decision the user reserved is always theirs.',
    'flows/planning/question-filter.md': '**Material fork:** ask only if plausible answers change the goal',
    'flows/planning/record.md': '`## Standing directives` section in the ledger',
    'flows/planning/refinement.md': 'Matt Pocock\'s `/mattpocock-skills:to-tickets` breaks a spec',
    'flows/planning/ticket-template.md': '# NN: <title, a behaviour not a component>',
    'flows/board/board.md': '## Local Markdown board',
    'flows/board/scope.md': 'Record the initiating request, selection boundary, exclusions',
    'flows/board/project-loop.md': '# Project execution facts',
    'flows/board/conventions.md': '# Tracker and project conventions',
    'flows/board/approval-path.md': 'An author cannot satisfy their own independent-review',
    'flows/setup/procedure.md': None,
    'flows/setup/apply.md': None,
    'flows/setup/reset-and-validate.md': None,
    'flows/setup/troubleshooting.md': None,
    'flows/setup/legacy-preferences.md': None,
    'flows/setup/models-skill.md': None,
    'flows/setup/README.md': None,
}
# built from parts: the doc checker flags a literal path to a doc that no longer exists
OLD = [('skills', 'dispatch', 'board.md'), ('skills', 'dispatch', 'project-loop.md'),
       ('skills', 'dispatch', 'conventions.md'), ('skills', 'refine', 'workflow.md'), ('harnesses', 'setup')]


def targets(path):
    for target in LINK.findall(path.read_text()):
        if not re.match(r'[a-z]+:', target):
            yield (path.parent / target).resolve().relative_to(ROOT)


class Flows(unittest.TestCase):
    def test_each_flow_holds_its_files_and_the_old_homes_are_gone(self):
        for name, marker in MOVED.items():
            with self.subTest(doc=name):
                self.assertTrue((ROOT / name).is_file())
                if marker:
                    self.assertIn(marker, (ROOT / name).read_text())
        for old in OLD:
            self.assertFalse(ROOT.joinpath(*old).exists(), old)

    def test_a_flow_doc_links_only_its_own_flow_or_lower_modules(self):
        for path in sorted(FLOWS.rglob('*.md')):
            flow = path.relative_to(FLOWS).parts[0]
            if flow not in ALLOWED:
                continue  # review and remediation are checked in test_flows_review_remediation.py
            for target in targets(path):
                with self.subTest(doc=str(path.relative_to(ROOT)), target=str(target)):
                    top = target.parts[0]
                    own = top == 'flows' and target.parts[1] in ALLOWED[flow]
                    self.assertTrue(own or top in BELOW[flow], f'{flow} may not link {target}')

    def test_the_skills_that_others_depended_on_are_thin_entries(self):
        for skill, links in (('mandate', ['authority.md', 'question-filter.md', 'record.md']),
                             ('refine', ['refinement.md']), ('models', ['procedure.md'])):
            text = (ROOT / 'skills' / skill / 'SKILL.md').read_text()
            self.assertLess(len(text), 3500, skill)
            for name in links:
                self.assertRegex(text, rf'\]\(\.\./\.\./flows/(planning|setup)/{name}')

    def test_no_skill_links_the_mandate_or_refine_skills(self):
        for path in sorted((ROOT / 'skills').rglob('*.md')):
            for target in targets(path):
                with self.subTest(doc=str(path.relative_to(ROOT)), target=str(target)):
                    self.assertNotIn(target.parts[:2], [('skills', 'mandate'), ('skills', 'refine')])

    def test_these_flows_record_no_debt(self):
        debt = ARCHITECTURE['debt']
        moved = ('board.md', 'project-loop.md', 'conventions.md')
        mine = ('flows/', 'skills/mandate/', 'skills/refine/', 'skills/models/') + tuple(f'skills/dispatch/{n}' for n in moved)
        for link in debt['links']:
            source, target = link.split(' -> ')
            self.assertFalse(source.startswith(mine) or target.startswith(mine), link)
        self.assertNotIn('skills/align/SKILL.md', debt['first_read'])
        config = json.loads((ROOT / '.agents/skills/writing-agent-docs/config.json').read_text())['debt']
        self.assertEqual([name for name in config if name.startswith(('skills/refine', 'skills/mandate', 'flows/'))
                          or name in [f'skills/dispatch/{n}' for n in moved]], [])

    def test_the_bootstrap_triggers_link_the_planning_and_board_flows(self):
        text = (ROOT / 'bootstrap.md').read_text()
        for target in ('flows/planning/question-filter.md', 'flows/planning/refinement.md',
                       'flows/planning/record.md', 'flows/board/conventions.md', 'flows/board/board.md'):
            self.assertIn(f']({target}', text)


if __name__ == '__main__':
    unittest.main()
