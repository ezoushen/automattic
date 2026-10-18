#!/usr/bin/env python3
"""check_fold.py proves a restructuring kept every body line and the feature surface."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import support

TOOL = support.ROOT / '.agents/skills/writing-agent-docs/check_fold.py'
CONFIG = {'docs': ['skills/**/*.md', 'agents/*.md', 'standards/**/*.md'], 'architecture': 'architecture.json'}
ARCHITECTURE = {
    'levels': [['all']], 'modules': {'all': {}},
    'fold': {
        'skills': ['skills/*/SKILL.md'],
        'agents': ['agents/*.md'],
        'jobs': ['skills/*/jobs/*.md', 'flows/*/jobs/*.md'],
        'kinds': ['skills/kinds/*.md', 'standards/kinds/*.md'],
        'hooks': ['hooks/hooks.json'],
        'commands': ['scripts/*.py'],
        'decision_families': 'schemas/decision.schema.json',
    },
}
SKILL = '---\nname: tool\ndescription: Runs the tool.\n---\n\n# Tool\n\nFirst rule.\n\nSecond rule, see [the job](jobs/ticket.md).\n'
SCRIPT = ("import argparse\n\nparser = argparse.ArgumentParser()\nsub = parser.add_subparsers()\n"
          "sub.add_parser('route')\nparser.add_argument('--repo')\n")


class FoldCheck(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix='fold check ')
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name) / 'repo'
        self.root.mkdir()
        self.config = Path(directory.name) / 'config.json'
        self.config.write_text(json.dumps(CONFIG))
        (Path(directory.name) / 'architecture.json').write_text(json.dumps(ARCHITECTURE))
        self.write('skills/tool/SKILL.md', SKILL)
        self.write('skills/tool/jobs/ticket.md', '---\nname: ticket\nagent: builder\ninputs: ["ticket"]\nreturns: ["## Implemented"]\n---\n\n# ticket\n\nBuild it.\n')
        self.write('skills/kinds/comments.md', '# Comments\n\nKeep them true.\n')
        self.write('agents/builder.md', '---\nname: builder\n---\n\n# builder\n\nBuild.\n')
        self.write('scripts/run.py', SCRIPT)
        self.write('hooks/hooks.json', json.dumps({'hooks': {'SessionStart': [], 'Stop': []}}))
        self.write('schemas/decision.schema.json', json.dumps({'properties': {'family': {'enum': ['mandate', 'recovery']}}}))
        self.git('init', '-q')
        self.git('add', '-A')
        self.git('-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-qm', 'base')

    def git(self, *args):
        subprocess.run(['git', '-C', str(self.root), *args], check=True, capture_output=True)

    def write(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def fold(self, *args, base='HEAD'):
        result = subprocess.run([sys.executable, str(TOOL), '--root', str(self.root), '--config', str(self.config),
                                 '--base', base, '--json', *args], capture_output=True, text=True)
        assert result.returncode in (0, 1), result.stderr
        report = json.loads(result.stdout)
        assert result.returncode == int(bool(report)), (result.returncode, report)
        return report

    def differences(self, *args):
        return {(d['kind'], d['text']) for d in self.fold(*args)}

    def test_an_unchanged_tree_and_moved_lines_with_rewritten_links_report_nothing(self):
        self.assertEqual(self.differences(), set())
        (self.root / 'skills/tool/jobs/ticket.md').rename(self.root / 'skills/tool/jobs/build.md')
        self.write('skills/tool/SKILL.md', SKILL.replace('jobs/ticket.md', 'jobs/build.md')
                   .replace('First rule.\n\n', 'First rule.\n\nSee [moved](moved.md).\n\n'))
        self.write('skilmoved.md', '# Moved\n\nNew home.\n')
        self.assertEqual(self.differences(), set())

    def test_a_dropped_body_line_is_reported_and_an_edit_listed_as_deliberate_is_accepted(self):
        self.write('skills/tool/SKILL.md', SKILL.replace('First rule.\n\n', ''))
        self.assertEqual(self.differences(), {('line', 'First rule.')})
        allow = self.root.parent / 'allow.json'
        allow.write_text(json.dumps({'lines': ['First rule.']}))
        self.assertEqual(self.differences('--allow', str(allow)), set())

    def test_a_duplicate_line_dropped_in_one_place_is_still_missing(self):
        self.write('skills/kinds/comments.md', '# Comments\n\nKeep them true.\n\nKeep them true.\n')
        self.git('add', '-A')
        self.git('-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-qm', 'two')
        self.write('skills/kinds/comments.md', '# Comments\n\nKeep them true.\n')
        self.assertEqual(self.differences(), {('line', 'Keep them true.')})

    def test_a_changed_link_label_is_a_changed_line(self):
        self.write('skills/tool/SKILL.md', SKILL.replace('the job', 'a job'))
        self.assertEqual(self.differences(), {('line', 'Second rule, see [the job]().')})

    def test_each_feature_surface_difference_is_reported(self):
        self.write('skills/tool/SKILL.md', SKILL.replace('name: tool', 'name: tool2'))
        self.write('agents/builder.md', '---\nname: builder2\n---\n\n# builder\n\nBuild.\n')
        self.write('skills/tool/jobs/ticket.md', '---\nname: ticket\nagent: reviewer\ninputs: ["ticket"]\nreturns: ["## Implemented"]\n---\n\n# ticket\n\nBuild it.\n')
        self.write('skills/kinds/extra.md', '# Extra\n\nA new kind.\n')
        self.write('hooks/hooks.json', json.dumps({'hooks': {'SessionStart': []}}))
        self.write('schemas/decision.schema.json', json.dumps({'properties': {'family': {'enum': ['mandate', 'recovery', 'delivery']}}}))
        self.write('scripts/run.py', SCRIPT.replace("sub.add_parser('route')", "sub.add_parser('save')"))
        found = self.differences()
        self.assertEqual({kind for kind, _ in found} - {'line'}, {'skill', 'agent', 'job', 'kind', 'hook-event', 'decision-family', 'command'})
        self.assertIn(('skill', 'removed tool'), found)
        self.assertIn(('skill', 'added tool2'), found)
        self.assertIn(('kind', 'added extra'), found)
        self.assertIn(('hook-event', 'removed hooks/Stop'), found)
        self.assertIn(('decision-family', 'added delivery'), found)
        self.assertIn(('command', 'removed run sub:route'), found)
        self.assertIn(('command', 'added run sub:save'), found)
        self.assertTrue(any(kind == 'job' and text.startswith('removed ticket') for kind, text in found), found)

    def test_a_removed_flag_alias_or_positional_choice_is_a_command_difference(self):
        self.write('scripts/run.py', SCRIPT + "parser.add_argument('--thinking', '--effort')\n"
                   "parser.add_argument('action', choices=('record', 'retire'))\n")
        self.git('add', '-A')
        self.git('-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-qm', 'flags')
        self.assertEqual(self.differences(), set())
        self.write('scripts/run.py', SCRIPT + "parser.add_argument('--thinking')\n"
                   "parser.add_argument('action', choices=('record',))\n")
        self.assertEqual(self.differences(), {('command', 'removed run option:--effort'),
                                              ('command', 'removed run choice:action=retire')})

    def test_surface_differences_listed_as_deliberate_are_accepted_and_moved_files_keep_their_surface(self):
        (self.root / 'skills/kinds/comments.md').rename(self.root / 'skills/kinds/comments2.md')
        allow = self.root.parent / 'allow.json'
        allow.write_text(json.dumps({'surface': ['removed kind comments', 'added kind comments2']}))
        self.assertEqual(self.differences(), {('kind', 'removed comments'), ('kind', 'added comments2')})
        self.assertEqual(self.differences('--allow', str(allow)), set())
        # A job moved to another flow folder is the same job.
        (self.root / 'flows/delivery/jobs').mkdir(parents=True)
        (self.root / 'skills/tool/jobs/ticket.md').rename(self.root / 'flows/delivery/jobs/ticket.md')
        self.assertEqual({kind for kind, _ in self.differences('--allow', str(allow))}, {'line'})

    def test_a_bad_base_is_invalid_input(self):
        result = subprocess.run([sys.executable, str(TOOL), '--root', str(self.root), '--config', str(self.config),
                                 '--base', 'no-such-base'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn('no-such-base', result.stderr)


if __name__ == '__main__':
    unittest.main()
