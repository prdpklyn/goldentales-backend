# GoldenTales API Versioning Guide

**Version**: 3.0.0  
**Last Updated**: December 2024  
**Status**: Active

---

## Overview

GoldenTales API uses URL path versioning to ensure backward compatibility and smooth migrations. This guide explains our versioning strategy, deprecation policy, and migration procedures.

---

## Versioning Strategy

### URL Path Versioning

All API endpoints are versioned using the URL path:

```
Current:  /api/v1/books/create
Future:   /api/v2/books/create
```

### Version-Agnostic Endpoints

Some endpoints remain unversioned and are accessible across all versions:

- `/` - Root health check
- `/api/health` - Detailed health check
- `/docs` - OpenAPI documentation
- `/redoc` - ReDoc documentation

---

## Current API Versions

| Version | Status | Release Date | Deprecation Date | Sunset Date |
|---------|--------|--------------|------------------|-------------|
| **v1** | ✅ Current | Dec 2024 | - | - |
| Legacy (`/api/*`) | ⚠️ Deprecated | - | Mar 1, 2025 | Jun 1, 2025 |

---

## Deprecation Policy

### Timeline

When a version is deprecated, we follow a **3-month sunset period**:

1. **Deprecation Announcement** (T+0)
   - Version marked as deprecated
   - Deprecation headers added to responses
   - Email notification sent to API consumers
   - Documentation updated

2. **Warning Period** (T+0 to T+3 months)
   - API continues to function normally
   - All responses include deprecation headers
   - Migration guide published
   - Support for migration questions

3. **Sunset** (T+3 months)
   - API version removed
   - Requests return `410 Gone` with migration info
   - Successor version clearly indicated

### Response Headers

Deprecated endpoints include these headers:

```http
Deprecation: 2025-03-01
Sunset: 2025-06-01
Link: </api/v1>; rel="successor-version"
X-API-Warning: This endpoint is deprecated and will be removed on 2025-06-01. Please migrate to /api/v1/* endpoints.
```

---

## Migration Guide: Legacy → v1

### Overview

Legacy endpoints (`/api/*`) are being deprecated in favor of versioned endpoints (`/api/v1/*`).

**Timeline**:
- **Deprecation Date**: March 1, 2025
- **Sunset Date**: June 1, 2025

### What's Changing?

The only change is the URL path prefix. All functionality remains identical.

### Endpoint Mapping

| Legacy Endpoint | New v1 Endpoint | Status |
|----------------|-----------------|--------|
| `/api/books/create` | `/api/v1/books/create` | ✅ Available |
| `/api/books/{book_id}` | `/api/v1/books/{book_id}` | ✅ Available |
| `/api/books/{book_id}/preview` | `/api/v1/books/{book_id}/preview` | ✅ Available |
| `/api/books/{book_id}/regenerate-page/{num}` | `/api/v1/books/{book_id}/regenerate-page/{num}` | ✅ Available |
| `/api/books/{book_id}/price` | `/api/v1/books/{book_id}/price` | ✅ Available |
| `/api/orders/create` | `/api/v1/orders/create` | ✅ Available |
| `/api/orders/{order_id}/status` | `/api/v1/orders/{order_id}/status` | ✅ Available |
| `/api/shipping-options` | `/api/v1/shipping-options` | ✅ Available |
| `/api/shopify/webhooks/*` | `/api/v1/shopify/webhooks/*` | ✅ Available |
| `/api/config` | `/api/v1/config` | ✅ Available |

### Migration Steps

#### 1. Update Base URL

**Before** (Legacy):
```javascript
const BASE_URL = 'https://api.goldentales.app/api';
```

**After** (v1):
```javascript
const BASE_URL = 'https://api.goldentales.app/api/v1';
```

#### 2. Update All API Calls

**JavaScript/TypeScript Example**:

```javascript
// Before (Legacy)
fetch('https://api.goldentales.app/api/books/create', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': 'your-api-key'
  },
  body: JSON.stringify(bookData)
})

// After (v1)
fetch('https://api.goldentales.app/api/v1/books/create', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': 'your-api-key'
  },
  body: JSON.stringify(bookData)
})
```

**Python Example**:

```python
# Before (Legacy)
response = requests.post(
    'https://api.goldentales.app/api/books/create',
    headers={'X-API-Key': 'your-api-key'},
    json=book_data
)

# After (v1)
response = requests.post(
    'https://api.goldentales.app/api/v1/books/create',
    headers={'X-API-Key': 'your-api-key'},
    json=book_data
)
```

