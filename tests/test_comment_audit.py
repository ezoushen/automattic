#!/usr/bin/env python3
"""Comment audit regressions through its CLI and real temporary Git history."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import support

SCRIPT = support.script('comment_audit.py')


class CommentAudit(unittest.TestCase):
    """Added plain comments are listed; documentation, directives, literals and unchanged lines are not."""

    def test_lists_only_added_plain_comments(self):
        with tempfile.TemporaryDirectory(prefix='automattic comment audit ') as directory:
            repo = Path(directory)
            env = support.isolated_env(repo)

            def git(*args):
                return subprocess.check_output(['git', '-c', 'core.hooksPath=/dev/null',
                                                '-c', 'commit.gpgsign=false', '-C', directory,
                                                *args], text=True, env=env).strip()

            def audit(*args, ok=True):
                result = subprocess.run([sys.executable, '-B', str(SCRIPT), '--repo', directory,
                                         '--base', base, *args], text=True, capture_output=True,
                                        env=env, cwd=repo.parent)
                if ok:
                    assert result.returncode == 0, (result.stdout, result.stderr)
                    return json.loads(result.stdout)
                assert result.returncode != 0, result.stdout
                return result

            git('init', '-b', 'main')
            git('config', 'user.name', 'Audit Test')
            git('config', 'user.email', 'audit@example.invalid')
            git('commit', '--allow-empty', '-m', 'base')
            base = git('rev-parse', 'HEAD')
            (repo / 'sample.py').write_text('''#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright Example

"""Module docs."""
def value():
    """Function docs."""
    text = "# string"
    # plain Python
    return text  # noqa: E501
''')
            (repo / 'sample.ts').write_text('''/** Interface docs. */
/// <reference types="node" />
const url = "https://example.invalid/#string";
// eslint-disable-next-line no-console
// @ts-expect-error fixture
// plain TypeScript
const x = 1; /* inline plain */
/* plain block
 * second line
 */
''')
            (repo / 'sample.js').write_text('''#!/usr/bin/env node
/* SPDX-License-Identifier: MIT
 * Copyright Example
 */

/** Function docs. */
const text = '// string';
// plain JavaScript
''')
            (repo / 'sample.sh').write_text('''#!/bin/sh
# shellcheck disable=SC2034
text='# string'
# plain shell
echo "$text" # inline shell
''')
            (repo / 'sample.sql').write_text('''-- noqa: LT01
SELECT '-- string', '/* string */';
-- plain SQL
SELECT 1; /* inline SQL */
''')
            (repo / 'unknown.txt').write_text('# unknown\n// unknown\n/* unknown */\n-- unknown\n')
            git('add', '.')
            expected = [
                {'file': 'sample.js', 'line': 8, 'text': '// plain JavaScript'},
                {'file': 'sample.py', 'line': 9, 'text': '# plain Python'},
                {'file': 'sample.sh', 'line': 4, 'text': '# plain shell'},
                {'file': 'sample.sh', 'line': 5, 'text': '# inline shell'},
                {'file': 'sample.sql', 'line': 3, 'text': '-- plain SQL'},
                {'file': 'sample.sql', 'line': 4, 'text': '/* inline SQL */'},
                {'file': 'sample.ts', 'line': 6, 'text': '// plain TypeScript'},
                {'file': 'sample.ts', 'line': 7, 'text': '/* inline plain */'},
                {'file': 'sample.ts', 'line': 8, 'text': '/* plain block'},
                {'file': 'sample.ts', 'line': 9, 'text': ' * second line'},
                {'file': 'sample.ts', 'line': 10, 'text': ' */'},
            ]
            actual = audit()
            assert actual == expected, actual
            assert audit('sample.py') == [
                {'file': 'sample.py', 'line': 9, 'text': '# plain Python'},
            ]
            git('commit', '-m', 'fixture')
            head = git('rev-parse', 'HEAD')
            (repo / 'sample.js').write_text('// working tree only\n')
            assert audit('--head', head) == expected
            base = head
            assert audit() == [{'file': 'sample.js', 'line': 1, 'text': '// working tree only'}]
            (repo / 'sample.js').write_text('''#!/usr/bin/env node
/* SPDX-License-Identifier: MIT
 * Copyright Example
 */

/** Function docs. */
const text = '// string';
// plain JavaScript
''')
            (repo / 'sample.ts').write_text('''/** Interface docs.
 * added doc line
 */
/// <reference types="node" />
const url = "https://example.invalid/#string";
// eslint-disable-next-line no-console
// @ts-expect-error fixture
// plain TypeScript
const x = 1; /* inline plain */
/* plain block
 * second line
 * added block line
 */
''')
            assert audit() == [
                {'file': 'sample.ts', 'line': 12, 'text': ' * added block line'},
            ]
            git('add', '.')
            git('commit', '-m', 'context')
            base = git('rev-parse', 'HEAD')
            (repo / 'sample.ts').unlink()
            (repo / 'space \" tab\t name.py').write_text('x = 1 # new comment\n')
            (repo / 'untracked.py').write_text('# outside Git diff\n')
            git('add', '-u')
            git('add', 'space " tab\t name.py')
            assert audit() == [
                {'file': 'space " tab\t name.py', 'line': 1, 'text': '# new comment'},
            ]
            assert audit('--head', base) == []
            assert 'comment-audit:' in audit('--head', 'missing-ref', ok=False).stderr
            git('commit', '-m', 'paths')
            base = git('rev-parse', 'HEAD')
            (repo / 'literals.js').write_text(r'''const regex = /[/*]/;
const division = 10 / 2; // after division
const raw = `// template text
/* template text */ ${1 /* interpolation comment */}`;
/// ordinary comment
const text = "escaped \" // string"; // after string
// discusses copyright after code
''')
            (repo / 'literals.sh').write_text('''cat <<'END'
# heredoc data
END
echo foo#word \\#escaped # shell comment
''')
            (repo / 'literals.sql').write_text('''SELECT $$-- dollar string$$, $tag$/* dollar string */$tag$;
SELECT 'escaped '' -- string'; -- after SQL string
''')
            (repo / 'literals.py').write_text('''# -*- coding: utf-8 -*-
value = 1 # type: int
# explains coding: wrong
value = """# multiline string
# still string
"""
# plain after string
''')
            git('add', 'literals.js', 'literals.sh', 'literals.sql', 'literals.py')
            expected = [
                {'file': 'literals.js', 'line': 2, 'text': '// after division'},
                {'file': 'literals.js', 'line': 4, 'text': '/* interpolation comment */'},
                {'file': 'literals.js', 'line': 5, 'text': '/// ordinary comment'},
                {'file': 'literals.js', 'line': 6, 'text': '// after string'},
                {'file': 'literals.js', 'line': 7, 'text': '// discusses copyright after code'},
                {'file': 'literals.py', 'line': 3, 'text': '# explains coding: wrong'},
                {'file': 'literals.py', 'line': 7, 'text': '# plain after string'},
                {'file': 'literals.sh', 'line': 4, 'text': '# shell comment'},
                {'file': 'literals.sql', 'line': 2, 'text': '-- after SQL string'},
            ]
            actual = audit('literals.*')
            assert actual == expected, actual
            git('commit', '-m', 'literals')
            base = git('rev-parse', 'HEAD')
            (repo / 'binary.py').write_bytes(b'\x00# binary data\n')
            (repo / 'link.py').symlink_to('sample.py')
            git('add', 'binary.py', 'link.py')
            git('config', 'color.ui', 'always')
            git('config', 'diff.outputIndicatorNew', '>')
            git('config', 'diff.outputIndicatorOld', '<')
            (repo / 'sample.py').write_text('# unstaged comment\n')
            status = git('status', '--porcelain')
            assert audit() == [
                {'file': 'sample.py', 'line': 1, 'text': '# unstaged comment'},
            ]
            assert git('status', '--porcelain') == status
            git('commit', '-m', 'binary and symlink')
            assert audit('--head', 'HEAD') == []
            base = git('rev-parse', 'HEAD')
            (repo / 'encoding.py').write_bytes(b'# coding: latin-1\n# caf\xe9\n')
            git('add', 'encoding.py')
            assert audit('encoding.py') == [
                {'file': 'encoding.py', 'line': 2, 'text': '# café'},
            ]


if __name__ == '__main__':
    unittest.main()
