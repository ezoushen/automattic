#!/usr/bin/env python3
"""The edit hook reports the architecture rules an edit breaks, so the agent fixes them before going on."""
import json
from pathlib import Path
import subprocess
import sys
import unittest

import support
from test_architecture_rules import ARCHITECTURE
from test_doc_checker import SKILL, Fixture

HOOK = support.ROOT / '.agents/skills/writing-agent-docs/edit_check.py'


class EditCheck(Fixture):
    def setUp(self):
        super().setUp()
        self.architecture = json.loads(json.dumps(ARCHITECTURE))
        self.config['docs'] = ['skills/**/*.md', 'shared/**/*.md', 'flows/**/*.md']
        self.config['linking'] = ['README.md'] + self.config['docs']
        self.config['code_doc_pattern'] = r'(?:shared|skills|flows)/[\w/-]+\.md'

    def run_hook(self, edited, tool='Edit'):
        self.check_full()  # writes the fixture's checker and architecture files
        config = Path(self.config_dir.name) / 'checker.json'
        event = {'tool_name': tool, 'tool_input': {'file_path': str(edited)}}
        return subprocess.run([sys.executable, str(HOOK), '--root', str(self.root), '--config', str(config)],
                              input=json.dumps(event), capture_output=True, text=True)

    def test_an_edit_that_breaks_no_architecture_rule_is_silent(self):
        result = self.run_hook(self.root / 'shared/guide.md')
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, '', ''))

    def test_an_edit_linking_a_higher_module_is_reported_back_to_the_agent(self):
        self.write('flows/a/one.md', '# One\n')
        self.write('skills/tool/SKILL.md', SKILL.format(name='tool', description='Runs the tool.')
                   + '[one](../../flows/a/one.md)\n')
        self.write('shared/guide.md', '# Guide\n\n## Steps\n\nUp: [one](../flows/a/one.md).\n')
        result = self.run_hook(self.root / 'shared/guide.md')
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn('shared/guide.md:5 direction', result.stderr)
        self.assertIn('writing-agent-docs', result.stderr)

    def test_other_findings_such_as_a_long_doc_are_left_to_the_commit_check(self):
        self.write('shared/guide.md', '# Guide\n\n## Steps\n\n' + 'x' * 3000 + '\n')
        result = self.run_hook(self.root / 'shared/guide.md')
        self.assertEqual((result.returncode, result.stderr), (0, ''))

    def test_an_edit_outside_the_repository_is_ignored(self):
        self.write('shared/guide.md', '# Guide\n\nUp: [one](../flows/a/one.md).\n')
        self.write('flows/a/one.md', '# One\n')
        result = self.run_hook(Path('/elsewhere/notes.md'))
        self.assertEqual((result.returncode, result.stderr), (0, ''))

    def test_an_edit_in_a_worktree_inside_the_repository_checks_that_worktree(self):
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True)
        tree = self.root / '.worktrees/w'
        for name in ('README.md', 'skills/tool/SKILL.md', 'shared/guide.md', 'scripts/run.py'):
            (tree / name).parent.mkdir(parents=True, exist_ok=True)
            (tree / name).write_text((self.root / name).read_text())
        subprocess.run(['git', 'init', '-q', str(tree)], check=True)
        (tree / 'flows/a').mkdir(parents=True)
        (tree / 'flows/a/one.md').write_text('# One\n')
        (tree / 'skills/tool/SKILL.md').write_text(SKILL.format(name='tool', description='Runs the tool.')
                                                  + '[one](../../flows/a/one.md)\n')
        (tree / 'shared/guide.md').write_text('# Guide\n\n## Steps\n\nUp: [one](../flows/a/one.md).\n')
        result = self.run_hook(tree / 'shared/guide.md')
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn('shared/guide.md:5 direction', result.stderr)

    def test_an_event_without_json_is_ignored(self):
        self.check_full()
        config = Path(self.config_dir.name) / 'checker.json'
        result = subprocess.run([sys.executable, str(HOOK), '--root', str(self.root), '--config', str(config)],
                                input='', capture_output=True, text=True)
        self.assertEqual((result.returncode, result.stderr), (0, ''))

    def test_the_repository_registers_the_hook_for_claude_edits(self):
        settings = json.loads((support.ROOT / '.claude/settings.json').read_text())
        [entry] = settings['hooks']['PostToolUse']
        self.assertEqual(set(entry['matcher'].split('|')), {'Edit', 'Write', 'MultiEdit'})
        [hook] = entry['hooks']
        import shlex
        self.assertEqual(shlex.split(hook['command']),
                         ['python3', '$CLAUDE_PROJECT_DIR/.agents/skills/writing-agent-docs/edit_check.py',
                          '--root', '$CLAUDE_PROJECT_DIR'])


if __name__ == '__main__':
    unittest.main()
