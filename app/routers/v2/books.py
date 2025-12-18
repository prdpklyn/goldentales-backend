# app/routers/v2/books.py
"""
GoldenTales V2 Books Router
============================
API endpoints for tier-aware book creation (Basic, Premium, Ultra).
"""

import uuid
from datetime import datetime
from typing import Dict, Optional
from fastapi import APIRouter, HTTPException, Request, Depends

from app.models.requests import CreateBookV2Request, RegeneratePageRequest
from app.models.responses import BookResponseV2, PageResponse
from app.models.enums import GenerationQuality, BookTier
from app.services.story_generator import StoryGenerator
from app.services.image_generator import ImageGenerator
from app.services.character_service import CharacterService
from app.services.photo_character_service import get_photo_character_service
from app.services.database import get_database
from app.middleware.jwt_auth import require_jwt_auth, JWTUser, extract_user_context_from_jwt
from app.utils.logging import get_logger
from app.utils.exceptions import ResourceNotFoundException, ValidationException

logger = get_logger(__name__)

router = APIRouter(prefix="/books", tags=["Books V2"])

# Database service for persistent storage via Edge Functions
db = get_database()


@router.post("/create", response_model=BookResponseV2)
async def create_book_v2(
    request: CreateBookV2Request,
    user: JWTUser = Depends(require_jwt_auth)
) -> BookResponseV2:
    """
    Create a new personalized storybook with tier selection.
    
    Tiers:
    - BASIC: AI character, standard side-by-side layout
    - PREMIUM: Full-page illustrations with text overlays
    - ULTRA: Photo-to-character transformation + Premium features
    
    This endpoint:
    1. Creates a character profile from the request
    2. Generates the character bible for consistency
    3. Generates a 10-page story using Gemini
    4. Generates illustrations using tier-appropriate methods
    5. Stores everything in database via Edge Functions
    6. Returns the complete book data
    
    Args:
        request: CreateBookV2Request with tier, character details, and settings
        
    Returns:
        BookResponseV2 with book data
        
    Raises:
        400: Invalid request or validation failed
        500: Internal server error
    """
    logger.info(f"Creating {request.tier.value} tier book for {user.user_id}")
    
    try:
        # Extract user context for RLS (user_id from JWT, token for forwarding)
        user_id = user.user_id
        auth_token = user.raw_token
        
        # Validate ULTRA tier requirements
        if request.tier == BookTier.ULTRA:
            if not request.character_reference_url:
                raise ValidationException(
                    "ULTRA tier requires character_reference_url from approved preview"
                )
        
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
        
        # 2. Create story record in database via Edge Function
        story_data = await db.create_story(
            child_name=request.child_name,
            child_age=request.child_age,
            theme=request.theme.value,
            art_style=request.art_style.value,
            tier=request.tier.value,
            photo_url=request.photo_url,
            character_reference_url=request.character_reference_url,
            occasion=request.occasion,
            special_details=request.special_details,
            status="generating",
            user_id=user_id,  # Required for RLS
            auth_token=auth_token  # Forward JWT token for RLS
        )
        
        book_id = story_data["id"]
        logger.info(f"Created story record: {book_id}")
        
        # 3. Generate story
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
        
        # 4. Generate illustrations with tier support
        image_generator = ImageGenerator()
        
        if request.tier in [BookTier.PREMIUM, BookTier.ULTRA]:
            # Use tier-aware generation
            illustrations = await image_generator.generate_all_illustrations_with_tier(
                character_bible=bible,
                story_pages=story_pages,
                art_style=request.art_style.value,
                tier=request.tier,
                character_reference_url=request.character_reference_url,
                quality=GenerationQuality.PREVIEW
            )
        else:
            # Use standard generation for BASIC tier
            illustrations = await image_generator.generate_all_illustrations(
                character_bible=bible,
                story_pages=story_pages,
                art_style=request.art_style.value,
                quality=GenerationQuality.PREVIEW
            )
        
        # 5. Store pages in database via Edge Functions
        for i, page in enumerate(story_pages):
            image_url = illustrations[i].get('url', '') if i < len(illustrations) else ''
            await db.create_page(
                story_id=book_id,
                page_number=page.get('page_number', i + 1),
                text_content=page.get('text', ''),
                image_prompt=page.get('scene_description', ''),
                image_url=image_url,
                auth_token=auth_token  # Forward JWT token for RLS
            )
        
        # 6. Update story status
        # Ensure character_bible is JSON-serializable (it's already a dict)
        await db.update_story(
            book_id, 
            {
                "status": "preview",
                "character_bible": bible  # This should be a dict, not a string
            },
            auth_token=auth_token  # Forward JWT token for RLS
        )
        
        # 7. Build response pages
        response_pages = [
            PageResponse(
                page_number=page.get('page_number', i + 1),
                text=page.get('text', ''),
                scene_description=page.get('scene_description', ''),
                character_action=page.get('character_action', ''),
                mood=page.get('mood', 'happy'),
                image_url=illustrations[i].get('url', '') if i < len(illustrations) else '',
                characters_in_scene=page.get('characters_in_scene', [])
            )
            for i, page in enumerate(story_pages)
        ]
        
        logger.info(f"{request.tier.value} tier book {book_id} created successfully")
        
        return BookResponseV2(
            book_id=book_id,
            title=f"{request.child_name}'s {request.theme.value.title()} Adventure",
            tier=request.tier,
            child_name=request.child_name,
            child_age=request.child_age,
            theme=request.theme.value,
            art_style=request.art_style.value,
            is_photo_based=request.tier == BookTier.ULTRA,
            character_reference_url=request.character_reference_url,
            pages=response_pages,
            preview_images=[img.get('url', '') for img in illustrations],
            page_count=len(story_pages),
            character_bible=bible,
            created_at=story_data["created_at"],
            status="preview"
        )
        
    except ValidationException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error creating book: {e}")
        # Clean up partial story if created
        if 'book_id' in locals():
            try:
                auth_token = user.raw_token if 'user' in locals() else None
                await db.update_story(book_id, {"status": "failed"}, auth_token=auth_token)
            except:
                pass
        raise HTTPException(status_code=500, detail=f"Failed to create book: {str(e)}")


