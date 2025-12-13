# GoldenTales: Security, Scalability & Go-Live Implementation Plan

> Comprehensive plan for renaming Taleom/DreamWeaver to GoldenTales, implementing security hardening, scalability improvements, and production readiness.

---

## Executive Summary

**Current State**: FastAPI application with core features (story generation, image generation, PDF creation, Shopify integration) running on Railway.

**Target State**: Production-ready, secure, scalable API with configurable AI models, API versioning, A/B testing, and comprehensive monitoring.

---

## Phase 1: MUST-HAVE for Go-Live 🔴

### 1.1 Application Rename: Taleom → GoldenTales

**Scope**: Full rebrand of the application

**Tasks**:
| Task | Files Affected | Priority |
|------|----------------|----------|
| Rename package and module references | All Python files | P0 |
| Update logger names (`dreamweaver` → `goldentales`) | `app/utils/logging.py` | P0 |
| Update API metadata (title, description) | `main.py` | P0 |
| Update CORS allowed origins | `main.py`, `app/config.py` | P0 |
| Update frontend URL config | `app/config.py` | P0 |
| Rename `CLAUDE.md` references | `CLAUDE.md` | P0 |
| Update environment variable prefix | `.env.example`, `app/config.py` | P0 |
| Update test fixtures and imports | `tests/*` | P0 |

---

### 1.2 API Security Hardening

#### 1.2.1 Authentication & Authorization (MUST)

**Current**: No authentication on public endpoints
**Target**: API key authentication with optional JWT for future user accounts

```
New Files:
├── app/
│   ├── middleware/
│   │   ├── __init__.py
│   │   ├── auth.py           # API key verification middleware
│   │   ├── rate_limit.py     # Rate limiting middleware
│   │   └── request_id.py     # Request tracing
│   └── utils/
│       └── api_keys.py       # API key validation logic
```

**Implementation**:
```python
# app/middleware/auth.py
class APIKeyMiddleware:
    """
    Validates X-API-Key header for protected routes.
    Public routes: /, /api/health, /api/config
    Protected routes: All others
    """

    async def __call__(self, request: Request, call_next):
        if request.url.path in PUBLIC_PATHS:
            return await call_next(request)

        api_key = request.headers.get("X-API-Key")
        if not await validate_api_key(api_key):
            raise HTTPException(401, "Invalid or missing API key")

        return await call_next(request)
```

**API Key Storage**:
- Store hashed API keys in Supabase `api_keys` table
- Fields: `id`, `key_hash`, `name`, `created_at`, `last_used_at`, `is_active`, `rate_limit_tier`

#### 1.2.2 Rate Limiting (MUST)

**Current**: Configured but not enforced
**Target**: Tiered rate limiting per API key

```python
# app/middleware/rate_limit.py
from slowapi import Limiter
from slowapi.util import get_remote_address

RATE_LIMIT_TIERS = {
    "free": "10/minute",
    "standard": "100/minute",
    "premium": "1000/minute",
    "internal": "10000/minute"  # For webhooks
}
```

**Redis Configuration**:
```python
# app/config.py additions
REDIS_URL: str = Field(default="redis://localhost:6379/0")
RATE_LIMIT_ENABLED: bool = Field(default=True)
```

#### 1.2.3 Input Validation Hardening (MUST)

**Current**: Basic sanitization
**Target**: Comprehensive injection protection

**Enhancements**:
```python
# app/utils/security.py additions

# Extended prompt injection patterns
INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior)",
    r"disregard\s+(all\s+)?(previous|prior|above)",
    r"forget\s+(everything|all)",
    r"new\s+instructions?",
    r"system\s*:",
    r"assistant\s*:",
    r"\[INST\]",
    r"<\|.*?\|>",
    r"```.*system",
    r"role\s*:\s*(system|assistant)",
]

# SQL injection patterns (for any DB queries)
SQL_INJECTION_PATTERNS = [
    r";\s*(DROP|DELETE|UPDATE|INSERT)",
    r"--\s*$",
    r"'\s*OR\s+'1'\s*=\s*'1",
    r"UNION\s+SELECT",
]
```

#### 1.2.4 Webhook Security Enhancement (MUST)

**Current**: HMAC verification for Shopify
**Target**: IP whitelisting + signature verification + replay protection

```python
# app/utils/security.py additions

SHOPIFY_WEBHOOK_IPS = [
    "23.227.38.0/24",
    "104.16.64.0/24",
    # ... other Shopify IP ranges
]

async def verify_webhook_request(request: Request) -> bool:
    # 1. Check IP whitelist
    client_ip = request.client.host
    if not is_ip_in_whitelist(client_ip, SHOPIFY_WEBHOOK_IPS):
        return False

    # 2. Verify HMAC signature
    body = await request.body()
    signature = request.headers.get("X-Shopify-Hmac-SHA256")
    if not verify_webhook_signature(body, signature):
        return False

    # 3. Replay protection (webhook ID + timestamp)
    webhook_id = request.headers.get("X-Shopify-Webhook-Id")
    timestamp = request.headers.get("X-Shopify-Triggered-At")
    if await is_webhook_replayed(webhook_id, timestamp):
        return False

    return True
```

#### 1.2.5 CORS Hardening (MUST)

**Current**: Environment-aware but permissive
**Target**: Strict production CORS with credentials support

```python
# main.py CORS configuration
if settings.is_production:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,  # Explicit list only
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Authorization", "X-API-Key", "Content-Type"],
        expose_headers=["X-Request-ID", "X-RateLimit-Remaining"],
        max_age=600,  # 10 minutes
    )
```

---

### 1.3 Configuration Management System (MUST)

**Goal**: Enable runtime configuration of AI models, prompts, and feature flags without code deployment.

#### 1.3.1 Configuration Architecture

```
New Files:
├── app/
│   ├── config/
│   │   ├── __init__.py
│   │   ├── ai_config.py      # AI model configurations
│   │   ├── prompt_config.py  # Prompt templates
│   │   ├── feature_flags.py  # Feature toggles
│   │   └── loader.py         # Config loading logic
```

**Database Schema** (Supabase):
```sql
-- AI Model Configurations
CREATE TABLE ai_model_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL UNIQUE,
    provider VARCHAR(50) NOT NULL,  -- 'fal', 'gemini', 'openai', 'replicate'
    model_id VARCHAR(200) NOT NULL,
    quality_tier VARCHAR(20) NOT NULL,  -- 'preview', 'standard', 'print'
    parameters JSONB NOT NULL DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    version INT DEFAULT 1,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Prompt Templates
CREATE TABLE prompt_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,  -- 'story', 'image', 'character'
    template TEXT NOT NULL,
    variables JSONB NOT NULL DEFAULT '[]',  -- Required variables list
    version INT DEFAULT 1,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(name, version)
);

-- Feature Flags
CREATE TABLE feature_flags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    is_enabled BOOLEAN DEFAULT false,
    rollout_percentage INT DEFAULT 0,  -- 0-100 for gradual rollout
    conditions JSONB DEFAULT '{}',  -- User/request conditions
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### 1.3.2 AI Model Configuration

