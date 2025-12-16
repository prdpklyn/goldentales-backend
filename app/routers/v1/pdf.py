# app/routers/v1/pdf.py
"""
GoldenTales PDF Router v1
=========================
API v1 endpoints for PDF data retrieval and generation.
"""

from typing import Dict
from fastapi import APIRouter, HTTPException, Query

from app.utils.logging import get_logger
from app.utils.exceptions import NotFoundException, ExternalServiceException
from app.services.pdf_data_service import get_pdf_data_service
from app.models.pdf_models import (
    GetStoryForPDFRequest,
    StoryForPDFResponse,
    PDFBookData
)

logger = get_logger(__name__)

router = APIRouter()


@router.post("/story", response_model=StoryForPDFResponse)
async def get_story_for_pdf(request: GetStoryForPDFRequest) -> StoryForPDFResponse:
    """
    Get story data for PDF generation.
    
    Fetches complete story and page data from Supabase Edge Function
    for use in PDF generation.
    
    Args:
        request: Request containing story_id
        
    Returns:
        StoryForPDFResponse with story metadata and all pages
        
    Raises:
        404: Story not found
        502: External service error
        500: Internal server error
    """
    logger.info(f"[v1] Fetching story for PDF: {request.story_id}")
    
    try:
        service = get_pdf_data_service()
        response = await service.get_story_for_pdf(request.story_id)
        
        logger.info(
            f"Story fetched successfully: {response.data.story.child_name}'s story, "
            f"{len(response.data.pages)} pages"
        )
        
        return response
        
    except NotFoundException as e:
        logger.warning(f"Story not found: {request.story_id}")
        raise HTTPException(status_code=404, detail=str(e))
    except ExternalServiceException as e:
        logger.error(f"External service error: {e}")
        raise HTTPException(status_code=502, detail=str(e))
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error fetching story: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch story data")


@router.get("/story/{story_id}", response_model=StoryForPDFResponse)
async def get_story_for_pdf_by_id(story_id: str) -> StoryForPDFResponse:
    """
    Get story data for PDF generation by story ID (GET method).
    
    Alternative to POST endpoint for simple retrieval.
    
    Args:
        story_id: UUID of the story to fetch
        
    Returns:
        StoryForPDFResponse with story metadata and all pages
    """
    request = GetStoryForPDFRequest(story_id=story_id)
    return await get_story_for_pdf(request)


@router.get("/story/{story_id}/book-data")
async def get_pdf_book_data(story_id: str) -> Dict:
    """
    Get story data formatted for PDF generation.
    
    Returns a simplified structure optimized for the PDF generator,
    with pages sorted by page_number and character bible extracted.
    
    Args:
        story_id: UUID of the story to fetch
        
    Returns:
        PDFBookData structure ready for PDF generation
    """
    logger.info(f"[v1] Fetching PDF book data: {story_id}")
    
    try:
        service = get_pdf_data_service()
        book_data = await service.get_pdf_book_data(story_id)
        
        return book_data.model_dump()
        
    except NotFoundException as e:
        logger.warning(f"Story not found: {story_id}")
        raise HTTPException(status_code=404, detail=str(e))
    except ExternalServiceException as e:
        logger.error(f"External service error: {e}")
        raise HTTPException(status_code=502, detail=str(e))
    except ValueError as e:
        logger.error(f"Error processing story data: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch PDF book data")


@router.get("/story/{story_id}/validate")
async def validate_story_for_pdf(story_id: str) -> Dict:
    """
    Validate that a story is ready for PDF generation.
    
    Checks:
    - Story exists and has status "ready"
    - All pages have images
    - Required metadata is present
    
    Args:
        story_id: UUID of the story to validate
        
    Returns:
        Validation result with ready status and any issues found
    """
    logger.info(f"[v1] Validating story for PDF: {story_id}")
    
    try:
        service = get_pdf_data_service()
        
        response = await service.get_story_for_pdf(story_id)
        
        issues = []
        
        if not response.success or not response.data:
            return {
                "story_id": story_id,
                "ready": False,
                "issues": ["Failed to fetch story data"]
            }
        
        story = response.data.story
        pages = response.data.pages
        
        # Check story status
        if story.status != "ready":
            issues.append(f"Story status is '{story.status}', expected 'ready'")
        
        # Check pages exist
        if not pages:
            issues.append("No pages found")
        else:
            # Check for missing images
            missing_images = [p.page_number for p in pages if not p.image_url]
            if missing_images:
                issues.append(f"Missing images for pages: {missing_images}")
            
            # Check page sequence
            page_numbers = sorted([p.page_number for p in pages])
            expected = list(range(1, len(pages) + 1))
            if page_numbers != expected:
                issues.append(f"Page sequence issue: expected {expected}, got {page_numbers}")
        
        # Check cover image
        if not story.cover_image_url:
            issues.append("No cover image URL")
        
        is_ready = len(issues) == 0
        
        result = {
            "story_id": story_id,
            "ready": is_ready,
            "child_name": story.child_name,
            "theme": story.theme,
            "page_count": len(pages) if pages else 0,
            "status": story.status
        }
        
        if issues:
            result["issues"] = issues
        
        logger.info(f"Validation result for {story_id}: ready={is_ready}")
        return result
        
    except NotFoundException:
        return {
            "story_id": story_id,
            "ready": False,
            "issues": ["Story not found"]
        }
    except Exception as e:
        logger.error(f"Error validating story: {e}")
        return {
            "story_id": story_id,
            "ready": False,
            "issues": [f"Validation error: {str(e)}"]
        }


@router.get("/story/{story_id}/pages")
async def get_story_pages(
    story_id: str,
    current_only: bool = Query(True, description="Only return current versions of pages")
) -> Dict:
    """
    Get just the pages data for a story.
    
    Useful for preview or when only page content is needed.
    
    Args:
        story_id: UUID of the story
        current_only: If True, only returns pages where is_current=True
        
    Returns:
        List of pages with text content and image URLs
    """
    logger.info(f"[v1] Fetching pages for story: {story_id}")
    
    try:
        service = get_pdf_data_service()
        response = await service.get_story_for_pdf(story_id)
        
        pages = response.data.pages
        
        # Filter to current versions if requested
        if current_only:
            pages = [p for p in pages if p.is_current]
        
        # Sort by page number
        pages = sorted(pages, key=lambda p: p.page_number)
        
        return {
            "story_id": story_id,
            "page_count": len(pages),
            "pages": [
                {
                    "page_number": p.page_number,
                    "text_content": p.text_content,
                    "image_url": p.image_url,
                    "version": p.version,
                    "is_current": p.is_current
                }
                for p in pages
            ]
        }
        
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching pages: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch pages")

