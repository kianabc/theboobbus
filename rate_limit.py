"""Simple in-memory rate limiter for serverless."""

import time
from collections import defaultdict

# In-memory store (resets on cold start, which is fine for serverless)
_buckets: dict[str, list[float]] = defaultdict(list)


def check_rate_limit(key: str, max_requests: int, window_seconds: int) -> bool:
    """Check if a request is within rate limits.

    Returns True if allowed, False if rate limited.
    """
    now = time.time()
    bucket = _buckets[key]

    # Remove expired entries
    _buckets[key] = [t for t in bucket if now - t < window_seconds]

    if len(_buckets[key]) >= max_requests:
        return False

    _buckets[key].append(now)
    return True
