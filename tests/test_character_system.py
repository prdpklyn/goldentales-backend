# tests/test_character_system.py
"""
Tests for the character consistency system.
"""

import pytest
from character_system import (
    Gender, SkinTone, HairColor, HairStyle, EyeColor, BodyType,
    MainCharacter, CharacterProfile, CharacterDescriptionGenerator
)


def test_main_character_creation():
    """Test creating a main character."""
    char = MainCharacter(
        name="Emma",
        gender=Gender.GIRL,
        age=6,
        skin_tone=SkinTone.LIGHT,
        hair_color=HairColor.BROWN,
        hair_style=HairStyle.PIGTAILS,
        eye_color=EyeColor.BLUE,
        body_type=BodyType.AVERAGE
    )
    
    assert char.name == "Emma"
    assert char.gender == Gender.GIRL
    assert char.age == 6


def test_character_description_generation():
    """Test generating character descriptions."""
    char = MainCharacter(
        name="Emma",
        gender=Gender.GIRL,
        age=6,
        skin_tone=SkinTone.LIGHT,
        hair_color=HairColor.BROWN,
        hair_style=HairStyle.PIGTAILS,
        eye_color=EyeColor.BLUE,
        body_type=BodyType.AVERAGE
    )
    
    generator = CharacterDescriptionGenerator()
    description = generator.generate_main_character_description(char)
    
    assert "Emma" in description
    assert "6-year-old" in description
    assert "girl" in description
    assert "light" in description.lower()
    assert "brown" in description.lower()
    assert "pigtails" in description.lower()


def test_character_bible_generation():
    """Test generating a complete character bible."""
    profile = CharacterProfile(
        main_character=MainCharacter(
            name="Emma",
            gender=Gender.GIRL,
            age=6,
            skin_tone=SkinTone.LIGHT,
            hair_color=HairColor.BROWN,
            hair_style=HairStyle.PIGTAILS,
            eye_color=EyeColor.BLUE,
            body_type=BodyType.AVERAGE
        ),
        additional_characters=[],
        theme="christmas",
        art_style="watercolor"
    )
    
    generator = CharacterDescriptionGenerator()
    bible = generator.generate_full_character_bible(profile)
    
    assert "main_character" in bible
    assert "main_character_short" in bible
    assert "all_characters_summary" in bible
    assert "Emma" in bible["main_character"]


def test_page_prompt_building():
    """Test building a complete page prompt."""
    profile = CharacterProfile(
        main_character=MainCharacter(
            name="Emma",
            gender=Gender.GIRL,
            age=6,
            skin_tone=SkinTone.LIGHT,
            hair_color=HairColor.BROWN,
            hair_style=HairStyle.PIGTAILS,
            eye_color=EyeColor.BLUE,
            body_type=BodyType.AVERAGE
        ),
        additional_characters=[],
        theme="christmas",
        art_style="watercolor"
    )
    
    generator = CharacterDescriptionGenerator()
    bible = generator.generate_full_character_bible(profile)
    
    prompt = generator.build_page_prompt(
        character_bible=bible,
        scene_description="A snowy Christmas scene",
        character_action="building a snowman",
        mood="happy",
        art_style="watercolor",
        page_number=1
    )
    
    # Check that the prompt contains character description
    assert "Emma" in prompt
    assert "watercolor" in prompt.lower()
    assert "snowman" in prompt or "snow" in prompt
