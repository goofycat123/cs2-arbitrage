"""
Per-source rate limiter. Tracks request timestamps and sleeps
if we'd exceed the limit. Keeps us safe from bans.
"""

import time
from collections import defaultdict

from config import RATE_LIMITS


_timestamps: dict[str, list[float]] = defaultdict(list)


def wait_if_needed(source: str):
    """Block until it's safe to make another request to this source."""
    limit = RATE_LIMITS.get(source, 10)
    window = 60.0  # 1 minute window
    now = time.time()

    # Prune old timestamps
    _timestamps[source] = [t for t in _timestamps[source] if now - t < window]

    if len(_timestamps[source]) >= limit:
        oldest = _timestamps[source][0]
        sleep_for = window - (now - oldest) + 0.5  # +0.5s buffer
        if sleep_for > 0:
            print(f"  [rate-limit] {source}: waiting {sleep_for:.1f}s")
            time.sleep(sleep_for)

    _timestamps[source].append(time.time())
