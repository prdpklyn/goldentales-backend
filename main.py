# main.py
"""
GoldenTales Backend API
=======================
AI-powered personalized children's storybook generation with character consistency.

This is the main entry point for the FastAPI application.
All business logic has been extracted to the app/ package for modularity.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

# Import configuration and logging
from app.settings import settings
from app.utils.logging import setup_logging, get_logger

# Import middleware
from app.middleware.request_id import RequestIDMiddleware
from app.middleware.auth import APIKeyMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.versioning import VersioningMiddleware

# Import deprecation utilities
from app.utils.deprecation import add_deprecation_headers

# Import exception classes
from app.utils.exceptions import GoldenTalesException

# Import versioned routers
from app.routers.v1 import router as v1_router
from app.routers.common import router as common_router

# Legacy routers (for backward compatibility during migration)
from app.routers.books import router as books_router
from app.routers.orders import router as orders_router
from app.routers.shopify import router as shopify_router
from app.routers.config import router as config_router
from app.routers.pdf import router as pdf_router

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

# 4. API Versioning (detects version from path, handles deprecation)
app.add_middleware(
    VersioningMiddleware,
    enabled=True
)

logger.info(
    f"Middleware configured: RequestID, RateLimit (enabled={settings.rate_limit_enabled}), "
    f"Auth, Versioning"
)


# =================================================================
# Exception Handlers
# =================================================================

@app.exception_handler(GoldenTalesException)
async def goldentales_exception_handler(request: Request, exc: GoldenTalesException):
    """Handle custom GoldenTales exceptions."""
    request_id = request.headers.get("X-Request-ID", "unknown")
    
    logger.error(
        f"GoldenTalesException [{exc.error_code}]: {exc.message}",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "error_code": exc.error_code,
            "status_code": exc.status_code,
            "details": exc.details
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict(),
        headers={"X-Request-ID": request_id}
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle standard HTTP exceptions."""
    request_id = request.headers.get("X-Request-ID", "unknown")
    
    logger.warning(
        f"HTTP {exc.status_code}: {exc.detail}",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "status_code": exc.status_code
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": f"http_{exc.status_code}",
            "message": exc.detail
        },
        headers={"X-Request-ID": request_id}
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors."""
    request_id = request.headers.get("X-Request-ID", "unknown")
    
    errors = exc.errors()
    logger.warning(
        f"Validation error: {len(errors)} field(s) invalid",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "errors": errors
        }
    )
    
    return JSONResponse(
        status_code=422,
        content={
            "error": "validation_error",
            "message": "Request validation failed",
            "details": errors
        },
        headers={"X-Request-ID": request_id}
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Handle any unhandled exceptions."""
    request_id = request.headers.get("X-Request-ID", "unknown")
    
    logger.exception(
        f"Unhandled exception: {type(exc).__name__}",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "exception_type": type(exc).__name__,
            "exception_message": str(exc)
        }
    )
    
    # In production, don't expose internal error details
    if settings.is_production:
        message = "An internal error occurred. Please contact support with request ID: " + request_id
    else:
        message = f"{type(exc).__name__}: {str(exc)}"
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_error",
            "message": message,
            "request_id": request_id
        },
        headers={"X-Request-ID": request_id}
    )


logger.info("Exception handlers configured")

# =================================================================
# Versioned API Routes (recommended)
# =================================================================
# New versioned endpoints: /api/v1/books/*, /api/v1/orders/*, etc.
app.include_router(v1_router, prefix="/api/v1")

# =================================================================
# Common Routes (version-agnostic)
# =================================================================
# Health checks and root: /, /api/health, /api/v1/health
app.include_router(common_router)

# =================================================================
# Legacy Routes (backward compatibility)
# =================================================================
# These maintain the old /api/* paths for existing clients.
# They will be deprecated in favor of /api/v1/* in a future release.
#
# Old paths:
#   /api/books/* -> Now also at /api/v1/books/*
#   /api/orders/* -> Now also at /api/v1/orders/*
#   /api/shopify/* -> Now also at /api/v1/shopify/*
#   /api/config -> Now also at /api/v1/config
#
# Migration: Update clients to use /api/v1/* prefix
app.include_router(books_router)   # /api/books/*
app.include_router(orders_router)  # /api/orders/*, /api/shipping-options
app.include_router(shopify_router) # /api/shopify/*
app.include_router(config_router)  # /api/config (legacy, not root)
app.include_router(pdf_router)     # /api/pdf/*


# =================================================================
# Deprecation Middleware (for legacy routes)
# =================================================================
@app.middleware("http")
async def deprecation_middleware(request, call_next):
    """Add deprecation headers to legacy endpoint responses."""
    response = await call_next(request)
    add_deprecation_headers(response, request)
    return response


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=not settings.is_production
    )
