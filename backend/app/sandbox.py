"""
Docker-based code execution sandbox.

Replaces the Piston API call in main.py, which stopped being usable once
Piston's public instance was locked down (Feb 2026). Every execution runs in
its own disposable, locked-down container. See SANDBOX_BRIEF.md for what
each isolation control defends against, what breaks without it, and why its
value was chosen for this host.

docker-py is a synchronous SDK - every call is a blocking HTTP request to the
Docker daemon's socket. Everything here goes through asyncio.to_thread so it
never stalls the event loop that's also running the Socket.IO relay.
"""
import asyncio
import os
import re
import shutil
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Callable, Optional

import docker
from docker.errors import NotFound
from docker.types import Mount, Ulimit

_client = docker.from_env()

# Every container we create carries this label so the startup reaper (piece 8)
# can find ours specifically and never touches unrelated containers.
SANDBOX_LABEL = "codencollab.sandbox"

# ---------------------------------------------------------------------------
# Tunables. Chosen for THIS host: Docker Desktop on Apple Silicon, whose
# Linux VM is allocated 8 CPUs / 7.65 GiB (confirmed via `docker info`) - not
# the Mac's full 16 GB. See SANDBOX_BRIEF.md for the tradeoff behind each.
# ---------------------------------------------------------------------------
MEMORY_LIMIT = "512m"          # hard cap per container; memswap set equal -> no swap
PIDS_LIMIT = 64                # max processes/threads per container
CPU_LIMIT_NANOCPUS = int(1.0 * 1e9)  # 1 full core per container
TIMEOUT_SECONDS = 10            # host-enforced wall clock per execution
OUTPUT_CAP_BYTES = 64 * 1024    # 64 KiB combined stdout+stderr before we cut it off
MAX_CONCURRENT_EXECUTIONS = 3   # asyncio.Semaphore size
TMPFS_SIZE = "16m"              # /tmp size inside the container
ULIMIT_NOFILE = 64              # max open file descriptors
ULIMIT_FSIZE_BYTES = 10 * 1024 * 1024  # max size of any single file the process writes
REAPER_MAX_AGE_SECONDS = 60     # orphans older than this get killed at startup

_semaphore = asyncio.Semaphore(MAX_CONCURRENT_EXECUTIONS)


class FailureReason(str, Enum):
    NONE = "none"
    TIMEOUT = "timeout"
    OOM_KILLED = "oom_killed"
    NON_ZERO_EXIT = "non_zero_exit"


@dataclass
class SandboxResult:
    output: str
    exit_code: Optional[int]
    failure: FailureReason
    truncated: bool = False


# ---------------------------------------------------------------------------
# Piece 6: language whitelist. The client sends an identifier string, never
# an image name or a command - that mapping lives here, server-side, only.
# ---------------------------------------------------------------------------
def _java_classname(code: str) -> str:
    # Constrained to a valid Java identifier by construction (\w+ with a
    # non-digit first character) - this value later gets spliced into a
    # shell string (see `command_for` below), so it must never be able to
    # contain shell metacharacters. If nothing matches, "Main" is a fixed,
    # trusted literal, not attacker input.
    match = re.search(r"public\s+(?:final\s+|abstract\s+)?class\s+([A-Za-z_][A-Za-z0-9_]*)", code)
    return match.group(1) if match else "Main"


@dataclass(frozen=True)
class LanguageSpec:
    image: str
    filename_for: Callable[[str], str]        # code -> filename to write inside /sandbox
    command_for: Callable[[str, str], list]   # (in_container_path, code) -> argv
    shell: bool = False                        # argv is a single shell command string


