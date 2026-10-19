#!/usr/bin/env python3
"""Automattic scheduler. Run from any directory; state stays in the main checkout.

  next_tickets.py --repo /path/to/repo [slug] [--max-live N] [action]

No action: JSON candidates. No slug: all efforts. Other efforts still hold locks.
Actions: --board, --counts, --check, --accept TICKET,
         --can-verify TICKET, --delivery, --set TICKET status=VALUE (or worker=ID).
Only --set may be combined with --counts.

Tickets: .scratch/<slug>/issues/NN-title.md, with restricted YAML front matter
(key: scalar and key: [a, b]). Only the orchestrator changes machine state.
Cross-effort prerequisites require the entire source effort done and its retained
branch merged into main and the target effort branch. --check detects missing
edges and cycles between tickets or efforts. One orchestrator per checkout.
"""
import argparse
from graphlib import CycleError, TopologicalSorter
import json
import os
import re
import sys
import subprocess
from pathlib import Path

ROOT = Path.cwd()
ISSUES = ROOT / ".scratch"
LIVE = {"implementing", "reviewing", "fixing", "verifying"}
TERMINAL = {"done"}
STATUSES = {"ready", "blocked"} | LIVE | TERMINAL
try:
    MAX_LIVE = int(os.environ.get("MAX_LIVE", "8"))
    assert MAX_LIVE >= 1
except (ValueError, AssertionError):
    sys.exit(f"MAX_LIVE must be a positive integer, got {os.environ.get('MAX_LIVE')!r}")
# Critical path first. TICKET_PRIORITY=spec-a,spec-b names the specs to drain first; default is name order.
PRIORITY = [s for s in os.environ.get("TICKET_PRIORITY", "").split(",") if s]


def parse_front_matter(text):
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return None
    fm = {}
    for line in m.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, _, value = line.partition(":")
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            fm[key.strip()] = [v.strip() for v in value[1:-1].split(",") if v.strip()]
        else:
            fm[key.strip()] = value
    return fm


def load():
    tickets = {}
    for path in sorted(ISSUES.glob("*/issues/*.md")):
        fm = parse_front_matter(path.read_text())
        if fm and "ticket" in fm:
            if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*/[0-9]+", fm["ticket"]):
                sys.exit(f"{path}: invalid ticket id {fm['ticket']!r}")
            if fm["ticket"] in tickets:
                sys.exit(f"{path}: duplicate ticket {fm['ticket']}")
            if path.parent.parent.name != spec_of(fm["ticket"]):
                sys.exit(f"{path}: ticket effort differs from its directory")
            for key in ("blocked_by", "touches", "devices"):
                if not isinstance(fm.get(key), list):
                    sys.exit(f"{path}: {key} must be a bracketed list")
            fm["path"] = str(path.relative_to(ROOT))
            tickets[fm["ticket"]] = fm
        elif fm and set(fm) & {"blocked_by", "touches", "devices", "worker"}:
            sys.exit(f"{path}: missing ticket front matter")
    return tickets


def check(tickets):
    bad = [f"{t}: status {fm.get('status')!r} is not one of {sorted(STATUSES)}"
           for t, fm in tickets.items() if fm.get('status') not in STATUSES]
    bad += [f"{t}: blocked_by {dep} does not exist" for t, fm in tickets.items()
           for dep in fm.get("blocked_by", []) if dep not in tickets]
    bad += [f"{t}: no blocked_by key (write blocked_by: [] when nothing gates it)" for t, fm in tickets.items()
            if "blocked_by" not in fm]
    bad += [f"{t}: number differs from its filename {Path(fm['path']).name}" for t, fm in tickets.items()
            if not Path(fm["path"]).name.startswith(t.split("/")[-1] + "-")]
    graphs = {"ticket": {t: fm.get("blocked_by", []) for t, fm in tickets.items()},
              "effort": {spec_of(t): set() for t in tickets}}
    for t, fm in tickets.items():
        graphs["effort"][spec_of(t)].update(spec_of(d) for d in fm.get("blocked_by", [])
                                           if spec_of(d) != spec_of(t))
    for label, graph in graphs.items():
        try:
            tuple(TopologicalSorter(graph).static_order())
        except CycleError as error:
            bad.append(f"{label} dependency cycle: {' -> '.join(error.args[1])}")
    for line in bad:
        print(line, file=sys.stderr)
    return not bad


def spec_of(name):
    return name.split("/")[0]


def integrated(tickets, name, dependency):
    source = spec_of(dependency)
    if source == spec_of(name):
        return True
    if any(fm["status"] != "done" for t, fm in tickets.items() if spec_of(t) == source):
        return False
    if not delivery_evidence(source):
        return False
    prerequisite = f"refs/heads/feat/{source}"
    target = f"refs/heads/feat/{spec_of(name)}"
    exists = subprocess.run(["git", "-C", str(ROOT), "show-ref", "--verify", "--quiet", target])
    bases = ["refs/heads/main"] + ([target] if exists.returncode == 0 else [])
    return all(subprocess.run(["git", "-C", str(ROOT), "merge-base", "--is-ancestor", prerequisite, base],
                              capture_output=True).returncode == 0 for base in bases)


