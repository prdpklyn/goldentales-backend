# app/services/character_service.py
"""
GoldenTales Character Service
=============================
Manages character profiles and bible generation.
"""

from typing import Dict, Optional, Tuple

from app.config import settings
from app.utils.logging import get_logger
from character_system import (
    Gender, SkinTone, HairColor, HairStyle, EyeColor, BodyType,
    MainCharacter, AdditionalCharacter, CharacterProfile,
    CharacterAccessories, CharacterClothing, DistinctiveFeatures,
    CharacterDescriptionGenerator, analyze_photo_for_character
)

logger = get_logger(__name__)


class CharacterService:
    """
    Service for managing character profiles and generating character bibles.
    
    The character bible is the core of the consistency system - it's a
    detailed text description that's included in every image prompt.
    
    Example:
        service = CharacterService()
        profile, bible = await service.create_profile(request)
    """
    
    def __init__(self):
        """Initialize the character service."""
        self.description_generator = CharacterDescriptionGenerator()
    
    async def create_profile(
        self,
        child_name: str,
        child_gender: Gender,
        child_age: int,
        skin_tone: SkinTone,
        hair_color: HairColor,
        hair_style: HairStyle,
        eye_color: EyeColor = EyeColor.BROWN,
        body_type: BodyType = BodyType.AVERAGE,
        has_glasses: bool = False,
        glasses_type: Optional[str] = None,
        has_freckles: bool = False,
        has_dimples: bool = False,
        other_features: Optional[str] = None,
        favorite_outfit: Optional[str] = None,
        favorite_color: Optional[str] = None,
        photo_url: Optional[str] = None,
        additional_characters: list = None,
        theme: str = "christmas",
        art_style: str = "watercolor"
    ) -> Tuple[CharacterProfile, Dict[str, str]]:
        """
        Create a complete character profile and generate the character bible.
        
        The bible will be used in EVERY image generation for consistency.
        
        Returns:
            Tuple of (CharacterProfile, character_bible dict)
        """
        
        # Build accessories
        accessories = None
        if has_glasses or other_features:
            accessories = CharacterAccessories(
                glasses=has_glasses,
                glasses_type=glasses_type,
                other=other_features
            )
        
        # Build distinctive features
        distinctive = None
        if has_freckles or has_dimples or other_features:
            distinctive = DistinctiveFeatures(
                freckles=has_freckles,
                dimples=has_dimples,
                other=other_features
            )
        
        # Build clothing preferences
        clothing = None
        if favorite_outfit or favorite_color:
            clothing = CharacterClothing(
                specific_outfit=favorite_outfit,
                favorite_color=favorite_color
            )
        
        # Analyze photo if provided
        photo_description = None
        if photo_url and settings.gemini_api_key:
            try:
                logger.info("Analyzing photo for character features")
                photo_analysis = await analyze_photo_for_character(
                    photo_url,
                    settings.gemini_api_key
                )
                photo_description = photo_analysis.get('overall_description')
                logger.info(f"Photo analysis complete: {photo_description[:100]}...")
            except Exception as e:
                logger.warning(f"Photo analysis failed: {e}")
        
        # Create main character
        main_character = MainCharacter(
            name=child_name,
            gender=child_gender,
            age=child_age,
            skin_tone=skin_tone,
            hair_color=hair_color,
            hair_style=hair_style,
            eye_color=eye_color,
            body_type=body_type,
            accessories=accessories,
            distinctive_features=distinctive,
            clothing=clothing,
            photo_url=photo_url,
            photo_description=photo_description
        )
        
        # Process additional characters
        additional_chars = []
        if additional_characters:
            for char_req in additional_characters:
                additional_chars.append(AdditionalCharacter(
                    name=char_req.name,
                    character_type=char_req.character_type,
                    relationship=char_req.relationship,
                    gender=char_req.gender,
                    age_description=char_req.age_description,
                    skin_tone=char_req.skin_tone,
                    hair_color=char_req.hair_color,
                    pet_species=char_req.pet_species,
                    pet_color=char_req.pet_color,
                    distinctive_feature=char_req.distinctive_feature
                ))
        
        # Create profile
        profile = CharacterProfile(
            main_character=main_character,
            additional_characters=additional_chars,
            theme=theme,
            art_style=art_style
        )
        
        # Generate character bible
        bible = self.description_generator.generate_full_character_bible(profile)
        
        logger.info(f"Created character profile for {child_name}")
        
        return profile, bible
