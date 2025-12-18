# tests/test_v2_api_books.py
"""
Comprehensive tests for V2 Books API endpoints.
Tests all tiers (Basic, Premium, Ultra) and Edge Function integration.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime

from main import app
from app.models.enums import BookTier, ArtStyle, Theme, GenerationQuality
from character_system import Gender, SkinTone, HairColor, HairStyle, EyeColor, BodyType
from tests.fixtures.edge_functions import mock_database_edge_service


def mock_edge_function_call(payload, method="POST"):
    """Helper to mock Edge Function calls based on payload."""
    # Determine which function based on payload structure
    if "story_data" in payload or ("child_name" in payload and "theme" in payload):
        return {"success": True, "data": {"id": "story-123", "child_name": "Emma", "created_at": datetime.now().isoformat()}}
    elif "page_data" in payload or ("story_id" in payload and "page_number" in payload):
        return {"success": True, "data": {"id": "page-1", "page_number": payload.get("page_number", 1)}}
    elif "updates" in payload:
        return {"success": True, "data": {"id": payload.get("story_id") or payload.get("page_id") or "story-123", "status": "preview"}}
    elif "story_id" in payload and "updates" not in payload:
        return {"success": True, "data": {"id": payload["story_id"], "child_name": "Emma", "theme": "christmas", "tier": "basic", "status": "preview", "created_at": datetime.now().isoformat()}}
    elif "page_id" in payload:
        return {"success": True, "data": {"id": payload["page_id"], "page_number": 1}}
    return {"success": True, "data": {}}


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def basic_book_request():
    """Valid BASIC tier book creation request."""
    from character_system import Gender, SkinTone, HairColor, HairStyle, EyeColor, BodyType
    return {
        "child_name": "Emma",
        "child_gender": Gender.GIRL.value,
        "child_age": 6,
        "skin_tone": SkinTone.LIGHT.value,
        "hair_color": HairColor.BROWN.value,
        "hair_style": HairStyle.PIGTAILS.value,
        "eye_color": EyeColor.BLUE.value,
        "body_type": BodyType.AVERAGE.value,
        "has_glasses": False,
        "has_freckles": True,
        "has_dimples": False,
        "theme": "christmas",
        "art_style": "watercolor",
        "tier": "basic",
        "additional_characters": []
    }


@pytest.fixture
def premium_book_request():
    """Valid PREMIUM tier book creation request."""
    from character_system import Gender, SkinTone, HairColor, HairStyle, EyeColor, BodyType
    return {
        "child_name": "Emma",
        "child_gender": Gender.GIRL.value,
        "child_age": 6,
        "skin_tone": SkinTone.LIGHT.value,
        "hair_color": HairColor.BROWN.value,
        "hair_style": HairStyle.PIGTAILS.value,
        "eye_color": EyeColor.BLUE.value,
        "body_type": BodyType.AVERAGE.value,
        "has_glasses": False,
        "has_freckles": True,
        "has_dimples": False,
        "theme": "christmas",
        "art_style": "watercolor",
        "tier": "premium",
        "additional_characters": []
    }


@pytest.fixture
def ultra_book_request():
    """Valid ULTRA tier book creation request."""
    from character_system import Gender, SkinTone, HairColor, HairStyle, EyeColor, BodyType
    return {
        "child_name": "Emma",
        "child_gender": Gender.GIRL.value,
        "child_age": 6,
        "skin_tone": SkinTone.LIGHT.value,
        "hair_color": HairColor.BROWN.value,
        "hair_style": HairStyle.PIGTAILS.value,
        "eye_color": EyeColor.BLUE.value,
        "body_type": BodyType.AVERAGE.value,
        "has_glasses": False,
        "has_freckles": True,
        "has_dimples": False,
        "theme": "christmas",
        "art_style": "watercolor",
        "tier": "ultra",
        "character_reference_url": "https://example.com/character-ref.jpg",
        "additional_characters": []
    }


@pytest.fixture
def mock_story_pages():
    """Mock story pages returned by story generator."""
    return [
        {
            "page_number": i + 1,
            "text": f"Story text for page {i + 1}",
            "scene_description": f"Scene description for page {i + 1}",
            "character_action": "standing",
            "mood": "happy",
            "characters_in_scene": ["Emma"]
        }
        for i in range(10)
    ]


@pytest.fixture
def mock_illustrations():
    """Mock illustrations returned by image generator."""
    return [
        {"url": f"https://example.com/image{i + 1}.png", "quality": "preview", "page_number": i + 1}
        for i in range(10)
    ]


@pytest.fixture
def mock_story_data():
    """Mock story data from database."""
    return {
        "id": "story-123",
        "child_name": "Emma",
        "child_age": 6,
        "theme": "christmas",
        "art_style": "watercolor",
        "tier": "basic",
        "status": "preview",
        "character_bible": {"main_character": "Emma, 6-year-old girl"},
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }


@pytest.fixture
def mock_pages_data():
    """Mock pages data from database."""
    return [
        {
            "id": f"page-{i + 1}",
            "story_id": "story-123",
            "page_number": i + 1,
            "text_content": f"Page {i + 1} text",
            "image_prompt": f"Page {i + 1} prompt",
            "image_url": f"https://example.com/page{i + 1}.jpg",
            "version": 1,
            "is_current": True,
            "created_at": datetime.now().isoformat()
        }
        for i in range(10)
    ]


class TestV2BookCreation:
    """Tests for POST /api/v2/books/create endpoint."""
    
    @patch("app.services.edge_function_client.EdgeFunctionClient.call")
    @patch("app.routers.v2.books.StoryGenerator")
    @patch("app.routers.v2.books.ImageGenerator")
    @patch("app.routers.v2.books.CharacterService")
    def test_create_basic_tier_book(
        self,
        MockCharacterService,
        MockImageGenerator,
        MockStoryGenerator,
        mock_edge_call,
        client,
        basic_book_request,
        mock_story_pages,
        mock_illustrations
    ):
        """Test creating a BASIC tier book."""
        # Setup Edge Function mocks
        async def edge_call_side_effect(payload, method="POST"):
            return mock_edge_function_call(payload, method)
        
        mock_edge_call.side_effect = edge_call_side_effect
        
        mock_character = MockCharacterService.return_value
        mock_character.create_profile = AsyncMock(return_value=(
            MagicMock(additional_characters=[]),
            {"main_character": "Emma, 6-year-old girl"}
        ))
        
        mock_story = MockStoryGenerator.return_value
        mock_story.generate_story = AsyncMock(return_value=mock_story_pages)
        
        mock_image = MockImageGenerator.return_value
        mock_image.generate_all_illustrations = AsyncMock(return_value=mock_illustrations)
        
        response = client.post("/api/v2/books/create", json=basic_book_request)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["book_id"] == "story-123"
        assert data["tier"] == "basic"
        assert data["child_name"] == "Emma"
        assert data["theme"] == "christmas"
        assert len(data["pages"]) == 10
        assert len(data["preview_images"]) == 10
        assert data["is_photo_based"] is False
        assert data["character_reference_url"] is None
    
    @patch("app.services.edge_function_client.EdgeFunctionClient.call")
    @patch("app.routers.v2.books.StoryGenerator")
    @patch("app.routers.v2.books.ImageGenerator")
    @patch("app.routers.v2.books.CharacterService")
    def test_create_premium_tier_book(
        self,
        MockCharacterService,
        MockImageGenerator,
        MockStoryGenerator,
        mock_edge_call,
        client,
        premium_book_request,
        mock_story_pages,
        mock_illustrations
    ):
        """Test creating a PREMIUM tier book."""
        async def edge_call_side_effect(payload, method="POST"):
            return mock_edge_function_call(payload, method)
        mock_edge_call.side_effect = edge_call_side_effect
        
        mock_character = MockCharacterService.return_value
        mock_character.create_profile = AsyncMock(return_value=(
            MagicMock(additional_characters=[]),
            {"main_character": "Emma, 6-year-old girl"}
        ))
        
        mock_story = MockStoryGenerator.return_value
        mock_story.generate_story = AsyncMock(return_value=mock_story_pages)
        
        mock_image = MockImageGenerator.return_value
        mock_image.generate_all_illustrations_with_tier = AsyncMock(return_value=mock_illustrations)
        
        response = client.post("/api/v2/books/create", json=premium_book_request)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["tier"] == "premium"
        assert data["is_photo_based"] is False
        # Premium should use tier-aware generation
        mock_image.generate_all_illustrations_with_tier.assert_called_once()
    
    @patch("app.services.edge_function_client.EdgeFunctionClient.call")
    @patch("app.routers.v2.books.StoryGenerator")
    @patch("app.routers.v2.books.ImageGenerator")
    @patch("app.routers.v2.books.CharacterService")
    def test_create_ultra_tier_book(
        self,
        MockCharacterService,
        MockImageGenerator,
        MockStoryGenerator,
        mock_edge_call,
        client,
        ultra_book_request,
        mock_story_pages,
        mock_illustrations
    ):
        """Test creating an ULTRA tier book with photo reference."""
        async def edge_call_side_effect(payload, method="POST"):
            return mock_edge_function_call(payload, method)
        mock_edge_call.side_effect = edge_call_side_effect
        
        mock_character = MockCharacterService.return_value
        mock_character.create_profile = AsyncMock(return_value=(
            MagicMock(additional_characters=[]),
            {"main_character": "Emma, 6-year-old girl"}
        ))
        
        mock_story = MockStoryGenerator.return_value
        mock_story.generate_story = AsyncMock(return_value=mock_story_pages)
        
        mock_image = MockImageGenerator.return_value
        mock_image.generate_all_illustrations_with_tier = AsyncMock(return_value=mock_illustrations)
        
        mock_database_edge_service.create_story = AsyncMock(return_value={
            "id": "story-123",
            "created_at": datetime.now().isoformat()
        })
        mock_database_edge_service.create_page = AsyncMock(return_value={"id": "page-1"})
        mock_database_edge_service.update_story = AsyncMock(return_value={"id": "story-123"})
        
        response = client.post("/api/v2/books/create", json=ultra_book_request)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["tier"] == "ultra"
        assert data["is_photo_based"] is True
        assert data["character_reference_url"] == "https://example.com/character-ref.jpg"
        # Ultra should use tier-aware generation with character reference
        call_kwargs = mock_image.generate_all_illustrations_with_tier.call_args[1]
        assert call_kwargs["character_reference_url"] == ultra_book_request["character_reference_url"]
    
    def test_create_ultra_tier_missing_reference_url(self, client, ultra_book_request):
        """Test ULTRA tier requires character_reference_url."""
        ultra_book_request.pop("character_reference_url")
        
        response = client.post("/api/v2/books/create", json=ultra_book_request)
        
        assert response.status_code == 400
        assert "character_reference_url" in response.json()["message"].lower()
    
    def test_create_book_invalid_tier(self, client, basic_book_request):
        """Test book creation fails with invalid tier."""
        basic_book_request["tier"] = "invalid_tier"
        
        response = client.post("/api/v2/books/create", json=basic_book_request)
        
        assert response.status_code == 422  # Validation error
    
    @patch("app.services.edge_function_client.EdgeFunctionClient.call")
    @patch("app.routers.v2.books.StoryGenerator")
    @patch("app.routers.v2.books.ImageGenerator")
    @patch("app.routers.v2.books.CharacterService")
    def test_create_book_database_error(
        self,
        MockCharacterService,
        MockImageGenerator,
        MockStoryGenerator,
        mock_edge_call,
        client,
        basic_book_request
    ):
        """Test book creation handles database errors."""
        mock_character = MockCharacterService.return_value
        mock_character.create_profile = AsyncMock(return_value=(
            MagicMock(additional_characters=[]),
            {"main_character": "Emma"}
        ))
        
        # Simulate database error
        async def edge_call_error(payload, method="POST"):
            raise Exception("Database error")
        mock_edge_call.side_effect = edge_call_error
        
        response = client.post("/api/v2/books/create", json=basic_book_request)
        
        assert response.status_code == 500
        # Error format uses "message" not "detail"
        assert "Failed to create book" in response.json().get("message", "")


class TestV2GetBook:
    """Tests for GET /api/v2/books/{book_id} endpoint."""
    
    @patch("app.services.edge_function_client.EdgeFunctionClient.call")
    def test_get_book_success(
        self,
        mock_edge_call,
        client,
        mock_story_data,
        mock_pages_data
    ):
        """Test successfully retrieving a book."""
        call_count = 0
        async def edge_call_side_effect(payload, method="POST"):
            nonlocal call_count
            call_count += 1
            if call_count == 1:  # get_story
                return {"success": True, "data": mock_story_data}
            else:  # get_pages
                return {"success": True, "data": mock_pages_data}
        mock_edge_call.side_effect = edge_call_side_effect
        
        response = client.get("/api/v2/books/story-123")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["book_id"] == "story-123"
        assert data["child_name"] == "Emma"
        assert data["tier"] == "basic"
        assert len(data["pages"]) == 10
        assert len(data["preview_images"]) == 10
    
    @patch("app.services.edge_function_client.EdgeFunctionClient.call")
    def test_get_book_not_found(
        self,
        mock_edge_call,
        client
    ):
        """Test getting a non-existent book returns 404."""
        async def edge_call_side_effect(payload, method="POST"):
            return {"success": False, "error": "Story not found", "error_code": "not_found"}
        mock_edge_call.side_effect = edge_call_side_effect
        
        response = client.get("/api/v2/books/nonexistent")
        
        assert response.status_code == 404
        assert "not found" in response.json()["message"].lower()


class TestV2RegeneratePage:
    """Tests for POST /api/v2/books/{book_id}/regenerate-page/{page_number} endpoint."""
    
    @patch("app.services.edge_function_client.EdgeFunctionClient.call")
    @patch("app.routers.v2.books.ImageGenerator")
    def test_regenerate_page_basic_tier(
        self,
        MockImageGenerator,
        mock_edge_call,
        client,
        mock_story_data,
        mock_pages_data
    ):
        """Test regenerating a page for BASIC tier book."""
        mock_story_data["tier"] = "basic"
        call_count = 0
        async def edge_call_side_effect(payload, method="POST"):
            nonlocal call_count
            call_count += 1
            if call_count == 1:  # get_story
                return {"success": True, "data": mock_story_data}
            elif call_count == 2:  # get_pages (for get_page_by_number)
                return {"success": True, "data": mock_pages_data}
            else:  # update_page
                return {"success": True, "data": {"id": "page-1", "image_url": "https://example.com/new.jpg"}}
        mock_edge_call.side_effect = edge_call_side_effect
        
        mock_image = MockImageGenerator.return_value
        mock_image.generate_illustration = AsyncMock(return_value={
            "url": "https://example.com/new-image.jpg"
        })
        
        response = client.post(
            "/api/v2/books/story-123/regenerate-page/1",
            json={"mood": "excited"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["book_id"] == "story-123"
        assert data["page_number"] == 1
        assert "new_image_url" in data
        assert data["tier"] == "basic"
        # BASIC tier should use standard generation
        mock_image.generate_illustration.assert_called_once()
    
    @patch("app.services.edge_function_client.EdgeFunctionClient.call")
    @patch("app.routers.v2.books.ImageGenerator")
    def test_regenerate_page_premium_tier(
        self,
        MockImageGenerator,
        mock_edge_call,
        client,
        mock_story_data,
        mock_pages_data
    ):
        """Test regenerating a page for PREMIUM tier book."""
        mock_story_data["tier"] = "premium"
        call_count = 0
        async def edge_call_side_effect(payload, method="POST"):
            nonlocal call_count
            call_count += 1
            if call_count == 1:  # get_story
                return {"success": True, "data": mock_story_data}
            elif call_count == 2:  # get_pages
                return {"success": True, "data": mock_pages_data}
            else:  # update_page
                return {"success": True, "data": {"id": "page-1", "image_url": "https://example.com/new.jpg"}}
        mock_edge_call.side_effect = edge_call_side_effect
        
        mock_image = MockImageGenerator.return_value
        mock_image.generate_illustration_premium = AsyncMock(return_value={
            "url": "https://example.com/new-image.jpg"
        })
        
        response = client.post(
            "/api/v2/books/story-123/regenerate-page/1",
            json={"mood": "excited"}
        )
        
        assert response.status_code == 200
        # PREMIUM tier should use tier-aware generation
        mock_image.generate_illustration_premium.assert_called_once()
    
    @patch("app.services.edge_function_client.EdgeFunctionClient.call")
    def test_regenerate_page_book_not_found(
        self,
        mock_edge_call,
        client
    ):
        """Test regenerating page for non-existent book returns 404."""
        async def edge_call_side_effect(payload, method="POST"):
            return {"success": False, "error": "Story not found", "error_code": "not_found"}
        mock_edge_call.side_effect = edge_call_side_effect
        
        response = client.post(
            "/api/v2/books/nonexistent/regenerate-page/1",
            json={"mood": "happy"}
        )
        
        assert response.status_code == 404
    
    @patch("app.services.edge_function_client.EdgeFunctionClient.call")
    def test_regenerate_page_invalid_page_number(
        self,
        mock_edge_call,
        client,
        mock_story_data
    ):
        """Test regenerating invalid page number returns 400."""
        call_count = 0
        async def edge_call_side_effect(payload, method="POST"):
            nonlocal call_count
            call_count += 1
            if call_count == 1:  # get_story
                return {"success": True, "data": mock_story_data}
            else:  # get_pages - return empty list (page not found)
                return {"success": True, "data": []}
        mock_edge_call.side_effect = edge_call_side_effect
        
        response = client.post(
            "/api/v2/books/story-123/regenerate-page/99",
            json={"mood": "happy"}
        )
        
        assert response.status_code == 400
        assert "Invalid page number" in response.json()["message"]


class TestV2GetBookPreview:
    """Tests for GET /api/v2/books/{book_id}/preview endpoint."""
    
    @patch("app.services.edge_function_client.EdgeFunctionClient.call")
    def test_get_book_preview_success(
        self,
        mock_edge_call,
        client,
        mock_story_data,
        mock_pages_data
    ):
        """Test successfully getting book preview."""
        call_count = 0
        async def edge_call_side_effect(payload, method="POST"):
            nonlocal call_count
            call_count += 1
            if call_count == 1:  # get_story
                return {"success": True, "data": mock_story_data}
            else:  # get_pages
                return {"success": True, "data": mock_pages_data}
        mock_edge_call.side_effect = edge_call_side_effect
        
        response = client.get("/api/v2/books/story-123/preview")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["book_id"] == "story-123"
        assert "preview_images" in data
        assert len(data["preview_images"]) == 10
        assert data["page_count"] == 10
        assert data["tier"] == "basic"
        assert data["is_photo_based"] is False
    
    @patch("app.services.edge_function_client.EdgeFunctionClient.call")
    def test_get_book_preview_not_found(
        self,
        mock_edge_call,
        client
    ):
        """Test getting preview for non-existent book returns 404."""
        async def edge_call_side_effect(payload, method="POST"):
            return {"success": False, "error": "Story not found", "error_code": "not_found"}
        mock_edge_call.side_effect = edge_call_side_effect
        
        response = client.get("/api/v2/books/nonexistent/preview")
        
        assert response.status_code == 404