```python
# app/config/ai_config.py
from dataclasses import dataclass
from typing import Dict, Any, Optional
from enum import Enum

class AIProvider(str, Enum):
    FAL = "fal"
    GEMINI = "gemini"
    OPENAI = "openai"
    REPLICATE = "replicate"
    ANTHROPIC = "anthropic"

@dataclass
class AIModelConfig:
    provider: AIProvider
    model_id: str
    quality_tier: str
    parameters: Dict[str, Any]
    cost_per_call: float
    avg_latency_ms: int
    is_active: bool = True

class AIConfigManager:
    """Manages AI model configurations with caching."""

    def __init__(self, database: DatabaseService, redis: Redis):
        self.db = database
        self.redis = redis
        self._cache_ttl = 300  # 5 minutes

    async def get_model_config(
        self,
        quality_tier: str,
        provider: Optional[AIProvider] = None
    ) -> AIModelConfig:
        """Get active model config for quality tier."""
        cache_key = f"ai_config:{quality_tier}:{provider or 'default'}"

        # Check cache first
        cached = await self.redis.get(cache_key)
        if cached:
            return AIModelConfig(**json.loads(cached))

        # Load from database
        config = await self.db.get_active_model_config(quality_tier, provider)
        if config:
            await self.redis.setex(cache_key, self._cache_ttl, json.dumps(config))
            return AIModelConfig(**config)

        # Fallback to hardcoded defaults
        return self._get_default_config(quality_tier)

    async def update_model_config(self, name: str, updates: Dict) -> AIModelConfig:
        """Update model config and invalidate cache."""
        config = await self.db.update_model_config(name, updates)
        await self._invalidate_cache(name)
        return config
```

#### 1.3.3 Prompt Template System

```python
# app/config/prompt_config.py
from jinja2 import Template, Environment, BaseLoader
from typing import Dict, Any, List

class PromptTemplateManager:
    """Manages prompt templates with variable substitution."""

    def __init__(self, database: DatabaseService, redis: Redis):
        self.db = database
        self.redis = redis
        self.jinja_env = Environment(loader=BaseLoader())

    async def get_prompt(
        self,
        name: str,
        variables: Dict[str, Any],
        version: Optional[int] = None
    ) -> str:
        """Render prompt template with variables."""
        template_data = await self._get_template(name, version)

        # Validate required variables
        required_vars = template_data.get("variables", [])
        missing = [v for v in required_vars if v not in variables]
        if missing:
            raise ValueError(f"Missing required variables: {missing}")

        # Render template
        template = self.jinja_env.from_string(template_data["template"])
        return template.render(**variables)

    async def _get_template(self, name: str, version: Optional[int]) -> Dict:
        cache_key = f"prompt:{name}:{version or 'latest'}"

        cached = await self.redis.get(cache_key)
        if cached:
            return json.loads(cached)

        template = await self.db.get_prompt_template(name, version)
        if template:
            await self.redis.setex(cache_key, 300, json.dumps(template))
            return template

        raise ValueError(f"Prompt template not found: {name}")

# Example prompt template in database:
# {
#   "name": "story_generation",
#   "template": """
#     You are creating a personalized children's story for {{ child_name }},
#     age {{ child_age }}.
#
#     Character Description:
#     {{ character_bible }}
#
#     Theme: {{ theme }}
#     Additional Characters: {{ additional_characters | join(', ') }}
#
#     Requirements:
#     - {{ page_count }} pages
#     - Age-appropriate vocabulary
#     - Include character in every scene
#     ...
#   """,
#   "variables": ["child_name", "child_age", "character_bible", "theme", "additional_characters", "page_count"]
# }
```

---

### 1.4 API Versioning (MUST)

**Goal**: Support multiple API versions for backward compatibility.

#### 1.4.1 Versioning Strategy

**Approach**: URL path versioning (`/api/v1/`, `/api/v2/`)

```
New Structure:
├── app/
│   ├── routers/
│   │   ├── v1/                   # API v1 (current)
│   │   │   ├── __init__.py
│   │   │   ├── books.py
│   │   │   ├── orders.py
│   │   │   ├── shopify.py
│   │   │   └── config.py
│   │   ├── v2/                   # API v2 (future)
│   │   │   ├── __init__.py
│   │   │   └── ...
│   │   └── common/               # Shared endpoints
│   │       ├── health.py
│   │       └── webhooks.py
```

```python
# main.py - API versioning setup
from app.routers.v1 import router as v1_router
from app.routers.v2 import router as v2_router
from app.routers.common import health_router, webhook_router

app = FastAPI(
    title="GoldenTales API",
    version="2.2.0",
    docs_url="/docs",
)

# Mount versioned routers
app.include_router(v1_router, prefix="/api/v1", tags=["v1"])
app.include_router(v2_router, prefix="/api/v2", tags=["v2"])

# Legacy support - redirect /api/* to /api/v1/*
app.include_router(v1_router, prefix="/api", tags=["legacy"], deprecated=True)

# Common endpoints (version-agnostic)
app.include_router(health_router)  # /, /health
app.include_router(webhook_router, prefix="/webhooks")  # Shopify webhooks
```

#### 1.4.2 Version Deprecation Headers

```python
# app/middleware/versioning.py
class APIVersionMiddleware:
    async def __call__(self, request: Request, call_next):
        response = await call_next(request)

        # Add deprecation headers for legacy routes
        if request.url.path.startswith("/api/") and not request.url.path.startswith("/api/v"):
            response.headers["Deprecation"] = "true"
            response.headers["Sunset"] = "2025-06-01"
            response.headers["Link"] = '</api/v1/>; rel="successor-version"'

        return response
```

---

### 1.5 Database Activation & Migration (MUST)

**Current**: In-memory storage with Supabase available
**Target**: Full Supabase integration with proper migrations

#### 1.5.1 Migration System Setup

```bash
# Install Alembic
pip install alembic

# Initialize
alembic init alembic
```

```python
# alembic/env.py
from app.config import get_settings
from app.models.database import Base

settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
target_metadata = Base.metadata
```

#### 1.5.2 Database Schema Migrations

```python
# alembic/versions/001_initial_schema.py
def upgrade():
    # Stories table
    op.create_table(
        'stories',
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column('child_name', sa.String(100), nullable=False),
        sa.Column('child_age', sa.Integer(), nullable=False),
        sa.Column('theme', sa.String(50), nullable=False),
        sa.Column('art_style', sa.String(50), nullable=False),
        sa.Column('character_bible', sa.Text(), nullable=False),
        sa.Column('status', sa.String(20), default='draft'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), onupdate=sa.func.now()),
    )

    # Pages table
    op.create_table(
        'pages',
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column('story_id', sa.UUID(), sa.ForeignKey('stories.id')),
        sa.Column('page_number', sa.Integer(), nullable=False),
        sa.Column('text_content', sa.Text(), nullable=False),
        sa.Column('image_prompt', sa.Text()),
        sa.Column('preview_image_url', sa.String(500)),
        sa.Column('print_image_url', sa.String(500)),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )

    # API Keys table
    op.create_table(
        'api_keys',
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column('key_hash', sa.String(64), nullable=False, unique=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('rate_limit_tier', sa.String(20), default='standard'),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('last_used_at', sa.DateTime()),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )
```

