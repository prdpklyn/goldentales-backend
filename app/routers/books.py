# app/routers/books.py
"""
GoldenTales Books Router
========================
API endpoints for book creation and management.
"""

import uuid
from datetime import datetime
from typing import Dict

from fastapi import APIRouter, HTTPException

from app.settings import settings
from app.models.requests import CreateBookRequest, RegeneratePageRequest
from app.models.enums import GenerationQuality
from app.services.story_generator import StoryGenerator
from app.services.image_generator import ImageGenerator
from app.services.character_service import CharacterService
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/books", tags=["Books"])

# In-memory storage (replace with database in production)
book_storage: Dict[str, Dict] = {}
character_profiles: Dict[str, object] = {}
character_bibles: Dict[str, Dict] = {}


@router.post("/create")
async def create_book(request: CreateBookRequest) -> Dict:
    """
    Create a new personalized storybook with preview-quality images.
    
    This endpoint:
    1. Creates a character profile from the request
    2. Generates the character bible for consistency
    3. Generates a 10-page story using Gemini
    4. Generates preview illustrations using Fal.ai
    5. Returns the complete book data
    
    The character bible is stored and used for page regeneration
    to maintain consistency.
    """
    book_id = str(uuid.uuid4())[:8]
    
    logger.info(f"Creating book {book_id} for {request.child_name}")
    
    try:
        # 1. Create character profile and bible
        character_service = CharacterService()
        profile, bible = await character_service.create_profile(
            child_name=request.child_name,
            child_gender=request.child_gender,
            child_age=request.child_age,
            skin_tone=request.skin_tone,
            hair_color=request.hair_color,
            hair_style=request.hair_style,
            eye_color=request.eye_color,
            body_type=request.body_type,
            has_glasses=request.has_glasses,
            glasses_type=request.glasses_type,
            has_freckles=request.has_freckles,
            has_dimples=request.has_dimples,
            other_features=request.other_features,
            favorite_outfit=request.favorite_outfit,
            favorite_color=request.favorite_color,
            photo_url=request.photo_url,
            additional_characters=request.additional_characters,
            theme=request.theme.value,
            art_style=request.art_style.value
        )
        
        character_profiles[book_id] = profile
        character_bibles[book_id] = bible
        
        # 2. Generate story
        story_generator = StoryGenerator()
        story_pages = await story_generator.generate_story(
            character_bible=bible,
            child_name=request.child_name,
            age=request.child_age,
            theme=request.theme.value,
            occasion=request.occasion,
            special_details=request.special_details,
            additional_characters=profile.additional_characters
        )
        
        # 3. Generate preview illustrations
        image_generator = ImageGenerator()
        illustrations = await image_generator.generate_all_illustrations(
            character_bible=bible,
            story_pages=story_pages,
            art_style=request.art_style.value,
            quality=GenerationQuality.PREVIEW
        )
        
        # 4. Store book data
        book_data = {
            "book_id": book_id,
            "title": f"{request.child_name}'s {request.theme.value.title()} Adventure",
            "child_name": request.child_name,
            "child_age": request.child_age,
            "theme": request.theme.value,
            "art_style": request.art_style.value,
            "pages": story_pages,
            "preview_images": [img.get('url', '') for img in illustrations],
            "page_count": len(story_pages),
            "character_bible": bible,
            "created_at": datetime.now().isoformat(),
            "status": "preview"
        }
        
        book_storage[book_id] = book_data
        
        logger.info(f"Book {book_id} created successfully")
        
        return book_data
        
    except ValueError as e:
        logger.error(f"Book creation failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error creating book: {e}")
        raise HTTPException(status_code=500, detail="Failed to create book")


@router.get("/{book_id}")
async def get_book(book_id: str) -> Dict:
    """Get a book by ID."""
    if book_id not in book_storage:
        raise HTTPException(status_code=404, detail="Book not found")
    return book_storage[book_id]


@router.post("/{book_id}/regenerate-page/{page_number}")
async def regenerate_page(
    book_id: str,
    page_number: int,
    request: RegeneratePageRequest
) -> Dict:
    """
    Regenerate a specific page illustration.
    
    Uses the stored character bible to maintain consistency.
    """
    if book_id not in book_storage:
        raise HTTPException(status_code=404, detail="Book not found")
    
    book = book_storage[book_id]
    bible = book.get('character_bible') or character_bibles.get(book_id)
    
    if not bible:
        raise HTTPException(status_code=400, detail="Character profile not found")
    
    if page_number < 1 or page_number > len(book['pages']):
        raise HTTPException(status_code=400, detail="Invalid page number")
    
    page = book['pages'][page_number - 1]
    
    try:
        image_generator = ImageGenerator()
        
        illustration = await image_generator.generate_illustration(
            character_bible=bible,
            scene_description=request.scene_description or page.get('scene_description', ''),
            character_action=request.character_action or page.get('character_action', ''),
            mood=request.mood or page.get('mood', 'happy'),
            art_style=book['art_style'],
            page_number=page_number,
            characters_in_scene=request.include_characters or page.get('characters_in_scene', []),
            quality=GenerationQuality.PREVIEW
        )
        
        # Update stored image
        book['preview_images'][page_number - 1] = illustration['url']
        
        logger.info(f"Regenerated page {page_number} for book {book_id}")
        
        return {
            "book_id": book_id,
            "page_number": page_number,
            "new_image_url": illustration['url'],
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Page regeneration failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to regenerate: {str(e)}")


@router.get("/{book_id}/preview")
async def get_book_preview(book_id: str) -> Dict:
    """Get preview images for a book."""
    if book_id not in book_storage:
        raise HTTPException(status_code=404, detail="Book not found")
    
    book = book_storage[book_id]
    return {
        "book_id": book_id,
        "title": book.get("title"),
        "preview_images": book.get("preview_images", []),
        "page_count": book.get("page_count", 0)
    }


# Export storage for use by other modules
def get_book_storage() -> Dict[str, Dict]:
    """Get reference to book storage."""
    return book_storage


def get_character_bibles() -> Dict[str, Dict]:
    """Get reference to character bibles."""
    return character_bibles
