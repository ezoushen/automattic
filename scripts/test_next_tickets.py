#!/usr/bin/env python3
"""Self-check for the loop's scheduling rules. Run: python3 scripts/test_next_tickets.py"""
import os
import json
import subprocess
import sys
import tempfile
from pathlib import Path

os.environ.pop("TICKET_PRIORITY", None)
os.environ.pop("MAX_LIVE", None)

SCRIPT = Path(__file__).with_name("next-tickets.py")
nt = {"__file__": str(SCRIPT)}
exec(compile(SCRIPT.read_text().replace('if __name__ == "__main__":\n    main(sys.argv[1:])', ""),
             str(SCRIPT), "exec"), nt)
ready, can_verify, counts, last, report_problems, MAX_LIVE = (
    nt["ready"], nt["can_verify"], nt["counts"], nt["last"], nt["report_problems"], nt["MAX_LIVE"])


def ticket(name, status, touches, devices=(), blocked=()):
    return {"ticket": name, "status": status, "touches": list(touches), "devices": list(devices),
            "blocked_by": list(blocked), "model": "sonnet", "path": "x"}


def names(tickets):
    return [fm["ticket"] for fm in ready(tickets)]


# A device is held only by the `verifying` stage that boots it, so an unrelated
# ticket may start work on a device it will not touch until its own E2E run.
verifying_on_ios = {
    "apple-native-edge/01": ticket("apple-native-edge/01", "verifying", ["apple"], ["ios"]),
    "runtime-instance/02": ticket("runtime-instance/02", "ready", ["runtime"], ["android", "ios"]),
}
assert names(verifying_on_ios) == ["runtime-instance/02"], names(verifying_on_ios)

# ...but it must not enter `verifying` while the holder is still there.
assert can_verify(verifying_on_ios, "runtime-instance/02") is False
verifying_on_ios["apple-native-edge/01"]["status"] = "done"
assert can_verify(verifying_on_ios, "runtime-instance/02") is True

# An area stays locked for a ticket's whole life: two live tickets never share a hot file.
same_area = {"a/01": ticket("a/01", "implementing", ["runtime"]),
             "b/01": ticket("b/01", "ready", ["runtime"])}
assert names(same_area) == [], names(same_area)

# Blockers must be done, and the live cap still holds.
blocked = {"a/01": ticket("a/01", "reviewing", ["apple"]),
           "b/01": ticket("b/01", "ready", ["runtime"], blocked=["a/01"])}
assert names(blocked) == [], names(blocked)
assert len(ready({f"s{i}/01": ticket(f"s{i}/01", "ready", [f"area{i}"]) for i in range(MAX_LIVE + 2)})) == MAX_LIVE

# Two tickets of one spec may run at once when their areas differ: each live
# ticket gets its own worktree.
same_spec_parallel = {"s/01": ticket("s/01", "implementing", ["generator"]),
                      "s/02": ticket("s/02", "ready", ["docs"]),
                      "t/01": ticket("t/01", "ready", ["apple"])}
assert names(same_spec_parallel) == ["s/02", "t/01"], names(same_spec_parallel)

# The live cap is checked before admitting a candidate, not after: a full board
# must hand out nothing at all.
full = {f"s{i}/01": ticket(f"s{i}/01", "implementing", [f"area{i}"]) for i in range(MAX_LIVE)}
full["spare/01"] = ticket("spare/01", "ready", ["spare"])
assert names(full) == [], names(full)

# A spec's E2E needs every device its tickets name, not just the last ticket's.
spec_union = {"u/01": ticket("u/01", "done", ["a"], ["android"]),
              "u/02": ticket("u/02", "verifying", ["b"], []),
              "v/01": ticket("v/01", "done", ["c"], ["android"])}
assert can_verify(spec_union, "v/01") is False

# The count line names every bucket, zeros included, so the goal evaluator can read "0 ready".
assert counts({"a/01": ticket("a/01", "done", ["x"])}) == "1 done · 0 blocked · 0 ready · 0 live", counts({"a/01": ticket("a/01", "done", ["x"])})

# The spec lane waits for every sibling, and a blocked sibling holds it: an incomplete spec is never reviewed.
lane = {"w/01": ticket("w/01", "done", ["a"]), "w/02": ticket("w/02", "blocked", ["b"]),
        "w/03": ticket("w/03", "implementing", ["c"])}
assert last(lane, "w/03") is False
lane["w/02"]["status"] = "done"
assert last(lane, "w/03") is True

# The accept check is structural and deterministic: a report without base, section or checkboxes is not evidence.
good = "base: `" + "a" * 40 + "`\n## Implemented\n- [x] done\n"
assert report_problems(good) == [], report_problems(good)
assert len(report_problems("# empty\n")) == 3

with tempfile.TemporaryDirectory(prefix='automattic-board-') as directory:
    root = Path(directory)
    subprocess.run(['git', 'init', '-q', '-b', 'main', str(root)], check=True)

    def write_ticket(name, status='ready', touches='runtime', blocked='', devices=''):
        slug, number = name.split('/')
        path = root / '.scratch' / slug / 'issues' / f'{number}-task.md'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f'---\nticket: {name}\nstatus: {status}\n'
                        f'blocked_by: [{blocked}]\ntouches: [{touches}]\ndevices: [{devices}]\n---\n')
        return path

    def cli(*args, code=0):
        result = subprocess.run([sys.executable, '-B', str(SCRIPT), '--repo', str(root), *args],
                                capture_output=True, text=True)
        assert result.returncode == code, result.stdout + result.stderr
        return result

    active = write_ticket('active/01')
    history = root / '.scratch/history/issues/old.md'
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

    other = write_ticket('other/01', 'implementing')
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

print("next-tickets scheduling rules: ok")
sys.exit(0)
