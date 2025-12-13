# GoldenTales Backend

> AI-powered personalized children's storybook generation service

## Purpose

FastAPI backend that generates personalized children's storybooks using AI. Handles story generation, image creation with character consistency, and print production after Shopify orders.

## Core Responsibilities

1. Generate stories via Gemini AI
2. Generate illustrations via Fal.ai with character consistency
3. Process Shopify webhooks to trigger print production
4. Create print-ready PDFs for fulfillment

---

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
# Edit .env with your API keys

# Run development server
uvicorn main:app --reload --port 8000

# Run tests
pytest tests/ -v
```

---

## Project Structure

```
Taleom/
├── main.py                     # FastAPI app entry point
├── app/                        # Application package
│   ├── config.py               # Configuration with pydantic-settings
│   ├── models/
│   │   ├── enums.py            # All enums (Theme, ArtStyle, etc.)
│   │   ├── requests.py         # Request models with validation
│   │   └── responses.py        # Response models
│   ├── routers/
│   │   ├── books.py            # /api/books/* endpoints
│   │   ├── orders.py           # /api/orders/* endpoints
│   │   ├── shopify.py          # /api/shopify/* webhooks
│   │   └── config.py           # /, /api/health, /api/config
│   ├── services/
│   │   ├── story_generator.py  # Gemini AI story generation
│   │   ├── image_generator.py  # Fal.ai image generation
│   │   ├── character_service.py # Character profile management
│   │   └── print_service.py    # Print production and Lulu integration
│   └── utils/
│       ├── logging.py          # Logging configuration
│       └── security.py         # Webhook verification, sanitization
├── character_system.py         # Character enums and bible generator
├── tests/                      # Test suite
├── requirements.txt
└── .env.example
```

---

## API Endpoints

### Books

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/books/create` | Create book with character profile |
| `GET` | `/api/books/{book_id}` | Get book data |
| `GET` | `/api/books/{book_id}/preview` | Get preview images |
| `POST` | `/api/books/{book_id}/regenerate-page/{num}` | Regenerate single page |

### Orders

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/books/{book_id}/price` | Calculate price |
| `POST` | `/api/orders/create` | Create order |
| `GET` | `/api/orders/{order_id}/status` | Get order status |
| `GET` | `/api/shipping-options` | Get shipping options |

### Config

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Root / health check |
| `GET` | `/api/health` | Detailed health check |
| `GET` | `/api/config` | Public configuration |

### Shopify Webhooks

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/shopify/webhooks/orders/create` | Order created |
| `POST` | `/api/shopify/webhooks/orders/fulfilled` | Order fulfilled |
| `POST` | `/api/shopify/webhooks/orders/cancelled` | Order cancelled |

---

## Character Consistency System

The critical challenge: ensuring the child looks identical across all 10+ pages.

### Solution: Character Bible

Before generating any images, create a detailed character description used in EVERY prompt:

```python
character_bible = {
    "main_character": "a 6-year-old girl named Emma, light skin, brown hair in pigtails, blue eyes, with freckles, wearing purple clothes",
    "main_character_short": "Emma, 6-year-old girl",
    "additional_characters": ["Max the golden retriever with red collar"]
}
```

### Character Attributes

- **Gender**: boy, girl
- **Skin Tone**: 7 options (very light → very dark)
- **Hair Color**: 11 options (black → white)
- **Hair Style**: 18 options (short, medium, long, styled)
- **Eye Color**: 7 options
- **Body Type**: 5 options

---

## Two-Stage Image Generation

### Stage 1: Preview (On Create)
- **Model**: Flux Schnell (fast)
- **Resolution**: 800×600
- **Cost**: ~$0.02/image
- **Purpose**: User approval before purchase

### Stage 2: Print (After Payment)
- **Model**: Flux Pro 1.1 (quality)
- **Resolution**: 2400×1800 (300 DPI)
- **Cost**: ~$0.10/image
- **Purpose**: Print-ready output

---

## Environment Variables

See `.env.example` for all available options.

**Required:**
- `FAL_KEY` - Fal.ai for image generation
- `GEMINI_API_KEY` - Google AI for story generation

**Shopify:**
- `SHOPIFY_WEBHOOK_SECRET` - Webhook verification

**Fulfillment:**
- `PRINTFUL_API_KEY` or `LULU_API_KEY`

---

## Security

- **CORS**: Configured per environment (strict in production)
- **Webhook Verification**: HMAC-SHA256 signature validation
- **Input Sanitization**: Prompt injection prevention
- **Content Safety**: Blocked words filter for children's content

---

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html

# Run specific test file
pytest tests/test_character_system.py -v
```

---

## Key Constraints

1. **Character Consistency**: Use character bible in EVERY image prompt
2. **Cost Control**: Preview = cheap/fast, Print = quality (only after payment)
3. **Child Safety**: All content must be age-appropriate
4. **Print Quality**: 300 DPI, CMYK, proper bleed margins
5. **Webhook Reliability**: Signature verification required in production