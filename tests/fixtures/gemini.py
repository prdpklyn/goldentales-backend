# tests/fixtures/gemini.py
"""
Mock fixtures for Gemini AI API.
"""

import pytest
from typing import Dict, Any, List
from unittest.mock import AsyncMock, MagicMock


class MockGeminiClient:
    """Mock Gemini client for testing."""
    
    def __init__(self):
        self.calls = []
        self.default_story = self._generate_default_story()
    
    def _generate_default_story(self) -> List[Dict[str, Any]]:
        """Generate a default mock story."""
        return [
            {
                "page_number": i + 1,
                "text": f"This is page {i + 1} of the story.",
                "scene_description": f"Scene description for page {i + 1}",
                "character_action": f"character action {i + 1}",
                "mood": "happy",
                "characters_in_scene": ["Emma"]
            }
            for i in range(10)
        ]
    
    async def generate_story(
        self,
        prompt: str,
        **kwargs
    ) -> str:
        """Mock story generation."""
        self.calls.append({
            "prompt": prompt,
            **kwargs
        })
        
        # Return JSON-formatted story
        import json
        return json.dumps(self.default_story)
    
    def set_story(self, story: List[Dict[str, Any]]):
        """Set custom story for testing."""
        self.default_story = story


class MockStoryGenerator:
    """Mock StoryGenerator service for testing."""
    
    def __init__(self):
        self.generated_stories = []
    
    async def generate_story(
        self,
        character_bible: Dict,
        child_name: str,
        age: int,
        theme: str,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Mock story generation."""
        story = [
            {
                "page_number": i + 1,
                "text": f"{child_name} embarked on a {theme} adventure. Page {i + 1}.",
                "scene_description": f"{character_bible.get('main_character', child_name)} in a {theme} scene",
                "character_action": f"exploring the {theme}",
                "mood": "excited" if i < 5 else "happy",
                "characters_in_scene": [child_name]
            }
            for i in range(10)
        ]
        
        self.generated_stories.append(story)
        return story


class MockCharacterService:
    """Mock CharacterService for testing."""
    
    async def create_profile(
        self,
        child_name: str,
        child_gender: str,
        child_age: int,
        **kwargs
    ):
        """Mock character profile creation."""
        profile = MagicMock()
        profile.additional_characters = kwargs.get("additional_characters", [])
        
        bible = {
            "main_character": f"{child_name}, {child_age}-year-old {child_gender}",
            "main_character_short": f"{child_name}, {child_age}-year-old",
            "additional_characters": [],
            "all_characters_summary": f"{child_name}, {child_age}-year-old {child_gender}"
        }
        
        return profile, bible


@pytest.fixture
def mock_gemini_client():
    """Fixture providing a mock Gemini client."""
    return MockGeminiClient()


@pytest.fixture
def mock_story_generator():
    """Fixture providing a mock StoryGenerator service."""
    return MockStoryGenerator()


@pytest.fixture
def mock_character_service():
    """Fixture providing a mock CharacterService."""
    return MockCharacterService()

