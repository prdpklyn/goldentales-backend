# Quick Test Guide - Preview API

## 🚀 Start Server

```bash
uvicorn main:app --reload --port 8000
```

## 🔑 Setup API Key

Add to `.env`:
```bash
DEV_API_KEY=gt_dev_test_key_12345
```

## 📝 Test Commands

### 1. Quick Preview (60s)
```bash
curl -X POST "http://localhost:8000/api/v2/preview/quick" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: gt_dev_test_key_12345" \
  -d '{
    "child_name": "Emma",
    "child_gender": "girl",
    "age_band": "6-8",
    "theme": "space",
    "session_id": "test-123"
  }' | jq '.'
```

### 2. Regenerate (15s)
```bash
# Use preview_id from step 1
curl -X POST "http://localhost:8000/api/v2/preview/regenerate" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: gt_dev_test_key_12345" \
  -d '{
    "preview_id": "PREVIEW_ID_HERE",
    "tweaks": {
      "tone": "adventurous",
      "sidekick": "robot"
    }
  }' | jq '.'
```

### 3. Get Status
```bash
curl "http://localhost:8000/api/v2/preview/PREVIEW_ID_HERE" \
  -H "X-API-Key: gt_dev_test_key_12345" | jq '.'
```

## 🎨 Swagger UI (Easiest)

1. Open: http://localhost:8000/docs
2. Click "Authorize" 🔓
3. Enter API key: `gt_dev_test_key_12345`
4. Test endpoints!

## 🐛 Troubleshooting

**Missing API key?**
```bash
# Check .env has DEV_API_KEY
# Restart server
```

**FAL_KEY not configured?**
```bash
# Add to .env
FAL_KEY=your_fal_ai_key
```

**GEMINI_API_KEY not configured?**
```bash
# Add to .env
GEMINI_API_KEY=your_gemini_key
```

## ✅ Expected Results

- Quick preview: Returns preview_id, cover, hero_portrait, 2 spreads
- Regenerate: Returns updated hero_portrait and spreads
- Status: Returns session details

## 📚 Full Docs

See: `documentation/TESTING_PREVIEW_API.md`
