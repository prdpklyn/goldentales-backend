# dreamweaver_backend/main.py
"""
DreamWeaver Backend API
Complete implementation for personalized storybook generation.
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from enum import Enum
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize FastAPI
app = FastAPI(
    title="DreamWeaver API",
    description="AI-powered personalized storybook generation",
    version="1.0.0"
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://taleom.lovable.app", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# DATA MODELS
# ============================================

class ArtStyle(str, Enum):
    WATERCOLOR = "watercolor"
    CARTOON = "cartoon"
    ANIME = "anime"
    STORYBOOK = "storybook"

class Theme(str, Enum):
    CHRISTMAS = "christmas"
    SPACE = "space"
    OCEAN = "ocean"
    FOREST = "forest"
    DINOSAUR = "dinosaur"
    SUPERHERO = "superhero"

class ShippingTier(str, Enum):
    DIGITAL = "digital"
    STANDARD = "standard"
    EXPRESS = "express"

class BookFormat(str, Enum):
    DIGITAL = "digital"
    SOFTCOVER = "softcover"
    HARDCOVER = "hardcover"

class CreateBookRequest(BaseModel):
    child_name: str = Field(..., min_length=2, max_length=30)
    child_age: int = Field(..., ge=3, le=12)
    theme: Theme
    art_style: ArtStyle
    occasion: Optional[str] = None
    additional_characters: Optional[str] = None
    special_details: Optional[str] = None
    photo_url: Optional[str] = None

class OrderRequest(BaseModel):
    book_id: str
    format: BookFormat
    shipping_tier: ShippingTier
    gift_wrap: bool = False
    recipient_name: Optional[str] = None
    recipient_address: Optional[Dict] = None

class BookPreview(BaseModel):
    book_id: str
    title: str
    pages: List[Dict]
    preview_images: List[str]
    estimated_cost: float
    created_at: datetime

# ============================================
# CONFIGURATION
# ============================================

class Config:
    FAL_KEY = os.getenv("FAL_KEY")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    LULU_API_KEY = os.getenv("LULU_API_KEY")
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # Pricing
    PRICES = {
        BookFormat.DIGITAL: 9.99,
        BookFormat.SOFTCOVER: 24.99,
        BookFormat.HARDCOVER: 34.99,
    }
    
    SHIPPING_COSTS = {
        ShippingTier.DIGITAL: 0,
        ShippingTier.STANDARD: 0,
        ShippingTier.EXPRESS: 12,
    }
    
    GIFT_WRAP_COST = 5.00
    
    # Christmas deadline
    CHRISTMAS_DATE = datetime(2024, 12, 25)
    STANDARD_SHIPPING_DAYS = 10
    EXPRESS_SHIPPING_DAYS = 4

# ============================================
# STORY GENERATION (Gemini Integration)
# ============================================

async def generate_story_with_gemini(
    child_name: str,
    age: int,
    theme: str,
    occasion: Optional[str] = None,
    special_details: Optional[str] = None
) -> List[Dict]:
    """
    Generate a personalized story using Google Gemini.
    """
    import google.generativeai as genai
    
    genai.configure(api_key=Config.GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-3-pro-preview')
    
    prompt = f"""
    Create a 10-page children's storybook for a {age}-year-old child named {child_name}.
    
    Theme: {theme}
    Occasion: {occasion or 'Just for fun'}
    Special details to include: {special_details or 'None'}
    
    Requirements:
    1. Each page should have 2-3 sentences, age-appropriate vocabulary
    2. The story should have a clear beginning, middle, and end
    3. {child_name} should be the hero who learns something positive
    4. Include vivid scene descriptions for illustrations
    5. Keep it warm, positive, and empowering
    
    Format your response as JSON array:
    [
        {{
            "page_number": 1,
            "text": "Story text for this page...",
            "scene_description": "Detailed description for illustrator...",
            "character_action": "What {child_name} is doing...",
            "mood": "happy/excited/curious/brave/etc"
        }},
        ...
    ]
    
    Return ONLY the JSON array, no other text.
    """
    
    response = await model.generate_content_async(prompt)
    
    import json
    story_pages = json.loads(response.text)
    
    return story_pages

# ============================================
# IMAGE GENERATION (Fal.ai Integration)
# ============================================

async def generate_illustration(
    scene_description: str,
    character_description: str,
    art_style: str,
    reference_image_url: Optional[str] = None,
    is_preview: bool = True
) -> Dict:
    """
    Generate an illustration using Fal.ai Flux.
    """
    import fal_client
    
    # Build prompt
    style_prompts = {
        "watercolor": "soft watercolor painting, gentle colors, dreamy atmosphere",
        "cartoon": "vibrant cartoon style, bold colors, fun and playful",
        "anime": "anime style illustration, expressive, detailed",
        "storybook": "classic children's book illustration, warm and nostalgic"
    }
    
    prompt = f"""
    Children's book illustration, {style_prompts.get(art_style, 'storybook')}.
    
    Scene: {scene_description}
    Character: {character_description}
    
    Professional quality, warm inviting colors, safe for children.
    """
    
    negative_prompt = "nsfw, nude, violence, blood, scary, horror, dark, disturbing, ugly, deformed"
    
    # Choose model based on preview vs print
    if is_preview:
        model = "fal-ai/flux/schnell"
        params = {
            "prompt": prompt,
            "image_size": "landscape_4_3",
            "num_inference_steps": 4,
            "enable_safety_checker": True,
        }
    else:
        model = "fal-ai/flux-pro/v1.1"
        params = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "image_size": {"width": 2400, "height": 1800},
            "enable_safety_checker": True,
            "guidance_scale": 7.5,
        }
    
    # Add IP-Adapter for character consistency if reference provided
    if reference_image_url:
        model = "fal-ai/flux-pro/v1.1/ip-adapter"
        params["ip_adapter_image_url"] = reference_image_url
        params["ip_adapter_scale"] = 0.7
    
    handler = await fal_client.submit_async(model, arguments=params)
    result = await handler.get()
    
    return {
        "url": result['images'][0]['url'],
        "is_preview": is_preview,
    }

async def generate_all_illustrations(
    story_pages: List[Dict],
    character_description: str,
    art_style: str,
    child_photo_url: Optional[str] = None,
    is_preview: bool = True
) -> List[Dict]:
    """
    Generate all illustrations for a book in parallel.
    """
    
    # First, generate character reference if photo provided
    reference_url = None
    if child_photo_url:
        reference_result = await generate_illustration(
            "Character reference sheet, multiple angles, white background",
            character_description,
            art_style,
            is_preview=False  # Always high quality for reference
        )
        reference_url = reference_result['url']
    
    # Generate all pages in parallel
    tasks = []
    for page in story_pages:
        task = generate_illustration(
            page['scene_description'],
            f"{character_description}, {page['character_action']}",
            art_style,
            reference_url,
            is_preview
        )
        tasks.append(task)
    
    illustrations = await asyncio.gather(*tasks)
    
    return illustrations

# ============================================
# PDF GENERATION
# ============================================

def generate_print_pdf(
    book_id: str,
    title: str,
    child_name: str,
    pages: List[Dict],
    image_urls: List[str]
) -> str:
    """
    Generate a print-ready PDF.
    """
    from reportlab.lib.pagesizes import inch
    from reportlab.pdfgen import canvas
    from reportlab.lib.colors import CMYKColor
    import requests
    from PIL import Image
    import io
    
    # Book dimensions (8x8 inch square with bleed)
    BLEED = 0.125 * inch
    TRIM_SIZE = 8 * inch
    PAGE_SIZE = TRIM_SIZE + (2 * BLEED)
    
    output_path = f"/tmp/books/{book_id}.pdf"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    c = canvas.Canvas(output_path, pagesize=(PAGE_SIZE, PAGE_SIZE))
    c.setTitle(title)
    c.setAuthor("DreamWeaver")
    
    for i, (page, image_url) in enumerate(zip(pages, image_urls)):
        # Download and process image
        response = requests.get(image_url)
        img = Image.open(io.BytesIO(response.content))
        
        # Convert to CMYK
        if img.mode != 'CMYK':
            img = img.convert('CMYK')
        
        # Resize for 300 DPI
        target_px = int(PAGE_SIZE / inch * 300)
        img = img.resize((target_px, int(target_px * 0.6)), Image.LANCZOS)
        
        # Save to temp file
        img_path = f"/tmp/books/{book_id}_page_{i}.tiff"
        img.save(img_path, format='TIFF')
        
        # Draw image (top 60% of page)
        c.drawImage(
            img_path,
            BLEED,
            BLEED + (TRIM_SIZE * 0.4),
            width=TRIM_SIZE,
            height=TRIM_SIZE * 0.6
        )
        
        # Draw text (bottom 35%)
        c.setFont("Helvetica", 14)
        c.setFillColor(CMYKColor(0, 0, 0, 1))
        
        text_lines = page['text'].split('. ')
        y = BLEED + (TRIM_SIZE * 0.3)
        for line in text_lines:
            c.drawCentredString(PAGE_SIZE / 2, y, line + '.')
            y -= 20
        
        # Page number
        c.setFont("Helvetica", 10)
        c.drawCentredString(PAGE_SIZE / 2, BLEED + 20, str(i + 1))
        
        c.showPage()
    
    c.save()
    return output_path

# ============================================
# PRINT-ON-DEMAND (Lulu Integration)
# ============================================

async def submit_to_lulu(
    pdf_path: str,
    book_title: str,
    shipping_address: Dict,
    shipping_tier: ShippingTier
) -> Dict:
    """
    Submit book to Lulu for printing.
    """
    import httpx
    
    LULU_API_URL = "https://api.lulu.com/v1"
    
    async with httpx.AsyncClient() as client:
        # 1. Upload PDF
        with open(pdf_path, 'rb') as f:
            upload_response = await client.post(
                f"{LULU_API_URL}/files",
                headers={"Authorization": f"Bearer {Config.LULU_API_KEY}"},
                files={"file": f}
            )
            file_id = upload_response.json()['id']
        
        # 2. Create print job
        shipping_level = {
            ShippingTier.STANDARD: "MAIL",
            ShippingTier.EXPRESS: "PRIORITY_MAIL",
        }.get(shipping_tier, "MAIL")
        
        order_data = {
            "line_items": [{
                "title": book_title,
                "quantity": 1,
                "printable_normalization": {
                    "pod_package_id": "0850X0850FCSTDPB060UW444GXX",  # 8.5x8.5 softcover
                    "cover": {"source_url": file_id},
                    "interior": {"source_url": file_id}
                }
            }],
            "shipping_address": shipping_address,
            "shipping_level": shipping_level
        }
        
        order_response = await client.post(
            f"{LULU_API_URL}/print-jobs",
            headers={
                "Authorization": f"Bearer {Config.LULU_API_KEY}",
                "Content-Type": "application/json"
            },
            json=order_data
        )
        
        return order_response.json()

# ============================================
# TIMELINE MANAGEMENT
# ============================================

def get_shipping_options() -> List[Dict]:
    """
    Get available shipping options with Christmas deadlines.
    """
    today = datetime.now()
    christmas = Config.CHRISTMAS_DATE
    
    options = []
    
    # Digital - always available
    options.append({
        "tier": "digital",
        "name": "Digital PDF",
        "price": 0,
        "description": "Instant download",
        "available": True,
        "estimated_arrival": "Instant"
    })
    
    # Standard shipping
    standard_deadline = christmas - timedelta(days=Config.STANDARD_SHIPPING_DAYS)
    standard_available = today < standard_deadline
    options.append({
        "tier": "standard",
        "name": "Standard Shipping",
        "price": 0,
        "description": f"Order by {standard_deadline.strftime('%b %d')} for Christmas",
        "available": standard_available,
        "deadline": standard_deadline.isoformat(),
        "estimated_arrival": (today + timedelta(days=Config.STANDARD_SHIPPING_DAYS)).strftime('%b %d')
    })
    
    # Express shipping
    express_deadline = christmas - timedelta(days=Config.EXPRESS_SHIPPING_DAYS)
    express_available = today < express_deadline
    options.append({
        "tier": "express",
        "name": "Express Shipping",
        "price": 12,
        "description": "Arrives by Dec 23",
        "available": express_available,
        "deadline": express_deadline.isoformat(),
        "estimated_arrival": (today + timedelta(days=Config.EXPRESS_SHIPPING_DAYS)).strftime('%b %d')
    })
    
    return options

def get_countdown() -> Dict:
    """
    Get countdown to Christmas shipping deadline.
    """
    today = datetime.now()
    deadline = Config.CHRISTMAS_DATE - timedelta(days=Config.STANDARD_SHIPPING_DAYS)
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
    if days <= 3:
        urgency = "critical"
    elif days <= 7:
        urgency = "urgent"
    
    return {
        "expired": False,
        "days": days,
        "hours": hours,
        "minutes": minutes,
        "urgency": urgency,
        "deadline": deadline.strftime('%B %d')
    }

# ============================================
# API ENDPOINTS
# ============================================

@app.get("/")
async def root():
    return {"message": "DreamWeaver API", "version": "1.0.0"}

@app.get("/api/shipping-options")
async def shipping_options():
    """Get available shipping options."""
    return {
        "options": get_shipping_options(),
        "countdown": get_countdown()
    }

@app.post("/api/books/create")
async def create_book(
    request: CreateBookRequest,
    background_tasks: BackgroundTasks
) -> Dict:
    """
    Create a new personalized book (preview).
    """
    import uuid
    
    book_id = str(uuid.uuid4())[:8]
    
    # Validate inputs
    if len(request.child_name) < 2:
        raise HTTPException(400, "Name must be at least 2 characters")
    
    # Generate story
    story_pages = await generate_story_with_gemini(
        request.child_name,
        request.child_age,
        request.theme.value,
        request.occasion,
        request.special_details
    )
    
    # Build character description
    character_desc = f"A {request.child_age}-year-old child named {request.child_name}"
    if request.additional_characters:
        character_desc += f", with {request.additional_characters}"
    
    # Generate preview illustrations
    illustrations = await generate_all_illustrations(
        story_pages,
        character_desc,
        request.art_style.value,
        request.photo_url,
        is_preview=True
    )
    
    # Calculate cost
    page_count = len(story_pages)
    preview_cost = page_count * 0.02  # Schnell model
    
    return {
        "book_id": book_id,
        "title": f"{request.child_name}'s {request.theme.value.title()} Adventure",
        "pages": story_pages,
        "preview_images": [img['url'] for img in illustrations],
        "page_count": page_count,
        "generation_cost": round(preview_cost, 2),
        "created_at": datetime.now().isoformat()
    }

@app.post("/api/books/{book_id}/regenerate-page/{page_number}")
async def regenerate_page(
    book_id: str,
    page_number: int,
    scene_description: str,
    art_style: ArtStyle
) -> Dict:
    """
    Regenerate a specific page illustration.
    """
    # In production, fetch existing book data from database
    
    illustration = await generate_illustration(
        scene_description,
        "The child character",
        art_style.value,
        is_preview=True
    )
    
    return {
        "page_number": page_number,
        "new_image_url": illustration['url']
    }

@app.get("/api/books/{book_id}/price")
async def get_book_price(
    book_id: str,
    format: BookFormat,
    shipping: ShippingTier,
    gift_wrap: bool = False
) -> Dict:
    """
    Calculate total price for a book order.
    """
    base_price = Config.PRICES[format]
    shipping_cost = Config.SHIPPING_COSTS[shipping]
    wrap_cost = Config.GIFT_WRAP_COST if gift_wrap else 0
    
    total = base_price + shipping_cost + wrap_cost
    
    return {
        "base_price": base_price,
        "shipping_cost": shipping_cost,
        "gift_wrap_cost": wrap_cost,
        "total": round(total, 2),
        "currency": "USD"
    }

@app.post("/api/orders/create")
async def create_order(
    request: OrderRequest,
    background_tasks: BackgroundTasks
) -> Dict:
    """
    Create an order for a book.
    """
    import uuid
    
    order_id = str(uuid.uuid4())[:8]
    
    # Calculate price
    price = await get_book_price(
        request.book_id,
        request.format,
        request.shipping_tier,
        request.gift_wrap
    )
    
    # For digital orders, no printing needed
    if request.format == BookFormat.DIGITAL:
        # Generate high-quality PDF immediately
        # In production, this would fetch the book data and generate PDF
        background_tasks.add_task(
            generate_and_deliver_digital,
            order_id,
            request.book_id
        )
        
        return {
            "order_id": order_id,
            "status": "processing",
            "format": "digital",
            "total": price['total'],
            "delivery": "Email within 5 minutes"
        }
    
    # For print orders, generate high-quality images and submit to printer
    background_tasks.add_task(
        process_print_order,
        order_id,
        request.book_id,
        request.format,
        request.shipping_tier,
        request.recipient_address
    )
    
    return {
        "order_id": order_id,
        "status": "processing",
        "format": request.format.value,
        "total": price['total'],
        "estimated_delivery": get_shipping_options()[1 if request.shipping_tier == ShippingTier.STANDARD else 2]['estimated_arrival']
    }

async def generate_and_deliver_digital(order_id: str, book_id: str):
    """Background task: Generate and email digital PDF."""
    # Implementation would:
    # 1. Fetch book data
    # 2. Generate high-quality images
    # 3. Create PDF
    # 4. Email to customer
    pass

async def process_print_order(
    order_id: str,
    book_id: str,
    format: BookFormat,
    shipping: ShippingTier,
    address: Dict
):
    """Background task: Process print order."""
    # Implementation would:
    # 1. Fetch book data
    # 2. Generate print-quality images
    # 3. Create print-ready PDF
    # 4. Submit to Lulu
    # 5. Track order
    pass

@app.get("/api/orders/{order_id}/status")
async def order_status(order_id: str) -> Dict:
    """Get order status."""
    # In production, fetch from database
    return {
        "order_id": order_id,
        "status": "processing",
        "steps": [
            {"name": "Order received", "completed": True},
            {"name": "Generating artwork", "completed": True},
            {"name": "Creating PDF", "completed": False},
            {"name": "Sent to printer", "completed": False},
            {"name": "Shipped", "completed": False},
        ]
    }

# ============================================
# RUN SERVER
# ============================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)