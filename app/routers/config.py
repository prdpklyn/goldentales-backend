# app/routers/config.py
"""
GoldenTales Config Router
=========================
API endpoints for public configuration and health checks.
"""

from datetime import datetime
from typing import Dict

from fastapi import APIRouter

from app.settings import settings
from app.models.enums import Theme, ArtStyle, BookFormat
from app.routers.orders import get_shipping_options, get_countdown
from app.utils.logging import get_logger
from character_system import (
    Gender, SkinTone, HairColor, HairStyle, EyeColor, BodyType,
    AdditionalCharacterType
)

logger = get_logger(__name__)

router = APIRouter(tags=["Config"])

# App version
VERSION = "3.0.0"


@router.get("/")
async def root():
    """Root endpoint / health check."""
    return {
        "service": "GoldenTales API",
        "version": VERSION,
        "status": "healthy"
    }


@router.get("/api/health")
async def health_check() -> Dict:
    """
    Detailed health check endpoint.
    
    Returns status of all dependencies and configuration.
    """
    checks = {
        "fal_key_configured": bool(settings.fal_key),
        "gemini_key_configured": bool(settings.gemini_api_key),
        "shopify_configured": bool(settings.shopify_webhook_secret),
    }
    
    all_healthy = all([
        checks["fal_key_configured"],
        checks["gemini_key_configured"]
    ])
    
    return {
        "status": "healthy" if all_healthy else "degraded",
        "version": VERSION,
        "environment": settings.environment.value,
        "checks": checks,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/api/config")
async def get_config() -> Dict:
    """
    ⚠️ DEPRECATED: This endpoint is deprecated. Use `/api/v1/config` instead.
    
    Sunset date: 2025-06-01
    
    Get all public configuration for the frontend.
    
    Returns available themes, styles, prices, and character options.
    """
    prices = {
        BookFormat.DIGITAL.value: settings.price_digital,
        BookFormat.SOFTCOVER.value: settings.price_softcover,
        BookFormat.HARDCOVER.value: settings.price_hardcover
    }
    
    return {
        "api": {
            "version": "legacy",
            "status": "deprecated",
            "deprecation": str(settings.legacy_api_deprecation_date),
            "sunset": str(settings.legacy_api_sunset_date),
            "successor": "/api/v1/config",
        },
        "themes": [t.value for t in Theme],
        "art_styles": [s.value for s in ArtStyle],
        "formats": [f.value for f in BookFormat],
        "prices": prices,
        "shipping_options": get_shipping_options(),
        "countdown": get_countdown(),
        "character_options": {
            "genders": [g.value for g in Gender],
            "skin_tones": [{"value": s.name, "label": s.value} for s in SkinTone],
            "hair_colors": [{"value": h.name, "label": h.value} for h in HairColor],
            "hair_styles": [{"value": h.name, "label": h.value} for h in HairStyle],
            "eye_colors": [{"value": e.name, "label": e.value} for e in EyeColor],
            "body_types": [{"value": b.name, "label": b.value} for b in BodyType],
            "additional_character_types": [t.value for t in AdditionalCharacterType]
        }
    }