---

### 1.6 Order Database & PDF Storage (MUST)

**Goal**: Persist all orders with complete details and store generated PDFs for retrieval.

#### 1.6.1 Orders Database Schema

```sql
-- Orders table (comprehensive)
CREATE TABLE orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- External references
    shopify_order_id VARCHAR(100) UNIQUE,
    shopify_order_number VARCHAR(50),

    -- Book reference
    story_id UUID NOT NULL REFERENCES stories(id),

    -- Order details
    format VARCHAR(20) NOT NULL,           -- 'digital', 'softcover', 'hardcover'
    book_size VARCHAR(20) DEFAULT '8x8',   -- '8x8', '8.5x8.5', '10x8'
    quantity INT DEFAULT 1,

    -- Pricing (stored at time of order for audit trail)
    base_price DECIMAL(10,2) NOT NULL,
    shipping_cost DECIMAL(10,2) DEFAULT 0,
    gift_wrap_cost DECIMAL(10,2) DEFAULT 0,
    discount_amount DECIMAL(10,2) DEFAULT 0,
    tax_amount DECIMAL(10,2) DEFAULT 0,
    total_amount DECIMAL(10,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',

    -- Shipping
    shipping_tier VARCHAR(20),             -- 'standard', 'express', 'digital'
    shipping_address JSONB,                -- Full address object

    -- Gift options
    is_gift BOOLEAN DEFAULT false,
    gift_message TEXT,
    gift_wrap BOOLEAN DEFAULT false,
    recipient_email VARCHAR(255),

    -- Customer info
    customer_email VARCHAR(255),
    customer_name VARCHAR(200),
    customer_phone VARCHAR(50),

    -- Status tracking
    status VARCHAR(30) NOT NULL DEFAULT 'pending_payment',
    status_history JSONB DEFAULT '[]',     -- Array of {status, timestamp, note}

    -- Print production
    print_job_id VARCHAR(100),
    pdf_storage_path VARCHAR(500),         -- Supabase Storage path
    pdf_url VARCHAR(1000),                 -- Public/signed URL
    pdf_generated_at TIMESTAMP,

    -- Fulfillment
    fulfillment_provider VARCHAR(50),      -- 'lulu', 'printful', etc.
    fulfillment_order_id VARCHAR(100),
    tracking_number VARCHAR(100),
    tracking_url VARCHAR(500),
    shipped_at TIMESTAMP,
    delivered_at TIMESTAMP,

    -- Metadata
    metadata JSONB DEFAULT '{}',           -- Flexible additional data
    notes TEXT,                            -- Internal notes

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

-- Indexes for common queries
CREATE INDEX idx_orders_shopify_order_id ON orders(shopify_order_id);
CREATE INDEX idx_orders_story_id ON orders(story_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_customer_email ON orders(customer_email);
CREATE INDEX idx_orders_created_at ON orders(created_at DESC);

-- Order status history trigger
CREATE OR REPLACE FUNCTION update_order_status_history()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.status IS DISTINCT FROM NEW.status THEN
        NEW.status_history = NEW.status_history || jsonb_build_object(
            'status', NEW.status,
            'previous_status', OLD.status,
            'timestamp', NOW(),
            'note', NULL
        );
        NEW.updated_at = NOW();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER order_status_change
BEFORE UPDATE ON orders
FOR EACH ROW
EXECUTE FUNCTION update_order_status_history();
```

#### 1.6.2 Order Status Enum

```python
# app/models/enums.py - Enhanced OrderStatus
class OrderStatus(str, Enum):
    # Payment
    PENDING_PAYMENT = "pending_payment"
    PAYMENT_CONFIRMED = "payment_confirmed"
    PAYMENT_FAILED = "payment_failed"

    # Production
    GENERATING_PRINT_FILES = "generating_print_files"
    UPSCALING_IMAGES = "upscaling_images"
    CREATING_PDF = "creating_pdf"
    PDF_READY = "pdf_ready"

    # Fulfillment
    UPLOADING_TO_PRINTER = "uploading_to_printer"
    SENT_TO_PRINTER = "sent_to_printer"
    PRINTING = "printing"
    QUALITY_CHECK = "quality_check"

    # Shipping
    READY_TO_SHIP = "ready_to_ship"
    SHIPPED = "shipped"
    IN_TRANSIT = "in_transit"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"

    # Digital delivery
    DIGITAL_READY = "digital_ready"
    DIGITAL_SENT = "digital_sent"

    # Issues
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    ON_HOLD = "on_hold"
```

#### 1.6.3 PDF Storage Service

