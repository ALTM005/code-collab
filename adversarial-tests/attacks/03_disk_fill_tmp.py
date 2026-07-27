"""
Attack: write far more data than /tmp's tmpfs size (and the per-file fsize
ulimit) allow, to see whether a program can fill disk space without bound.

Correct containment: /tmp is a size-capped tmpfs, and the fsize ulimit caps
any single file's size. Depending on which limit is hit first, the write
either raises a clean OSError (ENOSPC/EFBIG) or the process is killed
outright by SIGXFSZ - either way, writing stops far short of the ~1GB this
script asks for, and nothing about this can ever touch the host's real
disk (the container's rootfs is read-only and /tmp is an in-memory tmpfs,
not a bind mount to anything on the host).
"""
written = 0
chunk = b"x" * (1024 * 1024)  # 1MB per write

try:
    with open("/tmp/fill.bin", "wb") as f:
        for _ in range(1024):  # would be ~1GB if nothing stopped it
            f.write(chunk)
            f.flush()
            written += len(chunk)
except OSError as e:
    print(f"CONTAINED: write blocked after {written} bytes -> {type(e).__name__}: {e}")
else:
    print(f"NOT CONTAINED: wrote {written} bytes without being blocked")
