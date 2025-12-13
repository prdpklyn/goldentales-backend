# app/middleware/auth.py
"""
GoldenTales API Key Authentication
==================================
Validates API keys for protected endpoints.
"""

import hashlib
import secrets
from typing import Optional, List, Callable

from fastapi import Request, HTTPException, Security
from fastapi.security import APIKeyHeader
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response, JSONResponse

from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

# API Key header configuration
API_KEY_HEADER_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_HEADER_NAME, auto_error=False)

# Public paths that don't require authentication
PUBLIC_PATHS = [
    "/",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/health",
    "/api/config",
    "/api/v1/health",
    "/api/v1/config",
    # Shopify webhooks use HMAC signature verification instead
    "/api/shopify/webhooks/orders/create",
    "/api/shopify/webhooks/orders/fulfilled",
    "/api/shopify/webhooks/orders/cancelled",
    "/api/v1/shopify/webhooks/orders/create",
    "/api/v1/shopify/webhooks/orders/fulfilled",
    "/api/v1/shopify/webhooks/orders/cancelled",
]

# Rate limit tiers
RATE_LIMIT_TIERS = {
    "free": {"requests_per_minute": 10, "requests_per_day": 100},
    "standard": {"requests_per_minute": 60, "requests_per_day": 5000},
    "premium": {"requests_per_minute": 300, "requests_per_day": 50000},
    "internal": {"requests_per_minute": 1000, "requests_per_day": 1000000},
}


def hash_api_key(api_key: str) -> str:
    """Hash an API key for storage/comparison."""
    return hashlib.sha256(api_key.encode()).hexdigest()


def generate_api_key(prefix: str = "gt") -> str:
    """Generate a new API key with prefix."""
    random_part = secrets.token_urlsafe(32)
    return f"{prefix}_{random_part}"


class APIKeyData:
    """Represents validated API key data."""

    def __init__(
        self,
        key_id: str,
        name: str,
        rate_limit_tier: str = "standard",
        is_active: bool = True
    ):
        self.key_id = key_id
        self.name = name
        self.rate_limit_tier = rate_limit_tier
        self.is_active = is_active

    @property
    def rate_limits(self) -> dict:
        """Get rate limits for this key's tier."""
        return RATE_LIMIT_TIERS.get(self.rate_limit_tier, RATE_LIMIT_TIERS["standard"])


class APIKeyValidator:
    """
    Validates API keys against the database.

    In development mode, also accepts a configured dev key.
    """

    def __init__(self):
        self._dev_key = settings.dev_api_key if hasattr(settings, 'dev_api_key') else None

    async def validate(self, api_key: str) -> Optional[APIKeyData]:
        """
        Validate an API key and return its data if valid.

        Returns None if key is invalid or inactive.
        """
        if not api_key:
            return None

        # Check development key first
        if self._dev_key and api_key == self._dev_key:
            return APIKeyData(
                key_id="dev",
                name="Development Key",
                rate_limit_tier="internal",
                is_active=True
            )

        # Hash the key for lookup
        key_hash = hash_api_key(api_key)

        # Look up in database
        try:
            from app.services.database import get_database
            db = get_database()

            if db.client:
                result = db.client.table("api_keys").select("*").eq(
                    "key_hash", key_hash
                ).eq("is_active", True).execute()

                if result.data:
                    key_data = result.data[0]

                    # Update last_used_at
                    db.client.table("api_keys").update({
                        "last_used_at": "now()"
                    }).eq("id", key_data["id"]).execute()

                    return APIKeyData(
                        key_id=key_data["id"],
                        name=key_data["name"],
                        rate_limit_tier=key_data.get("rate_limit_tier", "standard"),
                        is_active=key_data["is_active"]
                    )
        except Exception as e:
            logger.warning(f"API key lookup failed: {e}")

        return None


# Global validator instance
_validator: Optional[APIKeyValidator] = None


def get_api_key_validator() -> APIKeyValidator:
    """Get the API key validator singleton."""
    global _validator
    if _validator is None:
        _validator = APIKeyValidator()
    return _validator


class APIKeyMiddleware(BaseHTTPMiddleware):
    """
    Middleware that validates API keys on protected routes.

    - Skips validation for public paths
    - Returns 401 for missing/invalid keys in production
    - Logs authentication attempts
    """

    def __init__(self, app, enforce_in_dev: bool = False):
        super().__init__(app)
        self.enforce_in_dev = enforce_in_dev
        self.validator = get_api_key_validator()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip auth for public paths
        if self._is_public_path(request.url.path):
            return await call_next(request)

        # Get API key from header
        api_key = request.headers.get(API_KEY_HEADER_NAME)

        # In development, allow requests without API key unless enforced
        if not settings.is_production and not self.enforce_in_dev:
            if not api_key:
                logger.debug(f"No API key provided (dev mode, path: {request.url.path})")
                request.state.api_key_data = None
                return await call_next(request)

        # Validate API key
        if not api_key:
            logger.warning(f"Missing API key for {request.url.path}")
            return JSONResponse(
                status_code=401,
                content={
                    "error": "unauthorized",
                    "message": "API key is required",
                    "detail": f"Provide API key in {API_KEY_HEADER_NAME} header"
                }
            )

        # Validate the key
        key_data = await self.validator.validate(api_key)

        if not key_data:
            logger.warning(f"Invalid API key used for {request.url.path}")
            return JSONResponse(
                status_code=401,
                content={
                    "error": "unauthorized",
                    "message": "Invalid API key"
                }
            )

        if not key_data.is_active:
            logger.warning(f"Inactive API key used: {key_data.key_id}")
            return JSONResponse(
                status_code=401,
                content={
                    "error": "unauthorized",
                    "message": "API key is inactive"
                }
            )

        # Store key data in request state
        request.state.api_key_data = key_data

        logger.debug(
            f"Authenticated request",
            extra={
                "key_id": key_data.key_id,
                "key_name": key_data.name,
                "path": request.url.path
            }
        )

        return await call_next(request)

    def _is_public_path(self, path: str) -> bool:
        """Check if path is public (no auth required)."""
        # Exact match
        if path in PUBLIC_PATHS:
            return True

        # Check path prefixes for docs
        if path.startswith("/docs") or path.startswith("/redoc"):
            return True

        return False


async def get_api_key_header(
    api_key: Optional[str] = Security(api_key_header)
) -> Optional[str]:
    """FastAPI dependency for getting API key from header."""
    return api_key


async def require_api_key(
    request: Request,
    api_key: Optional[str] = Security(api_key_header)
) -> APIKeyData:
    """
    FastAPI dependency that requires a valid API key.

    Use this in route handlers that need authentication:

        @router.get("/protected")
        async def protected_route(key_data: APIKeyData = Depends(require_api_key)):
            return {"message": f"Hello {key_data.name}"}
    """
    # Check if already validated by middleware
    if hasattr(request.state, "api_key_data") and request.state.api_key_data:
        return request.state.api_key_data

    # Validate manually (for routes that bypass middleware)
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="API key is required",
            headers={"WWW-Authenticate": f"ApiKey realm='{API_KEY_HEADER_NAME}'"}
        )

    validator = get_api_key_validator()
    key_data = await validator.validate(api_key)

    if not key_data or not key_data.is_active:
        raise HTTPException(
            status_code=401,
            detail="Invalid or inactive API key",
            headers={"WWW-Authenticate": f"ApiKey realm='{API_KEY_HEADER_NAME}'"}
        )

    return key_data


def get_optional_api_key(request: Request) -> Optional[APIKeyData]:
    """Get API key data if available, otherwise None."""
    return getattr(request.state, "api_key_data", None)
