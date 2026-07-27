"""
Attack: try to read /etc/passwd, and specifically try to find and read the
HOST's real /etc/passwd - not just the container's own, which every
container has by default and is NOT a security issue on its own (it's a
harmless, minimal file baked into the base image, unrelated to this Mac's
real user accounts).

Correct containment: this sandbox never bind-mounts anything from the host
except one throwaway temp directory (read-only, at /sandbox). There is no
path inside the container that leads back to the real host filesystem, so
every probe below should either read the container's own harmless
/etc/passwd, or fail to find anything host-related at all.
"""
import os

with open("/etc/passwd") as f:
    own_passwd = f.read()
print(f"Container's own /etc/passwd ({len(own_passwd)} bytes) - expected, NOT a host leak:")
print(own_passwd[:200])

print("\nChecking for any suspicious host-mounted paths...")
suspicious_paths = ["/host", "/rootfs", "/hostfs", "/mnt/host"]
found_any = False
for path in suspicious_paths:
    if os.path.exists(path):
        found_any = True
        print(f"NOT CONTAINED: found unexpected host-like path: {path}")
if not found_any:
    print("CONTAINED: no host-mounted paths found")

print("\n/proc/mounts (should show only /sandbox, the tmpfs at /tmp, and standard container mounts):")
with open("/proc/mounts") as f:
    print(f.read())
