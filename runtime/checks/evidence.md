# Retain evidence

Assign an absolute evidence directory outside disposable worktrees, normally beside
the main-checkout report under `reports/evidence/<assignment>/<attempt>/<head>/`.
Each execution gets its own log and result paths. Preserve failed attempts alongside
the final pass; shared names such as a global `gates.log` can overwrite sibling proof.

Copy the logs, test XML, screenshots, ABI comparisons and other files needed for the
acceptance claims out of ignored build/temp directories while they still exist.
Retain the original base/head, exact command, exit code, execution time and relevant
toolchain/input identity in the report. Preserve both baseline and candidate files
for before/after claims. Compare source/copy hashes and update report links to the
retained copies; a symlink into the retiring checkout is not a retained copy.
Keep only the files needed to support the claims, not a second build tree.
This policy also applies to cleanup outside worktrees or by file size/type. Preserve
the minimum original recordings/traces needed for audit and reanalysis, or sufficient
exports with explicit limits. Verify downstream references before deletion. A derived
CSV alone does not preserve every claim made from a video or trace; any agreed loss
of reanalysis stays explicit in the report rather than leaving broken proof links.

Acceptance requires the retained artifacts to exist and support the claimed result.
A checked box, reported pass or surviving Git commit cannot replace missing output.
Recover existing evidence first; rerun only the missing or invalidated checks when
needed. The lifecycle owner applies
[worktree retirement](../resources/retire-worktree.md) after the
remaining gates and verifies that removal cannot break these evidence links.
