"""In-memory sliding window rate limiter."""

import time
from collections import deque


class SlidingWindowRateLimiter:
    """Sliding window rate limiter using a deque of timestamps.

    Args:
        max_requests: Maximum requests allowed in the window. Default 600.
        window_seconds: Window duration in seconds. Default 60.
    """

    def __init__(self, max_requests: int = 600, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._timestamps: deque = deque()

    def allow(self) -> bool:
        """Check if a request is allowed and record it if so.

        Returns:
            True if the request is allowed, False if rate limit exceeded.
        """
        now = time.monotonic()
        cutoff = now - self.window_seconds

        # Prune expired timestamps
        while self._timestamps and self._timestamps[0] <= cutoff:
            self._timestamps.popleft()

        if len(self._timestamps) >= self.max_requests:
            return False

        self._timestamps.append(now)
        return True
