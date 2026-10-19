#!/usr/bin/env python3
"""The local board's scheduling rules and its command line."""
import os
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import support

os.environ.pop("TICKET_PRIORITY", None)
os.environ.pop("MAX_LIVE", None)

SCRIPT = support.script("next_tickets.py")
nt = support.load_script("next_tickets.py", "next_tickets")
ready, can_verify, counts, report_problems, MAX_LIVE = (
    nt.ready, nt.can_verify, nt.counts, nt.report_problems, nt.MAX_LIVE)


def ticket(name, status, touches, devices=(), blocked=()):
    return {"ticket": name, "status": status, "touches": list(touches), "devices": list(devices),
            "blocked_by": list(blocked), "model": "sonnet", "path": "x"}


def names(tickets):
    return [fm["ticket"] for fm in ready(tickets)]


class Scheduling(unittest.TestCase):
    def test_a_device_is_held_only_while_its_holder_is_verifying(self):
        # An unrelated ticket may start work on a device it will not touch until its own E2E run...
        verifying_on_ios = {
            "apple-native-edge/01": ticket("apple-native-edge/01", "verifying", ["apple"], ["ios"]),
            "runtime-instance/02": ticket("runtime-instance/02", "ready", ["runtime"], ["android", "ios"]),
        }
        assert names(verifying_on_ios) == ["runtime-instance/02"], names(verifying_on_ios)
        # ...but it must not enter `verifying` while the holder is still there.
        assert can_verify(verifying_on_ios, "runtime-instance/02") is False
        verifying_on_ios["apple-native-edge/01"]["status"] = "done"
        assert can_verify(verifying_on_ios, "runtime-instance/02") is True

    def test_two_live_tickets_never_share_an_area(self):
        same_area = {"a/01": ticket("a/01", "implementing", ["runtime"]),
                     "b/01": ticket("b/01", "ready", ["runtime"])}
        assert names(same_area) == [], names(same_area)

    def test_blockers_must_be_done_and_the_live_cap_holds(self):
        blocked = {"a/01": ticket("a/01", "reviewing", ["apple"]),
                   "b/01": ticket("b/01", "ready", ["runtime"], blocked=["a/01"])}
        assert names(blocked) == [], names(blocked)
        assert len(ready({f"s{i}/01": ticket(f"s{i}/01", "ready", [f"area{i}"]) for i in range(MAX_LIVE + 2)})) == MAX_LIVE

    def test_tickets_of_one_spec_run_together_when_their_areas_differ(self):
        same_spec_parallel = {"s/01": ticket("s/01", "implementing", ["generator"]),
                              "s/02": ticket("s/02", "ready", ["docs"]),
                              "t/01": ticket("t/01", "ready", ["apple"])}
        assert names(same_spec_parallel) == ["s/02", "t/01"], names(same_spec_parallel)

    def test_a_full_board_admits_nothing(self):
        # The live cap is checked before admitting a candidate, not after.
        full = {f"s{i}/01": ticket(f"s{i}/01", "implementing", [f"area{i}"]) for i in range(MAX_LIVE)}
        full["spare/01"] = ticket("spare/01", "ready", ["spare"])
        assert names(full) == [], names(full)

    def test_a_spec_verifies_with_every_device_its_tickets_name(self):
        spec_union = {"u/01": ticket("u/01", "done", ["a"], ["android"]),
                      "u/02": ticket("u/02", "verifying", ["b"], []),
                      "v/01": ticket("v/01", "done", ["c"], ["android"])}
        assert can_verify(spec_union, "v/01") is False

    def test_the_count_line_names_every_bucket(self):
        # Zeros included, so the goal evaluator can read "0 ready".
        line = counts({"a/01": ticket("a/01", "done", ["x"])})
        assert line == "1 done · 0 blocked · 0 ready · 0 live", line

    def test_acceptance_requires_base_section_and_checkboxes(self):
        good = "base: `" + "a" * 40 + "`\n## Implemented\n- [x] done\n"
        assert report_problems(good) == [], report_problems(good)
        assert len(report_problems("# empty\n")) == 3


