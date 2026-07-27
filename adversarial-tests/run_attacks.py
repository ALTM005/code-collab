"""
Runs one or all adversarial test programs THROUGH the real sandbox
(sandbox.run_sandboxed) and reports the sandbox's own observed result -
failure/exit_code/truncated - not just what the attack script printed,
since a fully-uncontained attack might never get a chance to report on
itself (e.g. an OOM kill happens mid-script, before any print runs).

Usage:
    python run_attacks.py                       # run all attacks
    python run_attacks.py 05_infinite_loop_silent.py   # run just one

IMPORTANT: never execute the files in attacks/ directly on your host with
`python attacks/whatever.py` - several of them (fork bomb, memory
exhaustion, disk fill) will do to THIS machine exactly what they're
supposed to fail to do inside the sandbox. Only ever run them through this
script, which feeds their source into the sandboxed container - it never
executes them locally.
"""
import asyncio
import sys
import time
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app import sandbox  # noqa: E402

ATTACKS_DIR = Path(__file__).resolve().parent / "attacks"

# One entry per attack file: what "correct containment" looks like, checked
# against the sandbox's own SandboxResult - not the attack script's stdout.
EXPECTATIONS = {
    "01_fork_bomb.py": lambda r, t: r.failure.value in ("none", "non_zero_exit"),
    "02_memory_exhaustion.py": lambda r, t: r.failure.value == "oom_killed",
    "03_disk_fill_tmp.py": lambda r, t: r.failure.value in ("none", "non_zero_exit"),
    "04_unbounded_stdout.py": lambda r, t: r.truncated,
    "05_infinite_loop_silent.py": lambda r, t: r.failure.value == "timeout" and t < sandbox.TIMEOUT_SECONDS + 5,
    "06_outbound_network.py": lambda r, t: r.failure.value == "none",
    "07_read_host_passwd.py": lambda r, t: r.failure.value == "none",
    "08_write_rootfs.py": lambda r, t: r.failure.value == "none",
    "09_escalate_root.py": lambda r, t: r.failure.value == "none",
    "10_docker_socket.py": lambda r, t: r.failure.value == "none",
    "11_sigterm_trap.py": lambda r, t: r.failure.value == "timeout" and t < sandbox.TIMEOUT_SECONDS + 5,
}


async def run_one(path: Path) -> bool:
    code = path.read_text()
    start = time.monotonic()
    result = await sandbox.run_sandboxed("python", code)
    elapsed = time.monotonic() - start

    check = EXPECTATIONS.get(path.name)
    ok = check(result, elapsed) if check else None
    verdict = "PASS" if ok else ("FAIL" if ok is False else "??? (no expectation registered)")

    print(f"=== {path.name} [{verdict}] ({elapsed:.1f}s) ===")
    print(f"failure={result.failure.value} exit_code={result.exit_code} truncated={result.truncated}")
    output = result.output.strip()
    print(output[:2000] + ("... [truncated for display]" if len(output) > 2000 else ""))
    print()
    return bool(ok)


async def main():
    if len(sys.argv) > 1:
        targets = [ATTACKS_DIR / sys.argv[1]]
    else:
        targets = sorted(ATTACKS_DIR.glob("*.py"))

    results = [await run_one(path) for path in targets]

    passed = sum(results)
    print(f"{passed}/{len(results)} attacks correctly contained")
    if passed != len(results):
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
