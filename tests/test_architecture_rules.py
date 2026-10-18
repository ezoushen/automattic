#!/usr/bin/env python3
"""check_docs.py enforces the module architecture: each rule on a small fixture tree."""
import json
import shutil
import subprocess
import sys
import unittest

import support
from test_doc_checker import CHECKER, GUIDE, Fixture, SKILL

ARCHITECTURE = {
    'levels': [['skills'], ['flows'], ['runtime']],
    'modules': {
        'skills': {'docs': ['skills/*/SKILL.md'], 'isolated': True},
        'flows': {'docs': ['flows/**/*.md']},
        'runtime': {'docs': ['shared/**/*.md']},
    },
    'debt': {},
}


class ArchitectureRules(Fixture):
    def setUp(self):
        super().setUp()
        self.architecture = json.loads(json.dumps(ARCHITECTURE))
        self.config['docs'] = ['skills/**/*.md', 'shared/**/*.md', 'flows/**/*.md']
        self.config['linking'] = ['README.md'] + self.config['docs']
        self.config['code_doc_pattern'] = r'(?:shared|skills|flows)/[\w/-]+\.md'

    def messages(self, code):
        return [(f['path'], f['line'], f['message']) for f in self.check_full() if f['code'] == code]

    def test_the_clean_fixture_passes(self):
        self.assertEqual(self.check(), set())

    def test_a_lower_layer_linking_a_higher_one_is_reported_with_both_modules_but_same_module_links_are_not(self):
        self.write('flows/a/one.md', '# One\n\nSee [two](two.md).\n')
        self.write('flows/a/two.md', '# Two\n')
        self.write('skills/tool/SKILL.md', SKILL.format(name='tool', description='Runs the tool.')
                   + 'And [one](../../flows/a/one.md).\n')
        self.assertEqual(self.check(), set())
        self.write('shared/guide.md', '# Guide\n\nUp: [one](../flows/a/one.md).\n')
        self.assertEqual(self.check(), {('shared/guide.md', 3, 'direction', 'error')})
        [(_, _, message)] = self.messages('direction')
        self.assertIn('runtime', message)
        self.assertIn('flows', message)

    def test_a_skill_linking_another_skill_is_reported_and_a_skill_may_link_what_it_owns_below(self):
        self.write('skills/other/SKILL.md', SKILL.format(name='other', description='Runs another tool.')
                   + 'Also [tool](../tool/SKILL.md).\n')
        self.assertEqual(self.check(), {('skills/other/SKILL.md', 9, 'direction', 'error')})
        [(_, _, message)] = self.messages('direction')
        self.assertIn('skills/other/SKILL.md', message)
        self.assertIn('skills/tool/SKILL.md', message)

    def test_modules_in_the_same_level_are_siblings_and_may_not_link_each_other(self):
        self.architecture['levels'] = [['skills'], ['flows', 'peer'], ['runtime']]
        self.architecture['modules']['peer'] = {'docs': ['peer/**/*.md']}
        self.config['docs'] += ['peer/**/*.md']
        self.config['linking'] += ['peer/**/*.md']
        self.write('peer/p.md', '# Peer\n')
        self.write('flows/a/one.md', '# One\n\nSee [peer](../../peer/p.md).\n')
        self.write('skills/tool/SKILL.md', SKILL.format(name='tool', description='Runs the tool.')
                   + '[one](../../flows/a/one.md) [peer](../../peer/p.md)\n')
        self.assertEqual(self.check(), {('flows/a/one.md', 3, 'direction', 'error')})
        [(_, _, message)] = self.messages('direction')
        self.assertIn('sibling', message)

    def test_a_module_injected_by_path_may_not_be_linked(self):
        self.first_read_tree()
        self.write('flows/a/one.md', '# One\n\nSee [host](../../hosts/small/session.md).\n')
        self.write('skills/tool/SKILL.md', SKILL.format(name='tool', description='Runs the tool.')
                   + '[one](../../flows/a/one.md)\n')
        self.assertIn(('flows/a/one.md', 3, 'direction', 'error'), self.check())
        [(_, _, message)] = self.messages('direction')
        self.assertIn('never linked', message)

    def test_two_modules_linking_each_other_form_a_cycle_naming_both(self):
        self.write('flows/a/one.md', '# One\n\nDown: [guide](../../shared/guide.md).\n')
        self.write('shared/guide.md', '# Guide\n\nUp: [one](../flows/a/one.md).\n')
        self.write('skills/tool/SKILL.md', SKILL.format(name='tool', description='Runs the tool.')
                   + 'And [one](../../flows/a/one.md).\n')
        found = {(f['code'], f['severity']) for f in self.check_full()}
        self.assertEqual(found, {('direction', 'error'), ('cycle', 'error')})
        [(_, _, message)] = self.messages('cycle')
        self.assertIn('flows', message)
        self.assertIn('runtime', message)

    def test_recorded_debt_is_tolerated_and_stale_debt_is_flagged(self):
        self.write('shared/guide.md', '# Guide\n\nUp: [one](../flows/a/one.md).\n')
        self.write('flows/a/one.md', '# One\n\nDown: [guide](../../shared/guide.md).\n')
        self.write('skills/tool/SKILL.md', SKILL.format(name='tool', description='Runs the tool.')
                   + 'And [one](../../flows/a/one.md).\n')
        self.architecture['debt'] = {'links': ['shared/guide.md -> flows/a/one.md'], 'cycles': [['flows', 'runtime']]}
        self.assertEqual(self.check(), set())
        self.architecture['debt'] = {'links': ['shared/guide.md -> flows/a/one.md', 'skills/tool/SKILL.md -> shared/guide.md'],
                                     'cycles': [['flows', 'runtime', 'skills']]}
        self.assertEqual(self.check(), {('skills/tool/SKILL.md', 1, 'stale-debt', 'warning'),
                                        ('flows/a/one.md', 3, 'debt', 'warning')})
        self.write('shared/guide.md', GUIDE)
        self.assertEqual(self.check(), {('shared/guide.md', 1, 'stale-debt', 'warning'),
                                        ('skills/tool/SKILL.md', 1, 'stale-debt', 'warning'),
                                        ('architecture.json', 1, 'stale-debt', 'warning')})

    def test_a_doc_no_module_owns_is_an_error(self):
        self.write('shared/guide.md', GUIDE)
        self.config['docs'] = self.config['docs'] + ['extra/*.md']
        self.write('extra/loose.md', '# Loose\n')
        self.write('README.md', '# Project\n\nSee [tool](skills/tool/SKILL.md) and [loose](extra/loose.md).\n')
        self.assertEqual(self.check(), {('extra/loose.md', 1, 'unmapped', 'error')})

    def first_read_tree(self):
        self.architecture['levels'] = [['skills'], ['bootstrap'], ['flows'], ['runtime'], ['hosts']]
        self.architecture['modules']['bootstrap'] = {'docs': ['bootstrap.md']}
        self.architecture['modules']['hosts'] = {'docs': ['hosts/**/*.md'], 'unlinked': True}
        self.architecture['first_read'] = {'budget': 100000, 'bootstrap': ['bootstrap.md'],
                                           'host_session': ['hosts/*/session.md'], 'skills': ['skills/*/SKILL.md']}
        self.config['max_bytes'] = 10000
        self.config['docs'] += ['bootstrap.md', 'hosts/**/*.md']
        self.config['entry_points'] += ['bootstrap.md', 'hosts/*/session.md']
        self.config['code_doc_pattern'] = r'(?:shared|skills|flows|hosts)/[\w/-]+\.md'
        bootstrap, small, large = '# Bootstrap\n' + 'b' * 300 + '\n', '# S\n' + 'h' * 200 + '\n', '# L\n' + 'h' * 500 + '\n'
        skill = SKILL.format(name='tool', description='Runs the tool.') + '\n## Later\n\nSee [flow](../../flows/a/late.md).\n'
        skill = skill.replace('Read [the guide](../../shared/guide.md).', 'First [bootstrap](../../bootstrap.md), then [the guide](../../shared/guide.md).')
        self.write('bootstrap.md', bootstrap)
        self.write('hosts/small/session.md', small)
        self.write('hosts/large/session.md', large)
        self.write('flows/a/late.md', '# Late\n' + 'x' * 5000 + '\n')
        self.write('skills/tool/SKILL.md', skill)
        encoded = lambda text: len(text.encode())
        # Bootstrap, the larger host session, the skill and its opening link; the link after "## Later" is not read first.
        return encoded(bootstrap) + encoded(large) + encoded(skill) + encoded(GUIDE)

    def test_a_skill_whose_first_reads_exceed_the_budget_is_reported_with_its_total_bytes(self):
        total = self.first_read_tree()
        self.architecture['first_read']['budget'] = total
        self.assertEqual(self.check(), set())
        self.architecture['first_read']['budget'] = total - 1
        self.assertEqual(self.check(), {('skills/tool/SKILL.md', 1, 'first-read', 'error')})
        [(_, _, message)] = self.messages('first-read')
        self.assertIn(str(total), message)
        self.architecture['debt'] = {'first_read': {'skills/tool/SKILL.md': total}}
        self.assertEqual(self.check(), set())
        self.architecture['debt'] = {'first_read': {'skills/tool/SKILL.md': total - 1}}
        self.assertEqual(self.check(), {('skills/tool/SKILL.md', 1, 'first-read', 'error')})
        self.architecture['debt'] = {'first_read': {'skills/tool/SKILL.md': total + 7}}
        self.assertEqual(self.check(), {('skills/tool/SKILL.md', 1, 'debt', 'warning')})
        self.architecture['first_read']['budget'] = total + 1
        self.assertEqual(self.check(), {('skills/tool/SKILL.md', 1, 'stale-debt', 'warning')})

    def host_tree(self, **extra):
        self.first_read_tree()
        self.architecture['host_shape'] = {'root': 'hosts', 'files': ['session.md', 'workers.md'], 'exempt': ['tools']}
        for name in ('session.md', 'workers.md'):
            self.write(f'hosts/pair/{name}', '# Part\n')
        self.write('hosts/tools/bash.md', '# Tool\n')
        self.write('hosts/small/workers.md', '# Workers\n')
        for path, text in extra.items():
            self.write(path, text)
        self.write('README.md', '# Project\n\nSee [tool](skills/tool/SKILL.md).\n')

    def host_findings(self):
        return {(f['path'], f['code'], f['severity']) for f in self.check_full() if f['code'] == 'host-shape'}

    def test_a_host_folder_holds_exactly_a_session_part_and_a_worker_part(self):
        self.host_tree()
        self.write('hosts/large/workers.md', '# Workers\n')
        self.assertEqual(self.host_findings(), set())
        self.write('hosts/pair/extra.md', '# Extra\n')
        self.assertEqual(self.host_findings(), {('hosts/pair', 'host-shape', 'error')})
        (self.root / 'hosts/pair/extra.md').unlink()
        (self.root / 'hosts/pair/workers.md').unlink()
        self.assertEqual(self.host_findings(), {('hosts/pair', 'host-shape', 'error')})

    def test_a_section_linked_from_three_files_in_other_modules_should_be_its_own_file(self):
        self.write('shared/guide.md', '# Guide\n\n## Steps\n\nRun.\n')
        for name in ('a', 'b', 'c'):
            self.write(f'flows/{name}/f.md', f'# F\n\nSee [steps](../../shared/guide.md#steps).\n')
        self.write('skills/tool/SKILL.md', SKILL.format(name='tool', description='Runs the tool.')
                   + ''.join(f'[{n}](../../flows/{n}/f.md) ' for n in 'abc') + '\n')
        self.assertEqual(self.check(), {('shared/guide.md', 1, 'shared-section', 'warning')})
        self.write('flows/c/f.md', '# F\n\nSee [guide](../../shared/guide.md).\n')
        self.assertEqual(self.check(), set())
        self.write('shared/other.md', '# Other\n\nSee [steps](guide.md#steps).\n')
        self.write('flows/c/f.md', '# F\n\nSee [guide](../../shared/guide.md) and [other](../../shared/other.md).\n')
        self.assertEqual(self.check(), set())

    def test_skills_count_as_other_modules_to_each_other_for_shared_sections(self):
        self.write('skills/tool/SKILL.md', SKILL.format(name='tool', description='Runs the tool.') + '\n## Filter\n\nAsk less.\n')
        for name in ('a', 'b', 'c'):
            self.write(f'skills/{name}/SKILL.md', SKILL.format(name=name, description='Runs a tool.')
                       + 'See [filter](../tool/SKILL.md#filter).\n')
        self.architecture['debt'] = {'links': [f'skills/{n}/SKILL.md -> skills/tool/SKILL.md' for n in 'abc']}
        self.assertEqual(self.check(), {('skills/tool/SKILL.md', 1, 'shared-section', 'warning')})