**cURL Example**:

```bash
# Before (Legacy)
curl -X POST https://api.goldentales.app/api/books/create \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"child_name": "Emma", ...}'

# After (v1)
curl -X POST https://api.goldentales.app/api/v1/books/create \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"child_name": "Emma", ...}'
```

#### 3. Test Your Integration

After updating:
1. Test all API calls in your staging/development environment
2. Verify responses match expected format
3. Check for any breaking changes (there should be none)
4. Monitor for errors in production

#### 4. Deploy

Once tested, deploy your changes before the sunset date (June 1, 2025).

---

## Request/Response Format

### No Changes

The request and response formats remain **identical** between legacy and v1 endpoints. Only the URL path changes.

**Example**: Create Book Request

```json
{
  "child_name": "Emma",
  "child_age": 6,
  "theme": "adventure",
  "art_style": "watercolor",
  "gender": "girl",
  "skin_tone": "light",
  "hair_color": "brown",
  "hair_style": "pigtails",
  "eye_color": "blue"
}
```

Response format is identical regardless of version.

---

## Detecting Deprecation

### Check Response Headers

Monitor response headers to detect when you're using deprecated endpoints:

```javascript
fetch(url)
  .then(response => {
    // Check for deprecation
    if (response.headers.has('Deprecation')) {
      console.warn('API endpoint is deprecated!');
      console.warn('Deprecation Date:', response.headers.get('Deprecation'));
      console.warn('Sunset Date:', response.headers.get('Sunset'));
      console.warn('Successor:', response.headers.get('Link'));
    }
    return response.json();
  })
```

### API Response

Deprecated endpoints also include version information in the response headers:

```http
X-API-Version: legacy
X-API-Status: deprecated
Deprecation: 2025-03-01
Sunset: 2025-06-01
```

---

## Version Detection Middleware

The API automatically detects the version from the URL path:

- `/api/v1/*` → Version 1
- `/api/v2/*` → Version 2 (future)
- `/api/*` (no version) → Legacy (deprecated)

No special headers or query parameters are required.

---

## Best Practices

### 1. Always Use Versioned Endpoints

New integrations should always use versioned endpoints (`/api/v1/*`).

### 2. Monitor Deprecation Headers

Implement monitoring to alert when deprecation headers are detected.

### 3. Version in Configuration

Store the API version in your configuration:

```javascript
// config.js
export const API_CONFIG = {
  baseUrl: 'https://api.goldentales.app',
  version: 'v1',  // Easy to update when migrating
  endpoints: {
    createBook: '/books/create',
    getBook: '/books/{id}',
    // ...
  }
}

// Usage
const url = `${API_CONFIG.baseUrl}/api/${API_CONFIG.version}${API_CONFIG.endpoints.createBook}`;
```

### 4. Subscribe to Updates

Subscribe to API updates at: https://goldentales.app/developers/updates

---

## Frequently Asked Questions

### Q: What if I don't migrate before the sunset date?

A: After June 1, 2025, legacy endpoints will return `410 Gone` errors. Your integration will break. Migrate as soon as possible.

### Q: Will there be any downtime during migration?

A: No. Both legacy and v1 endpoints will work during the transition period (until June 1, 2025).

### Q: Are there any breaking changes in v1?

A: No. v1 is functionally identical to the legacy API. Only the URL path changes.

### Q: How will I be notified about future deprecations?

A: We'll send email notifications to all registered API consumers 3 months before any deprecation.

### Q: Can I use both legacy and v1 endpoints simultaneously?

A: Yes, during the transition period. However, we recommend migrating all calls at once to avoid confusion.

### Q: Will my API keys work with v1 endpoints?

A: Yes. API keys are version-agnostic and work across all versions.

---

## Support

Need help with migration?

- **Documentation**: https://goldentales.app/docs
- **Email**: api-support@goldentales.app
- **Discord**: https://discord.gg/goldentales

---

## Future Versions

We're committed to maintaining backward compatibility and providing ample migration time:

- **v2** (planned for Q2 2025): Enhanced character consistency, new art styles
- **v3** (planned for Q4 2025): Multi-language support, advanced customization

All future versions will follow the same 3-month deprecation policy.

---

## Changelog

### v1.0.0 (December 2024)
- Initial versioned release
- Identical to legacy API (no breaking changes)
- Added versioning middleware
- Legacy endpoints marked as deprecated

---

**Last Updated**: December 2024  
**Document Version**: 1.0.0

