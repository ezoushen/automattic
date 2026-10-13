#!/usr/bin/env bash
# Optional mutex for commands sharing a verified local resource.
#
#   scripts/build-lock.sh <your build command>
#
# Use only when the project's commands need exclusive access to a local build
# lane or mutable output. Set BUILD_LOCK to that shared resource's lock path.
# The legacy /tmp/build.lock default serialises all callers on this host; it is
# not an automatic machine-load limit. Never wrap remote queue submissions or
# waits: the remote scheduler owns those resources. A held lock is another command,
# not a hang. Set BUILD_LOCK_TIMEOUT (seconds, default 3600) to bound the wait.
#
# Once acquired, execvp passes the flock fd to the command. Inherited copies can
# retain the lock in descendants, so reconcile those jobs before releasing the
# resource; terminating a launcher alone does not prove that the lock is free.
set -euo pipefail
[ $# -gt 0 ] || { echo "usage: $0 <command> [args...]" >&2; exit 2; }
LOCK="${BUILD_LOCK:-/tmp/build.lock}"
exec python3 - "$LOCK" "${BUILD_LOCK_TIMEOUT:-3600}" "$@" <<'PY_EOF'
import fcntl, os, sys, time
lock, timeout, cmd = sys.argv[1], float(sys.argv[2]), sys.argv[3:]
fd = os.open(lock, os.O_CREAT | os.O_RDWR, 0o666)
start = time.time()
last = -60
while True:
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        break
    except BlockingIOError:
        waited = time.time() - start
        if waited > timeout:
            sys.exit(f"build-lock: still held after {timeout:.0f}s; another build is stuck")
        if waited - last >= 60:
            last = waited
            print(f"build-lock: waiting ({waited:.0f}s)", file=sys.stderr)
        time.sleep(3)
os.ftruncate(fd, 0)
os.write(fd, f"{os.getpid()} {' '.join(cmd)}\n".encode())
# Hand the locked fd to the build: the lock now dies with the build, not before.
os.set_inheritable(fd, True)
try:
    os.execvp(cmd[0], cmd)
except FileNotFoundError:
    sys.exit(f"build-lock: {cmd[0]}: not found")
PY_EOF