TARGET_DOCS = {  # doc under a target folder: is it an entry point (exempt from the orphan rule)?
    'bootstrap.md': True,
    'flows/delivery/procedure.md': False,
    'flows/delivery/jobs/job.md': True,
    'standards/style.md': False,
    'runtime/workers/launch.md': False,
    'hosts/claude/session.md': True,
    'hosts/claude/workers.md': False,
    'hosts/herdr.md': False,
    'hosts/executors/bash.md': False,
}


class TargetFolders(Fixture):
    """The repository's own config applies size, link, orphan and code-path rules to every target folder."""

    def run_repository_config(self):
        result = subprocess.run([sys.executable, str(CHECKER), '--root', str(self.root), '--json'],
                                capture_output=True, text=True)
        assert result.returncode in (0, 1), result.stderr
        return {f['code'] for f in json.loads(result.stdout) if f['path'] == self.doc or f['path'] == 'scripts/run.py'}

    def test_each_target_folder_gets_the_size_link_orphan_and_code_path_rules(self):
        for doc, entry in TARGET_DOCS.items():
            with self.subTest(doc=doc):
                self.doc = doc
                (self.root / 'scripts').mkdir(exist_ok=True)
                for name in self.root.iterdir():
                    if name.name != 'scripts':
                        shutil.rmtree(name) if name.is_dir() else name.unlink()
                self.write(doc, '# Doc\n\nSee [gone](gone.md).\n\n' + 'x' * 13000 + '\n')
                sibling = doc.rsplit('/', 1)[0] + '/missing.md' if '/' in doc else None
                self.write('scripts/run.py', f"MISSING = '{sibling}'\n" if sibling else "OK = 1\n")
                expected = {'size', 'link'} | (set() if entry else {'orphan'}) | ({'code-path'} if sibling else set())
                self.assertEqual(self.run_repository_config() & {'size', 'link', 'orphan', 'code-path', 'unmapped'}, expected)

    def test_a_missing_bootstrap_named_in_code_is_a_code_path_error(self):
        self.write('scripts/run.py', "BOOT = 'bootstrap.md'\n")
        self.doc = 'bootstrap.md'
        self.assertEqual(self.run_repository_config(), {'code-path'})


