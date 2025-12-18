# tests/fixtures/edge_functions.py
"""
Mock fixtures for Supabase Edge Functions.
"""

from typing import Dict, Any, Optional
import pytest
from unittest.mock import AsyncMock, MagicMock


class MockEdgeFunctionClient:
    """Mock Edge Function client for testing."""
    
    def __init__(self):
        self.calls = []
        self.responses = {}
    
    async def call(self, payload: Dict[str, Any], method: str = "POST") -> Dict[str, Any]:
        """Mock call method."""
        self.calls.append({"payload": payload, "method": method})
        
        # Return configured response or default
        key = str(payload)
        if key in self.responses:
            return self.responses[key]
        
        return {
            "success": True,
            "data": {"id": "mock-id", **payload}
        }
    
    def set_response(self, payload: Dict[str, Any], response: Dict[str, Any]):
        """Configure a specific response for a payload."""
        self.responses[str(payload)] = response


class MockDatabaseEdgeService:
    """Mock Database Edge Service for testing."""
    
    def __init__(self):
        self.stories = {}
        self.pages = {}
        self.orders = {}
    
    async def create_story(self, **kwargs) -> Dict[str, Any]:
        """Mock create_story."""
        story_id = f"story-{len(self.stories) + 1}"
        story = {
            "id": story_id,
            "created_at": "2024-01-01T00:00:00",
            **kwargs
        }
        self.stories[story_id] = story
        return story
    
    async def get_story(self, story_id: str) -> Optional[Dict[str, Any]]:
        """Mock get_story."""
        return self.stories.get(story_id)
    
    async def update_story(
        self,
        story_id: str,
        updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Mock update_story."""
        if story_id in self.stories:
            self.stories[story_id].update(updates)
            return self.stories[story_id]
        return None
    
    async def create_page(
        self,
        story_id: str,
        page_number: int,
        text_content: str,
        image_prompt: str,
        image_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Mock create_page."""
        page_id = f"page-{story_id}-{page_number}"
        page = {
            "id": page_id,
            "story_id": story_id,
            "page_number": page_number,
            "text_content": text_content,
            "image_prompt": image_prompt,
            "image_url": image_url
        }
        
        if story_id not in self.pages:
            self.pages[story_id] = []
        self.pages[story_id].append(page)
        
        return page
    
    async def get_pages(self, story_id: str) -> list[Dict[str, Any]]:
        """Mock get_pages."""
        return sorted(
            self.pages.get(story_id, []),
            key=lambda p: p["page_number"]
        )
    
    async def update_page(
        self,
        page_id: str,
        updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Mock update_page."""
        for story_id, pages in self.pages.items():
            for page in pages:
                if page["id"] == page_id:
                    page.update(updates)
                    return page
        return None
    
    async def get_page_by_number(
        self,
        story_id: str,
        page_number: int
    ) -> Optional[Dict[str, Any]]:
        """Mock get_page_by_number."""
        pages = self.pages.get(story_id, [])
        for page in pages:
            if page["page_number"] == page_number:
                return page
        return None
    
    async def get_full_book(self, story_id: str) -> Optional[Dict[str, Any]]:
        """Mock get_full_book."""
        story = await self.get_story(story_id)
        if not story:
            return None
        
        pages = await self.get_pages(story_id)
        
        return {
            "book_id": story["id"],
            "title": f"{story['child_name']}'s {story['theme'].title()} Adventure",
            "child_name": story["child_name"],
            "child_age": story["child_age"],
            "theme": story["theme"],
            "pages": pages,
            "preview_images": [p.get("image_url") for p in pages if p.get("image_url")],
            "page_count": len(pages),
            "created_at": story["created_at"],
            "character_bible": story.get("character_bible", {})
        }
    
    async def create_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock create_order."""
        order_id = f"order-{len(self.orders) + 1}"
        order = {
            "id": order_id,
            "created_at": "2024-01-01T00:00:00",
            **order_data
        }
        self.orders[order_id] = order
        return order
    
    async def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Mock get_order."""
        return self.orders.get(order_id)
    
    async def update_order(
        self,
        order_id: str,
        updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Mock update_order."""
        if order_id in self.orders:
            self.orders[order_id].update(updates)
            return self.orders[order_id]
        return None


@pytest.fixture
def mock_edge_function_client():
    """Fixture providing a mock Edge Function client."""
    return MockEdgeFunctionClient()


@pytest.fixture
def mock_database_edge_service():
    """Fixture providing a mock Database Edge Service."""
    return MockDatabaseEdgeService()


@pytest.fixture
def mock_edge_function_response():
    """Fixture for creating mock Edge Function responses."""
    def _create_response(success: bool = True, data: Optional[Dict] = None, error: Optional[str] = None):
        return {
            "success": success,
            "data": data,
            "error": error
        }
    return _create_response

