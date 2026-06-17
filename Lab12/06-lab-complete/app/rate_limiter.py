"""Redis-backed sliding window rate limiter."""
import time
from collections import defaultdict, deque

from fastapi import HTTPException

from app.config import settings
from app.redis_client import get_redis, redis_available

_memory_windows: dict[str, deque] = defaultdict(deque)


def check_rate_limit(user_id: str) -> dict:
    limit = settings.rate_limit_per_minute
    window = 60
    now = time.time()

    client = get_redis()
    if redis_available() and client is not None:
        key = f"ratelimit:{user_id}"
        pipe = client.pipeline()
        pipe.zremrangebyscore(key, 0, now - window)
        pipe.zadd(key, {f"{now}": now})
        pipe.zcard(key)
        pipe.expire(key, window)
        _, _, count, _ = pipe.execute()

        if count > limit:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded: {limit} requests per minute",
                headers={"Retry-After": "60"},
            )
        return {"limit": limit, "remaining": max(0, limit - count)}

    bucket = _memory_windows[user_id]
    while bucket and bucket[0] < now - window:
        bucket.popleft()
    if len(bucket) >= limit:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: {limit} requests per minute",
            headers={"Retry-After": "60"},
        )
    bucket.append(now)
    return {"limit": limit, "remaining": limit - len(bucket)}
