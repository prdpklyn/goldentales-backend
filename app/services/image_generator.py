# app/services/image_generator.py
"""
GoldenTales Image Generator
===========================
Generates illustrations using Fal.ai with character consistency.
"""

import os
import asyncio
from typing import List, Dict, Optional, Any

from app.settings import settings
from app.models.enums import GenerationQuality, BookTier
from app.utils.logging import get_logger
from app.utils.security import SAFETY_NEGATIVE_PROMPT, ANATOMICAL_POSITIVE_GUIDANCE
from app.utils.retry import with_retry
from app.utils.exceptions import ExternalServiceException
from character_system import CharacterDescriptionGenerator

logger = get_logger(__name__)


class ImageGenerator:
    """
    Service for generating illustrations using Fal.ai.
    
    Supports multiple quality tiers:
    - PREVIEW: Fast generation for user approval
    - STANDARD: Balanced quality 
    - PRINT: High resolution for printing
    
    Example:
        generator = ImageGenerator()
        result = await generator.generate_illustration(
            character_bible={"main_character": "Emma..."},
            scene_description="Emma in a magical forest",
            art_style="watercolor",
            page_number=1
        )
    """
    
    # Model configurations by quality tier - BASIC tier
    MODEL_CONFIGS = {
        GenerationQuality.PREVIEW: {
            "model": "fal-ai/flux/schnell",
            "image_size": "landscape_4_3",
            "num_inference_steps": 4,
        },
        GenerationQuality.STANDARD: {
            "model": "fal-ai/flux-pro",
            "image_size": "landscape_4_3",
            "guidance_scale": 7.5,
        },
        GenerationQuality.PRINT: {
            "model": "fal-ai/flux-pro/v1.1",
            "image_size": {"width": 2400, "height": 1800},
            "guidance_scale": 7.5,
        }
    }
    
    # Model configurations for PREMIUM/ULTRA tiers (full-page spreads)
    MODEL_CONFIGS_PREMIUM = {
        GenerationQuality.PREVIEW: {
            "model": "fal-ai/flux/schnell",
            "image_size": {"width": 2048, "height": 1024},  # Wide for spread
            "num_inference_steps": 4,
        },
        GenerationQuality.STANDARD: {
            "model": "fal-ai/flux-pro",
            "image_size": {"width": 2048, "height": 1024},
            "guidance_scale": 7.5,
        },
        GenerationQuality.PRINT: {
            "model": "fal-ai/flux-pro/v1.1",
            "image_size": {"width": 3072, "height": 1536},  # High-res spread
            "guidance_scale": 7.5,
        }
    }
    
    # Full-page composition instructions for Premium/Ultra tiers
    FULL_PAGE_COMPOSITION = """
COMPOSITION FOR FULL-PAGE LAYOUT:
- Leave clear space at TOP (15%) for text overlay
- Leave clear space at BOTTOM (20%) for paragraph text  
- Main action should be in CENTER of image
- Include areas with simple/solid backgrounds for text readability
- Full bleed illustration across the entire spread
- Avoid important details at edges (they may be cropped)
"""
    
    # Style descriptions for prompts
    STYLE_DESCRIPTIONS = {
        "watercolor": "soft watercolor illustration style, gentle flowing colors, dreamy brushstrokes",
        "cartoon": "vibrant cartoon illustration, bold outlines, bright cheerful colors, Pixar-inspired",
        "anime": "anime/manga illustration style, expressive features, soft shading, Studio Ghibli inspired",
        "storybook": "classic children's book illustration, warm nostalgic colors, golden age storybook art",
        "pixar": "3D animated style illustration, Pixar-quality, soft lighting, expressive characters",
        "ghibli": "Studio Ghibli style, hand-painted aesthetic, detailed backgrounds, magical atmosphere"
    }
    
    # Mood lighting descriptions
    MOOD_LIGHTING = {
        "happy": "warm golden lighting, bright and cheerful atmosphere",
        "excited": "dynamic lighting, energetic sparkles, vibrant scene",
        "curious": "soft mysterious lighting, sense of wonder",
        "brave": "dramatic heroic lighting, bold atmosphere",
        "peaceful": "soft diffused lighting, calm serene atmosphere",
        "magical": "ethereal glowing light, sparkles and magic particles",
        "cozy": "warm indoor lighting, comfortable inviting atmosphere"
    }
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the image generator.
        
        Args:
            api_key: Fal.ai API key. Defaults to settings.
        """
        self.api_key = api_key or settings.fal_key
        if self.api_key:
            os.environ["FAL_KEY"] = self.api_key
        else:
            logger.warning("Fal.ai API key not configured")
        
        self.description_generator = CharacterDescriptionGenerator()
    
    @with_retry(
        max_attempts=3,
        initial_delay=2.0,
        max_delay=30.0,
        circuit_breaker_name="fal_ai"
    )
    async def _call_fal_ai_with_retry(
        self,
        model: str,
        params: Dict[str, Any],
        page_number: int
    ) -> Dict[str, Any]:
        """
        Call Fal.ai API with automatic retry logic.
        
        This is wrapped with @with_retry decorator for:
        - Exponential backoff on transient failures
        - Circuit breaker to prevent cascade failures
        - Automatic retry on rate limits and server errors
        """
        import fal_client
        
        try:
            handler = await fal_client.submit_async(model, arguments=params)
            result = await handler.get()
            return result
        except Exception as e:
            # Convert to a more specific exception
            error_msg = str(e).lower()
            is_transient = any(
                pattern in error_msg
                for pattern in ['timeout', 'rate limit', 'unavailable', '429', '503']
            )
            
            raise ExternalServiceException(
                service_name="Fal.ai",
                message=str(e),
                is_transient=is_transient
            )
    
    async def generate_illustration(
        self,
        character_bible: Dict[str, str],
        scene_description: str,
        character_action: str,
        mood: str,
        art_style: str,
        page_number: int,
        characters_in_scene: Optional[List[str]] = None,
        art_modifier: str = "",
        quality: GenerationQuality = GenerationQuality.PREVIEW
    ) -> Dict[str, Any]:
        """
        Generate a single illustration with character consistency.

        The character bible is included in EVERY prompt to ensure
        the character looks the same across all pages.

        Args:
            character_bible: Character description dictionary
            scene_description: Description of the scene
            character_action: What the character is doing
            mood: Emotional mood of the scene
            art_style: Art style to use
            page_number: Page number (used for seed consistency)
            characters_in_scene: Names of additional characters
            art_modifier: Optional modifier (softer/brighter/detailed)
            quality: Generation quality tier

        Returns:
            Dictionary with url, quality, page_number, and cost
        """
        import fal_client
        
        if not self.api_key:
            raise ValueError("Fal.ai API key not configured")
        
        # Build the complete prompt using character description generator
        full_prompt = self.description_generator.build_page_prompt(
            character_bible=character_bible,
            scene_description=scene_description,
            character_action=character_action,
            mood=mood,
            art_style=art_style,
            page_number=page_number,
            include_additional_characters=characters_in_scene
        )
        
        # Add quality, consistency, and anatomical correctness instructions
        full_prompt += f"""

