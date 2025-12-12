# app/routers/shopify.py
"""
DreamWeaver Shopify Router
==========================
Handles Shopify webhooks for order processing and fulfillment.
"""

import json
from typing import Dict, Optional

from fastapi import APIRouter, Request, HTTPException

from app.config import settings
from app.utils.security import verify_webhook_signature
from app.utils.logging import get_logger
from app.routers.books import get_book_storage

logger = get_logger(__name__)

router = APIRouter(prefix="/api/shopify", tags=["Shopify"])


def extract_book_id_from_order(order: dict) -> Optional[str]:
    """
    Extract book_id from order notes or line item properties.
    
    Shopify orders can contain book_id in:
    1. Order notes: "book_id:abc123"
    2. Line item properties: {"name": "book_id", "value": "abc123"}
    """
    # Check order notes
    if order.get('note'):
        for line in order['note'].split('\n'):
            if line.startswith('book_id:'):
                return line.split(':')[1].strip()
    
    # Check line item properties
    for item in order.get('line_items', []):
        for prop in item.get('properties', []):
            if prop.get('name') == 'book_id':
                return prop.get('value')
    
    # Check note_attributes
    for attr in order.get('note_attributes', []):
        if attr.get('name') == 'book_id':
            return attr.get('value')
    
    return None


def determine_format_from_item(item: dict) -> str:
    """Determine book format from line item."""
    title = item.get('title', '').lower()
    variant = item.get('variant_title', '').lower()
    sku = item.get('sku', '').lower()
    
    combined = f"{title} {variant} {sku}"
    
    if 'hardcover' in combined:
        return 'hardcover'
    elif 'softcover' in combined or 'paperback' in combined:
        return 'softcover'
    elif 'digital' in combined or 'pdf' in combined:
        return 'digital'
    
    return 'hardcover'  # Default


@router.post("/webhooks/orders/create")
async def handle_order_created(request: Request):
    """
    Handle Shopify order creation webhook.
    
    Called by Shopify when an order is placed.
    Triggers print production for physical books or
    digital delivery for PDF orders.
    """
    body = await request.body()
    signature = request.headers.get("X-Shopify-Hmac-SHA256")
    
    # Verify webhook signature
    if not verify_webhook_signature(body, signature):
        logger.warning("Invalid webhook signature received")
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    
    try:
        order = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    
    order_id = order.get('id')
    logger.info(f"Received Shopify order webhook: {order_id}")
    
    # Extract book_id from order
    book_id = extract_book_id_from_order(order)
    
    if not book_id:
        logger.info(f"Order {order_id} has no book_id, skipping")
        return {"status": "skipped", "reason": "no book_id found"}
    
    # Get book data
    book_storage = get_book_storage()
    book = book_storage.get(book_id)
    
    if not book:
        logger.error(f"Book {book_id} not found for order {order_id}")
        raise HTTPException(status_code=404, detail=f"Book {book_id} not found")
    
    # Determine format from line items
    format_type = 'hardcover'
    for item in order.get('line_items', []):
        format_type = determine_format_from_item(item)
        break
    
    logger.info(f"Processing order {order_id} for book {book_id}, format: {format_type}")
    
    # TODO: Start print production or digital delivery
    # This would trigger the PrintProductionPipeline for physical books
    # or generate and email a PDF for digital orders
    
    return {
        "status": "processing",
        "order_id": str(order_id),
        "book_id": book_id,
        "format": format_type
    }


@router.post("/webhooks/orders/fulfilled")
async def handle_order_fulfilled(request: Request):
    """Handle Shopify order fulfillment webhook."""
    body = await request.body()
    signature = request.headers.get("X-Shopify-Hmac-SHA256")
    
    if not verify_webhook_signature(body, signature):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    
    order = json.loads(body)
    logger.info(f"Order {order.get('id')} fulfilled")
    
    return {"status": "acknowledged"}


@router.post("/webhooks/orders/cancelled")
async def handle_order_cancelled(request: Request):
    """Handle Shopify order cancellation webhook."""
    body = await request.body()
    signature = request.headers.get("X-Shopify-Hmac-SHA256")
    
    if not verify_webhook_signature(body, signature):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    
    order = json.loads(body)
    logger.info(f"Order {order.get('id')} cancelled")
    
    # TODO: Cancel any pending print jobs
    
    return {"status": "acknowledged"}


@router.get("/health")
async def shopify_health():
    """Shopify integration health check."""
    return {
        "status": "healthy",
        "webhook_secret_configured": bool(settings.shopify_webhook_secret),
        "store_url_configured": bool(settings.shopify_store_url)
    }
