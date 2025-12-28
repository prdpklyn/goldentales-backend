# app/routers/v2/__init__.py
"""
GoldenTales V2 API Routers
===========================
V2 API endpoints with Premium and Ultra tier support.
"""

from fastapi import APIRouter
from app.routers.v2 import photo, books, preview

# Create V2 router
v2_router = APIRouter(prefix="/api/v2", tags=["V2 API"])

# Include sub-routers
v2_router.include_router(photo.router, tags=["Photo Character"])
v2_router.include_router(books.router, tags=["Books V2"])
v2_router.include_router(preview.router, tags=["Preview"])
