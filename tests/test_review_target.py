#!/usr/bin/env python3
"""Target/options regressions with real temporary Git history and a local gh stub."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import support

SCRIPT = support.script('review_target.py')
rt = support.load_script('review_target.py', 'review_target')


class ReviewTarget(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='zloop review ')
        self.addCleanup(self.tmp.cleanup)
        self.directory = self.tmp.name
        self.repo = Path(self.directory)
        self.git('init', '-b', 'trunk')
        self.git('config', 'user.name', 'Review Test')
        self.git('config', 'user.email', 'review@example.invalid')
        self.git('remote', 'add', 'origin', 'git@github.com:O/R.git')
        (self.repo / 'code.txt').write_text('base\n')
        self.git('add', '.')
        self.git('commit', '-m', 'base')
        self.base = self.git('rev-parse', 'HEAD')
        self.git('checkout', '-b', 'feature')
        (self.repo / 'code.txt').write_text('changed\n')
        (self.repo / ' leading space.txt').write_text('file\n')
        self.git('add', '.')
        self.git('commit', '-m', 'feature')
        self.head = self.git('rev-parse', 'HEAD')
        self.git('branch', '123')
        (self.repo / 'unrelated.txt').write_text('preserve me\n')

    def git(self, *args):
        return subprocess.check_output(['git', '-C', self.directory, *args], text=True).strip()

    def args(self, *extra):
        return rt.parser().parse_args(['--repo', self.directory, *extra])

    def rejects(self, fn):
        with self.assertRaises((ValueError, SystemExit)):
            fn()

    def test_branch_target_resolves_head_base_and_changed_files(self):
        plain = rt.resolve(self.args('feature', '--base', 'trunk'))
        assert plain['head'] == self.head and plain['base'] == plain['diff_base'] == self.base
        assert 'mode' not in plain and not plain['autofix']
        assert plain['comments'] == 'draft'
        assert set(plain['files']) == {'code.txt', ' leading space.txt'}
        assert rt.resolve(self.args('refs/heads/123', '--base', 'trunk'))['head'] == self.head
        self.rejects(lambda: rt.resolve(self.args('missing', '--base', 'trunk')))

    def test_only_autofix_and_comment_options_are_accepted(self):
        self.rejects(lambda: self.args('feature', '--auto'))
        self.rejects(lambda: self.args('feature', '--interactive'))
        self.rejects(lambda: self.args('feature', '--unattended'))
        self.rejects(lambda: self.args('feature', '--comments', 'auto'))
        self.rejects(lambda: self.args('feature', '--comments'))
        for flags in ([], ['--autofix']):
            for comments in ('draft', 'confirm', 'post'):
                resolved = rt.resolve(self.args('feature', '--base', 'trunk', *flags,
                                                '--comments', comments))
                assert resolved['comments'] == comments
                assert resolved['autofix'] == bool(flags)
                assert 'mode' not in resolved

    def test_pull_request_targets_must_match_the_repository_and_head(self):
        for target in ['http://github.com/o/r/pull/1', 'https://u:p@github.com/o/r/pull/1',
                       'https://github.com/o/r/issues/1']:
            self.rejects(lambda: rt.pr_target(target))
        pr = dict(number=123, url='https://github.com/o/r/pull/123', title='Change', body='Goal',
                  baseRefName='trunk', baseRefOid=self.base, headRefName='feature', headRefOid=self.head)
        actual_run = rt.run
        def stub(cwd, *command):
            if command[:3] == ('gh', 'repo', 'view'):
                return json.dumps(dict(url='https://github.com/o/r', defaultBranchRef=dict(name='trunk')))
            if command[:3] == ('gh', 'pr', 'view'):
                return json.dumps(pr)
            if command[:3] == ('gh', 'pr', 'list'):
                return '[{"number":123}]'
            return actual_run(cwd, *command)
        with patch.object(rt, 'run', stub), patch.object(rt.shutil, 'which', return_value='/fake/gh'):
            for target in ['123', pr['url'], pr['url'] + '/files', 'feature']:
                resolved = rt.resolve(self.args(target, '--comments', 'post'))
                assert resolved['head'] == self.head and resolved['pr']['number'] == 123
                assert resolved['comments'] == 'post'
            self.rejects(lambda: rt.resolve(self.args('https://github.com/other/repo/pull/123')))
            self.git('remote', 'set-url', 'origin', 'https://github.com/other/repo.git')
            self.rejects(lambda: rt.resolve(self.args('123')))
            self.git('remote', 'set-url', 'origin', 'ssh://git@github.com/o/r.git')
            assert rt.resolve(self.args('123'))['head'] == self.head
            pr['headRefOid'] = self.base
            self.rejects(lambda: rt.resolve(self.args('feature')))

    def test_cli_resolution_preserves_the_checkout(self):
        original_status = self.git('status', '--porcelain')
        result = subprocess.run([sys.executable, str(SCRIPT), '--repo', self.directory,
                                 'feature', '--base', 'trunk'], capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
        assert self.git('symbolic-ref', '--short', 'HEAD') == 'feature'
        assert self.git('status', '--porcelain') == original_status
        assert (self.repo / 'unrelated.txt').read_text() == 'preserve me\n'


if __name__ == '__main__':
    unittest.main()
