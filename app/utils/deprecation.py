# app/utils/deprecation.py
"""
GoldenTales API Deprecation Utilities
======================================
Utilities for marking endpoints as deprecated and adding appropriate headers.
"""

from datetime import date
from typing import Callable
from functools import wraps

from fastapi import Response
from starlette.requests import Request

from app.utils.logging import get_logger
from app.settings import settings

logger = get_logger(__name__)


# Deprecation timeline (configurable via settings)
LEGACY_API_DEPRECATION_DATE = settings.legacy_api_deprecation_date
LEGACY_API_SUNSET_DATE = settings.legacy_api_sunset_date


def add_deprecation_headers(response: Response, request: Request) -> None:
    """
    Add deprecation headers to response for legacy endpoints.
    
    Args:
        response: FastAPI response object
        request: FastAPI request object
    """
    # Check if this is a legacy endpoint (not /api/v1/*)
    path = request.url.path
    
    if path.startswith("/api/v1/") or path.startswith("/api/health") or path == "/":
        # Not a legacy endpoint, skip
        return
    
    # Add deprecation headers
    response.headers["Deprecation"] = LEGACY_API_DEPRECATION_DATE.isoformat()
    response.headers["Sunset"] = LEGACY_API_SUNSET_DATE.isoformat()
    response.headers["Link"] = '</api/v1>; rel="successor-version"'
    response.headers["X-API-Warning"] = (
        f"This endpoint is deprecated and will be removed on {LEGACY_API_SUNSET_DATE}. "
        "Please migrate to /api/v1/* endpoints."
    )
    
    # Log deprecation warning
    logger.warning(
        f"Legacy API endpoint accessed: {path}",
        extra={
            "path": path,
            "client": request.client.host if request.client else "unknown",
            "user_agent": request.headers.get("user-agent", "unknown"),
            "deprecation_date": str(LEGACY_API_DEPRECATION_DATE),
            "sunset_date": str(LEGACY_API_SUNSET_DATE)
        }
    )


def deprecated_endpoint(successor_path: str):
    """
    Decorator to mark an endpoint as deprecated.
    
    Usage:
        @router.get("/api/books/{book_id}")
        @deprecated_endpoint("/api/v1/books/{book_id}")
        async def get_book(book_id: str):
            ...
    
    Args:
        successor_path: Path to the replacement endpoint
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get response from the original function
            result = await func(*args, **kwargs)
            return result
        
        # Add metadata for OpenAPI documentation
        wrapper.__doc__ = (
            f"⚠️ DEPRECATED: This endpoint is deprecated. "
            f"Use `{successor_path}` instead.\n\n"
            f"Sunset date: {LEGACY_API_SUNSET_DATE}\n\n"
            + (func.__doc__ or "")
        )
        
        return wrapper
    return decorator

