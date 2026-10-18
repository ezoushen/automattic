#!/usr/bin/env python3
"""Review and remediation are flows that own their jobs: review links nothing in remediation or delivery,
its files each fit one read, and the skills that others depended on are thin entries over them."""
import json
import re
import unittest

import support

ROOT = support.ROOT
FLOWS = ROOT / 'flows'
LINK = re.compile(r'\]\(([^)\s#]+)(?:#[^)\s]*)?\)')
LIMIT = 12 * 1024
# the flows a flow doc may link: its own and the ones the architecture puts below it
ALLOWED = {'review': {'review', 'planning', 'board'}, 'remediation': {'remediation', 'review', 'planning', 'board'}}
BELOW = {'runtime', 'standards', 'hosts', 'agents', 'addons'}
MOVED = {
    'flows/review/review.md': '# Shared review procedure',
    'flows/review/coverage.md': '## Review to coverage completion',
    'flows/review/repair.md': '## Optional repair',
    'flows/review/e2e.md': '## Verify autofix through E2E',
    'flows/review/finish.md': '## Publish authorized comments',
    'flows/review/layers.md': None, 'flows/review/method.md': None,
    'flows/review/report.md': None, 'flows/review/comments.md': None,
    'flows/review/guided.md': '## Continue into review when requested',
    'flows/remediation/procedure.md': '## Arguments',
}
JOBS = {'diff-review': ('reviewer', 'flows/review'), 'repair': ('builder', 'flows/review'),
        'reproduce': ('reviewer', 'flows/review'), 'e2e-gate': ('verifier', 'flows/review'),
        'audit': ('reviewer', 'flows/remediation'), 'ticket': ('builder', 'flows/delivery'),
        'merge-conflict': ('builder', 'flows/delivery')}
OLD = [('skills', 'review', 'workflow.md'), ('skills', 'review', 'layers.md'), ('skills', 'review', 'jobs'),
       ('skills', 'remediate', 'jobs')]


def targets(path):
    for target in LINK.findall(path.read_text()):
        if not re.match(r'[a-z]+:', target):
            yield (path.parent / target).resolve().relative_to(ROOT)


class ReviewFlow(unittest.TestCase):
    def test_each_flow_holds_its_files_and_the_old_homes_are_gone(self):
        for name, marker in MOVED.items():
            with self.subTest(doc=name):
                self.assertTrue((ROOT / name).is_file())
                if marker:
                    self.assertIn(marker, (ROOT / name).read_text())
        for old in OLD:
            self.assertFalse(ROOT.joinpath(*old).exists(), old)

    def test_no_flow_file_exceeds_one_read(self):
        for path in sorted(FLOWS.joinpath('review').rglob('*.md')) + sorted(FLOWS.joinpath('remediation').rglob('*.md')):
            with self.subTest(doc=str(path.relative_to(ROOT))):
                self.assertLessEqual(len(path.read_bytes()), LIMIT)

    def test_a_flow_doc_links_only_its_own_flow_or_lower_modules(self):
        for flow in ALLOWED:
            for path in sorted((FLOWS / flow).rglob('*.md')):
                for target in targets(path):
                    with self.subTest(doc=str(path.relative_to(ROOT)), target=str(target)):
                        top = target.parts[0]
                        own = top == 'flows' and target.parts[1] in ALLOWED[flow]
                        self.assertTrue(own or top in BELOW, f'{flow} may not link {target}')

    def test_every_job_loads_from_its_owner_with_its_agent(self):
        import agent_defs
        jobs = agent_defs.load(ROOT)['jobs']
        self.assertEqual(sorted(jobs), sorted(JOBS))
        for name, (agent, owner) in JOBS.items():
            with self.subTest(job=name):
                self.assertEqual(jobs[name]['agent'], agent)
                self.assertEqual(jobs[name]['path'], str(ROOT / owner / 'jobs' / f'{name}.md'))
        self.assertEqual(agent_defs.problems(ROOT), [])

    def test_the_skills_are_thin_entries_over_the_flows(self):
        for skill, flow, name in (('review', 'review', 'review.md'), ('walkthrough', 'review', 'guided.md'),
                                  ('remediate', 'remediation', 'procedure.md')):
            text = (ROOT / 'skills' / skill / 'SKILL.md').read_text()
            self.assertLess(len(text), 2500, skill)
            self.assertIn(f'](../../flows/{flow}/{name})', text)
            self.assertTrue(text.startswith('---\nname: ' + skill + '\n'))

    def test_no_skill_links_the_review_walkthrough_or_remediate_skills_or_the_brief_from_a_flow(self):
        for path in sorted((ROOT / 'skills').rglob('*.md')) + sorted(FLOWS.rglob('*.md')):
            for target in targets(path):
                with self.subTest(doc=str(path.relative_to(ROOT)), target=str(target)):
                    self.assertNotIn(target.parts[:2], [('skills', 'review'), ('skills', 'walkthrough'),
                                                        ('skills', 'remediate')])
                    if path.parts[-3:-1] != ('review', 'jobs') and 'flows' in path.parts:
                        self.assertNotEqual(target.parts[:2], ('skills', 'brief'))

    def test_the_architecture_has_no_debt_left_for_review_and_remediation(self):
        debt = json.loads((ROOT / '.agents/skills/writing-agent-docs/architecture.json').read_text())['debt']
        text = json.dumps(debt)
        for fragment in ('skills/review', 'skills/walkthrough', 'skills/remediate'):
            self.assertNotIn(fragment, text)
        for cycle in debt['cycles']:
            self.assertFalse({'review', 'remediation'} & set(cycle), cycle)


if __name__ == '__main__':
    unittest.main()