@router.get("/{book_id}", response_model=BookResponseV2)
async def get_book_v2(
    book_id: str,
    user: JWTUser = Depends(require_jwt_auth)
) -> BookResponseV2:
    """
    Get a V2 book by ID via Edge Functions.
    
    Args:
        book_id: Book identifier
        
    Returns:
        BookResponseV2 with complete book data
        
    Raises:
        404: Book not found
    """
    # Fetch story from database via Edge Function
    story = await db.get_story(book_id)
    if not story:
        raise ResourceNotFoundException(resource_type="book", resource_id=book_id)
    
    # Fetch pages from database via Edge Function
    pages = await db.get_pages(book_id)
    
    # Build response pages
    response_pages = [
        PageResponse(
            page_number=p["page_number"],
            text=p["text_content"],
            scene_description=p["image_prompt"],
            character_action="",  # Not stored separately in DB
            mood="happy",  # Not stored separately in DB
            image_url=p.get("image_url", ""),
            characters_in_scene=[]  # Not stored separately in DB
        )
        for p in pages
    ]
    
    return BookResponseV2(
        book_id=story["id"],
        title=f"{story['child_name']}'s {story['theme'].title()} Adventure",
        tier=BookTier(story.get("tier", "basic")),
        child_name=story["child_name"],
        child_age=story["child_age"],
        theme=story["theme"],
        art_style=story.get("art_style", "watercolor"),
        is_photo_based=story.get("tier") == "ultra",
        character_reference_url=story.get("character_reference_url"),
        pages=response_pages,
        preview_images=[p.get("image_url", "") for p in pages if p.get("image_url")],
        page_count=len(pages),
        character_bible=story.get("character_bible"),
        created_at=story["created_at"],
        status=story.get("status", "preview")
    )


