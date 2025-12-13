# app/routers/common/__init__.py
"""
GoldenTales Common Routers
==========================
Version-agnostic endpoints like health checks and root.
"""

from fastapi import APIRouter

from app.routers.common.health import router as health_router

# Create the common router
router = APIRouter()

# Include health endpoints
router.include_router(health_router, tags=["health"])

__all__ = ["router"]
