# app/services/database_edge_service.py
"""
GoldenTales Database Edge Service
==================================
Database operations via Supabase Edge Functions.

This replaces direct database access with Edge Function calls,
following the architectural constraint that all database operations
must go through Supabase Edge Functions.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime

from app.services.edge_function_client import EdgeFunctionClient
from app.utils.logging import get_logger
from app.settings import settings

logger = get_logger(__name__)


class DatabaseEdgeService:
    """
    Service for database operations via Supabase Edge Functions.
    
    All database access goes through Edge Functions, not direct database connections.
    This ensures proper security, RLS policies, and architectural compliance.
    
    Example:
        service = DatabaseEdgeService()
        story = await service.create_story(
            child_name="Emma",
            child_age=6,
            theme="christmas"
        )
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None
    ):
        """
        Initialize Database Edge Service.
        
        Args:
            base_url: Supabase base URL (defaults to settings)
            api_key: API key for authentication (defaults to settings)
        """
        self.base_url = base_url or settings.supabase_url
        self.api_key = api_key or settings.supabase_pdf_api_key
        
        # Initialize Edge Function clients for each operation
        self._clients = {
            "create-story": EdgeFunctionClient("create-story", self.base_url, self.api_key),
            "get-story": EdgeFunctionClient("get-story", self.base_url, self.api_key),
            "update-story": EdgeFunctionClient("update-story", self.base_url, self.api_key),
            "create-page": EdgeFunctionClient("create-page", self.base_url, self.api_key),
            "get-pages": EdgeFunctionClient("get-pages", self.base_url, self.api_key),
            "update-page": EdgeFunctionClient("update-page", self.base_url, self.api_key),
            "create-order": EdgeFunctionClient("create-order", self.base_url, self.api_key),
            "get-order": EdgeFunctionClient("get-order", self.base_url, self.api_key),
            "update-order": EdgeFunctionClient("update-order", self.base_url, self.api_key),
            "get-orders-by-status": EdgeFunctionClient("get-orders-by-status", self.base_url, self.api_key),
            "get-orders-by-customer": EdgeFunctionClient("get-orders-by-customer", self.base_url, self.api_key),
        }
    
    # ==========================================
    # STORY OPERATIONS
    # ==========================================
    
    def _normalize_status_for_db(self, status: Optional[str]) -> Optional[str]:
        """
        Map application statuses to database-allowed statuses.

        DB constraint allows: draft, generating, ready, failed.
        The app uses 'preview' to indicate a pre-final state; map it to 'ready'
        to satisfy the constraint while preserving downstream behavior.
        """
        if status is None:
            return None

        if status == "preview":
            logger.debug("Mapped 'preview' status to 'ready' for database compatibility")
            return "ready"

        return status

    async def create_story(
        self,
        user_id: str,
        child_name: str,
        child_age: int,
        theme: str,
        photo_url: Optional[str] = None,
        siblings: Optional[str] = None,
        favorite_characters: Optional[str] = None,
        pets: Optional[str] = None,
        parents: Optional[str] = None,
        friends: Optional[str] = None,
        auth_token: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a new story via Edge Function.
        
        Args:
            user_id: UUID of the user creating the story (required for RLS)
            child_name: Name of the child
            child_age: Age of the child
            theme: Story theme
            photo_url: Optional photo URL
            siblings: Optional siblings info
            favorite_characters: Optional favorite characters
            pets: Optional pets info
            parents: Optional parents info
            friends: Optional friends info
            auth_token: Optional JWT token for RLS (if provided, forwarded to Edge Function)
            **kwargs: Additional fields
            
        Returns:
            The created story record with id
        """
        payload = {
            "user_id": user_id,  # Required by OpenAPI spec and RLS
            "child_name": child_name,
            "child_age": child_age,
            "theme": theme,
            "photo_url": photo_url,
            "siblings": siblings,
            "favorite_characters": favorite_characters,
            "pets": pets,
            "parents": parents,
            "friends": friends,
            **kwargs
        }

        # Normalize status if provided via kwargs
        if "status" in payload:
            payload["status"] = self._normalize_status_for_db(payload.get("status"))
        
        response = await self._clients["create-story"].call(payload, auth_token=auth_token)
        
        if response.get("success"):
            logger.info(f"Created story via Edge Function: {response.get('data', {}).get('id')}")
            return response.get("data", {})
        else:
            error_msg = response.get("error", "Failed to create story")
            logger.error(f"Edge Function create-story failed: {error_msg}")
            raise Exception(error_msg)
    
    async def get_story(self, story_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a story by ID via Edge Function.
        
        Args:
            story_id: UUID of the story
            
        Returns:
            Story data or None if not found
        """
        try:
            response = await self._clients["get-story"].call({"story_id": story_id})
            
            if response.get("success"):
                logger.info(f"Retrieved story via Edge Function: {story_id}")
                return response.get("data")
            else:
                logger.warning(f"Story {story_id} not found")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching story {story_id} via Edge Function: {e}")
            raise
    
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
            auth_token: Optional JWT token for RLS (if provided, forwarded to Edge Function)
            
        Returns:
            Updated story data or None if not found
        """
        # Valid fields in the stories table (based on schema)
        VALID_STORY_FIELDS = {
            "child_name", "child_age", "theme", "art_style", "character_json",
            "gender", "skin_tone", "hair_color", "hair_style", "eye_color",
            "occasion", "special_details", "photo_url", "status", "cover_image_url",
            "error_json", "tier", "is_photo_based", "character_reference_url",
            "siblings", "favorite_characters", "pets", "parents", "friends"
        }
        
        # Immutable fields that cannot be updated
        IMMUTABLE_FIELDS = {"id", "user_id", "created_at", "updated_at"}
        
        # Map character_bible to character_json (database field name)
        # The codebase uses 'character_bible' but database uses 'character_json'
        normalized_updates = updates.copy()
        if "character_bible" in normalized_updates:
            normalized_updates["character_json"] = normalized_updates.pop("character_bible")
            logger.debug("Mapped character_bible to character_json for database update")
            
        # Map V2 'preview' status to database 'ready' status (constraint-safe)
        if "status" in normalized_updates:
            normalized_updates["status"] = self._normalize_status_for_db(normalized_updates.get("status"))
        
        # Filter out invalid fields
        filtered_updates = {}
        invalid_fields = []
        for key, value in normalized_updates.items():
            if key in IMMUTABLE_FIELDS:
                logger.warning(f"Skipping immutable field '{key}' in update for story {story_id}")
                continue
            elif key not in VALID_STORY_FIELDS:
                invalid_fields.append(key)
                logger.warning(f"Skipping invalid field '{key}' in update for story {story_id}")
                continue
            else:
                # Ensure JSONB fields are properly formatted (dict/list, not string)
                if key in ("character_json", "error_json") and isinstance(value, str):
                    try:
                        import json
                        value = json.loads(value)
                    except json.JSONDecodeError:
                        logger.error(f"Invalid JSON string for field '{key}' in story {story_id}")
                        continue
                # Ensure status respects DB constraint
                if key == "status":
                    value = self._normalize_status_for_db(value)
                filtered_updates[key] = value
        
        if invalid_fields:
            logger.warning(
                f"Filtered out {len(invalid_fields)} invalid fields for story {story_id}: {invalid_fields}"
            )
        
        if not filtered_updates:
            logger.error(f"No valid fields to update for story {story_id}")
            return None
        
        payload = {
            "story_id": story_id,
            "updates": filtered_updates
        }
        
        logger.debug(
            f"Updating story {story_id} with {len(filtered_updates)} fields: {list(filtered_updates.keys())}"
        )
        
        try:
            response = await self._clients["update-story"].call(payload, auth_token=auth_token)
            
            if response.get("success"):
                logger.info(f"Updated story via Edge Function: {story_id}")
                return response.get("data")
            else:
                error_msg = response.get("error", "Unknown error")
                error_code = response.get("error_code", "unknown")
                logger.error(
                    f"Failed to update story {story_id}: {error_msg} (code: {error_code})",
                    extra={
                        "story_id": story_id,
                        "updates": list(filtered_updates.keys()),
                        "invalid_fields": invalid_fields
                    }
                )
                return None
        except Exception as e:
            logger.error(
                f"Exception updating story {story_id} via Edge Function: {e}",
                extra={
                    "story_id": story_id,
                    "updates": list(filtered_updates.keys()),
                    "invalid_fields": invalid_fields
                }
            )
            raise
    
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
            auth_token: Optional JWT token for RLS (if provided, forwarded to Edge Function)
            
        Returns:
            The created page record
        """
        payload = {
            "story_id": story_id,
            "page_number": page_number,
            "text_content": text_content,
            "image_prompt": image_prompt,
            "image_url": image_url
        }
        
        response = await self._clients["create-page"].call(payload, auth_token=auth_token)
        
        if response.get("success"):
            logger.info(f"Created page {page_number} for story {story_id} via Edge Function")
            return response.get("data", {})
        else:
            error_msg = response.get("error", f"Failed to create page {page_number}")
            logger.error(f"Edge Function create-page failed: {error_msg}")
            raise Exception(error_msg)
    
    async def get_pages(self, story_id: str) -> List[Dict[str, Any]]:
        """
        Get all pages for a story via Edge Function.
        
        Args:
            story_id: UUID of the story
            
        Returns:
            List of page records ordered by page_number
        """
        response = await self._clients["get-pages"].call({"story_id": story_id})
        
        if response.get("success"):
            return response.get("data", [])
        else:
            logger.warning(f"Failed to get pages for story {story_id}")
            return []
    
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
            
        Returns:
            Updated page data or None if failed
        """
        payload = {
            "page_id": page_id,
            "updates": updates
        }
        
        response = await self._clients["update-page"].call(payload, auth_token=auth_token)
        
        if response.get("success"):
            return response.get("data")
        return None
    
    async def get_page_by_number(
        self,
        story_id: str,
        page_number: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get a specific page by story_id and page_number via Edge Function.
        
        Args:
            story_id: UUID of the story
            page_number: Page number to retrieve
            
        Returns:
            Page data or None if not found
        """
        pages = await self.get_pages(story_id)
        
        for page in pages:
            if page.get("page_number") == page_number:
                return page
        
        return None
    
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
            "character_bible": self._build_character_bible_from_story(story, pages)
        }
    
    def _build_character_bible_from_story(
        self,
        story: Dict[str, Any],
        pages: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """
        Reconstruct character bible from story data.
        
        The image_prompt in pages contains the character description.
        """
        main_char_desc = ""
        
        if pages and pages[0].get("image_prompt"):
            prompt = pages[0]["image_prompt"]
            if "Scene:" in prompt:
                main_char_desc = prompt.split("Scene:")[0].strip()
            else:
                main_char_desc = prompt[:200]
        
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
        Create a new order via Edge Function.
        
        Args:
            order_data: Complete order data dict
            
        Returns:
            The created order record
        """
        response = await self._clients["create-order"].call(order_data)
        
        if response.get("success"):
            logger.info(f"Created order via Edge Function: {response.get('data', {}).get('id')}")
            return response.get("data", {})
        else:
            error_msg = response.get("error", "Failed to create order")
            logger.error(f"Edge Function create-order failed: {error_msg}")
            raise Exception(error_msg)
    
    async def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """
        Get an order by ID via Edge Function.
        
        Args:
            order_id: UUID of the order
            
        Returns:
            Order data or None if not found
        """
        response = await self._clients["get-order"].call({"order_id": order_id})
        
        if response.get("success"):
            return response.get("data")
        return None
    
    async def get_order_by_shopify_id(
        self,
        shopify_order_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get order by Shopify order ID via Edge Function.
        
        Note: This may need a dedicated Edge Function endpoint.
        For now, falls back to get-order with shopify_order_id.
        
        Args:
            shopify_order_id: Shopify's order ID
            
        Returns:
            Order data or None if not found
        """
        response = await self._clients["get-order"].call({"shopify_order_id": shopify_order_id})
        
        if response.get("success"):
            return response.get("data")
        return None
    
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
        updates["updated_at"] = datetime.utcnow().isoformat()
        
        payload = {
            "order_id": order_id,
            "updates": updates
        }
        
        response = await self._clients["update-order"].call(payload)
        
        if response.get("success"):
            return response.get("data")
        return None
    
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
        payload = {
            "customer_email": customer_email,
            "limit": limit
        }
        
        response = await self._clients["get-orders-by-customer"].call(payload)
        
        if response.get("success"):
            return response.get("data", [])
        return []
    
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
        payload = {
            "status": status,
            "limit": limit
        }
        
        response = await self._clients["get-orders-by-status"].call(payload)
        
        if response.get("success"):
            return response.get("data", [])
        return []
    
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
        order = await self.get_order(order_id)
        
        if not order:
            return None
        
        book = await self.get_full_book(order["story_id"])
        
        return {
            **order,
            "book": book
        }


# Global instance
_db_edge_service: Optional[DatabaseEdgeService] = None


def get_database_edge_service() -> DatabaseEdgeService:
    """Get the database edge service singleton."""
    global _db_edge_service
    if _db_edge_service is None:
        _db_edge_service = DatabaseEdgeService()
    return _db_edge_service

