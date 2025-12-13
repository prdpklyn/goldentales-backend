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
from app.models.enums import GenerationQuality
from app.utils.logging import get_logger
from app.utils.security import SAFETY_NEGATIVE_PROMPT
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
    
    # Model configurations by quality tier
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
    
    async def generate_illustration(
        self,
        character_bible: Dict[str, str],
        scene_description: str,
        character_action: str,
        mood: str,
        art_style: str,
        page_number: int,
        characters_in_scene: Optional[List[str]] = None,
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
        
        # Add quality and consistency instructions
        full_prompt += """

CRITICAL CONSISTENCY RULES:
- Character's face, hair, skin tone, and features must match the description EXACTLY
- Same character design as all other pages in this book
- Maintain exact hair color, style, and length
- Keep any accessories (glasses, bows, etc.) consistent
- Same clothing style/colors throughout

OUTPUT: High-quality children's book illustration, professional, vibrant, safe for all ages.
"""
        
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
        
        # Add negative prompt for higher quality
        if quality != GenerationQuality.PREVIEW:
            params["negative_prompt"] = SAFETY_NEGATIVE_PROMPT
        
        try:
            logger.info(f"Generating page {page_number} with {quality.value} quality")
            
            handler = await fal_client.submit_async(model, arguments=params)
            result = await handler.get()
            
            cost = getattr(settings, f"cost_{quality.value}", 0.02)
            
            return {
                "url": result['images'][0]['url'],
                "quality": quality.value,
                "page_number": page_number,
                "cost": cost
            }
            
        except Exception as e:
            logger.error(f"Image generation failed for page {page_number}: {e}")
            raise ValueError(f"Image generation failed: {str(e)}")
    
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
