"""The module architecture contract (architecture.json), shared by the doc checker, the
fold check and the import-direction test.

Modules sit in ordered levels, top first. A module may depend on a module in a lower
level and on itself; it may not depend on a higher level, a sibling in its own level or
a module marked `unlinked` (injected by path, never linked). A module marked `isolated`
may not even link its own other files. Violations recorded under `debt` are tolerated;
a debt entry may only shrink, so a new violation is an error and a fixed one is stale.
"""
import ast
import json
from pathlib import Path
import re


def glob_regex(pattern):
    """Regex for a repository-relative glob: `**` crosses folders, `*` and `?` stay inside one."""
    out, index = '', 0
    while index < len(pattern):
        if pattern.startswith('**/', index):
            out, index = out + '(?:.*/)?', index + 3
        elif pattern.startswith('**', index):
            out, index = out + '.*', index + 2
        elif pattern[index] == '*':
            out, index = out + '[^/]*', index + 1
        elif pattern[index] == '?':
            out, index = out + '[^/]', index + 1
        else:
            out, index = out + re.escape(pattern[index]), index + 1
    return re.compile(out + r'\Z')


class Architecture:
    def __init__(self, data, name='architecture.json'):
        self.data = data
        self.name = name
        self.debt = data.get('debt', {})
        self.modules = data['modules']
        self.level = {name: number for number, names in enumerate(data['levels']) for name in names}
        missing = set(self.modules) - set(self.level)
        if missing:
            raise ValueError(f'modules missing from levels: {sorted(missing)}')
        self.patterns = {kind: [(name, [glob_regex(glob) for glob in spec.get(kind, [])])
                                for name, spec in self.modules.items()] for kind in ('docs', 'code')}

    @classmethod
    def load(cls, path):
        return cls(json.loads(Path(path).read_text()), Path(path).name)

    def module(self, rel, kind='docs'):
        """The first module whose globs match a repository-relative path, or None."""
        for name, patterns in self.patterns[kind]:
            if any(pattern.match(rel) for pattern in patterns):
                return name
        return None

    def reason(self, src, src_module, dst, dst_module):
        """Why a dependency breaks the architecture, or None when it is allowed."""
        if src_module == dst_module:
            if self.modules[src_module].get('isolated') and src != dst:
                return f'{src_module} entries are independent of each other'
            return None
        if self.modules[dst_module].get('unlinked'):
            return f'{dst_module} is injected by path, never linked'
        if self.level[dst_module] < self.level[src_module]:
            return f'{src_module} may not depend on {dst_module}, which sits above it'
        if self.level[dst_module] == self.level[src_module]:
            return f'{src_module} may not depend on {dst_module}, its sibling'
        return None

    def assess(self, edges, kind, code, debt_edges, debt_cycles):
        """Findings (path, line, severity, code, message) for dependency edges.

        edges: (source, line, target) repository-relative paths; kind: 'docs' or 'code'
        picks the module mapping; code names the direction finding; debt_edges and
        debt_cycles are the recorded debt lists for this kind.
        """
        findings, broken, graph = [], {}, {}
        for src, line, dst in edges:
            src_module, dst_module = self.module(src, kind), self.module(dst, kind)
            if src_module is None or dst_module is None:
                continue
            if src_module != dst_module:
                graph.setdefault(src_module, {}).setdefault(dst_module, (src, line))
            if reason := self.reason(src, src_module, dst, dst_module):
                broken.setdefault(f'{src} -> {dst}', []).append((src, line, reason))
        for key, sites in broken.items():
            if key not in debt_edges:
                for src, line, reason in sites:
                    findings.append((src, line, 'error', code, f'{key}: {reason}'))
        for key in debt_edges:
            if key not in broken:
                findings.append((key.split(' -> ')[0], 1, 'warning', 'stale-debt',
                                 f'{key} breaks no rule now; remove its recorded debt'))
        recorded = [set(cycle) for cycle in debt_cycles]
        found = self.cycles(graph)
        for cycle in found:
            names = ', '.join(sorted(cycle))
            src, line = min(site for a in cycle for b, site in graph[a].items() if b in cycle)
            bigger = [r for r in recorded if cycle <= r]
            if not bigger:
                findings.append((src, line, 'error', 'cycle', f'modules depend on each other in a cycle: {names}'))
            elif cycle not in recorded:
                findings.append((src, line, 'warning', 'debt',
                                 f'cycle {names} is smaller than its recorded debt; record the smaller cycle'))
        for cycle in recorded:
            if not any(f <= cycle for f in found):
                findings.append((self.name, 1, 'warning', 'stale-debt',
                                 f'cycle {", ".join(sorted(cycle))} no longer exists; remove its recorded debt'))
        return findings

    @staticmethod
    def cycles(graph):
        """Strongly connected sets of two or more modules (Tarjan)."""
        index, low, stack, on, result, counter = {}, {}, [], set(), [], [0]

        def visit(node):
            index[node] = low[node] = counter[0]
            counter[0] += 1
            stack.append(node)
            on.add(node)
            for nxt in graph.get(node, {}):
                if nxt not in index:
                    visit(nxt)
                    low[node] = min(low[node], low[nxt])
                elif nxt in on:
                    low[node] = min(low[node], index[nxt])
            if low[node] == index[node]:
                members = set()
                while True:
                    member = stack.pop()
                    on.discard(member)
                    members.add(member)
                    if member == node:
                        break
                if len(members) > 1:
                    result.append(members)

        for node in sorted(set(graph) | {n for targets in graph.values() for n in targets}):
            if node not in index:
                visit(node)
        return result


def check_imports(root, architecture):
    """Findings for Python imports between the scripts and hooks that modules own.

    An import counts wherever it sits, including inside a function, and so does a string
    naming another script's path (scripts loaded by file location).
    """
    files = {str(path.relative_to(root)) for spec in architecture.modules.values()
             for glob in spec.get('code', []) for path in root.glob(glob) if path.is_file()}
    stems = {Path(name).stem: name for name in sorted(files)}
    edges = []
    for name in sorted(files):
        tree = ast.parse((root / name).read_text(), name)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                found = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
                found = [node.module]
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                found = [match.group(1) for match in re.finditer(r'(?:scripts|hooks)/(\w+)\.py', node.value)]
            else:
                continue
            for module in found:
                target = stems.get(module.split('.')[0])
                if target and target != name:
                    edges.append((name, node.lineno, target))
    debt = architecture.debt
    return architecture.assess(edges, 'code', 'import-direction', debt.get('imports', []), debt.get('import_cycles', []))
