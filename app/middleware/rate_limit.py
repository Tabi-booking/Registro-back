from __future__ import annotations

import time

import redis.asyncio as aioredis
from fastapi import Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.database.session import get_redis

# Route-specific rate limits: (max_requests, window_seconds)
RATE_LIMITS: dict[str, tuple[int, int]] = {
    "/api/v1/auth/register": (5, 60),
    "/api/v1/auth/login": (5, 60),
    "/api/v1/auth/refresh": (10, 60),
}
DEFAULT_LIMIT = (60, 60)


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, redis_client: aioredis.Redis | None = None):
        super().__init__(app)
        self._redis = redis_client

    @property
    def redis(self) -> aioredis.Redis:
        if self._redis is None:
            self._redis = get_redis()
        return self._redis

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path
        max_req, window = RATE_LIMITS.get(path, DEFAULT_LIMIT)
        ip = _get_client_ip(request)
        key = f"rate:{path}:{ip}"

        try:
            pipe = self.redis.pipeline()
            now_window = int(time.time()) // window
            window_key = f"{key}:{now_window}"
            pipe.incr(window_key)
            pipe.expire(window_key, window)
            results = await pipe.execute()
            count = results[0]

            if count > max_req:
                return Response(
                    content='{"success":false,"error":"Too many requests","code":"RATE_LIMIT_EXCEEDED"}',
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    media_type="application/json",
                    headers={"Retry-After": str(window)},
                )
        except Exception:
            # If Redis is down, allow the request (fail open)
            pass

        return await call_next(request)
