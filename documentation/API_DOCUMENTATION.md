# GoldenTales API - Complete Documentation

**Base URL**: `http://localhost:8000` (development)  
**API Version**: 3.0.0  
**Last Updated**: December 13, 2024

---

## 📋 Documentation Status

✅ **Complete and Verified**: This documentation has been verified against the actual codebase implementation. All request/response examples match the actual API behavior.

### What's Included

- ✅ Complete request payloads with all required and optional fields
- ✅ Complete response payloads with all fields documented
- ✅ Field types, constraints, and descriptions
- ✅ Error responses for all endpoints
- ✅ Enum values with exact strings used by the API
- ✅ Example requests and responses
- ✅ Field-by-field breakdowns

---

## Table of Contents

1. [Quick Reference](#quick-reference)
2. [Create Book API](#create-book-api)
3. [Get Book API](#get-book-api)
4. [Get Book Preview API](#get-book-preview-api)
5. [Regenerate Page API](#regenerate-page-api)
6. [Get Book Price API](#get-book-price-api)
7. [Create Order API](#create-order-api)
8. [Get Order Status API](#get-order-status-api)
9. [Get Shipping Options API](#get-shipping-options-api)
10. [Enums Reference](#enums-reference)

---

## Quick Reference

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|--------------|
| `POST` | `/api/books/create` | Create a personalized storybook | Optional |
| `GET` | `/api/books/{book_id}` | Get book details | Optional |
| `GET` | `/api/books/{book_id}/preview` | Get preview images | Optional |
| `POST` | `/api/books/{book_id}/regenerate-page/{page_number}` | Regenerate a page illustration | Optional |
| `GET` | `/api/books/{book_id}/price` | Calculate book price | Optional |
| `POST` | `/api/orders/create` | Create an order | Optional |
| `GET` | `/api/orders/{order_id}/status` | Get order status | Optional |
| `GET` | `/api/shipping-options` | Get shipping options | Optional |

**Note**: All endpoints support optional API key authentication via `X-API-Key` header. In development mode, API keys are not required.

---

## Create Book API

### Endpoint
```
POST /api/books/create
```

### Request Headers
```http
Content-Type: application/json
X-API-Key: your-api-key (optional in dev mode)
```

### Request Body

**Complete Request Example:**
```json
{
  "child_name": "Emma",
  "child_gender": "girl",
  "child_age": 6,
  "skin_tone": "light skin",
  "hair_color": "brown hair",
  "hair_style": "hair in pigtails",
  "eye_color": "blue eyes",
  "body_type": "average build",
  "has_glasses": false,
  "glasses_type": null,
  "has_freckles": true,
  "has_dimples": false,
  "other_features": null,
  "favorite_outfit": "purple dress with white dots",
  "favorite_color": "purple",
  "photo_url": null,
  "additional_characters": [
    {
      "name": "Max",
      "character_type": "pet",
      "relationship": "pet dog",
      "gender": null,
      "age_description": null,
      "skin_tone": null,
      "hair_color": null,
      "pet_species": "golden retriever",
      "pet_color": "golden",
      "distinctive_feature": "red collar"
    }
  ],
  "theme": "christmas",
  "art_style": "watercolor",
  "occasion": "birthday",
    "special_details": "Emma loves unicorns and fairy tales"
}
```

### Required Fields

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `child_name` | string | 2-30 chars, letters/spaces/apostrophes/hyphens only | Child's name |
| `child_gender` | enum | "boy" or "girl" | Child's gender |
| `child_age` | integer | 2-12 | Child's age |
| `skin_tone` | enum | See [Skin Tone](#skin-tone) | Skin tone |
| `hair_color` | enum | See [Hair Color](#hair-color) | Hair color |
| `hair_style` | enum | See [Hair Style](#hair-style) | Hair style |
| `eye_color` | enum | See [Eye Color](#eye-color) | Eye color (default: "brown eyes") |
| `body_type` | enum | See [Body Type](#body-type) | Body type (default: "average build") |
| `theme` | enum | See [Theme](#theme) | Story theme |
| `art_style` | enum | See [Art Style](#art-style) | Illustration style |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `has_glasses` | boolean | Whether child wears glasses (default: false) |
| `glasses_type` | string | Description of glasses (e.g., "round pink glasses") |
| `has_freckles` | boolean | Whether child has freckles (default: false) |
| `has_dimples` | boolean | Whether child has dimples (default: false) |
| `other_features` | string | Other distinctive features (e.g., "birthmark on cheek") |
| `favorite_outfit` | string | Favorite outfit description |
| `favorite_color` | string | Favorite color |
| `photo_url` | string | URL to photo for character extraction |
| `occasion` | string | Special occasion (e.g., "birthday", "Christmas") |
| `special_details` | string | Max 500 chars, personalization details |
| `additional_characters` | array | List of additional characters (see below) |

### Additional Character Object

```json
{
  "name": "Max",
  "character_type": "pet",
  "relationship": "pet dog",
  "gender": null,
  "age_description": null,
  "skin_tone": null,
  "hair_color": null,
  "pet_species": "golden retriever",
  "pet_color": "golden",
  "distinctive_feature": "red collar"
}
```

**For Human Characters:**
```json
{
  "name": "Lily",
  "character_type": "sibling",
  "relationship": "little sister",
  "gender": "girl",
  "age_description": "4-year-old",
  "skin_tone": "light skin",
  "hair_color": "blonde hair",
  "pet_species": null,
  "pet_color": null,
  "distinctive_feature": "always wears a pink bow"
}
```

### Response

**Status Code**: `200 OK`

**Response Body:**
```json
{
  "book_id": "abc12345",
  "title": "Emma's Christmas Adventure",
  "child_name": "Emma",
  "child_age": 6,
  "theme": "christmas",
  "art_style": "watercolor",
  "pages": [
    {
      "page_number": 1,
      "text": "Emma woke up on Christmas morning to find snow falling outside her window. She ran to the window, her brown pigtails bouncing with excitement.",
      "scene_description": "Emma, a 6-year-old girl with light skin, brown hair in pigtails, blue eyes, and freckles, wearing a purple dress. Scene: Cozy bedroom with Christmas decorations, snow falling outside the window.",
      "character_action": "running to the window",
      "mood": "excited",
      "characters_in_scene": ["Emma"]
    },
    {
      "page_number": 2,
      "text": "She put on her warm coat and boots, ready for an adventure. Her dog Max wagged his tail, eager to join her.",
      "scene_description": "Emma, a 6-year-old girl with light skin, brown hair in pigtails, blue eyes, and freckles, wearing a purple dress and warm coat. Scene: Front door area with winter gear, Max the golden retriever with red collar nearby.",
      "character_action": "putting on winter gear",
      "mood": "happy",
      "characters_in_scene": ["Emma", "Max"]
    }
    // ... 8 more pages (total of 10 pages)
  ],
  "preview_images": [
    "https://fal.ai/files/abc123/image1.jpg",
    "https://fal.ai/files/abc123/image2.jpg",
    "https://fal.ai/files/abc123/image3.jpg",
    "https://fal.ai/files/abc123/image4.jpg",
    "https://fal.ai/files/abc123/image5.jpg",
    "https://fal.ai/files/abc123/image6.jpg",
    "https://fal.ai/files/abc123/image7.jpg",
    "https://fal.ai/files/abc123/image8.jpg",
    "https://fal.ai/files/abc123/image9.jpg",
    "https://fal.ai/files/abc123/image10.jpg"
  ],
  "page_count": 10,
  "character_bible": {
    "main_character": "Emma, a 6-year-old girl with light skin, brown hair in pigtails, blue eyes, freckles on her cheeks, wearing a purple dress with white dots",
    "main_character_short": "Emma, 6-year-old girl",
    "additional_characters": [
      "Max the golden retriever (pet dog) with golden fur and red collar"
    ],
    "all_characters_summary": "Emma, a 6-year-old girl with light skin, brown hair in pigtails, blue eyes, freckles on her cheeks, wearing a purple dress with white dots. Also featuring: Max the golden retriever (pet dog) with golden fur and red collar"
  },
  "created_at": "2024-12-13T10:30:45.123456",
  "status": "preview"
}
```

**Note**: The `preview_images` array contains exactly 10 image URLs, one for each page. The order matches the pages array (index 0 = page 1, index 1 = page 2, etc.).

### Page Object Structure

Each page in the `pages` array contains:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `page_number` | integer | Yes | Page number (1-10) |
| `text` | string | Yes | Story text for this page (2-3 sentences, 25-40 words) |
| `scene_description` | string | Yes | Detailed scene description including character appearance. Always starts with character description for consistency. |
| `character_action` | string | Yes | What the main character is doing (e.g., "running to the window", "putting on winter gear") |
| `mood` | string | Yes | Mood: "happy", "excited", "curious", "brave", "peaceful", "magical", "cozy" |
| `characters_in_scene` | array | Yes | List of character names in this scene (e.g., ["Emma"] or ["Emma", "Max"]) |

**Important Notes:**
- Each page always has exactly these 6 fields
- `scene_description` always includes the full character appearance description at the start
- `preview_images` array index corresponds to page number (index 0 = page 1, index 1 = page 2, etc.)
- Pages are always returned in order (page 1 through page 10)

### Character Bible Structure

The `character_bible` object contains:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `main_character` | string | Yes | Full detailed description of main character including all physical features, clothing, and distinctive features |
| `main_character_short` | string | Yes | Short description format: "{name}, {age}-year-old {gender}" |
| `additional_characters` | array | Yes | List of additional character descriptions (empty array if none) |
| `all_characters_summary` | string | Yes | Combined description of all characters, formatted as: "{main_character}. Also featuring: {additional_characters}" (or just main_character if no additional characters) |

**Example Character Bible:**
```json
{
  "main_character": "Emma, a 6-year-old girl with light skin, brown hair in pigtails, blue eyes, freckles on her cheeks, wearing a purple dress with white dots",
  "main_character_short": "Emma, 6-year-old girl",
  "additional_characters": [
    "Max the golden retriever (pet dog) with golden fur and red collar"
  ],
  "all_characters_summary": "Emma, a 6-year-old girl with light skin, brown hair in pigtails, blue eyes, freckles on her cheeks, wearing a purple dress with white dots. Also featuring: Max the golden retriever (pet dog) with golden fur and red collar"
}
```

**Note**: The character bible is used in every image generation prompt to ensure character consistency across all pages.

### Error Responses

**400 Bad Request:**
```json
{
  "detail": "Name can only contain letters, spaces, apostrophes, and hyphens"
}
```

**500 Internal Server Error:**
```json
{
  "detail": "Failed to create book"
}
```

---

## Get Book API

### Endpoint
```
GET /api/books/{book_id}
```

### Response

Same structure as Create Book response (see above).

**404 Not Found:**
```json
{
  "detail": "Book not found"
}
```

---

## Get Book Preview API

### Endpoint
```
GET /api/books/{book_id}/preview
```

### Response

**Status Code**: `200 OK`

```json
{
  "book_id": "abc12345",
  "title": "Emma's Christmas Adventure",
  "preview_images": [
    "https://fal.ai/files/abc123/image1.jpg",
    "https://fal.ai/files/abc123/image2.jpg",
    "https://fal.ai/files/abc123/image3.jpg",
    "https://fal.ai/files/abc123/image4.jpg",
    "https://fal.ai/files/abc123/image5.jpg",
    "https://fal.ai/files/abc123/image6.jpg",
    "https://fal.ai/files/abc123/image7.jpg",
    "https://fal.ai/files/abc123/image8.jpg",
    "https://fal.ai/files/abc123/image9.jpg",
    "https://fal.ai/files/abc123/image10.jpg"
  ],
  "page_count": 10
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `book_id` | string | Unique book identifier |
| `title` | string | Book title |
| `preview_images` | array | Array of exactly 10 image URLs, one per page |
| `page_count` | integer | Total number of pages (always 10) |

**404 Not Found:**
```json
{
  "detail": "Book not found"
}
```

---

## Regenerate Page API

### Endpoint
```
POST /api/books/{book_id}/regenerate-page/{page_number}
```

### Request Body

```json
{
  "scene_description": "Emma playing in a magical forest with unicorns",
  "character_action": "running through the forest",
  "mood": "magical",
  "include_characters": ["Emma", "Max"]
}
```

**All fields are optional** - if omitted, values from the original page are used.

### Response

**Status Code**: `200 OK`

```json
{
  "book_id": "abc12345",
  "page_number": 3,
  "new_image_url": "https://fal.ai/files/abc123/image3_new.jpg",
  "status": "success"
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `book_id` | string | Book identifier |
| `page_number` | integer | Page number that was regenerated |
| `new_image_url` | string | URL of the newly generated image |
| `status` | string | Always "success" on successful regeneration |

**Note**: The new image URL replaces the corresponding entry in the book's `preview_images` array.

**Error Responses:**

**400 Bad Request:**
```json
{
  "detail": "Character profile not found"
}
```
or
```json
{
  "detail": "Invalid page number"
}
```

**404 Not Found:**
```json
{
  "detail": "Book not found"
}
```

**500 Internal Server Error:**
```json
{
  "detail": "Failed to regenerate: {error message}"
}
```

---

## Get Book Price API

### Endpoint
```
GET /api/books/{book_id}/price?format={format}&shipping={shipping}&gift_wrap={gift_wrap}
```

### Query Parameters

| Parameter | Type | Required | Values |
|-----------|------|----------|--------|
| `format` | enum | Yes | "digital", "softcover", "hardcover" |
| `shipping` | enum | Yes | "digital", "standard", "express" |
| `gift_wrap` | boolean | No | true/false (default: false) |

### Example Request
```
GET /api/books/abc12345/price?format=hardcover&shipping=standard&gift_wrap=true
```

### Response

**Status Code**: `200 OK`

```json
{
  "book_id": "abc12345",
  "format": "hardcover",
  "base_price": 34.99,
  "shipping_cost": 5.99,
  "gift_wrap_cost": 5.00,
  "total": 45.98,
  "currency": "USD"
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `book_id` | string | Book identifier |
| `format` | string | Book format: "digital", "softcover", or "hardcover" |
| `base_price` | float | Base price of the book format (USD) |
| `shipping_cost` | float | Shipping cost (0 for digital, 5.99 for standard, 14.99 for express) |
| `gift_wrap_cost` | float | Gift wrap cost (5.00 if gift_wrap=true and format is not digital, otherwise 0) |
| `total` | float | Total price rounded to 2 decimal places (base_price + shipping_cost + gift_wrap_cost) |
| `currency` | string | Always "USD" |

**Price Reference:**
- Digital: $9.99
- Softcover: $24.99
- Hardcover: $34.99
- Standard Shipping: $5.99
- Express Shipping: $14.99
- Gift Wrap: $5.00

**404 Not Found:**
```json
{
  "detail": "Book not found"
}
```

---

## Create Order API

### Endpoint
```
POST /api/orders/create
```

### Request Body

**Complete Request Example:**
```json
{
  "book_id": "abc12345",
  "format": "hardcover",
  "shipping_tier": "standard",
  "gift_wrap": true,
  "gift_message": "Happy Birthday! Love, Grandma",
  "recipient_email": "recipient@example.com",
  "recipient_address": {
    "name": "Emma Smith",
    "street": "123 Main St",
    "city": "San Francisco",
    "state": "CA",
    "postal_code": "94102",
    "country": "USA"
  }
}
```

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `book_id` | string | Book ID from book creation |
| `format` | enum | "digital", "softcover", "hardcover" |
| `shipping_tier` | enum | "digital", "standard", "express" |

### Optional Fields

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `gift_wrap` | boolean | default: false | Whether to gift wrap |
| `gift_message` | string | max 200 chars | Gift message |
| `recipient_email` | string | email format | Recipient email |
| `recipient_address` | object | See below | Shipping address |

### Recipient Address Object

```json
{
  "name": "Emma Smith",
  "street": "123 Main St",
  "city": "San Francisco",
  "state": "CA",
  "postal_code": "94102",
  "country": "USA"
}
```

### Response

**Status Code**: `200 OK`

```json
{
  "order_id": "order123",
  "book_id": "abc12345",
  "book_title": "Emma's Christmas Adventure",
  "total": 45.98,
  "status": "pending_payment",
  "estimated_delivery": "Dec 20",
  "checkout_url": "/checkout/order123"
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `order_id` | string | Unique order identifier (8-character UUID) |
| `book_id` | string | Book identifier from book creation |
| `book_title` | string | Title of the book |
| `total` | float | Total order amount in USD (matches price calculation) |
| `status` | string | Order status, always "pending_payment" for new orders |
| `estimated_delivery` | string | Estimated delivery date (e.g., "Dec 20", "Instant" for digital) |
| `checkout_url` | string | Relative URL path for checkout (e.g., "/checkout/order123") |

**Note**: The order is created but payment is not processed. The `checkout_url` should be used to redirect the user to complete payment.

**Error Responses:**

**404 Not Found:**
```json
{
  "detail": "Book not found"
}
```

### Error Responses

**404 Not Found:**
```json
{
  "detail": "Book not found"
}
```

---

## Get Order Status API

### Endpoint
```
GET /api/orders/{order_id}/status
```

### Response

**Status Code**: `200 OK`

```json
{
  "order_id": "order123",
  "status": "processing",
  "steps": [
    {
      "name": "Order Received",
      "status": "completed"
    },
    {
      "name": "Payment Confirmed",
      "status": "completed"
    },
    {
      "name": "Generating Print Files",
      "status": "in_progress"
    },
    {
      "name": "Sent to Printer",
      "status": "pending"
    },
    {
      "name": "Shipped",
      "status": "pending"
    },
    {
      "name": "Delivered",
      "status": "pending"
    }
  ]
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `order_id` | string | Order identifier |
| `status` | string | Overall order status (e.g., "processing", "pending_payment", "shipped") |
| `steps` | array | Array of order processing steps |

**Step Object Structure:**

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Step name (e.g., "Order Received", "Payment Confirmed") |
| `status` | string | Step status: "completed", "in_progress", or "pending" |

**Note**: This is a mock response. In production, this would fetch actual order status from the database.

### Order Status Values

- `pending_payment`
- `payment_confirmed`
- `generating_print_files`
- `creating_pdf`
- `uploading_to_printer`
- `sent_to_printer`
- `printing`
- `shipped`
- `delivered`
- `failed`

---

## Get Shipping Options API

### Endpoint
```
GET /api/shipping-options
```

### Response

**Status Code**: `200 OK`

```json
{
  "options": [
    {
      "tier": "digital",
      "name": "Digital PDF",
      "description": "Instant download",
      "available": true,
      "estimated_arrival": "Instant"
    },
    {
      "tier": "standard",
      "name": "Standard Shipping",
      "description": "Order by Dec 15 for Christmas",
      "available": true,
      "deadline": "2024-12-15T00:00:00",
      "estimated_arrival": "Dec 20",
      "days_until_deadline": 2
    },
    {
      "tier": "express",
      "name": "Express Shipping",
      "description": "Fast delivery",
      "available": true,
      "deadline": "2024-12-21T00:00:00",
      "estimated_arrival": "Dec 24",
      "days_until_deadline": 8
    }
  ],
  "countdown": {
    "expired": false,
    "days": 2,
    "hours": 14,
    "minutes": 30,
    "urgency": "critical",
    "deadline": "December 15"
  }
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `options` | array | List of shipping options |
| `countdown` | object | Countdown to shipping deadline |

**Shipping Option Object:**

| Field | Type | Description |
|-------|------|-------------|
| `tier` | string | Shipping tier: "digital", "standard", or "express" |
| `name` | string | Display name |
| `description` | string | Description text |
| `available` | boolean | Whether this option is currently available |
| `estimated_arrival` | string | Estimated arrival date (e.g., "Dec 20", "Instant") |
| `deadline` | string | ISO 8601 deadline date (only for standard/express) |
| `days_until_deadline` | integer | Days until deadline (0 if expired, only for standard/express) |

**Countdown Object:**

| Field | Type | Description |
|-------|------|-------------|
| `expired` | boolean | Whether the deadline has passed |
| `days` | integer | Days remaining |
| `hours` | integer | Hours remaining (0-23) |
| `minutes` | integer | Minutes remaining (0-59) |
| `urgency` | string | Urgency level: "normal", "warning", "urgent", "critical", or "expired" |
| `deadline` | string | Formatted deadline date (e.g., "December 15") |

**Note**: The countdown is based on the standard shipping deadline for Christmas delivery. Digital shipping is always available.

---

## Enums Reference

### Gender
- `"boy"`
- `"girl"`

### Skin Tone
- `"very light/pale skin"`
- `"light skin"`
- `"light olive/medium-light skin"`
- `"medium/olive skin"`
- `"medium-dark/tan skin"`
- `"dark brown skin"`
- `"very dark/deep brown skin"`

### Hair Color
- `"black hair"`
- `"dark brown hair"`
- `"brown hair"`
- `"light brown hair"`
- `"auburn/reddish-brown hair"`
- `"red/ginger hair"`
- `"strawberry blonde hair"`
- `"blonde hair"`
- `"platinum/white blonde hair"`
- `"gray hair"`
- `"white hair"`

### Hair Style
- `"very short buzz cut"`
- `"short neat hair"`
- `"short messy/tousled hair"`
- `"short curly hair"`
- `"medium-length straight hair"`
- `"medium-length wavy hair"`
- `"medium-length curly hair"`
- `"bob haircut"`
- `"long straight hair"`
- `"long wavy hair"`
- `"long curly hair"`
- `"hair in a ponytail"`
- `"hair in pigtails"`
- `"hair in braids"`
- `"hair in a bun"`
- `"afro hairstyle"`
- `"locs/dreadlocks"`

### Eye Color
- `"brown eyes"`
- `"dark brown eyes"`
- `"hazel eyes"`
- `"green eyes"`
- `"blue eyes"`
- `"gray eyes"`
- `"amber eyes"`

### Body Type
- `"slim build"`
- `"average build"`
- `"athletic build"`
- `"stocky/sturdy build"`
- `"chubby/round build"`

### Theme
- `"christmas"`
- `"space"`
- `"ocean"`
- `"forest"`
- `"dinosaur"`
- `"superhero"`
- `"birthday"`
- `"bedtime"`

### Art Style
- `"watercolor"`
- `"cartoon"`
- `"anime"`
- `"storybook"`
- `"pixar"`
- `"ghibli"`

### Book Format
- `"digital"`
- `"softcover"`
- `"hardcover"`

### Shipping Tier
- `"digital"`
- `"standard"`
- `"express"`

### Additional Character Type
- `"sibling"`
- `"friend"`
- `"pet"`
- `"parent"`
- `"grandparent"`
- `"other"`

---

## Error Responses

All endpoints may return these error responses:

### 400 Bad Request
```json
{
  "detail": "Error message describing the validation error"
}
```

### 401 Unauthorized
```json
{
  "error": "unauthorized",
  "message": "API key is required",
  "detail": "Provide API key in X-API-Key header"
}
```

### 404 Not Found
```json
{
  "detail": "Resource not found"
}
```

### 429 Too Many Requests
```json
{
  "error": "rate_limit_exceeded",
  "message": "Rate limit exceeded. Too many requests per minute.",
  "tier": "standard",
  "limit": 60,
  "retry_after": 60
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error message"
}
```

---

## Notes

1. **Book Creation Time**: Creating a book takes 30-60 seconds as it generates:
   - 10-page story using Gemini AI
   - 10 preview images using Fal.ai
   - Character bible for consistency

2. **Character Consistency**: The character bible ensures the child looks identical across all pages. It's included in every image generation prompt.

3. **Preview vs Print Quality**: 
   - Preview images: Fast, low-cost (~$0.02/image)
   - Print images: High-quality, expensive (~$0.10/image), generated after payment

4. **API Keys**: In development mode, API keys are optional. Set `API_KEY_REQUIRED=false` in your environment.

5. **Rate Limiting**: Disabled by default in development. Set `RATE_LIMIT_ENABLED=true` to enable.

---

## Testing

### Using curl

```bash
# Create a book
curl -X POST http://localhost:8000/api/books/create \
  -H "Content-Type: application/json" \
  -d '{
    "child_name": "Emma",
    "child_gender": "girl",
    "child_age": 6,
    "skin_tone": "light skin",
    "hair_color": "brown hair",
    "hair_style": "hair in pigtails",
    "eye_color": "blue eyes",
    "body_type": "average build",
    "theme": "christmas",
    "art_style": "watercolor"
  }' | python -m json.tool
```

### Using FastAPI Docs

Visit http://localhost:8000/docs for interactive API documentation.

---

**Last Updated**: December 13, 2024

