"""
Attack: print forever, to see whether output is actually capped or Docker's
log driver is left to buffer/write it to the host's disk without bound.

Correct containment: the sandbox's output cap kills this container once
accumulated stdout exceeds the cap. The caller should see truncated=True
and a bounded amount of output - not gigabytes of "x"s, and no unbounded
growth of any log file on the host.
"""
while True:
    print("x" * 100)