LANGUAGES: dict[str, LanguageSpec] = {
    "python": LanguageSpec(
        image="python:3.10-alpine",
        filename_for=lambda code: "main.py",
        command_for=lambda path, code: ["python3", path],
    ),
    "javascript": LanguageSpec(
        image="node:18.15.0-alpine",
        filename_for=lambda code: "main.js",
        command_for=lambda path, code: ["node", path],
    ),
    "typescript": LanguageSpec(
        # Custom image (backend/docker/typescript.Dockerfile) with ts-node
        # pre-installed at build time - containers run with --network none,
        # so nothing can be `npm install`-ed at execution time.
        image="sandbox-typescript:5.0.3",
        filename_for=lambda code: "main.ts",
        command_for=lambda path, code: ["ts-node", "--transpile-only", path],
    ),
    "php": LanguageSpec(
        image="php:8.2-alpine",
        filename_for=lambda code: "main.php",
        command_for=lambda path, code: ["php", path],
    ),
    "java": LanguageSpec(
        # Not the -alpine tag: it's amd64-only and this host is arm64
        # (Apple Silicon) - confirmed via `docker manifest inspect`.
        image="eclipse-temurin:17-jdk",
        filename_for=lambda code: f"{_java_classname(code)}.java",
        # /tmp is writable (tmpfs, piece 3) for compiled .class output; the
        # `java` process itself loads from the read-only image rootfs, so
        # /tmp's `noexec` doesn't affect it - noexec blocks exec()/mmap of
        # files stored on that filesystem, not a running JVM reading
        # classfiles as data.
        command_for=lambda path, code: (
            f"javac {path} -d /tmp/build && java -cp /tmp/build {_java_classname(code)}"
        ),
        shell=True,
    ),
    # csharp intentionally not wired up: real dotnet execution needs a
    # generated .csproj plus a writable build directory, not just a mounted
    # file - meaningfully more moving parts than the other five for the
    # marginal value of one more language. Deferred, not silently dropped;
    # requests for "csharp" are rejected with an explicit error.
}


def _write_code_dir(code: str, filename: str) -> str:
    tmp_dir = tempfile.mkdtemp(prefix="sandbox-")
    os.chmod(tmp_dir, 0o755)
    path = os.path.join(tmp_dir, filename)
    with open(path, "w") as f:
        f.write(code)
    os.chmod(path, 0o444)
    return tmp_dir


def _create_container(spec: LanguageSpec, host_dir: str, filename: str, code: str):
    in_container_path = f"/sandbox/{filename}"
    command = spec.command_for(in_container_path, code)
    if spec.shell:
        command = ["sh", "-c", command]

    mount = Mount(target="/sandbox", source=host_dir, type="bind", read_only=True)

    return _client.containers.create(
        image=spec.image,
        command=command,
        mounts=[mount],
        # --- piece 3: isolation flags ---
        network_mode="none",                       # no network namespace at all
        mem_limit=MEMORY_LIMIT,
        memswap_limit=MEMORY_LIMIT,                 # == mem_limit -> zero swap
        nano_cpus=CPU_LIMIT_NANOCPUS,
        pids_limit=PIDS_LIMIT,
        read_only=True,                              # rootfs read-only
        tmpfs={"/tmp": f"rw,noexec,nosuid,size={TMPFS_SIZE}"},
        user="65534:65534",                          # nobody:nobody, never root
        cap_drop=["ALL"],
        security_opt=["no-new-privileges"],
        ulimits=[
            Ulimit(name="nofile", soft=ULIMIT_NOFILE, hard=ULIMIT_NOFILE),
            Ulimit(name="fsize", soft=ULIMIT_FSIZE_BYTES, hard=ULIMIT_FSIZE_BYTES),
        ],
        labels={SANDBOX_LABEL: "true"},
        detach=True,
    )


POLL_INTERVAL = 0.1


def _run_and_monitor(container, deadline: float, output_cap: int) -> tuple[bytes, bool, bool]:
    """Piece 4 + 5 share one monitoring loop on purpose: both are really the
    same question - "is this container still worth watching?" - checked
    against wall-clock time and byte count on every poll, not just once
    after some other blocking call returns.

    Polling (not `logs(stream=True)`) is deliberate: a streaming log
    generator blocks on each read until new output arrives, so a container
    stuck in an infinite loop that never prints anything would hang that
    read forever - the deadline would never even get checked. Polling
    `container.logs()` on an interval means the deadline is checked whether
    or not the container is producing output.

    Returns (logs_bytes, truncated, timed_out).
    """
    while True:
        container.reload()
        status = container.attrs["State"]["Status"]
        logs = container.logs(stdout=True, stderr=True)
        truncated = len(logs) > output_cap

        if status == "exited":
            return logs[:output_cap], truncated, False

        if truncated:
            container.kill()  # piece 5: stop it before it can write more
            return logs[:output_cap], True, False

        if time.monotonic() >= deadline:
            container.kill()  # piece 4: see module docstring on kill vs stop
            return logs[:output_cap], truncated, True

        time.sleep(POLL_INTERVAL)


