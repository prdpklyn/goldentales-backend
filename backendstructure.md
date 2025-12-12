# DreamWeaver Backend - File Structure

## Overview

```
Taleom/
├── main.py                     # FastAPI app entry point (thin orchestrator)
├── app/                        # Application package
│   ├── __init__.py
│   ├── config.py               # Configuration with pydantic-settings
│   ├── models/
│   │   ├── __init__.py
│   │   ├── enums.py            # All enums (Theme, ArtStyle, BookFormat, etc.)
│   │   ├── requests.py         # Request models with validation
│   │   └── responses.py        # Response models
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── books.py            # /api/books/* endpoints
│   │   ├── orders.py           # /api/orders/*, /api/shipping-options
│   │   ├── shopify.py          # /api/shopify/* webhooks
│   │   └── config.py           # /, /api/health, /api/config
│   ├── services/
│   │   ├── __init__.py
│   │   ├── story_generator.py  # Gemini AI story generation
│   │   ├── image_generator.py  # Fal.ai image generation
│   │   └── character_service.py # Character profile management
│   └── utils/
│       ├── __init__.py
│       ├── logging.py          # Logging configuration
│       └── security.py         # Webhook verification, sanitization
├── character_system.py         # Character enums, models, bible generator
├── print_production.py         # Print-quality PDF generation (Lulu/Printful)
├── tests/
│   ├── __init__.py
│   ├── conftest.py             # Pytest fixtures
│   ├── test_config.py          # Config endpoint tests
│   └── test_character_system.py # Character system tests
├── requirements.txt
├── .env                        # Environment variables (not in git)
├── .env.example                # Environment template
└── .gitignore
```

---

## File Details

### 1. `main.py` - Entry Point

The thin orchestrator that initializes FastAPI and registers all routers.

```python
from fastapi import FastAPI
from app.config import settings
from app.routers import books_router, orders_router, shopify_router, config_router

app = FastAPI(title="DreamWeaver API", version="2.2.0")

# CORS configured based on environment
# Production: only configured origins
# Development: all origins

app.include_router(config_router)
app.include_router(books_router)
app.include_router(orders_router)
app.include_router(shopify_router)
```

---

### 2. `app/config.py` - Configuration

Centralized configuration using pydantic-settings.

```python
class Settings(BaseSettings):
    # Environment
    environment: Environment = Environment.DEVELOPMENT
    
    # CORS - strict in production
    cors_origins: List[str] = ["http://localhost:3000"]
    
    # API Keys
    fal_key: Optional[str] = Field(alias="FAL_KEY")
    gemini_api_key: Optional[str] = Field(alias="GEMINI_API_KEY")
    
    # Pricing
    price_digital: float = 9.99
    price_softcover: float = 24.99
    price_hardcover: float = 34.99

settings = get_settings()  # Cached singleton
```

---

### 3. `app/routers/books.py` - Books Router

Handles book creation and management.

**Endpoints:**
- `POST /api/books/create` - Create book with character profile
- `GET /api/books/{book_id}` - Get book data
- `GET /api/books/{book_id}/preview` - Get preview images
- `POST /api/books/{book_id}/regenerate-page/{num}` - Regenerate page

**Flow:**
1. CreateBookRequest received
2. CharacterService creates profile and bible
3. StoryGenerator creates 10-page story with Gemini
4. ImageGenerator creates preview images with Fal.ai
5. Book data stored and returned

---

### 4. `app/services/story_generator.py` - Story Generation

Generates personalized stories using Gemini AI.

```python
class StoryGenerator:
    async def generate_story(
        self,
        character_bible: Dict[str, str],
        child_name: str,
        age: int,
        theme: str,
        ...
    ) -> List[Dict]:
        # Returns 10 pages with text, scene_description, mood, etc.
```

---

### 5. `app/services/image_generator.py` - Image Generation

Generates illustrations using Fal.ai with character consistency.

```python
class ImageGenerator:
    # Quality tiers
    MODEL_CONFIGS = {
        GenerationQuality.PREVIEW: {"model": "fal-ai/flux/schnell"},
        GenerationQuality.STANDARD: {"model": "fal-ai/flux-pro"},
        GenerationQuality.PRINT: {"model": "fal-ai/flux-pro/v1.1"},
    }
    
    async def generate_illustration(
        self,
        character_bible: Dict[str, str],  # Included in EVERY prompt
        scene_description: str,
        ...
    ) -> Dict[str, Any]:
```

---