@router.post("/{book_id}/regenerate-page/{page_number}")
async def regenerate_page_v2(
    book_id: str,
    page_number: int,
    request: RegeneratePageRequest,
    user: JWTUser = Depends(require_jwt_auth)
) -> Dict:
    """
    Regenerate a specific page illustration (tier-aware) via Edge Functions.
    
    Uses the stored character bible and tier settings to maintain consistency.
    
    Args:
        book_id: Book identifier
        page_number: Page number to regenerate (1-based)
        request: Regeneration parameters
        
    Returns:
        Updated page with new image URL
        
    Raises:
        404: Book not found
        400: Invalid page number
        500: Regeneration failed
    """
    # Fetch story from database via Edge Function
    story = await db.get_story(book_id)
    if not story:
        raise ResourceNotFoundException(resource_type="book", resource_id=book_id)
    
    bible = story.get('character_bible')
    if not bible:
        raise ValidationException("Character profile not found")
    
    # Fetch the specific page
    page = await db.get_page_by_number(book_id, page_number)
    if not page:
        raise ValidationException("Invalid page number")
    
    tier = BookTier(story.get('tier', 'basic'))
    
    try:
        image_generator = ImageGenerator()
        
        # Use tier-aware generation if Premium/Ultra
        if tier in [BookTier.PREMIUM, BookTier.ULTRA]:
            illustration = await image_generator.generate_illustration_premium(
                character_bible=bible,
                scene_description=request.scene_description or page.get('image_prompt', ''),
                character_action=request.character_action or '',
                mood=request.mood or 'happy',
                art_style=story['art_style'],
                page_number=page_number,
                tier=tier,
                character_reference_url=story.get('character_reference_url'),
                characters_in_scene=request.include_characters or [],
                quality=GenerationQuality.PREVIEW
            )
        else:
            # Standard generation for BASIC tier
            illustration = await image_generator.generate_illustration(
                character_bible=bible,
                scene_description=request.scene_description or page.get('image_prompt', ''),
                character_action=request.character_action or '',
                mood=request.mood or 'happy',
                art_style=story['art_style'],
                page_number=page_number,
                characters_in_scene=request.include_characters or [],
                quality=GenerationQuality.PREVIEW
            )
        
        # Update page in database via Edge Function
        await db.update_page(
            page["id"], 
            {
                "image_url": illustration['url']
            },
            auth_token=user.raw_token
        )
        
        logger.info(f"Regenerated page {page_number} for {tier.value} tier book {book_id}")
        
        return {
            "book_id": book_id,
            "page_number": page_number,
            "new_image_url": illustration['url'],
            "tier": tier.value,
            "status": "success"
        }
        
    except ValidationException:
        raise
    except Exception as e:
        logger.error(f"Page regeneration failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to regenerate: {str(e)}")


@router.get("/{book_id}/preview")
async def get_book_preview_v2(
    book_id: str,
    user: JWTUser = Depends(require_jwt_auth)
) -> Dict:
    """
    Get preview images for a V2 book via Edge Functions.
    
    Args:
        book_id: Book identifier
        
    Returns:
        Preview data with images and tier information
        
    Raises:
        404: Book not found
    """
    # Fetch story from database via Edge Function
    story = await db.get_story(book_id)
    if not story:
        raise ResourceNotFoundException(resource_type="book", resource_id=book_id)
    
    # Fetch pages from database via Edge Function
    pages = await db.get_pages(book_id)
    
    return {
        "book_id": book_id,
        "title": f"{story['child_name']}'s {story['theme'].title()} Adventure",
        "tier": story.get("tier", "basic"),
        "preview_images": [p.get("image_url", "") for p in pages if p.get("image_url")],
        "page_count": len(pages),
        "is_photo_based": story.get("tier") == "ultra"
    }
