# app/models/requests.py
"""
GoldenTales Request Models
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
from app.models.enums import Theme, ArtStyle, BookFormat, ShippingTier, BookTier


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
            r'</s>', r'<\|', r'\|>'
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


# ============================================
# V2 API REQUEST MODELS (Premium/Ultra Tiers)
# ============================================

class ValidatePhotoRequest(BaseModel):
    """Request to validate a photo for character transformation."""
    photo_url: str = Field(..., description="URL of the child's photo")
    
    @field_validator('photo_url')
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate photo URL format."""
        if not v.startswith(('http://', 'https://')):
            raise ValueError('Photo URL must start with http:// or https://')
        return v


class PreviewCharacterRequest(BaseModel):
    """Request to generate character preview from photo."""
    photo_url: str = Field(..., description="URL of validated photo")
    art_style: ArtStyle = Field(..., description="Illustration style for transformation")
    preserve_likeness: float = Field(default=0.8, ge=0.5, le=1.0, description="How much to preserve photo likeness (0.5-1.0)")


class CreateBookV2Request(BaseModel):
    """V2 book creation request with tier selection."""
    
    # Tier selection
    tier: BookTier = Field(default=BookTier.BASIC, description="Book tier: basic, premium, or ultra")
    
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
    glasses_type: Optional[str] = None
    has_freckles: bool = False
    has_dimples: bool = False
    other_features: Optional[str] = None
    favorite_outfit: Optional[str] = None
    favorite_color: Optional[str] = None
    
    # Photo reference (REQUIRED for ULTRA tier)
    photo_url: Optional[str] = None
    character_reference_url: Optional[str] = None  # Transformed character image (from preview)
    
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
        
        dangerous_patterns = [
            r'ignore\s+previous', r'disregard', r'forget\s+everything',
            r'new\s+instructions', r'system:', r'assistant:', r'\[INST\]',
            r'</s>', r'<\|', r'\|>'
        ]
        for pattern in dangerous_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError('Invalid input detected')
        
        return v.strip()
    
    @field_validator('character_reference_url')
    @classmethod
    def validate_ultra_requirements(cls, v: Optional[str], info) -> Optional[str]:
        """Validate that ULTRA tier has character reference."""
        if info.data.get('tier') == BookTier.ULTRA and not v:
            raise ValueError('ULTRA tier requires character_reference_url from approved preview')
        return v


# ============================================
# PREVIEW API REQUEST MODELS (Kids Flow)
# ============================================

class QuickPreviewRequest(BaseModel):
    """Request for quick 60s preview generation."""
    child_name: str = Field(..., min_length=1, max_length=50, description="Child's name")
    child_gender: str = Field(..., description="One of: boy, girl, they")
    age_band: str = Field(..., description="One of: 3-5, 6-8, 9-12")
    theme: str = Field(..., description="One of: space, dinosaur, ocean, forest, superhero")
    photo_url: Optional[str] = Field(None, description="URL to uploaded photo for initial likeness")
    session_id: str = Field(..., description="Session tracking ID")

    @field_validator('child_gender')
    @classmethod
    def validate_gender(cls, v: str) -> str:
        """Validate gender options."""
        allowed = ['boy', 'girl', 'they']
        if v not in allowed:
            raise ValueError(f'child_gender must be one of: {", ".join(allowed)}')
        return v

    @field_validator('age_band')
    @classmethod
    def validate_age_band(cls, v: str) -> str:
        """Validate age band options."""
        allowed = ['3-5', '6-8', '9-12']
        if v not in allowed:
            raise ValueError(f'age_band must be one of: {", ".join(allowed)}')
        return v

    @field_validator('theme')
    @classmethod
    def validate_theme(cls, v: str) -> str:
        """Validate theme options."""
        allowed = ['space', 'dinosaur', 'ocean', 'forest', 'superhero']
        if v not in allowed:
            raise ValueError(f'theme must be one of: {", ".join(allowed)}')
        return v


class LikenessVariantsRequest(BaseModel):
    """Request for photo likeness variant generation."""
    photo_url: str = Field(..., description="URL to uploaded photo")
    art_style: str = Field(..., description="One of: watercolor, cartoon, storybook, anime")
    child_name: str = Field(..., min_length=1, max_length=50)
    child_gender: str = Field(..., description="One of: boy, girl, they")
    age_band: str = Field(..., description="One of: 3-5, 6-8, 9-12")
    num_variants: int = Field(default=3, ge=1, le=5, description="Number of variants (1-5)")

    @field_validator('art_style')
    @classmethod
    def validate_art_style(cls, v: str) -> str:
        """Validate art style options."""
        allowed = ['watercolor', 'cartoon', 'storybook', 'anime']
        if v not in allowed:
            raise ValueError(f'art_style must be one of: {", ".join(allowed)}')
        return v

    @field_validator('child_gender')
    @classmethod
    def validate_gender(cls, v: str) -> str:
        """Validate gender options."""
        allowed = ['boy', 'girl', 'they']
        if v not in allowed:
            raise ValueError(f'child_gender must be one of: {", ".join(allowed)}')
        return v

    @field_validator('age_band')
    @classmethod
    def validate_age_band(cls, v: str) -> str:
        """Validate age band options."""
        allowed = ['3-5', '6-8', '9-12']
        if v not in allowed:
            raise ValueError(f'age_band must be one of: {", ".join(allowed)}')
        return v


class PreviewRegenerateRequest(BaseModel):
    """Request for quick preview regeneration with tweaks."""
    preview_id: str = Field(..., description="Preview ID from initial generation")
    character_reference_url: Optional[str] = Field(None, description="URL to selected likeness variant")
    tweaks: Optional[Dict[str, str]] = Field(
        None,
        description="Optional tweaks: tone (funny/gentle/adventurous), art_modifier (softer/brighter/detailed), sidekick (dog/unicorn/robot/none)"
    )

    @field_validator('tweaks')
    @classmethod
    def validate_tweaks(cls, v: Optional[Dict[str, str]]) -> Optional[Dict[str, str]]:
        """Validate tweak options."""
        if v is None:
            return v

        allowed_tones = ['funny', 'gentle', 'adventurous']
        allowed_art_modifiers = ['softer', 'brighter', 'detailed']
        allowed_sidekicks = ['dog', 'unicorn', 'robot', 'none']

        if 'tone' in v and v['tone'] not in allowed_tones:
            raise ValueError(f'tone must be one of: {", ".join(allowed_tones)}')
        if 'art_modifier' in v and v['art_modifier'] not in allowed_art_modifiers:
            raise ValueError(f'art_modifier must be one of: {", ".join(allowed_art_modifiers)}')
        if 'sidekick' in v and v['sidekick'] not in allowed_sidekicks:
            raise ValueError(f'sidekick must be one of: {", ".join(allowed_sidekicks)}')

        return v
