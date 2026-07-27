"""
Attack: try to write to several parts of the container's own root
filesystem outside of /sandbox and /tmp, to see whether the rootfs is
genuinely read-only everywhere, not just in the one or two paths someone
thought to test.

Correct containment: read_only=True on the container means every one of
these should fail with a read-only-filesystem error, regardless of path.
"""
targets = ["/etc/pwned", "/usr/local/pwned", "/root/pwned", "/pwned", "/bin/pwned"]

for path in targets:
    try:
        with open(path, "w") as f:
            f.write("x")
        print(f"NOT CONTAINED: wrote to {path}")
    except OSError as e:
        print(f"CONTAINED: {path} blocked -> {type(e).__name__}: {e}")
