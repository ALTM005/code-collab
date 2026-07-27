"""
Attack: recursively spawn child processes without bound (a classic fork
bomb), to exhaust the process table.

Correct containment: --pids-limit stops this well before it can affect the
container's host. os.fork() should start raising OSError once the limit is
hit; the container finishes within the timeout, never hangs, and the host's
process table is never at risk.
"""
import os

spawned = 0
try:
    for _ in range(100000):
        pid = os.fork()
        if pid == 0:
            os._exit(0)
        spawned += 1
except OSError as e:
    print(f"CONTAINED: fork blocked after spawning {spawned} children -> {type(e).__name__}: {e}")
else:
    print(f"NOT CONTAINED: spawned all {spawned} children without being blocked")
