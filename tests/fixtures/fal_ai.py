# tests/fixtures/fal_ai.py
"""
Mock fixtures for Fal.ai API.
"""

import pytest
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, MagicMock


class MockFalAiClient:
    """Mock Fal.ai client for testing."""
    
    def __init__(self):
        self.calls = []
        self.default_image_url = "https://mock-fal-ai.com/image.jpg"
    
    async def generate_image(
        self,
        prompt: str,
        model: str = "fal-ai/flux/schnell",
        **kwargs
    ) -> Dict[str, Any]:
        """Mock image generation."""
        self.calls.append({
            "prompt": prompt,
            "model": model,
            **kwargs
        })
        
        return {
            "url": self.default_image_url,
            "width": kwargs.get("width", 1024),
            "height": kwargs.get("height", 1024),
            "model": model
        }
    
    async def upscale_image(
        self,
        image_url: str,
        scale: int = 2
    ) -> Dict[str, Any]:
        """Mock image upscaling."""
        self.calls.append({
            "operation": "upscale",
            "image_url": image_url,
            "scale": scale
        })
        
        return {
            "url": f"{image_url}_upscaled",
            "scale": scale
        }


class MockImageGenerator:
    """Mock ImageGenerator service for testing."""
    
    def __init__(self):
        self.generated_images = []
    
    async def generate_illustration(
        self,
        character_bible: Dict,
        scene_description: str,
        character_action: str,
        mood: str,
        art_style: str,
        page_number: int,
        **kwargs
    ) -> Dict[str, Any]:
        """Mock illustration generation."""
        image_data = {
            "url": f"https://mock-image.com/page-{page_number}.jpg",
            "page_number": page_number,
            "prompt": scene_description,
            "mood": mood
        }
        self.generated_images.append(image_data)
        return image_data
    
    async def generate_all_illustrations(
        self,
        character_bible: Dict,
        story_pages: list,
        art_style: str,
        **kwargs
    ) -> list[Dict[str, Any]]:
        """Mock all illustrations generation."""
        illustrations = []
        for i, page in enumerate(story_pages):
            illustration = await self.generate_illustration(
                character_bible=character_bible,
                scene_description=page.get("scene_description", ""),
                character_action=page.get("character_action", ""),
                mood=page.get("mood", "happy"),
                art_style=art_style,
                page_number=i + 1
            )
            illustrations.append(illustration)
        return illustrations
    
    async def generate_illustration_premium(
        self,
        character_bible: Dict,
        scene_description: str,
        character_action: str,
        mood: str,
        art_style: str,
        page_number: int,
        tier: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Mock premium illustration generation."""
        return await self.generate_illustration(
            character_bible=character_bible,
            scene_description=scene_description,
            character_action=character_action,
            mood=mood,
            art_style=art_style,
            page_number=page_number,
            **kwargs
        )
    
    async def generate_all_illustrations_with_tier(
        self,
        character_bible: Dict,
        story_pages: list,
        art_style: str,
        tier: str,
        **kwargs
    ) -> list[Dict[str, Any]]:
        """Mock tier-aware illustrations generation."""
        return await self.generate_all_illustrations(
            character_bible=character_bible,
            story_pages=story_pages,
            art_style=art_style,
            **kwargs
        )
    
    async def upscale_for_print(
        self,
        image_url: str,
        target_size: tuple = (3072, 3072)
    ) -> Dict[str, Any]:
        """Mock image upscaling for print."""
        return {
            "url": f"{image_url}_upscaled",
            "width": target_size[0],
            "height": target_size[1]
        }


@pytest.fixture
def mock_fal_ai_client():
    """Fixture providing a mock Fal.ai client."""
    return MockFalAiClient()


@pytest.fixture
def mock_image_generator():
    """Fixture providing a mock ImageGenerator service."""
    return MockImageGenerator()


@pytest.fixture
def mock_fal_ai_service():
    """Fixture providing a mock Fal.ai service (alias for compatibility)."""
    return MockFalAiClient()

