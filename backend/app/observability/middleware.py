"""
Middleware for request tracing and metrics collection.
"""
import time
import logging
from uuid import uuid4
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from .metrics import (
    request_duration_seconds,
    request_total,
    active_connections_gauge,
)

logger = logging.getLogger("dcp.middleware")


class RequestTracingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds trace IDs to requests.

    Extracts trace ID from X-Trace-ID or X-Request-ID headers,
    or generates a new one if not present.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Extract or generate trace ID
        trace_id = (
            request.headers.get("X-Trace-ID")
            or request.headers.get("X-Request-ID")
            or str(uuid4())
        )

        # Store in request state
        request.state.trace_id = trace_id

        # Process request
        response = await call_next(request)

        # Add trace ID to response headers
        response.headers["X-Trace-ID"] = trace_id

        return response


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware that collects request metrics.

    Records:
    - Request duration histogram
    - Request count by method/endpoint/status
    - Active connections gauge
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip metrics endpoint to avoid recursion
        if request.url.path == "/metrics":
            return await call_next(request)

        # Track active connections
        active_connections_gauge.inc()

        # Record start time
        start_time = time.perf_counter()

        try:
            # Process request
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            status_code = 500
            raise
        finally:
            # Calculate duration
            duration = time.perf_counter() - start_time

            # Get endpoint path (normalize path parameters)
            endpoint = self._normalize_path(request.url.path)
            method = request.method

            # Record metrics
            request_duration_seconds.labels(
                method=method,
                endpoint=endpoint,
                status=str(status_code),
            ).observe(duration)

            request_total.labels(
                method=method,
                endpoint=endpoint,
                status=str(status_code),
            ).inc()

            # Update active connections
            active_connections_gauge.dec()

        return response

    def _normalize_path(self, path: str) -> str:
        """
        Normalize path by replacing UUIDs and IDs with placeholders.

        This prevents high cardinality in metrics labels.
        """
        import re

        # Replace UUIDs with placeholder
        path = re.sub(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            "{id}",
            path,
            flags=re.IGNORECASE,
        )

        # Replace numeric IDs with placeholder
        path = re.sub(r"/\d+(?=/|$)", "/{id}", path)

        return path


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that logs request/response information.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Get trace ID
        trace_id = getattr(request.state, "trace_id", "unknown")

        # Log request
        logger.info(
            "Request started",
            extra={
                "trace_id": trace_id,
                "method": request.method,
                "path": request.url.path,
                "client": request.client.host if request.client else "unknown",
            },
        )

        start_time = time.perf_counter()

        try:
            response = await call_next(request)
            duration = time.perf_counter() - start_time

            # Log response
            logger.info(
                "Request completed",
                extra={
                    "trace_id": trace_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "duration_ms": round(duration * 1000, 2),
                },
            )

            return response

        except Exception as e:
            duration = time.perf_counter() - start_time
            logger.error(
                "Request failed",
                extra={
                    "trace_id": trace_id,
                    "method": request.method,
                    "path": request.url.path,
                    "error": str(e),
                    "duration_ms": round(duration * 1000, 2),
                },
            )
            raise
