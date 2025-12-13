# app/middleware/rate_limit.py
"""
GoldenTales Rate Limiting Middleware
====================================
Implements tiered rate limiting based on API key tier.
"""

import time
from typing import Optional, Callable, Dict
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

from app.config import settings
from app.utils.logging import get_logger
from app.middleware.auth import APIKeyData, RATE_LIMIT_TIERS

logger = get_logger(__name__)


class InMemoryRateLimiter:
    """
    Simple in-memory rate limiter using sliding window.

    For production, use Redis-based implementation.
    """

    def __init__(self):
        # Structure: {key: [(timestamp, count), ...]}
        self._minute_windows: Dict[str, list] = defaultdict(list)
        self._day_windows: Dict[str, list] = defaultdict(list)

    def _clean_old_entries(self, entries: list, window_seconds: int) -> list:
        """Remove entries older than the window."""
        cutoff = time.time() - window_seconds
        return [e for e in entries if e[0] > cutoff]

    def check_rate_limit(
        self,
        key: str,
        tier: str = "standard"
    ) -> tuple[bool, dict]:
        """
        Check if request is within rate limits.

        Returns:
            (is_allowed, info_dict)
            info_dict contains remaining requests, reset time, etc.
        """
        limits = RATE_LIMIT_TIERS.get(tier, RATE_LIMIT_TIERS["standard"])
        now = time.time()

        # Clean old entries
        self._minute_windows[key] = self._clean_old_entries(
            self._minute_windows[key], 60
        )
        self._day_windows[key] = self._clean_old_entries(
            self._day_windows[key], 86400
        )

        # Count requests in windows
        minute_count = sum(e[1] for e in self._minute_windows[key])
        day_count = sum(e[1] for e in self._day_windows[key])

        # Check limits
        per_minute = limits["requests_per_minute"]
        per_day = limits["requests_per_day"]

        minute_remaining = max(0, per_minute - minute_count)
        day_remaining = max(0, per_day - day_count)

        info = {
            "limit_minute": per_minute,
            "remaining_minute": minute_remaining,
            "limit_day": per_day,
            "remaining_day": day_remaining,
            "reset_minute": int(now + 60),
            "reset_day": int(now + 86400),
            "tier": tier
        }

        if minute_count >= per_minute:
            return False, {**info, "exceeded": "minute"}

        if day_count >= per_day:
            return False, {**info, "exceeded": "day"}

        return True, info

    def record_request(self, key: str):
        """Record a request for rate limiting."""
        now = time.time()
        self._minute_windows[key].append((now, 1))
        self._day_windows[key].append((now, 1))


class RedisRateLimiter:
    """
    Redis-based rate limiter for production use.

    Uses sliding window with Redis sorted sets.
    """

    def __init__(self, redis_client):
        self.redis = redis_client

    async def check_rate_limit(
        self,
        key: str,
        tier: str = "standard"
    ) -> tuple[bool, dict]:
        """Check rate limit using Redis."""
        limits = RATE_LIMIT_TIERS.get(tier, RATE_LIMIT_TIERS["standard"])
        now = time.time()

        minute_key = f"ratelimit:minute:{key}"
        day_key = f"ratelimit:day:{key}"

        # Remove old entries and count
        pipe = self.redis.pipeline()

        # Minute window
        pipe.zremrangebyscore(minute_key, 0, now - 60)
        pipe.zcard(minute_key)

        # Day window
        pipe.zremrangebyscore(day_key, 0, now - 86400)
        pipe.zcard(day_key)

        results = await pipe.execute()
        minute_count = results[1]
        day_count = results[3]

        per_minute = limits["requests_per_minute"]
        per_day = limits["requests_per_day"]

        info = {
            "limit_minute": per_minute,
            "remaining_minute": max(0, per_minute - minute_count),
            "limit_day": per_day,
            "remaining_day": max(0, per_day - day_count),
            "reset_minute": int(now + 60),
            "reset_day": int(now + 86400),
            "tier": tier
        }

        if minute_count >= per_minute:
            return False, {**info, "exceeded": "minute"}

        if day_count >= per_day:
            return False, {**info, "exceeded": "day"}

        return True, info

    async def record_request(self, key: str):
        """Record a request in Redis."""
        now = time.time()

        minute_key = f"ratelimit:minute:{key}"
        day_key = f"ratelimit:day:{key}"

        pipe = self.redis.pipeline()
        pipe.zadd(minute_key, {str(now): now})
        pipe.expire(minute_key, 120)  # Keep 2 minutes
        pipe.zadd(day_key, {str(now): now})
        pipe.expire(day_key, 90000)  # Keep 25 hours
        await pipe.execute()


