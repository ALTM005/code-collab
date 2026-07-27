"""
Attack: try to make an outbound network connection and a DNS lookup, to see
whether network isolation actually blocks all traffic (not just, say, one
specific port or protocol).

Correct containment: network_mode=none means there is no network namespace
at all inside the container - not even loopback to the host - so both
attempts below should fail immediately with a clear error, not hang or
time out waiting for a response that will never come.
"""
import socket

try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(3)
    s.connect(("8.8.8.8", 53))
    print("NOT CONTAINED: raw TCP connect succeeded")
except Exception as e:
    print(f"CONTAINED: TCP connect blocked -> {type(e).__name__}: {e}")

try:
    socket.setdefaulttimeout(3)
    socket.gethostbyname("example.com")
    print("NOT CONTAINED: DNS resolution succeeded")
except Exception as e:
    print(f"CONTAINED: DNS resolution blocked -> {type(e).__name__}: {e}")