CRITICAL CONSISTENCY RULES:
- Character's face, hair, skin tone, and features must match the description EXACTLY
- Same character design as all other pages in this book
- Maintain exact hair color, style, and length
- Keep any accessories (glasses, bows, etc.) consistent
- Same clothing style/colors throughout

ANATOMICAL REQUIREMENTS (VERY IMPORTANT):
- Character must have exactly TWO hands with FIVE fingers each
- Character must have exactly ONE head, properly connected to body
- Natural, relaxed pose with correct body proportions
- Arms and hands must be clearly connected to body
- No floating or disconnected body parts
- Proper perspective and foreshortening

COMPOSITION:
- Single clear focal point on the main character
- Character fully visible in frame (not cropped awkwardly)
- {ANATOMICAL_POSITIVE_GUIDANCE}

OUTPUT: High-quality children's book illustration, professional, vibrant, safe for all ages.
"""

        # Apply art modifier if provided
        if art_modifier:
            modifier_text = ""
            if art_modifier == "softer":
                modifier_text = "STYLE MODIFIER: Softer edges, gentler colors, dreamy atmosphere"
            elif art_modifier == "brighter":
                modifier_text = "STYLE MODIFIER: Brighter colors, more vibrant, cheerful tones"
            elif art_modifier == "detailed":
                modifier_text = "STYLE MODIFIER: More detailed textures, richer elements, intricate details"

            if modifier_text:
                full_prompt += f"\n\n{modifier_text}\n"

        # Get model config for quality tier
        config = self.MODEL_CONFIGS[quality]
        model = config["model"]
        
        # Build params
        params = {
            "prompt": full_prompt,
            "num_images": 1,
            "enable_safety_checker": True,
            "seed": 42 + page_number,  # Consistent seed per page
        }
        
        # Add quality-specific params
        if "image_size" in config:
            params["image_size"] = config["image_size"]
        if "num_inference_steps" in config:
            params["num_inference_steps"] = config["num_inference_steps"]
        if "guidance_scale" in config:
            params["guidance_scale"] = config["guidance_scale"]
        
        # ALWAYS add negative prompt to prevent anatomical issues (extra hands, etc.)
        # This is critical for all quality levels including preview
        params["negative_prompt"] = SAFETY_NEGATIVE_PROMPT
        
        try:
            logger.info(f"Generating page {page_number} with {quality.value} quality")
            
            #  Call Fal.ai with retry logic
            result = await self._call_fal_ai_with_retry(model, params, page_number)
            
            cost = getattr(settings, f"cost_{quality.value}", 0.02)
            
            return {
                "url": result['images'][0]['url'],
                "quality": quality.value,
                "page_number": page_number,
                "cost": cost
            }
            
        except Exception as e:
            logger.error(f"Image generation failed for page {page_number}: {e}")
            raise ExternalServiceException(
                service_name="Fal.ai",
                message=f"Image generation failed for page {page_number}: {str(e)}",
                is_transient=True
            )
    
    async def generate_all_illustrations(
        self,
        character_bible: Dict[str, str],
        story_pages: List[Dict],
        art_style: str,
        quality: GenerationQuality = GenerationQuality.PREVIEW,
        batch_size: int = 3
    ) -> List[Dict]:
        """
        Generate illustrations for all story pages.
        
        Args:
            character_bible: Character description dictionary
            story_pages: List of story page dictionaries
            art_style: Art style to use
            quality: Generation quality tier
            batch_size: Number of concurrent generations
            
        Returns:
            List of illustration result dictionaries
        """
        illustrations = []
        
        for i in range(0, len(story_pages), batch_size):
            batch = story_pages[i:i + batch_size]
            
            tasks = [
                self.generate_illustration(
                    character_bible=character_bible,
                    scene_description=page.get('scene_description', ''),
                    character_action=page.get('character_action', ''),
                    mood=page.get('mood', 'happy'),
                    art_style=art_style,
                    page_number=page.get('page_number', i + idx + 1),
                    characters_in_scene=page.get('characters_in_scene', []),
                    quality=quality
                )
                for idx, page in enumerate(batch)
            ]
            
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"Batch image generation failed: {result}")
                    illustrations.append({
                        "url": "https://placehold.co/800x600/amber/white?text=Regenerate",
                        "error": str(result)
                    })
                else:
                    illustrations.append(result)
            
            # Small delay between batches to avoid rate limiting
            if i + batch_size < len(story_pages):
                await asyncio.sleep(0.5)
        
        logger.info(f"Generated {len(illustrations)} illustrations")
        return illustrations
    
    # ============================================
    # PREMIUM/ULTRA TIER FEATURES
    # ============================================
    
    async def generate_illustration_premium(
        self,
        character_bible: Dict[str, str],
        scene_description: str,
        character_action: str,
        mood: str,
        art_style: str,
        page_number: int,
        tier: BookTier,
        character_reference_url: Optional[str] = None,
        characters_in_scene: Optional[List[str]] = None,
        quality: GenerationQuality = GenerationQuality.PREVIEW
    ) -> Dict[str, Any]:
        """
        Generate illustration with premium features.
        
        Premium features:
        - Full-page composition with text-safe zones
        - Wider aspect ratio for spreads
        
        Ultra features (if character_reference_url provided):
        - IP-Adapter for character consistency from photo
        
        Args:
            character_bible: Character description dictionary
            scene_description: Description of the scene
            character_action: What the character is doing
            mood: Emotional mood of the scene
            art_style: Art style to use
            page_number: Page number (used for seed consistency)
            tier: Book tier (PREMIUM or ULTRA)
            character_reference_url: URL of transformed character image (for ULTRA)
            characters_in_scene: Names of additional characters
            quality: Generation quality tier
            
        Returns:
            Dictionary with url, quality, page_number, and cost
        """
        if not self.api_key:
            raise ValueError("Fal.ai API key not configured")
        
        # Build the complete prompt
        full_prompt = self.description_generator.build_page_prompt(
            character_bible=character_bible,
            scene_description=scene_description,
            character_action=character_action,
            mood=mood,
            art_style=art_style,
            page_number=page_number,
            include_additional_characters=characters_in_scene
        )
        
        # Add premium composition instructions
        if tier in [BookTier.PREMIUM, BookTier.ULTRA]:
            full_prompt += f"\n\n{self.FULL_PAGE_COMPOSITION}"
        
        # Add consistency rules and anatomical guidance
        full_prompt += f"""

