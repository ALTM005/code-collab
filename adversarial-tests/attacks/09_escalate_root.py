"""
Attack: try several ways to regain root privilege from a non-root starting
user, to see whether cap-drop + no-new-privileges actually close off
privilege escalation - not just the starting UID being non-zero.

Correct containment: every attempt below should fail with PermissionError.
Reading /proc/self/status also confirms the process holds zero effective
capabilities (every Cap* line should read all zeros).
"""
import os

print("Starting uid/gid:", os.getuid(), os.getgid())

for name, fn in [
    ("setuid(0)", lambda: os.setuid(0)),
    ("seteuid(0)", lambda: os.seteuid(0)),
    ("setgid(0)", lambda: os.setgid(0)),
]:
    try:
        fn()
        print(f"NOT CONTAINED: {name} succeeded, now uid={os.getuid()}")
    except PermissionError as e:
        print(f"CONTAINED: {name} blocked -> {e}")

print("\n/proc/self/status capability bits (all should be 0):")
with open("/proc/self/status") as f:
    for line in f:
        if line.startswith("Cap"):
            print(line.strip())
