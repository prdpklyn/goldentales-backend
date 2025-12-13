# app/routers/v1/config.py
"""
GoldenTales Config Router (API v1)
==================================
Version 1 config endpoints returning public configuration.
"""

from typing import Dict

from fastapi import APIRouter

from app.settings import settings
from app.models.enums import Theme, ArtStyle, BookFormat
from app.utils.logging import get_logger
from character_system import (
    Gender, SkinTone, HairColor, HairStyle, EyeColor, BodyType,
    AdditionalCharacterType
)

logger = get_logger(__name__)

router = APIRouter()

# v1 API version
API_VERSION = "1.0.0"


def get_shipping_options():
    """Get available shipping options with prices."""
    return [
        {
            "id": "standard",
            "name": "Standard Shipping",
            "price": 5.99,
            "estimated_days": "7-10 business days"
        },
        {
            "id": "express",
            "name": "Express Shipping",
            "price": 12.99,
            "estimated_days": "3-5 business days"
        },
        {
            "id": "priority",
            "name": "Priority Shipping",
            "price": 19.99,
            "estimated_days": "1-2 business days"
        }
    ]


def get_countdown():
    """Get countdown timer configuration."""
    return {
        "enabled": True,
        "hours": 48,
        "message": "Order within {hours}h {minutes}m for guaranteed Christmas delivery!"
    }


@router.get("/config")
async def get_config() -> Dict:
    """
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
            "version": "v1",
            "status": "current",
            "deprecation": None,
            "sunset": None,
        },
        "api_version": API_VERSION,
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
