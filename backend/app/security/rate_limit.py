"""
Rate limiting configuration for DCP API.

Uses slowapi for rate limiting based on client IP or custom keys.
"""
import logging
from typing import Callable

from fastapi import Request, Response
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.responses import JSONResponse

logger = logging.getLogger("dcp.security.rate_limit")


def get_client_identifier(request: Request) -> str:
    """
    Get a unique identifier for the client.

    Uses X-Forwarded-For header if present (for proxied requests),
    otherwise falls back to remote address.
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Take the first IP in the chain (original client)
        return forwarded.split(",")[0].strip()

    return get_remote_address(request)


def get_api_key_or_ip(request: Request) -> str:
    """
    Get rate limit key based on API key or IP.

    If bearer token is used, rate limit by token.
    Otherwise, rate limit by IP.
    """
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1]
        # Use hash of token to avoid storing sensitive data
        return f"token:{hash(token) % 10000000}"

    return get_client_identifier(request)


# Create limiter instance
limiter = Limiter(
    key_func=get_api_key_or_ip,
    default_limits=["200 per minute"],
    storage_uri="memory://",  # Use Redis for distributed: "redis://redis:6379"
    strategy="fixed-window",
)


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """
    Custom handler for rate limit exceeded errors.

    Returns a JSON response with retry-after information.
    """
    logger.warning(
        f"Rate limit exceeded for {get_client_identifier(request)}",
        extra={
            "client": get_client_identifier(request),
            "path": request.url.path,
            "limit": str(exc.detail),
        },
    )

    return JSONResponse(
        status_code=429,
        content={
            "error": "rate_limit_exceeded",
            "detail": "Too many requests. Please try again later.",
            "retry_after": 60,  # seconds
        },
        headers={
            "Retry-After": "60",
            "X-RateLimit-Limit": str(exc.detail).split()[0] if exc.detail else "200",
        },
    )


# Decorator functions for common rate limits
def limit_create(limit: str = "50/minute") -> Callable:
    """Rate limit decorator for create operations."""
    return limiter.limit(limit)


def limit_read(limit: str = "200/minute") -> Callable:
    """Rate limit decorator for read operations."""
    return limiter.limit(limit)


def limit_action(limit: str = "100/minute") -> Callable:
    """Rate limit decorator for action operations."""
    return limiter.limit(limit)