CRITICAL CONSISTENCY RULES:
- Character's face, hair, skin tone, and features must match the description EXACTLY
- Same character design as all other pages in this book
- Maintain exact hair color, style, and length
- Keep any accessories (glasses, bows, etc.) consistent
- Same clothing style/colors throughout

ANATOMICAL REQUIREMENTS (VERY IMPORTANT):
- Character must have exactly TWO hands with FIVE fingers each
- Character must have exactly ONE head, properly connected to body
- Natural, relaxed pose with correct body proportions
- Arms and hands must be clearly connected to body
- No floating or disconnected body parts
- Proper perspective and foreshortening

COMPOSITION:
- Single clear focal point on the main character
- Character fully visible in frame (not cropped awkwardly)
- {ANATOMICAL_POSITIVE_GUIDANCE}

OUTPUT: High-quality children's book illustration, professional, vibrant, safe for all ages.
"""
        
        # Get premium model config
        config = self.MODEL_CONFIGS_PREMIUM.get(
            quality,
            self.MODEL_CONFIGS[quality]  # Fallback to standard
        )
        model = config["model"]
        
        # Build params
        params = {
            "prompt": full_prompt,
            "num_images": 1,
            "enable_safety_checker": True,
            "seed": 42 + page_number,
        }
        
        # Add quality-specific params
        if "image_size" in config:
            params["image_size"] = config["image_size"]
        if "num_inference_steps" in config:
            params["num_inference_steps"] = config["num_inference_steps"]
        if "guidance_scale" in config:
            params["guidance_scale"] = config["guidance_scale"]
        
        # Add IP-Adapter for ULTRA tier with character reference
        if tier == BookTier.ULTRA and character_reference_url:
            params["ip_adapter_image_url"] = character_reference_url
            params["ip_adapter_scale"] = 0.7  # Strong influence from reference
        
        # ALWAYS add negative prompt to prevent anatomical issues (extra hands, etc.)
        # This is critical for all quality levels including preview
        params["negative_prompt"] = SAFETY_NEGATIVE_PROMPT
        
        try:
            logger.info(f"Generating {tier.value} tier page {page_number} with {quality.value} quality")
            
            result = await self._call_fal_ai_with_retry(model, params, page_number)
            
            # Calculate cost based on tier
            if tier == BookTier.ULTRA:
                cost = getattr(settings, f"cost_{quality.value}", 0.02) + 0.03  # Extra for IP-Adapter
            elif tier == BookTier.PREMIUM:
                cost = getattr(settings, f"cost_{quality.value}", 0.02) + 0.01  # Extra for premium composition
            else:
                cost = getattr(settings, f"cost_{quality.value}", 0.02)
            
            return {
                "url": result['images'][0]['url'],
                "quality": quality.value,
                "tier": tier.value,
                "page_number": page_number,
                "cost": cost
            }
            
        except Exception as e:
            logger.error(f"Premium image generation failed for page {page_number}: {e}")
            raise ExternalServiceException(
                service_name="Fal.ai",
                message=f"Image generation failed for page {page_number}: {str(e)}",
                is_transient=True
            )
    
    async def generate_all_illustrations_with_tier(
        self,
        character_bible: Dict[str, str],
        story_pages: List[Dict],
        art_style: str,
        tier: BookTier = BookTier.BASIC,
        character_reference_url: Optional[str] = None,
        quality: GenerationQuality = GenerationQuality.PREVIEW,
        batch_size: int = 3
    ) -> List[Dict]:
        """
        Generate illustrations for all story pages with tier support.
        
        Args:
            character_bible: Character description dictionary
            story_pages: List of story page dictionaries
            art_style: Art style to use
            tier: Book tier (BASIC, PREMIUM, or ULTRA)
            character_reference_url: Transformed character image (for ULTRA)
            quality: Generation quality tier
            batch_size: Number of concurrent generations
            
        Returns:
            List of illustration result dictionaries
        """
        illustrations = []
        
        for i in range(0, len(story_pages), batch_size):
            batch = story_pages[i:i + batch_size]
            
            # Use premium generation for PREMIUM and ULTRA tiers
            if tier in [BookTier.PREMIUM, BookTier.ULTRA]:
                tasks = [
                    self.generate_illustration_premium(
                        character_bible=character_bible,
                        scene_description=page.get('scene_description', ''),
                        character_action=page.get('character_action', ''),
                        mood=page.get('mood', 'happy'),
                        art_style=art_style,
                        page_number=page.get('page_number', i + idx + 1),
                        tier=tier,
                        character_reference_url=character_reference_url,
                        characters_in_scene=page.get('characters_in_scene', []),
                        quality=quality
                    )
                    for idx, page in enumerate(batch)
                ]
            else:
                # Use standard generation for BASIC tier
                tasks = [
                    self.generate_illustration(
                        character_bible=character_bible,
                        scene_description=page.get('scene_description', ''),
                        character_action=page.get('character_action', ''),
                        mood=page.get('mood', 'happy'),
                        art_style=art_style,
                        page_number=page.get('page_number', i + idx + 1),
                        characters_in_scene=page.get('characters_in_scene', []),
                        quality=quality
                    )
                    for idx, page in enumerate(batch)
                ]
            
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"Batch image generation failed: {result}")
                    illustrations.append({
                        "url": "https://placehold.co/800x600/amber/white?text=Regenerate",
                        "error": str(result)
                    })
                else:
                    illustrations.append(result)
            
            # Small delay between batches to avoid rate limiting
            if i + batch_size < len(story_pages):
                await asyncio.sleep(0.5)
        
        logger.info(f"Generated {len(illustrations)} {tier.value} tier illustrations")
        return illustrations

    async def generate_cover(
        self,
        character_bible: Dict[str, str],
        title: str,
        art_style: str,
        quality: GenerationQuality = GenerationQuality.PREVIEW
    ) -> Dict[str, Any]:
        """
        Generate book cover image.

        Args:
            character_bible: Character description
            title: Book title
            art_style: Art style
            quality: Generation quality

        Returns:
            Dict with url and prompt
        """
        import fal_client

        if not self.api_key:
            raise ValueError("Fal.ai API key not configured")

        config = self.MODEL_CONFIGS.get(quality, self.MODEL_CONFIGS[GenerationQuality.PREVIEW])
        style_desc = self.STYLE_DESCRIPTIONS.get(art_style, "watercolor illustration")

        main_char = character_bible.get('main_character', '')

        prompt = f"""
{style_desc}

