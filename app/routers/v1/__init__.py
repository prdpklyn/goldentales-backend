# app/routers/v1/__init__.py
"""
GoldenTales API v1 Router
=========================
Version 1 of the GoldenTales API.

This module combines all v1 endpoints into a single router.
"""

from fastapi import APIRouter

from app.routers.v1.books import router as books_router
from app.routers.v1.orders import router as orders_router
from app.routers.v1.shopify import router as shopify_router
from app.routers.v1.config import router as config_router
from app.routers.v1.pdf import router as pdf_router

# Create the main v1 router
router = APIRouter()

# Include all v1 sub-routers
router.include_router(books_router, prefix="/books", tags=["v1-books"])
router.include_router(orders_router, tags=["v1-orders"])
router.include_router(shopify_router, prefix="/shopify", tags=["v1-shopify"])
router.include_router(config_router, tags=["v1-config"])
router.include_router(pdf_router, prefix="/pdf", tags=["v1-pdf"])

__all__ = ["router"]
