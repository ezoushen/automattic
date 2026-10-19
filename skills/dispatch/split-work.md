# Split oversized work

A step of [dispatch](SKILL.md) setup and its [iteration](iteration.md). The board's
[overall scope](../../runtime/board/scope.md) rules own inheritance and parent completion.

Selected work too large for one worker is split by the board's
[slicing rules](../../runtime/board/slicing.md), each child written with a story and
Given/When/Then criteria carrying a `Verify` line in the project's ticket convention,
within native permissions and existing tracker-write authorization.
Reuse existing child issues and dependencies; dispatch ready children rather than
refining an already executable breakdown again. New children wait for the user's check like any new cut.
