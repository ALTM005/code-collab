"""
Attack: loop forever without producing any output at all - specifically to
test whether the timeout is enforced independently of output. A naive
implementation that only checks its deadline while reading container
output would hang forever on a silent loop like this, since there's never
any output to read.

Correct containment: failure=timeout, and total wall-clock time should land
close to the configured timeout (TIMEOUT_SECONDS), not hang indefinitely.
"""
while True:
    pass
