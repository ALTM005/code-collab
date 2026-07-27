# Adversarial test suite for the Docker sandbox

Eleven malicious programs, one per attack, run manually against the real sandbox to confirm containment actually holds — not just that the code *looks* like it should. Every attack below has been run at least once against this host and passed; see `SANDBOX_BRIEF.md` at the repo root for the isolation controls these are exercising.

**Never run a file in `attacks/` directly on your host** (`python attacks/whatever.py`). Several of these (fork bomb, memory exhaustion, disk fill) will do to *your machine* exactly what they're supposed to fail to do inside the sandbox. Only run them through `run_attacks.py`, which feeds each file's source into `sandbox.run_sandboxed(...)` — it never executes anything locally.

## Running it

```bash
cd backend  # needs backend/.venv (docker-py) and a running Docker daemon
.venv/bin/python ../adversarial-tests/run_attacks.py                        # all 11
.venv/bin/python ../adversarial-tests/run_attacks.py 02_memory_exhaustion.py # just one
```

Each run prints the sandbox's own observed result (`failure`, `exit_code`, `truncated`) plus the attack script's own self-report, and a PASS/FAIL verdict per attack based on what "correctly contained" means for that specific one — the verdict is always checked against the sandbox's result object, never just the attack's stdout, because a fully-uncontained attack might get killed before it ever gets a chance to print anything.

## The attacks

| File | Tries to | Correct containment |
|---|---|---|
| `01_fork_bomb.py` | Fork children in an unbounded loop to exhaust the process table. | `--pids-limit` stops it (observed: blocked after ~63 children); container finishes normally, host process table unaffected. |
| `02_memory_exhaustion.py` | Allocate + touch 800MB against a 512MB cap. | Killed by the kernel's cgroup OOM killer; `failure=oom_killed`, read from `State.OOMKilled`, not guessed from the exit code. |
| `03_disk_fill_tmp.py` | Write ~1GB into `/tmp`. | Blocked well before completion by the smaller of the tmpfs size (16MB) or the per-file `fsize` ulimit (10MB) — observed: stopped at exactly 10,485,760 bytes, `EFBIG`. Never touches the host's real disk; `/tmp` is an in-memory tmpfs, not a bind mount. |
| `04_unbounded_stdout.py` | Print forever. | Killed once accumulated output exceeds the 64KB cap; `truncated=True`, bounded output size, not gigabytes written to a host-side log file. |
| `05_infinite_loop_silent.py` | Loop forever with **zero** output. | Killed by the host-enforced deadline anyway — the timeout doesn't depend on the container producing output; `failure=timeout`, total wall time ≈ 10s, not indefinite. |
| `06_outbound_network.py` | Open a raw TCP connection and do a DNS lookup. | Both fail immediately (`Network unreachable` / DNS failure) — `--network none` means no network namespace at all, not even loopback. |
| `07_read_host_passwd.py` | Read `/etc/passwd` and probe for any host-mounted path. | The container's *own* `/etc/passwd` is readable (expected — every container has one, it's not this Mac's real user list); no host-mounted path exists. `/proc/mounts` will show Docker's own plumbing (overlay rootfs, a `/sandbox` mount, `/etc/hosts`/`/etc/resolv.conf` sourced from the Docker Desktop VM's own disk) — none of that is this Mac's actual filesystem. |
| `08_write_rootfs.py` | Write to `/etc`, `/usr/local`, `/root`, `/`, `/bin`. | Every path blocked (`Read-only file system` or `Permission denied`) — `read_only=True` covers the whole rootfs, not just the paths someone thought to lock down. |
| `09_escalate_root.py` | `setuid(0)`, `seteuid(0)`, `setgid(0)`; inspect `/proc/self/status` capability bits. | All three blocked (`Operation not permitted`) — starts as `nobody` (65534) with every Linux capability dropped, so there's nothing to escalate *to* even before `no-new-privileges` is considered. `Cap*` lines all read zero. |
| `10_docker_socket.py` | Reach `/var/run/docker.sock`. | Path doesn't exist inside the container — the socket is never mounted in. (If it ever were, this is effectively full host takeover, so this test is really "does the mount list contain a mistake," not "is the socket protected.") |
| `11_sigterm_trap.py` | Install a handler that ignores SIGTERM, then loop forever, to see if a program can outlast the timeout by refusing to cooperate. | Dies at essentially the same wall-clock time as `05` (`failure=timeout`, ≈10s) — the sandbox kills with SIGKILL (`container.kill()`), never SIGTERM/`container.stop()`, and SIGKILL cannot be caught, blocked, or ignored by any userspace handler. |

## Last full run (this host, this build)

```
01_fork_bomb.py              PASS  0.3s  failure=none            (blocked after 63 children)
02_memory_exhaustion.py      PASS  0.5s  failure=oom_killed
03_disk_fill_tmp.py          PASS  0.3s  failure=none            (blocked at 10,485,760 bytes)
04_unbounded_stdout.py       PASS  0.5s  failure=non_zero_exit, truncated=True
05_infinite_loop_silent.py   PASS 10.3s  failure=timeout
06_outbound_network.py       PASS  5.3s  failure=none            (both attempts blocked)
07_read_host_passwd.py       PASS  0.3s  failure=none            (no host path found)
08_write_rootfs.py           PASS  0.2s  failure=none            (all 5 paths blocked)
09_escalate_root.py          PASS  0.2s  failure=none            (all 3 attempts blocked, CapEff=0)
10_docker_socket.py          PASS  0.3s  failure=none            (socket absent)
11_sigterm_trap.py           PASS 10.2s  failure=timeout         (same wall time as 05)

11/11 attacks correctly contained
```

If a re-run ever produces a different verdict on this same host, treat it as a real regression, not flakiness — none of these depend on timing races or external state.
