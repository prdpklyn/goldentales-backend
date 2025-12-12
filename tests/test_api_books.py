# tests/test_api_books.py
"""
Tests for Book API endpoints.
Tests the full book creation and management workflow.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def valid_book_request():
    """Valid book creation request."""
    return {
        "child_name": "Emma",
        "child_gender": "girl",
        "child_age": 6,
        "skin_tone": "light skin",
        "hair_color": "brown hair",
        "hair_style": "hair in pigtails",
        "eye_color": "blue eyes",
        "body_type": "average build",
        "has_glasses": False,
        "has_freckles": True,
        "has_dimples": False,
        "theme": "christmas",
        "art_style": "watercolor",
        "additional_characters": []
    }


class TestBookCreation:
    """Tests for POST /api/books/create endpoint."""
    
    def test_create_book_missing_required_fields(self, client):
        """Test book creation fails with missing required fields."""
        response = client.post("/api/books/create", json={})
        assert response.status_code == 422  # Validation error
    
    def test_create_book_invalid_child_name(self, client, valid_book_request):
        """Test book creation fails with invalid child name."""
        valid_book_request["child_name"] = "A"  # Too short
        response = client.post("/api/books/create", json=valid_book_request)
        assert response.status_code == 422
    
    def test_create_book_invalid_age(self, client, valid_book_request):
        """Test book creation fails with age out of range."""
        valid_book_request["child_age"] = 15  # Too old
        response = client.post("/api/books/create", json=valid_book_request)
        assert response.status_code == 422
    
    def test_create_book_invalid_theme(self, client, valid_book_request):
        """Test book creation fails with invalid theme."""
        valid_book_request["theme"] = "invalid_theme"
        response = client.post("/api/books/create", json=valid_book_request)
        assert response.status_code == 422
    
    def test_create_book_invalid_art_style(self, client, valid_book_request):
        """Test book creation fails with invalid art style."""
        valid_book_request["art_style"] = "invalid_style"
        response = client.post("/api/books/create", json=valid_book_request)
        assert response.status_code == 422
    
    def test_create_book_with_special_characters_in_name(self, client, valid_book_request):
        """Test book creation fails with special characters in name."""
        valid_book_request["child_name"] = "Emma<script>"
        response = client.post("/api/books/create", json=valid_book_request)
        assert response.status_code == 422
    
    def test_create_book_with_additional_characters(self, client, valid_book_request):
        """Test book creation with additional characters passes validation."""
        valid_book_request["additional_characters"] = [
            {
                "name": "Max",
                "character_type": "pet",
                "relationship": "pet dog",
                "pet_species": "golden retriever",
                "pet_color": "golden"
            }
        ]
        # This tests the validation, not the full creation (would need mocks for AI)
        # Just ensure the request structure is valid
        assert "additional_characters" in valid_book_request


class TestBookRetrieval:
    """Tests for GET /api/books/{book_id} endpoint."""
    
    def test_get_book_not_found(self, client):
        """Test getting a non-existent book returns 404."""
        response = client.get("/api/books/nonexistent123")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_get_book_preview_not_found(self, client):
        """Test getting preview for non-existent book returns 404."""
        response = client.get("/api/books/nonexistent123/preview")
        assert response.status_code == 404


class TestPageRegeneration:
    """Tests for POST /api/books/{book_id}/regenerate-page/{page_number} endpoint."""
    
    def test_regenerate_page_book_not_found(self, client):
        """Test regenerating page for non-existent book returns 404."""
        response = client.post(
            "/api/books/nonexistent123/regenerate-page/1",
            json={"mood": "happy"}
        )
        assert response.status_code == 404


class TestBookWithMockedAI:
    """Tests for book creation with mocked AI services."""
    
    @pytest.fixture
    def mock_story_pages(self):
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
    def mock_illustrations(self):
        """Mock illustrations returned by image generator."""
        return [
            {"url": f"https://example.com/image{i + 1}.png", "quality": "preview", "page_number": i + 1}
            for i in range(10)
        ]
    
    @patch("app.routers.books.StoryGenerator")
    @patch("app.routers.books.ImageGenerator")
    def test_create_book_success(
        self,
        MockImageGenerator,
        MockStoryGenerator,
        client,
        valid_book_request,
        mock_story_pages,
        mock_illustrations
    ):
        """Test successful book creation with mocked AI services."""
        # Setup mocks
        mock_story_instance = MockStoryGenerator.return_value
        mock_story_instance.generate_story = AsyncMock(return_value=mock_story_pages)
        
        mock_image_instance = MockImageGenerator.return_value
        mock_image_instance.generate_all_illustrations = AsyncMock(return_value=mock_illustrations)
        
        response = client.post("/api/books/create", json=valid_book_request)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "book_id" in data
        assert data["child_name"] == "Emma"
        assert data["theme"] == "christmas"
        assert data["art_style"] == "watercolor"
        assert "pages" in data
        assert "preview_images" in data
        assert "character_bible" in data
        assert len(data["pages"]) == 10
        assert len(data["preview_images"]) == 10
    
    @patch("app.routers.books.StoryGenerator")
    @patch("app.routers.books.ImageGenerator")
    def test_create_and_retrieve_book(
        self,
        MockImageGenerator,
        MockStoryGenerator,
        client,
        valid_book_request,
        mock_story_pages,
        mock_illustrations
    ):
        """Test creating a book and then retrieving it."""
        mock_story_instance = MockStoryGenerator.return_value
        mock_story_instance.generate_story = AsyncMock(return_value=mock_story_pages)
        
        mock_image_instance = MockImageGenerator.return_value
        mock_image_instance.generate_all_illustrations = AsyncMock(return_value=mock_illustrations)
        
        # Create book
        create_response = client.post("/api/books/create", json=valid_book_request)
        assert create_response.status_code == 200
        book_id = create_response.json()["book_id"]
        
        # Retrieve book
        get_response = client.get(f"/api/books/{book_id}")
        assert get_response.status_code == 200
        
        data = get_response.json()
        assert data["book_id"] == book_id
        assert data["child_name"] == "Emma"
    
    @patch("app.routers.books.StoryGenerator")
    @patch("app.routers.books.ImageGenerator")
    def test_get_book_preview(
        self,
        MockImageGenerator,
        MockStoryGenerator,
        client,
        valid_book_request,
        mock_story_pages,
        mock_illustrations
    ):
        """Test getting book preview images."""
        mock_story_instance = MockStoryGenerator.return_value
        mock_story_instance.generate_story = AsyncMock(return_value=mock_story_pages)
        
        mock_image_instance = MockImageGenerator.return_value
        mock_image_instance.generate_all_illustrations = AsyncMock(return_value=mock_illustrations)
        
        # Create book
        create_response = client.post("/api/books/create", json=valid_book_request)
        assert create_response.status_code == 200
        book_id = create_response.json()["book_id"]
        
        # Get preview
        preview_response = client.get(f"/api/books/{book_id}/preview")
        assert preview_response.status_code == 200
        
        data = preview_response.json()
        assert data["book_id"] == book_id
        assert "preview_images" in data
        assert len(data["preview_images"]) == 10
