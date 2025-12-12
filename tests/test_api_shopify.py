# tests/test_api_shopify.py
"""
Tests for Shopify webhook endpoints.
Tests webhook verification and order processing.
"""

import pytest
import json
import hmac
import hashlib
import base64
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock

from main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def sample_order():
    """Sample Shopify order payload."""
    return {
        "id": 123456789,
        "email": "customer@example.com",
        "note": "story_id:e921daea-d19c-4758-8129-e2b19e709687",
        "line_items": [
            {
                "id": 1,
                "title": "Personalized Storybook - Hardcover",
                "variant_title": "Hardcover",
                "sku": "BOOK-HC-001",
                "properties": [
                    {"name": "story_id", "value": "e921daea-d19c-4758-8129-e2b19e709687"}
                ]
            }
        ],
        "shipping_address": {
            "name": "John Doe",
            "address1": "123 Main St",
            "city": "New York",
            "province": "NY",
            "zip": "10001",
            "country": "US"
        }
    }


@pytest.fixture
def mock_database():
    """Mock the database service."""
    with patch("app.routers.shopify.get_database") as mock_get:
        db_mock = MagicMock()
        
        # Make get_full_book return an async mock
        async def mock_get_full_book(story_id):
            if story_id == "e921daea-d19c-4758-8129-e2b19e709687":
                return {
                    "book_id": story_id,
                    "title": "Jishitha's Christmas Adventure",
                    "child_name": "Jishitha",
                    "child_age": 3,
                    "theme": "christmas",
                    "pages": [{"page_number": 1, "text": "Test page"}],
                    "character_bible": {"main_character": "Jishitha, 3 years old"}
                }
            return None
        
        db_mock.get_full_book = mock_get_full_book
        mock_get.return_value = db_mock
        yield db_mock


@pytest.fixture
def mock_print_service():
    """Mock the print service."""
    with patch("app.routers.shopify.get_print_service") as mock_get:
        service_mock = MagicMock()
        job_mock = MagicMock()
        job_mock.job_id = "job_123"
        
        # Make start_print_production async
        async def mock_start_production(*args, **kwargs):
            return job_mock
        
        service_mock.start_print_production = mock_start_production
        mock_get.return_value = service_mock
        yield service_mock


def create_webhook_signature(body: bytes, secret: str) -> str:
    """Create a valid Shopify webhook signature."""
    computed = hmac.new(
        secret.encode('utf-8'),
        body,
        hashlib.sha256
    ).digest()
    return base64.b64encode(computed).decode('utf-8')


class TestShopifyHealth:
    """Tests for GET /api/shopify/health endpoint."""
    
    def test_shopify_health_check(self, client):
        """Test Shopify integration health check."""
        response = client.get("/api/shopify/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
        assert "webhook_secret_configured" in data
        assert "store_url_configured" in data


class TestWebhookVerification:
    """Tests for webhook signature verification."""
    
    @patch("app.routers.shopify.verify_webhook_signature", return_value=True)
    def test_webhook_accepted_with_mocked_verification(
        self, mock_verify, client, sample_order, mock_database, mock_print_service
    ):
        """Test webhook is accepted when verification is mocked."""
        response = client.post(
            "/api/shopify/webhooks/orders/create",
            json=sample_order,
        )
        
        assert response.status_code == 200
    
    def test_webhook_rejected_with_invalid_signature(self, client, sample_order):
        """Test webhook is rejected with invalid signature."""
        body = json.dumps(sample_order).encode()
        
        response = client.post(
            "/api/shopify/webhooks/orders/create",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Shopify-Hmac-SHA256": "invalid_signature"
            }
        )
        
        assert response.status_code == 401