```python
# app/services/storage_service.py
"""
PDF and asset storage using Supabase Storage.

Storage Structure:
├── pdfs/
│   ├── orders/
│   │   └── {order_id}/
│   │       ├── {book_id}_print.pdf       # Print-ready PDF
│   │       ├── {book_id}_preview.pdf     # Low-res preview (optional)
│   │       └── metadata.json             # Generation metadata
│   └── temp/                             # Temporary files (auto-cleaned)
├── images/
│   ├── preview/
│   │   └── {book_id}/
│   │       └── page_{n}.jpg
│   └── print/
│       └── {book_id}/
│           └── page_{n}_upscaled.jpg
└── covers/
    └── {book_id}_cover.jpg
"""

from supabase import Client
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import os

class StorageService:
    """Handles PDF and image storage with Supabase Storage."""

    BUCKET_NAME = "goldentales-assets"
    PDF_FOLDER = "pdfs/orders"
    IMAGES_FOLDER = "images"

    def __init__(self, supabase_client: Client):
        self.client = supabase_client
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        """Create storage bucket if it doesn't exist."""
        try:
            self.client.storage.get_bucket(self.BUCKET_NAME)
        except Exception:
            self.client.storage.create_bucket(
                self.BUCKET_NAME,
                options={
                    "public": False,  # Private by default
                    "file_size_limit": 100 * 1024 * 1024,  # 100MB max
                    "allowed_mime_types": [
                        "application/pdf",
                        "image/jpeg",
                        "image/png",
                        "application/json"
                    ]
                }
            )

    async def upload_order_pdf(
        self,
        order_id: str,
        book_id: str,
        pdf_path: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """
        Upload print-ready PDF for an order.

        Returns:
            Dict with 'storage_path' and 'signed_url'
        """
        storage_path = f"{self.PDF_FOLDER}/{order_id}/{book_id}_print.pdf"

        # Upload PDF
        with open(pdf_path, 'rb') as f:
            self.client.storage.from_(self.BUCKET_NAME).upload(
                path=storage_path,
                file=f,
                file_options={"content-type": "application/pdf"}
            )

        # Upload metadata
        if metadata:
            meta_path = f"{self.PDF_FOLDER}/{order_id}/metadata.json"
            import json
            self.client.storage.from_(self.BUCKET_NAME).upload(
                path=meta_path,
                file=json.dumps(metadata).encode(),
                file_options={"content-type": "application/json"}
            )

        # Generate signed URL (valid for 7 days)
        signed_url = self.client.storage.from_(self.BUCKET_NAME).create_signed_url(
            path=storage_path,
            expires_in=7 * 24 * 60 * 60  # 7 days in seconds
        )

        return {
            "storage_path": storage_path,
            "signed_url": signed_url.get("signedURL"),
            "uploaded_at": datetime.utcnow().isoformat()
        }

    async def get_order_pdf_url(
        self,
        order_id: str,
        book_id: str,
        expiry_hours: int = 24
    ) -> Optional[str]:
        """Get a fresh signed URL for an order's PDF."""
        storage_path = f"{self.PDF_FOLDER}/{order_id}/{book_id}_print.pdf"

        try:
            result = self.client.storage.from_(self.BUCKET_NAME).create_signed_url(
                path=storage_path,
                expires_in=expiry_hours * 60 * 60
            )
            return result.get("signedURL")
        except Exception as e:
            logger.error(f"Failed to get PDF URL: {e}")
            return None

    async def upload_print_images(
        self,
        book_id: str,
        image_urls: List[str]
    ) -> List[str]:
        """Upload upscaled print images to permanent storage."""
        storage_urls = []

        async with httpx.AsyncClient() as client:
            for i, url in enumerate(image_urls):
                if not url:
                    storage_urls.append(None)
                    continue

                # Download image
                response = await client.get(url)
                image_data = response.content

                # Upload to storage
                storage_path = f"{self.IMAGES_FOLDER}/print/{book_id}/page_{i+1}.jpg"
                self.client.storage.from_(self.BUCKET_NAME).upload(
                    path=storage_path,
                    file=image_data,
                    file_options={"content-type": "image/jpeg"}
                )

                # Get public URL
                public_url = self.client.storage.from_(self.BUCKET_NAME).get_public_url(
                    storage_path
                )
                storage_urls.append(public_url)

        return storage_urls

    async def delete_order_assets(self, order_id: str):
        """Delete all assets for an order (for cancellations/refunds)."""
        folder_path = f"{self.PDF_FOLDER}/{order_id}"

        # List all files in order folder
        files = self.client.storage.from_(self.BUCKET_NAME).list(folder_path)

        if files:
            paths = [f"{folder_path}/{f['name']}" for f in files]
            self.client.storage.from_(self.BUCKET_NAME).remove(paths)
```

#### 1.6.4 Order Service

```python
# app/services/order_service.py
"""
Order management service with PDF storage integration.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid

from app.services.database import DatabaseService
from app.services.storage_service import StorageService
from app.services.print_service import PrintService, PrintJob
from app.models.enums import OrderStatus
from app.utils.logging import get_logger

logger = get_logger(__name__)


class OrderService:
    """Manages orders with database persistence and PDF storage."""

    def __init__(
        self,
        database: DatabaseService,
        storage: StorageService,
        print_service: PrintService
    ):
        self.db = database
        self.storage = storage
        self.print_service = print_service

    async def create_order(
        self,
        story_id: str,
        format: str,
        shipping_tier: str,
        customer_email: str,
        shopify_order_id: Optional[str] = None,
        shipping_address: Optional[Dict] = None,
        gift_options: Optional[Dict] = None,
        pricing: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Create a new order in the database.

        Returns:
            Complete order record with ID
        """
        order_id = str(uuid.uuid4())

        # Build order data
        order_data = {
            "id": order_id,
            "story_id": story_id,
            "shopify_order_id": shopify_order_id,
            "format": format,
            "shipping_tier": shipping_tier,
            "customer_email": customer_email,
            "status": OrderStatus.PENDING_PAYMENT.value,
            "status_history": [{
                "status": OrderStatus.PENDING_PAYMENT.value,
                "timestamp": datetime.utcnow().isoformat(),
                "note": "Order created"
            }],
            "shipping_address": shipping_address,
            "is_gift": gift_options.get("is_gift", False) if gift_options else False,
            "gift_message": gift_options.get("message") if gift_options else None,
            "gift_wrap": gift_options.get("wrap", False) if gift_options else False,
            "recipient_email": gift_options.get("recipient_email") if gift_options else None,
            "base_price": pricing.get("base_price", 0) if pricing else 0,
            "shipping_cost": pricing.get("shipping_cost", 0) if pricing else 0,
            "gift_wrap_cost": pricing.get("gift_wrap_cost", 0) if pricing else 0,
            "total_amount": pricing.get("total", 0) if pricing else 0,
            "created_at": datetime.utcnow().isoformat()
        }

        # Insert into database
        result = await self.db.create_order(order_data)

        logger.info(f"Order created: {order_id}", extra={
            "order_id": order_id,
            "story_id": story_id,
            "format": format
        })

        return result

    async def process_payment_confirmed(
        self,
        order_id: str,
        shopify_order_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Handle payment confirmation - start print production.

        Flow:
        1. Update order status to PAYMENT_CONFIRMED
        2. Fetch full book data
        3. Start print production
        4. Store PDF when complete
        """
        # Update status
        await self.update_order_status(
            order_id,
            OrderStatus.PAYMENT_CONFIRMED,
            note="Payment received from Shopify"
        )

        # Get order and book data
        order = await self.db.get_order(order_id)
        if not order:
            raise ValueError(f"Order not found: {order_id}")

        book_data = await self.db.get_full_book(order["story_id"])
        if not book_data:
            raise ValueError(f"Book not found: {order['story_id']}")

        # Start print production
        print_job = await self.print_service.start_print_production(
            order_id=order_id,
            book_data=book_data,
            format=order["format"],
            book_size=order.get("book_size", "square_8x8"),
            shipping_address=order.get("shipping_address")
        )

        # Update order with print job ID
        await self.db.update_order(order_id, {
            "print_job_id": print_job.job_id,
            "status": OrderStatus.GENERATING_PRINT_FILES.value
        })

        # Monitor job and upload PDF when complete
        asyncio.create_task(
            self._monitor_print_job_and_store_pdf(order_id, print_job, book_data)
        )

        return {
            "order_id": order_id,
            "print_job_id": print_job.job_id,
            "status": OrderStatus.GENERATING_PRINT_FILES.value
        }

    async def _monitor_print_job_and_store_pdf(
        self,
        order_id: str,
        print_job: PrintJob,
        book_data: Dict
    ):
        """Monitor print job and store PDF when complete."""
        import asyncio

        while True:
            await asyncio.sleep(5)  # Check every 5 seconds

            job = self.print_service.get_job_status(print_job.job_id)
            if not job:
                break

            # Update order status based on job status
            await self.update_order_status(order_id, job.status)

            if job.status == OrderStatus.SENT_TO_PRINTER:
                # Job complete - upload PDF to storage
                if job.pdf_path:
                    pdf_result = await self.storage.upload_order_pdf(
                        order_id=order_id,
                        book_id=book_data["book_id"],
                        pdf_path=job.pdf_path,
                        metadata={
                            "book_id": book_data["book_id"],
                            "title": book_data.get("title"),
                            "child_name": book_data.get("child_name"),
                            "page_count": len(book_data.get("pages", [])),
                            "format": job.order_id,
                            "generated_at": datetime.utcnow().isoformat(),
                            "upscale_method": self.print_service.upscale_method.value
                        }
                    )

                    # Update order with PDF info
                    await self.db.update_order(order_id, {
                        "pdf_storage_path": pdf_result["storage_path"],
                        "pdf_url": pdf_result["signed_url"],
                        "pdf_generated_at": pdf_result["uploaded_at"],
                        "status": OrderStatus.PDF_READY.value
                    })

                    logger.info(f"PDF stored for order {order_id}", extra={
                        "storage_path": pdf_result["storage_path"]
                    })
                break

            elif job.status == OrderStatus.FAILED:
                await self.db.update_order(order_id, {
                    "status": OrderStatus.FAILED.value,
                    "notes": f"Print job failed: {job.error_message}"
                })
                break

    async def update_order_status(
        self,
        order_id: str,
        status: OrderStatus,
        note: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update order status with history tracking."""
        return await self.db.update_order(order_id, {
            "status": status.value if isinstance(status, OrderStatus) else status
        })

    async def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Get order with fresh PDF URL if available."""
        order = await self.db.get_order(order_id)

        if order and order.get("pdf_storage_path"):
            # Get fresh signed URL
            fresh_url = await self.storage.get_order_pdf_url(
                order_id=order_id,
                book_id=order["story_id"],
                expiry_hours=24
            )
            if fresh_url:
                order["pdf_url"] = fresh_url

        return order

    async def get_order_by_shopify_id(
        self,
        shopify_order_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get order by Shopify order ID."""
        return await self.db.get_order_by_shopify_id(shopify_order_id)

    async def get_orders_by_customer(
        self,
        customer_email: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get all orders for a customer."""
        return await self.db.get_orders_by_customer(customer_email, limit)

    async def get_pdf_download_url(
        self,
        order_id: str,
        expiry_hours: int = 24
    ) -> Optional[str]:
        """Get a download URL for the order's PDF."""
        order = await self.db.get_order(order_id)

        if not order or not order.get("pdf_storage_path"):
            return None

        return await self.storage.get_order_pdf_url(
            order_id=order_id,
            book_id=order["story_id"],
            expiry_hours=expiry_hours
        )
```

