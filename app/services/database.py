# app/services/database.py
"""
GoldenTales Database Service
============================
Database operations via Supabase Edge Functions.

This service now uses Edge Functions for all database operations,
replacing direct Supabase client calls to comply with architectural constraints.
"""

import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime

from app.services.database_edge_service import get_database_edge_service, DatabaseEdgeService
from app.settings import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


class DatabaseService:
    """
    Service for interacting with Supabase database via Edge Functions.
    
    All database operations go through Supabase Edge Functions,
    not direct database connections. This ensures proper security,
    RLS policies, and architectural compliance.
    
    Tables (accessed via Edge Functions):
    - stories: Main story/book data
    - pages: Individual pages with text and images
    - orders: Order records
    """
    
    _instance: Optional["DatabaseService"] = None
    _edge_service: Optional[DatabaseEdgeService] = None
    
    def __new__(cls):
        """Singleton pattern for database service."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize Database Service with Edge Functions."""
        if self._edge_service is None:
            if not settings.supabase_url:
                logger.warning("Supabase URL not configured")
                return
            
            if not settings.supabase_pdf_api_key:
                logger.warning("Supabase API key not configured")
                return
            
            self._edge_service = get_database_edge_service()
            logger.info("DatabaseService initialized with Edge Functions")
    
    @property
    def client(self) -> Optional[DatabaseEdgeService]:
        """
        Get the Edge Function service.
        
        Note: This property is maintained for backwards compatibility,
        but now returns the Edge Function service instead of direct client.
        """
        return self._edge_service
    
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
        user_id: Optional[str] = None,
        auth_token: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a new story via Edge Function.
        
        Args:
            user_id: Optional user ID (required for RLS if not using auth_token)
            auth_token: Optional JWT token for RLS
        
        Returns:
            The created story record with id.
        """
        if not self._edge_service:
            raise ValueError("Database not configured")
        
        # user_id is required for RLS - use a default if not provided (dev mode)
        if not user_id:
            user_id = str(uuid.uuid4())
            logger.warning(f"No user_id provided to create_story, using temporary ID: {user_id}")
        
        return await self._edge_service.create_story(
            user_id=user_id,
            child_name=child_name,
            child_age=child_age,
            theme=theme,
            photo_url=photo_url,
            siblings=siblings,
            favorite_characters=favorite_characters,
            pets=pets,
            parents=parents,
            friends=friends,
            auth_token=auth_token,
            **kwargs
        )
    
    async def get_story(self, story_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a story by ID via Edge Function.
        
        Args:
            story_id: UUID of the story
            
        Returns:
            Story data or None if not found
        """
        if not self._edge_service:
            raise ValueError("Database not configured")
        
        return await self._edge_service.get_story(story_id)
    
    async def update_story(
        self, 
        story_id: str, 
        updates: Dict[str, Any],
        auth_token: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Update a story via Edge Function.
        
        Args:
            story_id: UUID of the story
            updates: Fields to update
            auth_token: Optional JWT token for RLS
        """
        if not self._edge_service:
            raise ValueError("Database not configured")
        
        return await self._edge_service.update_story(story_id, updates, auth_token=auth_token)
    
    # ==========================================
    # PAGE OPERATIONS
    # ==========================================
    
    async def create_page(
        self,
        story_id: str,
        page_number: int,
        text_content: str,
        image_prompt: str,
        image_url: Optional[str] = None,
        auth_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a page for a story via Edge Function.
        
        Args:
            story_id: UUID of the parent story
            page_number: Page number (1-indexed)
            text_content: The story text for this page
            image_prompt: The prompt used to generate the image
            image_url: URL of the generated image
            auth_token: Optional JWT token for RLS
            
        Returns:
            The created page record
        """
        if not self._edge_service:
            raise ValueError("Database not configured")
        
        return await self._edge_service.create_page(
            story_id=story_id,
            page_number=page_number,
            text_content=text_content,
            image_prompt=image_prompt,
            image_url=image_url,
            auth_token=auth_token
        )
    
    async def get_pages(self, story_id: str) -> List[Dict[str, Any]]:
        """
        Get all pages for a story via Edge Function, ordered by page_number.
        
        Args:
            story_id: UUID of the story
            
        Returns:
            List of page records
        """
        if not self._edge_service:
            raise ValueError("Database not configured")
        
        return await self._edge_service.get_pages(story_id)
    
    async def update_page(
        self,
        page_id: str,
        updates: Dict[str, Any],
        auth_token: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Update a page via Edge Function.
        
        Args:
            page_id: UUID of the page
            updates: Fields to update
            auth_token: Optional JWT token for RLS
        """
        if not self._edge_service:
            raise ValueError("Database not configured")
        
        return await self._edge_service.update_page(page_id, updates, auth_token=auth_token)
    
    async def get_page_by_number(
        self,
        story_id: str,
        page_number: int
    ) -> Optional[Dict[str, Any]]:
        """Get a specific page by story_id and page_number via Edge Function."""
        if not self._edge_service:
            raise ValueError("Database not configured")
        
        return await self._edge_service.get_page_by_number(story_id, page_number)
    
    # ==========================================
    # COMBINED OPERATIONS
    # ==========================================
    
    async def get_full_book(self, story_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a complete book with story data and all pages via Edge Functions.
        
        This is the main method used by the print service.
        
        Args:
            story_id: UUID of the story (same as book_id)
            
        Returns:
            Combined book data with pages, or None if not found
        """
        if not self._edge_service:
            raise ValueError("Database not configured")
        
        return await self._edge_service.get_full_book(story_id)


    # ==========================================
    # ORDER OPERATIONS
    # ==========================================

    async def create_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new order via Edge Function.

        Args:
            order_data: Complete order data dict

        Returns:
            The created order record
        """
        if not self._edge_service:
            raise ValueError("Database not configured")

        return await self._edge_service.create_order(order_data)

    async def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """
        Get an order by ID via Edge Function.

        Args:
            order_id: UUID of the order

        Returns:
            Order data or None if not found
        """
        if not self._edge_service:
            raise ValueError("Database not configured")

        return await self._edge_service.get_order(order_id)

    async def get_order_by_shopify_id(
        self,
        shopify_order_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get order by Shopify order ID via Edge Function.

        Args:
            shopify_order_id: Shopify's order ID

        Returns:
            Order data or None if not found
        """
        if not self._edge_service:
            raise ValueError("Database not configured")

        return await self._edge_service.get_order_by_shopify_id(shopify_order_id)

    async def update_order(
        self,
        order_id: str,
        updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Update an order via Edge Function.

        Args:
            order_id: UUID of the order
            updates: Fields to update

        Returns:
            Updated order data
        """
        if not self._edge_service:
            raise ValueError("Database not configured")

        return await self._edge_service.update_order(order_id, updates)

    async def get_orders_by_customer(
        self,
        customer_email: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get orders for a customer by email via Edge Function.

        Args:
            customer_email: Customer's email address
            limit: Maximum number of orders to return

        Returns:
            List of orders, newest first
        """
        if not self._edge_service:
            raise ValueError("Database not configured")

        return await self._edge_service.get_orders_by_customer(customer_email, limit)

    async def get_orders_by_status(
        self,
        status: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get orders by status via Edge Function.

        Args:
            status: Order status to filter by
            limit: Maximum number of orders to return

        Returns:
            List of matching orders
        """
        if not self._edge_service:
            raise ValueError("Database not configured")

        return await self._edge_service.get_orders_by_status(status, limit)

    async def get_order_with_book(
        self,
        order_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get order with associated book data via Edge Functions.

        Args:
            order_id: UUID of the order

        Returns:
            Order with embedded book data, or None
        """
        if not self._edge_service:
            raise ValueError("Database not configured")

        return await self._edge_service.get_order_with_book(order_id)


# Global instance
_db_service: Optional[DatabaseService] = None


def get_database() -> DatabaseService:
    """Get the database service singleton."""
    global _db_service
    if _db_service is None:
        _db_service = DatabaseService()
    return _db_service
