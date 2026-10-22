#!/usr/bin/env python3
"""The plugin is zloop: no tracked file, path or untracked source names it by its former name."""
import re
import subprocess
import unittest

import support

ROOT = support.ROOT
# Spelled in two parts, so this file does not name it.
FORMER = re.compile('auto' + 'mattic', re.IGNORECASE)


def files():
    listed = subprocess.run(['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'],
                            cwd=ROOT, capture_output=True, text=True, check=True).stdout
    return [name for name in listed.split('\0') if name and (ROOT / name).is_file()]


class PluginName(unittest.TestCase):
    def test_no_file_or_path_names_the_former_plugin(self):
        found = []
        for name in files():
            if FORMER.search(name):
                found.append(name)
            try:
                text = (ROOT / name).read_text()
            except UnicodeDecodeError:
                continue
            found += [f'{name}:{number}' for number, line in enumerate(text.splitlines(), 1) if FORMER.search(line)]
        self.assertEqual(found, [])

    def test_the_guard_catches_every_case_of_the_former_name(self):
        for text in ('auto' + 'mattic', 'Auto' + 'mattic', 'AUTO' + 'MATTIC_WORKER', '/auto' + 'mattic:dispatch'):
            with self.subTest(text=text):
                self.assertIsNotNone(FORMER.search(text))
        self.assertIsNone(FORMER.search('automatic zloop'))


if __name__ == '__main__':
    unittest.main()