#### 1.6.5 Database Service Extensions

```python
# Add to app/services/database.py

# ==========================================
# ORDER OPERATIONS
# ==========================================

async def create_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new order."""
    if not self._client:
        raise ValueError("Database not configured")

    result = self._client.table("orders").insert(order_data).execute()

    if result.data:
        logger.info(f"Created order: {result.data[0]['id']}")
        return result.data[0]

    raise Exception("Failed to create order")

async def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
    """Get an order by ID."""
    if not self._client:
        raise ValueError("Database not configured")

    result = self._client.table("orders").select("*").eq("id", order_id).execute()

    return result.data[0] if result.data else None

async def get_order_by_shopify_id(
    self,
    shopify_order_id: str
) -> Optional[Dict[str, Any]]:
    """Get order by Shopify order ID."""
    if not self._client:
        raise ValueError("Database not configured")

    result = (
        self._client.table("orders")
        .select("*")
        .eq("shopify_order_id", shopify_order_id)
        .execute()
    )

    return result.data[0] if result.data else None

async def update_order(
    self,
    order_id: str,
    updates: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """Update an order."""
    if not self._client:
        raise ValueError("Database not configured")

    updates["updated_at"] = datetime.utcnow().isoformat()

    result = (
        self._client.table("orders")
        .update(updates)
        .eq("id", order_id)
        .execute()
    )

    return result.data[0] if result.data else None

async def get_orders_by_customer(
    self,
    customer_email: str,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """Get orders for a customer."""
    if not self._client:
        raise ValueError("Database not configured")

    result = (
        self._client.table("orders")
        .select("*")
        .eq("customer_email", customer_email)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )

    return result.data or []

async def get_orders_by_status(
    self,
    status: str,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """Get orders by status."""
    if not self._client:
        raise ValueError("Database not configured")

    result = (
        self._client.table("orders")
        .select("*")
        .eq("status", status)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )

    return result.data or []

async def get_order_with_book(
    self,
    order_id: str
) -> Optional[Dict[str, Any]]:
    """Get order with associated book data."""
    order = await self.get_order(order_id)

    if not order:
        return None

    book = await self.get_full_book(order["story_id"])

    return {
        **order,
        "book": book
    }
```

#### 1.6.6 Order API Endpoints

```python
# app/routers/v1/orders.py - Enhanced

@router.get("/orders/{order_id}")
async def get_order(
    order_id: str,
    db: DatabaseService = Depends(get_database)
) -> OrderResponse:
    """Get order details with PDF URL."""
    order_service = get_order_service()
    order = await order_service.get_order(order_id)

    if not order:
        raise HTTPException(404, "Order not found")

    return OrderResponse(**order)

@router.get("/orders/{order_id}/pdf")
async def get_order_pdf(
    order_id: str,
    expiry_hours: int = Query(default=24, le=168),  # Max 7 days
    db: DatabaseService = Depends(get_database)
):
    """Get a fresh download URL for the order's PDF."""
    order_service = get_order_service()

    pdf_url = await order_service.get_pdf_download_url(order_id, expiry_hours)

    if not pdf_url:
        raise HTTPException(404, "PDF not available for this order")

    return {
        "order_id": order_id,
        "pdf_url": pdf_url,
        "expires_in_hours": expiry_hours
    }

@router.get("/orders/{order_id}/status")
async def get_order_status(
    order_id: str,
    db: DatabaseService = Depends(get_database)
):
    """Get current order status with history."""
    order = await db.get_order(order_id)

    if not order:
        raise HTTPException(404, "Order not found")

    return {
        "order_id": order_id,
        "status": order["status"],
        "status_history": order.get("status_history", []),
        "pdf_ready": order.get("pdf_url") is not None,
        "tracking": {
            "number": order.get("tracking_number"),
            "url": order.get("tracking_url"),
            "shipped_at": order.get("shipped_at")
        } if order.get("tracking_number") else None
    }

@router.get("/customers/{email}/orders")
async def get_customer_orders(
    email: str,
    limit: int = Query(default=50, le=100),
    db: DatabaseService = Depends(get_database)
):
    """Get all orders for a customer by email."""
    order_service = get_order_service()
    orders = await order_service.get_orders_by_customer(email, limit)

    return {
        "customer_email": email,
        "order_count": len(orders),
        "orders": orders
    }
```

---

### 1.7 Monitoring & Observability (MUST)

#### 1.7.1 Structured Logging

```python
# app/utils/logging.py - Enhanced
import structlog
from pythonjsonlogger import jsonlogger

def setup_logging():
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

# Usage
logger = structlog.get_logger("goldentales")
logger.info("book_created", book_id=book_id, theme=theme, duration_ms=duration)
```

#### 1.7.2 Request Tracing