Book cover for: {title}

Main character: {main_char}

The character is featured prominently on the cover, looking heroic and adventurous.
Beautiful background matching the story theme.
Title space at the top.
Whimsical, magical children's book aesthetic.

{SAFETY_NEGATIVE_PROMPT}
"""

        params = {
            "prompt": prompt,
            "negative_prompt": SAFETY_NEGATIVE_PROMPT,
            **config
        }

        result = await self._call_fal_ai_with_retry(config["model"], params)

        return {
            "url": result.get("images", [{}])[0].get("url", ""),
            "prompt": prompt,
            "quality": quality.value
        }

    async def generate_hero_portrait(
        self,
        character_bible: Dict[str, str],
        art_style: str,
        photo_url: Optional[str],
        quality: GenerationQuality = GenerationQuality.PREVIEW
    ) -> Dict[str, Any]:
        """
        Generate hero portrait.

        Args:
            character_bible: Character description
            art_style: Art style
            photo_url: Optional photo for likeness
            quality: Generation quality

        Returns:
            Dict with url and is_placeholder flag
        """
        import fal_client

        if not self.api_key:
            raise ValueError("Fal.ai API key not configured")

        config = self.MODEL_CONFIGS.get(quality, self.MODEL_CONFIGS[GenerationQuality.PREVIEW])
        style_desc = self.STYLE_DESCRIPTIONS.get(art_style, "watercolor illustration")

        main_char = character_bible.get('main_character', '')

        # If no photo, generate generic portrait
        if not photo_url:
            prompt = f"""
{style_desc}

