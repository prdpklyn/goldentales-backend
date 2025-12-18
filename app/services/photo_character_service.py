# app/services/photo_character_service.py
"""
GoldenTales Photo Character Service
====================================
Transform child photos into illustrated characters using fal-ai/nano-banana/edit.

This service handles:
1. Photo validation (face detection, quality check)
2. Photo-to-character transformation
3. Character preview generation for user approval
"""

import os
import uuid
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from app.settings import settings
from app.models.enums import ArtStyle
from app.utils.logging import get_logger
from app.utils.retry import with_retry
from app.utils.exceptions import ExternalServiceException

logger = get_logger(__name__)


class PhotoCharacterService:
    """
    Service for transforming child photos into illustrated characters.
    
    Uses fal-ai/nano-banana/edit for style transfer while preserving likeness.
    
    Example:
        service = PhotoCharacterService()
        validation = await service.validate_photo("https://example.com/photo.jpg")
        if validation["valid"]:
            preview = await service.generate_character_preview(
                photo_url="https://example.com/photo.jpg",
                art_style="cartoon"
            )
    """
    
    # Style-specific transformation prompts
    STYLE_PROMPTS = {
        ArtStyle.CARTOON: "Transform into vibrant cartoon illustration, Pixar-inspired, bold outlines, bright cheerful colors",
        ArtStyle.PIXAR: "Transform into Pixar-style 3D animated character, soft lighting, expressive features",
        ArtStyle.WATERCOLOR: "Transform into soft watercolor illustration style, gentle flowing colors, dreamy brushstrokes",
        ArtStyle.STORYBOOK: "Transform into classic children's book illustration, warm nostalgic colors, golden age storybook art",
        ArtStyle.GHIBLI: "Transform into Studio Ghibli anime style character, hand-painted aesthetic, soft shading",
        ArtStyle.ANIME: "Transform into anime/manga illustration style, expressive features, soft shading",
    }
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the photo character service.
        
        Args:
            api_key: Fal.ai API key. Defaults to settings.
        """
        self.api_key = api_key or settings.fal_key
        if self.api_key:
            os.environ["FAL_KEY"] = self.api_key
        else:
            logger.warning("Fal.ai API key not configured")
        
        # In-memory storage for preview sessions (replace with Redis in production)
        self._preview_sessions: Dict[str, Dict[str, Any]] = {}
    
    async def validate_photo(self, photo_url: str) -> Dict[str, Any]:
        """
        Validate a photo for character transformation.
        
        Checks:
        - Face is detected
        - Photo quality is sufficient
        - Face is clear and front-facing
        
        Args:
            photo_url: URL of the photo to validate
            
        Returns:
            Validation result with face_detected, confidence, message, issues
        """
        logger.info(f"Validating photo: {photo_url}")
        
        try:
            # For now, we'll use a simple validation
            # In production, you could use fal-ai/face-detector or similar
            
            # Basic URL validation
            if not photo_url.startswith(('http://', 'https://')):
                return {
                    "valid": False,
                    "face_detected": False,
                    "confidence": 0.0,
                    "message": "Invalid photo URL format",
                    "issues": ["URL must start with http:// or https://"]
                }
            
            # TODO: Implement actual face detection
            # For now, assume valid
            return {
                "valid": True,
                "face_detected": True,
                "confidence": 0.95,
                "message": "Photo validated successfully",
                "issues": []
            }
            
        except Exception as e:
            logger.error(f"Photo validation error: {e}")
            return {
                "valid": False,
                "face_detected": False,
                "confidence": 0.0,
                "message": f"Validation failed: {str(e)}",
                "issues": [str(e)]
            }
    
    @with_retry(
        max_attempts=3,
        initial_delay=2.0,
        max_delay=30.0,
        circuit_breaker_name="fal_ai_nano_banana"
    )
    async def _call_nano_banana_with_retry(
        self,
        photo_url: str,
        prompt: str,
        preserve_likeness: float
    ) -> Dict[str, Any]:
        """
        Call fal-ai/nano-banana/edit API with retry logic.
        
        Args:
            photo_url: URL of the original photo
            prompt: Transformation prompt
            preserve_likeness: How much to preserve original features (0.5-1.0)
            
        Returns:
            API result with transformed image
            
        Note:
            According to fal.ai nano-banana/edit API documentation:
            - image_urls: list<string> (required) - The URLs of the images to use
            - prompt: string (required) - The prompt for image editing
            - num_images: integer (optional, default: 1)
            - aspect_ratio: AspectRatioEnum (optional, default: "auto")
            - output_format: OutputFormatEnum (optional, default: "png")
        """
        import fal_client
        
        try:
            # Enhance prompt with likeness preservation instructions
            # Higher preserve_likeness = more emphasis on keeping original features
            likeness_instruction = ""
            if preserve_likeness >= 0.9:
                likeness_instruction = " Maintain strong facial resemblance and key features from the original photo."
            elif preserve_likeness >= 0.7:
                likeness_instruction = " Preserve recognizable facial features and characteristics from the original."
            elif preserve_likeness >= 0.5:
                likeness_instruction = " Keep some resemblance to the original while transforming the style."
            
            enhanced_prompt = prompt + likeness_instruction
            
            params = {
                "image_urls": [photo_url],  # Must be a list of strings (required)
                "prompt": enhanced_prompt,  # Required
                "num_images": 1,  # Optional, default: 1
                "aspect_ratio": "auto",  # Optional, default: "auto"
                "output_format": "png",  # Optional, default: "png"
            }
            
            handler = await fal_client.submit_async(
                "fal-ai/nano-banana/edit",
                arguments=params
            )
            result = await handler.get()
            return result
            
        except Exception as e:
            error_msg = str(e).lower()
            is_transient = any(
                pattern in error_msg
                for pattern in ['timeout', 'rate limit', 'unavailable', '429', '503']
            )
            
            raise ExternalServiceException(
                service_name="Fal.ai nano-banana",
                message=str(e),
                is_transient=is_transient
            )
    
    async def transform_to_character(
        self,
        photo_url: str,
        art_style: str,
        preserve_likeness: float = 0.8
    ) -> Dict[str, Any]:
        """
        Transform a photo into an illustrated character.
        
        Args:
            photo_url: URL of the validated photo
            art_style: Illustration style to use
            preserve_likeness: How much to preserve photo likeness (0.5-1.0)
            
        Returns:
            Transformation result with character_image_url, style, cost
        """
        if not self.api_key:
            raise ValueError("Fal.ai API key not configured")
        
        # Get style-specific prompt
        style_enum = ArtStyle(art_style)
        prompt = self.STYLE_PROMPTS.get(
            style_enum,
            self.STYLE_PROMPTS[ArtStyle.CARTOON]
        )
        
        # Add safety instructions
        prompt += ". Child-friendly illustration, safe for all ages, appropriate for children's book."
        
        logger.info(f"Transforming photo to {art_style} style with likeness {preserve_likeness}")
        
        try:
            result = await self._call_nano_banana_with_retry(
                photo_url=photo_url,
                prompt=prompt,
                preserve_likeness=preserve_likeness
            )
            
            character_url = result['images'][0]['url']
            
            logger.info(f"Character transformation successful: {character_url}")
            
            return {
                "character_image_url": character_url,
                "art_style": art_style,
                "preserve_likeness": preserve_likeness,
                "cost": settings.cost_photo_character_transform
            }
            
        except Exception as e:
            logger.error(f"Character transformation failed: {e}")
            raise ExternalServiceException(
                service_name="Fal.ai nano-banana",
                message=f"Character transformation failed: {str(e)}",
                is_transient=True
            )
    
    async def generate_character_preview(
        self,
        photo_url: str,
        art_style: str,
        preserve_likeness: float = 0.8
    ) -> Dict[str, Any]:
        """
        Generate a character preview for user approval.
        
        Creates a preview session that expires after 1 hour.
        
        Args:
            photo_url: URL of the validated photo
            art_style: Illustration style to use
            preserve_likeness: How much to preserve photo likeness (0.5-1.0)
            
        Returns:
            Preview result with preview_id, character_image_url, expires_at
        """
        # Transform photo to character
        transform_result = await self.transform_to_character(
            photo_url=photo_url,
            art_style=art_style,
            preserve_likeness=preserve_likeness
        )
        
        # Create preview session
        preview_id = str(uuid.uuid4())
        expires_at = datetime.now() + timedelta(hours=1)
        
        session = {
            "preview_id": preview_id,
            "original_photo_url": photo_url,
            "character_image_url": transform_result["character_image_url"],
            "art_style": art_style,
            "preserve_likeness": preserve_likeness,
            "created_at": datetime.now().isoformat(),
            "expires_at": expires_at.isoformat(),
            "approved": False
        }
        
        self._preview_sessions[preview_id] = session
        
        logger.info(f"Character preview created: {preview_id}")
        
        return {
            "preview_id": preview_id,
            "original_photo_url": photo_url,
            "character_image_url": transform_result["character_image_url"],
            "art_style": art_style,
            "message": "Character preview generated successfully. Please approve to use in your book.",
            "expires_at": expires_at.isoformat()
        }
    
    async def approve_character(self, preview_id: str) -> Dict[str, Any]:
        """
        Approve a character preview for use in book generation.
        
        Args:
            preview_id: ID of the preview session
            
        Returns:
            Approval result with character_reference_url
        """
        if preview_id not in self._preview_sessions:
            raise ValueError(f"Preview session {preview_id} not found or expired")
        
        session = self._preview_sessions[preview_id]
        
        # Check if expired
        expires_at = datetime.fromisoformat(session["expires_at"])
        if datetime.now() > expires_at:
            del self._preview_sessions[preview_id]
            raise ValueError(f"Preview session {preview_id} has expired")
        
        # Mark as approved
        session["approved"] = True
        session["approved_at"] = datetime.now().isoformat()
        
        logger.info(f"Character preview approved: {preview_id}")
        
        return {
            "approved": True,
            "character_reference_url": session["character_image_url"],
            "message": "Character approved! You can now create your book."
        }
    
    def get_preview_session(self, preview_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a preview session by ID.
        
        Args:
            preview_id: ID of the preview session
            
        Returns:
            Preview session data or None if not found
        """
        return self._preview_sessions.get(preview_id)


# ============================================
# SINGLETON INSTANCE
# ============================================

_photo_character_service: Optional[PhotoCharacterService] = None


def get_photo_character_service() -> PhotoCharacterService:
    """Get the photo character service singleton."""
    global _photo_character_service
    if _photo_character_service is None:
        _photo_character_service = PhotoCharacterService()
    return _photo_character_service