```python
# app/middleware/request_id.py
import uuid

class RequestIDMiddleware:
    async def __call__(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

        # Add to request state
        request.state.request_id = request_id

        # Add to structlog context
        structlog.contextvars.bind_contextvars(request_id=request_id)

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id

        return response
```

#### 1.7.3 Metrics Collection

```python
# app/utils/metrics.py
from prometheus_client import Counter, Histogram, Gauge

# Request metrics
REQUEST_COUNT = Counter(
    'goldentales_requests_total',
    'Total requests',
    ['method', 'endpoint', 'status']
)

REQUEST_LATENCY = Histogram(
    'goldentales_request_latency_seconds',
    'Request latency',
    ['method', 'endpoint']
)

# AI Generation metrics
AI_GENERATION_COUNT = Counter(
    'goldentales_ai_generations_total',
    'AI generation calls',
    ['service', 'model', 'quality_tier', 'status']
)

AI_GENERATION_LATENCY = Histogram(
    'goldentales_ai_generation_latency_seconds',
    'AI generation latency',
    ['service', 'model']
)

# Business metrics
BOOKS_CREATED = Counter('goldentales_books_created_total', 'Books created', ['theme', 'art_style'])
ORDERS_COMPLETED = Counter('goldentales_orders_completed_total', 'Orders completed', ['format'])
```

#### 1.7.4 Health Check Enhancement

```python
# app/routers/common/health.py
@router.get("/health/detailed")
async def detailed_health_check():
    checks = {
        "database": await check_database_health(),
        "redis": await check_redis_health(),
        "fal_api": await check_fal_health(),
        "gemini_api": await check_gemini_health(),
        "supabase_storage": await check_storage_health(),
    }

    overall_status = "healthy" if all(c["status"] == "healthy" for c in checks.values()) else "degraded"

    return {
        "status": overall_status,
        "version": "2.2.0",
        "environment": settings.ENVIRONMENT,
        "checks": checks,
        "timestamp": datetime.utcnow().isoformat()
    }
```

---

### 1.8 Error Handling & Resilience (MUST)

#### 1.8.1 Circuit Breaker Pattern

```python
# app/utils/circuit_breaker.py
from circuitbreaker import circuit

class ExternalServiceError(Exception):
    pass

@circuit(
    failure_threshold=5,
    recovery_timeout=60,
    expected_exception=ExternalServiceError
)
async def call_fal_api(prompt: str, model: str, **kwargs):
    try:
        result = await fal_client.submit(model, arguments={**kwargs})
        return result
    except Exception as e:
        raise ExternalServiceError(f"Fal API error: {e}")

@circuit(
    failure_threshold=3,
    recovery_timeout=30,
    expected_exception=ExternalServiceError
)
async def call_gemini_api(prompt: str, **kwargs):
    try:
        result = await gemini_model.generate_content_async(prompt)
        return result
    except Exception as e:
        raise ExternalServiceError(f"Gemini API error: {e}")
```

#### 1.8.2 Retry Logic

```python
# app/utils/retry.py
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(ExternalServiceError)
)
async def generate_image_with_retry(prompt: str, model: str, **kwargs):
    return await call_fal_api(prompt, model, **kwargs)
```

#### 1.8.3 Graceful Degradation

```python
# app/services/image_generator.py - Enhanced
async def generate_illustration(self, prompt: str, quality: GenerationQuality) -> str:
    """Generate illustration with fallback chain."""

    # Primary: Fal.ai
    try:
        return await self._generate_with_fal(prompt, quality)
    except CircuitBreakerError:
        logger.warning("fal_circuit_open", quality=quality.value)

    # Fallback 1: Replicate
    if settings.REPLICATE_API_KEY:
        try:
            return await self._generate_with_replicate(prompt, quality)
        except Exception as e:
            logger.warning("replicate_fallback_failed", error=str(e))

    # Fallback 2: Placeholder image
    logger.error("all_image_generators_failed", prompt=prompt[:100])
    return self._get_placeholder_image(quality)
```

---

## Phase 2: SHOULD-HAVE for Go-Live 🟡

### 2.1 A/B Testing Framework

**Goal**: Test different AI models, prompts, and features with user segments.

#### 2.1.1 A/B Test Configuration

```sql
-- A/B Test Experiments table
CREATE TABLE ab_experiments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    status VARCHAR(20) DEFAULT 'draft',  -- draft, running, paused, completed
    start_date TIMESTAMP,
    end_date TIMESTAMP,
    variants JSONB NOT NULL DEFAULT '[]',
    traffic_allocation JSONB NOT NULL DEFAULT '{}',  -- {"control": 50, "variant_a": 50}
    metrics JSONB DEFAULT '[]',  -- Metrics to track
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- User experiment assignments
CREATE TABLE ab_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    experiment_id UUID REFERENCES ab_experiments(id),
    user_identifier VARCHAR(100) NOT NULL,  -- session_id or user_id
    variant VARCHAR(50) NOT NULL,
    assigned_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(experiment_id, user_identifier)
);

-- Experiment events/conversions
CREATE TABLE ab_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    experiment_id UUID REFERENCES ab_experiments(id),
    user_identifier VARCHAR(100) NOT NULL,
    variant VARCHAR(50) NOT NULL,
    event_type VARCHAR(50) NOT NULL,  -- 'book_created', 'purchase', 'regeneration'
    event_data JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### 2.1.2 A/B Testing Service

```python
# app/services/ab_testing.py
import hashlib
from typing import Optional, Dict, Any

class ABTestingService:
    def __init__(self, database: DatabaseService, redis: Redis):
        self.db = database
        self.redis = redis

    async def get_variant(
        self,
        experiment_name: str,
        user_identifier: str
    ) -> Optional[str]:
        """Get or assign variant for user in experiment."""

        # Check if experiment is running
        experiment = await self._get_active_experiment(experiment_name)
        if not experiment:
            return None

        # Check existing assignment
        existing = await self.db.get_ab_assignment(
            experiment["id"],
            user_identifier
        )
        if existing:
            return existing["variant"]

        # Deterministic assignment based on user hash
        variant = self._assign_variant(
            user_identifier,
            experiment["traffic_allocation"]
        )

        # Store assignment
        await self.db.create_ab_assignment(
            experiment["id"],
            user_identifier,
            variant
        )

        return variant

    def _assign_variant(
        self,
        user_identifier: str,
        allocation: Dict[str, int]
    ) -> str:
        """Deterministically assign variant based on hash."""
        hash_value = int(hashlib.md5(user_identifier.encode()).hexdigest(), 16)
        bucket = hash_value % 100

        cumulative = 0
        for variant, percentage in allocation.items():
            cumulative += percentage
            if bucket < cumulative:
                return variant

        return list(allocation.keys())[0]  # Default to first variant

    async def track_event(
        self,
        experiment_name: str,
        user_identifier: str,
        event_type: str,
        event_data: Optional[Dict[str, Any]] = None
    ):
        """Track conversion event for experiment."""
        experiment = await self._get_active_experiment(experiment_name)
        if not experiment:
            return

        assignment = await self.db.get_ab_assignment(
            experiment["id"],
            user_identifier
        )
        if not assignment:
            return

        await self.db.create_ab_event(
            experiment["id"],
            user_identifier,
            assignment["variant"],
            event_type,
            event_data or {}
        )