Portrait of {main_char}

Smiling, friendly expression.
Centered portrait, shoulders and head visible.
Magical sparkles or stars in background.
Clean, simple composition perfect for a character profile.

{SAFETY_NEGATIVE_PROMPT}
"""
            is_placeholder = True
        else:
            # With photo, try to preserve likeness
            prompt = f"""
{style_desc}

Transform this photo into an illustration: {photo_url}

Character: {main_char}

Preserve the child's facial features and likeness.
Smiling, friendly expression.
Centered portrait.

{SAFETY_NEGATIVE_PROMPT}
"""
            is_placeholder = False

        params = {
            "prompt": prompt,
            "negative_prompt": SAFETY_NEGATIVE_PROMPT,
            **config
        }

        if photo_url and not is_placeholder:
            params["image_url"] = photo_url

        result = await self._call_fal_ai_with_retry(config["model"], params)

        return {
            "url": result.get("images", [{}])[0].get("url", ""),
            "is_placeholder": is_placeholder,
            "quality": quality.value
        }

    async def generate_hero_portrait_with_reference(
        self,
        character_reference_url: str,
        art_style: str,
        art_modifier: str = "",
        quality: GenerationQuality = GenerationQuality.PREVIEW
    ) -> Dict[str, Any]:
        """
        Generate hero portrait using approved character reference.

        Args:
            character_reference_url: URL to approved character variant
            art_style: Art style
            art_modifier: Optional modifier (softer/brighter/detailed)
            quality: Generation quality

        Returns:
            Dict with url
        """
        import fal_client

        if not self.api_key:
            raise ValueError("Fal.ai API key not configured")

        config = self.MODEL_CONFIGS.get(quality, self.MODEL_CONFIGS[GenerationQuality.PREVIEW])
        style_desc = self.STYLE_DESCRIPTIONS.get(art_style, "watercolor illustration")

        modifier_text = ""
        if art_modifier == "softer":
            modifier_text = "softer edges, gentler colors"
        elif art_modifier == "brighter":
            modifier_text = "brighter colors, more vibrant"
        elif art_modifier == "detailed":
            modifier_text = "more detailed, richer textures"

        prompt = f"""
{style_desc}

Using this character reference: {character_reference_url}

Portrait maintaining EXACT character likeness.
{modifier_text}
Smiling, friendly expression.
Centered portrait.

{SAFETY_NEGATIVE_PROMPT}
"""

        params = {
            "prompt": prompt,
            "image_url": character_reference_url,
            "negative_prompt": SAFETY_NEGATIVE_PROMPT,
            **config
        }

        result = await self._call_fal_ai_with_retry(config["model"], params)

        return {
            "url": result.get("images", [{}])[0].get("url", ""),
            "quality": quality.value
        }