class TestOrderProcessing:
    """Tests for order processing logic."""
    
    @patch("app.utils.security.verify_webhook_signature", return_value=True)
    def test_webhook_without_story_id_skipped(self, mock_verify, client):
        """Test webhook without story_id is skipped."""
        order = {
            "id": 123456789,
            "email": "customer@example.com",
            "line_items": [{"title": "Other Product"}]
        }
        
        response = client.post(
            "/api/shopify/webhooks/orders/create",
            json=order
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "skipped"
    
    @patch("app.utils.security.verify_webhook_signature", return_value=True)
    def test_webhook_story_not_found(self, mock_verify, client, mock_database):
        """Test webhook returns 404 when story not found in database."""
        order = {
            "id": 123456789,
            "note": "story_id:nonexistent-uuid",
            "line_items": []
        }
        
        response = client.post(
            "/api/shopify/webhooks/orders/create",
            json=order
        )
        
        assert response.status_code == 404
    
    @patch("app.utils.security.verify_webhook_signature", return_value=True)
    def test_webhook_successful_processing(
        self, mock_verify, client, sample_order, mock_database, mock_print_service
    ):
        """Test webhook processes order successfully with database."""
        response = client.post(
            "/api/shopify/webhooks/orders/create",
            json=sample_order
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processing"
        assert data["story_id"] == "e921daea-d19c-4758-8129-e2b19e709687"
        assert data["format"] == "hardcover"
        assert "job_id" in data


class TestStoryIdExtraction:
    """Tests for extracting story_id from orders."""
    
    @patch("app.utils.security.verify_webhook_signature", return_value=True)
    def test_extract_story_id_from_note(
        self, mock_verify, client, mock_database, mock_print_service
    ):
        """Test extracting story_id from order note."""
        order = {
            "id": 123,
            "note": "story_id:e921daea-d19c-4758-8129-e2b19e709687\nOther notes",
            "line_items": []
        }
        
        response = client.post(
            "/api/shopify/webhooks/orders/create",
            json=order
        )
        
        assert response.status_code == 200
        assert response.json()["story_id"] == "e921daea-d19c-4758-8129-e2b19e709687"
    
    @patch("app.utils.security.verify_webhook_signature", return_value=True)
    def test_extract_story_id_from_line_item_properties(
        self, mock_verify, client, mock_database, mock_print_service
    ):
        """Test extracting story_id from line item properties."""
        order = {
            "id": 123,
            "line_items": [
                {
                    "title": "Book",
                    "properties": [
                        {"name": "story_id", "value": "e921daea-d19c-4758-8129-e2b19e709687"}
                    ]
                }
            ]
        }
        
        response = client.post(
            "/api/shopify/webhooks/orders/create",
            json=order
        )
        
        assert response.status_code == 200
        assert response.json()["story_id"] == "e921daea-d19c-4758-8129-e2b19e709687"


class TestFormatDetection:
    """Tests for detecting book format from orders."""
    
    @patch("app.utils.security.verify_webhook_signature", return_value=True)
    def test_detect_hardcover_format(
        self, mock_verify, client, mock_database, mock_print_service
    ):
        """Test detecting hardcover format from line item."""
        order = {
            "id": 123,
            "note": "story_id:e921daea-d19c-4758-8129-e2b19e709687",
            "line_items": [{"title": "Book - Hardcover Edition"}]
        }
        
        response = client.post(
            "/api/shopify/webhooks/orders/create",
            json=order
        )
        
        assert response.json()["format"] == "hardcover"
    
    @patch("app.utils.security.verify_webhook_signature", return_value=True)
    def test_detect_softcover_format(
        self, mock_verify, client, mock_database, mock_print_service
    ):
        """Test detecting softcover format from line item."""
        order = {
            "id": 123,
            "note": "story_id:e921daea-d19c-4758-8129-e2b19e709687",
            "line_items": [{"title": "Book - Softcover"}]
        }
        
        response = client.post(
            "/api/shopify/webhooks/orders/create",
            json=order
        )
        
        assert response.json()["format"] == "softcover"
    
    @patch("app.utils.security.verify_webhook_signature", return_value=True)
    def test_detect_digital_format(
        self, mock_verify, client, mock_database, mock_print_service
    ):
        """Test detecting digital format from line item."""
        order = {
            "id": 123,
            "note": "story_id:e921daea-d19c-4758-8129-e2b19e709687",
            "line_items": [{"title": "Book - Digital PDF Download"}]
        }
        
        response = client.post(
            "/api/shopify/webhooks/orders/create",
            json=order
        )
        
        assert response.json()["format"] == "digital"


class TestOtherWebhooks:
    """Tests for other Shopify webhook endpoints."""
    
    @patch("app.utils.security.verify_webhook_signature", return_value=True)
    def test_order_fulfilled_webhook(self, mock_verify, client):
        """Test order fulfilled webhook."""
        response = client.post(
            "/api/shopify/webhooks/orders/fulfilled",
            json={"id": 123}
        )
        
        assert response.status_code == 200
        assert response.json()["status"] == "acknowledged"
    
    @patch("app.utils.security.verify_webhook_signature", return_value=True)
    def test_order_cancelled_webhook(self, mock_verify, client):
        """Test order cancelled webhook."""
        response = client.post(
            "/api/shopify/webhooks/orders/cancelled",
            json={"id": 123}
        )
        
        assert response.status_code == 200
        assert response.json()["status"] == "acknowledged"
