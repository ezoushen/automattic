"""Shared test helpers: plugin paths, script loading and machine-state isolation."""
import importlib.util
import os
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