# Global rate limiter instance
_rate_limiter: Optional[InMemoryRateLimiter] = None


def get_rate_limiter() -> InMemoryRateLimiter:
    """Get the rate limiter singleton."""
    global _rate_limiter
    if _rate_limiter is None:
        # TODO: Use RedisRateLimiter in production if Redis is configured
        _rate_limiter = InMemoryRateLimiter()
    return _rate_limiter


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware that enforces rate limits based on API key tier.

    Rate limits are applied per API key (or IP for unauthenticated requests).
    """

    # Paths exempt from rate limiting
    EXEMPT_PATHS = [
        "/",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/health",
        "/api/v1/health",
    ]

    def __init__(self, app, enabled: bool = True):
        super().__init__(app)
        self.enabled = enabled
        self.limiter = get_rate_limiter()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip if disabled
        if not self.enabled:
            return await call_next(request)

        # Skip exempt paths
        if self._is_exempt(request.url.path):
            return await call_next(request)

        # Determine rate limit key and tier
        key, tier = self._get_limit_key_and_tier(request)

        # Check rate limit
        is_allowed, info = self.limiter.check_rate_limit(key, tier)

        if not is_allowed:
            logger.warning(
                f"Rate limit exceeded",
                extra={
                    "key": key[:20] + "...",  # Truncate for logging
                    "tier": tier,
                    "exceeded": info.get("exceeded"),
                    "path": request.url.path
                }
            )

            exceeded_type = info.get("exceeded", "minute")
            if exceeded_type == "minute":
                retry_after = 60
                message = "Rate limit exceeded. Too many requests per minute."
            else:
                retry_after = 3600
                message = "Daily rate limit exceeded."

            return JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limit_exceeded",
                    "message": message,
                    "tier": tier,
                    "limit": info.get(f"limit_{exceeded_type}"),
                    "retry_after": retry_after
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(info.get("limit_minute")),
                    "X-RateLimit-Remaining": str(info.get("remaining_minute")),
                    "X-RateLimit-Reset": str(info.get("reset_minute"))
                }
            )

        # Record the request
        self.limiter.record_request(key)

        # Process request
        response = await call_next(request)

        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit"] = str(info.get("limit_minute"))
        response.headers["X-RateLimit-Remaining"] = str(
            max(0, info.get("remaining_minute", 0) - 1)
        )
        response.headers["X-RateLimit-Reset"] = str(info.get("reset_minute"))

        return response

    def _is_exempt(self, path: str) -> bool:
        """Check if path is exempt from rate limiting."""
        return path in self.EXEMPT_PATHS or path.startswith("/docs")

    def _get_limit_key_and_tier(self, request: Request) -> tuple[str, str]:
        """Get the rate limit key and tier for a request."""
        # If authenticated, use API key ID
        api_key_data: Optional[APIKeyData] = getattr(
            request.state, "api_key_data", None
        )

        if api_key_data:
            return f"apikey:{api_key_data.key_id}", api_key_data.rate_limit_tier

        # Otherwise, use client IP with default tier
        client_ip = self._get_client_ip(request)
        return f"ip:{client_ip}", "free"

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request."""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        if request.client:
            return request.client.host

        return "unknown"
