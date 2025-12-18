# Testing APIs with Supabase Authentication

This guide explains how to test the V2 APIs that require JWT Bearer token authentication.

## Overview

V2 APIs (`/api/v2/books/*` and `/api/v2/photo/*`) require JWT authentication to:
1. Identify the user making the request
2. Satisfy Row Level Security (RLS) policies in Supabase
3. Ensure users can only access their own data

## Prerequisites

1. **Supabase Project**: You need access to a Supabase project
2. **Supabase Client**: Install `@supabase/supabase-js` (JavaScript) or `supabase` (Python)
3. **User Account**: A test user account in Supabase Auth

## Method 1: Using Supabase JavaScript Client (Recommended for Frontend)

### Step 1: Install Supabase Client

```bash
npm install @supabase/supabase-js
```

### Step 2: Initialize Supabase Client

```javascript
import { createClient } from '@supabase/supabase-js'

const supabaseUrl = 'https://your-project.supabase.co'
const supabaseAnonKey = 'your-anon-key'

const supabase = createClient(supabaseUrl, supabaseAnonKey)
```

### Step 3: Login and Get JWT Token

```javascript
// Login with email/password
const { data, error } = await supabase.auth.signInWithPassword({
  email: 'test@example.com',
  password: 'your-password'
})

if (error) {
  console.error('Login error:', error)
} else {
  // Get the JWT token
  const token = data.session.access_token
  console.log('JWT Token:', token)
  
  // Use this token in API requests
}
```

### Step 4: Make API Request with JWT Token

```javascript
const response = await fetch('http://localhost:8000/api/v2/books/create', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`  // Include JWT token
  },
  body: JSON.stringify({
    child_name: "Emma",
    child_age: 5,
    theme: "space",
    art_style: "watercolor",
    tier: "basic",
    // ... other fields
  })
})

const book = await response.json()
console.log('Created book:', book)
```

## Method 2: Using FastAPI Interactive Docs (Swagger UI)

### Step 1: Get JWT Token from Supabase

First, get a JWT token using one of these methods:

**Option A: Using Supabase Dashboard**
1. Go to your Supabase project dashboard
2. Navigate to Authentication → Users
3. Create a test user or use an existing one
4. Copy the user's JWT token (if available in dashboard)

**Option B: Using Supabase Client (JavaScript)**

```javascript
const { data } = await supabase.auth.signInWithPassword({
  email: 'test@example.com',
  password: 'password'
})
const token = data.session.access_token
console.log(token)  // Copy this token
```

**Option C: Using cURL**

```bash
curl -X POST 'https://your-project.supabase.co/auth/v1/token?grant_type=password' \
  -H "apikey: your-anon-key" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "your-password"
  }'
```

### Step 2: Use Token in Swagger UI

1. Open `http://localhost:8000/docs` in your browser
2. Click the **"Authorize"** button (top right, lock icon)
3. In the "BearerAuth" section, enter your JWT token
4. Click **"Authorize"**
5. Now all V2 API endpoints will include the token automatically

### Step 3: Test an Endpoint

1. Navigate to any V2 endpoint (e.g., `POST /api/v2/books/create`)
2. Click **"Try it out"**
3. Fill in the request body
4. Click **"Execute"**
5. The request will include your JWT token automatically

## Method 3: Using cURL

```bash
# First, get JWT token (see Method 2, Option C)
TOKEN="your-jwt-token-here"

# Make API request with JWT token
curl -X POST 'http://localhost:8000/api/v2/books/create' \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "child_name": "Emma",
    "child_age": 5,
    "theme": "space",
    "art_style": "watercolor",
    "tier": "basic"
  }'
```

## Method 4: Using Python Requests

```python
import requests
from supabase import create_client, Client

# Initialize Supabase client
supabase_url = "https://your-project.supabase.co"
supabase_key = "your-anon-key"
supabase: Client = create_client(supabase_url, supabase_key)

# Login and get token
response = supabase.auth.sign_in_with_password({
    "email": "test@example.com",
    "password": "your-password"
})

token = response.session.access_token

# Make API request
api_url = "http://localhost:8000/api/v2/books/create"
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}
data = {
    "child_name": "Emma",
    "child_age": 5,
    "theme": "space",
    "art_style": "watercolor",
    "tier": "basic"
}

response = requests.post(api_url, headers=headers, json=data)
print(response.json())
```

## JWT Token Structure

A Supabase JWT token contains:
- `sub`: User ID (UUID)
- `email`: User's email address
- `exp`: Expiration timestamp
- Other claims

Example decoded token:
```json
{
  "sub": "123e4567-e89b-12d3-a456-426614174000",
  "email": "test@example.com",
  "exp": 1234567890,
  ...
}
```

## Troubleshooting

### Error: "Authentication required"
- **Cause**: Missing or invalid JWT token
- **Solution**: Ensure `Authorization: Bearer <token>` header is included

### Error: "Invalid or expired token"
- **Cause**: Token has expired or is malformed
- **Solution**: Get a new token by logging in again

### Error: "Token missing user identifier"
- **Cause**: JWT token doesn't contain `sub` or `user_id` claim
- **Solution**: Ensure you're using a valid Supabase Auth token

### Error: "RLS policy violation"
- **Cause**: User doesn't have permission to access the resource
- **Solution**: Ensure the user_id in the token matches the resource owner

## Security Notes

⚠️ **Important**:
- Never commit JWT tokens to version control
- Tokens expire after a set time (default: 1 hour for Supabase)
- Use environment variables for Supabase credentials
- In production, always use HTTPS

## Next Steps

1. Set up Supabase Auth in your frontend application
2. Implement token refresh logic
3. Handle token expiration gracefully
4. Add error handling for authentication failures

