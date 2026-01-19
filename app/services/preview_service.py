# app/services/preview_service.py
"""
GoldenTales Preview Service v2.0
================================
Fast preview generation service for the Kids 60s Magic Preview flow.

UPDATED: Now uses Pixar/Disney-like 3D animation style instead of watercolor.
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
from app.models.enums import GenerationQuality, ArtStyle
from character_system import Gender, SkinTone, HairColor, HairStyle, EyeColor, BodyType

logger = get_logger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

# In-memory preview session storage (expires after 1 hour)
PREVIEW_SESSIONS: Dict[str, Dict[str, Any]] = {}

# Art style configuration - Pixar/Disney 3D Animation
PIXAR_ART_STYLE = "pixar_3d"

PIXAR_STYLE_PROMPT_PREFIX = """
Pixar-style 3D animated character, Disney animation quality, 
soft volumetric lighting, subsurface skin scattering, 
expressive cartoon eyes with catchlights, 
rounded friendly features, warm color palette,
high-quality 3D render, octane render quality,
cinematic lighting, depth of field,
""".strip().replace("\n", " ")

PIXAR_STYLE_NEGATIVE_PROMPT = """
anime, 2D, flat, watercolor, sketch, drawing, painting,
realistic, photorealistic, uncanny valley, scary, dark,
low quality, blurry, distorted, deformed, ugly,
text, watermark, signature, logo
""".strip().replace("\n", " ")

# Theme-specific scene settings for Pixar style
THEME_SCENE_SETTINGS = {
    "space": {
        "environment": "colorful nebula space background with twinkling stars and friendly planets",
        "lighting": "cosmic glow with purple and blue rim lighting",
        "props": ["rocket ship", "friendly alien", "floating asteroids", "space helmet"],
        "mood_colors": ["deep purple", "cosmic blue", "starlight white", "nebula pink"]
    },
    "dinosaur": {
        "environment": "lush prehistoric jungle with giant ferns and volcanoes in distance",
        "lighting": "warm golden hour sunlight filtering through leaves",
        "props": ["friendly dinosaur", "dinosaur eggs", "prehistoric plants", "butterfly"],
        "mood_colors": ["jungle green", "warm orange", "sky blue", "earthy brown"]
    },
    "ocean": {
        "environment": "vibrant coral reef underwater world with sunbeams from surface",
        "lighting": "dappled underwater caustics, bioluminescent glow",
        "props": ["friendly fish", "sea turtle", "coral", "treasure chest", "bubbles"],
        "mood_colors": ["ocean blue", "coral pink", "seafoam green", "sandy gold"]
    },
    "forest": {
        "environment": "magical enchanted forest with glowing mushrooms and fairy lights",
        "lighting": "soft dappled sunlight through canopy, magical sparkles",
        "props": ["woodland creatures", "mushroom house", "butterfly", "flowers"],
        "mood_colors": ["forest green", "warm amber", "soft pink", "magical purple"]
    },
    "superhero": {
        "environment": "colorful cartoon city skyline with fluffy clouds",
        "lighting": "heroic dramatic lighting with lens flare",
        "props": ["cape", "mask", "city buildings", "swoosh lines"],
        "mood_colors": ["hero red", "power blue", "gold", "sky blue"]
    }
}


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

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
        "they": Gender.GIRL  # Default to GIRL for 'they' since Gender enum only has BOY/GIRL
    }
    return mapping.get(gender_str, Gender.GIRL)


def _get_default_character_attributes(age_band: str, gender: str) -> Dict[str, Any]:
    """Get default character attributes for quick preview."""
    return {
        "skin_tone": SkinTone.LIGHT,
        "hair_color": HairColor.BROWN,
        "hair_style": HairStyle.SHORT_NEAT if gender == "boy" else HairStyle.LONG_STRAIGHT,
        "eye_color": EyeColor.BROWN,
        "body_type": BodyType.AVERAGE
    }


def _build_pixar_character_prompt(
    child_name: str,
    gender: str,
    age: int,
    character_bible: Dict[str, Any],
    action: str = "smiling happily"
) -> str:
    """
    Build a Pixar/Disney style character prompt.
    
    Args:
        child_name: Child's name
        gender: boy/girl/they
        age: Child's age
        character_bible: Character description dict
        action: What the character is doing
        
    Returns:
        Formatted prompt string for Pixar-style generation
    """
    # Gender-specific terms
    gender_term = "boy" if gender == "boy" else "girl"
    pronoun = "he" if gender == "boy" else "she"
    
    # Extract character features from bible
    skin_tone = character_bible.get("skin_tone", "light")
    hair_color = character_bible.get("hair_color", "brown")
    hair_style = character_bible.get("hair_style", "short neat")
    eye_color = character_bible.get("eye_color", "brown")
    
    prompt = f"""
{PIXAR_STYLE_PROMPT_PREFIX}
adorable {age}-year-old {gender_term} character named {child_name},
{skin_tone} skin tone, {hair_color} {hair_style} hair, 
big expressive {eye_color} eyes with sparkle highlights,
{action},
cute button nose, rosy cheeks, friendly smile,
wearing colorful adventure clothes,
full body shot, dynamic pose,
Pixar movie quality, Disney animation style,
ultra detailed, 8k resolution
""".strip().replace("\n", " ")
    
    return prompt


def _build_pixar_scene_prompt(
    child_name: str,
    character_bible: Dict[str, Any],
    theme: str,
    scene_description: str,
    character_action: str,
    mood: str
) -> str:
    """
    Build a Pixar/Disney style scene prompt.
    
    Args:
        child_name: Child's name
        character_bible: Character description dict
        theme: Story theme (space, dinosaur, etc.)
        scene_description: Description of the scene
        character_action: What the character is doing
        mood: Emotional mood of the scene
        
    Returns:
        Formatted prompt string for Pixar-style scene
    """
    theme_settings = THEME_SCENE_SETTINGS.get(theme, THEME_SCENE_SETTINGS["forest"])
    
    # Build character description
    gender = character_bible.get("gender", "child")
    age = character_bible.get("age", 7)
    skin_tone = character_bible.get("skin_tone", "light")
    hair_color = character_bible.get("hair_color", "brown")
    eye_color = character_bible.get("eye_color", "brown")
    
    prompt = f"""
{PIXAR_STYLE_PROMPT_PREFIX}
cinematic scene from a Pixar animated movie,
{scene_description},
featuring an adorable {age}-year-old child character named {child_name},
{skin_tone} skin, {hair_color} hair, big {eye_color} eyes,
{character_action},
{theme_settings['environment']},
{theme_settings['lighting']},
mood: {mood}, warm and inviting atmosphere,
movie poster composition, rule of thirds,
vibrant {', '.join(theme_settings['mood_colors'][:2])} color scheme,
Pixar movie quality, Disney animation excellence,
ultra detailed background, 8k resolution
""".strip().replace("\n", " ")
    
    return prompt


def _build_pixar_cover_prompt(
    child_name: str,
    character_bible: Dict[str, Any],
    theme: str,
    title: str
) -> str:
    """
    Build a Pixar/Disney style book cover prompt.
    
    Args:
        child_name: Child's name
        character_bible: Character description dict
        theme: Story theme
        title: Book title
        
    Returns:
        Formatted prompt for cover generation
    """
    theme_settings = THEME_SCENE_SETTINGS.get(theme, THEME_SCENE_SETTINGS["forest"])
    
    gender = character_bible.get("gender", "child")
    age = character_bible.get("age", 7)
    skin_tone = character_bible.get("skin_tone", "light")
    hair_color = character_bible.get("hair_color", "brown")
    eye_color = character_bible.get("eye_color", "brown")
    
    prompt = f"""
{PIXAR_STYLE_PROMPT_PREFIX}
children's book cover illustration, Pixar movie poster style,
heroic portrait of an adorable {age}-year-old child named {child_name},
{skin_tone} skin, {hair_color} hair, big sparkling {eye_color} eyes,
excited confident expression, hands on hips superhero pose,
{theme_settings['environment']},
{theme_settings['lighting']},
dramatic composition, looking at viewer,
vibrant saturated colors, magical sparkles and particles,
space for title text at top,
Disney Pixar movie quality, ultra polished,
professional children's book cover, 8k resolution
""".strip().replace("\n", " ")
    
    return prompt


def _build_pixar_portrait_prompt(
    child_name: str,
    character_bible: Dict[str, Any]
) -> str:
    """
    Build a Pixar/Disney style hero portrait prompt.
    
    Args:
        child_name: Child's name
        character_bible: Character description dict
        
    Returns:
        Formatted prompt for portrait generation
    """
    gender = character_bible.get("gender", "child")
    age = character_bible.get("age", 7)
    skin_tone = character_bible.get("skin_tone", "light")
    hair_color = character_bible.get("hair_color", "brown")
    hair_style = character_bible.get("hair_style", "short neat")
    eye_color = character_bible.get("eye_color", "brown")
    
    prompt = f"""
{PIXAR_STYLE_PROMPT_PREFIX}
close-up character portrait, Pixar animation style,
adorable {age}-year-old child named {child_name},
{skin_tone} skin with subtle subsurface scattering,
{hair_color} {hair_style} hair with individual strand detail,
huge expressive {eye_color} eyes with beautiful catchlights,
cute button nose, rosy cheeks, warm genuine smile,
soft studio lighting, gradient background,
head and shoulders shot, slight head tilt,
Disney character design, Pixar render quality,
ultra detailed, 8k resolution, masterpiece
""".strip().replace("\n", " ")
    
    return prompt


# ═══════════════════════════════════════════════════════════════════════════════
# PREVIEW SERVICE CLASS
# ═══════════════════════════════════════════════════════════════════════════════

class PreviewService:
    """
    Service for fast preview generation with Pixar/Disney 3D style.

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
        Generate a quick preview in under 60 seconds with Pixar/Disney 3D style.

        Args:
            child_name: Child's name
            child_gender: One of: boy, girl, they
            age_band: One of: 3-5, 6-8, 9-12
            theme: One of: space, dinosaur, ocean, forest, superhero
            photo_url: Optional photo URL for initial likeness
            session_id: Session tracking ID

        Returns:
            Dict with preview data including Pixar-style images

        Raises:
            ValidationException: Invalid input
            ExternalServiceException: AI service error
        """
        start_time = time.time()
        logger.info(f"Starting Pixar-style preview for {child_name}, theme: {theme}")

        try:
            # Convert inputs to internal format
            child_age = _age_band_to_age(age_band)
            gender_enum = _gender_to_enum(child_gender)
            default_attrs = _get_default_character_attributes(age_band, child_gender)

            # 1. Create character profile (optimized for Pixar style)
            character_bible = {
                "name": child_name,
                "gender": child_gender,
                "age": child_age,
                "skin_tone": str(default_attrs["skin_tone"].value),
                "hair_color": str(default_attrs["hair_color"].value),
                "hair_style": str(default_attrs["hair_style"].value),
                "eye_color": str(default_attrs["eye_color"].value),
                "body_type": str(default_attrs["body_type"].value),
                "photo_reference": photo_url,
                "theme": theme,
                "art_style": PIXAR_ART_STYLE
            }

            # 2. Generate a SHORT story (just 2 pages for preview)
            story_pages = await self.story_generator.generate_preview_story(
                character_bible=character_bible,
                child_name=child_name,
                age=child_age,
                theme=theme,
                num_pages=2
            )

            # 3. Build Pixar-style prompts
            title = f"{child_name}'s {theme.title()} Adventure"
            
            cover_prompt = _build_pixar_cover_prompt(
                child_name=child_name,
                character_bible=character_bible,
                theme=theme,
                title=title
            )
            
            portrait_prompt = _build_pixar_portrait_prompt(
                child_name=child_name,
                character_bible=character_bible
            )
            
            page1_prompt = _build_pixar_scene_prompt(
                child_name=child_name,
                character_bible=character_bible,
                theme=theme,
                scene_description=story_pages[0].get('scene_description', 'starting an adventure'),
                character_action=story_pages[0].get('character_action', 'looking excited'),
                mood=story_pages[0].get('mood', 'happy')
            )
            
            page2_prompt = _build_pixar_scene_prompt(
                child_name=child_name,
                character_bible=character_bible,
                theme=theme,
                scene_description=story_pages[1].get('scene_description', 'discovering something amazing'),
                character_action=story_pages[1].get('character_action', 'pointing with wonder'),
                mood=story_pages[1].get('mood', 'excited')
            )

            # 4. Generate images in parallel for speed
            tasks = [
                # Cover image
                self.image_generator.generate_with_prompt(
                    prompt=cover_prompt,
                    negative_prompt=PIXAR_STYLE_NEGATIVE_PROMPT,
                    width=1024,
                    height=1024,
                    quality=GenerationQuality.PREVIEW
                ),
                # Hero portrait
                self.image_generator.generate_with_prompt(
                    prompt=portrait_prompt,
                    negative_prompt=PIXAR_STYLE_NEGATIVE_PROMPT,
                    width=1024,
                    height=1024,
                    quality=GenerationQuality.PREVIEW
                ),
                # Page 1 illustration
                self.image_generator.generate_with_prompt(
                    prompt=page1_prompt,
                    negative_prompt=PIXAR_STYLE_NEGATIVE_PROMPT,
                    width=1024,
                    height=1024,
                    quality=GenerationQuality.PREVIEW
                ),
                # Page 2 illustration
                self.image_generator.generate_with_prompt(
                    prompt=page2_prompt,
                    negative_prompt=PIXAR_STYLE_NEGATIVE_PROMPT,
                    width=1024,
                    height=1024,
                    quality=GenerationQuality.PREVIEW
                )
            ]

            # Run all image generation in parallel
            logger.info("Starting parallel Pixar-style image generation...")
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Check for errors
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Image generation failed for task {i}: {result}")
                    raise ExternalServiceException(
                        service_name="Image Generator",
                        message=f"Pixar-style image generation failed: {str(result)}",
                        is_transient=True
                    )

            cover_img, hero_img, page1_img, page2_img = results

            # 5. Store preview session
            preview_id = str(uuid.uuid4())
            preview_data = {
                "preview_id": preview_id,
                "session_id": session_id,
                "child_name": child_name,
                "child_gender": child_gender,
                "age_band": age_band,
                "theme": theme,
                "character_bible": character_bible,
                "story_pages": story_pages,
                "cover_url": cover_img.get('url', ''),
                "cover_prompt": cover_prompt,
                "hero_url": hero_img.get('url', ''),
                "hero_prompt": portrait_prompt,
                "is_placeholder": photo_url is None,
                "page1_url": page1_img.get('url', ''),
                "page1_prompt": page1_prompt,
                "page1_text": story_pages[0].get('text', ''),
                "page2_url": page2_img.get('url', ''),
                "page2_prompt": page2_prompt,
                "page2_text": story_pages[1].get('text', ''),
                "art_style": PIXAR_ART_STYLE,
                "created_at": datetime.utcnow().isoformat(),
                "expires_at": (datetime.utcnow() + timedelta(hours=1)).isoformat()
            }

            PREVIEW_SESSIONS[preview_id] = preview_data

            # 6. Calculate total time
            generation_time_ms = int((time.time() - start_time) * 1000)
            logger.info(f"Pixar-style preview generated in {generation_time_ms}ms")

            # 7. Build response
            return {
                "preview_id": preview_id,
                "title": title,
                "cover": {
                    "image_url": cover_img.get('url', ''),
                    "prompt_used": cover_prompt
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
                    "model_version": "v2.1-pixar",
                    "art_style": "Pixar/Disney 3D Animation"
                }
            }

        except Exception as e:
            logger.error(f"Pixar-style preview generation failed: {e}")
            raise ExternalServiceException(
                service_name="Preview Service",
                message=f"Failed to generate Pixar-style preview: {str(e)}",
                is_transient=False
            )

    async def regenerate_preview(
        self,
        preview_id: str,
        character_reference_url: Optional[str],
        tweaks: Optional[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        Regenerate preview with user tweaks in Pixar/Disney style.

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
        logger.info(f"Regenerating Pixar-style preview {preview_id} with tweaks: {tweaks}")

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
            # Apply tweaks
            character_bible = session["character_bible"].copy()
            story_pages = session["story_pages"].copy()
            theme = session["theme"]
            child_name = session["child_name"]

            # Apply tone tweak to story mood
            mood_modifier = ""
            if tweaks and "tone" in tweaks:
                tone = tweaks["tone"]
                if tone == "funny":
                    mood_modifier = "silly and playful, comic expression"
                    for page in story_pages:
                        page["mood"] = "playful"
                elif tone == "gentle":
                    mood_modifier = "calm and peaceful, serene expression"
                    for page in story_pages:
                        page["mood"] = "calm"
                elif tone == "adventurous":
                    mood_modifier = "brave and excited, determined expression"
                    for page in story_pages:
                        page["mood"] = "excited"

            # Apply sidekick tweak
            sidekick_prompt = ""
            if tweaks and "sidekick" in tweaks and tweaks["sidekick"] != "none":
                sidekick = tweaks["sidekick"]
                sidekick_prompts = {
                    "puppy": "with an adorable Pixar-style puppy companion with big eyes",
                    "kitten": "with a cute fluffy Pixar-style kitten friend",
                    "dragon": "with a small friendly baby dragon companion with colorful scales",
                    "robot": "with a cute round Pixar-style robot buddy with expressive eyes"
                }
                sidekick_prompt = sidekick_prompts.get(sidekick, "")

            # Build regeneration prompts
            page1_prompt = _build_pixar_scene_prompt(
                child_name=child_name,
                character_bible=character_bible,
                theme=theme,
                scene_description=story_pages[0].get('scene_description', ''),
                character_action=story_pages[0].get('character_action', ''),
                mood=story_pages[0].get('mood', 'happy')
            )
            if mood_modifier:
                page1_prompt += f", {mood_modifier}"
            if sidekick_prompt:
                page1_prompt += f", {sidekick_prompt}"

            page2_prompt = _build_pixar_scene_prompt(
                child_name=child_name,
                character_bible=character_bible,
                theme=theme,
                scene_description=story_pages[1].get('scene_description', ''),
                character_action=story_pages[1].get('character_action', ''),
                mood=story_pages[1].get('mood', 'happy')
            )
            if mood_modifier:
                page2_prompt += f", {mood_modifier}"
            if sidekick_prompt:
                page2_prompt += f", {sidekick_prompt}"

            # Regenerate images in parallel
            tasks = [
                self.image_generator.generate_with_prompt(
                    prompt=page1_prompt,
                    negative_prompt=PIXAR_STYLE_NEGATIVE_PROMPT,
                    width=1024,
                    height=1024,
                    quality=GenerationQuality.PREVIEW
                ),
                self.image_generator.generate_with_prompt(
                    prompt=page2_prompt,
                    negative_prompt=PIXAR_STYLE_NEGATIVE_PROMPT,
                    width=1024,
                    height=1024,
                    quality=GenerationQuality.PREVIEW
                )
            ]

            # Optionally regenerate hero portrait with reference
            if character_reference_url:
                portrait_prompt = _build_pixar_portrait_prompt(
                    child_name=child_name,
                    character_bible=character_bible
                )
                tasks.append(
                    self.image_generator.generate_with_reference(
                        prompt=portrait_prompt,
                        reference_url=character_reference_url,
                        negative_prompt=PIXAR_STYLE_NEGATIVE_PROMPT,
                        width=1024,
                        height=1024,
                        quality=GenerationQuality.PREVIEW
                    )
                )

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Check for errors
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Regeneration failed for task {i}: {result}")
                    raise ExternalServiceException(
                        service_name="Image Generator",
                        message=f"Pixar-style regeneration failed: {str(result)}",
                        is_transient=True
                    )

            page1_img = results[0]
            page2_img = results[1]
            
            # Update session
            session["page1_url"] = page1_img.get('url', '')
            session["page1_prompt"] = page1_prompt
            session["page2_url"] = page2_img.get('url', '')
            session["page2_prompt"] = page2_prompt
            session["story_pages"] = story_pages

            # Update hero if regenerated
            hero_updated = False
            if len(results) > 2:
                hero_img = results[2]
                session["hero_url"] = hero_img.get('url', '')
                session["is_placeholder"] = False
                hero_updated = True

            generation_time_ms = int((time.time() - start_time) * 1000)
            logger.info(f"Pixar-style preview regenerated in {generation_time_ms}ms")

            return {
                "preview_id": preview_id,
                "hero_portrait": {
                    "image_url": session["hero_url"],
                    "updated": hero_updated
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
                    "tweaks_applied": tweaks or {},
                    "art_style": "Pixar/Disney 3D Animation"
                }
            }

        except ValidationException:
            raise
        except Exception as e:
            logger.error(f"Pixar-style preview regeneration failed: {e}")
            raise ExternalServiceException(
                service_name="Preview Service",
                message=f"Failed to regenerate Pixar-style preview: {str(e)}",
                is_transient=False
            )

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

    async def extend_preview_to_book(
        self,
        preview_id: str,
        photo_url: Optional[str] = None,
        regenerate_story: bool = False,
        target_pages: int = 10,
        occasion: Optional[str] = None,
        special_details: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extend a 2-page preview to a full 10-page book.

        This method:
        1. Retrieves the preview session data
        2. Either continues the existing story OR regenerates a full story
        3. Generates high-quality images for all pages
        4. Returns the complete book data

        Args:
            preview_id: The preview session ID
            photo_url: Optional photo URL for better hero portrait
            regenerate_story: If True, generate new 10-page story; if False, continue from preview
            target_pages: Total pages for the book (default: 10)
            occasion: Special occasion for the book
            special_details: Additional story details

        Returns:
            Dict with complete book data including all pages

        Raises:
            ValidationException: If preview not found or expired
            ExternalServiceException: If generation fails
        """
        start_time = time.time()

        # 1. Get preview session
        session = self.get_preview_session(preview_id)
        if not session:
            raise ValidationException("Preview not found or expired")

        logger.info(f"Extending preview {preview_id} to {target_pages}-page book (regenerate_story={regenerate_story})")

        try:
            # 2. Extract preview data
            character_bible = session["character_bible"]
            existing_pages = session["story_pages"]
            theme = session["theme"]
            child_name = session["child_name"]
            child_gender = session["child_gender"]
            age_band = session["age_band"]
            child_age = _age_band_to_age(age_band)

            title = f"{child_name}'s {theme.title()} Adventure"

            # 3. Generate story (continue or regenerate)
            if regenerate_story:
                # Generate entirely new 10-page story
                logger.info("Generating fresh 10-page story")
                all_story_pages = await self.story_generator.generate_story(
                    character_bible=character_bible,
                    child_name=child_name,
                    age=child_age,
                    theme=theme,
                    occasion=occasion,
                    special_details=special_details,
                    num_pages=target_pages
                )
            else:
                # Continue from existing preview pages
                logger.info(f"Continuing story from {len(existing_pages)} preview pages")
                continuation_pages = await self.story_generator.continue_story(
                    character_bible=character_bible,
                    child_name=child_name,
                    age=child_age,
                    theme=theme,
                    existing_pages=existing_pages,
                    target_total_pages=target_pages,
                    occasion=occasion,
                    special_details=special_details
                )
                # Combine preview pages + new pages
                all_story_pages = existing_pages + continuation_pages

            logger.info(f"Full story ready: {len(all_story_pages)} pages")

            # 4. Build prompts for all pages
            cover_prompt = _build_pixar_cover_prompt(
                child_name=child_name,
                character_bible=character_bible,
                theme=theme,
                title=title
            )

            # 5. Generate all images in parallel (high quality for final book)
            image_tasks = []

            # Cover
            image_tasks.append(
                self.image_generator.generate_with_prompt(
                    prompt=cover_prompt,
                    negative_prompt=PIXAR_STYLE_NEGATIVE_PROMPT,
                    width=2048,  # High res for print
                    height=2048,
                    quality=GenerationQuality.PRINT,
                    page_number=0
                )
            )

            # Hero portrait (with photo if provided)
            if photo_url:
                portrait_prompt = _build_pixar_portrait_prompt(
                    child_name=child_name,
                    character_bible=character_bible
                )
                image_tasks.append(
                    self.image_generator.generate_with_prompt(
                        prompt=f"photo reference style. {portrait_prompt}",
                        negative_prompt=PIXAR_STYLE_NEGATIVE_PROMPT,
                        width=2048,
                        height=2048,
                        quality=GenerationQuality.PRINT,
                        page_number=0
                    )
                )
            else:
                portrait_prompt = _build_pixar_portrait_prompt(
                    child_name=child_name,
                    character_bible=character_bible
                )
                image_tasks.append(
                    self.image_generator.generate_with_prompt(
                        prompt=portrait_prompt,
                        negative_prompt=PIXAR_STYLE_NEGATIVE_PROMPT,
                        width=2048,
                        height=2048,
                        quality=GenerationQuality.PRINT,
                        page_number=0
                    )
                )

            # All story pages
            for page in all_story_pages:
                page_prompt = _build_pixar_scene_prompt(
                    child_name=child_name,
                    character_bible=character_bible,
                    theme=theme,
                    scene_description=page.get('scene_description', ''),
                    character_action=page.get('character_action', ''),
                    mood=page.get('mood', 'happy')
                )
                image_tasks.append(
                    self.image_generator.generate_with_prompt(
                        prompt=page_prompt,
                        negative_prompt=PIXAR_STYLE_NEGATIVE_PROMPT,
                        width=2048,
                        height=2048,
                        quality=GenerationQuality.PRINT,
                        page_number=page['page_number']
                    )
                )

            # Generate all images in parallel
            logger.info(f"Starting parallel high-quality image generation for {len(image_tasks)} images...")
            results = await asyncio.gather(*image_tasks, return_exceptions=True)

            # Check for errors
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Image generation failed for image {i}: {result}")
                    raise ExternalServiceException(
                        service_name="Image Generator",
                        message=f"Image generation failed: {str(result)}",
                        is_transient=True
                    )

            cover_img = results[0]
            hero_img = results[1]
            page_images = results[2:]

            # 6. Build complete book data
            book_pages = []
            for i, page in enumerate(all_story_pages):
                book_pages.append({
                    "page_number": page['page_number'],
                    "text": page['text'],
                    "image_url": page_images[i].get('url', ''),
                    "scene_description": page.get('scene_description', ''),
                    "character_action": page.get('character_action', ''),
                    "mood": page.get('mood', 'happy')
                })

            generation_time_ms = int((time.time() - start_time) * 1000)
            logger.info(f"Extended preview to full book in {generation_time_ms}ms")

            return {
                "preview_id": preview_id,
                "book_id": str(uuid.uuid4())[:8],  # Generate new book ID
                "title": title,
                "child_name": child_name,
                "theme": theme,
                "cover_url": cover_img.get('url', ''),
                "hero_portrait_url": hero_img.get('url', ''),
                "pages": book_pages,
                "total_pages": len(book_pages),
                "character_bible": character_bible,
                "art_style": PIXAR_ART_STYLE,
                "generation_time_ms": generation_time_ms,
                "was_continued": not regenerate_story
            }

        except ExternalServiceException:
            raise
        except Exception as e:
            logger.error(f"Failed to extend preview to book: {e}")
            raise ExternalServiceException(
                service_name="Preview Service",
                message=f"Failed to extend preview to book: {str(e)}",
                is_transient=False
            )


