"""
Attack: install a SIGTERM handler that ignores the signal, then loop
forever - to test whether the sandbox's timeout enforcement can be evaded
by a program that refuses to respond to a polite "please stop."

Correct containment: the sandbox kills timed-out containers with SIGKILL
(container.kill()), never SIGTERM/container.stop(). SIGKILL cannot be
caught, blocked, or ignored by userspace code - so this program should die
at essentially the same time as a plain silent infinite loop would
(failure=timeout, close to TIMEOUT_SECONDS), gaining no extra survival time
from trapping SIGTERM. Note: under the current implementation SIGTERM is
never even sent (only SIGKILL), so the handler below is expected to never
actually fire - it's here as a regression guard in case a future change
ever reintroduces container.stop() (SIGTERM-then-wait) for timeouts.
"""
import signal
import time

def ignore_sigterm(signum, frame):
    print("caught SIGTERM, ignoring it")

signal.signal(signal.SIGTERM, ignore_sigterm)

while True:
    time.sleep(0.1)
