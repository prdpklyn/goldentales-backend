# tests/conftest.py
"""
DreamWeaver Test Configuration
==============================
Pytest fixtures and configuration for testing.
"""

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def sample_book_request():
    """Sample book creation request for testing."""
    return {
        "child_name": "Emma",
        "child_gender": "girl",
        "child_age": 6,
        "skin_tone": "LIGHT",
        "hair_color": "BROWN",
        "hair_style": "PIGTAILS",
        "eye_color": "BLUE",
        "body_type": "AVERAGE",
        "has_glasses": False,
        "has_freckles": True,
        "has_dimples": False,
        "theme": "christmas",
        "art_style": "watercolor",
        "additional_characters": []
    }


@pytest.fixture
def sample_character_bible():
    """Sample character bible for testing."""
    return {
        "main_character": "a 6-year-old girl named Emma, with light skin, brown hair in pigtails style, blue eyes, with freckles",
        "main_character_short": "Emma, 6-year-old girl",
        "additional_characters": [],
        "all_characters_summary": "a 6-year-old girl named Emma, with light skin, brown hair in pigtails style, blue eyes, with freckles"
    }


@pytest.fixture
def sample_story_pages():
    """Sample story pages for testing."""
    return [
        {
            "page_number": 1,
            "text": "On a snowy Christmas Eve, Emma looked out her window at the falling snowflakes.",
            "scene_description": "A 6-year-old girl with light skin, brown pigtails, and blue eyes looking out a frosted window",
            "character_action": "pressing her nose against the cold glass",
            "mood": "curious",
            "characters_in_scene": ["Emma"]
        },
        {
            "page_number": 2,
            "text": "Suddenly, a magical light appeared in the sky!",
            "scene_description": "Emma pointing excitedly at a glowing light in the night sky",
            "character_action": "pointing up with excitement",
            "mood": "excited",
            "characters_in_scene": ["Emma"]
        }
    ]
