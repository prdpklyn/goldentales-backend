# Testing the Preview API Locally

## 🚀 Quick Start

The V2 Preview endpoints use **X-API-Key** authentication (not JWT), making them easy to test.

### 1. Start the Server

```bash
cd /Users/thepradeeps/Taleom
uvicorn main:app --reload --port 8000
```

### 2. Get a Development API Key

Add this to your `.env` file:

```bash
# Development API key (for local testing only)
DEV_API_KEY=gt_dev_test_key_12345
```

This key will be automatically accepted in development mode.

---

## 📝 Testing with cURL

### Quick Preview

```bash
curl -X POST "http://localhost:8000/api/v2/preview/quick" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: gt_dev_test_key_12345" \
  -d '{
    "child_name": "Emma",
    "child_gender": "girl",
    "age_band": "6-8",
    "theme": "space",
    "photo_url": null,
    "session_id": "test-session-123"
  }'
```

### Likeness Variants

```bash
curl -X POST "http://localhost:8000/api/v2/photo/likeness-variants" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: gt_dev_test_key_12345" \
  -d '{
    "photo_url": "https://example.com/photo.jpg",
    "art_style": "watercolor",
    "child_name": "Emma",
    "child_gender": "girl",
    "age_band": "6-8",
    "num_variants": 3
  }'
```

### Regenerate Preview

```bash
# First, get preview_id from the quick preview response
curl -X POST "http://localhost:8000/api/v2/preview/regenerate" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: gt_dev_test_key_12345" \
  -d '{
    "preview_id": "PREVIEW_ID_FROM_QUICK_PREVIEW",
    "tweaks": {
      "tone": "adventurous",
      "art_modifier": "brighter",
      "sidekick": "robot"
    }
  }'
```

---

## 🎨 Testing with Swagger UI (Easiest!)

1. **Open**: http://localhost:8000/docs

2. **Click the "Authorize" button** 🔓 at the top right

3. **Enter your API key** in the "ApiKeyAuth (apiKey)" field:
   ```
   gt_dev_test_key_12345
   ```

4. **Click "Authorize"**, then "Close"

5. **Now test any endpoint**:
   - Click on `/api/v2/preview/quick`
   - Click "Try it out"
   - Fill in the request body
   - Click "Execute"

All subsequent requests will automatically include your API key!

---

## 🧪 Testing with Postman

### Setup

1. Create a new Postman collection
2. Add a collection variable:
   - Variable: `api_key`
   - Value: `gt_dev_test_key_12345`

### Request Template

**Headers**:
```
Content-Type: application/json
X-API-Key: {{api_key}}
```

**URL**: `http://localhost:8000/api/v2/preview/quick`

**Body**:
```json
{
  "child_name": "Emma",
  "child_gender": "girl",
  "age_band": "6-8",
  "theme": "space",
  "photo_url": null,
  "session_id": "test-session-123"
}
```

---

## 🔑 API Key vs JWT Authentication

### Preview Endpoints (X-API-Key)
- ✅ `/api/v2/preview/quick`
- ✅ `/api/v2/preview/regenerate`
- ✅ `/api/v2/preview/{preview_id}`

**Why API Key?** These are public preview endpoints that don't need user-specific data.

### Other V2 Endpoints (JWT Bearer)
- 🔒 `/api/v2/books/create`
- 🔒 `/api/v2/photo/validate`
- 🔒 `/api/v2/photo/likeness-variants`

**Why JWT?** These endpoints create user-specific resources tied to their account.

---

## 🐛 Troubleshooting

### Error: "Missing API key"

**Solution**: Add the `X-API-Key` header:
```bash
-H "X-API-Key: gt_dev_test_key_12345"
```

### Error: "Invalid or inactive API key"

**Solution**:
1. Check your `.env` file has `DEV_API_KEY=gt_dev_test_key_12345`
2. Restart the server
3. Make sure you're using the exact key from `.env`

### Error: "FAL_KEY not configured"

**Solution**: Add to `.env`:
```bash
FAL_KEY=your_fal_ai_api_key_here
```

Get your key from: https://fal.ai/dashboard

### Error: "GEMINI_API_KEY not configured"

**Solution**: Add to `.env`:
```bash
GEMINI_API_KEY=your_gemini_api_key_here
```

Get your key from: https://aistudio.google.com/app/apikey

---

## 📊 Expected Response Times

Based on performance requirements:

### Quick Preview
- **Target**: < 60 seconds
- **Breakdown**:
  - Cover: ~15s
  - Hero portrait: ~10s
  - Page 1: ~15s
  - Page 2: ~15s
  - Total: ~55s

### Likeness Variants
- **Target**: < 15 seconds
- **Breakdown**:
  - Face detection: ~1s
  - 3 variants (parallel): ~10s
  - Post-processing: ~4s
  - Total: ~15s

### Preview Regenerate
- **Target**: < 15 seconds
- **Breakdown**:
  - Hero portrait: ~5s
  - Page 1: ~5s
  - Page 2: ~5s
  - Total: ~15s

---

## 🎯 Complete Test Flow

Here's a full end-to-end test:

```bash
# 1. Generate quick preview
PREVIEW_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v2/preview/quick" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: gt_dev_test_key_12345" \
  -d '{
    "child_name": "Emma",
    "child_gender": "girl",
    "age_band": "6-8",
    "theme": "space",
    "photo_url": null,
    "session_id": "test-123"
  }')

echo "Preview Response:"
echo $PREVIEW_RESPONSE | jq '.'

# 2. Extract preview_id
PREVIEW_ID=$(echo $PREVIEW_RESPONSE | jq -r '.preview_id')
echo "Preview ID: $PREVIEW_ID"

# 3. Get preview status
curl -s "http://localhost:8000/api/v2/preview/$PREVIEW_ID" \
  -H "X-API-Key: gt_dev_test_key_12345" | jq '.'

# 4. Regenerate with tweaks
curl -s -X POST "http://localhost:8000/api/v2/preview/regenerate" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: gt_dev_test_key_12345" \
  -d "{
    \"preview_id\": \"$PREVIEW_ID\",
    \"tweaks\": {
      \"tone\": \"adventurous\",
      \"sidekick\": \"robot\"
    }
  }" | jq '.'
```

---

## 🔒 Production API Keys

For production, you'll need to create API keys in the database:

```sql
-- Create an API key
INSERT INTO api_keys (
  name,
  key_hash,
  rate_limit_tier,
  is_active
) VALUES (
  'Production Client',
  -- Hash of 'gt_prod_abc123...'
  '1234567890abcdef...',
  'standard',
  true
);
```

Then clients use:
```bash
-H "X-API-Key: gt_prod_abc123..."
```

---

## 📚 Next Steps

1. **Test all three endpoints** using Swagger UI
2. **Verify response times** are within targets
3. **Check the logs** for any errors
4. **Test error cases** (invalid inputs, missing fields)
5. **Integrate with your frontend** using the same `X-API-Key` header

Need help? Check the main documentation at `documentation/V2_PREVIEW_API.md`
