"""Security primitives: response headers and rate limiting.

These are transport/edge protections. They add no candidate data and
never log secrets or personal information.
"""

import time
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


SECURITY_HEADERS = {
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    # This API returns JSON only; a strict policy blocks any embedding
    # or resource loading if a response is ever rendered in a browser.
    "Content-Security-Policy": (
        "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
    ),
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        for header, value in SECURITY_HEADERS.items():
            response.headers.setdefault(header, value)
        return response


class RateLimiter:
    """In-process fixed-window rate limiter.

    Suitable for a single-process single-user deployment to blunt
    brute-force attempts. Production multi-instance deployments should
    move this to a shared store (documented as deferred).
    """

    def __init__(self, max_attempts: int, window_seconds: int) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._hits: dict[str, list[float]] = defaultdict(list)

    def _now(self) -> float:
        return time.monotonic()

    def check(self, key: str) -> tuple[bool, int]:
        """Record a hit for key; return (allowed, retry_after_seconds)."""
        now = self._now()
        window_start = now - self.window_seconds
        recent = [t for t in self._hits[key] if t >= window_start]

        if len(recent) >= self.max_attempts:
            self._hits[key] = recent
            oldest = min(recent)
            retry_after = max(
                1,
                int(self.window_seconds - (now - oldest)),
            )
            return False, retry_after

        recent.append(now)
        self._hits[key] = recent
        return True, 0

    def reset(self) -> None:
        self._hits.clear()