# The harness-to-skill links measured on 2026-10-19 that break the layers (grep of `](../skills/` from
# harnesses/); the other links from harnesses/ to skills/ go from the bootstrap down to flows or standards.
RUNTIME_TO_SKILL_DEBT = [
    'harnesses/checks/run.md -> skills/housekeeping/SKILL.md',
    'harnesses/decisions/journal.md -> skills/decision/SKILL.md',
    'harnesses/decisions/phases.md -> skills/decision/SKILL.md',
    'harnesses/routing/decision-model.md -> skills/decision/SKILL.md',
    'harnesses/setup/apply.md -> skills/decision/SKILL.md',
    'harnesses/setup/executors.md -> skills/setup-automattic/SKILL.md',
    'harnesses/setup/routers.md -> skills/model-routing/SKILL.md',
]


class RepositoryDebt(unittest.TestCase):
    def test_the_upward_links_from_harnesses_to_skills_are_recorded_as_debt(self):
        debt = json.loads((support.ROOT / '.agents/skills/writing-agent-docs/architecture.json').read_text())['debt']
        self.assertEqual(set(RUNTIME_TO_SKILL_DEBT) - set(debt['links']), set())
        self.assertEqual({link for link in debt['links'] if link.startswith('harnesses/') and ' -> skills/' in link},
                         set(RUNTIME_TO_SKILL_DEBT))


if __name__ == "__main__":
    unittest.main()
