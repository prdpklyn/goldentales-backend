# tests/test_order_service.py
"""
GoldenTales Order Service Tests
===============================
Tests for order management, storage, and status tracking.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.models.enums import OrderStatus
from app.services.order_service import OrderService


def run_async(coro):
    """Helper to run async functions in sync tests."""
    return asyncio.get_event_loop().run_until_complete(coro)


class MockDatabaseService:
    """Mock database service for testing."""

    def __init__(self):
        self.orders = {}
        self.books = {}

    async def create_order(self, order_data):
        self.orders[order_data["id"]] = order_data
        return order_data

    async def get_order(self, order_id):
        return self.orders.get(order_id)

    async def get_order_by_shopify_id(self, shopify_order_id):
        for order in self.orders.values():
            if order.get("shopify_order_id") == shopify_order_id:
                return order
        return None

    async def update_order(self, order_id, updates):
        if order_id in self.orders:
            self.orders[order_id].update(updates)
            return self.orders[order_id]
        return None

    async def get_orders_by_customer(self, customer_email, limit=50):
        return [o for o in self.orders.values()
                if o.get("customer_email") == customer_email][:limit]

    async def get_orders_by_status(self, status, limit=100):
        return [o for o in self.orders.values()
                if o.get("status") == status][:limit]

    async def get_full_book(self, story_id):
        return self.books.get(story_id)

    async def get_order_with_book(self, order_id):
        order = await self.get_order(order_id)
        if not order:
            return None
        book = await self.get_full_book(order["story_id"])
        return {**order, "book": book}


class MockStorageService:
    """Mock storage service for testing."""

    def __init__(self, is_available=True):
        self._is_available = is_available
        self.uploaded_pdfs = {}
        self.deleted_orders = []

    @property
    def is_available(self):
        return self._is_available

    async def upload_order_pdf(self, order_id, book_id, pdf_path, metadata=None):
        result = {
            "storage_path": f"pdfs/orders/{order_id}/{book_id}_print.pdf",
            "signed_url": f"https://storage.example.com/signed/{order_id}",
            "uploaded_at": datetime.utcnow().isoformat()
        }
        self.uploaded_pdfs[order_id] = result
        return result

    async def get_order_pdf_url(self, order_id, book_id, expiry_hours=24):
        if order_id in self.uploaded_pdfs:
            return f"https://storage.example.com/signed/{order_id}?expires={expiry_hours}h"
        return None

    async def delete_order_assets(self, order_id):
        self.deleted_orders.append(order_id)
        return True


@pytest.fixture
def mock_db():
    """Create a mock database service."""
    return MockDatabaseService()


@pytest.fixture
def mock_storage():
    """Create a mock storage service."""
    return MockStorageService()


@pytest.fixture
def order_service(mock_db, mock_storage):
    """Create an order service with mock dependencies."""
    return OrderService(database=mock_db, storage=mock_storage)


class TestOrderCreation:
    """Tests for order creation."""

    def test_create_order_basic(self, order_service, mock_db):
        """Should create an order with basic fields."""
        result = run_async(order_service.create_order(
            story_id="story-123",
            format="hardcover",
            shipping_tier="standard",
            customer_email="test@example.com"
        ))

        assert result is not None
        assert result["story_id"] == "story-123"
        assert result["format"] == "hardcover"
        assert result["shipping_tier"] == "standard"
        assert result["customer_email"] == "test@example.com"
        assert result["status"] == OrderStatus.PENDING_PAYMENT.value
        assert len(result["status_history"]) == 1

    def test_create_order_with_shopify(self, order_service, mock_db):
        """Should create an order with Shopify references."""
        result = run_async(order_service.create_order(
            story_id="story-123",
            format="softcover",
            shipping_tier="express",
            customer_email="buyer@example.com",
            shopify_order_id="shopify-456",
            shopify_order_number="#1001"
        ))

        assert result["shopify_order_id"] == "shopify-456"
        assert result["shopify_order_number"] == "#1001"

    def test_create_order_with_gift_options(self, order_service, mock_db):
        """Should create an order with gift options."""
        result = run_async(order_service.create_order(
            story_id="story-123",
            format="hardcover",
            shipping_tier="express",
            customer_email="giver@example.com",
            gift_options={
                "is_gift": True,
                "message": "Happy Birthday!",
                "wrap": True,
                "recipient_email": "receiver@example.com"
            }
        ))

        assert result["is_gift"] is True
        assert result["gift_message"] == "Happy Birthday!"
        assert result["gift_wrap"] is True
        assert result["recipient_email"] == "receiver@example.com"

    def test_create_order_with_pricing(self, order_service, mock_db):
        """Should create an order with pricing details."""
        result = run_async(order_service.create_order(
            story_id="story-123",
            format="hardcover",
            shipping_tier="express",
            customer_email="buyer@example.com",
            pricing={
                "base_price": 29.99,
                "shipping_cost": 9.99,
                "gift_wrap_cost": 4.99,
                "discount_amount": 5.00,
                "tax_amount": 3.50,
                "total": 43.47,
                "currency": "USD"
            }
        ))

        assert result["base_price"] == 29.99
        assert result["shipping_cost"] == 9.99
        assert result["gift_wrap_cost"] == 4.99
        assert result["total_amount"] == 43.47
        assert result["currency"] == "USD"


class TestOrderStatusManagement:
    """Tests for order status updates."""

    def test_update_order_status(self, order_service, mock_db):
        """Should update order status and add to history."""
        # Create an order first
        order = run_async(order_service.create_order(
            story_id="story-123",
            format="hardcover",
            shipping_tier="standard",
            customer_email="test@example.com"
        ))

        # Update status
        result = run_async(order_service.update_order_status(
            order["id"],
            OrderStatus.PAYMENT_CONFIRMED,
            note="Payment received"
        ))

        assert result["status"] == OrderStatus.PAYMENT_CONFIRMED.value
        assert len(result["status_history"]) == 2
        assert result["status_history"][-1]["note"] == "Payment received"

    def test_process_payment_confirmed(self, order_service, mock_db):
        """Should process payment confirmation."""
        order = run_async(order_service.create_order(
            story_id="story-123",
            format="hardcover",
            shipping_tier="standard",
            customer_email="test@example.com"
        ))

        result = run_async(order_service.process_payment_confirmed(order["id"]))

        assert result["status"] == OrderStatus.PAYMENT_CONFIRMED.value

    def test_update_shipping_info(self, order_service, mock_db):
        """Should update order with shipping information."""
        order = run_async(order_service.create_order(
            story_id="story-123",
            format="hardcover",
            shipping_tier="express",
            customer_email="test@example.com"
        ))

        result = run_async(order_service.update_shipping_info(
            order["id"],
            tracking_number="1Z999AA10123456784",
            tracking_url="https://ups.com/track/1Z999AA10123456784"
        ))

        assert result["tracking_number"] == "1Z999AA10123456784"
        assert result["tracking_url"] == "https://ups.com/track/1Z999AA10123456784"
        assert result["shipped_at"] is not None
        assert result["status"] == OrderStatus.SHIPPED.value

    def test_mark_delivered(self, order_service, mock_db):
        """Should mark order as delivered."""
        order = run_async(order_service.create_order(
            story_id="story-123",
            format="hardcover",
            shipping_tier="standard",
            customer_email="test@example.com"
        ))

        result = run_async(order_service.mark_delivered(order["id"]))

        assert result["status"] == OrderStatus.DELIVERED.value
        assert result["delivered_at"] is not None


class TestPDFStorage:
    """Tests for PDF storage integration."""

    def test_store_order_pdf(self, order_service, mock_db, mock_storage):
        """Should store PDF and update order."""
        order = run_async(order_service.create_order(
            story_id="story-123",
            format="hardcover",
            shipping_tier="standard",
            customer_email="test@example.com"
        ))

        result = run_async(order_service.store_order_pdf(
            order_id=order["id"],
            book_id="book-123",
            pdf_path="/tmp/test.pdf",
            metadata={"page_count": 12}
        ))

        assert "storage_path" in result
        assert "signed_url" in result
        assert order["id"] in mock_storage.uploaded_pdfs

    def test_get_pdf_download_url(self, order_service, mock_db, mock_storage):
        """Should get fresh download URL for PDF."""
        order = run_async(order_service.create_order(
            story_id="story-123",
            format="hardcover",
            shipping_tier="standard",
            customer_email="test@example.com"
        ))

        # Store PDF first
        run_async(order_service.store_order_pdf(
            order_id=order["id"],
            book_id="book-123",
            pdf_path="/tmp/test.pdf"
        ))

        # Update order with storage path
        mock_db.orders[order["id"]]["pdf_storage_path"] = f"pdfs/orders/{order['id']}/book-123_print.pdf"

        url = run_async(order_service.get_pdf_download_url(order["id"], expiry_hours=48))

        assert url is not None
        assert "expires=48h" in url

    def test_storage_unavailable(self, mock_db):
        """Should handle storage unavailability gracefully."""
        storage = MockStorageService(is_available=False)
        service = OrderService(database=mock_db, storage=storage)

        order = run_async(service.create_order(
            story_id="story-123",
            format="hardcover",
            shipping_tier="standard",
            customer_email="test@example.com"
        ))

        result = run_async(service.store_order_pdf(
            order_id=order["id"],
            book_id="book-123",
            pdf_path="/tmp/test.pdf"
        ))

        assert "error" in result


class TestOrderRetrieval:
    """Tests for order retrieval operations."""

    def test_get_order(self, order_service, mock_db):
        """Should retrieve an order by ID."""
        order = run_async(order_service.create_order(
            story_id="story-123",
            format="hardcover",
            shipping_tier="standard",
            customer_email="test@example.com"
        ))

        result = run_async(order_service.get_order(order["id"]))

        assert result is not None
        assert result["id"] == order["id"]

    def test_get_order_by_shopify_id(self, order_service, mock_db):
        """Should retrieve order by Shopify ID."""
        order = run_async(order_service.create_order(
            story_id="story-123",
            format="hardcover",
            shipping_tier="standard",
            customer_email="test@example.com",
            shopify_order_id="shopify-789"
        ))

        result = run_async(order_service.get_order_by_shopify_id("shopify-789"))

        assert result is not None
        assert result["shopify_order_id"] == "shopify-789"

    def test_get_orders_by_customer(self, order_service, mock_db):
        """Should retrieve all orders for a customer."""
        # Create multiple orders
        run_async(order_service.create_order(
            story_id="story-1",
            format="hardcover",
            shipping_tier="standard",
            customer_email="repeat@customer.com"
        ))
        run_async(order_service.create_order(
            story_id="story-2",
            format="softcover",
            shipping_tier="express",
            customer_email="repeat@customer.com"
        ))
        run_async(order_service.create_order(
            story_id="story-3",
            format="digital",
            shipping_tier="digital",
            customer_email="other@customer.com"
        ))

        results = run_async(order_service.get_orders_by_customer("repeat@customer.com"))

        assert len(results) == 2
        assert all(r["customer_email"] == "repeat@customer.com" for r in results)

    def test_get_orders_by_status(self, order_service, mock_db):
        """Should retrieve orders by status."""
        order1 = run_async(order_service.create_order(
            story_id="story-1",
            format="hardcover",
            shipping_tier="standard",
            customer_email="test1@example.com"
        ))
        order2 = run_async(order_service.create_order(
            story_id="story-2",
            format="softcover",
            shipping_tier="express",
            customer_email="test2@example.com"
        ))

        # Update one order's status
        run_async(order_service.update_order_status(
            order1["id"],
            OrderStatus.PAYMENT_CONFIRMED
        ))

        pending = run_async(order_service.get_orders_by_status(OrderStatus.PENDING_PAYMENT))
        confirmed = run_async(order_service.get_orders_by_status(OrderStatus.PAYMENT_CONFIRMED))

        assert len(pending) == 1
        assert len(confirmed) == 1


class TestOrderCancellation:
    """Tests for order cancellation."""

    def test_cancel_order(self, order_service, mock_db, mock_storage):
        """Should cancel order and delete assets."""
        order = run_async(order_service.create_order(
            story_id="story-123",
            format="hardcover",
            shipping_tier="standard",
            customer_email="test@example.com"
        ))

        result = run_async(order_service.cancel_order(
            order["id"],
            reason="Customer requested cancellation"
        ))

        assert result["status"] == OrderStatus.CANCELLED.value
        assert order["id"] in mock_storage.deleted_orders

    def test_cancel_order_keep_assets(self, order_service, mock_db, mock_storage):
        """Should cancel order without deleting assets."""
        order = run_async(order_service.create_order(
            story_id="story-123",
            format="hardcover",
            shipping_tier="standard",
            customer_email="test@example.com"
        ))

        result = run_async(order_service.cancel_order(
            order["id"],
            reason="Refund processed",
            delete_assets=False
        ))

        assert result["status"] == OrderStatus.CANCELLED.value
        assert order["id"] not in mock_storage.deleted_orders
