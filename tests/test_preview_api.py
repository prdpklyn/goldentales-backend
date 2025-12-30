# tests/test_preview_api.py
"""
Tests for V2 Preview API Endpoints
===================================
Tests for the Kids 60s Magic Preview flow endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch

from main import app
from app.routers.v2.preview import require_api_key
from app.routers.v2.photo import require_jwt_auth
from app.middleware.auth import APIKeyData
from app.middleware.jwt_auth import JWTUser


# Mock API key for testing
async def mock_api_key_dependency():
    """Mock API key dependency."""
    return APIKeyData(
        key_id="test-key-123",
        name="Test Key",
        rate_limit_tier="standard",
        is_active=True
    )


# Mock JWT user for testing
async def mock_jwt_dependency():
    """Mock JWT dependency."""
    return JWTUser(
        user_id="test-user-123",
        email="test@example.com"
    )


# Test client with mocked auth
@pytest.fixture
def client():
    """Create test client with mocked authentication."""
    # Override dependencies
    app.dependency_overrides[require_api_key] = mock_api_key_dependency
    app.dependency_overrides[require_jwt_auth] = mock_jwt_dependency

    client = TestClient(app)
    yield client

    # Clean up
    app.dependency_overrides.clear()


# Mock preview service
@pytest.fixture
def mock_preview_service():
    """Mock PreviewService for testing."""
    with patch("app.routers.v2.preview.PreviewService") as MockService:
        mock_service = MockService.return_value
        yield mock_service


# Mock photo character service
@pytest.fixture
def mock_photo_service():
    """Mock PhotoCharacterService for testing."""
    with patch("app.routers.v2.photo.get_photo_character_service") as mock:
        mock_service = MagicMock()
        mock.return_value = mock_service
        yield mock_service


class TestQuickPreviewEndpoint:
    """Tests for POST /api/v2/preview/quick"""

    def test_quick_preview_success(self, client, mock_preview_service):
        """Test successful quick preview generation."""
        # Mock service response
        mock_preview_service.generate_quick_preview = AsyncMock(return_value={
            "preview_id": "preview-123",
            "title": "Emma's Space Adventure",
            "cover": {
                "image_url": "https://cdn.example.com/cover.jpg",
                "prompt_used": "watercolor illustration..."
            },
            "hero_portrait": {
                "image_url": "https://cdn.example.com/hero.jpg",
                "is_placeholder": True
            },
            "spreads": [
                {
                    "page_number": 1,
                    "image_url": "https://cdn.example.com/page1.jpg",
                    "text": "Emma looked up at the stars..."
                },
                {
                    "page_number": 2,
                    "image_url": "https://cdn.example.com/page2.jpg",
                    "text": "Her spaceship was ready..."
                }
            ],
            "metadata": {
                "generation_time_ms": 45000,
                "model_version": "v2.1",
                "art_style": "watercolor"
            }
        })

        # Make request
        response = client.post(
            "/api/v2/preview/quick",
            json={
                "child_name": "Emma",
                "child_gender": "girl",
                "age_band": "6-8",
                "theme": "space",
                "photo_url": None,
                "session_id": "session-123"
            }
        )

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["preview_id"] == "preview-123"
        assert data["title"] == "Emma's Space Adventure"
        assert len(data["spreads"]) == 2
        assert data["metadata"]["generation_time_ms"] < 60000  # Under 60 seconds

    def test_quick_preview_invalid_age_band(self, client):
        """Test quick preview with invalid age_band."""
        response = client.post(
            "/api/v2/preview/quick",
            json={
                "child_name": "Emma",
                "child_gender": "girl",
                "age_band": "invalid",
                "theme": "space",
                "session_id": "session-123"
            }
        )

        assert response.status_code == 422
        assert "age_band" in response.text.lower()

    def test_quick_preview_invalid_theme(self, client):
        """Test quick preview with invalid theme."""
        response = client.post(
            "/api/v2/preview/quick",
            json={
                "child_name": "Emma",
                "child_gender": "girl",
                "age_band": "6-8",
                "theme": "invalid",
                "session_id": "session-123"
            }
        )

        assert response.status_code == 422
        assert "theme" in response.text.lower()


class TestLikenessVariantsEndpoint:
    """Tests for POST /api/v2/photo/likeness-variants"""

    def test_likeness_variants_success(self, client, mock_photo_service):
        """Test successful likeness variant generation."""
        # Mock service response
        mock_photo_service.generate_likeness_variants = AsyncMock(return_value={
            "variants": [
                {
                    "id": "var_a_123",
                    "image_url": "https://cdn.example.com/variant-a.jpg",
                    "likeness_score": 92,
                    "style_label": "A",
                    "description": "Warm, expressive watercolor with soft edges",
                    "style_attributes": {
                        "warmth": "high",
                        "detail": "medium",
                        "expressiveness": "high"
                    }
                },
                {
                    "id": "var_b_123",
                    "image_url": "https://cdn.example.com/variant-b.jpg",
                    "likeness_score": 88,
                    "style_label": "B",
                    "description": "Soft, dreamy watercolor with gentle tones",
                    "style_attributes": {
                        "warmth": "medium",
                        "detail": "low",
                        "expressiveness": "medium"
                    }
                },
                {
                    "id": "var_c_123",
                    "image_url": "https://cdn.example.com/variant-c.jpg",
                    "likeness_score": 85,
                    "style_label": "C",
                    "description": "Bold, vibrant watercolor with rich colors",
                    "style_attributes": {
                        "warmth": "high",
                        "detail": "high",
                        "expressiveness": "high"
                    }
                }
            ],
            "processing_time_ms": 8000,
            "source_photo_analysis": {
                "face_detected": True,
                "quality_score": 95,
                "lighting": "good",
                "angle": "frontal"
            }
        })

        # Make request
        response = client.post(
            "/api/v2/photo/likeness-variants",
            json={
                "photo_url": "https://example.com/photo.jpg",
                "art_style": "watercolor",
                "child_name": "Emma",
                "child_gender": "girl",
                "age_band": "6-8",
                "num_variants": 3
            }
        )

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert len(data["variants"]) == 3
        assert data["variants"][0]["style_label"] == "A"
        assert data["source_photo_analysis"]["face_detected"] is True
        assert data["processing_time_ms"] < 15000  # Under 15 seconds


class TestPreviewRegenerateEndpoint:
    """Tests for POST /api/v2/preview/regenerate"""

    def test_regenerate_preview_success(self, client, mock_preview_service):
        """Test successful preview regeneration."""
        # Mock service response (matching actual service response structure)
        mock_preview_service.regenerate_preview = AsyncMock(return_value={
            "preview_id": "preview-123",
            "hero_portrait": {
                "image_url": "https://cdn.example.com/hero-updated.jpg",
                "is_placeholder": False
            },
            "spreads": [
                {
                    "page_number": 1,
                    "image_url": "https://cdn.example.com/page1-v2.jpg",
                    "text": "Emma and her robot companion zoomed...",
                    "updated": True
                },
                {
                    "page_number": 2,
                    "image_url": "https://cdn.example.com/page2-v2.jpg",
                    "text": "The stars seemed brighter than ever!",
                    "updated": True
                }
            ],
            "metadata": {
                "regeneration_time_ms": 12000,
                "tweaks_applied": {
                    "tone": "adventurous",
                    "art_modifier": "brighter",
                    "sidekick": "robot"
                }
            }
        })

        # Make request
        response = client.post(
            "/api/v2/preview/regenerate",
            json={
                "preview_id": "preview-123",
                "character_reference_url": "https://cdn.example.com/variant-a.jpg",
                "tweaks": {
                    "tone": "adventurous",
                    "art_modifier": "brighter",
                    "sidekick": "robot"
                }
            }
        )

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["preview_id"] == "preview-123"
        assert data["hero_portrait"]["image_url"] == "https://cdn.example.com/hero-updated.jpg"
        assert data["hero_portrait"]["is_placeholder"] is False
        assert len(data["spreads"]) == 2
        assert data["spreads"][0]["updated"] is True
        assert data["metadata"]["regeneration_time_ms"] < 15000  # Under 15 seconds

    def test_regenerate_preview_not_found(self, client, mock_preview_service):
        """Test regenerate with non-existent preview_id."""
        from app.utils.exceptions import ValidationException

        mock_preview_service.regenerate_preview = AsyncMock(
            side_effect=ValidationException("Preview not found or expired")
        )

        response = client.post(
            "/api/v2/preview/regenerate",
            json={
                "preview_id": "nonexistent",
                "tweaks": {}
            }
        )

        assert response.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
