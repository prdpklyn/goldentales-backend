# Lovable.dev Prompt: Supabase Edge Functions for GoldenTales

> Copy and paste this prompt into Lovable.dev to generate all required Supabase Edge Functions

---

## 🚀 THE PROMPT

```
Create Supabase Edge Functions for a personalized children's storybook platform called "GoldenTales". The backend needs 11 Edge Functions that handle CRUD operations for stories, pages, and orders.

## Project Context

GoldenTales creates AI-generated personalized storybooks for children. The FastAPI backend (hosted on Railway) communicates with Supabase exclusively through Edge Functions - no direct database access.

## Authentication

All functions use API key authentication via the `x-api-key` header:
- Header: `x-api-key: <PDF_API_KEY>`
- Validate against environment variable `PDF_API_KEY`
- Return 401 if invalid/missing

## Environment Variables (all functions need these)

- `SUPABASE_URL` - Project URL
- `SUPABASE_SERVICE_ROLE_KEY` - Service role key for bypassing RLS
- `PDF_API_KEY` - API key for authentication

## Standard Response Format

Success:
```json
{
  "success": true,
  "data": { /* resource */ }
}
```

Error:
```json
{
  "success": false,
  "error": "Message",
  "error_code": "not_found" // optional
}
```

## Database Schema

### stories table
```sql
CREATE TABLE stories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,
    child_name VARCHAR(100) NOT NULL,
    child_age INT NOT NULL,
    theme VARCHAR(50) NOT NULL,
    art_style VARCHAR(50) DEFAULT 'watercolor',
    character_json JSONB DEFAULT '{}',
    gender VARCHAR(20),
    skin_tone VARCHAR(50),
    hair_color VARCHAR(50),
    hair_style VARCHAR(50),
    eye_color VARCHAR(50),
    occasion VARCHAR(100),
    special_details TEXT,
    photo_url TEXT,
    siblings TEXT,
    favorite_characters TEXT,
    pets TEXT,
    parents TEXT,
    friends TEXT,
    status VARCHAR(30) DEFAULT 'generating',
    cover_image_url TEXT,
    error_json JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### pages table
```sql
CREATE TABLE pages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    story_id UUID REFERENCES stories(id) ON DELETE CASCADE,
    page_number INT NOT NULL,
    text_content TEXT NOT NULL,
    image_prompt TEXT,
    image_url TEXT,
    version INT DEFAULT 1,
    is_current BOOLEAN DEFAULT true,
    edited_by_user BOOLEAN DEFAULT false,
    regen_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### orders table
```sql
CREATE TABLE orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    shopify_order_id VARCHAR(100) UNIQUE,
    shopify_order_number VARCHAR(50),
    story_id UUID NOT NULL REFERENCES stories(id),
    format VARCHAR(20) NOT NULL, -- 'digital', 'softcover', 'hardcover'
    book_size VARCHAR(20) DEFAULT '8x8',
    quantity INT DEFAULT 1,
    base_price DECIMAL(10,2) DEFAULT 0,
    shipping_cost DECIMAL(10,2) DEFAULT 0,
    gift_wrap_cost DECIMAL(10,2) DEFAULT 0,
    discount_amount DECIMAL(10,2) DEFAULT 0,
    tax_amount DECIMAL(10,2) DEFAULT 0,
    total_amount DECIMAL(10,2) DEFAULT 0,
    currency VARCHAR(3) DEFAULT 'USD',
    shipping_tier VARCHAR(20),
    shipping_address JSONB,
    is_gift BOOLEAN DEFAULT false,
    gift_message TEXT,
    gift_wrap BOOLEAN DEFAULT false,
    recipient_email VARCHAR(255),
    customer_email VARCHAR(255),
    customer_name VARCHAR(200),
    customer_phone VARCHAR(50),
    status VARCHAR(30) DEFAULT 'pending_payment',
    status_history JSONB DEFAULT '[]',
    print_job_id VARCHAR(100),
    pdf_storage_path TEXT,
    pdf_url TEXT,
    pdf_generated_at TIMESTAMP,
    fulfillment_provider VARCHAR(50),
    fulfillment_order_id VARCHAR(100),
    tracking_number VARCHAR(100),
    tracking_url TEXT,
    shipped_at TIMESTAMP,
    delivered_at TIMESTAMP,
    metadata JSONB DEFAULT '{}',
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

## Edge Functions to Create

### 1. create-story
POST - Creates a new story

Request:
```json
{
  "child_name": "Emma",
  "child_age": 6,
  "theme": "christmas",
  "art_style": "watercolor",
  "character_json": {},
  "photo_url": null,
  "siblings": null,
  "pets": null
}
```

