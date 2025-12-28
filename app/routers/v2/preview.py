# app/routers/v2/preview.py
"""
GoldenTales V2 Preview Router
===============================
Fast preview generation endpoints for the Kids 60s Magic Preview flow.
"""

from typing import Dict
from fastapi import APIRouter, HTTPException, Depends

from app.models.requests import QuickPreviewRequest, PreviewRegenerateRequest
from app.models.responses import QuickPreviewResponse, PreviewRegenerateResponse
from app.services.preview_service import PreviewService
from app.middleware.jwt_auth import require_jwt_auth, JWTUser
from app.utils.logging import get_logger
from app.utils.exceptions import ValidationException, ExternalServiceException

logger = get_logger(__name__)

router = APIRouter(prefix="/preview", tags=["Preview"])


@router.post("/quick", response_model=QuickPreviewResponse)
async def quick_preview(
    request: QuickPreviewRequest,
    user: JWTUser = Depends(require_jwt_auth)
) -> QuickPreviewResponse:
    """
    Generate a quick preview (cover + hero portrait + 2 spreads) in under 60 seconds.

    This endpoint generates a minimal preview to give users a feel for the book
    before they provide full character details or upload photos.

    **Performance**: Must complete in < 60 seconds
    - Cover generation: ~15s
    - Hero portrait: ~10s
    - 2 spreads: ~15s each
    - Buffer: ~5s

    Args:
        request: Quick preview request with minimal character info
        user: Authenticated user

    Returns:
        QuickPreviewResponse with preview data

    Raises:
        400: Invalid request or validation failed
        503: AI service temporarily unavailable
        500: Internal server error
    """
    logger.info(f"Quick preview requested by {user.user_id} for {request.child_name}")

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
    user: JWTUser = Depends(require_jwt_auth)
) -> PreviewRegenerateResponse:
    """
    Quickly regenerate preview with user tweaks applied.

    **Performance**: Must complete in < 15 seconds
    - Only regenerates hero + 2 spreads
    - Uses existing prompts with tweaks applied

    **Tweaks**:
    - `tone`: funny, gentle, adventurous
    - `art_modifier`: softer, brighter, detailed
    - `sidekick`: dog, unicorn, robot, none

    Args:
        request: Regeneration request with preview_id and tweaks
        user: Authenticated user

    Returns:
        PreviewRegenerateResponse with updated preview

    Raises:
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
    user: JWTUser = Depends(require_jwt_auth)
) -> Dict:
    """
    Get the status of a preview session.

    Args:
        preview_id: Preview session ID
        user: Authenticated user

    Returns:
        Preview session details

    Raises:
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
