# app/services/order_service.py
"""
GoldenTales Order Service
=========================
Order management with database persistence and PDF storage integration.
"""

import asyncio
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List

from app.models.enums import OrderStatus
from app.services.database import DatabaseService, get_database
from app.services.storage_service import StorageService, get_storage_service
from app.utils.logging import get_logger

logger = get_logger(__name__)


class OrderService:
    """
    Manages orders with database persistence and PDF storage.

    Responsibilities:
    - Order creation and updates
    - Status tracking with history
    - PDF storage integration
    - Payment confirmation handling
    - Customer order retrieval
    """

    def __init__(
        self,
        database: Optional[DatabaseService] = None,
        storage: Optional[StorageService] = None
    ):
        self.db = database or get_database()
        self.storage = storage or get_storage_service()

    async def create_order(
        self,
        story_id: str,
        format: str,
        shipping_tier: str,
        customer_email: str,
        shopify_order_id: Optional[str] = None,
        shopify_order_number: Optional[str] = None,
        shipping_address: Optional[Dict] = None,
        gift_options: Optional[Dict] = None,
        pricing: Optional[Dict] = None,
        customer_name: Optional[str] = None,
        customer_phone: Optional[str] = None,
        book_size: str = "8x8",
        quantity: int = 1
    ) -> Dict[str, Any]:
        """
        Create a new order in the database.

        Args:
            story_id: UUID of the story/book
            format: Book format (digital, softcover, hardcover)
            shipping_tier: Shipping option (standard, express, digital)
            customer_email: Customer's email address
            shopify_order_id: Shopify order ID (if from Shopify)
            shopify_order_number: Shopify order number (human-readable)
            shipping_address: Full shipping address dict
            gift_options: Gift settings (is_gift, message, wrap, recipient_email)
            pricing: Pricing details (base_price, shipping_cost, gift_wrap_cost, total)
            customer_name: Customer's full name
            customer_phone: Customer's phone number
            book_size: Book dimensions (8x8, 8.5x8.5, 10x8)
            quantity: Number of copies

        Returns:
            Complete order record with ID
        """
        order_id = str(uuid.uuid4())

        # Build order data
        order_data = {
            "id": order_id,
            "story_id": story_id,
            "shopify_order_id": shopify_order_id,
            "shopify_order_number": shopify_order_number,
            "format": format,
            "book_size": book_size,
            "quantity": quantity,
            "shipping_tier": shipping_tier,
            "shipping_address": shipping_address,
            "customer_email": customer_email,
            "customer_name": customer_name,
            "customer_phone": customer_phone,
            "status": OrderStatus.PENDING_PAYMENT.value,
            "status_history": [{
                "status": OrderStatus.PENDING_PAYMENT.value,
                "timestamp": datetime.utcnow().isoformat(),
                "note": "Order created"
            }],
            # Gift options
            "is_gift": gift_options.get("is_gift", False) if gift_options else False,
            "gift_message": gift_options.get("message") if gift_options else None,
            "gift_wrap": gift_options.get("wrap", False) if gift_options else False,
            "recipient_email": gift_options.get("recipient_email") if gift_options else None,
            # Pricing (stored at time of order for audit trail)
            "base_price": pricing.get("base_price", 0) if pricing else 0,
            "shipping_cost": pricing.get("shipping_cost", 0) if pricing else 0,
            "gift_wrap_cost": pricing.get("gift_wrap_cost", 0) if pricing else 0,
            "discount_amount": pricing.get("discount_amount", 0) if pricing else 0,
            "tax_amount": pricing.get("tax_amount", 0) if pricing else 0,
            "total_amount": pricing.get("total", 0) if pricing else 0,
            "currency": pricing.get("currency", "USD") if pricing else "USD",
            "created_at": datetime.utcnow().isoformat()
        }

        # Insert into database
        result = await self.db.create_order(order_data)

        logger.info(f"Order created: {order_id}", extra={
            "order_id": order_id,
            "story_id": story_id,
            "format": format,
            "shopify_order_id": shopify_order_id
        })

        return result

    async def update_order_status(
        self,
        order_id: str,
        status: OrderStatus,
        note: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update order status with history tracking.

        Args:
            order_id: Order UUID
            status: New status
            note: Optional note about the status change

        Returns:
            Updated order record
        """
        status_value = status.value if isinstance(status, OrderStatus) else status

        # Get current order to update history
        current_order = await self.db.get_order(order_id)
        if not current_order:
            raise ValueError(f"Order not found: {order_id}")

        # Build status history entry
        history_entry = {
            "status": status_value,
            "previous_status": current_order.get("status"),
            "timestamp": datetime.utcnow().isoformat(),
            "note": note
        }

        # Append to history
        status_history = current_order.get("status_history", [])
        status_history.append(history_entry)

        # Update order
        updates = {
            "status": status_value,
            "status_history": status_history
        }

        # Set completion timestamp for terminal states
        if status_value in [
            OrderStatus.DELIVERED.value,
            OrderStatus.FAILED.value
        ]:
            updates["completed_at"] = datetime.utcnow().isoformat()

        result = await self.db.update_order(order_id, updates)

        logger.info(f"Order status updated: {order_id} -> {status_value}", extra={
            "order_id": order_id,
            "status": status_value,
            "note": note
        })

        return result

    async def process_payment_confirmed(
        self,
        order_id: str,
        shopify_order_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Handle payment confirmation - triggers print production.

        This is called when Shopify webhook confirms payment.

        Args:
            order_id: Order UUID
            shopify_order_data: Full Shopify order payload

        Returns:
            Order with updated status
        """
        # Update status
        await self.update_order_status(
            order_id,
            OrderStatus.PAYMENT_CONFIRMED,
            note="Payment received from Shopify"
        )

        # Update order with any additional Shopify data
        if shopify_order_data:
            updates = {}

            # Extract tracking info if available
            if "fulfillments" in shopify_order_data:
                for fulfillment in shopify_order_data.get("fulfillments", []):
                    if fulfillment.get("tracking_number"):
                        updates["tracking_number"] = fulfillment["tracking_number"]
                        updates["tracking_url"] = fulfillment.get("tracking_url")
                        break

            # Extract customer info if not already set
            customer = shopify_order_data.get("customer", {})
            if customer:
                if not updates.get("customer_name"):
                    updates["customer_name"] = f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip()
                if not updates.get("customer_phone"):
                    updates["customer_phone"] = customer.get("phone")

            if updates:
                await self.db.update_order(order_id, updates)

        logger.info(f"Payment confirmed for order: {order_id}")

        return await self.db.get_order(order_id)

    async def store_order_pdf(
        self,
        order_id: str,
        book_id: str,
        pdf_path: str,
        metadata: Optional[Dict] = None
    ) -> Dict[str, str]:
        """
        Upload generated PDF to storage and update order.

        Args:
            order_id: Order UUID
            book_id: Book/story UUID
            pdf_path: Local path to generated PDF
            metadata: PDF generation metadata

        Returns:
            Storage result with path and URL
        """
        if not self.storage.is_available:
            logger.warning("Storage not available - PDF not uploaded")
            return {"error": "Storage not available"}

        # Upload PDF
        pdf_result = await self.storage.upload_order_pdf(
            order_id=order_id,
            book_id=book_id,
            pdf_path=pdf_path,
            metadata=metadata
        )

        # Update order with PDF info
        await self.db.update_order(order_id, {
            "pdf_storage_path": pdf_result["storage_path"],
            "pdf_url": pdf_result["signed_url"],
            "pdf_generated_at": pdf_result["uploaded_at"]
        })

        # Update status
        await self.update_order_status(
            order_id,
            OrderStatus.CREATING_PDF,
            note="PDF generated and uploaded to storage"
        )

        logger.info(f"PDF stored for order {order_id}", extra={
            "storage_path": pdf_result["storage_path"]
        })

        return pdf_result

    async def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """
        Get order with fresh PDF URL if available.

        Args:
            order_id: Order UUID

        Returns:
            Order data with refreshed PDF URL, or None
        """
        order = await self.db.get_order(order_id)

        if order and order.get("pdf_storage_path"):
            # Get fresh signed URL
            fresh_url = await self.storage.get_order_pdf_url(
                order_id=order_id,
                book_id=order["story_id"],
                expiry_hours=24
            )
            if fresh_url:
                order["pdf_url"] = fresh_url

        return order

    async def get_order_by_shopify_id(
        self,
        shopify_order_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get order by Shopify order ID.

        Args:
            shopify_order_id: Shopify's order ID

        Returns:
            Order data or None
        """
        return await self.db.get_order_by_shopify_id(shopify_order_id)

    async def get_orders_by_customer(
        self,
        customer_email: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get all orders for a customer.

        Args:
            customer_email: Customer's email address
            limit: Maximum number of orders to return

        Returns:
            List of orders, newest first
        """
        return await self.db.get_orders_by_customer(customer_email, limit)

    async def get_orders_by_status(
        self,
        status: OrderStatus,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get orders by status.

        Args:
            status: Order status to filter by
            limit: Maximum number of orders to return

        Returns:
            List of matching orders
        """
        status_value = status.value if isinstance(status, OrderStatus) else status
        return await self.db.get_orders_by_status(status_value, limit)

    async def get_pdf_download_url(
        self,
        order_id: str,
        expiry_hours: int = 24
    ) -> Optional[str]:
        """
        Get a fresh download URL for the order's PDF.

        Args:
            order_id: Order UUID
            expiry_hours: How long the URL should be valid

        Returns:
            Signed URL or None if PDF not available
        """
        order = await self.db.get_order(order_id)

        if not order or not order.get("pdf_storage_path"):
            return None

        return await self.storage.get_order_pdf_url(
            order_id=order_id,
            book_id=order["story_id"],
            expiry_hours=expiry_hours
        )

    async def update_shipping_info(
        self,
        order_id: str,
        tracking_number: str,
        tracking_url: Optional[str] = None,
        shipped_at: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update order with shipping/tracking information.

        Args:
            order_id: Order UUID
            tracking_number: Carrier tracking number
            tracking_url: URL to track package
            shipped_at: When the order was shipped

        Returns:
            Updated order record
        """
        updates = {
            "tracking_number": tracking_number,
            "tracking_url": tracking_url,
            "shipped_at": shipped_at or datetime.utcnow().isoformat()
        }

        await self.db.update_order(order_id, updates)

        # Update status
        await self.update_order_status(
            order_id,
            OrderStatus.SHIPPED,
            note=f"Shipped with tracking: {tracking_number}"
        )

        return await self.db.get_order(order_id)

    async def mark_delivered(self, order_id: str) -> Dict[str, Any]:
        """
        Mark order as delivered.

        Args:
            order_id: Order UUID

        Returns:
            Updated order record
        """
        await self.db.update_order(order_id, {
            "delivered_at": datetime.utcnow().isoformat()
        })

        await self.update_order_status(
            order_id,
            OrderStatus.DELIVERED,
            note="Order delivered"
        )

        return await self.db.get_order(order_id)

    async def cancel_order(
        self,
        order_id: str,
        reason: Optional[str] = None,
        delete_assets: bool = True
    ) -> Dict[str, Any]:
        """
        Cancel an order and optionally clean up assets.

        Args:
            order_id: Order UUID
            reason: Cancellation reason
            delete_assets: Whether to delete stored PDFs/images

        Returns:
            Updated order record
        """
        # Delete stored assets if requested
        if delete_assets and self.storage.is_available:
            await self.storage.delete_order_assets(order_id)
            logger.info(f"Deleted assets for cancelled order: {order_id}")

        # Update status
        await self.update_order_status(
            order_id,
            OrderStatus.CANCELLED,
            note=f"Order cancelled: {reason}" if reason else "Order cancelled"
        )

        return await self.db.get_order(order_id)

    async def get_order_with_book(self, order_id: str) -> Optional[Dict[str, Any]]:
        """
        Get order with associated book data.

        Args:
            order_id: Order UUID

        Returns:
            Order data with embedded book details
        """
        return await self.db.get_order_with_book(order_id)


# Singleton instance
_order_service: Optional[OrderService] = None


def get_order_service() -> OrderService:
    """Get the order service singleton."""
    global _order_service
    if _order_service is None:
        _order_service = OrderService()
    return _order_service
