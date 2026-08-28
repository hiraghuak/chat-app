"""Tiny in-memory per-IP rate limiter.

The deployed URL is public and the OpenRouter free tier is ~200 requests/day, so
an open endpoint can be drained by bots. This caps requests per client IP per
minute and per day. State is in-memory (resets on restart) — sufficient for a
single-instance demo; a shared store (Redis) would be the production upgrade.
"""
from __future__ import annotations

import time
from collections import defaultdict, deque

_MINUTE = 60
_DAY = 86_400


class RateLimiter:
    def __init__(self, per_minute: int, per_day: int):
        self.per_minute = per_minute
        self.per_day = per_day
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str) -> tuple[bool, str]:
        """Return (allowed, message). Records the hit when allowed."""
        now = time.time()
        hits = self._hits[key]
        while hits and now - hits[0] > _DAY:
            hits.popleft()
        last_minute = sum(1 for t in hits if now - t <= _MINUTE)
        if last_minute >= self.per_minute:
            return False, "Too many requests. Please wait a minute and try again."
        if len(hits) >= self.per_day:
            return False, "Daily request limit reached for this demo. Try again tomorrow."
        hits.append(now)
        return True, ""
