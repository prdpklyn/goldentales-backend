# app/routers/v2/preview.py
"""
GoldenTales V2 Preview Router
===============================
Fast preview generation endpoints for the Kids 60s Magic Preview flow.

These endpoints are PUBLIC and only require API key authentication (not JWT).
"""

from typing import Dict, Optional
from fastapi import APIRouter, HTTPException, Depends, Header

from app.models.requests import QuickPreviewRequest, PreviewRegenerateRequest, ExtendPreviewRequest
from app.models.responses import QuickPreviewResponse, PreviewRegenerateResponse, ExtendPreviewResponse
from app.services.preview_service import PreviewService
from app.middleware.auth import APIKeyData, get_api_key_validator
from app.utils.logging import get_logger
from app.utils.exceptions import ValidationException, ExternalServiceException

logger = get_logger(__name__)

router = APIRouter(prefix="/preview", tags=["Preview"])


async def require_api_key(x_api_key: Optional[str] = Header(None)) -> APIKeyData:
    """
    Dependency to validate API key from X-API-Key header.

    Preview endpoints are public and only require API key (not JWT).
    """
    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Include X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"}
        )

    validator = get_api_key_validator()
    api_key_data = await validator.validate(x_api_key)

    if not api_key_data:
        raise HTTPException(
            status_code=401,
            detail="Invalid or inactive API key",
            headers={"WWW-Authenticate": "ApiKey"}
        )

    return api_key_data


