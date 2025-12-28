# app/services/preview_service.py
"""
GoldenTales Preview Service
============================
Fast preview generation service for the Kids 60s Magic Preview flow.
"""

import uuid
import time
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from app.settings import settings
from app.utils.logging import get_logger
from app.utils.exceptions import ValidationException, ExternalServiceException
from app.services.story_generator import StoryGenerator
from app.services.image_generator import ImageGenerator
from app.services.character_service import CharacterService
from app.models.enums import GenerationQuality
from character_system import Gender, SkinTone, HairColor, HairStyle, EyeColor, BodyType

logger = get_logger(__name__)


# In-memory preview session storage (expires after 1 hour)
PREVIEW_SESSIONS: Dict[str, Dict[str, Any]] = {}


def _age_band_to_age(age_band: str) -> int:
    """Convert age band to representative age."""
    mapping = {
        "3-5": 4,
        "6-8": 7,
        "9-12": 10
    }
    return mapping.get(age_band, 7)


def _gender_to_enum(gender_str: str) -> Gender:
    """Convert string gender to Gender enum."""
    mapping = {
        "boy": Gender.BOY,
        "girl": Gender.GIRL,
        "they": Gender.NONBINARY
    }
    return mapping.get(gender_str, Gender.NONBINARY)


def _get_default_character_attributes(age_band: str, gender: str) -> Dict[str, Any]:
    """Get default character attributes for quick preview."""
    # Default to common attributes for speed
    return {
        "skin_tone": SkinTone.LIGHT,
        "hair_color": HairColor.BROWN,
        "hair_style": HairStyle.SHORT if gender == "boy" else HairStyle.LONG_STRAIGHT,
        "eye_color": EyeColor.BROWN,
        "body_type": BodyType.AVERAGE
    }


