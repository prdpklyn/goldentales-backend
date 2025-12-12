# app/models/requests.py
"""
DreamWeaver Request Models
==========================
Pydantic models for API request validation.
"""

import re
from typing import List, Optional, Dict
from pydantic import BaseModel, Field, field_validator

# Import character enums from character_system
from character_system import (
    Gender, SkinTone, HairColor, HairStyle, EyeColor, BodyType,
    AdditionalCharacterType
)
from app.models.enums import Theme, ArtStyle, BookFormat, ShippingTier


class AddCharacterRequest(BaseModel):
    """Request to add an additional character."""
    name: str = Field(..., min_length=1, max_length=30)
    character_type: AdditionalCharacterType
    relationship: str  # "little sister", "pet dog"
    
    # For humans
    gender: Optional[Gender] = None
    age_description: Optional[str] = None
    skin_tone: Optional[SkinTone] = None
    hair_color: Optional[HairColor] = None
    
    # For pets
    pet_species: Optional[str] = None
    pet_color: Optional[str] = None
    
    distinctive_feature: Optional[str] = None


class CreateBookRequest(BaseModel):
    """Full book creation request with character details."""
    
    # Main character - REQUIRED
    child_name: str = Field(..., min_length=2, max_length=30)
    child_gender: Gender
    child_age: int = Field(..., ge=2, le=12)
    
    # Physical appearance - REQUIRED for consistency
    skin_tone: SkinTone
    hair_color: HairColor
    hair_style: HairStyle
    eye_color: EyeColor = EyeColor.BROWN
    body_type: BodyType = BodyType.AVERAGE
    
    # Optional appearance details
    has_glasses: bool = False
    glasses_type: Optional[str] = None  # "round pink glasses"
    has_freckles: bool = False
    has_dimples: bool = False
    other_features: Optional[str] = None  # "birthmark on cheek"
    favorite_outfit: Optional[str] = None  # "red dress with white dots"
    favorite_color: Optional[str] = None
    
    # Photo reference
    photo_url: Optional[str] = None
    
    # Additional characters
    additional_characters: List[AddCharacterRequest] = []
    
    # Story settings
    theme: Theme
    art_style: ArtStyle
    occasion: Optional[str] = None
    special_details: Optional[str] = Field(None, max_length=500)
    
    @field_validator('child_name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate child name contains only safe characters."""
        if not re.match(r"^[a-zA-Z\s'\-]+$", v):
            raise ValueError('Name can only contain letters, spaces, apostrophes, and hyphens')
        return v.strip()
    
    @field_validator('special_details')
    @classmethod
    def sanitize_special_details(cls, v: Optional[str]) -> Optional[str]:
        """Sanitize special details to prevent prompt injection."""
        if v is None:
            return None
        
        # Remove potential prompt injection patterns
        dangerous_patterns = [
            r'ignore\s+previous', r'disregard', r'forget\s+everything',
            r'new\s+instructions', r'system:', r'assistant:', r'\[INST\]',
            r'</s>', r'<|', r'|>'
        ]
        for pattern in dangerous_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError('Invalid input detected')
        
        return v.strip()


class RegeneratePageRequest(BaseModel):
    """Request to regenerate a specific page."""
    scene_description: Optional[str] = Field(None, max_length=500)
    character_action: Optional[str] = Field(None, max_length=200)
    mood: Optional[str] = "happy"
    include_characters: Optional[List[str]] = None  # Names of additional chars


class OrderRequest(BaseModel):
    """Request to create an order."""
    book_id: str
    format: BookFormat
    shipping_tier: ShippingTier
    gift_wrap: bool = False
    gift_message: Optional[str] = Field(None, max_length=200)
    recipient_email: Optional[str] = None
    recipient_address: Optional[Dict[str, str]] = None