@router.post("/quick", response_model=QuickPreviewResponse)
async def quick_preview(
    request: QuickPreviewRequest,
    api_key: APIKeyData = Depends(require_api_key)
) -> QuickPreviewResponse:
    """
    Generate a quick preview (cover + hero portrait + 2 spreads) in under 60 seconds.

    This endpoint generates a minimal preview to give users a feel for the book
    before they provide full character details or upload photos.

    **Authentication**: Requires X-API-Key header

    **Performance**: Must complete in < 60 seconds
    - Cover generation: ~15s
    - Hero portrait: ~10s
    - 2 spreads: ~15s each
    - Buffer: ~5s

    Args:
        request: Quick preview request with minimal character info
        api_key: Validated API key data

    Returns:
        QuickPreviewResponse with preview data

    Raises:
        401: Missing or invalid API key
        400: Invalid request or validation failed
        503: AI service temporarily unavailable
        500: Internal server error
    """
    logger.info(f"Quick preview requested for {request.child_name} (session: {request.session_id})")

    try:
        service = PreviewService()
        result = await service.generate_quick_preview(
            child_name=request.child_name,
            child_gender=request.child_gender,
            age_band=request.age_band,
            theme=request.theme,
            photo_url=request.photo_url,
            session_id=request.session_id
        )

        logger.info(f"Quick preview generated: {result['preview_id']}")

        return QuickPreviewResponse(**result)

    except ValidationException as e:
        logger.warning(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except ExternalServiceException as e:
        logger.error(f"External service error: {e}")
        if e.is_transient:
            raise HTTPException(status_code=503, detail="AI service temporarily unavailable. Please try again.")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error generating quick preview: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate preview")


@router.post("/regenerate", response_model=PreviewRegenerateResponse)
async def regenerate_preview(
    request: PreviewRegenerateRequest,
    api_key: APIKeyData = Depends(require_api_key)
) -> PreviewRegenerateResponse:
    """
    Quickly regenerate preview with user tweaks applied.

    **Authentication**: Requires X-API-Key header

    **Performance**: Must complete in < 15 seconds
    - Only regenerates hero + 2 spreads
    - Uses existing prompts with tweaks applied

    **Tweaks**:
    - `tone`: funny, gentle, adventurous
    - `art_modifier`: softer, brighter, detailed
    - `sidekick`: dog, unicorn, robot, none

    Args:
        request: Regeneration request with preview_id and tweaks
        api_key: Validated API key data

    Returns:
        PreviewRegenerateResponse with updated preview

    Raises:
        401: Missing or invalid API key
        404: Preview not found or expired
        400: Invalid request
        500: Regeneration failed
    """
    logger.info(f"Preview regeneration requested: {request.preview_id}")

    try:
        service = PreviewService()
        result = await service.regenerate_preview(
            preview_id=request.preview_id,
            character_reference_url=request.character_reference_url,
            tweaks=request.tweaks
        )

        logger.info(f"Preview regenerated: {request.preview_id}")

        return PreviewRegenerateResponse(**result)

    except ValidationException as e:
        logger.warning(f"Validation error: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except ExternalServiceException as e:
        logger.error(f"External service error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error regenerating preview: {e}")
        raise HTTPException(status_code=500, detail="Failed to regenerate preview")


@router.get("/{preview_id}")
async def get_preview_status(
    preview_id: str,
    api_key: APIKeyData = Depends(require_api_key)
) -> Dict:
    """
    Get the status of a preview session.

    **Authentication**: Requires X-API-Key header

    Args:
        preview_id: Preview session ID
        api_key: Validated API key data

    Returns:
        Preview session details

    Raises:
        401: Missing or invalid API key
        404: Preview not found or expired
    """
    logger.info(f"Getting preview status: {preview_id}")

    try:
        service = PreviewService()
        session = service.get_preview_session(preview_id)

        if not session:
            raise HTTPException(status_code=404, detail="Preview not found or expired")

        return {
            "preview_id": session["preview_id"],
            "child_name": session["child_name"],
            "theme": session["theme"],
            "created_at": session["created_at"],
            "expires_at": session["expires_at"],
            "cover_url": session["cover_url"],
            "hero_url": session["hero_url"],
            "is_placeholder": session["is_placeholder"]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting preview status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get preview status")


@router.post("/{preview_id}/extend", response_model=ExtendPreviewResponse)
async def extend_preview_to_book(
    preview_id: str,
    request: ExtendPreviewRequest,
    api_key: APIKeyData = Depends(require_api_key)
) -> ExtendPreviewResponse:
    """
    Extend a 2-page preview to a full 10-page book.

    **Authentication**: Requires X-API-Key header

    **Performance**: May take 2-5 minutes for full generation

    **Story Continuation**:
    - `regenerate_story=false` (default): Continues the existing preview story to 10 pages
    - `regenerate_story=true`: Generates an entirely new 10-page story with the same character

    **Features**:
    - Maintains character consistency using the preview's character_bible
    - Optional photo upload for enhanced hero portrait
    - High-quality (2048x2048) images for print
    - Configurable page count (3-20 pages)
    - Optional occasion and special details

    Args:
        preview_id: Preview session ID from /api/v2/preview/quick
        request: Extension parameters (photo_url, regenerate_story, etc.)
        api_key: Validated API key data

    Returns:
        ExtendPreviewResponse with complete book data

    Raises:
        401: Missing or invalid API key
        404: Preview not found or expired
        400: Invalid request parameters
        500: Generation failed

    Example:
        POST /api/v2/preview/{preview_id}/extend
        {
            "photo_url": "https://example.com/photo.jpg",
            "regenerate_story": false,
            "target_pages": 10,
            "occasion": "Birthday gift",
            "special_details": "Include a rainbow unicorn friend"
        }
    """
    logger.info(f"Extending preview {preview_id} to book (API key: {api_key.key_id})")

    try:
        service = PreviewService()
        result = await service.extend_preview_to_book(
            preview_id=preview_id,
            photo_url=request.photo_url,
            regenerate_story=request.regenerate_story,
            target_pages=request.target_pages,
            occasion=request.occasion,
            special_details=request.special_details
        )

        logger.info(f"Successfully extended preview {preview_id} to book {result['book_id']}")

        return ExtendPreviewResponse(**result)

    except ValidationException as e:
        logger.warning(f"Validation error: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except ExternalServiceException as e:
        logger.error(f"External service error: {e}")
        if e.is_transient:
            raise HTTPException(status_code=503, detail="AI service temporarily unavailable. Please try again.")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error extending preview: {e}")
        raise HTTPException(status_code=500, detail="Failed to extend preview to book")