def delivery_evidence(slug):
    """Structural delivery gate; the orchestrator must also judge the recorded evidence."""
    report = ISSUES / slug / 'reports' / 'spec-review.md'
    if not report.is_file():
        return False
    fm = parse_front_matter(report.read_text()) or {}
    head = subprocess.run(['git', '-C', str(ROOT), 'rev-parse', '--verify',
                           f'refs/heads/feat/{slug}^{{commit}}'], capture_output=True, text=True)
    base = fm.get('review_base', '')
    if head.returncode or not isinstance(base, str) or not re.fullmatch('[0-9a-f]{40}', base):
        return False
    sha = head.stdout.strip()
    merge_base = subprocess.run(['git', '-C', str(ROOT), 'merge-base', '--all', base, sha],
                                capture_output=True, text=True)
    # The worker runs that produced the statuses; a host-written status alone is not evidence.
    producers = [str(fm.get(key) or '').strip() for key in ('review_by', 'e2e_by')]
    if any(p.lower() in ('', 'none', 'n/a', 'unknown', 'orchestrator', 'host') for p in producers):
        return False
    return (fm.get('review_status') == 'clean' and fm.get('review_head') == sha
            and fm.get('documentation_status') == 'passed'
            and fm.get('e2e_status') == 'passed' and fm.get('e2e_head') == sha
            and merge_base.returncode == 0
            and merge_base.stdout.splitlines() == [fm.get('review_diff_base')])


def ready(tickets, slug=None, max_live=MAX_LIVE):
    live = [fm for fm in tickets.values() if fm["status"] in LIVE]
    busy_areas = {a for fm in live for a in fm.get("touches", [])}
    out = []
    order = sorted(tickets, key=lambda n: (PRIORITY.index(n.split("/")[0]) if n.split("/")[0] in PRIORITY else 99, n))
    for name in order:
        if len(live) + len(out) >= max_live:
            break
        fm = tickets[name]
        if fm["status"] != "ready" or (slug and spec_of(name) != slug):
            continue
        if any(tickets[d]["status"] not in TERMINAL for d in fm.get("blocked_by", [])):
            continue
        if any(not integrated(tickets, name, d) for d in fm.get("blocked_by", [])):
            continue
        if busy_areas & set(fm.get("touches", [])):
            continue
        out.append(fm)
        busy_areas |= set(fm.get("touches", []))
    return out


def spec_devices(tickets, spec):
    """E2E runs once per spec, so a spec's run needs the union of its tickets' devices."""
    return {d for fm in tickets.values() if spec_of(fm["ticket"]) == spec for d in fm.get("devices", [])}


def can_verify(tickets, name):
    """A device is held only for the duration of a spec's `verifying` stage."""
    want = spec_devices(tickets, spec_of(name))
    held = {d: t for t, fm in tickets.items() if fm["status"] == "verifying" and spec_of(t) != spec_of(name)
            for d in spec_devices(tickets, spec_of(t))}
    clash = {d: held[d] for d in want & held.keys()}
    if clash:
        print(f"{name}: wait, {', '.join(f'{d} held by {t}' for d, t in sorted(clash.items()))}")
        return False
    print(f"{name}: devices free ({', '.join(sorted(want)) or 'none needed'})")
    return True


def report_problems(text):
    """The structural half of the Implementer exit criterion: what a report must carry before anyone reads it."""
    problems = []
    if not re.search(r"^base:\s*`?[0-9a-f]{40}`?", text, re.M):
        problems.append("no `base: <40-hex sha>` line")
    if "## Implemented" not in text:
        problems.append("no `## Implemented` section")
    if not re.search(r"- \[[ x]\]", text):
        problems.append("no ticket checkbox accounted for")
    return problems


def accept(tickets, name):
    """Deterministic verify node: the report exists in the main checkout with its evidence, and the branch moved."""
    slug, nn = name.split("/")
    report = ISSUES / slug / "reports" / f"{nn}.md"
    if not report.exists():
        print(f"{name}: no report at {report}", file=sys.stderr)
        return False
    text = report.read_text()
    problems = report_problems(text)
    base = re.search(r"^base:\s*`?([0-9a-f]{40})", text, re.M)
    if base:
        # An inline ticket records the effort branch it committed on; a delegated one has its own.
        recorded = re.search(r"^branch:\s*`?([^\s`]+)", text, re.M)
        branch = recorded.group(1) if recorded else f"feat/{slug}-{nn}"
        count = subprocess.run(["git", "-C", str(ROOT), "rev-list", "--count", f"{base.group(1)}..{branch}"],
                               capture_output=True, text=True)
        if count.returncode != 0:
            problems.append(f"branch {branch} or base not found: {count.stderr.strip()}")
        elif subprocess.run(["git", "-C", str(ROOT), "merge-base", "--is-ancestor", base.group(1), branch],
                            capture_output=True).returncode != 0:
            problems.append(f"base is not an ancestor of {branch}")
        elif int(count.stdout) == 0:
            problems.append(f"no commit past base on {branch}")
    for p in problems:
        print(f"{name}: {p}", file=sys.stderr)
    if not problems:
        print(f"{name}: report and branch carry the evidence; judge the content now")
    return not problems


