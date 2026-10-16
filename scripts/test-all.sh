#!/usr/bin/env bash
# Run every tests/test_*.py regression script in parallel.
#
#   scripts/test-all.sh
#
# Uses the plugin environment's .venv (the main checkout's, from a worktree) unless
# PYTHON names another interpreter. Prints each failing script's output tail and
# exits 1 when any script fails. Native checks (AUTOMATTIC_NATIVE=1) stay opt-in; see the README.
set -uo pipefail
# A Git hook exports these; the tests' temporary repositories must not inherit them.
unset GIT_DIR GIT_INDEX_FILE GIT_WORK_TREE GIT_PREFIX GIT_OBJECT_DIRECTORY GIT_COMMON_DIR
root=$(cd "$(dirname "$0")/.." && pwd)
main=$(cd "$root" && cd "$(git rev-parse --git-common-dir)/.." && pwd)
python=${PYTHON:-}
for candidate in "$root/.venv/bin/python" "$main/.venv/bin/python" python3; do
  [ -n "$python" ] && break
  command -v "$candidate" >/dev/null && python=$candidate
done
logs=$(mktemp -d)
trap 'rm -rf "$logs"' EXIT
jobs=()
for test in "$root"/tests/test_*.py; do
  name=$(basename "$test" .py)
  "$python" -B "$test" >"$logs/$name.log" 2>&1 &
  jobs+=("$!:$name")
done
failed=0
for job in "${jobs[@]}"; do
  if ! wait "${job%%:*}"; then
    failed=1
    echo "FAIL ${job#*:}"
    tail -n 20 "$logs/${job#*:}.log"
  fi
done
[ "$failed" = 0 ] && echo "${#jobs[@]} regression scripts passed ($python)"
exit "$failed"