def _blocking_run(spec: LanguageSpec, code: str, timeout: int, output_cap: int) -> SandboxResult:
    """Runs entirely inside a worker thread (see run_sandboxed) - docker-py
    has no async API, so this whole function is one blocking unit of work."""
    filename = spec.filename_for(code)
    host_dir = _write_code_dir(code, filename)
    container = _create_container(spec, host_dir, filename, code)

    try:
        container.start()
        deadline = time.monotonic() + timeout
        logs, truncated, timed_out = _run_and_monitor(container, deadline, output_cap)

        # Give a just-killed container a moment to settle so State/ExitCode
        # reflect what actually happened, rather than a race with the kill.
        try:
            container.wait(timeout=5)
        except Exception:
            pass
        container.reload()
        state = container.attrs.get("State", {})
        exit_code = state.get("ExitCode")

        if timed_out:
            # Piece 4: timeout takes priority over whatever exit_code a
            # SIGKILL happens to leave behind.
            failure = FailureReason.TIMEOUT
        elif state.get("OOMKilled"):
            # Piece 9: read OOM status from the inspect result, not the exit
            # code - a killed process's exit code (often 137) is ambiguous
            # between "OOM" and "someone sent SIGKILL for another reason."
            failure = FailureReason.OOM_KILLED
        elif exit_code not in (0,):
            failure = FailureReason.NON_ZERO_EXIT
        else:
            failure = FailureReason.NONE

        output = logs.decode("utf-8", errors="replace")
        return SandboxResult(output=output, exit_code=exit_code, failure=failure, truncated=truncated)
    finally:
        try:
            container.remove(force=True)
        except NotFound:
            pass
        shutil.rmtree(host_dir, ignore_errors=True)


async def run_sandboxed(language: str, code: str) -> SandboxResult:
    spec = LANGUAGES.get(language)
    if spec is None:
        return SandboxResult(
            output=f"Unsupported language: {language!r}",
            exit_code=None,
            failure=FailureReason.NON_ZERO_EXIT,
        )

    async with _semaphore:  # piece 7: bound concurrent containers
        try:
            # The real timeout enforcement is the deadline inside
            # _run_and_monitor, running in the worker thread - it's the only
            # code that can actually see and kill the container. This outer
            # wait_for is a backstop: asyncio.to_thread can't cancel a
            # thread that's stuck (a docker-py bug, a hung daemon), so if
            # our own deadline logic somehow fails to return in time, this
            # is what keeps the request from hanging forever. If it ever
            # fires, the orphaned container is cleaned up later by the
            # startup reaper (piece 8), not by us here.
            return await asyncio.wait_for(
                asyncio.to_thread(_blocking_run, spec, code, TIMEOUT_SECONDS, OUTPUT_CAP_BYTES),
                timeout=TIMEOUT_SECONDS + 10,
            )
        except asyncio.TimeoutError:
            return SandboxResult(
                output="Execution timed out.",
                exit_code=None,
                failure=FailureReason.TIMEOUT,
            )


async def reap_orphaned_containers() -> int:
    """Piece 8: on startup, kill any of our labelled containers older than
    REAPER_MAX_AGE_SECONDS - leftovers from a crash between `create` and the
    `finally: container.remove()` in a previous process's lifetime."""

    def _reap() -> int:
        killed = 0
        containers = _client.containers.list(
            all=True, filters={"label": f"{SANDBOX_LABEL}=true"}
        )
        now = datetime.now(timezone.utc)
        for container in containers:
            created = container.attrs.get("Created")
            try:
                # Docker's Created field is UTC ("...Z"), with up to
                # nanosecond precision - keep only whole seconds and parse
                # explicitly as UTC. (An earlier version of this used
                # time.mktime, which interprets its input as *local* time;
                # on a UTC-behind host that silently shifted every
                # timestamp into the future, so nothing was ever "old
                # enough" to reap regardless of the threshold.)
                created_dt = datetime.strptime(created[:19], "%Y-%m-%dT%H:%M:%S").replace(
                    tzinfo=timezone.utc
                )
            except Exception:
                created_dt = now  # unparseable -> treat as brand new, don't reap
            age_seconds = (now - created_dt).total_seconds()
            if age_seconds > REAPER_MAX_AGE_SECONDS:
                try:
                    container.remove(force=True)
                    killed += 1
                except NotFound:
                    pass
        return killed

    return await asyncio.to_thread(_reap)
