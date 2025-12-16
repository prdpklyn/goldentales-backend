# app/models/pdf_models.py
"""
GoldenTales PDF Data Models
===========================
Pydantic models for PDF story data from Supabase Edge Function.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


# ============================================
# REQUEST MODELS
# ============================================

class GetStoryForPDFRequest(BaseModel):
    """Request to fetch story data for PDF generation."""
    story_id: str = Field(..., description="UUID of the story to fetch")


# ============================================
# RESPONSE MODELS - Story Data
# ============================================

class HeroCharacter(BaseModel):
    """Hero character details from character_json."""
    name: str
    age: int
    gender: str
    body_type: Optional[str] = None
    eye_color: Optional[str] = None
    skin_tone: Optional[str] = None
    hair_color: Optional[str] = None
    hair_style: Optional[str] = None
    has_dimples: bool = False
    has_glasses: bool = False
    has_freckles: bool = False


class CharacterJSON(BaseModel):
    """Character configuration from story."""
    hero: HeroCharacter
    additional_characters: List[Dict[str, Any]] = []


class StoryData(BaseModel):
    """Story metadata from Supabase."""
    id: str
    child_name: str
    child_age: int
    theme: str
    art_style: str
    gender: str
    skin_tone: Optional[str] = None
    hair_color: Optional[str] = None
    hair_style: Optional[str] = None
    eye_color: Optional[str] = None
    special_features: Optional[str] = None
    occasion: Optional[str] = None
    special_details: Optional[str] = None
    siblings: Optional[str] = None
    favorite_characters: Optional[str] = None
    pets: Optional[str] = None
    parents: Optional[str] = None
    friends: Optional[str] = None
    photo_url: Optional[str] = None
    cover_image_url: Optional[str] = None
    character_json: Optional[CharacterJSON] = None
    status: str = "ready"
    error_json: Optional[Dict[str, Any]] = None
    user_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class PageData(BaseModel):
    """Individual page data from Supabase."""
    id: str
    story_id: str
    page_number: int
    text_content: str
    image_prompt: Optional[str] = None
    image_url: Optional[str] = None
    version: int = 1
    is_current: bool = True
    edited_by_user: bool = False
    regen_count: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class StoryForPDFData(BaseModel):
    """Combined story and pages data."""
    story: StoryData
    pages: List[PageData]


class StoryForPDFResponse(BaseModel):
    """Response from get-story-for-pdf endpoint."""
    success: bool
    data: Optional[StoryForPDFData] = None
    error: Optional[str] = None


# ============================================
# INTERNAL MODELS - For PDF Generation
# ============================================

class PDFPageContent(BaseModel):
    """Simplified page content for PDF generation."""
    page_number: int
    text: str
    image_url: Optional[str] = None
    image_prompt: Optional[str] = None


class PDFBookData(BaseModel):
    """Book data structured for PDF generation service."""
    book_id: str
    title: str
    child_name: str
    child_age: int
    theme: str
    art_style: str
    cover_image_url: Optional[str] = None
    pages: List[PDFPageContent]
    character_bible: Optional[Dict[str, Any]] = None
    
    @classmethod
    def from_story_response(cls, response: StoryForPDFResponse) -> "PDFBookData":
        """Convert Supabase response to PDF book data."""
        if not response.success or not response.data:
            raise ValueError("Invalid story response")
        
        story = response.data.story
        pages = response.data.pages
        
        # Sort pages by page_number
        sorted_pages = sorted(pages, key=lambda p: p.page_number)
        
        # Build character bible from character_json
        character_bible = None
        if story.character_json:
            hero = story.character_json.hero
            character_bible = {
                "main_character": (
                    f"{hero.name}, {hero.age}-year-old {hero.gender} with "
                    f"{hero.skin_tone or 'light skin'}, {hero.hair_color or 'brown hair'}, "
                    f"in {hero.hair_style or 'neat'} style, and {hero.eye_color or 'brown eyes'}"
                ),
                "main_character_short": f"{hero.name}, {hero.age}-year-old {hero.gender}",
                "additional_characters": story.character_json.additional_characters
            }
        
        return cls(
            book_id=story.id,
            title=f"{story.child_name}'s {story.theme.title()} Adventure",
            child_name=story.child_name,
            child_age=story.child_age,
            theme=story.theme,
            art_style=story.art_style,
            cover_image_url=story.cover_image_url,
            pages=[
                PDFPageContent(
                    page_number=p.page_number,
                    text=p.text_content,
                    image_url=p.image_url,
                    image_prompt=p.image_prompt
                )
                for p in sorted_pages
            ],
            character_bible=character_bible
        )