# ═══════════════════════════════════════════════════════════════════════════════
# THEME PROMPTS FOR STORY GENERATION
# ═══════════════════════════════════════════════════════════════════════════════

THEME_STORY_STARTERS = {
    "space": {
        "opening": "zooms through the stars in a shiny rocket ship",
        "discovery": "meets a friendly purple alien who waves hello",
        "adventure": "explores a planet made of rainbow crystals",
        "triumph": "saves the day and becomes a Space Hero"
    },
    "dinosaur": {
        "opening": "discovers a magical door that leads to dinosaur times",
        "discovery": "makes friends with a gentle giant dinosaur",
        "adventure": "rides on the dinosaur's back through the jungle",
        "triumph": "helps the dinosaurs and earns a special dino badge"
    },
    "ocean": {
        "opening": "dives into a magical underwater kingdom",
        "discovery": "meets a wise sea turtle with a treasure map",
        "adventure": "swims through a coral castle full of friendly fish",
        "triumph": "finds the legendary pearl and becomes Ocean Champion"
    },
    "forest": {
        "opening": "finds a secret path into an enchanted forest",
        "discovery": "meets talking woodland animals who need help",
        "adventure": "follows a trail of glowing mushrooms to a fairy village",
        "triumph": "breaks the spell and becomes Friend of the Forest"
    },
    "superhero": {
        "opening": "discovers a magical cape that grants superpowers",
        "discovery": "learns to fly and zoom through the clouds",
        "adventure": "rescues a kitten stuck in a very tall tree",
        "triumph": "saves the city and becomes the town's favorite hero"
    }
}