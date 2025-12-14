# API Testing Guide - Create Book & Create Order

Complete guide for testing the Create Book and Create Order endpoints.

---

## 🚀 Quick Start

### 1. Start the Server

```bash
# Activate virtual environment (if using)
source venv/bin/activate

# Start server
uvicorn main:app --reload --port 8000
```

Server will be available at: **http://localhost:8000**

---

## 📚 Create Book API

### Endpoint
```
POST /api/v1/books/create
```

### Request Body Example

```json
{
  "child_name": "Emma",
  "child_gender": "girl",
  "child_age": 6,
  "skin_tone": "light",
  "hair_color": "brown",
  "hair_style": "pigtails",
  "eye_color": "blue",
  "body_type": "average",
  "has_freckles": true,
  "favorite_color": "purple",
  "theme": "adventure",
  "art_style": "watercolor",
  "occasion": "birthday",
    "special_details": "Emma loves unicorns and fairy tales"
}
```

### Required Fields

- `child_name` (string, 2-30 chars)
- `child_gender` (enum: "boy", "girl")
- `child_age` (int, 2-12)
- `skin_tone` (enum: see below)
- `hair_color` (enum: see below)
- `hair_style` (enum: see below)
- `eye_color` (enum: see below)
- `body_type` (enum: see below)
- `theme` (enum: "adventure", "fantasy", "mystery", "friendship", "nature", "space", "ocean", "animals", "sports", "music")
- `art_style` (enum: "watercolor", "digital_art", "cartoon", "realistic", "sketch", "pastel")

### Optional Fields

- `has_glasses` (boolean)
- `glasses_type` (string)
- `has_freckles` (boolean)
- `has_dimples` (boolean)
- `other_features` (string)
- `favorite_outfit` (string)
- `favorite_color` (string)
- `photo_url` (string, URL)
- `occasion` (string)
- `special_details` (string, max 500 chars)
- `additional_characters` (array)

### Response Example

```json
{
  "book_id": "abc12345",
  "title": "Emma's Adventure Adventure",
  "child_name": "Emma",
  "child_age": 6,
  "theme": "adventure",
  "art_style": "watercolor",
  "pages": [...],
  "preview_images": ["url1", "url2", ...],
  "page_count": 10,
  "character_bible": {...},
  "created_at": "2024-12-13T10:30:00",
  "status": "preview"
}
```

---

## 🛒 Create Order API

### Endpoint
```
POST /api/v1/orders/create
```

### Request Body Example

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

- `book_id` (string) - ID from book creation
- `format` (enum: "digital", "softcover", "hardcover")
- `shipping_tier` (enum: "digital", "standard", "express")

### Optional Fields

- `gift_wrap` (boolean, default: false)
- `gift_message` (string, max 200 chars)
- `recipient_email` (string, email)
- `recipient_address` (object)

### Response Example

```json
{
  "order_id": "order123",
  "book_id": "abc12345",
  "book_title": "Emma's Adventure Adventure",
  "total": 34.99,
  "status": "pending_payment",
  "estimated_delivery": "Dec 20",
  "checkout_url": "/checkout/order123"
}
```

---

## 🧪 Testing Methods

### Method 1: Using the Python Test Script (Recommended)

```bash
# Run comprehensive test suite
python test_create_book_and_order.py

# With API key
export API_KEY=your-api-key
python test_create_book_and_order.py
```

This script will:
1. Create a book
2. Get book details
3. Get book preview
4. Calculate prices
5. Create an order
6. Get order status
7. Get shipping options

### Method 2: Using the Bash Script

```bash
./test_book_order_examples.sh

# With API key
export API_KEY=your-api-key
./test_book_order_examples.sh
```

### Method 3: Using curl

#### Create Book
```bash
curl -X POST http://localhost:8000/api/v1/books/create \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "child_name": "Emma",
    "child_gender": "girl",
    "child_age": 6,
    "skin_tone": "light",
    "hair_color": "brown",
    "hair_style": "pigtails",
    "eye_color": "blue",
    "body_type": "average",
    "theme": "adventure",
    "art_style": "watercolor"
  }' | python -m json.tool
```

#### Create Order
```bash
curl -X POST http://localhost:8000/api/v1/orders/create \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "book_id": "abc12345",
    "format": "hardcover",
    "shipping_tier": "standard",
    "gift_wrap": true
  }' | python -m json.tool
```

### Method 4: Using FastAPI Interactive Docs

1. Open http://localhost:8000/docs
2. Find `POST /api/v1/books/create`
3. Click "Try it out"
4. Fill in the request body
5. Click "Execute"