Response (201):
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "child_name": "Emma",
    "status": "generating",
    "created_at": "2024-12-16T10:00:00Z"
  }
}
```

### 2. get-story
POST - Gets a story by ID

Request:
```json
{
  "story_id": "uuid"
}
```

Response (200):
```json
{
  "success": true,
  "data": { /* full story object */ }
}
```

If not found, return `{ "success": false, "error": "Story not found", "error_code": "not_found" }` with status 200.

### 3. update-story
POST - Updates a story

Request:
```json
{
  "story_id": "uuid",
  "updates": {
    "status": "ready",
    "cover_image_url": "https://..."
  }
}
```

Don't allow updating: id, user_id, created_at
Always set updated_at to current timestamp.

### 4. create-page
POST - Creates a page for a story

Request:
```json
{
  "story_id": "uuid",
  "page_number": 1,
  "text_content": "Once upon a time...",
  "image_prompt": "A watercolor illustration of...",
  "image_url": "https://..."
}
```

Verify story exists before creating. Set version=1, is_current=true, edited_by_user=false, regen_count=0.

### 5. get-pages
POST - Gets all current pages for a story

Request:
```json
{
  "story_id": "uuid"
}
```

Response:
```json
{
  "success": true,
  "data": [
    { "id": "uuid", "page_number": 1, "text_content": "...", "image_url": "..." },
    { "id": "uuid", "page_number": 2, "text_content": "...", "image_url": "..." }
  ]
}
```

Filter by `is_current = true`, order by `page_number ASC`.

### 6. update-page
POST - Updates a page

Request:
```json
{
  "page_id": "uuid",
  "updates": {
    "image_url": "https://new-url...",
    "text_content": "Updated text",
    "edited_by_user": true
  }
}
```

Don't allow updating: id, story_id, created_at

### 7. create-order
POST - Creates an order

Request:
```json
{
  "story_id": "uuid",
  "format": "hardcover",
  "base_price": 39.99,
  "total_amount": 49.99,
  "customer_email": "customer@example.com",
  "shipping_address": { "street": "123 Main St", "city": "NYC", "state": "NY", "postal_code": "10001", "country": "US" }
}
```

Verify story exists. Set status="pending_payment", initialize status_history with first entry.
Validate format is one of: digital, softcover, hardcover.

### 8. get-order
POST - Gets an order by ID or Shopify ID

Request (by order_id):
```json
{
  "order_id": "uuid"
}
```

OR (by shopify_order_id):
```json
{
  "shopify_order_id": "shopify-123"
}
```

Support both lookup methods. Return not_found error if neither matches.

### 9. update-order
POST - Updates an order

Request:
```json
{
  "order_id": "uuid",
  "updates": {
    "status": "shipped",
    "tracking_number": "1Z999...",
    "shipped_at": "2024-12-16T15:00:00Z"
  }
}
```

If status changes, append to status_history array:
```json
{
  "status": "shipped",
  "previous_status": "pdf_ready",
  "timestamp": "2024-12-16T15:00:00Z"
}
```

### 10. get-orders-by-status
POST - Gets orders filtered by status

Request:
```json
{
  "status": "pending_payment",
  "limit": 100
}
```

Max limit: 500. Order by created_at DESC.

### 11. get-orders-by-customer
POST - Gets orders for a customer

Request:
```json
{
  "customer_email": "customer@example.com",
  "limit": 50
}
```

Validate email format. Max limit: 200. Order by created_at DESC. Case-insensitive email match.

## Technical Requirements

1. Use Deno runtime with Supabase client v2
2. All functions use POST method
3. Handle CORS with preflight OPTIONS requests
4. Use service role key to bypass RLS
5. Validate UUID format for IDs (regex: /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i)
6. Log errors to console with context
7. Return proper HTTP status codes (200, 201, 400, 401, 404, 500)
8. Use `.maybeSingle()` for single record fetches to handle not found gracefully

## Code Template Structure

Each function should follow this structure:

```typescript
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type, x-api-key",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

