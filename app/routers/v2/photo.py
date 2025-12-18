# app/routers/v2/photo.py
"""
GoldenTales V2 Photo Router
============================
API endpoints for photo validation and character preview generation.
"""

from typing import Dict
from fastapi import APIRouter, HTTPException, Depends

from app.utils.logging import get_logger
from app.utils.exceptions import ExternalServiceException
from app.services.photo_character_service import get_photo_character_service
from app.middleware.jwt_auth import require_jwt_auth, JWTUser
from app.models.requests import ValidatePhotoRequest, PreviewCharacterRequest
from app.models.responses import (
    PhotoValidationResponse,
    CharacterPreviewResponse,
    ApprovalResponse
)

logger = get_logger(__name__)

router = APIRouter(prefix="/photo", tags=["Photo Character"])


@router.post("/validate", response_model=PhotoValidationResponse)
async def validate_photo(
    request: ValidatePhotoRequest,
    user: JWTUser = Depends(require_jwt_auth)
) -> PhotoValidationResponse:
    """
    Validate a photo for character transformation.
    
    Checks:
    - Face is detected
    - Photo quality is sufficient
    - Face is clear and front-facing
    
    Args:
        request: Request containing photo_url
        
    Returns:
        PhotoValidationResponse with validation results
        
    Raises:
        400: Invalid photo URL or validation failed
        500: Internal server error
    """
    logger.info(f"Validating photo: {request.photo_url}")
    
    try:
        service = get_photo_character_service()
        result = await service.validate_photo(request.photo_url)
        
        return PhotoValidationResponse(**result)
        
    except ValueError as e:
        logger.warning(f"Photo validation failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error validating photo: {e}")
        raise HTTPException(status_code=500, detail="Failed to validate photo")


@router.post("/preview", response_model=CharacterPreviewResponse)
async def preview_character(
    request: PreviewCharacterRequest,
    user: JWTUser = Depends(require_jwt_auth)
) -> CharacterPreviewResponse:
    """
    Generate character preview from photo for user approval.
    
    Transforms the uploaded photo into the selected illustration style
    and creates a preview session that expires after 1 hour.
    
    Args:
        request: Request containing photo_url, art_style, preserve_likeness
        
    Returns:
        CharacterPreviewResponse with preview_id and character image
        
    Raises:
        400: Invalid request or photo validation failed
        502: External service error
        500: Internal server error
    """
    logger.info(f"Generating character preview: {request.art_style.value}")
    
    try:
        service = get_photo_character_service()
        
        # Validate photo first
        validation = await service.validate_photo(request.photo_url)
        if not validation["valid"]:
            raise HTTPException(
                status_code=400,
                detail=f"Photo validation failed: {validation['message']}"
            )
        
        # Generate preview
        preview = await service.generate_character_preview(
            photo_url=request.photo_url,
            art_style=request.art_style.value,
            preserve_likeness=request.preserve_likeness
        )
        
        logger.info(f"Character preview generated: {preview['preview_id']}")
        
        return CharacterPreviewResponse(**preview)
        
    except HTTPException:
        raise
    except ExternalServiceException as e:
        logger.error(f"External service error: {e}")
        raise HTTPException(status_code=502, detail=str(e))
    except ValueError as e:
        logger.warning(f"Invalid request: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error generating preview: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate character preview")


@router.post("/approve/{preview_id}", response_model=ApprovalResponse)
async def approve_character(
    preview_id: str,
    user: JWTUser = Depends(require_jwt_auth)
) -> ApprovalResponse:
    """
    Approve a character preview for use in book generation.
    
    Args:
        preview_id: ID of the preview session to approve
        
    Returns:
        ApprovalResponse with character_reference_url
        
    Raises:
        404: Preview not found or expired
        500: Internal server error
    """
    logger.info(f"Approving character preview: {preview_id}")
    
    try:
        service = get_photo_character_service()
        result = await service.approve_character(preview_id)
        
        logger.info(f"Character approved: {preview_id}")
        
        return ApprovalResponse(**result)
        
    except ValueError as e:
        logger.warning(f"Approval failed: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error approving character: {e}")
        raise HTTPException(status_code=500, detail="Failed to approve character")


@router.get("/preview/{preview_id}")
async def get_preview_status(
    preview_id: str,
    user: JWTUser = Depends(require_jwt_auth)
) -> Dict:
    """
    Get the status of a character preview session.
    
    Args:
        preview_id: ID of the preview session
        
    Returns:
        Preview session details
        
    Raises:
        404: Preview not found or expired
    """
    logger.info(f"Getting preview status: {preview_id}")
    
    try:
        service = get_photo_character_service()
        session = service.get_preview_session(preview_id)
        
        if not session:
            raise HTTPException(status_code=404, detail="Preview not found or expired")
        
        return session
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting preview status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get preview status")
