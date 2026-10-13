#!/usr/bin/env python3
"""Target/options regressions with real temporary Git history and a local gh stub."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch

SCRIPT = Path(__file__).with_name('review-target.py')
spec = importlib.util.spec_from_file_location('review_target', SCRIPT)
rt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rt)


def check():
    with tempfile.TemporaryDirectory(prefix='automattic review ') as directory:
        repo = Path(directory)
        def git(*args):
            return subprocess.check_output(['git', '-C', directory, *args], text=True).strip()
        git('init', '-b', 'trunk')
        git('config', 'user.name', 'Review Test')
        git('config', 'user.email', 'review@example.invalid')
        git('remote', 'add', 'origin', 'git@github.com:O/R.git')
        (repo / 'code.txt').write_text('base\n')
        git('add', '.')
        git('commit', '-m', 'base')
        base = git('rev-parse', 'HEAD')
        git('checkout', '-b', 'feature')
        (repo / 'code.txt').write_text('changed\n')
        (repo / ' leading space.txt').write_text('file\n')
        git('add', '.')
        git('commit', '-m', 'feature')
        head = git('rev-parse', 'HEAD')
        git('branch', '123')
        (repo / 'unrelated.txt').write_text('preserve me\n')
        original_status = git('status', '--porcelain')

        def args(*extra):
            return rt.parser().parse_args(['--repo', directory, *extra])
        def rejects(fn):
            try:
                fn()
            except (ValueError, SystemExit):
                return
            raise AssertionError('expected rejection')
        plain = rt.resolve(args('feature', '--base', 'trunk'))
        assert plain['head'] == head and plain['base'] == plain['diff_base'] == base
        assert 'mode' not in plain and not plain['autofix']
        assert plain['comments'] == 'draft'
        assert set(plain['files']) == {'code.txt', ' leading space.txt'}
        assert rt.resolve(args('refs/heads/123', '--base', 'trunk'))['head'] == head
        rejects(lambda: args('feature', '--auto'))
        rejects(lambda: args('feature', '--interactive'))
        rejects(lambda: args('feature', '--unattended'))
        rejects(lambda: args('feature', '--comments', 'auto'))
        rejects(lambda: args('feature', '--comments'))
        for flags in ([], ['--autofix']):
            for comments in ('draft', 'confirm', 'post'):
                resolved = rt.resolve(args('feature', '--base', 'trunk', *flags,
                                           '--comments', comments))
                assert resolved['comments'] == comments
                assert resolved['autofix'] == bool(flags)
                assert 'mode' not in resolved
        rejects(lambda: rt.resolve(args('missing', '--base', 'trunk')))
        for target in ['http://github.com/o/r/pull/1', 'https://u:p@github.com/o/r/pull/1',
                       'https://github.com/o/r/issues/1']:
            rejects(lambda: rt.pr_target(target))

        pr = dict(number=123, url='https://github.com/o/r/pull/123', title='Change', body='Goal',
                  baseRefName='trunk', baseRefOid=base, headRefName='feature', headRefOid=head)
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
                resolved = rt.resolve(args(target, '--comments', 'post'))
                assert resolved['head'] == head and resolved['pr']['number'] == 123
                assert resolved['comments'] == 'post'
            rejects(lambda: rt.resolve(args('https://github.com/other/repo/pull/123')))
            git('remote', 'set-url', 'origin', 'https://github.com/other/repo.git')
            rejects(lambda: rt.resolve(args('123')))
            git('remote', 'set-url', 'origin', 'ssh://git@github.com/o/r.git')
            assert rt.resolve(args('123'))['head'] == head
            pr['headRefOid'] = base
            rejects(lambda: rt.resolve(args('feature')))
            pr['headRefOid'] = head
        # CLI resolution never changes the active branch or unrelated edits.
        result = subprocess.run([sys.executable, str(SCRIPT), '--repo', directory,
                                 'feature', '--base', 'trunk'], capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
        assert git('symbolic-ref', '--short', 'HEAD') == 'feature'
        assert git('status', '--porcelain') == original_status
        assert (repo / 'unrelated.txt').read_text() == 'preserve me\n'
    print('review targets: branch/PR/URL, options, revision identity and checkout preservation: ok')


if __name__ == '__main__':
    check()
