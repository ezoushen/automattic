#!/usr/bin/env python3
"""Resolve a review target without checking out, fetching, editing or publishing."""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
from urllib.parse import urlsplit


def run(repo, *args):
    result = subprocess.run(args, cwd=repo, capture_output=True, text=True, timeout=30)
    if result.returncode:
        raise ValueError(result.stderr.strip() or f'{args[0]} failed')
    return result.stdout.rstrip('\n')


def parser():
    p = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    p.add_argument('target', help='branch, PR number, or HTTPS PR URL')
    p.add_argument('--repo', type=Path, required=True)
    p.add_argument('--autofix', action='store_true')
    p.add_argument('--comments', choices=('draft', 'confirm', 'post'), default='draft',
                   help='keep local drafts, preview before posting, or authorize direct posting')
    p.add_argument('--base', help='explicit comparison ref')
    return p


def pr_target(target):
    if re.fullmatch(r'[1-9][0-9]*', target):
        return True
    if '://' not in target:
        return False
    url = urlsplit(target)
    if (url.scheme != 'https' or not url.hostname or url.username or url.password
            or url.query or not re.fullmatch(r'/[^/]+/[^/]+/pull/[1-9][0-9]*(?:/files)?/?', url.path)):
        raise ValueError('expected an HTTPS repository pull-request URL')
    return True


def repository_url(url):
    if '://' not in url:
        url = 'ssh://' + url.replace(':', '/', 1)
    parsed = urlsplit(url)
    return parsed.hostname, tuple(parsed.path.strip('/').removesuffix('.git').lower().split('/')[:2])


def resolve(args):
    repo = args.repo.resolve()
    root = run(repo, 'git', 'rev-parse', '--show-toplevel')
    if Path(root).resolve() != repo:
        raise ValueError('--repo must be the checkout root')
    target = args.target
    is_pr = pr_target(target)
    pr = None
    if is_pr or (not args.base and shutil.which('gh')):
        repository = json.loads(run(repo, 'gh', 'repo', 'view', '--json', 'url,defaultBranchRef'))
        remotes = run(repo, 'git', 'remote').splitlines()
        identities = {repository_url(run(repo, 'git', 'remote', 'get-url', remote)) for remote in remotes}
        if repository_url(repository['url']) not in identities:
            raise ValueError('GitHub repository is not a checkout remote; select the correct repository first')
        if is_pr:
            if '://' in target and repository_url(target) != repository_url(repository['url']):
                raise ValueError('PR belongs to a different repository; select its checkout first')
            selector = target
        else:
            branch = target.removeprefix('refs/heads/')
            candidates = json.loads(run(repo, 'gh', 'pr', 'list', '--head', branch,
                                        '--state', 'open', '--json', 'number', '--limit', '100'))
            if len(candidates) > 1:
                raise ValueError('branch matches multiple PRs; use a PR number or URL')
            selector = str(candidates[0]['number']) if candidates else None
        if selector:
            pr = json.loads(run(repo, 'gh', 'pr', 'view', selector, '--json',
                                'number,url,title,body,baseRefName,baseRefOid,headRefName,headRefOid'))
            if repository_url(pr['url']) != repository_url(repository['url']):
                raise ValueError('resolved PR repository differs from checkout repository')
        default = (repository.get('defaultBranchRef') or {}).get('name')
    else:
        default = None

    def commit(ref):
        return run(repo, 'git', 'rev-parse', '--verify', '--end-of-options', f'{ref}^{{commit}}')

    if is_pr:
        head = commit(pr['headRefOid'])
        base_ref = args.base or pr['baseRefOid']
    else:
        # Full refs also disambiguate a numeric branch from a PR number.
        ref = target if target.startswith(('refs/heads/', 'refs/remotes/')) else f'refs/heads/{target}'
        head = commit(ref)
        if pr and head != pr['headRefOid']:
            raise ValueError('local branch and PR head differ; choose PR number/URL or explicit --base for local review')
        base_ref = args.base or (pr['baseRefOid'] if pr else None)
        if not base_ref:
            if default:
                base_ref = f'refs/heads/{default}'
            else:
                remotes = run(repo, 'git', 'remote').splitlines()
                if len(remotes) != 1:
                    raise ValueError('default base is ambiguous; supply --base')
                base_ref = run(repo, 'git', 'symbolic-ref', f'refs/remotes/{remotes[0]}/HEAD')
    base = commit(base_ref)
    merge_bases = run(repo, 'git', 'merge-base', '--all', base, head).splitlines()
    if len(merge_bases) != 1:
        raise ValueError('review requires one unambiguous merge base')
    diff_base = merge_bases[0]
    files = run(repo, 'git', 'diff', '--no-ext-diff', '--name-only', '-z', diff_base, head).split('\0')
    return dict(repo=str(repo), target=target, pr=pr, base=base, head=head,
                diff_base=diff_base, files=[f for f in files if f],
                autofix=args.autofix, comments=args.comments)


if __name__ == '__main__':
    p = parser()
    try:
        print(json.dumps(resolve(p.parse_args()), indent=2))
    except (ValueError, OSError, subprocess.TimeoutExpired) as error:
        p.exit(2, f'review target: {error}\nMissing commits must be fetched from the verified repository before retrying; no checkout was changed.\n')