Deno.serve(async (req: Request) => {
  // Handle CORS preflight
  if (req.method === "OPTIONS") {
    return new Response(null, { headers: corsHeaders });
  }

  // Only POST allowed
  if (req.method !== "POST") {
    return new Response(
      JSON.stringify({ success: false, error: "Method not allowed" }),
      { status: 405, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  }

  try {
    // Validate API key
    const apiKey = req.headers.get("x-api-key");
    if (!apiKey || apiKey !== Deno.env.get("PDF_API_KEY")) {
      return new Response(
        JSON.stringify({ success: false, error: "Unauthorized" }),
        { status: 401, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    // Parse body
    const body = await req.json();

    // Initialize Supabase
    const supabase = createClient(
      Deno.env.get("SUPABASE_URL")!,
      Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!
    );

    // Function-specific logic here...

    return new Response(
      JSON.stringify({ success: true, data: result }),
      { status: 200, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );

  } catch (error) {
    console.error("Error:", error);
    return new Response(
      JSON.stringify({ success: false, error: "Internal server error" }),
      { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  }
});
```

Please create all 11 Edge Functions following these specifications. Each function should be in its own file, production-ready with proper error handling, validation, and logging.
```

---

## 📋 ALTERNATIVE: Shorter Single-Function Prompts

If Lovable has token limits, use these individual prompts:

### Prompt for create-story

```
Create a Supabase Edge Function called "create-story" for a children's storybook platform.

Authentication: x-api-key header validated against PDF_API_KEY env var

Request (POST):
{
  "child_name": "Emma", // required
  "child_age": 6, // required
  "theme": "christmas", // required
  "art_style": "watercolor",
  "character_json": {},
  "photo_url": null
}

Stories table columns: id (uuid), child_name, child_age, theme, art_style, character_json (jsonb), gender, skin_tone, hair_color, hair_style, eye_color, occasion, special_details, photo_url, siblings, pets, parents, friends, favorite_characters, status (default 'generating'), cover_image_url, error_json, created_at, updated_at

Response format:
{ "success": true, "data": { /* story object */ } }
{ "success": false, "error": "message" }

Use Deno runtime, @supabase/supabase-js@2, service role key. Handle CORS. Return 201 on success.
```

### Prompt for get-story

```
Create a Supabase Edge Function called "get-story" that retrieves a story by ID.

Authentication: x-api-key header validated against PDF_API_KEY env var

Request (POST):
{ "story_id": "uuid-string" }

Validate UUID format. Use .maybeSingle() to handle not found.

If found: { "success": true, "data": { /* story */ } }
If not found: { "success": false, "error": "Story not found", "error_code": "not_found" }

Use Deno runtime, @supabase/supabase-js@2, service role key. Handle CORS.
```

### Prompt for update-story

```
Create a Supabase Edge Function called "update-story" that updates a story.

Authentication: x-api-key header validated against PDF_API_KEY env var

Request (POST):
{
  "story_id": "uuid",
  "updates": { "status": "ready", "cover_image_url": "https://..." }
}

Rules:
- Don't allow updating: id, user_id, created_at
- Always set updated_at to current timestamp
- Validate story_id is valid UUID

Response: { "success": true, "data": { /* updated story */ } }

Use Deno runtime, @supabase/supabase-js@2, service role key. Handle CORS.
```

### Prompt for create-page

```
Create a Supabase Edge Function called "create-page" that creates a story page.

Authentication: x-api-key header validated against PDF_API_KEY env var

Request (POST):
{
  "story_id": "uuid", // required
  "page_number": 1, // required
  "text_content": "Once upon a time...", // required
  "image_prompt": "A watercolor illustration...",
  "image_url": "https://..."
}

Rules:
- Verify story exists before creating
- Set defaults: version=1, is_current=true, edited_by_user=false, regen_count=0

Pages table: id, story_id, page_number, text_content, image_prompt, image_url, version, is_current, edited_by_user, regen_count, created_at, updated_at

Return 201 on success. Use Deno runtime, @supabase/supabase-js@2, service role key. Handle CORS.
```

### Prompt for get-pages

```
Create a Supabase Edge Function called "get-pages" that gets all pages for a story.

Authentication: x-api-key header validated against PDF_API_KEY env var

Request (POST):
{ "story_id": "uuid" }

Query: SELECT * FROM pages WHERE story_id = ? AND is_current = true ORDER BY page_number ASC

Response: { "success": true, "data": [ /* pages array */ ] }

Return empty array if no pages found (not an error).

Use Deno runtime, @supabase/supabase-js@2, service role key. Handle CORS.
```

### Prompt for update-page

```
Create a Supabase Edge Function called "update-page" that updates a page.

Authentication: x-api-key header validated against PDF_API_KEY env var

Request (POST):
{
  "page_id": "uuid",
  "updates": { "image_url": "https://...", "text_content": "Updated", "edited_by_user": true }
}

Rules:
- Don't allow updating: id, story_id, created_at
- Always set updated_at to current timestamp

Response: { "success": true, "data": { /* updated page */ } }

Use Deno runtime, @supabase/supabase-js@2, service role key. Handle CORS.
```

### Prompt for create-order

```
Create a Supabase Edge Function called "create-order" for a storybook e-commerce.

Authentication: x-api-key header validated against PDF_API_KEY env var

Request (POST):
{
  "story_id": "uuid", // required
  "format": "hardcover", // required: digital|softcover|hardcover
  "base_price": 39.99,
  "total_amount": 49.99,
  "customer_email": "test@example.com",
  "customer_name": "John Doe",
  "shipping_address": { "street": "...", "city": "...", "state": "...", "postal_code": "...", "country": "..." }
}

Rules:
- Verify story exists
- Validate format is: digital, softcover, or hardcover
- Set status = "pending_payment"
- Initialize status_history: [{ "status": "pending_payment", "timestamp": "..." }]

Orders table: id, shopify_order_id, story_id, format, book_size, quantity, base_price, shipping_cost, total_amount, currency, shipping_tier, shipping_address (jsonb), customer_email, customer_name, status, status_history (jsonb), created_at, updated_at

Return 201 on success. Use Deno runtime, @supabase/supabase-js@2, service role key. Handle CORS.
```

### Prompt for get-order

```
Create a Supabase Edge Function called "get-order" that retrieves an order.

Authentication: x-api-key header validated against PDF_API_KEY env var

Request (POST) - supports two lookup methods:
{ "order_id": "uuid" }
OR
{ "shopify_order_id": "shopify-123456" }

Logic:
- If order_id provided, query by id
- If shopify_order_id provided, query by shopify_order_id
- Require at least one parameter

If found: { "success": true, "data": { /* order */ } }
If not found: { "success": false, "error": "Order not found", "error_code": "not_found" }

Use Deno runtime, @supabase/supabase-js@2, service role key. Handle CORS.
```

### Prompt for update-order

```
Create a Supabase Edge Function called "update-order" that updates an order with status history tracking.

Authentication: x-api-key header validated against PDF_API_KEY env var

Request (POST):
{
  "order_id": "uuid",
  "updates": { "status": "shipped", "tracking_number": "1Z999..." }
}

Special handling for status changes:
1. Fetch current order to get current status and status_history
2. If status is changing, append to status_history array:
   { "status": "new_status", "previous_status": "old_status", "timestamp": "ISO-date" }

Don't allow updating: id, story_id, created_at
Always set updated_at.

Response: { "success": true, "data": { /* updated order with new status_history */ } }

Use Deno runtime, @supabase/supabase-js@2, service role key. Handle CORS.
```

### Prompt for get-orders-by-status

```
Create a Supabase Edge Function called "get-orders-by-status" that queries orders by status.

Authentication: x-api-key header validated against PDF_API_KEY env var

Request (POST):
{
  "status": "pending_payment", // required
  "limit": 100 // optional, default 100, max 500
}

Query: SELECT * FROM orders WHERE status = ? ORDER BY created_at DESC LIMIT ?

Response: { "success": true, "data": [ /* orders array */ ] }

Return empty array if no orders match.

Use Deno runtime, @supabase/supabase-js@2, service role key. Handle CORS.
```

### Prompt for get-orders-by-customer

```
Create a Supabase Edge Function called "get-orders-by-customer" that queries orders by customer email.

Authentication: x-api-key header validated against PDF_API_KEY env var

Request (POST):
{
  "customer_email": "test@example.com", // required
  "limit": 50 // optional, default 50, max 200
}

Rules:
- Validate email format (basic regex)
- Case-insensitive email matching (use .toLowerCase())

Query: SELECT * FROM orders WHERE customer_email = ? ORDER BY created_at DESC LIMIT ?

Response: { "success": true, "data": [ /* orders array */ ] }

Use Deno runtime, @supabase/supabase-js@2, service role key. Handle CORS.
```

---

## 🔧 Post-Generation Setup

After Lovable generates the functions:

1. **Set Environment Variables** in Supabase Dashboard → Edge Functions → Secrets:
   ```
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_SERVICE_ROLE_KEY=eyJhbG...
   PDF_API_KEY=your-secure-random-key
   ```

2. **Deploy Functions**:
   ```bash
   supabase functions deploy create-story
   supabase functions deploy get-story
   supabase functions deploy update-story
   supabase functions deploy create-page
   supabase functions deploy get-pages
   supabase functions deploy update-page
   supabase functions deploy create-order
   supabase functions deploy get-order
   supabase functions deploy update-order
   supabase functions deploy get-orders-by-status
   supabase functions deploy get-orders-by-customer
   ```

3. **Test Each Function**:
   ```bash
   curl -X POST \
     'https://your-project.supabase.co/functions/v1/create-story' \
     -H 'Content-Type: application/json' \
     -H 'x-api-key: your-pdf-api-key' \
     -d '{"child_name": "Test", "child_age": 5, "theme": "space"}'
   ```



