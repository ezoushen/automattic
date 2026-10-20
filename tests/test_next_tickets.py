#!/usr/bin/env python3
"""The local board's scheduling rules and its command line."""
import os
import json
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import time
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

    def test_a_recorded_branch_name_follows_git_rules_and_is_never_head_or_an_option(self):
        for name in ('-h', 'HEAD', 'feat/\x00bad', 'main~1', '', None):
            assert not nt.valid_branch_name(name), name
        for name in ('main', 'feat/x-01', 'feat/x+01', '_effort', 'feat/v1.2'):
            assert nt.valid_branch_name(name), name

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

    def write_ticket(self, name, status='ready', touches='runtime', blocked='', devices='', extra=''):
        slug, number = name.split('/')
        path = self.root / '.scratch' / slug / 'issues' / f'{number}-task.md'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f'---\nticket: {name}\nstatus: {status}\n'
                        f'blocked_by: [{blocked}]\ntouches: [{touches}]\ndevices: [{devices}]\n{extra}---\n')
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

    def write_report(self, base, branch=None, commits=(), body=''):
        report = self.root / '.scratch/inline/reports/01.md'
        report.parent.mkdir(parents=True, exist_ok=True)
        branch_line = f'branch: {branch}\n' if branch else ''
        listed = ''.join(f'- Commit: {sha}\n' for sha in commits)
        report.write_text(f'base: `{base}`\n{branch_line}## Implemented\n{listed}- [x] done\n{body}')

    def test_acceptance_checks_the_branch_the_report_records(self):
        self.write_ticket('inline/01', 'implementing')
        base = self.commit('base')
        self.git('switch', '-q', '-c', 'feat/inline')
        self.write_report(base, 'feat/inline')
        assert 'no commit past base on feat/inline' in self.cli('inline', '--accept', 'inline/01', code=1).stderr
        work = self.commit('ticket work')
        self.write_report(base, 'feat/inline', [work])
        assert 'carry the evidence' in self.cli('inline', '--accept', 'inline/01').stdout
        self.write_report(base)
        assert 'feat/inline-01' in self.cli('inline', '--accept', 'inline/01', code=1).stderr
        self.write_report(base, body=f'Checked branch: feat/inline\nbranch: feat/inline\n')
        assert 'feat/inline-01' in self.cli('inline', '--accept', 'inline/01', code=1).stderr

    def test_a_shared_effort_branch_counts_only_the_commits_the_report_lists(self):
        self.write_ticket('inline/01', 'implementing')
        base = self.commit('base')
        self.git('switch', '-q', '-c', 'feat/inline')
        other = self.commit('another ticket merged here')
        self.write_report(base, 'feat/inline')
        assert 'no listed commit' in self.cli('inline', '--accept', 'inline/01', code=1).stderr
        self.write_report(base, 'feat/inline', [base])
        assert 'no listed commit' in self.cli('inline', '--accept', 'inline/01', code=1).stderr
        self.write_report(base, 'feat/inline', [other])
        self.cli('inline', '--accept', 'inline/01')
        self.write_report(base, 'feat/inline', body=f'- Evidence: reports/evidence/01/1/{other}/\n')
        assert 'no listed commit' in self.cli('inline', '--accept', 'inline/01', code=1).stderr
        self.git('switch', '-q', 'main')
        off_branch = self.commit('on main, not on the effort branch')
        self.git('switch', '-q', '-c', 'side', 'feat/inline')
        unmerged = self.commit('past base but never merged into the effort branch')
        self.git('switch', '-q', 'feat/inline')
        self.commit('later work on the effort branch')
        for sha in (off_branch, base, unmerged):
            self.write_report(other, 'feat/inline', [sha])
            assert 'no listed commit' in self.cli('inline', '--accept', 'inline/01', code=1).stderr, sha

    def commit_gitignore(self):
        # The dispatch convention: `.scratch/` and `.worktrees/` are ignored; `build.log` stands for build output.
        (self.root / '.gitignore').write_text('.scratch/\n.worktrees/\nbuild.log\n')
        self.git('add', '.gitignore')

    def record_measurement(self, command, baseline=100, direction='higher', metric='recall', **extra):
        entry = {'name': 'recall tool', 'command': command, 'metric': metric,
                 'baseline': baseline, 'direction': direction, **extra}
        (self.root / '.scratch/inline/measurements.json').write_text(json.dumps([entry]))

    def measured_ticket(self, command, extra='', **entry):
        """inline/01 is finished on feat/inline, checked out in the main checkout, and its effort records one measurement."""
        self.write_ticket('inline/01', 'implementing', extra=extra)
        self.commit_gitignore()
        base = self.commit('base')
        self.git('switch', '-q', '-c', 'feat/inline')
        self.record_measurement(command, **entry)
        self.write_report(base, 'feat/inline', [self.commit('ticket work')])
        return base

    def test_a_metric_worse_than_its_baseline_refuses_acceptance_and_names_it(self):
        # A measured regression is a refusal even when the report and branch are structurally fine.
        self.measured_ticket('echo recall 83')
        refused = self.cli('inline', '--accept', 'inline/01', code=1).stderr
        assert refused == ("inline/01: measurement 'recall tool': recall is 83, worse than baseline 100 "
                           "(higher is better)\n"), refused
        for command in ('echo recall 100', 'echo recall 101.5'):
            self.record_measurement(command)
            assert 'carry the evidence' in self.cli('inline', '--accept', 'inline/01').stdout, command

    def test_a_metric_that_is_better_lower_is_worse_when_it_rises(self):
        self.measured_ticket('echo latency 120', baseline=100, direction='lower', metric='latency')
        refused = self.cli('inline', '--accept', 'inline/01', code=1).stderr
        assert refused == ("inline/01: measurement 'recall tool': latency is 120, worse than baseline 100 "
                           "(lower is better)\n"), refused
        for command in ('echo latency 100', 'echo latency 90'):
            self.record_measurement(command, direction='lower', metric='latency')
            assert 'carry the evidence' in self.cli('inline', '--accept', 'inline/01').stdout, command

    def test_a_metric_the_command_does_not_print_refuses_acceptance(self):
        # No `recall <number>` line means nothing was measured; a longer metric name or a comment is not that line.
        self.measured_ticket('true')
        for command in ('true', 'echo recall_t4 100', 'echo "# recall 100"'):
            self.record_measurement(command)
            refused = self.cli('inline', '--accept', 'inline/01', code=1).stderr
            assert refused == ("inline/01: measurement 'recall tool': recall has no value "
                               "(no `recall <number>` line in its output); baseline 100\n"), (command, refused)

    def test_a_metric_that_is_not_a_number_refuses_acceptance(self):
        # `nan` is the dangerous one: it compares false against every baseline, so it would read as no regression.
        self.measured_ticket('true')
        for text in ('high', 'nan', 'inf', '83%', '83 percent', ''):
            self.record_measurement(f'echo recall {text}')
            refused = self.cli('inline', '--accept', 'inline/01', code=1).stderr
            assert refused == (f"inline/01: measurement 'recall tool': recall is {text!r}, not a number; "
                               "baseline 100\n"), (text, refused)

    def test_a_measurement_command_that_fails_refuses_acceptance_even_after_printing_a_good_value(self):
        self.measured_ticket('true')
        for command, status in (('echo recall 100; exit 3', 3), ('no-such-measurement-tool-4f2a', 127)):
            self.record_measurement(command)
            refused = self.cli('inline', '--accept', 'inline/01', code=1).stderr
            assert refused == (f"inline/01: measurement 'recall tool': recall has no value "
                               f"(its command exited {status}); baseline 100\n"), (command, refused)

    def test_a_measurements_file_that_cannot_be_read_as_specified_refuses_acceptance(self):
        # An unreadable standing measurement is a gate that cannot run, never a pass.
        self.measured_ticket('true')
        path = self.root / '.scratch/inline/measurements.json'
        good = {'name': 'recall tool', 'command': 'echo recall 100', 'metric': 'recall',
                'baseline': 100, 'direction': 'higher'}
        reason = 'entry 1 needs a name, command, metric without spaces, numeric baseline and a direction of higher or lower'
        bad = [('not json', 'not valid JSON'), (json.dumps(good), 'not a JSON array of entries'),
               (json.dumps([1]), reason), (json.dumps([{k: v for k, v in good.items() if k != 'command'}]), reason)]
        bad += [(json.dumps([{**good, key: value}]), reason) for key, value in (
            ('baseline', '100'), ('baseline', True), ('baseline', float('nan')), ('direction', 'up'),
            ('metric', 'recall tool'), ('command', ''))]
        for text, why in bad:
            path.write_text(text)
            refused = self.cli('inline', '--accept', 'inline/01', code=1).stderr
            assert refused == f"inline/01: measurements.json is unusable: {why}\n", (text, refused)
        path.write_text(json.dumps([good]))
        self.cli('inline', '--accept', 'inline/01')

    def write_ledger(self):
        ledger = self.root / '.scratch/inline/ledger.md'
        ledger.parent.mkdir(parents=True, exist_ok=True)
        ledger.write_text('# inline: ledger\n\n| # | Decision | Hinge | Rejected |\n|---|---|---|---|\n'
                          '| A1 (agent) | Cut the fixture | the tool | none |\n'
                          '| U3 (user) | The SSN rule may lower recall to 80 | "go ahead" | keep 100 |\n'
                          '| U12 (user) | Keep the recall tool | quoted | drop it |\n')

    def test_a_cited_allowance_accepts_a_regression_up_to_its_bound_and_no_further(self):
        # `allows` is the worst value the ticket tolerates, inclusive, in the metric's own direction.
        self.write_ledger()
        self.measured_ticket('echo recall 83', extra='allows: recall 80\nallows_source: U3\n')
        accepted = self.cli('inline', '--accept', 'inline/01').stdout
        assert accepted == ("inline/01: measurement 'recall tool': recall is 83, worse than baseline 100; "
                            "allowed down to 80 by ledger row U3\n"
                            "inline/01: report and branch carry the evidence; judge the content now\n"), accepted
        self.record_measurement('echo recall 80')
        self.cli('inline', '--accept', 'inline/01')
        self.record_measurement('echo recall 79')
        refused = self.cli('inline', '--accept', 'inline/01', code=1).stderr
        assert refused == ("inline/01: measurement 'recall tool': recall is 79, worse than baseline 100 "
                           "and past the bound 80 that ledger row U3 allows\n"), refused
        self.write_ticket('inline/01', 'implementing', extra='allows: latency 130\nallows_source: U3\n')
        self.record_measurement('echo latency 130', direction='lower', metric='latency')
        assert 'allowed up to 130' in self.cli('inline', '--accept', 'inline/01').stdout
        self.record_measurement('echo latency 131', direction='lower', metric='latency')
        assert 'past the bound 130' in self.cli('inline', '--accept', 'inline/01', code=1).stderr

    def test_an_allowance_covers_only_the_metric_it_names(self):
        self.write_ledger()
        self.measured_ticket('echo recall 83')
        for allows in ('latency 80', 'recall_t4 80'):
            self.write_ticket('inline/01', 'implementing', extra=f'allows: {allows}\nallows_source: U3\n')
            refused = self.cli('inline', '--accept', 'inline/01', code=1).stderr
            assert refused == ("inline/01: measurement 'recall tool': recall is 83, worse than baseline 100 "
                               "(higher is better)\n"), (allows, refused)

    def refusal(self, ticket='inline/01'):
        return self.cli('inline', '--accept', ticket, code=1).stderr

    def test_an_allowance_without_a_citation_is_refused(self):
        # The ticket author cannot excuse a regression alone; the authority is a recorded ledger row.
        self.write_ledger()
        expected = "inline/01: allows: recall 80 needs allows_source naming a row of .scratch/inline/ledger.md\n"
        self.measured_ticket('echo recall 83', extra='allows: recall 80\n')
        assert self.refusal() == expected, self.refusal()
        self.write_ticket('inline/01', 'implementing', extra='allows: recall 80\nallows_source:\n')
        assert self.refusal() == expected, self.refusal()
        self.record_measurement('echo recall 100')  # an uncited allowance is refused even when no regression needs it
        assert self.refusal() == expected, self.refusal()

    def test_an_allowance_citing_a_row_the_ledger_does_not_have_is_refused(self):
        # Only a row id (the first cell of a ledger table row) is a citation: not a prefix, a header or a missing file.
        self.measured_ticket('echo recall 83', extra='allows: recall 80\nallows_source: U3\n')
        expected = "inline/01: allows_source {} is not a row of .scratch/inline/ledger.md\n"
        assert self.refusal() == expected.format('U3'), self.refusal()  # no ledger file at all
        self.write_ledger()
        self.cli('inline', '--accept', 'inline/01')
        for cited in ('U9', 'U', 'U1', 'U30', 'u3', '#', '---', 'Decision', 'A1)'):
            self.write_ticket('inline/01', 'implementing', extra=f'allows: recall 80\nallows_source: {cited}\n')
            assert self.refusal() == expected.format(cited), (cited, self.refusal())
        self.write_ticket('inline/01', 'implementing', extra='allows: recall 80\nallows_source: A1\n')
        self.cli('inline', '--accept', 'inline/01')

    def test_an_allowance_that_does_not_read_metric_then_numeric_bound_is_refused(self):
        self.write_ledger()
        self.measured_ticket('echo recall 100')
        for value in ('recall', 'recall high', 'recall 80 90', 'recall nan', ''):
            self.write_ticket('inline/01', 'implementing', extra=f'allows: {value}\nallows_source: U3\n')
            assert self.refusal() == (f"inline/01: allows {value!r} must read `<metric> <bound>` with a numeric bound\n"), \
                (value, self.refusal())

    def test_an_effort_without_a_measurements_file_accepts_exactly_as_before(self):
        # No file, no gate: another effort's file and this ticket's own `allows` line change nothing here.
        self.measured_ticket('echo recall 1', extra='allows: recall 80\n')
        (self.root / '.scratch/inline/measurements.json').rename(self.root / '.scratch/inline/measurements.old')
        other = self.root / '.scratch/other/measurements.json'
        other.parent.mkdir(parents=True)
        other.write_text(json.dumps([{'name': 'x', 'command': 'exit 1', 'metric': 'recall',
                                      'baseline': 100, 'direction': 'higher'}]))
        accepted = self.cli('inline', '--accept', 'inline/01').stdout
        assert accepted == "inline/01: report and branch carry the evidence; judge the content now\n", accepted

    def test_a_measurement_that_outruns_its_timeout_is_killed_with_its_children_and_refused(self):
        # The shell is not the only process to stop: a child it started must not outlive the refusal.
        scratch = Path(tempfile.mkdtemp(prefix='automattic-pid-'))
        self.addCleanup(shutil.rmtree, scratch, True)
        pidfile = scratch / 'pid'
        self.measured_ticket(f'sleep 15 >/dev/null 2>&1 & echo $! > {shlex.quote(str(pidfile))}; wait', timeout_seconds=1)
        started = time.monotonic()
        refused = self.refusal()
        assert time.monotonic() - started < 10, 'acceptance waited for the command'
        assert refused == ("inline/01: measurement 'recall tool': recall has no value "
                           "(its command timed out after 1 s); baseline 100\n"), refused
        child = int(pidfile.read_text())
        for _ in range(50):
            try:
                os.kill(child, 0)
            except ProcessLookupError:
                return
            time.sleep(0.1)
        os.kill(child, signal.SIGKILL)
        self.fail(f'the timed-out measurement left its child {child} running')

    def test_a_timeout_that_is_not_a_positive_number_makes_the_measurements_file_unusable(self):
        self.measured_ticket('echo recall 100')
        for value in (0, -1, '5', True, float('nan'), float('inf')):
            self.record_measurement('echo recall 100', timeout_seconds=value)
            assert self.refusal() == ("inline/01: measurements.json is unusable: "
                                      "entry 1 needs timeout_seconds to be a positive number\n"), (value, self.refusal())
        self.record_measurement('echo recall 100', timeout_seconds=0.5)
        self.cli('inline', '--accept', 'inline/01')

    def test_a_measurement_without_timeout_seconds_is_not_cut_short(self):
        self.measured_ticket('sleep 2; echo recall 100')
        self.cli('inline', '--accept', 'inline/01')

    def test_a_ticket_worktree_with_uncommitted_changes_is_refused_naming_them(self):
        # The committed head regresses (83); an uncommitted edit would hide that, so the measurement would not be of the head.
        self.ticket_worktree(83)
        worktree = self.root / '.worktrees/inline-01'
        dirty = "inline/01: branch feat/inline-01 has uncommitted changes ({}); a measurement of it would not be of the ticket head\n"
        (worktree / 'score.txt').write_text('100\n')
        assert self.refusal() == dirty.format('score.txt'), self.refusal()
        self.git('-C', str(worktree), 'add', 'score.txt')
        assert self.refusal() == dirty.format('score.txt'), self.refusal()
        (worktree / 'notes.txt').write_text('scratch\n')
        assert self.refusal() == dirty.format('notes.txt, score.txt'), self.refusal()
        self.git('-C', str(worktree), 'reset', '-q', '--hard')
        assert self.refusal() == dirty.format('notes.txt'), self.refusal()
        (worktree / 'notes.txt').unlink()
        (worktree / 'build.log').write_text('ignored build output\n')
        assert self.refusal() == ("inline/01: measurement 'recall tool': recall is 83, worse than baseline 100 "
                                  "(higher is better)\n"), self.refusal()

    def test_a_main_checkout_holding_the_ticket_branch_with_a_stray_file_is_refused(self):
        self.measured_ticket('echo recall 100')
        self.cli('inline', '--accept', 'inline/01')
        (self.root / 'stray.txt').write_text('left behind\n')
        assert self.refusal() == ("inline/01: branch feat/inline has uncommitted changes (stray.txt); "
                                  "a measurement of it would not be of the ticket head\n"), self.refusal()

    def test_a_worktree_whose_git_status_cannot_be_read_is_refused(self):
        self.ticket_worktree(100)
        self.cli('inline', '--accept', 'inline/01')
        (self.root / '.worktrees/inline-01/.git').write_text('gitdir: /nonexistent\n')
        refused = self.refusal()
        assert refused.startswith("inline/01: branch feat/inline-01 has a worktree whose git status cannot be read: "), refused

    def ticket_worktree(self, score):
        """inline/01 on feat/inline-01 in its own worktree; main keeps scoring 100 and the ticket branch scores `score`."""
        self.write_ticket('inline/01', 'implementing')
        (self.root / 'score.txt').write_text('100\n')
        self.git('add', 'score.txt')
        self.commit_gitignore()
        base = self.commit('base with the recall score')
        worktree = self.root / '.worktrees/inline-01'
        self.git('worktree', 'add', '-q', '-b', 'feat/inline-01', str(worktree), base)
        (worktree / 'score.txt').write_text(f'{score}\n')
        self.git('-C', str(worktree), '-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-q', '--allow-empty', '-am', 'ticket work')
        work = self.git('-C', str(worktree), 'rev-parse', 'HEAD')
        self.record_measurement('echo recall $(cat score.txt)')
        self.write_report(base, 'feat/inline-01', [work])

    def test_the_measurement_runs_in_the_worktree_that_holds_the_ticket_head(self):
        # Main still scores 100; only the ticket worktree, at the ticket head, scores 83.
        self.ticket_worktree(83)
        refused = self.cli('inline', '--accept', 'inline/01', code=1).stderr
        assert refused == ("inline/01: measurement 'recall tool': recall is 83, worse than baseline 100 "
                           "(higher is better)\n"), refused

    def test_a_ticket_branch_checked_out_nowhere_cannot_be_measured_and_is_refused(self):
        self.ticket_worktree(100)
        self.cli('inline', '--accept', 'inline/01')
        self.git('worktree', 'remove', '--force', '.worktrees/inline-01')
        refused = self.cli('inline', '--accept', 'inline/01', code=1).stderr
        assert refused == "inline/01: branch feat/inline-01 is checked out in no worktree; its head cannot be measured\n", refused

    def test_a_recorded_branch_must_name_an_existing_branch(self):
        self.write_ticket('inline/01', 'implementing')
        base = self.commit('base')
        self.git('switch', '-q', '-c', 'feat/inline')
        work = self.commit('ticket work')
        for value in ('HEAD', work, 'feat/inline~1', '-h', 'feat/missing'):
            self.write_report(base, value, [work])
            assert 'not an existing branch' in self.cli('inline', '--accept', 'inline/01', code=1).stderr, value
        for name in ('feat/x+01', '_effort', 'feat/v1.2'):
            self.git('branch', name)
            self.write_report(base, name, [work])
            self.cli('inline', '--accept', 'inline/01')

    def deliver(self, slug, branch, start, head):
        review = self.root / f'.scratch/{slug}/reports/spec-review.md'
        review.parent.mkdir(parents=True, exist_ok=True)
        evidence = (f'---\neffort_branch: {branch}\nreview_status: clean\ndocumentation_status: passed\n'
                    f'review_head: {head}\nreview_base: {start}\nreview_diff_base: {start}\n'
                    f'e2e_status: passed\ne2e_head: {head}\nreview_by: reviewer/1\ne2e_by: verifier/2\n---\n')
        review.write_text(evidence)
        return review, evidence

    def ready_names(self, slug):
        return [t['ticket'] for t in json.loads(self.cli(slug).stdout)]

    def test_an_effort_run_on_main_is_delivered_from_main_and_releases_its_dependents(self):
        self.write_ticket('onmain/01', 'done')
        self.write_ticket('later/01', blocked='onmain/01', touches='docs')
        self.write_ticket('later/02', blocked='onmain/01', touches='tests')
        start = self.commit('start')
        head = self.commit('ticket work on main')
        review, evidence = self.deliver('onmain', 'main', start, head)
        self.cli('onmain', '--delivery')
        assert self.ready_names('later') == ['later/01', 'later/02']
        self.git('branch', 'feat/later', start)
        self.deliver('later', 'main', start, start)
        self.commit('later/01 lands on main')
        self.cli('onmain', '--delivery')
        assert self.ready_names('later') == ['later/01', 'later/02']
        review.write_text(evidence.replace('effort_branch: main\n', ''))
        self.cli('onmain', '--delivery', code=1)
        assert self.ready_names('later') == []
        review.write_text(evidence.replace('effort_branch: main', 'effort_branch: main~1'))
        self.cli('onmain', '--delivery', code=1)
        review.write_text(evidence)
        later_review, later_evidence = self.deliver('later', 'main', start, start)
        later_review.write_text(later_evidence.replace('effort_branch: main', 'effort_branch: main~1'))
        assert self.ready_names('later') == []
        later_review.write_text(later_evidence)
        unreviewed = review.read_text().replace('effort_branch: main~1', 'effort_branch: main')
        review.write_text(unreviewed.replace(head, start))
        self.cli('onmain', '--delivery', code=1)

if __name__ == '__main__':
    unittest.main()
