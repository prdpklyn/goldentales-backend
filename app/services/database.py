# app/services/database.py
"""
GoldenTales Database Service
============================
Supabase integration for story and page management.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import os

from supabase import create_client, Client

from app.settings import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


class DatabaseService:
    """
    Service for interacting with Supabase database.
    
    Tables:
    - stories: Main story/book data
    - pages: Individual pages with text and images
    """
    
    _instance: Optional["DatabaseService"] = None
    _client: Optional[Client] = None
    
    def __new__(cls):
        """Singleton pattern for database connection."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize Supabase client."""
        if self._client is None:
            if not settings.supabase_url or not settings.supabase_key:
                logger.warning("Supabase credentials not configured")
                return
            
            self._client = create_client(
                settings.supabase_url,
                settings.supabase_key
            )
            logger.info("Supabase client initialized")
    
    @property
    def client(self) -> Optional[Client]:
        """Get the Supabase client."""
        return self._client
    
    # ==========================================
    # STORY OPERATIONS
    # ==========================================
    
    async def create_story(
        self,
        child_name: str,
        child_age: int,
        theme: str,
        photo_url: Optional[str] = None,
        siblings: Optional[str] = None,
        favorite_characters: Optional[str] = None,
        pets: Optional[str] = None,
        parents: Optional[str] = None,
        friends: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a new story in the database.
        
        Returns:
            The created story record with id.
        """
        if not self._client:
            raise ValueError("Database not configured")
        
        data = {
            "child_name": child_name,
            "child_age": child_age,
            "theme": theme,
            "photo_url": photo_url,
            "siblings": siblings,
            "favorite_characters": favorite_characters,
            "pets": pets,
            "parents": parents,
            "friends": friends,
        }
        
        result = self._client.table("stories").insert(data).execute()
        
        if result.data:
            logger.info(f"Created story: {result.data[0]['id']}")
            return result.data[0]
        
        raise Exception("Failed to create story")
    
    async def get_story(self, story_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a story by ID.
        
        Args:
            story_id: UUID of the story
            
        Returns:
            Story data or None if not found
        """
        if not self._client:
            raise ValueError("Database not configured")
        
        result = self._client.table("stories").select("*").eq("id", story_id).execute()
        
        if result.data:
            return result.data[0]
        
        return None
    
    async def update_story(
        self, 
        story_id: str, 
        updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update a story."""
        if not self._client:
            raise ValueError("Database not configured")
        
        updates["updated_at"] = datetime.utcnow().isoformat()
        
        result = self._client.table("stories").update(updates).eq("id", story_id).execute()
        
        if result.data:
            return result.data[0]
        
        return None
    
    # ==========================================
    # PAGE OPERATIONS
    # ==========================================
    
    async def create_page(
        self,
        story_id: str,
        page_number: int,
        text_content: str,
        image_prompt: str,
        image_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a page for a story.
        
        Args:
            story_id: UUID of the parent story
            page_number: Page number (1-indexed)
            text_content: The story text for this page
            image_prompt: The prompt used to generate the image
            image_url: URL of the generated image
            
        Returns:
            The created page record
        """
        if not self._client:
            raise ValueError("Database not configured")
        
        data = {
            "story_id": story_id,
            "page_number": page_number,
            "text_content": text_content,
            "image_prompt": image_prompt,
            "image_url": image_url
        }
        
        result = self._client.table("pages").insert(data).execute()
        
        if result.data:
            logger.info(f"Created page {page_number} for story {story_id}")
            return result.data[0]
        
        raise Exception(f"Failed to create page {page_number}")
    
    async def get_pages(self, story_id: str) -> List[Dict[str, Any]]:
        """
        Get all pages for a story, ordered by page_number.
        
        Args:
            story_id: UUID of the story
            
        Returns:
            List of page records
        """
        if not self._client:
            raise ValueError("Database not configured")
        
        result = (
            self._client.table("pages")
            .select("*")
            .eq("story_id", story_id)
            .order("page_number")
            .execute()
        )
        
        return result.data or []
    
    async def update_page(
        self,
        page_id: str,
        updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update a page."""
        if not self._client:
            raise ValueError("Database not configured")
        
        result = self._client.table("pages").update(updates).eq("id", page_id).execute()
        
        if result.data:
            return result.data[0]
        
        return None
    
    async def get_page_by_number(
        self,
        story_id: str,
        page_number: int
    ) -> Optional[Dict[str, Any]]:
        """Get a specific page by story_id and page_number."""
        if not self._client:
            raise ValueError("Database not configured")
        
        result = (
            self._client.table("pages")
            .select("*")
            .eq("story_id", story_id)
            .eq("page_number", page_number)
            .execute()
        )
        
        if result.data:
            return result.data[0]
        
        return None
    
    # ==========================================
    # COMBINED OPERATIONS
    # ==========================================
    
    async def get_full_book(self, story_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a complete book with story data and all pages.
        
        This is the main method used by the print service.
        
        Args:
            story_id: UUID of the story (same as book_id)
            
        Returns:
            Combined book data with pages, or None if not found
        """
        story = await self.get_story(story_id)
        
        if not story:
            return None
        
        pages = await self.get_pages(story_id)
        
        # Transform to the format expected by PrintService
        return {
            "book_id": story["id"],
            "title": f"{story['child_name']}'s {story['theme'].title()} Adventure",
            "child_name": story["child_name"],
            "child_age": story["child_age"],
            "theme": story["theme"],
            "photo_url": story.get("photo_url"),
            "pages": [
                {
                    "page_number": p["page_number"],
                    "text": p["text_content"],
                    "scene_description": p["image_prompt"],
                    "image_url": p["image_url"]
                }
                for p in pages
            ],
            "preview_images": [p["image_url"] for p in pages if p.get("image_url")],
            "page_count": len(pages),
            "created_at": story["created_at"],
            # Character bible would need to be reconstructed or stored
            "character_bible": self._build_character_bible_from_story(story, pages)
        }
    
    def _build_character_bible_from_story(
        self, 
        story: Dict[str, Any],
        pages: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """
        Reconstruct character bible from story data.
        
        The image_prompt in pages contains the character description,
        so we extract it from the first page.
        """
        main_char_desc = ""
        
        if pages and pages[0].get("image_prompt"):
            # The prompt contains the character description at the start
            prompt = pages[0]["image_prompt"]
            # Extract description before "Scene:"
            if "Scene:" in prompt:
                main_char_desc = prompt.split("Scene:")[0].strip()
            else:
                main_char_desc = prompt[:200]  # Fallback
        
        return {
            "main_character": main_char_desc,
            "main_character_short": f"{story['child_name']}, {story['child_age']}-year-old",
            "additional_characters": []
        }


    # ==========================================
    # ORDER OPERATIONS
    # ==========================================

    async def create_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new order.

        Args:
            order_data: Complete order data dict

        Returns:
            The created order record
        """
        if not self._client:
            raise ValueError("Database not configured")

        result = self._client.table("orders").insert(order_data).execute()

        if result.data:
            logger.info(f"Created order: {result.data[0]['id']}")
            return result.data[0]

        raise Exception("Failed to create order")

    async def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """
        Get an order by ID.

        Args:
            order_id: UUID of the order

        Returns:
            Order data or None if not found
        """
        if not self._client:
            raise ValueError("Database not configured")

        result = self._client.table("orders").select("*").eq("id", order_id).execute()

        return result.data[0] if result.data else None

    async def get_order_by_shopify_id(
        self,
        shopify_order_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get order by Shopify order ID.

        Args:
            shopify_order_id: Shopify's order ID

        Returns:
            Order data or None if not found
        """
        if not self._client:
            raise ValueError("Database not configured")

        result = (
            self._client.table("orders")
            .select("*")
            .eq("shopify_order_id", shopify_order_id)
            .execute()
        )

        return result.data[0] if result.data else None

    async def update_order(
        self,
        order_id: str,
        updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Update an order.

        Args:
            order_id: UUID of the order
            updates: Fields to update

        Returns:
            Updated order data
        """
        if not self._client:
            raise ValueError("Database not configured")

        updates["updated_at"] = datetime.utcnow().isoformat()

        result = (
            self._client.table("orders")
            .update(updates)
            .eq("id", order_id)
            .execute()
        )

        return result.data[0] if result.data else None

    async def get_orders_by_customer(
        self,
        customer_email: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get orders for a customer by email.

        Args:
            customer_email: Customer's email address
            limit: Maximum number of orders to return

        Returns:
            List of orders, newest first
        """
        if not self._client:
            raise ValueError("Database not configured")

        result = (
            self._client.table("orders")
            .select("*")
            .eq("customer_email", customer_email)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )

        return result.data or []

    async def get_orders_by_status(
        self,
        status: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get orders by status.

        Args:
            status: Order status to filter by
            limit: Maximum number of orders to return

        Returns:
            List of matching orders
        """
        if not self._client:
            raise ValueError("Database not configured")

        result = (
            self._client.table("orders")
            .select("*")
            .eq("status", status)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )

        return result.data or []

    async def get_order_with_book(
        self,
        order_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get order with associated book data.

        Args:
            order_id: UUID of the order

        Returns:
            Order with embedded book data, or None
        """
        order = await self.get_order(order_id)

        if not order:
            return None

        book = await self.get_full_book(order["story_id"])

        return {
            **order,
            "book": book
        }


# Global instance
_db_service: Optional[DatabaseService] = None


def get_database() -> DatabaseService:
    """Get the database service singleton."""
    global _db_service
    if _db_service is None:
        _db_service = DatabaseService()
    return _db_service