---

## 📋 Available Enums

### Skin Tone
```
"very_light", "light", "medium_light", "medium", 
"medium_dark", "dark", "very_dark"
```

### Hair Color
```
"black", "dark_brown", "brown", "light_brown", 
"blonde", "strawberry_blonde", "red", "auburn", 
"gray", "white", "other"
```

### Hair Style
```
"short", "medium", "long", "bob", "pixie", 
"pigtails", "braids", "ponytail", "bun", 
"curly", "wavy", "straight", "afro", 
"dreadlocks", "bangs", "side_part", "center_part", "other"
```

### Eye Color
```
"brown", "blue", "green", "hazel", "gray", "amber", "other"
```

### Body Type
```
"average", "slim", "athletic", "curvy", "other"
```

### Theme
```
"adventure", "fantasy", "mystery", "friendship", 
"nature", "space", "ocean", "animals", "sports", "music"
```

### Art Style
```
"watercolor", "digital_art", "cartoon", 
"realistic", "sketch", "pastel"
```

### Book Format
```
"digital", "softcover", "hardcover"
```

### Shipping Tier
```
"digital", "standard", "express"
```

---

## 🔍 Other Useful Endpoints

### Get Book Details
```bash
GET /api/v1/books/{book_id}
```

### Get Book Preview Images
```bash
GET /api/v1/books/{book_id}/preview
```

### Calculate Book Price
```bash
GET /api/v1/orders/books/{book_id}/price?format=hardcover&shipping=standard&gift_wrap=true
```

### Get Order Status
```bash
GET /api/v1/orders/{order_id}/status
```

### Get Shipping Options
```bash
GET /api/v1/orders/shipping-options
```

### Regenerate Page
```bash
POST /api/v1/books/{book_id}/regenerate-page/{page_number}
{
  "scene_description": "New scene description",
  "character_action": "running",
  "mood": "excited"
}
```

---

## ⚠️ Important Notes

1. **API Keys**: In development mode, API keys are optional. Set `API_KEY_REQUIRED=false` in your `.env` file.

2. **Rate Limiting**: Rate limiting is disabled by default in development. Set `RATE_LIMIT_ENABLED=true` to enable.

3. **Required API Keys**: For full functionality, you need:
   - `FAL_KEY` - For image generation
   - `GEMINI_API_KEY` - For story generation

4. **Book Creation**: Creating a book will:
   - Generate a 10-page story using Gemini AI
   - Generate preview images using Fal.ai
   - This may take 30-60 seconds depending on API response times

5. **Order Creation**: Currently creates an order record. Print job creation happens via Shopify webhooks.

---

## 🐛 Troubleshooting

### "Connection refused"
- Make sure the server is running: `uvicorn main:app --reload --port 8000`

### "401 Unauthorized"
- Check if API key is required: Set `API_KEY_REQUIRED=false` for development
- Or provide a valid API key in the `X-API-Key` header

### "400 Bad Request"
- Check that all required fields are present
- Validate enum values match the allowed options
- Check field constraints (e.g., child_age must be 2-12)

### "404 Not Found"
- Verify the book_id exists (create a book first)
- Check the endpoint path is correct

### Book creation takes too long
- This is normal! Story generation (Gemini) + image generation (Fal.ai) takes time
- Preview images are generated sequentially for consistency
- Expect 30-60 seconds for a complete book

---

## 📚 Additional Resources

- **Interactive API Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **API Versioning Guide**: `documentation/API_VERSIONING_GUIDE.md`
- **Quick Start**: `QUICK_START.md`

---

## 🎯 Example Workflow

1. **Create a book**:
   ```bash
   python test_create_book_and_order.py
   # Note the book_id from the response
   ```

2. **View the book**:
   ```bash
   curl http://localhost:8000/api/v1/books/{book_id} | python -m json.tool
   ```

3. **Get preview images**:
   ```bash
   curl http://localhost:8000/api/v1/books/{book_id}/preview | python -m json.tool
   ```

4. **Calculate price**:
   ```bash
   curl "http://localhost:8000/api/v1/orders/books/{book_id}/price?format=hardcover&shipping=standard" | python -m json.tool
   ```

5. **Create an order**:
   ```bash
   # Use the book_id from step 1
   curl -X POST http://localhost:8000/api/v1/orders/create \
     -H "Content-Type: application/json" \
     -d '{"book_id": "{book_id}", "format": "hardcover", "shipping_tier": "standard"}'
   ```

---

**Happy Testing!** 🎉

