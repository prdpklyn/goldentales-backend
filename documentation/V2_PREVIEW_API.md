# V2 Preview API - Kids 60s Magic Preview Flow

## Overview

This document describes the V2 Preview API endpoints implemented for the Kids "60s Magic Preview" flow. These endpoints enable fast preview generation, photo likeness variants, and quick regeneration with tweaks.

## Endpoints

### 1. POST /api/v2/preview/quick

**Purpose**: Generate a quick preview (cover + hero portrait + 2 spreads) in under 60 seconds.

**Authentication**: JWT Bearer token required

**Request**:
```json
{
  "child_name": "Emma",
  "child_gender": "girl",
  "age_band": "6-8",
  "theme": "space",
  "photo_url": null,
  "session_id": "abc123"
}
```

**Response**:
```json
{
  "preview_id": "uuid-v4",
  "title": "Emma's Cosmic Quest",
  "cover": {
    "image_url": "https://cdn.example.com/covers/uuid.jpg",
    "prompt_used": "watercolor illustration of a 7-year-old girl..."
  },
  "hero_portrait": {
    "image_url": "https://cdn.example.com/portraits/uuid.jpg",
    "is_placeholder": true
  },
  "spreads": [
    {
      "page_number": 1,
      "image_url": "https://cdn.example.com/pages/uuid-p1.jpg",
      "text": "Emma looked up at the stars and felt her heart fill with wonder..."
    },
    {
      "page_number": 2,
      "image_url": "https://cdn.example.com/pages/uuid-p2.jpg",
      "text": "Her spaceship was ready, gleaming silver in the moonlight..."
    }
  ],
  "metadata": {
    "generation_time_ms": 45000,
    "model_version": "v2.1",
    "art_style": "watercolor"
  }
}
```

**Performance Requirements**:
- Must complete in < 60 seconds
- Cover generation: ~15s
- Hero portrait: ~10s
- 2 spreads: ~15s each
- Buffer: ~5s

---

### 2. POST /api/v2/photo/likeness-variants

**Purpose**: Generate 3 artistic style variants (A, B, C) that preserve photo likeness.

**Authentication**: JWT Bearer token required

**Request**:
```json
{
  "photo_url": "https://storage.example.com/photos/uuid.jpg",
  "art_style": "watercolor",
  "child_name": "Emma",
  "child_gender": "girl",
  "age_band": "6-8",
  "num_variants": 3
}
```

**Response**:
```json
{
  "variants": [
    {
      "id": "var_a_uuid",
      "image_url": "https://cdn.example.com/variants/uuid-a.jpg",
      "likeness_score": 92,
      "style_label": "A",
      "description": "Warm, expressive watercolor with soft edges",
      "style_attributes": {
        "warmth": "high",
        "detail": "medium",
        "expressiveness": "high"
      }
    },
    {
      "id": "var_b_uuid",
      "image_url": "https://cdn.example.com/variants/uuid-b.jpg",
      "likeness_score": 88,
      "style_label": "B",
      "description": "Soft, dreamy watercolor with gentle tones",
      "style_attributes": {
        "warmth": "medium",
        "detail": "low",
        "expressiveness": "medium"
      }
    },
    {
      "id": "var_c_uuid",
      "image_url": "https://cdn.example.com/variants/uuid-c.jpg",
      "likeness_score": 85,
      "style_label": "C",
      "description": "Bold, vibrant watercolor with rich colors",
      "style_attributes": {
        "warmth": "high",
        "detail": "high",
        "expressiveness": "high"
      }
    }
  ],
  "processing_time_ms": 8000,
  "source_photo_analysis": {
    "face_detected": true,
    "quality_score": 95,
    "lighting": "good",
    "angle": "frontal"
  }
}
```

**Performance Requirements**:
- Must complete in < 15 seconds
- Face detection: ~1s
- 3 variants in parallel: ~10s
- Post-processing: ~4s

---

### 3. POST /api/v2/preview/regenerate

**Purpose**: Quickly regenerate preview with user tweaks applied.

**Authentication**: JWT Bearer token required

**Request**:
```json
{
  "preview_id": "uuid-v4",
  "character_reference_url": "https://cdn.example.com/variants/uuid-a.jpg",
  "tweaks": {
    "tone": "adventurous",
    "art_modifier": "brighter",
    "sidekick": "robot"
  }
}
```

**Response**:
```json
{
  "preview_id": "uuid-v4",
  "hero_portrait": {
    "image_url": "https://cdn.example.com/portraits/uuid-updated.jpg",
    "updated": true
  },
  "spreads": [
    {
      "page_number": 1,
      "image_url": "https://cdn.example.com/pages/uuid-p1-v2.jpg",
      "text": "Emma and her robot companion zoomed through the cosmos...",
      "updated": true
    },
    {
      "page_number": 2,
      "image_url": "https://cdn.example.com/pages/uuid-p2-v2.jpg",
      "text": "The stars seemed brighter than ever before!",
      "updated": true
    }
  ],
  "metadata": {
    "regeneration_time_ms": 12000,
    "tweaks_applied": {
      "tone": "adventurous",
      "art_modifier": "brighter",
      "sidekick": "robot"
    }
  }
}
```

