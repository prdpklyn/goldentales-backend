# main.py
"""
GoldenTales Backend API
=======================
AI-powered personalized children's storybook generation with character consistency.

This is the main entry point for the FastAPI application.
All business logic has been extracted to the app/ package for modularity.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import configuration and logging
from app.config import settings
from app.utils.logging import setup_logging, get_logger

# Import middleware
from app.middleware.request_id import RequestIDMiddleware
from app.middleware.auth import APIKeyMiddleware
from app.middleware.rate_limit import RateLimitMiddleware

# Import routers
from app.routers.books import router as books_router
from app.routers.orders import router as orders_router
from app.routers.shopify import router as shopify_router
from app.routers.config import router as config_router

# Set up logging
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup/shutdown events."""
    # Startup
    logger.info(f"Starting GoldenTales API v3.0.0")
    logger.info(f"Environment: {settings.environment.value}")
    
    # Validate required API keys
    missing_keys = settings.validate_required_keys()
    if missing_keys:
        logger.warning(f"Missing API keys: {', '.join(missing_keys)}")
    else:
        logger.info("All required API keys configured")
    
    yield
    
    # Shutdown
    logger.info("Shutting down GoldenTales API")


# Create FastAPI app
app = FastAPI(
    title="GoldenTales API",
    description="AI-powered personalized children's storybook generation with character consistency",
    version="3.0.0",
    lifespan=lifespan
)

# Configure CORS
# In development: allow all origins
# In production: use configured origins only
if settings.is_production:
    origins = settings.cors_origins
    logger.info(f"CORS configured for production: {origins}")
else:
    origins = ["*"]
    logger.warning("CORS configured for development (all origins allowed)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom middleware (order matters - executed in reverse order)
# 1. Request ID (first, so all subsequent middleware has access)
app.add_middleware(RequestIDMiddleware)

# 2. Rate limiting (before auth, to protect against brute force)
app.add_middleware(
    RateLimitMiddleware,
    enabled=settings.rate_limit_enabled
)

# 3. API Key Authentication (in production or when explicitly enabled)
app.add_middleware(
    APIKeyMiddleware,
    enforce_in_dev=settings.api_key_required
)

logger.info(f"Middleware configured: RequestID, RateLimit (enabled={settings.rate_limit_enabled}), Auth")

# Register routers
app.include_router(config_router)  # /, /api/health, /api/config
app.include_router(books_router)   # /api/books/*
app.include_router(orders_router)  # /api/orders/*, /api/shipping-options
app.include_router(shopify_router) # /api/shopify/*


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=not settings.is_production
    )