def set_field(tickets, name, assignment):
    key, equals, value = assignment.partition("=")
    if not equals or key not in {"status", "worker"} or any(c in value for c in "\r\n"):
        sys.exit(f"{name}: --set accepts one-line status= or worker= only")
    if key == "status" and value not in STATUSES:
        sys.exit(f"{name}: status {value!r} is not one of {sorted(STATUSES)}")
    fm = tickets[name]
    path = ROOT / fm["path"]
    text = path.read_text()
    pattern = re.compile(rf"^({re.escape(key)}:).*$", re.M)
    head, sep, body = text.partition("\n---\n")
    if pattern.search(head):
        head = pattern.sub(lambda match: f"{match[1]} {value}", head, count=1)
    elif key == 'status':
        head += f'\nstatus: {value}'
    else:
        sys.exit(f"{name}: no front-matter key {key!r}")
    path.write_text(head + sep + body)
    print(f"{name}: {key} = {value}")


def counts(tickets):
    n = {s: sum(fm["status"] == s for fm in tickets.values()) for s in ("done", "blocked", "ready")}
    n["live"] = sum(fm["status"] in LIVE for fm in tickets.values())
    assert sum(n.values()) == len(tickets), "a ticket has a status outside the enum; see --board"
    return " · ".join(f"{v} {k}" for k, v in n.items())


def main(argv):
    global ROOT, ISSUES
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", type=Path, required=True, help="absolute main checkout path")
    parser.add_argument("slug", nargs="?", help="only this effort; locks still include the whole board")
    parser.add_argument("--max-live", type=int, default=MAX_LIVE)
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--check", action="store_true")
    actions.add_argument("--board", action="store_true")
    actions.add_argument("--accept", metavar="TICKET")
    actions.add_argument("--can-verify", metavar="TICKET")
    actions.add_argument("--delivery", action="store_true", help="require done tickets and current review/E2E evidence")
    actions.add_argument("--set", nargs=2, metavar=("TICKET", "ASSIGNMENT"))
    parser.add_argument("--counts", action="store_true")
    args = parser.parse_args(argv)
    if args.counts and any((args.check, args.board, args.accept, args.can_verify, args.delivery)):
        parser.error("--counts may only be combined with --set")
    if args.max_live < 1:
        parser.error("--max-live must be positive")
    if args.slug and not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", args.slug):
        parser.error("slug must be kebab-case")
    ROOT = args.repo.resolve()
    ISSUES = ROOT / ".scratch"
    root = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    common = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--git-common-dir"], capture_output=True, text=True)
    if root.returncode or Path(root.stdout.strip()).resolve() != ROOT or (ROOT / common.stdout.strip()).resolve() != ROOT / ".git":
        parser.error("--repo must name the main Git checkout, not a subdirectory or linked worktree")
    tickets = load()
    selected = {t: fm for t, fm in tickets.items() if not args.slug or spec_of(t) == args.slug}
    if not selected:
        parser.error(f"no tickets in requested scope under {ISSUES}")
    for name in (args.accept, args.can_verify, args.set[0] if args.set else None):
        if name and name not in selected:
            parser.error(f"{name}: no such ticket in requested scope")
    if args.board:
        for name, fm in selected.items():
            deps = ",".join(fm.get("blocked_by", [])) or "-"
            print(f"{fm.get('status', '<missing>'):<12} {name:<52} touches={','.join(fm.get('touches', []))} blocked_by={deps}")
        return
    if args.set:
        set_field(tickets, *args.set)
        if args.counts:
            print(counts({t: fm for t, fm in load().items() if t in selected}))
        return
    if not check(tickets):
        sys.exit(1)
    if args.check:
        return
    if args.delivery:
        bad = [slug for slug in sorted({spec_of(t) for t in selected})
               if any(fm['status'] != 'done' for t, fm in selected.items() if spec_of(t) == slug)
               or not delivery_evidence(slug)]
        if bad:
            sys.exit('delivery incomplete or stale: ' + ', '.join(bad))
        print('delivery evidence matches selected effort heads; inspect the recorded artifacts')
        return
    for name, fn in ((args.accept, accept), (args.can_verify, can_verify)):
        if name:
            sys.exit(0 if fn(tickets, name) else 1)
    if args.counts:
        print(counts(selected))
        return
    print(json.dumps(ready(tickets, args.slug, args.max_live), indent=2))


if __name__ == "__main__":
    main(sys.argv[1:])
