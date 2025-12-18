# API Key Configuration Guide

This document explains what API key variables need to be set for different types of API authentication.

## Authentication Methods

The GoldenTales API uses **two different authentication methods** depending on the API version:

### 1. V2 APIs (User-Facing) - JWT Bearer Token
**Endpoints**: `/api/v2/books/*`, `/api/v2/photo/*`

- **Authentication**: JWT Bearer token from Supabase Auth
- **Header**: `Authorization: Bearer <jwt_token>`
- **No environment variable needed** - tokens are obtained by logging in via Supabase
- See `TESTING_WITH_SUPABASE_AUTH.md` for details

### 2. V1/Legacy APIs (Service-to-Service) - API Key
**Endpoints**: `/api/v1/*`, `/api/*` (legacy)

- **Authentication**: API Key
- **Header**: `X-API-Key: <api_key>`
- **Environment Variable**: `DEV_API_KEY` (for development)

---

## Environment Variables

### Required for Core Functionality

```bash
# AI Services (Required)
FAL_KEY=your-fal-ai-api-key              # For image generation
GEMINI_API_KEY=your-gemini-api-key      # For story generation

# Supabase (Required)
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_PUBLISHABLE_KEY=your-publishable-key
SUPABASE_PDF_API_KEY=your-pdf-api-key   # For Edge Functions (x-api-key header)
```

### Optional for Development

```bash
# Development API Key (for testing V1/Legacy APIs)
DEV_API_KEY=your-dev-api-key            # Used when API_KEY_REQUIRED=false

# Supabase Service Role (for admin operations)
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key  # Bypasses RLS, use carefully!
```

### Optional for Production Features

```bash
# Payment Processing
STRIPE_SECRET_KEY=your-stripe-secret-key

# Email Notifications
SENDGRID_API_KEY=your-sendgrid-api-key

# Print Services
LULU_API_KEY=your-lulu-api-key
PRINTFUL_API_KEY=your-printful-api-key

# Shopify Integration
SHOPIFY_STORE_URL=your-store.myshopify.com
SHOPIFY_ACCESS_TOKEN=your-shopify-token
SHOPIFY_WEBHOOK_SECRET=your-webhook-secret
```

---

## API Key Usage by Endpoint Type

### V2 APIs (JWT Required)

**No API key needed!** These endpoints use JWT tokens:

```bash
# Get JWT token from Supabase
curl -X POST 'https://your-project.supabase.co/auth/v1/token?grant_type=password' \
  -H "apikey: your-anon-key" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password"}'

# Use token in requests
curl -X POST 'http://localhost:8000/api/v2/books/create' \
  -H "Authorization: Bearer <jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{...}'
```

### V1/Legacy APIs (API Key Required)

**Use `X-API-Key` header** with `DEV_API_KEY` value:

```bash
# Set in .env file
DEV_API_KEY=my-dev-key-12345

# Use in requests
curl -X GET 'http://localhost:8000/api/v1/books/123' \
  -H "X-API-Key: my-dev-key-12345"
```

---

## Configuration in `.env` File

Create a `.env` file in the project root:

```bash
# ============================================
# REQUIRED - Core Services
# ============================================
FAL_KEY=your-fal-ai-api-key
GEMINI_API_KEY=your-gemini-api-key

# Supabase Configuration
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_PUBLISHABLE_KEY=your-publishable-key
SUPABASE_PDF_API_KEY=your-pdf-api-key

# ============================================
# OPTIONAL - Development
# ============================================
DEV_API_KEY=dev-key-for-testing
API_KEY_REQUIRED=false  # Set to true to enforce API keys in dev mode

# ============================================
# OPTIONAL - Production Features
# ============================================
STRIPE_SECRET_KEY=sk_test_...
SENDGRID_API_KEY=SG....
```

---

## Quick Reference

| API Version | Auth Method | Header | Environment Variable |
|------------|-------------|--------|---------------------|
| V2 (`/api/v2/*`) | JWT Bearer | `Authorization: Bearer <token>` | None (get from Supabase) |
| V1 (`/api/v1/*`) | API Key | `X-API-Key: <key>` | `DEV_API_KEY` |
| Legacy (`/api/*`) | API Key | `X-API-Key: <key>` | `DEV_API_KEY` |
| Edge Functions | API Key | `x-api-key: <key>` | `SUPABASE_PDF_API_KEY` |

---

## Testing in Swagger UI

### For V2 APIs (JWT):
1. Get JWT token from Supabase (see `TESTING_WITH_SUPABASE_AUTH.md`)
2. Open `http://localhost:8000/docs`
3. Click **"Authorize"** button
4. Enter token in **"BearerAuth"** field
5. Click **"Authorize"**

### For V1/Legacy APIs (API Key):
1. Set `DEV_API_KEY` in `.env`
2. Open `http://localhost:8000/docs`
3. Click **"Authorize"** button (if API key auth is shown)
4. Enter `DEV_API_KEY` value
5. Click **"Authorize"**

---

## Notes

- **Development Mode**: API keys are optional unless `API_KEY_REQUIRED=true`
- **Production Mode**: API keys are required for all non-public endpoints
- **V2 APIs**: Always require JWT, regardless of environment
- **Edge Functions**: Use `SUPABASE_PDF_API_KEY` for the `x-api-key` header when calling Supabase Edge Functions

---

## Troubleshooting

### "API key is required" error
- **Solution**: Set `DEV_API_KEY` in `.env` or provide `X-API-Key` header

### "Authentication required" error (V2 APIs)
- **Solution**: Get JWT token from Supabase and include in `Authorization: Bearer <token>` header

### "Invalid API key" error
- **Solution**: Check that `DEV_API_KEY` matches the value in your request header