class BoardCLI(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix='automattic-board-')
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        subprocess.run(['git', 'init', '-q', '-b', 'main', str(self.root)], check=True)

    def write_ticket(self, name, status='ready', touches='runtime', blocked='', devices=''):
        slug, number = name.split('/')
        path = self.root / '.scratch' / slug / 'issues' / f'{number}-task.md'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f'---\nticket: {name}\nstatus: {status}\n'
                        f'blocked_by: [{blocked}]\ntouches: [{touches}]\ndevices: [{devices}]\n---\n')
        return path

    def cli(self, *args, code=0):
        result = subprocess.run([sys.executable, '-B', str(SCRIPT), '--repo', str(self.root), *args],
                                capture_output=True, text=True)
        assert result.returncode == code, result.stdout + result.stderr
        return result

    def test_board_reads_validates_and_repairs_ticket_state(self):
        write_ticket, cli = self.write_ticket, self.cli
        active = write_ticket('active/01')
        history = self.root / '.scratch/history/issues/old.md'
        history.parent.mkdir(parents=True)
        history.write_text('# Historical issue\nNo machine ticket state.\n')
        assert [item['ticket'] for item in json.loads(cli('active').stdout)] == ['active/01']
        history.write_text('---\nstatus: closed\n---\n# Historical tracker note\n')
        cli('active', '--check')

        write_ticket('active/01', 'typo')
        assert 'typo' in cli('active', '--board').stdout
        assert 'status' in cli('active', '--check', code=1).stderr
        cli('active', '--set', 'active/01', 'status=ready')
        cli('active', '--check')
        active.write_text(active.read_text().replace('status: ready\n', ''))
        assert '<missing>' in cli('active', '--board').stdout
        cli('active', '--set', 'active/01', 'status=ready')
        cli('active', '--check')

        write_ticket('other/01', 'implementing')
        assert json.loads(cli('active').stdout) == []
        write_ticket('other/01', 'implementing', touches='unrelated')
        assert json.loads(cli('active', '--max-live', '1').stdout) == []
        write_ticket('other/01', 'verifying', touches='unrelated', devices='ios')
        write_ticket('active/01', 'done', devices='ios')
        assert 'held by other/01' in cli('active', '--can-verify', 'active/01', code=1).stdout

        write_ticket('active/01', blocked='missing/01')
        assert 'does not exist' in cli('active', '--check', code=1).stderr
        write_ticket('active/01', blocked='other/01')
        write_ticket('other/01', blocked='active/01')
        assert 'dependency cycle' in cli('active', '--check', code=1).stderr
        duplicate = active.with_name('02-duplicate.md')
        duplicate.write_text(active.read_text())
        assert 'duplicate ticket' in cli('active', '--board', code=1).stderr
        duplicate.unlink()
        history.write_text('---\nstatus: implementing\ntouches: [runtime]\n---\n')
        assert 'missing ticket' in cli('active', '--board', code=1).stderr

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.root), *args], check=True,
                              capture_output=True, text=True).stdout.strip()

    def commit(self, message):
        self.git('-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-q', '--allow-empty', '-m', message)
        return self.git('rev-parse', 'HEAD')

    def write_report(self, base, branch=None):
        report = self.root / '.scratch/inline/reports/01.md'
        report.parent.mkdir(parents=True, exist_ok=True)
        branch_line = f'branch: {branch}\n' if branch else ''
        report.write_text(f'base: `{base}`\n{branch_line}## Implemented\n- [x] done\n')

    def test_acceptance_checks_the_branch_the_report_records(self):
        self.write_ticket('inline/01', 'implementing')
        base = self.commit('base')
        self.git('switch', '-q', '-c', 'feat/inline')
        # An inline ticket commits on the effort branch and records it.
        self.write_report(base, 'feat/inline')
        assert 'no commit past base on feat/inline' in self.cli('inline', '--accept', 'inline/01', code=1).stderr
        self.commit('ticket work')
        assert 'carry the evidence' in self.cli('inline', '--accept', 'inline/01').stdout
        # Without a recorded branch, the delegated ticket branch is still the one checked.
        self.write_report(base)
        assert 'feat/inline-01' in self.cli('inline', '--accept', 'inline/01', code=1).stderr

    def test_an_effort_run_on_main_is_delivered_from_main_and_releases_its_dependents(self):
        self.write_ticket('onmain/01', 'done')
        self.write_ticket('later/01', blocked='onmain/01', touches='docs')
        start = self.commit('start')
        head = self.commit('ticket work on main')
        review = self.root / '.scratch/onmain/reports/spec-review.md'
        review.parent.mkdir(parents=True, exist_ok=True)
        evidence = (f'---\neffort_branch: main\nreview_status: clean\ndocumentation_status: passed\n'
                    f'review_head: {head}\nreview_base: {start}\nreview_diff_base: {start}\n'
                    f'e2e_status: passed\ne2e_head: {head}\nreview_by: reviewer/1\ne2e_by: verifier/2\n---\n')
        review.write_text(evidence)
        self.cli('onmain', '--delivery')
        assert [t['ticket'] for t in json.loads(self.cli('later').stdout)] == ['later/01']
        # Without the recorded branch the gate still looks for feat/<slug>.
        review.write_text(evidence.replace('effort_branch: main\n', ''))
        self.cli('onmain', '--delivery', code=1)
        assert json.loads(self.cli('later').stdout) == []


if __name__ == '__main__':
    unittest.main()
