# app/middleware/request_id.py
"""
GoldenTales Request ID Middleware
=================================
Adds unique request IDs for tracing and debugging.
"""

import uuid
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.utils.logging import get_logger

logger = get_logger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds a unique request ID to each request.

    - Checks for existing X-Request-ID header (from load balancer/gateway)
    - Generates new UUID if not present
    - Adds request ID to response headers
    - Makes request ID available via request.state.request_id
    """

    HEADER_NAME = "X-Request-ID"

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Get or generate request ID
        request_id = request.headers.get(self.HEADER_NAME)

        if not request_id:
            request_id = str(uuid.uuid4())

        # Store in request state for access in route handlers
        request.state.request_id = request_id

        # Log the request with ID
        logger.debug(
            f"Request started",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "client_ip": self._get_client_ip(request)
            }
        )

        # Process request
        response = await call_next(request)

        # Add request ID to response headers
        response.headers[self.HEADER_NAME] = request_id

        # Log completion
        logger.debug(
            f"Request completed",
            extra={
                "request_id": request_id,
                "status_code": response.status_code
            }
        )

        return response

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request, checking forwarded headers."""
        # Check X-Forwarded-For (from load balancers/proxies)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP (original client)
            return forwarded_for.split(",")[0].strip()

        # Check X-Real-IP (nginx)
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fall back to direct client
        if request.client:
            return request.client.host

        return "unknown"


def get_request_id(request: Request) -> str:
    """Helper to get request ID from request state."""
    return getattr(request.state, "request_id", "unknown")
