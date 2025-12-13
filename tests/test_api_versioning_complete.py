# tests/test_api_versioning_complete.py
"""
Tests for API Versioning (Phase 1.4)
=====================================
Tests for versioning middleware, deprecation headers, and migration.
"""

import pytest
from fastapi.testclient import TestClient
from datetime import date

from main import app
from app.utils.deprecation import LEGACY_API_DEPRECATION_DATE, LEGACY_API_SUNSET_DATE


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestVersionedEndpoints:
    """Test v1 endpoints."""
    
    def test_v1_config_endpoint(self, client):
        """Test /api/v1/config returns versioning info."""
        response = client.get("/api/v1/config")
        assert response.status_code == 200
        
        data = response.json()
        assert "api" in data
        assert data["api"]["version"] == "v1"
        assert data["api"]["status"] == "current"
        assert data["api"]["deprecation"] is None
        assert data["api"]["sunset"] is None
    
    def test_v1_health_endpoint(self, client):
        """Test /api/v1/health works."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert "status" in response.json()
    
    def test_v1_no_deprecation_headers(self, client):
        """Test v1 endpoints don't have deprecation headers."""
        response = client.get("/api/v1/config")
        assert "Deprecation" not in response.headers
        assert "Sunset" not in response.headers
        assert "X-API-Warning" not in response.headers


class TestLegacyEndpoints:
    """Test legacy (deprecated) endpoints."""
    
    def test_legacy_config_has_deprecation_info(self, client):
        """Test /api/config returns deprecation info in response."""
        response = client.get("/api/config")
        assert response.status_code == 200
        
        data = response.json()
        assert "api" in data
        assert data["api"]["version"] == "legacy"
        assert data["api"]["status"] == "deprecated"
        assert data["api"]["deprecation"] == str(LEGACY_API_DEPRECATION_DATE)
        assert data["api"]["sunset"] == str(LEGACY_API_SUNSET_DATE)
        assert data["api"]["successor"] == "/api/v1/config"
    
    def test_legacy_has_deprecation_headers(self, client):
        """Test legacy endpoints include deprecation headers."""
        response = client.get("/api/config")
        
        # Check deprecation headers
        assert response.headers.get("Deprecation") == LEGACY_API_DEPRECATION_DATE.isoformat()
        assert response.headers.get("Sunset") == LEGACY_API_SUNSET_DATE.isoformat()
        assert "</api/v1>" in response.headers.get("Link", "")
        assert "X-API-Warning" in response.headers
        assert "2025-06-01" in response.headers.get("X-API-Warning", "")


class TestVersionAgnosticEndpoints:
    """Test endpoints that work across all versions."""
    
    def test_root_endpoint(self, client):
        """Test / endpoint works and has no deprecation."""
        response = client.get("/")
        assert response.status_code == 200
        assert "GoldenTales" in response.json()["service"]
        
        # Should not have deprecation headers
        assert "Deprecation" not in response.headers
    
    def test_health_endpoint(self, client):
        """Test /api/health endpoint works."""
        response = client.get("/api/health")
        assert response.status_code == 200
        assert "status" in response.json()


class TestDeprecationTimeline:
    """Test deprecation timeline configuration."""
    
    def test_deprecation_dates_configured(self):
        """Test deprecation dates are properly configured."""
        assert LEGACY_API_DEPRECATION_DATE == date(2025, 3, 1)
        assert LEGACY_API_SUNSET_DATE == date(2025, 6, 1)
        
        # Ensure sunset is after deprecation
        assert LEGACY_API_SUNSET_DATE > LEGACY_API_DEPRECATION_DATE


class TestBackwardCompatibility:
    """Test that legacy and v1 endpoints return compatible data."""
    
    def test_config_data_compatible(self, client):
        """Test legacy and v1 config return same core data."""
        legacy_response = client.get("/api/config")
        v1_response = client.get("/api/v1/config")
        
        assert legacy_response.status_code == 200
        assert v1_response.status_code == 200
        
        legacy_data = legacy_response.json()
        v1_data = v1_response.json()
        
        # Core data should be identical (ignoring api metadata)
        assert legacy_data["themes"] == v1_data["themes"]
        assert legacy_data["art_styles"] == v1_data["art_styles"]
        assert legacy_data["formats"] == v1_data["formats"]
        assert legacy_data["prices"] == v1_data["prices"]

