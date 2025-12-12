# app/models/responses.py
"""
DreamWeaver Response Models
===========================
Pydantic models for API response serialization.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime

from app.models.enums import OrderStatus


class PageResponse(BaseModel):
    """Single story page response."""
    page_number: int
    text: str
    scene_description: str
    character_action: Optional[str] = None
    mood: str = "happy"
    image_url: Optional[str] = None
    characters_in_scene: List[str] = []


class BookResponse(BaseModel):
    """Full book response."""
    book_id: str
    title: str
    child_name: str
    child_age: int
    theme: str
    art_style: str
    pages: List[PageResponse]
    preview_images: List[str]
    page_count: int
    character_bible: Optional[Dict[str, Any]] = None
    created_at: str
    status: str = "preview"


class PriceResponse(BaseModel):
    """Price calculation response."""
    book_id: str
    format: str
    base_price: float
    shipping_cost: float
    gift_wrap_cost: float
    total: float
    currency: str = "USD"


class OrderResponse(BaseModel):
    """Order creation response."""
    order_id: str
    book_id: str
    book_title: str
    total: float
    status: str
    estimated_delivery: str
    checkout_url: str


class OrderStatusResponse(BaseModel):
    """Order status response."""
    order_id: str
    status: OrderStatus
    steps: List[Dict[str, str]]


class ShippingOptionResponse(BaseModel):
    """Shipping option details."""
    tier: str
    name: str
    description: str
    available: bool
    deadline: Optional[str] = None
    estimated_arrival: str
    days_until_deadline: int = 0


class CountdownResponse(BaseModel):
    """Christmas countdown response."""
    expired: bool
    days: int
    hours: int
    minutes: int
    urgency: str
    deadline: Optional[str] = None


class ConfigResponse(BaseModel):
    """Public configuration response."""
    themes: List[str]
    art_styles: List[str]
    prices: Dict[str, float]
    shipping_options: List[ShippingOptionResponse]
    countdown: CountdownResponse
    character_options: Dict[str, Any]


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    environment: str
    checks: Dict[str, bool]
    timestamp: str