# Usage in book creation
async def create_book(request: CreateBookRequest, session_id: str):
    ab_service = get_ab_service()

    # Get image model variant
    image_model_variant = await ab_service.get_variant(
        "image_model_test",
        session_id
    )

    # Use appropriate model based on variant
    if image_model_variant == "flux_pro_v1.1":
        model_config = await ai_config.get_model_config("preview", AIProvider.FAL)
    elif image_model_variant == "dalle3":
        model_config = await ai_config.get_model_config("preview", AIProvider.OPENAI)
    else:
        model_config = DEFAULT_MODEL_CONFIG

    # Generate book...
    book = await generate_book(request, model_config)

    # Track creation event
    await ab_service.track_event(
        "image_model_test",
        session_id,
        "book_created",
        {"theme": request.theme, "art_style": request.art_style}
    )

    return book
```

---

### 2.2 Background Job Queue (Celery)

**Goal**: Handle long-running tasks (PDF generation, print upscaling) asynchronously.

#### 2.2.1 Celery Setup

```python
# app/celery_app.py
from celery import Celery
from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "goldentales",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,  # 10 minutes max
    worker_prefetch_multiplier=1,  # Fair scheduling
    task_acks_late=True,  # Acknowledge after completion
)

# Task routing
celery_app.conf.task_routes = {
    "app.tasks.image.*": {"queue": "images"},
    "app.tasks.pdf.*": {"queue": "pdf"},
    "app.tasks.email.*": {"queue": "email"},
}
```

#### 2.2.2 Task Definitions

```python
# app/tasks/image_tasks.py
from app.celery_app import celery_app
from app.services.image_generator import ImageGenerator

@celery_app.task(bind=True, max_retries=3)
def upscale_images_for_print(self, book_id: str, image_urls: list):
    """Upscale preview images to print quality."""
    try:
        image_generator = ImageGenerator()
        upscaled_urls = []

        for i, url in enumerate(image_urls):
            upscaled = image_generator.upscale_image_sync(url)
            upscaled_urls.append(upscaled)

            # Update progress
            self.update_state(
                state="PROGRESS",
                meta={"current": i + 1, "total": len(image_urls)}
            )

        return {"book_id": book_id, "upscaled_urls": upscaled_urls}

    except Exception as e:
        self.retry(exc=e, countdown=60)

@celery_app.task(bind=True)
def generate_print_pdf(self, book_id: str, upscaled_urls: list):
    """Generate print-ready PDF."""
    from app.services.print_service import PrintService

    print_service = PrintService()
    pdf_path = print_service.generate_pdf_sync(book_id, upscaled_urls)

    return {"book_id": book_id, "pdf_path": pdf_path}

# Chain tasks
from celery import chain

def start_print_production(book_id: str, preview_urls: list):
    """Start async print production pipeline."""
    workflow = chain(
        upscale_images_for_print.s(book_id, preview_urls),
        generate_print_pdf.s()
    )
    return workflow.apply_async()
```

---

### 2.3 Caching Strategy

#### 2.3.1 Multi-Level Cache

```python
# app/utils/cache.py
from functools import wraps
import hashlib
import json

class CacheManager:
    def __init__(self, redis: Redis):
        self.redis = redis
        self.local_cache = {}  # In-memory L1 cache

    async def get(self, key: str) -> Optional[Any]:
        # L1: Local memory
        if key in self.local_cache:
            return self.local_cache[key]

        # L2: Redis
        value = await self.redis.get(key)
        if value:
            self.local_cache[key] = json.loads(value)
            return self.local_cache[key]

        return None

    async def set(self, key: str, value: Any, ttl: int = 300):
        serialized = json.dumps(value)
        await self.redis.setex(key, ttl, serialized)
        self.local_cache[key] = value

    async def invalidate(self, pattern: str):
        keys = await self.redis.keys(pattern)
        if keys:
            await self.redis.delete(*keys)

        # Clear matching local cache
        self.local_cache = {
            k: v for k, v in self.local_cache.items()
            if not fnmatch.fnmatch(k, pattern)
        }

