#!/usr/bin/env python3
"""Delivery is a flow that owns the dispatch, housekeeping and PR procedures and the ticket and merge-conflict
jobs: its files each fit one read, it links only the flows the architecture puts below it, and no skill links
another skill."""
import json
import re
import unittest

import support

ROOT = support.ROOT
DELIVERY = ROOT / 'flows/delivery'
LINK = re.compile(r'\]\(([^)\s#]+)(?:#[^)\s]*)?\)')
LIMIT = 12 * 1024
ALLOWED = {'delivery', 'review', 'planning', 'board'}
BELOW = {'runtime', 'standards', 'hosts', 'agents', 'addons'}
MOVED = {
    'flows/delivery/dispatch.md': '# dispatch',
    'flows/delivery/iteration.md': '## One iteration',
    'flows/delivery/handoff.md': '## Review handoff',
    'flows/delivery/split-work.md': 'refinement procedure',
    'flows/delivery/reference.md': '# dispatch — reference',
    'flows/delivery/housekeeping.md': '## Remove disposable residue',
    'flows/delivery/pr.md': '## Repository approval path',
}
OLD = [('skills', 'dispatch', 'reference.md'), ('skills', 'dispatch', 'jobs')]
THIN = {'dispatch': 'dispatch.md', 'housekeeping': 'housekeeping.md', 'pr': 'pr.md'}


def targets(path):
    for target in LINK.findall(path.read_text()):
        if not re.match(r'[a-z]+:', target):
            yield (path.parent / target).resolve().relative_to(ROOT)


class DeliveryFlow(unittest.TestCase):
    def test_each_file_is_in_the_flow_and_the_old_homes_are_gone(self):
        for name, marker in MOVED.items():
            with self.subTest(doc=name):
                self.assertIn(marker, (ROOT / name).read_text())
        for old in OLD:
            self.assertFalse(ROOT.joinpath(*old).exists(), old)

    def test_no_delivery_file_exceeds_one_read(self):
        for path in sorted(DELIVERY.rglob('*.md')):
            with self.subTest(doc=str(path.relative_to(ROOT))):
                self.assertLessEqual(len(path.read_bytes()), LIMIT)

    def test_a_delivery_doc_links_only_its_flow_the_flows_below_it_or_lower_modules(self):
        for path in sorted(DELIVERY.rglob('*.md')):
            for target in targets(path):
                with self.subTest(doc=str(path.relative_to(ROOT)), target=str(target)):
                    top = target.parts[0]
                    self.assertTrue((top == 'flows' and target.parts[1] in ALLOWED) or top in BELOW,
                                    f'delivery may not link {target}')

    def test_the_jobs_load_from_the_flow_and_no_job_remains_under_skills(self):
        import agent_defs
        jobs = agent_defs.load(ROOT)['jobs']
        for name in ('ticket', 'merge-conflict'):
            self.assertEqual(jobs[name]['path'], str(DELIVERY / 'jobs' / f'{name}.md'))
        self.assertEqual(list(ROOT.glob('skills/*/jobs/*.md')), [])
        self.assertEqual(agent_defs.problems(ROOT), [])
        self.assertNotIn('skills/*/jobs', (ROOT / 'scripts/agent_defs.py').read_text().split('def load')[0]
                         .split('def job_files')[1])

    def test_the_builder_packet_names_the_moved_ticket_job(self):
        text = (DELIVERY / 'iteration.md').read_text()
        self.assertIn('job_file: <plugin_root>/flows/delivery/jobs/ticket.md', text)

    def test_the_skills_are_thin_entries_over_the_flow(self):
        for skill, name in THIN.items():
            text = (ROOT / 'skills' / skill / 'SKILL.md').read_text()
            self.assertLess(len(text), 2500, skill)
            self.assertIn(f'](../../flows/delivery/{name})', text)
            self.assertTrue(text.startswith('---\nname: ' + skill + '\n'))

    def test_no_skill_links_another_skill(self):
        for path in sorted((ROOT / 'skills').glob('*/SKILL.md')):
            for target in targets(path):
                with self.subTest(doc=str(path.relative_to(ROOT)), target=str(target)):
                    self.assertNotEqual(target.parts[0], 'skills')

    def test_the_board_does_not_link_the_review_flow_or_carry_the_split_rule(self):
        self.assertNotIn('too large for one worker', (ROOT / 'flows/board/scope.md').read_text())
        for path in (ROOT / 'flows/board').rglob('*.md'):
            for target in targets(path):
                self.assertNotEqual(target.parts[:2], ('flows', 'review'), path)

    def test_the_architecture_has_no_debt_left_for_delivery(self):
        debt = json.loads((ROOT / '.agents/skills/writing-agent-docs/architecture.json').read_text())['debt']
        text = json.dumps(debt)
        for fragment in ('skills/dispatch', 'skills/housekeeping', 'skills/pr/', 'skills/pipeline/SKILL.md -> skills'):
            self.assertNotIn(fragment, text)
        self.assertEqual(debt['links'], [])
        self.assertEqual(debt['cycles'], [])
        self.assertNotIn('skills/dispatch/SKILL.md', debt['first_read'])
        config = json.loads((ROOT / '.agents/skills/writing-agent-docs/config.json').read_text())['debt']
        self.assertNotIn('skills/dispatch/SKILL.md', config)


if __name__ == '__main__':
    unittest.main()
