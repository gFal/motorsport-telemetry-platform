"""Polling utility for waiting on eventually consistent cluster state. """
import time
from typing import Callable


def wait_until(condition: Callable[[], bool], timeout: float = 30, interval: float = 2,
               desc: str = "condition") -> None:
    """Poll a condition until it holds or the timeout expires.

    Exceptions raised by ``condition`` are treated as "not yet satisfied",
    since transient errors are expected while the system is converging.

    Args:
        condition: Callable returning True once the expected state is reached.
        timeout: Maximum time to wait, in seconds.
        interval: Delay between attempts, in seconds.
        desc: Human-readable description used in the failure message.

    Raises:
        AssertionError: If the condition is not met within ``timeout``.
    """
    deadline, last_error = time.monotonic() + timeout, None
    while time.monotonic() < deadline:
        try:
            if condition():
                return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
        time.sleep(interval)
    raise AssertionError(f"{desc}: not met within {timeout}s (last error: {last_error!r})")