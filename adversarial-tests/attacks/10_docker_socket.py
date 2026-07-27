"""
Attack: try to reach the Docker socket (/var/run/docker.sock). If this were
ever accidentally mounted into a sandbox container, it would hand the
container full control over the host's Docker daemon - enough to spin up a
brand new, unrestricted container with the host's real filesystem mounted
in, completely escaping this sandbox.

Correct containment: nothing about this sandbox ever mounts the Docker
socket in - the only mount is the one throwaway /sandbox temp directory.
The socket path shouldn't even exist inside the container.
"""
import os
import socket

path = "/var/run/docker.sock"

if not os.path.exists(path):
    print(f"CONTAINED: {path} does not exist inside the container")
else:
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.connect(path)
        print("NOT CONTAINED: connected to the Docker socket")
    except OSError as e:
        print(f"CONTAINED: socket path exists but connect failed -> {type(e).__name__}: {e}")
