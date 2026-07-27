"""
Attack: allocate and touch far more memory than the container's cap, to see
whether a limit is actually enforced or the process (and the host) can just
run out of memory.

Correct containment: mem_limit + memswap_limit == mem_limit (no swap) means
the kernel's cgroup OOM killer kills this process partway through the loop,
before the "NOT CONTAINED" line below can ever print. The sandbox should
report failure=oom_killed, read from the container's inspect state
(State.OOMKilled), not guessed from the exit code.
"""
size_mb = 800  # comfortably over the container's memory cap

data = bytearray(size_mb * 1024 * 1024)
# Touch every page so the kernel actually commits real memory rather than
# lazily-mapped pages that are never faulted in.
for i in range(0, len(data), 4096):
    data[i] = 1

print(f"NOT CONTAINED: successfully allocated and touched {size_mb}MB")