class PreviewService:
    """
    Service for fast preview generation.

    Generates cover + hero portrait + 2 spreads in under 60 seconds.
    """

    def __init__(self):
        self.story_generator = StoryGenerator()
        self.image_generator = ImageGenerator()
        self.character_service = CharacterService()

    async def generate_quick_preview(
        self,
        child_name: str,
        child_gender: str,
        age_band: str,
        theme: str,
        photo_url: Optional[str],
        session_id: str
    ) -> Dict[str, Any]:
        """
        Generate a quick preview in under 60 seconds.

        Args:
            child_name: Child's name
            child_gender: One of: boy, girl, they
            age_band: One of: 3-5, 6-8, 9-12
            theme: One of: space, dinosaur, ocean, forest, superhero
            photo_url: Optional photo URL for initial likeness
            session_id: Session tracking ID

        Returns:
            Dict with preview data

        Raises:
            ValidationException: Invalid input
            ExternalServiceException: AI service error
        """
        start_time = time.time()
        logger.info(f"Starting quick preview for {child_name}, theme: {theme}")

        try:
            # Convert inputs to internal format
            child_age = _age_band_to_age(age_band)
            gender_enum = _gender_to_enum(child_gender)
            default_attrs = _get_default_character_attributes(age_band, child_gender)

            # 1. Create character profile (fast, minimal attributes)
            profile, bible = await self.character_service.create_profile(
                child_name=child_name,
                child_gender=gender_enum,
                child_age=child_age,
                skin_tone=default_attrs["skin_tone"],
                hair_color=default_attrs["hair_color"],
                hair_style=default_attrs["hair_style"],
                eye_color=default_attrs["eye_color"],
                body_type=default_attrs["body_type"],
                photo_url=photo_url,
                theme=theme,
                art_style="watercolor"  # Default to watercolor for preview
            )

            # 2. Generate a SHORT story (just 2 pages for preview)
            story_pages = await self.story_generator.generate_preview_story(
                character_bible=bible,
                child_name=child_name,
                age=child_age,
                theme=theme,
                num_pages=2  # Only 2 pages for quick preview
            )

            # 3. Generate images in parallel for speed
            # Cover + Hero Portrait + 2 Spreads
            tasks = [
                # Cover image
                self.image_generator.generate_cover(
                    character_bible=bible,
                    title=f"{child_name}'s {theme.title()} Adventure",
                    art_style="watercolor",
                    quality=GenerationQuality.PREVIEW
                ),
                # Hero portrait (placeholder if no photo)
                self.image_generator.generate_hero_portrait(
                    character_bible=bible,
                    art_style="watercolor",
                    photo_url=photo_url,
                    quality=GenerationQuality.PREVIEW
                ),
                # Page 1 illustration
                self.image_generator.generate_illustration(
                    character_bible=bible,
                    scene_description=story_pages[0].get('scene_description', ''),
                    character_action=story_pages[0].get('character_action', ''),
                    mood=story_pages[0].get('mood', 'happy'),
                    art_style="watercolor",
                    page_number=1,
                    quality=GenerationQuality.PREVIEW
                ),
                # Page 2 illustration
                self.image_generator.generate_illustration(
                    character_bible=bible,
                    scene_description=story_pages[1].get('scene_description', ''),
                    character_action=story_pages[1].get('character_action', ''),
                    mood=story_pages[1].get('mood', 'happy'),
                    art_style="watercolor",
                    page_number=2,
                    quality=GenerationQuality.PREVIEW
                )
            ]

            # Run all image generation in parallel
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Check for errors
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Image generation failed for task {i}: {result}")
                    raise ExternalServiceException(f"Image generation failed: {str(result)}")

            cover_img, hero_img, page1_img, page2_img = results

            # 4. Store preview session
            preview_id = str(uuid.uuid4())
            preview_data = {
                "preview_id": preview_id,
                "session_id": session_id,
                "child_name": child_name,
                "child_gender": child_gender,
                "age_band": age_band,
                "theme": theme,
                "character_bible": bible,
                "story_pages": story_pages,
                "cover_url": cover_img.get('url', ''),
                "cover_prompt": cover_img.get('prompt', ''),
                "hero_url": hero_img.get('url', ''),
                "is_placeholder": photo_url is None,
                "page1_url": page1_img.get('url', ''),
                "page1_text": story_pages[0].get('text', ''),
                "page2_url": page2_img.get('url', ''),
                "page2_text": story_pages[1].get('text', ''),
                "created_at": datetime.utcnow().isoformat(),
                "expires_at": (datetime.utcnow() + timedelta(hours=1)).isoformat()
            }

            PREVIEW_SESSIONS[preview_id] = preview_data

            # 5. Calculate total time
            generation_time_ms = int((time.time() - start_time) * 1000)
            logger.info(f"Quick preview generated in {generation_time_ms}ms")

            # 6. Build response
            return {
                "preview_id": preview_id,
                "title": f"{child_name}'s {theme.title()} Adventure",
                "cover": {
                    "image_url": cover_img.get('url', ''),
                    "prompt_used": cover_img.get('prompt', '')
                },
                "hero_portrait": {
                    "image_url": hero_img.get('url', ''),
                    "is_placeholder": photo_url is None
                },
                "spreads": [
                    {
                        "page_number": 1,
                        "image_url": page1_img.get('url', ''),
                        "text": story_pages[0].get('text', '')
                    },
                    {
                        "page_number": 2,
                        "image_url": page2_img.get('url', ''),
                        "text": story_pages[1].get('text', '')
                    }
                ],
                "metadata": {
                    "generation_time_ms": generation_time_ms,
                    "model_version": "v2.1",
                    "art_style": "watercolor"
                }
            }

        except Exception as e:
            logger.error(f"Quick preview generation failed: {e}")
            raise ExternalServiceException(f"Failed to generate preview: {str(e)}")

    async def regenerate_preview(
        self,
        preview_id: str,
        character_reference_url: Optional[str],
        tweaks: Optional[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        Regenerate preview with user tweaks.

        Args:
            preview_id: Preview ID from initial generation
            character_reference_url: URL to selected likeness variant
            tweaks: Optional tweaks (tone, art_modifier, sidekick)

        Returns:
            Dict with regenerated preview data

        Raises:
            ValidationException: Preview not found or expired
            ExternalServiceException: AI service error
        """
        start_time = time.time()
        logger.info(f"Regenerating preview {preview_id} with tweaks: {tweaks}")

        # Get existing preview session
        session = PREVIEW_SESSIONS.get(preview_id)
        if not session:
            raise ValidationException("Preview not found or expired")

        # Check expiration
        expires_at = datetime.fromisoformat(session["expires_at"])
        if datetime.utcnow() > expires_at:
            del PREVIEW_SESSIONS[preview_id]
            raise ValidationException("Preview expired")

        try:
            # Apply tweaks to character bible and story
            bible = session["character_bible"].copy()
            story_pages = session["story_pages"].copy()

            # Apply tone tweak to story
            if tweaks and "tone" in tweaks:
                tone = tweaks["tone"]
                # Modify story tone
                for page in story_pages:
                    if tone == "funny":
                        page["mood"] = "playful"
                    elif tone == "gentle":
                        page["mood"] = "calm"
                    elif tone == "adventurous":
                        page["mood"] = "excited"

            # Apply sidekick tweak to character bible
            if tweaks and "sidekick" in tweaks and tweaks["sidekick"] != "none":
                sidekick = tweaks["sidekick"]
                if "additional_characters" not in bible:
                    bible["additional_characters"] = []
                bible["additional_characters"].append(f"a friendly {sidekick} companion")

            # Apply art modifier to prompts
            art_modifier = tweaks.get("art_modifier", "") if tweaks else ""

            # Regenerate hero portrait (if character reference provided)
            if character_reference_url:
                hero_img = await self.image_generator.generate_hero_portrait_with_reference(
                    character_reference_url=character_reference_url,
                    art_style="watercolor",
                    art_modifier=art_modifier,
                    quality=GenerationQuality.PREVIEW
                )
                session["hero_url"] = hero_img.get('url', '')
                session["is_placeholder"] = False

            # Regenerate page illustrations in parallel
            tasks = [
                self.image_generator.generate_illustration(
                    character_bible=bible,
                    scene_description=story_pages[0].get('scene_description', ''),
                    character_action=story_pages[0].get('character_action', ''),
                    mood=story_pages[0].get('mood', 'happy'),
                    art_style="watercolor",
                    page_number=1,
                    art_modifier=art_modifier,
                    quality=GenerationQuality.PREVIEW
                ),
                self.image_generator.generate_illustration(
                    character_bible=bible,
                    scene_description=story_pages[1].get('scene_description', ''),
                    character_action=story_pages[1].get('character_action', ''),
                    mood=story_pages[1].get('mood', 'happy'),
                    art_style="watercolor",
                    page_number=2,
                    art_modifier=art_modifier,
                    quality=GenerationQuality.PREVIEW
                )
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Check for errors
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Page regeneration failed for page {i+1}: {result}")
                    raise ExternalServiceException(f"Page regeneration failed: {str(result)}")

            page1_img, page2_img = results

            # Update session
            session["page1_url"] = page1_img.get('url', '')
            session["page2_url"] = page2_img.get('url', '')
            session["character_bible"] = bible
            session["story_pages"] = story_pages

            generation_time_ms = int((time.time() - start_time) * 1000)
            logger.info(f"Preview regenerated in {generation_time_ms}ms")

            return {
                "preview_id": preview_id,
                "hero_portrait": {
                    "image_url": session["hero_url"],
                    "updated": character_reference_url is not None
                },
                "spreads": [
                    {
                        "page_number": 1,
                        "image_url": page1_img.get('url', ''),
                        "text": story_pages[0].get('text', ''),
                        "updated": True
                    },
                    {
                        "page_number": 2,
                        "image_url": page2_img.get('url', ''),
                        "text": story_pages[1].get('text', ''),
                        "updated": True
                    }
                ],
                "metadata": {
                    "regeneration_time_ms": generation_time_ms,
                    "tweaks_applied": tweaks or {}
                }
            }

        except ValidationException:
            raise
        except Exception as e:
            logger.error(f"Preview regeneration failed: {e}")
            raise ExternalServiceException(f"Failed to regenerate preview: {str(e)}")

    def get_preview_session(self, preview_id: str) -> Optional[Dict[str, Any]]:
        """Get preview session by ID."""
        session = PREVIEW_SESSIONS.get(preview_id)
        if not session:
            return None

        # Check expiration
        expires_at = datetime.fromisoformat(session["expires_at"])
        if datetime.utcnow() > expires_at:
            del PREVIEW_SESSIONS[preview_id]
            return None

        return session

    def cleanup_expired_sessions(self):
        """Remove expired preview sessions."""
        now = datetime.utcnow()
        expired = [
            pid for pid, session in PREVIEW_SESSIONS.items()
            if datetime.fromisoformat(session["expires_at"]) <= now
        ]
        for pid in expired:
            del PREVIEW_SESSIONS[pid]
        if expired:
            logger.info(f"Cleaned up {len(expired)} expired preview sessions")
