# Quick Start Guide - Testing GoldenTales API

## 🚀 Starting the Application

### Option 1: Using uvicorn directly
```bash
# Activate virtual environment (if using one)
source venv/bin/activate

# Start the server
uvicorn main:app --reload --port 8000
```

### Option 2: Using Python directly
```bash
python main.py
```

The server will start at: **http://localhost:8000**

---

## 🧪 Testing API Endpoints

### Method 1: FastAPI Interactive Docs (Easiest!)

Once the server is running, open your browser:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

These provide interactive documentation where you can:
- See all available endpoints
- Test endpoints directly in the browser
- View request/response schemas
- See deprecation headers

### Method 2: Using the Test Scripts

#### Python Script (Recommended)
```bash
# Make sure server is running first
python test_api_endpoints.py

# With custom API key
export API_KEY=your-api-key
python test_api_endpoints.py

# Against different server
export BASE_URL=https://api.goldentales.app
python test_api_endpoints.py
```

#### Bash Script
```bash
./test_api_endpoints.sh

# With API key
export API_KEY=your-api-key
./test_api_endpoints.sh
```

### Method 3: Using curl

```bash
# Root endpoint
curl http://localhost:8000/

# Health check (version-agnostic)
curl http://localhost:8000/api/health

# Health check (v1)
curl http://localhost:8000/api/v1/health

# Config endpoint (legacy - shows deprecation)
curl -v http://localhost:8000/api/config

# Config endpoint (v1 - current)
curl http://localhost:8000/api/v1/config

# With API key (if required)
curl -H "X-API-Key: your-api-key" http://localhost:8000/api/v1/config
```

### Method 4: Using httpie (if installed)

```bash
# Install: pip install httpie

# Basic request
http GET http://localhost:8000/api/v1/config

# With API key
http GET http://localhost:8000/api/v1/config X-API-Key:your-api-key

# View headers (to see deprecation headers)
http -v GET http://localhost:8000/api/config
```

---

## 📋 Key Endpoints to Test

### Version-Agnostic (No versioning)
- `GET /` - Root health check
- `GET /api/health` - Detailed health check

### V1 Endpoints (Current)
- `GET /api/v1/health` - V1 health check
- `GET /api/v1/config` - Public configuration

### Legacy Endpoints (Deprecated)
- `GET /api/config` - Legacy config (shows deprecation headers)

---

## 🔍 What to Look For

### Testing Versioning

1. **V1 Endpoints** should return:
   ```json
   {
     "api": {
       "version": "v1",
       "status": "current"
     }
   }
   ```

2. **Legacy Endpoints** should:
   - Return deprecation info in response body
   - Include deprecation headers:
     - `Deprecation: 2025-03-01`
     - `Sunset: 2025-06-01`
     - `X-API-Warning: ...`
     - `X-API-Version: legacy`
     - `X-API-Status: deprecated`

### Testing Health Checks

Health check should return:
```json
{
  "status": "healthy" or "degraded",
  "version": "3.0.0",
  "environment": "development",
  "checks": {
    "fal_key_configured": true/false,
    "gemini_key_configured": true/false,
    "shopify_configured": true/false
  }
}
```

---

## ⚙️ Environment Variables

The app works without API keys in development mode, but for full functionality you may want:

```bash
# Required for full functionality
export FAL_KEY=your-fal-key
export GEMINI_API_KEY=your-gemini-key

# Optional
export SUPABASE_URL=your-supabase-url
export SUPABASE_PUBLISHABLE_KEY=your-key
export SHOPIFY_WEBHOOK_SECRET=your-secret

# For API authentication (dev mode)
export DEV_API_KEY=dev-key-123
export API_KEY_REQUIRED=false  # Set to true in production
export RATE_LIMIT_ENABLED=false  # Set to true in production
```

Create a `.env` file in the project root with these variables.

---

## 🐛 Troubleshooting

### Server won't start
- Check if port 8000 is already in use
- Try a different port: `uvicorn main:app --port 8001`
- Check Python version: `python --version` (should be 3.8+)

### Connection refused
- Make sure the server is running
- Check the URL (should be http://localhost:8000)

### Missing dependencies
```bash
pip install -r requirements.txt
```

### API key errors
- In development, API keys are optional
- Set `API_KEY_REQUIRED=false` in `.env` or environment

---

## 📚 Additional Resources

- **API Documentation**: http://localhost:8000/docs
- **Migration Guide**: `documentation/API_VERSIONING_GUIDE.md`
- **Implementation Plan**: `IMPLEMENTATION_PLAN.md`