### 6. `app/services/character_service.py` - Character Management

Creates character profiles and generates the character bible.

```python
class CharacterService:
    async def create_profile(
        self,
        child_name: str,
        child_gender: Gender,
        skin_tone: SkinTone,
        hair_color: HairColor,
        ...
    ) -> Tuple[CharacterProfile, Dict[str, str]]:
        # Returns (profile, character_bible)
```

---

### 7. `app/routers/shopify.py` - Shopify Integration

Handles Shopify webhooks with proper security.

```python
@router.post("/webhooks/orders/create")
async def handle_order_created(request: Request):
    # 1. Verify HMAC signature (required in production)
    # 2. Extract book_id from order
    # 3. Trigger print production or digital delivery
```

**Security:**
- HMAC-SHA256 signature verification
- No bypass in production (unlike original code)
- Proper error logging

---

### 8. `app/utils/security.py` - Security Utilities

```python
def verify_webhook_signature(body: bytes, signature: str) -> bool:
    # In production: Always requires valid signature
    # In development: Logs warning if secret not set

def sanitize_input(text: str) -> str:
    # Removes prompt injection patterns
    # Limits length
    # Removes dangerous characters

def validate_content_safety(text: str) -> Tuple[bool, Optional[str]]:
    # Checks for blocked words (violence, adult content, etc.)
```

---

### 9. `character_system.py` - Character Consistency Core

The heart of the character consistency system.

**Enums:**
- Gender, SkinTone, HairColor, HairStyle, EyeColor, BodyType
- AdditionalCharacterType (sibling, parent, pet, etc.)

**Models:**
- MainCharacter, AdditionalCharacter, CharacterProfile
- CharacterAccessories, CharacterClothing, DistinctiveFeatures

**Key Class:**
```python
class CharacterDescriptionGenerator:
    def generate_main_character_description(char: MainCharacter) -> str
    def generate_full_character_bible(profile: CharacterProfile) -> Dict
    def build_page_prompt(character_bible, scene, action, mood, style) -> str
```

---

### 10. `print_production.py` - Print Pipeline

Converts preview images to print-ready output after payment.

**Classes:**
- `PrintConfig` - Book sizes, bleed, DPI settings
- `PrintImageGenerator` - High-res image generation
- `PrintImageProcessor` - CMYK conversion, resolution
- `PrintPDFGenerator` - PDF with bleed margins
- `PrintProductionPipeline` - Orchestrates the full process

---

## Data Flow

```
┌────────────────────────────────────────────────────────────────┐
│                      CREATE BOOK FLOW                          │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  Frontend Request                                              │
│       ↓                                                        │
│  POST /api/books/create                                        │
│       ↓                                                        │
│  CharacterService.create_profile()                             │
│       ↓                                                        │
│  Character Bible Generated                                     │
│       ↓                                                        │
│  StoryGenerator.generate_story(bible, ...)                     │
│       ↓                                                        │
│  10 Story Pages with Scene Descriptions                        │
│       ↓                                                        │
│  ImageGenerator.generate_all_illustrations(bible, pages)       │
│       ↓                                                        │
│  Preview Images (fast, cheap)                                  │
│       ↓                                                        │
│  Book Response to Frontend                                     │
│                                                                │
└────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│                      ORDER FLOW                                │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  Shopify Order Created                                         │
│       ↓                                                        │
│  POST /api/shopify/webhooks/orders/create                      │
│       ↓                                                        │
│  Verify HMAC Signature                                         │
│       ↓                                                        │
│  Extract book_id from order                                    │
│       ↓                                                        │
│  ┌─────────────────┬─────────────────┐                         │
│  │    DIGITAL      │     PRINT       │                         │
│  ├─────────────────┼─────────────────┤                         │
│  │ Generate PDF    │ Generate hi-res │                         │
│  │ Email to        │ Create PDF      │                         │
│  │ customer        │ Send to Lulu    │                         │
│  └─────────────────┴─────────────────┘                         │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

---

## Running the Backend

```bash
# Development
uvicorn main:app --reload --port 8000

# Production
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# Tests
pytest tests/ -v
```

---

## Environment Variables

See `.env.example` for complete list.

**Required:**
```
FAL_KEY=your_fal_key
GEMINI_API_KEY=your_gemini_key
```

**Production:**
```
ENVIRONMENT=production
CORS_ORIGINS=["https://taleom.lovable.app"]
SHOPIFY_WEBHOOK_SECRET=whsec_xxxxx
```