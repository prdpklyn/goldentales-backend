# app/services/pdf_data_service.py
"""
GoldenTales PDF Data Service
============================
Service for fetching story data from Supabase Edge Function for PDF generation.

This service calls the external Supabase Edge Function to retrieve
story and page data needed for PDF generation.
"""

from typing import Optional, Dict, Any
import httpx

from app.settings import settings
from app.utils.logging import get_logger
from app.utils.retry import with_retry
from app.utils.exceptions import ExternalServiceException, NotFoundException
from app.models.pdf_models import (
    StoryForPDFResponse,
    PDFBookData,
    GetStoryForPDFRequest
)

logger = get_logger(__name__)


class PDFDataService:
    """
    Service for fetching story data for PDF generation from Supabase.
    
    Example:
        service = PDFDataService()
        story_data = await service.get_story_for_pdf("8acf211f-43b4-4d11-b8a6-e24f4fb6d8b1")
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None
    ):
        """
        Initialize the PDF data service.
        
        Args:
            base_url: Supabase Edge Function base URL (defaults to settings)
            api_key: API key for authentication (defaults to settings)
        """
        self.base_url = base_url or settings.supabase_url
        self.api_key = api_key or settings.supabase_pdf_api_key
        
        if not self.base_url:
            logger.warning("Supabase URL not configured for PDF data service")
        if not self.api_key:
            logger.warning("PDF API key not configured")
    
    @property
    def endpoint_url(self) -> str:
        """Get the full endpoint URL for get-story-for-pdf."""
        if not self.base_url:
            raise ValueError("Supabase URL not configured")
        # Handle both formats: with or without /functions/v1
        base = self.base_url.rstrip('/')
        if '/functions/v1' not in base:
            return f"{base}/functions/v1/get-story-for-pdf"
        return f"{base}/get-story-for-pdf"
    
    @with_retry(
        max_attempts=3,
        initial_delay=1.0,
        max_delay=15.0,
        circuit_breaker_name="supabase_pdf_api"
    )
    async def _fetch_story_data(self, story_id: str) -> Dict[str, Any]:
        """
        Fetch story data from Supabase Edge Function with retry logic.
        
        Args:
            story_id: UUID of the story to fetch
            
        Returns:
            Raw JSON response from the API
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    self.endpoint_url,
                    headers={
                        "x-api-key": self.api_key,
                        "Content-Type": "application/json"
                    },
                    json={"story_id": story_id}
                )
                
                # Handle specific HTTP errors
                if response.status_code == 404:
                    raise NotFoundException(
                        resource_type="story",
                        resource_id=story_id
                    )
                
                if response.status_code == 401:
                    raise ExternalServiceException(
                        service_name="Supabase PDF API",
                        message="Authentication failed - invalid API key",
                        is_transient=False
                    )
                
                if response.status_code >= 500:
                    raise ExternalServiceException(
                        service_name="Supabase PDF API",
                        message=f"Server error: {response.status_code}",
                        is_transient=True
                    )
                
                response.raise_for_status()
                return response.json()
                
            except httpx.TimeoutException as e:
                raise ExternalServiceException(
                    service_name="Supabase PDF API",
                    message=f"Request timed out: {str(e)}",
                    is_transient=True
                )
            except httpx.RequestError as e:
                raise ExternalServiceException(
                    service_name="Supabase PDF API",
                    message=f"Request failed: {str(e)}",
                    is_transient=True
                )
    
    async def get_story_for_pdf(self, story_id: str) -> StoryForPDFResponse:
        """
        Fetch story data for PDF generation.
        
        Args:
            story_id: UUID of the story to fetch
            
        Returns:
            StoryForPDFResponse with story and pages data
            
        Raises:
            NotFoundException: If story not found
            ExternalServiceException: If API call fails
            ValueError: If configuration is missing
        """
        if not self.base_url or not self.api_key:
            raise ValueError("PDF data service not properly configured")
        
        logger.info(f"Fetching story data for PDF: {story_id}")
        
        raw_data = await self._fetch_story_data(story_id)
        
        # Parse response
        response = StoryForPDFResponse(**raw_data)
        
        if not response.success:
            error_msg = response.error or "Unknown error fetching story"
            logger.error(f"Failed to fetch story {story_id}: {error_msg}")
            raise ExternalServiceException(
                service_name="Supabase PDF API",
                message=error_msg,
                is_transient=False
            )
        
        logger.info(
            f"Successfully fetched story {story_id}: "
            f"{response.data.story.child_name}'s {response.data.story.theme} story, "
            f"{len(response.data.pages)} pages"
        )
        
        return response
    
    async def get_pdf_book_data(self, story_id: str) -> PDFBookData:
        """
        Fetch and convert story data to PDFBookData format.
        
        This is a convenience method that fetches the story and
        converts it to the format expected by the PDF generator.
        
        Args:
            story_id: UUID of the story to fetch
            
        Returns:
            PDFBookData ready for PDF generation
        """
        response = await self.get_story_for_pdf(story_id)
        return PDFBookData.from_story_response(response)
    
    async def validate_story_ready(self, story_id: str) -> bool:
        """
        Check if a story is ready for PDF generation.
        
        Args:
            story_id: UUID of the story to check
            
        Returns:
            True if story is ready, False otherwise
        """
        try:
            response = await self.get_story_for_pdf(story_id)
            
            if not response.success or not response.data:
                return False
            
            story = response.data.story
            pages = response.data.pages
            
            # Check story status
            if story.status != "ready":
                logger.warning(f"Story {story_id} status is '{story.status}', not 'ready'")
                return False
            
            # Check we have pages
            if not pages or len(pages) == 0:
                logger.warning(f"Story {story_id} has no pages")
                return False
            
            # Check all pages have images
            missing_images = [p.page_number for p in pages if not p.image_url]
            if missing_images:
                logger.warning(
                    f"Story {story_id} missing images for pages: {missing_images}"
                )
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating story {story_id}: {e}")
            return False


# ============================================
# SINGLETON INSTANCE
# ============================================

_pdf_data_service: Optional[PDFDataService] = None


def get_pdf_data_service() -> PDFDataService:
    """Get the PDF data service singleton."""
    global _pdf_data_service
    if _pdf_data_service is None:
        _pdf_data_service = PDFDataService()
    return _pdf_data_service

