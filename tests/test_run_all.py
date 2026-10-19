#!/usr/bin/env python3
"""The suite runner runs every regression script, reports each failure's output tail and exits 1 on any failure."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import support

RUNNER = support.ROOT / 'tests/run_all.py'


class RunAll(unittest.TestCase):
    def suite(self, scripts, env=None):
        directory = tempfile.TemporaryDirectory(prefix='run all ')
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        (root / 'tests').mkdir()
        shutil.copy(RUNNER, root / 'tests/run_all.py')
        for name, body in scripts.items():
            (root / 'tests' / name).write_text(body)
        subprocess.run(['git', 'init', '-q', str(root)], check=True)
        # A Git hook exports GIT_DIR; the runner must not pass it to the scripts.
        env = dict(os.environ, PYTHON=sys.executable, GIT_DIR=str(root / '.git'), **(env or {}))
        self.root = root
        return subprocess.run([sys.executable, str(root / 'tests/run_all.py')], env=env,
                              capture_output=True, text=True, timeout=60)

    def test_every_script_passing_exits_zero_and_counts_them(self):
        result = self.suite({'test_one.py': 'pass\n', 'test_two.py': 'pass\n', 'helper.py': 'raise SystemExit(1)\n'})
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(f'2 regression scripts passed ({sys.executable})', result.stdout)

    def test_a_failure_exits_one_and_prints_its_name_and_output_tail(self):
        result = self.suite({'test_good.py': 'pass\n',
                             'test_bad.py': 'print("first line")\nprint("why it broke")\nraise SystemExit(3)\n'})
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn('FAIL test_bad', result.stdout)
        self.assertIn('why it broke', result.stdout)
        self.assertNotIn('FAIL test_good', result.stdout)
        self.assertNotIn('passed', result.stdout)

    def test_without_python_set_a_worktree_uses_the_main_checkout_environment(self):
        main = Path(tempfile.mkdtemp(prefix='run all main '))
        self.addCleanup(shutil.rmtree, main)
        subprocess.run(['git', 'init', '-q', str(main)], check=True)
        subprocess.run(['git', '-C', str(main), '-c', 'user.name=t', '-c', 'user.email=t@t', '-c', 'commit.gpgsign=false',
                        'commit', '-q', '--allow-empty', '-m', 'base'], check=True)
        (main / '.venv/bin').mkdir(parents=True)
        (main / '.venv/bin/python').symlink_to(sys.executable)
        tree = main.parent / f'{main.name} tree'
        subprocess.run(['git', '-C', str(main), 'worktree', 'add', '-q', '--detach', str(tree)], check=True)
        self.addCleanup(shutil.rmtree, tree, True)
        (tree / 'tests').mkdir()
        shutil.copy(RUNNER, tree / 'tests/run_all.py')
        (tree / 'tests/test_one.py').write_text('pass\n')
        env = {key: value for key, value in os.environ.items() if key not in ('PYTHON', 'GIT_DIR')}
        result = subprocess.run([sys.executable, str(tree / 'tests/run_all.py')], env=env, cwd=main.parent,
                                capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(f'1 regression scripts passed ({main.resolve() / ".venv/bin/python"})', result.stdout)

    def test_a_failure_with_undecodable_output_is_still_reported(self):
        result = self.suite({'test_bytes.py': 'import sys\nsys.stdout.buffer.write(b"bad \\xff byte\\n")\nraise SystemExit(1)\n',
                             'test_other.py': 'print("second failure")\nraise SystemExit(1)\n'})
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn('FAIL test_bytes', result.stdout)
        self.assertIn('second failure', result.stdout)

    def test_scripts_do_not_inherit_the_git_hook_environment(self):
        result = self.suite({'test_env.py': 'import os\nraise SystemExit(1 if "GIT_DIR" in os.environ else 0)\n'})
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
