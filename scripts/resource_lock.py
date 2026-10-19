#!/usr/bin/env python3
"""Optional mutex for commands sharing a verified local resource.

usage: resource_lock.py <command> [args...]

Use only when the project's commands need exclusive access to a local build lane,
device or mutable output. Set RESOURCE_LOCK to that shared resource's lock path.
The /tmp/resource.lock default serialises all callers on this host; it is not an
automatic machine-load limit. Never wrap remote queue submissions or waits: the
remote scheduler owns those resources. A held lock is another command, not a hang.
Set RESOURCE_LOCK_TIMEOUT (seconds, default 3600) to bound the wait.

Once acquired, the command replaces this process and inherits the lock descriptor.
Inherited copies can retain the lock in descendants, so reconcile those jobs before
releasing the resource; terminating a launcher alone does not prove the lock is free.
"""
import fcntl
import os
import sys
import time


def main(argv):
    if not argv:
        print(f'usage: {sys.argv[0]} <command> [args...]', file=sys.stderr)
        return 2
    lock = os.environ.get('RESOURCE_LOCK', '/tmp/resource.lock')
    timeout = float(os.environ.get('RESOURCE_LOCK_TIMEOUT', '3600'))
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
                sys.exit(f'resource-lock: still held after {timeout:.0f}s; another command is stuck')
            if waited - last >= 60:
                last = waited
                print(f'resource-lock: waiting ({waited:.0f}s)', file=sys.stderr)
            time.sleep(3)
    os.ftruncate(fd, 0)
    os.write(fd, f'{os.getpid()} {" ".join(argv)}\n'.encode())
    # Hand the locked descriptor to the command: the lock now dies with the command, not before.
    os.set_inheritable(fd, True)
    try:
        os.execvp(argv[0], argv)
    except FileNotFoundError:
        sys.exit(f'resource-lock: {argv[0]}: not found')


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
