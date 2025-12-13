# app/routers/common/health.py
"""
GoldenTales Health Endpoints
============================
Version-agnostic health check and root endpoints.
"""

from datetime import datetime
from typing import Dict

from fastapi import APIRouter

from app.settings import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()

# App version
APP_VERSION = "3.0.0"


@router.get("/")
async def root():
    """Root endpoint / basic health check."""
    return {
        "service": "GoldenTales API",
        "version": APP_VERSION,
        "status": "healthy"
    }


@router.get("/api/health")
async def health_check() -> Dict:
    """
    Detailed health check endpoint.

    Returns status of all dependencies and configuration.
    """
    checks = {
        "fal_key_configured": bool(settings.fal_key),
        "gemini_key_configured": bool(settings.gemini_api_key),
        "shopify_configured": bool(settings.shopify_webhook_secret),
    }

    all_healthy = all([
        checks["fal_key_configured"],
        checks["gemini_key_configured"]
    ])

    return {
        "status": "healthy" if all_healthy else "degraded",
        "version": APP_VERSION,
        "environment": settings.environment.value,
        "checks": checks,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/api/v1/health")
async def health_check_v1() -> Dict:
    """V1 API health check."""
    return await health_check()