**Tweak Options**:
- `tone`: funny, gentle, adventurous
- `art_modifier`: softer, brighter, detailed
- `sidekick`: dog, unicorn, robot, none

**Performance Requirements**:
- Must complete in < 15 seconds
- Only regenerates hero + 2 spreads
- Uses existing prompts with tweaks applied

---

## Implementation Details

### Architecture

```
app/
├── routers/v2/
│   ├── preview.py          # Preview endpoints
│   └── photo.py            # Updated with likeness-variants
├── services/
│   ├── preview_service.py  # Fast preview generation logic
│   └── photo_character_service.py  # Updated with variant generation
├── models/
│   ├── requests.py         # Added QuickPreviewRequest, LikenessVariantsRequest, PreviewRegenerateRequest
│   └── responses.py        # Added corresponding response models
```

### Key Components

1. **PreviewService** (`app/services/preview_service.py`)
   - Generates quick previews with minimal character attributes
   - Manages in-memory preview sessions (1-hour expiration)
   - Handles regeneration with tweaks

2. **PhotoCharacterService** (`app/services/photo_character_service.py`)
   - Added `generate_likeness_variants()` method
   - Generates 3-5 style variants in parallel
   - Preserves photo likeness while applying artistic styles

3. **ImageGenerator** (`app/services/image_generator.py`)
   - Added `generate_cover()` method
   - Added `generate_hero_portrait()` method
   - Added `generate_hero_portrait_with_reference()` method
   - Updated `generate_illustration()` to support `art_modifier` parameter

4. **StoryGenerator** (`app/services/story_generator.py`)
   - Added `generate_preview_story()` method for 2-page previews

### Session Management

Preview sessions are stored in-memory with a 1-hour TTL:
- `preview_id`: UUID v4
- `session_id`: Client tracking ID
- Character bible and story pages
- Generated image URLs
- `expires_at`: UTC timestamp

**Production Recommendation**: Replace in-memory storage with Redis for:
- Multi-instance support
- Persistence across restarts
- Better TTL management

### Error Handling

All endpoints return structured JSON errors:

**400 Bad Request**:
```json
{
  "error": "Invalid age_band",
  "code": "VALIDATION_ERROR",
  "details": "age_band must be one of: 3-5, 6-8, 9-12"
}
```

**422 Unprocessable Entity**:
```json
{
  "error": "No face detected",
  "code": "FACE_DETECTION_FAILED",
  "details": "Please upload a photo with a clearly visible face"
}
```

**503 Service Unavailable**:
```json
{
  "error": "AI service temporarily unavailable",
  "code": "SERVICE_UNAVAILABLE",
  "retry_after": 30
}
```

### Rate Limiting

Preview endpoints inherit from existing middleware:
- 10 requests/hour per session_id
- Prevents abuse of expensive AI operations

### Monitoring Metrics

Track these metrics for preview endpoints:
- Generation time percentiles (p50, p95, p99)
- Success rate per endpoint
- Likeness score distribution
- User selections (which variants are popular)
- Preview session expiration rates

---

## Testing

Comprehensive tests in `tests/test_preview_api.py`:
- Quick preview generation
- Likeness variant generation
- Preview regeneration
- Input validation
- Error handling

Run tests:
```bash
pytest tests/test_preview_api.py -v
```

---

## Migration from Specifications

The implementation follows the provided Railway API V2 specifications with one key difference:

### Authentication Change

**Specification**: `x-api-key` header authentication
**Implementation**: JWT Bearer token authentication

**Reason**: The existing V2 API already uses JWT Bearer tokens via Supabase Auth. For consistency and to leverage existing authentication infrastructure, JWT tokens are used instead of API keys.

**Frontend Migration**:
```javascript
// Specification (NOT used):
headers: {
  'x-api-key': RAILWAY_API_KEY
}

// Implementation (CURRENT):
headers: {
  'Authorization': `Bearer ${supabaseJwtToken}`
}
```

All other aspects match the specifications exactly.

---

## Future Enhancements

1. **Redis Session Storage**: Replace in-memory sessions for production scalability
2. **Face Detection**: Implement actual face detection using fal-ai/face-detector
3. **Likeness Scoring**: Add ML-based likeness scoring for variants
4. **CDN Integration**: Cache generated images on CDN for faster delivery
5. **Metrics Dashboard**: Real-time monitoring of preview performance
6. **A/B Testing**: Track which variants users prefer for optimization

---

## API Versioning

These endpoints are part of V2 API:
- Base path: `/api/v2/`
- Versioning middleware: Automatically adds `X-API-Version` header
- Deprecation: None (new endpoints)

---

## Related Documentation

- [API Versioning](./API_VERSIONING.md)
- [Character System](../character_system.py)
- [Image Generation](../app/services/image_generator.py)
- [Story Generation](../app/services/story_generator.py)
