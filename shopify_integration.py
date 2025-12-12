# shopify_integration.py
"""
Simplified backend that works with Shopify.
Only handles: Book generation + Fulfillment trigger
"""

from fastapi import APIRouter, Request, HTTPException
import hmac
import hashlib
import json

router = APIRouter(prefix="/api/shopify", tags=["Shopify"])

SHOPIFY_WEBHOOK_SECRET = os.getenv("SHOPIFY_WEBHOOK_SECRET")

@router.post("/order-created")
async def handle_order_created(request: Request):
    """
    Called by Shopify when an order is placed.
    Triggers print production.
    """
    
    # Verify webhook signature
    body = await request.body()
    signature = request.headers.get("X-Shopify-Hmac-SHA256")
    
    if not verify_shopify_webhook(body, signature):
        raise HTTPException(401, "Invalid webhook signature")
    
    order = json.loads(body)
    
    # Extract book_id from order metadata/notes
    book_id = extract_book_id_from_order(order)
    
    if not book_id:
        print(f"Order {order['id']} has no book_id, skipping")
        return {"status": "skipped"}
    
    # Get book data
    book = book_storage.get(book_id)
    if not book:
        raise HTTPException(404, f"Book {book_id} not found")
    
    # Determine format from line items
    format_type = determine_format(order['line_items'])
    
    # Start print production
    if format_type != "digital":
        # Generate high-res images + PDF
        await start_print_production(
            book_id=book_id,
            book_data=book,
            order_id=str(order['id']),
            shipping_address=order.get('shipping_address'),
            format_type=format_type
        )
    else:
        # Digital: Generate PDF and email to customer
        await generate_and_email_pdf(
            book_id=book_id,
            book_data=book,
            customer_email=order['email']
        )
    
    return {"status": "processing", "book_id": book_id}


def verify_shopify_webhook(body: bytes, signature: str) -> bool:
    """Verify Shopify webhook HMAC signature."""
    if not SHOPIFY_WEBHOOK_SECRET:
        return True  # Skip in development
    
    computed = hmac.new(
        SHOPIFY_WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha256
    ).digest()
    
    import base64
    computed_b64 = base64.b64encode(computed).decode()
    
    return hmac.compare_digest(computed_b64, signature)


def extract_book_id_from_order(order: dict) -> str:
    """Extract book_id from order notes or line item properties."""
    
    # Check order notes
    if order.get('note'):
        # Format: "book_id:abc123"
        for line in order['note'].split('\n'):
            if line.startswith('book_id:'):
                return line.split(':')[1].strip()
    
    # Check line item properties
    for item in order.get('line_items', []):
        for prop in item.get('properties', []):
            if prop.get('name') == 'book_id':
                return prop.get('value')
    
    return None


def determine_format(line_items: list) -> str:
    """Determine book format from line items."""
    for item in line_items:
        title = item.get('title', '').lower()
        if 'hardcover' in title:
            return 'hardcover'
        elif 'softcover' in title:
            return 'softcover'
        elif 'digital' in title:
            return 'digital'
    return 'hardcover'  # Default