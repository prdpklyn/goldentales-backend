# app/middleware/versioning.py
"""
GoldenTales API Versioning Middleware
=====================================
Handles API version detection, deprecation warnings, and sunset headers.
"""

from datetime import datetime, date
from typing import Callable, Dict, Optional
from dataclasses import dataclass

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

from app.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class APIVersion:
    """API version metadata."""
    version: str
    status: str  # "current", "deprecated", "sunset"
    deprecated_at: Optional[date] = None
    sunset_at: Optional[date] = None
    successor: Optional[str] = None


# API version registry
API_VERSIONS: Dict[str, APIVersion] = {
    "v1": APIVersion(
        version="v1",
        status="current",
    ),
    "v2": APIVersion(
        version="v2",
        status="current",
    ),
}

# Default version for unversioned requests
DEFAULT_VERSION = "v1"


class VersioningMiddleware(BaseHTTPMiddleware):
    """
    Middleware that handles API versioning.

    Features:
    - Detects API version from URL path (/api/v1/...)
    - Adds deprecation warnings for deprecated versions
    - Returns 410 Gone for sunset versions
    - Adds version headers to responses
    """

    # Paths that bypass versioning
    BYPASS_PATHS = [
        "/",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/health",
    ]

    def __init__(self, app, enabled: bool = True):
        super().__init__(app)
        self.enabled = enabled

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not self.enabled:
            return await call_next(request)

        path = request.url.path

        # Bypass for non-API paths
        if self._should_bypass(path):
            return await call_next(request)

        # Extract version from path
        version = self._extract_version(path)

        if version:
            version_info = API_VERSIONS.get(version)

            if not version_info:
                # Unknown version
                return JSONResponse(
                    status_code=400,
                    content={
                        "error": "invalid_api_version",
                        "message": f"Unknown API version: {version}",
                        "supported_versions": list(API_VERSIONS.keys())
                    }
                )

            # Check if version is sunset
            if version_info.status == "sunset":
                sunset_date = version_info.sunset_at
                return JSONResponse(
                    status_code=410,
                    content={
                        "error": "api_version_sunset",
                        "message": f"API version {version} has been discontinued as of {sunset_date}",
                        "successor": version_info.successor,
                        "migration_guide": f"/docs/migration/{version}-to-{version_info.successor}"
                    },
                    headers={
                        "Sunset": sunset_date.isoformat() if sunset_date else "",
                        "Link": f'</api/{version_info.successor}/>; rel="successor-version"'
                    }
                )

            # Store version info in request state
            request.state.api_version = version
            request.state.api_version_info = version_info

        # Process request
        response = await call_next(request)

        # Add version headers
        if version:
            version_info = API_VERSIONS.get(version)
            if version_info:
                response.headers["X-API-Version"] = version
                response.headers["X-API-Status"] = version_info.status

                # Add deprecation headers if deprecated
                if version_info.status == "deprecated":
                    if version_info.deprecated_at:
                        response.headers["Deprecation"] = version_info.deprecated_at.isoformat()
                    if version_info.sunset_at:
                        response.headers["Sunset"] = version_info.sunset_at.isoformat()
                    if version_info.successor:
                        response.headers["Link"] = (
                            f'</api/{version_info.successor}/>; rel="successor-version"'
                        )

                    # Log deprecation warning
                    logger.warning(
                        f"Deprecated API version {version} accessed",
                        extra={
                            "path": path,
                            "version": version,
                            "sunset_at": str(version_info.sunset_at)
                        }
                    )

        return response

    def _should_bypass(self, path: str) -> bool:
        """Check if path should bypass versioning."""
        for bypass_path in self.BYPASS_PATHS:
            if path == bypass_path or path.startswith(f"{bypass_path}/"):
                return True
        return False

    def _extract_version(self, path: str) -> Optional[str]:
        """Extract API version from path."""
        # Match /api/v1/... or /v1/...
        parts = path.strip("/").split("/")

        for i, part in enumerate(parts):
            if part.startswith("v") and part[1:].isdigit():
                return part
            if part == "api" and i + 1 < len(parts):
                next_part = parts[i + 1]
                if next_part.startswith("v") and next_part[1:].isdigit():
                    return next_part

        return None


def deprecate_version(
    version: str,
    deprecated_at: date,
    sunset_at: date,
    successor: str
):
    """
    Mark an API version as deprecated.

    Call this to deprecate a version:
        deprecate_version("v1", date(2024, 6, 1), date(2024, 12, 1), "v2")

    Args:
        version: Version to deprecate (e.g., "v1")
        deprecated_at: Date deprecation starts
        sunset_at: Date version will be removed
        successor: Version to migrate to
    """
    if version in API_VERSIONS:
        API_VERSIONS[version] = APIVersion(
            version=version,
            status="deprecated",
            deprecated_at=deprecated_at,
            sunset_at=sunset_at,
            successor=successor
        )
        logger.info(
            f"API version {version} deprecated",
            extra={
                "deprecated_at": str(deprecated_at),
                "sunset_at": str(sunset_at),
                "successor": successor
            }
        )


def sunset_version(version: str):
    """
    Mark an API version as sunset (no longer available).

    Args:
        version: Version to sunset
    """
    if version in API_VERSIONS:
        current = API_VERSIONS[version]
        API_VERSIONS[version] = APIVersion(
            version=version,
            status="sunset",
            deprecated_at=current.deprecated_at,
            sunset_at=current.sunset_at or date.today(),
            successor=current.successor
        )
        logger.info(f"API version {version} sunset")


def get_api_versions() -> Dict[str, dict]:
    """Get all API versions and their status."""
    return {
        v: {
            "version": info.version,
            "status": info.status,
            "deprecated_at": str(info.deprecated_at) if info.deprecated_at else None,
            "sunset_at": str(info.sunset_at) if info.sunset_at else None,
            "successor": info.successor
        }
        for v, info in API_VERSIONS.items()
    }
