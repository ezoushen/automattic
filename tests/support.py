"""Shared test helpers: plugin paths, script loading and machine-state isolation."""
import importlib.util
import os
import re
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / 'scripts'
HOOKS = ROOT / 'hooks'
# Scripts import their siblings by module name, as they do when run from scripts/.
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def script(filename):
    """Path of a script in scripts/."""
    return SCRIPTS / filename


def load_script(filename, name=None):
    """Import a fresh copy of a script from scripts/ as a module."""
    path = SCRIPTS / filename
    spec = importlib.util.spec_from_file_location(name or path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def isolated_env(root, **values):
    """The current environment with Automattic state, config and Codex home under root."""
    root = Path(root)
    return dict(os.environ, XDG_STATE_HOME=str(root / 'state'), XDG_CONFIG_HOME=str(root / 'config'),
                CODEX_HOME=str(root / 'codex'), **values)


def assignment_file(root, job, text=''):
    """An assignment for job that names every input the resolver requires, followed by text."""
    import agent_defs
    definition = agent_defs.load()['jobs'][job]
    lines = [f'{name}: /fixture/{name.replace(" ", "-")}' for name in (*agent_defs.COMMON_INPUTS, *definition['inputs'])]
    path = Path(root) / f'{job}-assignment.txt'
    path.write_text('\n'.join(lines) + '\n' + text)
    return path


def code_samples(text):
    """Code a prose-only doc must not contain: code spans, fenced or indented blocks, dotted identifiers."""
    unquoted = '\n'.join(re.sub(r'^ {0,3}(?:> ?)+', '', line) for line in text.splitlines())
    prose = re.sub(r'\]\([^)]*\)', ']', unquoted)
    found = re.findall(r'`[^`\n]+`', prose) + re.findall(r'(?m)^ {0,3}(?:```|~~~).*$', prose)
    in_list, after_blank = False, True
    for line in prose.splitlines():
        if not line.strip():
            after_blank = True
            continue
        if re.match(r' {0,3}(?:[-*+]|\d+\.) ', line):
            in_list = True
        elif line[0] not in ' \t':
            in_list = False
        elif line.startswith(('    ', '\t')) and after_blank and not in_list:
            found.append(line)
        after_blank = False
    return found + [name for name in re.findall(r'\b[A-Za-z_]\w+(?:\.[A-Za-z_]\w+)+', prose)
                    if not name.endswith('.md')]
