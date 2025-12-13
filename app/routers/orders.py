# app/routers/orders.py
"""
GoldenTales Orders Router
=========================
API endpoints for order management and pricing.
"""

import uuid
from datetime import datetime, timedelta
from typing import Dict, List

from fastapi import APIRouter, HTTPException, BackgroundTasks

from app.config import settings
from app.models.requests import OrderRequest
from app.models.enums import BookFormat, ShippingTier
from app.routers.books import get_book_storage
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["Orders"])


def get_shipping_options() -> List[Dict]:
    """Get available shipping options with Christmas deadlines."""
    today = datetime.now()
    christmas = settings.christmas_date
    
    options = []
    
    # Digital - always available
    options.append({
        "tier": "digital",
        "name": "Digital PDF",
        "description": "Instant download",
        "available": True,
        "estimated_arrival": "Instant"
    })
    
    # Standard shipping
    standard_deadline = settings.standard_deadline
    standard_available = today < standard_deadline
    options.append({
        "tier": "standard",
        "name": "Standard Shipping",
        "description": f"Order by {standard_deadline.strftime('%b %d')} for Christmas",
        "available": standard_available,
        "deadline": standard_deadline.isoformat(),
        "estimated_arrival": (today + timedelta(days=settings.standard_shipping_days)).strftime('%b %d'),
        "days_until_deadline": max(0, (standard_deadline - today).days)
    })
    
    # Express shipping
    express_deadline = settings.express_deadline
    express_available = today < express_deadline
    options.append({
        "tier": "express",
        "name": "Express Shipping",
        "description": "Fast delivery",
        "available": express_available,
        "deadline": express_deadline.isoformat(),
        "estimated_arrival": (today + timedelta(days=settings.express_shipping_days)).strftime('%b %d'),
        "days_until_deadline": max(0, (express_deadline - today).days)
    })
    
    return options


def get_countdown() -> Dict:
    """Get countdown to Christmas shipping deadline."""
    today = datetime.now()
    deadline = settings.standard_deadline
    diff = deadline - today
    
    if diff.total_seconds() < 0:
        return {
            "expired": True,
            "days": 0,
            "hours": 0,
            "minutes": 0,
            "urgency": "expired"
        }
    
    days = diff.days
    hours = diff.seconds // 3600
    minutes = (diff.seconds % 3600) // 60
    
    urgency = "normal"
    if days <= 2:
        urgency = "critical"
    elif days <= 5:
        urgency = "urgent"
    elif days <= 10:
        urgency = "warning"
    
    return {
        "expired": False,
        "days": days,
        "hours": hours,
        "minutes": minutes,
        "urgency": urgency,
        "deadline": deadline.strftime('%B %d')
    }


@router.get("/shipping-options")
async def shipping_options():
    """Get available shipping options."""
    return {
        "options": get_shipping_options(),
        "countdown": get_countdown()
    }


@router.get("/books/{book_id}/price")
async def get_book_price(
    book_id: str,
    format: BookFormat,
    shipping: ShippingTier,
    gift_wrap: bool = False
) -> Dict:
    """Calculate total price for a book order."""
    book_storage = get_book_storage()
    
    if book_id not in book_storage:
        raise HTTPException(status_code=404, detail="Book not found")
    
    # Get prices from settings
    prices = {
        BookFormat.DIGITAL: settings.price_digital,
        BookFormat.SOFTCOVER: settings.price_softcover,
        BookFormat.HARDCOVER: settings.price_hardcover
    }
    
    shipping_costs = {
        ShippingTier.DIGITAL: 0,
        ShippingTier.STANDARD: settings.shipping_standard,
        ShippingTier.EXPRESS: settings.shipping_express
    }
    
    base_price = prices.get(format, settings.price_digital)
    shipping_cost = shipping_costs.get(shipping, 0)
    wrap_cost = settings.gift_wrap_cost if gift_wrap and format != BookFormat.DIGITAL else 0
    
    return {
        "book_id": book_id,
        "format": format.value,
        "base_price": base_price,
        "shipping_cost": shipping_cost,
        "gift_wrap_cost": wrap_cost,
        "total": round(base_price + shipping_cost + wrap_cost, 2),
        "currency": "USD"
    }


@router.post("/orders/create")
async def create_order(
    request: OrderRequest,
    background_tasks: BackgroundTasks
) -> Dict:
    """Create an order for a book."""
    book_storage = get_book_storage()
    
    if request.book_id not in book_storage:
        raise HTTPException(status_code=404, detail="Book not found")
    
    book = book_storage[request.book_id]
    order_id = str(uuid.uuid4())[:8]
    
    # Calculate price
    price = await get_book_price(
        request.book_id,
        request.format,
        request.shipping_tier,
        request.gift_wrap
    )
    
    # Determine delivery estimate
    shipping_options = get_shipping_options()
    shipping_option = next(
        (o for o in shipping_options if o['tier'] == request.shipping_tier.value),
        shipping_options[0]
    )
    
    logger.info(f"Order {order_id} created for book {request.book_id}")
    
    return {
        "order_id": order_id,
        "book_id": request.book_id,
        "book_title": book['title'],
        "total": price['total'],
        "status": "pending_payment",
        "estimated_delivery": shipping_option['estimated_arrival'],
        "checkout_url": f"/checkout/{order_id}"
    }


@router.get("/orders/{order_id}/status")
async def get_order_status(order_id: str) -> Dict:
    """Get order status."""
    # In production: Fetch from database
    return {
        "order_id": order_id,
        "status": "processing",
        "steps": [
            {"name": "Order Received", "status": "completed"},
            {"name": "Payment Confirmed", "status": "completed"},
            {"name": "Generating Print Files", "status": "in_progress"},
            {"name": "Sent to Printer", "status": "pending"},
            {"name": "Shipped", "status": "pending"},
            {"name": "Delivered", "status": "pending"}
        ]
    }
