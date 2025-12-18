# tests/test_v2_api_photo.py
"""
Comprehensive tests for V2 Photo Character API endpoints.
Tests photo validation, preview generation, and approval workflow.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock

from main import app
from app.models.enums import ArtStyle


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def valid_photo_request():
    """Valid photo validation request."""
    return {
        "photo_url": "https://example.com/photo.jpg"
    }


@pytest.fixture
def preview_request():
    """Valid character preview request."""
    return {
        "photo_url": "https://example.com/photo.jpg",
        "art_style": "watercolor",
        "preserve_likeness": True
    }


class TestPhotoValidation:
    """Tests for POST /api/v2/photo/validate endpoint."""
    
    @patch("app.routers.v2.photo.get_photo_character_service")
    def test_validate_photo_success(
        self,
        mock_get_service,
        client,
        valid_photo_request
    ):
        """Test successful photo validation."""
        mock_service = mock_get_service.return_value
        mock_service.validate_photo = AsyncMock(return_value={
            "valid": True,
            "message": "Photo is valid",
            "face_detected": True,
            "confidence": 0.95,
            "issues": []
        })
        
        response = client.post("/api/v2/photo/validate", json=valid_photo_request)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["valid"] is True
        assert data["face_detected"] is True
        assert data["confidence"] == 0.95
        assert len(data["issues"]) == 0
    
    @patch("app.routers.v2.photo.get_photo_character_service")
    def test_validate_photo_no_face(
        self,
        mock_get_service,
        client,
        valid_photo_request
    ):
        """Test photo validation fails when no face detected."""
        mock_service = mock_get_service.return_value
        mock_service.validate_photo = AsyncMock(return_value={
            "valid": False,
            "message": "No face detected in photo",
            "face_detected": False,
            "confidence": 0.0,
            "issues": ["no_face"]
        })
        
        response = client.post("/api/v2/photo/validate", json=valid_photo_request)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["valid"] is False
        assert data["face_detected"] is False
        assert "no_face" in data["issues"]
    
    @patch("app.routers.v2.photo.get_photo_character_service")
    def test_validate_photo_low_quality(
        self,
        mock_get_service,
        client,
        valid_photo_request
    ):
        """Test photo validation fails for low quality."""
        mock_service = mock_get_service.return_value
        mock_service.validate_photo = AsyncMock(return_value={
            "valid": False,
            "message": "Photo quality is too low",
            "face_detected": True,
            "confidence": 0.3,
            "issues": ["low_quality", "blurry"]
        })
        
        response = client.post("/api/v2/photo/validate", json=valid_photo_request)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["valid"] is False
        assert data["confidence"] < 0.5
        assert "low_quality" in data["issues"]
    
    @patch("app.routers.v2.photo.get_photo_character_service")
    def test_validate_photo_invalid_url(
        self,
        mock_get_service,
        client
    ):
        """Test photo validation with invalid URL."""
        mock_service = mock_get_service.return_value
        # Service returns validation result, doesn't raise
        mock_service.validate_photo = AsyncMock(return_value={
            "valid": False,
            "message": "Invalid photo URL format",
            "face_detected": False,
            "confidence": 0.0,
            "issues": ["URL must start with http:// or https://"]
        })
        
        # Use a valid URL format that will pass Pydantic validation but fail service validation
        # Pydantic requires http:// or https://, so we'll use a valid format URL
        response = client.post("/api/v2/photo/validate", json={"photo_url": "http://invalid-url-that-fails-service-validation.com/photo.jpg"})
        
        # Service returns result, not error - should be 200
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        # Service may return different messages for invalid URLs
        assert "valid" in data
    
    def test_validate_photo_missing_url(self, client):
        """Test photo validation fails with missing URL."""
        response = client.post("/api/v2/photo/validate", json={})
        
        assert response.status_code == 422  # Validation error


class TestCharacterPreview:
    """Tests for POST /api/v2/photo/preview endpoint."""
    
    @patch("app.routers.v2.photo.get_photo_character_service")
    def test_preview_character_success(
        self,
        mock_get_service,
        client,
        preview_request
    ):
        """Test successful character preview generation."""
        mock_service = mock_get_service.return_value
        
        # Mock validation
        mock_service.validate_photo = AsyncMock(return_value={
            "valid": True,
            "message": "Photo is valid",
            "face_detected": True,
            "confidence": 0.95,
            "issues": []
        })
        
        # Mock preview generation
        mock_service.generate_character_preview = AsyncMock(return_value={
            "preview_id": "preview-123",
            "original_photo_url": "https://example.com/photo.jpg",
            "character_image_url": "https://example.com/character.jpg",
            "art_style": "watercolor",
            "message": "Character preview generated successfully",
            "preserve_likeness": True,
            "expires_at": "2024-12-17T10:00:00Z"
        })
        
        response = client.post("/api/v2/photo/preview", json=preview_request)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["preview_id"] == "preview-123"
        assert "character_image_url" in data
        assert data["art_style"] == "watercolor"
        assert "message" in data
        assert "expires_at" in data
    
    @patch("app.routers.v2.photo.get_photo_character_service")
    def test_preview_character_validation_fails(
        self,
        mock_get_service,
        client,
        preview_request
    ):
        """Test preview fails if photo validation fails."""
        mock_service = mock_get_service.return_value
        
        mock_service.validate_photo = AsyncMock(return_value={
            "valid": False,
            "message": "No face detected",
            "face_detected": False,
            "confidence": 0.0,
            "issues": ["no_face"]
        })
        
        response = client.post("/api/v2/photo/preview", json=preview_request)
        
        assert response.status_code == 400
        # Error format uses "message" for custom exceptions
        error_msg = response.json().get("message", response.json().get("detail", ""))
        assert "validation failed" in error_msg.lower()
    
    @patch("app.routers.v2.photo.get_photo_character_service")
    def test_preview_character_external_service_error(
        self,
        mock_get_service,
        client,
        preview_request
    ):
        """Test preview handles external service errors."""
        from app.utils.exceptions import ExternalServiceException
        
        mock_service = mock_get_service.return_value
        mock_service.validate_photo = AsyncMock(return_value={
            "valid": True,
            "message": "Photo is valid",
            "face_detected": True,
            "confidence": 0.95,
            "issues": []
        })
        mock_service.generate_character_preview = AsyncMock(
            side_effect=ExternalServiceException(
                service_name="Fal.ai",
                message="Service unavailable",
                is_transient=True
            )
        )
        
        response = client.post("/api/v2/photo/preview", json=preview_request)
        
        assert response.status_code == 502
        # Error format uses "message" for custom exceptions
        error_msg = response.json().get("message", response.json().get("detail", ""))
        assert "service" in error_msg.lower()
    
    def test_preview_character_invalid_art_style(self, client):
        """Test preview fails with invalid art style."""
        response = client.post("/api/v2/photo/preview", json={
            "photo_url": "https://example.com/photo.jpg",
            "art_style": "invalid_style",
            "preserve_likeness": True
        })
        
        assert response.status_code == 422  # Validation error


class TestCharacterApproval:
    """Tests for POST /api/v2/photo/approve/{preview_id} endpoint."""
    
    @patch("app.routers.v2.photo.get_photo_character_service")
    def test_approve_character_success(
        self,
        mock_get_service,
        client
    ):
        """Test successful character approval."""
        mock_service = mock_get_service.return_value
        mock_service.approve_character = AsyncMock(return_value={
            "approved": True,
            "character_reference_url": "https://example.com/character-ref.jpg",
            "message": "Character approved successfully"
        })
        
        response = client.post("/api/v2/photo/approve/preview-123")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["approved"] is True
        assert "character_reference_url" in data
        assert data["character_reference_url"] == "https://example.com/character-ref.jpg"
    
    @patch("app.routers.v2.photo.get_photo_character_service")
    def test_approve_character_not_found(
        self,
        mock_get_service,
        client
    ):
        """Test approval fails for non-existent preview."""
        mock_service = mock_get_service.return_value
        mock_service.approve_character = AsyncMock(
            side_effect=ValueError("Preview not found or expired")
        )
        
        response = client.post("/api/v2/photo/approve/nonexistent")
        
        assert response.status_code == 404
        # Error format uses "message" for custom exceptions
        error_msg = response.json().get("message", response.json().get("detail", ""))
        assert "not found" in error_msg.lower()
    
    @patch("app.routers.v2.photo.get_photo_character_service")
    def test_approve_character_expired(
        self,
        mock_get_service,
        client
    ):
        """Test approval fails for expired preview."""
        mock_service = mock_get_service.return_value
        mock_service.approve_character = AsyncMock(
            side_effect=ValueError("Preview session expired")
        )
        
        response = client.post("/api/v2/photo/approve/expired-123")
        
        assert response.status_code == 404
        # Error format uses "message" for custom exceptions
        error_msg = response.json().get("message", response.json().get("detail", ""))
        assert "expired" in error_msg.lower()


class TestGetPreviewStatus:
    """Tests for GET /api/v2/photo/preview/{preview_id} endpoint."""
    
    @patch("app.routers.v2.photo.get_photo_character_service")
    def test_get_preview_status_success(
        self,
        mock_get_service,
        client
    ):
        """Test successfully getting preview status."""
        mock_service = mock_get_service.return_value
        mock_service.get_preview_session = MagicMock(return_value={
            "preview_id": "preview-123",
            "character_image_url": "https://example.com/character.jpg",
            "art_style": "watercolor",
            "created_at": "2024-12-16T10:00:00Z",
            "expires_at": "2024-12-17T10:00:00Z",
            "approved": False
        })
        
        response = client.get("/api/v2/photo/preview/preview-123")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["preview_id"] == "preview-123"
        assert "character_image_url" in data
        assert data["approved"] is False
    
    @patch("app.routers.v2.photo.get_photo_character_service")
    def test_get_preview_status_not_found(
        self,
        mock_get_service,
        client
    ):
        """Test getting status for non-existent preview returns 404."""
        mock_service = mock_get_service.return_value
        mock_service.get_preview_session = MagicMock(return_value=None)
        
        response = client.get("/api/v2/photo/preview/nonexistent")
        
        assert response.status_code == 404
        # Error format uses "message" for custom exceptions
        error_msg = response.json().get("message", response.json().get("detail", ""))
        assert "not found" in error_msg.lower()

