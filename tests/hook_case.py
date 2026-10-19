#!/usr/bin/env python3
"""A temporary repository with the shipped git hooks, a stub suite and a bare remote."""
import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time
import unittest

import support
from test_doc_checker import CHECKER, CONFIG, GUIDE, SKILL, git

IDENTITY = ['-c', 'user.name=t', '-c', 'user.email=t@t', '-c', 'commit.gpgsign=false']


class HookRepo(unittest.TestCase):
    """Real commits and pushes through the shipped hooks; the stub suite records where it ran."""

    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix='git hooks ')
        self.addCleanup(directory.cleanup)
        self.base = Path(directory.name)
        self.root = self.base / 'repo'
        self.runs = self.base / 'suite-runs'
        self.status = self.base / 'suite-status'
        self.fail_at = self.base / 'suite-fails-at'
        self.slow = self.base / 'suite-slow'
        self.suite_pid = self.base / 'suite-pids'
        self.stubborn = self.base / 'suite-ignores-signals'
        self.signals = self.base / 'suite-signals'
        self.pipe = self.base / 'suite-pipe-status'
        self.orphan = self.base / 'suite-orphan'
        self.tmp = self.base / 'tmp'
        self.tmp.mkdir()
        self.env = dict(os.environ, TMPDIR=str(self.tmp))
        self.seen = set()
        self.addCleanup(self.stop_stragglers)
        skill = self.root / '.agents/skills/writing-agent-docs'
        skill.mkdir(parents=True)
        for module in ('check_docs.py', 'architecture.py'):
            (skill / module).write_text((CHECKER.parent / module).read_text())
        (skill / 'config.json').write_text(json.dumps(CONFIG))
        for hook in ('pre-commit', 'pre-push'):
            path = self.root / '.githooks' / hook
            path.parent.mkdir(exist_ok=True)
            path.write_text((support.ROOT / '.githooks' / hook).read_text())
            path.chmod(0o755)
        suite = self.root / 'tests/run_all.py'
        suite.parent.mkdir()
        # Records the commit and directory it ran in; exits with the status file's value. The shell body
        # replaces the Python process, so its pid is the suite's own; the signals Python ignores are restored
        # first, as the real runner's subprocesses restore them for each test.
        body = ('cat >/dev/null\n'
                f'echo "$(git rev-parse HEAD) $(pwd -P) $(git status --porcelain | wc -l)" >> "{self.runs}"\n'
                + self.slow_suite() +
                f'[ "$(git rev-parse HEAD)" = "$(cat "{self.fail_at}" 2>/dev/null)" ] && exit 1\n'
                f'exit "$(cat "{self.status}" 2>/dev/null || echo 0)"\n')
        suite.write_text('import os, signal\nfor name in ("SIGPIPE", "SIGXFSZ"):\n'
                         '    signal.signal(getattr(signal, name), signal.SIG_DFL)\n'
                         f'os.execvp("bash", ["bash", "-c", {body!r}])\n')
        for name, text in {'README.md': '# Project\n\nSee [tool](skills/tool/SKILL.md).\n',
                           'skills/tool/SKILL.md': SKILL.format(name='tool', description='Runs the tool.'),
                           'shared/guide.md': GUIDE, 'scripts/run.py': "GUIDE = 'shared/guide.md'\n"}.items():
            (self.root / name).parent.mkdir(parents=True, exist_ok=True)
            (self.root / name).write_text(text)
        git(self.root, 'init', '-q', '-b', 'main')
        git(self.root, 'config', 'core.hooksPath', '.githooks')
        self.remote = self.base / 'remote.git'
        git(self.base, 'init', '-q', '--bare', str(self.remote))
        git(self.root, 'remote', 'add', 'origin', str(self.remote))

    def slow_suite(self):
        """Shell lines for a suite that waits and records its process ids, group, default SIGPIPE and signals.

        The pid file holds: suite pid, its process group, its sleep, a double-forked sleep (reparented away).
        """
        group = '$(ps -o pgid= -p $$ | tr -d " ")'
        return (f'if [ -f "{self.slow}" ]; then\n'
                f'  yes | head -n 1 >/dev/null; echo "${{PIPESTATUS[0]}}" > "{self.pipe}"\n'
                f'  if [ -f "{self.stubborn}" ]; then echo "$$ {group}" > "{self.suite_pid}"; trap "" INT TERM HUP QUIT; exec sleep 60; fi\n'
                f'  ( sleep 60 & echo $! > "{self.orphan}" )\n'
                f'  sleep 60 & nap=$!\n'
                f'  echo "$$ {group} $nap $(cat "{self.orphan}")" > "{self.suite_pid}"\n'
                f'  for s in INT TERM HUP QUIT; do trap "echo $s >> \\"{self.signals}\\"; sleep 0.5; kill $nap; exit 1" $s; done\n'
                f'  wait $nap\n'
                f'fi\n')

    def stop_stragglers(self):
        self.suite_pids()
        for pid in self.seen:
            if self.alive(pid):
                os.kill(pid, signal.SIGKILL)

    def commit(self, *flags):
        git(self.root, 'add', '-A')
        return subprocess.run(['git', '-C', str(self.root), *IDENTITY, 'commit', '-qm', 'change', *flags],
                              capture_output=True, text=True, env=self.env)

    def push(self, *args):
        return subprocess.run(['git', '-C', str(self.root), 'push', '-q', 'origin', *args],
                              capture_output=True, text=True, env=self.env)

    def suite_runs(self):
        return self.runs.read_text().splitlines() if self.runs.exists() else []

    def remote_head(self, ref='main'):
        result = subprocess.run(['git', '-C', str(self.remote), 'rev-parse', '-q', '--verify', ref],
                                capture_output=True, text=True)
        return result.stdout.strip() or None

    def start_hook(self):
        """Run pre-push directly in its own process group, as git would for a push of main; wait for the suite."""
        self.assertEqual(self.commit('--allow-empty').returncode, 0)
        sha = git(self.root, 'rev-parse', 'HEAD').strip()
        self.slow.write_text('1')
        self.suite_pid.unlink(missing_ok=True)
        hook = subprocess.Popen([str(self.root / '.githooks/pre-push'), 'origin', str(self.remote)], cwd=self.root,
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                env=self.env, start_new_session=True,
                                # As from a terminal: a runner that started us in the background ignores INT and QUIT.
                                preexec_fn=lambda: [signal.signal(number, signal.SIG_DFL)
                                                    for number in (signal.SIGINT, signal.SIGQUIT)])
        self.addCleanup(lambda: hook.poll() is None and hook.kill())
        hook.stdin.write(f'refs/heads/main {sha} refs/heads/main {"0" * 40}\n')
        hook.stdin.close()
        deadline = time.monotonic() + 20
        while not self.suite_pid.exists() or len(self.suite_pid.read_text().split()) < 2:
            self.assertLess(time.monotonic(), deadline, 'the suite never started')
            time.sleep(0.05)
        return hook

    def suite_pids(self):
        if not self.suite_pid.exists():
            return []
        fields = [int(value) for value in self.suite_pid.read_text().split()]
        self.seen.update([fields[0], *fields[2:]])
        return [fields[0], *fields[2:]]

    def suite_group(self):
        return int(self.suite_pid.read_text().split()[1])

    @staticmethod
    def alive(pid):
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        return True

    def temporary_worktrees(self):
        listed = git(self.root, 'worktree', 'list', '--porcelain')
        return [line.split(' ', 1)[1] for line in listed.splitlines()
                if line.startswith('worktree ') and 'automattic-pre-push.' in line]