def cached(ttl: int = 300, key_prefix: str = ""):
    """Decorator for caching function results."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache = get_cache_manager()

            # Generate cache key from function name and arguments
            key_data = f"{func.__name__}:{args}:{sorted(kwargs.items())}"
            cache_key = f"{key_prefix}:{hashlib.md5(key_data.encode()).hexdigest()}"

            # Try cache first
            cached_result = await cache.get(cache_key)
            if cached_result is not None:
                return cached_result

            # Call function and cache result
            result = await func(*args, **kwargs)
            await cache.set(cache_key, result, ttl)

            return result
        return wrapper
    return decorator

# Usage
@cached(ttl=3600, key_prefix="config")
async def get_public_config():
    return {
        "themes": [...],
        "art_styles": [...],
        "prices": {...}
    }
```

---

### 2.4 Image Generation Scalability

#### 2.4.1 Generation Queue with Priority

```python
# app/services/image_queue.py
from dataclasses import dataclass
from enum import IntEnum
import asyncio
from typing import List

class GenerationPriority(IntEnum):
    HIGH = 1      # Paid orders, regenerations
    NORMAL = 2    # New book previews
    LOW = 3       # Background tasks

@dataclass
class GenerationRequest:
    id: str
    prompt: str
    quality: GenerationQuality
    priority: GenerationPriority
    callback: callable
    created_at: datetime

class ImageGenerationQueue:
    def __init__(self, max_concurrent: int = 10):
        self.queue = asyncio.PriorityQueue()
        self.max_concurrent = max_concurrent
        self.active_count = 0
        self.semaphore = asyncio.Semaphore(max_concurrent)

    async def submit(
        self,
        prompt: str,
        quality: GenerationQuality,
        priority: GenerationPriority = GenerationPriority.NORMAL
    ) -> str:
        """Submit generation request and return result."""
        request_id = str(uuid.uuid4())
        result_future = asyncio.Future()

        request = GenerationRequest(
            id=request_id,
            prompt=prompt,
            quality=quality,
            priority=priority,
            callback=lambda r: result_future.set_result(r),
            created_at=datetime.utcnow()
        )

        await self.queue.put((priority, request))

        # Start worker if not at capacity
        asyncio.create_task(self._process_queue())

        return await result_future

    async def _process_queue(self):
        async with self.semaphore:
            if self.queue.empty():
                return

            _, request = await self.queue.get()

            try:
                result = await self._generate(request)
                request.callback(result)
            except Exception as e:
                request.callback({"error": str(e)})
            finally:
                self.queue.task_done()
```

---

### 2.5 Multi-Provider AI Abstraction

```python
# app/services/ai/base.py
from abc import ABC, abstractmethod
from typing import Dict, Any

class AIProvider(ABC):
    @abstractmethod
    async def generate_image(self, prompt: str, **kwargs) -> str:
        pass

    @abstractmethod
    async def generate_text(self, prompt: str, **kwargs) -> str:
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        pass

# app/services/ai/fal_provider.py
class FalProvider(AIProvider):
    async def generate_image(self, prompt: str, model: str, **kwargs) -> str:
        result = await fal_client.submit(model, arguments={"prompt": prompt, **kwargs})
        return result["images"][0]["url"]

# app/services/ai/openai_provider.py
class OpenAIProvider(AIProvider):
    async def generate_image(self, prompt: str, model: str = "dall-e-3", **kwargs) -> str:
        response = await openai_client.images.generate(
            model=model,
            prompt=prompt,
            **kwargs
        )
        return response.data[0].url

# app/services/ai/factory.py
class AIProviderFactory:
    providers = {
        "fal": FalProvider,
        "openai": OpenAIProvider,
        "replicate": ReplicateProvider,
    }

    @classmethod
    def get_provider(cls, provider_name: str) -> AIProvider:
        provider_class = cls.providers.get(provider_name)
        if not provider_class:
            raise ValueError(f"Unknown provider: {provider_name}")
        return provider_class()
```

---

## Phase 3: NICE-TO-HAVE (Post Go-Live) 🟢

### 3.1 Admin Dashboard API

```python
# app/routers/admin/
├── __init__.py
├── config.py      # Manage AI configs, prompts
├── experiments.py # A/B test management
├── analytics.py   # Usage metrics
└── orders.py      # Order management
```

### 3.2 Email Notifications

```python
# app/services/email_service.py
- Order confirmation
- PDF ready notification
- Shipping updates
```

### 3.3 Webhook Retry System

```python
# Outbound webhooks for order status updates
# Retry with exponential backoff
```

### 3.4 Cost Analytics

```python
# Track AI generation costs per book/user
# ROI analysis per feature
```

### 3.5 Multi-Language Support

```python
# Story generation in multiple languages
# i18n for API responses
```

---

## Implementation Timeline

| Phase | Scope | Estimated Effort |
|-------|-------|------------------|
| **Phase 1.1** | Rename to GoldenTales | 1-2 days |
| **Phase 1.2** | API Security (Auth, Rate Limiting) | 3-4 days |
| **Phase 1.3** | Configuration Management | 3-4 days |
| **Phase 1.4** | API Versioning | 2-3 days |
| **Phase 1.5** | Database Migration | 2-3 days |
| **Phase 1.6** | Monitoring & Observability | 2-3 days |
| **Phase 1.7** | Error Handling & Resilience | 2-3 days |
| **Phase 2.1** | A/B Testing | 3-4 days |
| **Phase 2.2** | Background Jobs (Celery) | 2-3 days |
| **Phase 2.3** | Caching Strategy | 1-2 days |
| **Phase 2.4** | Image Queue Scalability | 2-3 days |
| **Phase 2.5** | Multi-Provider AI | 2-3 days |

---

## Environment Variables (Final)

```env
# Application
GOLDENTALES_ENV=production
GOLDENTALES_DEBUG=false
GOLDENTALES_HOST=0.0.0.0
GOLDENTALES_PORT=8000

# Security
GOLDENTALES_API_KEY_SALT=<random-32-char-string>
GOLDENTALES_WEBHOOK_SECRET=<shopify-webhook-secret>
GOLDENTALES_RATE_LIMIT_ENABLED=true

# Database
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_PUBLISHABLE_KEY=xxx
DATABASE_URL=postgresql://...

# Redis
REDIS_URL=redis://localhost:6379/0

# AI Services
FAL_KEY=<fal-api-key>
GEMINI_API_KEY=<google-api-key>
OPENAI_API_KEY=<optional-openai-key>
REPLICATE_API_KEY=<optional-replicate-key>

# External Services
SHOPIFY_WEBHOOK_SECRET=<webhook-secret>
LULU_API_KEY=<lulu-api-key>
SENDGRID_API_KEY=<sendgrid-key>
STRIPE_SECRET_KEY=<stripe-key>

# Monitoring
SENTRY_DSN=<sentry-dsn>

# Feature Flags
FEATURE_AB_TESTING_ENABLED=true
FEATURE_CELERY_ENABLED=true
```

---

## Go-Live Checklist

### MUST Complete Before Launch
- [ ] Rename application to GoldenTales
- [ ] Implement API key authentication
- [ ] Enable rate limiting
- [ ] Activate database persistence (remove in-memory storage)
- [ ] **Implement Order database with full schema**
- [ ] **Set up PDF storage in Supabase Storage**
- [ ] **Integrate PDF storage with print service**
- [ ] Configure production CORS
- [ ] Set up structured logging
- [ ] Configure Sentry error tracking
- [ ] Implement circuit breakers for external APIs
- [ ] Run database migrations
- [ ] Update all environment variables
- [ ] Configure API versioning
- [ ] Load test with expected traffic

### SHOULD Complete Before Launch
- [ ] Set up Redis caching
- [ ] Implement A/B testing framework
- [ ] Configure Celery workers
- [ ] Set up image generation queue
- [ ] Create admin API endpoints
- [ ] Configure metrics collection
- [ ] Set up alerting thresholds

### Post-Launch
- [ ] Enable email notifications
- [ ] Implement cost analytics
- [ ] Add multi-language support
- [ ] Build admin dashboard UI

---

## File Changes Summary

### New Files to Create
```
app/
├── middleware/
│   ├── __init__.py
│   ├── auth.py
│   ├── rate_limit.py
│   ├── request_id.py
│   └── versioning.py
├── config/
│   ├── __init__.py
│   ├── ai_config.py
│   ├── prompt_config.py
│   ├── feature_flags.py
│   └── loader.py
├── services/
│   ├── ab_testing.py
│   └── ai/
│       ├── __init__.py
│       ├── base.py
│       ├── fal_provider.py
│       ├── openai_provider.py
│       └── factory.py
├── tasks/
│   ├── __init__.py
│   ├── image_tasks.py
│   └── pdf_tasks.py
├── routers/
│   ├── v1/
│   │   ├── __init__.py
│   │   ├── books.py
│   │   ├── orders.py
│   │   └── config.py
│   └── common/
│       ├── __init__.py
│       ├── health.py
│       └── webhooks.py
├── utils/
│   ├── cache.py
│   ├── circuit_breaker.py
│   ├── retry.py
│   └── metrics.py
├── celery_app.py
alembic/
├── env.py
├── versions/
│   └── 001_initial_schema.py
```

### Files to Modify
```
main.py                    # Rename, add middleware, versioning
app/config.py              # Add new env vars, rename prefix
app/utils/logging.py       # Structlog, rename logger
app/utils/security.py      # Enhanced validation
app/services/*.py          # Use config manager, circuit breakers
app/routers/*.py           # Move to v1/, add auth
tests/*.py                 # Update imports, add new tests
.env.example               # New variables
requirements.txt           # Add new dependencies
CLAUDE.md                  # Update documentation
```

---

*Document Version: 1.0*
*Created: 2024-12-12*
*For: GoldenTales (formerly Taleom/DreamWeaver)*
