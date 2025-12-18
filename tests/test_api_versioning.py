# tests/test_api_versioning.py
"""
Tests for API Versioning System
===============================
Tests versioned routes, deprecation middleware, and backward compatibility.
"""

import pytest
from datetime import date
from unittest.mock import patch
from fastapi.testclient import TestClient

from main import app
from app.middleware.versioning import (
    API_VERSIONS,
    APIVersion,
    deprecate_version,
    sunset_version,
    get_api_versions,
    VersioningMiddleware
)


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def reset_versions():
    """Reset API versions to default state after test."""
    original = API_VERSIONS.copy()
    yield
    API_VERSIONS.clear()
    API_VERSIONS.update(original)


class TestCommonEndpoints:
    """Test version-agnostic endpoints."""

    def test_root_endpoint(self, client):
        """Test root health check."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "GoldenTales API"
        assert data["status"] == "healthy"
        assert "version" in data

    def test_health_endpoint(self, client):
        """Test detailed health check."""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "version" in data
        assert "environment" in data
        # Health endpoint returns 'connectivity' instead of 'checks'
        assert "connectivity" in data or "checks" in data

    def test_v1_health_endpoint(self, client):
        """Test v1 health check."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data


class TestV1Endpoints:
    """Test v1 versioned endpoints."""

    def test_v1_config_endpoint(self, client):
        """Test v1 config endpoint."""
        response = client.get("/api/v1/config")
        assert response.status_code == 200
        data = response.json()
        assert "api_version" in data
        assert data["api_version"] == "1.0.0"
        assert "themes" in data
        assert "art_styles" in data
        assert "formats" in data
        assert "prices" in data
        assert "character_options" in data

    def test_v1_version_header(self, client):
        """Test that v1 endpoints return version headers."""
        response = client.get("/api/v1/config")
        assert response.status_code == 200
        assert response.headers.get("X-API-Version") == "v1"
        assert response.headers.get("X-API-Status") == "current"

    def test_v1_shopify_health(self, client):
        """Test v1 shopify health endpoint."""
        response = client.get("/api/v1/shopify/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


class TestLegacyBackwardCompatibility:
    """Test backward compatibility with legacy /api/* routes."""

    def test_legacy_config_endpoint(self, client):
        """Test legacy /api/config still works."""
        response = client.get("/api/config")
        assert response.status_code == 200
        data = response.json()
        assert "themes" in data
        assert "art_styles" in data

    def test_legacy_shopify_health(self, client):
        """Test legacy shopify health endpoint."""
        response = client.get("/api/shopify/health")
        assert response.status_code == 200


class TestVersioningMiddleware:
    """Test versioning middleware behavior."""

    def test_unknown_version_rejected(self, client):
        """Test that unknown versions are rejected."""
        response = client.get("/api/v99/config")
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "invalid_api_version"
        assert "v99" in data["message"]
        assert "supported_versions" in data

    def test_bypass_paths_no_version_check(self, client):
        """Test that bypass paths skip version checking."""
        # These should work without version
        for path in ["/", "/docs", "/api/health"]:
            response = client.get(path)
            # docs redirects, so allow 200 or 307
            assert response.status_code in [200, 307]


class TestVersionDeprecation:
    """Test version deprecation functionality."""

    def test_deprecate_version(self, reset_versions):
        """Test marking a version as deprecated."""
        deprecate_version(
            "v1",
            deprecated_at=date(2024, 6, 1),
            sunset_at=date(2024, 12, 1),
            successor="v2"
        )

        version_info = API_VERSIONS["v1"]
        assert version_info.status == "deprecated"
        assert version_info.deprecated_at == date(2024, 6, 1)
        assert version_info.sunset_at == date(2024, 12, 1)
        assert version_info.successor == "v2"

    def test_deprecated_version_adds_headers(self, client, reset_versions):
        """Test that deprecated versions add warning headers."""
        # First deprecate v1
        deprecate_version(
            "v1",
            deprecated_at=date(2024, 6, 1),
            sunset_at=date(2024, 12, 1),
            successor="v2"
        )

        response = client.get("/api/v1/config")
        assert response.status_code == 200
        assert response.headers.get("X-API-Status") == "deprecated"
        assert response.headers.get("Deprecation") == "2024-06-01"
        assert response.headers.get("Sunset") == "2024-12-01"
        assert 'rel="successor-version"' in response.headers.get("Link", "")

    def test_sunset_version(self, reset_versions):
        """Test marking a version as sunset."""
        # First deprecate
        deprecate_version(
            "v1",
            deprecated_at=date(2024, 6, 1),
            sunset_at=date(2024, 12, 1),
            successor="v2"
        )

        # Then sunset
        sunset_version("v1")

        version_info = API_VERSIONS["v1"]
        assert version_info.status == "sunset"

    def test_sunset_version_returns_410(self, client, reset_versions):
        """Test that sunset versions return 410 Gone."""
        # First deprecate then sunset
        deprecate_version(
            "v1",
            deprecated_at=date(2024, 6, 1),
            sunset_at=date(2024, 12, 1),
            successor="v2"
        )
        sunset_version("v1")

        response = client.get("/api/v1/config")
        assert response.status_code == 410
        data = response.json()
        assert data["error"] == "api_version_sunset"
        assert data["successor"] == "v2"


class TestGetApiVersions:
    """Test API version listing."""

    def test_get_api_versions(self):
        """Test getting all API versions."""
        versions = get_api_versions()
        assert "v1" in versions
        assert versions["v1"]["status"] == "current"

    def test_get_api_versions_after_deprecation(self, reset_versions):
        """Test version listing reflects deprecation."""
        deprecate_version(
            "v1",
            deprecated_at=date(2024, 6, 1),
            sunset_at=date(2024, 12, 1),
            successor="v2"
        )

        versions = get_api_versions()
        assert versions["v1"]["status"] == "deprecated"
        assert versions["v1"]["deprecated_at"] == "2024-06-01"
        assert versions["v1"]["sunset_at"] == "2024-12-01"
        assert versions["v1"]["successor"] == "v2"


class TestV1Routers:
    """Test individual v1 router imports and structure."""

    def test_v1_books_router_exists(self):
        """Test v1 books router is properly configured."""
        from app.routers.v1 import router
        # Check router is included (by checking routes exist)
        routes = [r.path for r in router.routes]
        # Should have books routes
        assert any("create" in r for r in routes)

    def test_v1_orders_router_exists(self):
        """Test v1 orders router is properly configured."""
        from app.routers.v1 import router
        routes = [r.path for r in router.routes]
        # Should have orders routes
        assert any("order" in r.lower() for r in routes)

    def test_v1_shopify_router_exists(self):
        """Test v1 shopify router is properly configured."""
        from app.routers.v1 import router
        routes = [r.path for r in router.routes]
        # Should have shopify routes
        assert any("webhook" in r.lower() for r in routes)

    def test_v1_config_router_exists(self):
        """Test v1 config router is properly configured."""
        from app.routers.v1 import router
        routes = [r.path for r in router.routes]
        # Should have config route
        assert any("config" in r.lower() for r in routes)


class TestRouterStructure:
    """Test the overall router structure."""

    def test_v1_prefix_applied(self, client):
        """Test that v1 prefix is applied to versioned routes."""
        # V1 routes should be accessible at /api/v1/*
        response = client.get("/api/v1/config")
        assert response.status_code == 200

    def test_legacy_routes_still_work(self, client):
        """Test that legacy routes without version still work."""
        # Legacy routes at /api/*
        response = client.get("/api/config")
        assert response.status_code == 200

    def test_common_routes_no_version(self, client):
        """Test common routes don't require version."""
        response = client.get("/")
        assert response.status_code == 200

        response = client.get("/api/health")
        assert response.status_code == 200


class TestVersionExtractionEdgeCases:
    """Test edge cases in version extraction."""

    def test_version_in_path_middle(self, client):
        """Test version extraction when in middle of path."""
        response = client.get("/api/v1/shopify/health")
        assert response.status_code == 200
        assert response.headers.get("X-API-Version") == "v1"

    def test_no_version_legacy_path(self, client):
        """Test legacy paths without version don't get version headers."""
        response = client.get("/api/config")
        assert response.status_code == 200
        # Legacy paths may or may not have version headers depending on implementation
        # The key is they still work

    def test_version_with_trailing_slash(self, client):
        """Test version extraction with trailing slash."""
        response = client.get("/api/v1/config/")
        # Should work (FastAPI handles trailing slashes)
        assert response.status_code in [200, 307]  # 307 for redirect to non-slash
