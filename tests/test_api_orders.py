# tests/test_api_orders.py
"""
Tests for Orders API endpoints.
Tests pricing, order creation, and shipping options.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


class TestShippingOptions:
    """Tests for GET /api/shipping-options endpoint."""
    
    def test_get_shipping_options(self, client):
        """Test getting shipping options returns valid data."""
        response = client.get("/api/shipping-options")
        assert response.status_code == 200
        
        data = response.json()
        assert "options" in data
        assert "countdown" in data
        
        # Should have at least digital option
        options = data["options"]
        assert len(options) >= 1
        
        # Check digital option exists
        digital = next((o for o in options if o["tier"] == "digital"), None)
        assert digital is not None
        assert digital["available"] == True
    
    def test_shipping_options_have_required_fields(self, client):
        """Test each shipping option has required fields."""
        response = client.get("/api/shipping-options")
        data = response.json()
        
        for option in data["options"]:
            assert "tier" in option
            assert "name" in option
            assert "available" in option
            assert "estimated_arrival" in option
    
    def test_countdown_has_required_fields(self, client):
        """Test countdown has required fields."""
        response = client.get("/api/shipping-options")
        data = response.json()
        countdown = data["countdown"]
        
        assert "expired" in countdown
        assert "days" in countdown
        assert "hours" in countdown
        assert "minutes" in countdown
        assert "urgency" in countdown


class TestPricing:
    """Tests for GET /api/books/{book_id}/price endpoint."""
    
    def test_get_price_book_not_found(self, client):
        """Test getting price for non-existent book returns 404."""
        response = client.get(
            "/api/books/nonexistent/price",
            params={"format": "digital", "shipping": "digital", "gift_wrap": False}
        )
        assert response.status_code == 404
    
    @patch("app.routers.orders.get_book_storage")
    def test_get_price_digital(self, mock_storage, client):
        """Test digital book pricing."""
        mock_storage.return_value = {
            "test123": {"book_id": "test123", "title": "Test Book"}
        }
        
        response = client.get(
            "/api/books/test123/price",
            params={"format": "digital", "shipping": "digital", "gift_wrap": False}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["book_id"] == "test123"
        assert data["format"] == "digital"
        assert data["shipping_cost"] == 0
        assert data["gift_wrap_cost"] == 0
        assert data["base_price"] == 9.99
        assert data["total"] == 9.99
        assert data["currency"] == "USD"
    
    @patch("app.routers.orders.get_book_storage")
    def test_get_price_hardcover_standard(self, mock_storage, client):
        """Test hardcover with standard shipping pricing."""
        mock_storage.return_value = {
            "test123": {"book_id": "test123", "title": "Test Book"}
        }
        
        response = client.get(
            "/api/books/test123/price",
            params={"format": "hardcover", "shipping": "standard", "gift_wrap": False}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["format"] == "hardcover"
        assert data["base_price"] == 34.99
        assert data["shipping_cost"] == 5.99
        assert data["total"] == 40.98  # 34.99 + 5.99
    
    @patch("app.routers.orders.get_book_storage")
    def test_get_price_with_gift_wrap(self, mock_storage, client):
        """Test pricing includes gift wrap cost."""
        mock_storage.return_value = {
            "test123": {"book_id": "test123", "title": "Test Book"}
        }
        
        response = client.get(
            "/api/books/test123/price",
            params={"format": "softcover", "shipping": "standard", "gift_wrap": True}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["gift_wrap_cost"] == 5.00
        assert data["total"] == 35.98  # 24.99 + 5.99 + 5.00
    
    @patch("app.routers.orders.get_book_storage")
    def test_get_price_express_shipping(self, mock_storage, client):
        """Test express shipping pricing."""
        mock_storage.return_value = {
            "test123": {"book_id": "test123", "title": "Test Book"}
        }
        
        response = client.get(
            "/api/books/test123/price",
            params={"format": "softcover", "shipping": "express", "gift_wrap": False}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["shipping_cost"] == 14.99


class TestOrderCreation:
    """Tests for POST /api/orders/create endpoint."""
    
    def test_create_order_book_not_found(self, client):
        """Test creating order for non-existent book returns 404."""
        response = client.post(
            "/api/orders/create",
            json={
                "book_id": "nonexistent",
                "format": "digital",
                "shipping_tier": "digital",
                "gift_wrap": False
            }
        )
        assert response.status_code == 404
    
    @patch("app.routers.orders.get_book_storage")
    def test_create_order_success(self, mock_storage, client):
        """Test successful order creation."""
        mock_storage.return_value = {
            "test123": {"book_id": "test123", "title": "Emma's Christmas Adventure"}
        }
        
        response = client.post(
            "/api/orders/create",
            json={
                "book_id": "test123",
                "format": "digital",
                "shipping_tier": "digital",
                "gift_wrap": False
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "order_id" in data
        assert data["book_id"] == "test123"
        assert data["book_title"] == "Emma's Christmas Adventure"
        assert data["total"] == 9.99
        assert data["status"] == "pending_payment"
        assert "checkout_url" in data
    
    @patch("app.routers.orders.get_book_storage")
    def test_create_order_with_gift_wrap(self, mock_storage, client):
        """Test order creation with gift wrap."""
        mock_storage.return_value = {
            "test123": {"book_id": "test123", "title": "Test Book"}
        }
        
        response = client.post(
            "/api/orders/create",
            json={
                "book_id": "test123",
                "format": "hardcover",
                "shipping_tier": "standard",
                "gift_wrap": True,
                "gift_message": "Happy Birthday!"
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["total"] == 45.98  # 34.99 + 5.99 + 5.00


class TestOrderStatus:
    """Tests for GET /api/orders/{order_id}/status endpoint."""
    
    def test_get_order_status(self, client):
        """Test getting order status (placeholder implementation)."""
        response = client.get("/api/orders/test-order-id/status")
        assert response.status_code == 200
        
        data = response.json()
        assert "order_id" in data
        assert "status" in data
        assert "steps" in data
        
        # Check steps have required fields
        for step in data["steps"]:
            assert "name" in step
            assert "status" in step
