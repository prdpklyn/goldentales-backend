# Supabase Edge Functions Specification

> GoldenTales Backend - Complete Edge Function Reference

## Overview

The GoldenTales backend exclusively uses Supabase Edge Functions for all database operations. This architectural constraint ensures:

- **Security**: Row Level Security (RLS) enforcement at the database layer
- **Scalability**: Stateless functions that scale automatically
- **Separation of Concerns**: Business logic isolated from the FastAPI backend
- **Consistency**: All database access goes through the same controlled interface

## Environment Variables (All Edge Functions)

All Edge Functions require these base environment variables:

| Variable | Description | Required |
|----------|-------------|----------|
| `SUPABASE_URL` | Supabase project URL | ✅ |
| `SUPABASE_SERVICE_ROLE_KEY` | Service role key for database writes | ✅ |
| `SUPABASE_ANON_KEY` | Anon key for auth verification | ✅ (for user-facing functions) |
| `PDF_API_KEY` | API key for backend service calls | ✅ (for backend functions) |

---

## Table of Contents

1. [User-Facing Functions](#1-user-facing-functions)
   - [weave-story](#11-weave-story)
2. [Backend Service Functions](#2-backend-service-functions)
   - [get-story-for-pdf](#21-get-story-for-pdf)
   - [create-story](#22-create-story)
   - [get-story](#23-get-story)
   - [update-story](#24-update-story)
   - [create-page](#25-create-page)
   - [get-pages](#26-get-pages)
   - [update-page](#27-update-page)
   - [create-order](#28-create-order)
   - [get-order](#29-get-order)
   - [update-order](#210-update-order)
   - [get-orders-by-status](#211-get-orders-by-status)
   - [get-orders-by-customer](#212-get-orders-by-customer)
3. [Standard Response Format](#3-standard-response-format)
4. [Error Codes](#4-error-codes)
5. [Database Schema Reference](#5-database-schema-reference)

---

## 1. User-Facing Functions

### 1.1 weave-story

**Status**: ✅ IMPLEMENTED

Creates personalized storybooks by orchestrating story creation, Railway API calls for AI generation, and page insertion.

#### Endpoint
```
POST /functions/v1/weave-story
```

#### Authentication
- **Type**: Bearer Token (JWT)
- **Header**: `Authorization: Bearer <user_jwt>`

#### Rate Limiting
- Default: 3 stories per 24-hour window
- Configurable via `RATE_LIMIT_MAX` and `RATE_LIMIT_WINDOW_HOURS`

#### Additional Environment Variables
| Variable | Description | Default |
|----------|-------------|---------|
| `RAILWAY_API_URL` | Railway story generation API endpoint | `https://taleom-production.up.railway.app` |
| `ALLOWED_ORIGINS` | Comma-separated allowed origins | `""` |
| `RATE_LIMIT_MAX` | Max stories per window | `3` |
| `RATE_LIMIT_WINDOW_HOURS` | Rate limit window in hours | `24` |

#### Request Body
```typescript
interface WeaveStoryRequest {
  // Required fields
  child_name: string;           // Max 50 chars
  child_age: number;            // 1-18
  theme: "space" | "dinosaur" | "ocean" | "forest" | "superhero" | "christmas" | "birthday" | "bedtime" | "adventure";
  art_style: "watercolor" | "cartoon" | "storybook" | "anime";
  character_json: {
    hero: {
      name: string;
      gender: string;
      age?: number;
      skin_tone: string;
      hair_color: string;
      hair_style: string;
      eye_color: string;
      has_glasses?: boolean;
      glasses_type?: string;
      has_freckles?: boolean;
      has_dimples?: boolean;
      body_type?: string;
      favorite_outfit?: string;
      favorite_color?: string;
      other_features?: string;
    };
    additional_characters?: Array<{
      name: string;
      character_type: string;
      relationship: string;
      gender?: string;
      age_description?: string;
      skin_tone?: string;
      hair_color?: string;
      distinctive_feature?: string;
      pet_species?: string;
      pet_color?: string;
    }>;
  };
  
  // Optional fields
  occasion?: string;
  special_details?: string;     // Max 500 chars
  photo_url?: string;
}
```

#### Response (Success - 200)
```json
{
  "storyId": "uuid-string",
  "quota": {
    "used": 1,
    "limit": 3,
    "remaining": 2,
    "windowHours": 24
  }
}
```

#### Response (Error)
```json
{
  "error": "Error message",
  "code": "ERROR_CODE",
  "details": "Optional details"
}
```

#### Error Codes
| Code | Status | Description |
|------|--------|-------------|
| `UNAUTHORIZED` | 401 | Invalid/missing JWT |
| `VALIDATION_ERROR` | 400 | Invalid request body |
| `RATE_LIMIT_EXCEEDED` | 429 | User exceeded story limit |
| `GENERATION_FAILED` | 502 | Railway API failure |
| `DATABASE_ERROR` | 500 | Database operation failed |
| `EMPTY_CONTENT` | 502 | No pages generated |

---

## 2. Backend Service Functions

All backend service functions use API key authentication:
```
Header: x-api-key: <PDF_API_KEY>
```

### 2.1 get-story-for-pdf

**Status**: ✅ IMPLEMENTED

Fetches story and page data for PDF generation.

#### Endpoint
```
POST /functions/v1/get-story-for-pdf
```

#### Request Body
```json
{
  "story_id": "uuid-string"
}
```

#### Response (Success - 200)
```json
{
  "success": true,
  "data": {
    "story": {
      "id": "uuid-string",
      "user_id": "uuid-string",
      "child_name": "Emma",
      "child_age": 6,
      "theme": "christmas",
      "art_style": "watercolor",
      "character_json": {...},
      "gender": "female",
      "skin_tone": "fair",
      "hair_color": "brown",
      "hair_style": "curly",
      "eye_color": "blue",
      "occasion": "birthday",
      "special_details": "Loves dinosaurs",
      "photo_url": null,
      "status": "ready",
      "cover_image_url": "https://...",
      "error_json": null,
      "created_at": "2024-12-16T10:00:00Z",
      "updated_at": "2024-12-16T10:05:00Z"
    },
    "pages": [
      {
        "id": "uuid-string",
        "story_id": "uuid-string",
        "page_number": 1,
        "text_content": "Once upon a time...",
        "image_prompt": "A watercolor illustration of...",
        "image_url": "https://...",
        "version": 1,
        "is_current": true,
        "edited_by_user": false,
        "regen_count": 0,
        "created_at": "2024-12-16T10:01:00Z",
        "updated_at": "2024-12-16T10:01:00Z"
      }
    ]
  }
}
```

#### Response (Error - 404)
```json
{
  "success": false,
  "error": "Story not found"
}
```

---

### 2.2 create-story

**Status**: 🔲 TO BE IMPLEMENTED

Creates a new story record in the database.

#### Endpoint
```
POST /functions/v1/create-story
```

#### Request Body
```typescript
interface CreateStoryRequest {
  // Required
  child_name: string;
  child_age: number;
  theme: string;
  
  // Optional
  photo_url?: string;
  siblings?: string;
  favorite_characters?: string;
  pets?: string;
  parents?: string;
  friends?: string;
  art_style?: string;
  character_json?: object;
  occasion?: string;
  special_details?: string;
  gender?: string;
  skin_tone?: string;
  hair_color?: string;
  hair_style?: string;
  eye_color?: string;
  status?: string;  // Default: "generating"
}
```

#### Response (Success - 201)
```json
{
  "success": true,
  "data": {
    "id": "uuid-string",
    "child_name": "Emma",
    "child_age": 6,
    "theme": "christmas",
    "status": "generating",
    "created_at": "2024-12-16T10:00:00Z",
    "updated_at": "2024-12-16T10:00:00Z"
  }
}
```

#### Implementation Template
```typescript
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type, x-api-key",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response(null, { headers: corsHeaders });
  }

  if (req.method !== "POST") {
    return new Response(
      JSON.stringify({ success: false, error: "Method not allowed" }),
      { status: 405, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  }

  try {
    // Validate API key
    const apiKey = req.headers.get("x-api-key");
    const expectedApiKey = Deno.env.get("PDF_API_KEY");

    if (!apiKey || apiKey !== expectedApiKey) {
      return new Response(
        JSON.stringify({ success: false, error: "Unauthorized" }),
        { status: 401, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    const body = await req.json();
    
    // Validate required fields
    if (!body.child_name || !body.child_age || !body.theme) {
      return new Response(
        JSON.stringify({ success: false, error: "Missing required fields: child_name, child_age, theme" }),
        { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    const supabase = createClient(
      Deno.env.get("SUPABASE_URL")!,
      Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!
    );

    const storyData = {
      child_name: body.child_name,
      child_age: body.child_age,
      theme: body.theme,
      photo_url: body.photo_url || null,
      siblings: body.siblings || null,
      favorite_characters: body.favorite_characters || null,
      pets: body.pets || null,
      parents: body.parents || null,
      friends: body.friends || null,
      art_style: body.art_style || "watercolor",
      character_json: body.character_json || {},
      occasion: body.occasion || null,
      special_details: body.special_details || null,
      gender: body.gender || null,
      skin_tone: body.skin_tone || null,
      hair_color: body.hair_color || null,
      hair_style: body.hair_style || null,
      eye_color: body.eye_color || null,
      status: body.status || "generating",
    };

    const { data, error } = await supabase
      .from("stories")
      .insert(storyData)
      .select()
      .single();

    if (error) {
      console.error("Error creating story:", error);
      return new Response(
        JSON.stringify({ success: false, error: "Failed to create story", details: error.message }),
        { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    return new Response(
      JSON.stringify({ success: true, data }),
      { status: 201, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );

  } catch (error) {
    console.error("Unexpected error:", error);
    return new Response(
      JSON.stringify({ success: false, error: "Internal server error" }),
      { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  }
});
```

---

### 2.3 get-story

**Status**: 🔲 TO BE IMPLEMENTED

Retrieves a story by ID.

#### Endpoint
```
POST /functions/v1/get-story
```

#### Request Body
```json
{
  "story_id": "uuid-string"
}
```

#### Response (Success - 200)
```json
{
  "success": true,
  "data": {
    "id": "uuid-string",
    "child_name": "Emma",
    "child_age": 6,
    "theme": "christmas",
    "art_style": "watercolor",
    "character_json": {...},
    "status": "ready",
    "cover_image_url": "https://...",
    "created_at": "2024-12-16T10:00:00Z",
    "updated_at": "2024-12-16T10:05:00Z"
  }
}
```

#### Response (Not Found - 200)
```json
{
  "success": false,
  "error": "Story not found",
  "error_code": "not_found"
}
```

#### Implementation Template
```typescript
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type, x-api-key",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response(null, { headers: corsHeaders });
  }

  if (req.method !== "POST") {
    return new Response(
      JSON.stringify({ success: false, error: "Method not allowed" }),
      { status: 405, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  }

  try {
    const apiKey = req.headers.get("x-api-key");
    const expectedApiKey = Deno.env.get("PDF_API_KEY");

    if (!apiKey || apiKey !== expectedApiKey) {
      return new Response(
        JSON.stringify({ success: false, error: "Unauthorized" }),
        { status: 401, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    const { story_id } = await req.json();

    if (!story_id) {
      return new Response(
        JSON.stringify({ success: false, error: "story_id is required" }),
        { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    // Validate UUID format
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    if (!uuidRegex.test(story_id)) {
      return new Response(
        JSON.stringify({ success: false, error: "Invalid story_id format" }),
        { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    const supabase = createClient(
      Deno.env.get("SUPABASE_URL")!,
      Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!
    );

    const { data, error } = await supabase
      .from("stories")
      .select("*")
      .eq("id", story_id)
      .maybeSingle();

    if (error) {
      console.error("Error fetching story:", error);
      return new Response(
        JSON.stringify({ success: false, error: "Failed to fetch story" }),
        { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    if (!data) {
      return new Response(
        JSON.stringify({ success: false, error: "Story not found", error_code: "not_found" }),
        { status: 200, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    return new Response(
      JSON.stringify({ success: true, data }),
      { status: 200, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );

  } catch (error) {
    console.error("Unexpected error:", error);
    return new Response(
      JSON.stringify({ success: false, error: "Internal server error" }),
      { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  }
});
```

---

### 2.4 update-story

**Status**: 🔲 TO BE IMPLEMENTED

Updates an existing story.

#### Endpoint
```
POST /functions/v1/update-story
```

#### Request Body
```json
{
  "story_id": "uuid-string",
  "updates": {
    "status": "ready",
    "cover_image_url": "https://...",
    "any_other_field": "value"
  }
}
```

#### Response (Success - 200)
```json
{
  "success": true,
  "data": {
    "id": "uuid-string",
    "status": "ready",
    "updated_at": "2024-12-16T10:05:00Z"
  }
}
```

#### Implementation Template
```typescript
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type, x-api-key",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

// Fields that cannot be updated
const IMMUTABLE_FIELDS = ["id", "user_id", "created_at"];

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response(null, { headers: corsHeaders });
  }

  if (req.method !== "POST") {
    return new Response(
      JSON.stringify({ success: false, error: "Method not allowed" }),
      { status: 405, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  }

  try {
    const apiKey = req.headers.get("x-api-key");
    const expectedApiKey = Deno.env.get("PDF_API_KEY");

    if (!apiKey || apiKey !== expectedApiKey) {
      return new Response(
        JSON.stringify({ success: false, error: "Unauthorized" }),
        { status: 401, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    const { story_id, updates } = await req.json();

    if (!story_id || !updates) {
      return new Response(
        JSON.stringify({ success: false, error: "story_id and updates are required" }),
        { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    // Remove immutable fields from updates
    const safeUpdates = { ...updates };
    IMMUTABLE_FIELDS.forEach(field => delete safeUpdates[field]);
    
    // Always update updated_at
    safeUpdates.updated_at = new Date().toISOString();

    const supabase = createClient(
      Deno.env.get("SUPABASE_URL")!,
      Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!
    );

    const { data, error } = await supabase
      .from("stories")
      .update(safeUpdates)
      .eq("id", story_id)
      .select()
      .single();

    if (error) {
      console.error("Error updating story:", error);
      return new Response(
        JSON.stringify({ success: false, error: "Failed to update story" }),
        { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    return new Response(
      JSON.stringify({ success: true, data }),
      { status: 200, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );

  } catch (error) {
    console.error("Unexpected error:", error);
    return new Response(
      JSON.stringify({ success: false, error: "Internal server error" }),
      { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  }
});
```

---

### 2.5 create-page

**Status**: 🔲 TO BE IMPLEMENTED

Creates a new page for a story.

#### Endpoint
```
POST /functions/v1/create-page
```

#### Request Body
```json
{
  "story_id": "uuid-string",
  "page_number": 1,
  "text_content": "Once upon a time...",
  "image_prompt": "A watercolor illustration of...",
  "image_url": "https://..."
}
```

#### Response (Success - 201)
```json
{
  "success": true,
  "data": {
    "id": "uuid-string",
    "story_id": "uuid-string",
    "page_number": 1,
    "text_content": "Once upon a time...",
    "image_prompt": "A watercolor illustration of...",
    "image_url": "https://...",
    "version": 1,
    "is_current": true,
    "edited_by_user": false,
    "regen_count": 0,
    "created_at": "2024-12-16T10:01:00Z",
    "updated_at": "2024-12-16T10:01:00Z"
  }
}
```

#### Implementation Template
```typescript
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type, x-api-key",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response(null, { headers: corsHeaders });
  }

  if (req.method !== "POST") {
    return new Response(
      JSON.stringify({ success: false, error: "Method not allowed" }),
      { status: 405, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  }

  try {
    const apiKey = req.headers.get("x-api-key");
    const expectedApiKey = Deno.env.get("PDF_API_KEY");

    if (!apiKey || apiKey !== expectedApiKey) {
      return new Response(
        JSON.stringify({ success: false, error: "Unauthorized" }),
        { status: 401, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    const body = await req.json();
    
    // Validate required fields
    if (!body.story_id || body.page_number === undefined || !body.text_content) {
      return new Response(
        JSON.stringify({ success: false, error: "Missing required fields: story_id, page_number, text_content" }),
        { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    const supabase = createClient(
      Deno.env.get("SUPABASE_URL")!,
      Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!
    );

    // Verify story exists
    const { data: story } = await supabase
      .from("stories")
      .select("id")
      .eq("id", body.story_id)
      .maybeSingle();

    if (!story) {
      return new Response(
        JSON.stringify({ success: false, error: "Story not found" }),
        { status: 404, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    const pageData = {
      story_id: body.story_id,
      page_number: body.page_number,
      text_content: body.text_content,
      image_prompt: body.image_prompt || null,
      image_url: body.image_url || null,
      version: 1,
      is_current: true,
      edited_by_user: false,
      regen_count: 0,
    };

    const { data, error } = await supabase
      .from("pages")
      .insert(pageData)
      .select()
      .single();

    if (error) {
      console.error("Error creating page:", error);
      return new Response(
        JSON.stringify({ success: false, error: "Failed to create page" }),
        { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    return new Response(
      JSON.stringify({ success: true, data }),
      { status: 201, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );

  } catch (error) {
    console.error("Unexpected error:", error);
    return new Response(
      JSON.stringify({ success: false, error: "Internal server error" }),
      { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  }
});
```

---

### 2.6 get-pages

**Status**: 🔲 TO BE IMPLEMENTED

Gets all current pages for a story, ordered by page number.

#### Endpoint
```
POST /functions/v1/get-pages
```

#### Request Body
```json
{
  "story_id": "uuid-string"
}
```

#### Response (Success - 200)
```json
{
  "success": true,
  "data": [
    {
      "id": "uuid-string",
      "story_id": "uuid-string",
      "page_number": 1,
      "text_content": "Once upon a time...",
      "image_prompt": "A watercolor illustration of...",
      "image_url": "https://...",
      "version": 1,
      "is_current": true,
      "created_at": "2024-12-16T10:01:00Z"
    },
    {
      "id": "uuid-string",
      "story_id": "uuid-string",
      "page_number": 2,
      "text_content": "In a magical kingdom...",
      "image_url": "https://...",
      "version": 1,
      "is_current": true,
      "created_at": "2024-12-16T10:01:00Z"
    }
  ]
}
```

#### Implementation Template
```typescript
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type, x-api-key",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response(null, { headers: corsHeaders });
  }

  if (req.method !== "POST") {
    return new Response(
      JSON.stringify({ success: false, error: "Method not allowed" }),
      { status: 405, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  }

  try {
    const apiKey = req.headers.get("x-api-key");
    const expectedApiKey = Deno.env.get("PDF_API_KEY");

    if (!apiKey || apiKey !== expectedApiKey) {
      return new Response(
        JSON.stringify({ success: false, error: "Unauthorized" }),
        { status: 401, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    const { story_id } = await req.json();

    if (!story_id) {
      return new Response(
        JSON.stringify({ success: false, error: "story_id is required" }),
        { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    const supabase = createClient(
      Deno.env.get("SUPABASE_URL")!,
      Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!
    );

    const { data, error } = await supabase
      .from("pages")
      .select("*")
      .eq("story_id", story_id)
      .eq("is_current", true)
      .order("page_number", { ascending: true });

    if (error) {
      console.error("Error fetching pages:", error);
      return new Response(
        JSON.stringify({ success: false, error: "Failed to fetch pages" }),
        { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    return new Response(
      JSON.stringify({ success: true, data: data || [] }),
      { status: 200, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );

  } catch (error) {
    console.error("Unexpected error:", error);
    return new Response(
      JSON.stringify({ success: false, error: "Internal server error" }),
      { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  }
});
```

---

### 2.7 update-page

**Status**: 🔲 TO BE IMPLEMENTED

Updates an existing page.

#### Endpoint
```
POST /functions/v1/update-page
```

#### Request Body
```json
{
  "page_id": "uuid-string",
  "updates": {
    "image_url": "https://new-image-url...",
    "text_content": "Updated text...",
    "edited_by_user": true
  }
}
```

#### Response (Success - 200)
```json
{
  "success": true,
  "data": {
    "id": "uuid-string",
    "story_id": "uuid-string",
    "page_number": 1,
    "text_content": "Updated text...",
    "image_url": "https://new-image-url...",
    "edited_by_user": true,
    "updated_at": "2024-12-16T10:10:00Z"
  }
}
```

#### Implementation Template
```typescript
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type, x-api-key",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

const IMMUTABLE_FIELDS = ["id", "story_id", "created_at"];

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response(null, { headers: corsHeaders });
  }

  if (req.method !== "POST") {
    return new Response(
      JSON.stringify({ success: false, error: "Method not allowed" }),
      { status: 405, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  }

  try {
    const apiKey = req.headers.get("x-api-key");
    const expectedApiKey = Deno.env.get("PDF_API_KEY");

    if (!apiKey || apiKey !== expectedApiKey) {
      return new Response(
        JSON.stringify({ success: false, error: "Unauthorized" }),
        { status: 401, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    const { page_id, updates } = await req.json();

    if (!page_id || !updates) {
      return new Response(
        JSON.stringify({ success: false, error: "page_id and updates are required" }),
        { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    // Remove immutable fields
    const safeUpdates = { ...updates };
    IMMUTABLE_FIELDS.forEach(field => delete safeUpdates[field]);
    safeUpdates.updated_at = new Date().toISOString();

    const supabase = createClient(
      Deno.env.get("SUPABASE_URL")!,
      Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!
    );

    const { data, error } = await supabase
      .from("pages")
      .update(safeUpdates)
      .eq("id", page_id)
      .select()
      .single();

    if (error) {
      console.error("Error updating page:", error);
      return new Response(
        JSON.stringify({ success: false, error: "Failed to update page" }),
        { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    return new Response(
      JSON.stringify({ success: true, data }),
      { status: 200, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );

  } catch (error) {
    console.error("Unexpected error:", error);
    return new Response(
      JSON.stringify({ success: false, error: "Internal server error" }),
      { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  }
});
```

---

### 2.8 create-order

**Status**: 🔲 TO BE IMPLEMENTED

Creates a new order in the database.

#### Endpoint
```
POST /functions/v1/create-order
```

#### Request Body
```typescript
interface CreateOrderRequest {
  // Required
  story_id: string;             // UUID of the story/book
  format: "digital" | "softcover" | "hardcover";
  
  // Pricing (required)
  base_price: number;
  total_amount: number;
  
  // Optional
  shopify_order_id?: string;
  shopify_order_number?: string;
  book_size?: string;           // "8x8", "8.5x8.5", "10x8"
  quantity?: number;
  shipping_cost?: number;
  gift_wrap_cost?: number;
  discount_amount?: number;
  tax_amount?: number;
  currency?: string;            // Default: "USD"
  shipping_tier?: string;       // "standard", "express", "digital"
  shipping_address?: object;
  is_gift?: boolean;
  gift_message?: string;
  gift_wrap?: boolean;
  recipient_email?: string;
  customer_email?: string;
  customer_name?: string;
  customer_phone?: string;
  metadata?: object;
}
```

#### Response (Success - 201)
```json
{
  "success": true,
  "data": {
    "id": "uuid-string",
    "story_id": "uuid-string",
    "format": "hardcover",
    "status": "pending_payment",
    "total_amount": 49.99,
    "created_at": "2024-12-16T10:00:00Z"
  }
}
```

#### Implementation Template
```typescript
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type, x-api-key",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response(null, { headers: corsHeaders });
  }

  if (req.method !== "POST") {
    return new Response(
      JSON.stringify({ success: false, error: "Method not allowed" }),
      { status: 405, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  }

  try {
    const apiKey = req.headers.get("x-api-key");
    const expectedApiKey = Deno.env.get("PDF_API_KEY");

    if (!apiKey || apiKey !== expectedApiKey) {
      return new Response(
        JSON.stringify({ success: false, error: "Unauthorized" }),
        { status: 401, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    const body = await req.json();
    
    // Validate required fields
    if (!body.story_id || !body.format) {
      return new Response(
        JSON.stringify({ success: false, error: "Missing required fields: story_id, format" }),
        { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    // Validate format
    const validFormats = ["digital", "softcover", "hardcover"];
    if (!validFormats.includes(body.format)) {
      return new Response(
        JSON.stringify({ success: false, error: `Invalid format. Must be one of: ${validFormats.join(", ")}` }),
        { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    const supabase = createClient(
      Deno.env.get("SUPABASE_URL")!,
      Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!
    );

    // Verify story exists
    const { data: story } = await supabase
      .from("stories")
      .select("id")
      .eq("id", body.story_id)
      .maybeSingle();

    if (!story) {
      return new Response(
        JSON.stringify({ success: false, error: "Story not found" }),
        { status: 404, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    const orderData = {
      story_id: body.story_id,
      format: body.format,
      shopify_order_id: body.shopify_order_id || null,
      shopify_order_number: body.shopify_order_number || null,
      book_size: body.book_size || "8x8",
      quantity: body.quantity || 1,
      base_price: body.base_price || 0,
      shipping_cost: body.shipping_cost || 0,
      gift_wrap_cost: body.gift_wrap_cost || 0,
      discount_amount: body.discount_amount || 0,
      tax_amount: body.tax_amount || 0,
      total_amount: body.total_amount || 0,
      currency: body.currency || "USD",
      shipping_tier: body.shipping_tier || null,
      shipping_address: body.shipping_address || null,
      is_gift: body.is_gift || false,
      gift_message: body.gift_message || null,
      gift_wrap: body.gift_wrap || false,
      recipient_email: body.recipient_email || null,
      customer_email: body.customer_email || null,
      customer_name: body.customer_name || null,
      customer_phone: body.customer_phone || null,
      status: "pending_payment",
      status_history: [{ status: "pending_payment", timestamp: new Date().toISOString() }],
      metadata: body.metadata || {},
    };

    const { data, error } = await supabase
      .from("orders")
      .insert(orderData)
      .select()
      .single();

    if (error) {
      console.error("Error creating order:", error);
      return new Response(
        JSON.stringify({ success: false, error: "Failed to create order" }),
        { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    return new Response(
      JSON.stringify({ success: true, data }),
      { status: 201, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );

  } catch (error) {
    console.error("Unexpected error:", error);
    return new Response(
      JSON.stringify({ success: false, error: "Internal server error" }),
      { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  }
});
```

---

### 2.9 get-order

**Status**: 🔲 TO BE IMPLEMENTED

Retrieves an order by ID or Shopify order ID.

#### Endpoint
```
POST /functions/v1/get-order
```

#### Request Body
```json
{
  "order_id": "uuid-string"
}
```

OR

```json
{
  "shopify_order_id": "shopify-123456"
}
```

#### Response (Success - 200)
```json
{
  "success": true,
  "data": {
    "id": "uuid-string",
    "story_id": "uuid-string",
    "shopify_order_id": "shopify-123456",
    "format": "hardcover",
    "status": "pdf_ready",
    "total_amount": 49.99,
    "pdf_url": "https://...",
    "created_at": "2024-12-16T10:00:00Z"
  }
}
```

#### Implementation Template
```typescript
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type, x-api-key",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response(null, { headers: corsHeaders });
  }

  if (req.method !== "POST") {
    return new Response(
      JSON.stringify({ success: false, error: "Method not allowed" }),
      { status: 405, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  }

  try {
    const apiKey = req.headers.get("x-api-key");
    const expectedApiKey = Deno.env.get("PDF_API_KEY");

    if (!apiKey || apiKey !== expectedApiKey) {
      return new Response(
        JSON.stringify({ success: false, error: "Unauthorized" }),
        { status: 401, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    const { order_id, shopify_order_id } = await req.json();

    if (!order_id && !shopify_order_id) {
      return new Response(
        JSON.stringify({ success: false, error: "Either order_id or shopify_order_id is required" }),
        { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    const supabase = createClient(
      Deno.env.get("SUPABASE_URL")!,
      Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!
    );

    let query = supabase.from("orders").select("*");
    
    if (order_id) {
      query = query.eq("id", order_id);
    } else {
      query = query.eq("shopify_order_id", shopify_order_id);
    }

    const { data, error } = await query.maybeSingle();

    if (error) {
      console.error("Error fetching order:", error);
      return new Response(
        JSON.stringify({ success: false, error: "Failed to fetch order" }),
        { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    if (!data) {
      return new Response(
        JSON.stringify({ success: false, error: "Order not found", error_code: "not_found" }),
        { status: 200, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    return new Response(
      JSON.stringify({ success: true, data }),
      { status: 200, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );

  } catch (error) {
    console.error("Unexpected error:", error);
    return new Response(
      JSON.stringify({ success: false, error: "Internal server error" }),
      { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  }
});
```

---

### 2.10 update-order

**Status**: 🔲 TO BE IMPLEMENTED

Updates an order. Automatically tracks status changes in status_history.

#### Endpoint
```
POST /functions/v1/update-order
```

#### Request Body
```json
{
  "order_id": "uuid-string",
  "updates": {
    "status": "shipped",
    "tracking_number": "1Z999AA10123456784",
    "tracking_url": "https://track.ups.com/...",
    "shipped_at": "2024-12-16T15:00:00Z"
  }
}
```

#### Response (Success - 200)
```json
{
  "success": true,
  "data": {
    "id": "uuid-string",
    "status": "shipped",
    "tracking_number": "1Z999AA10123456784",
    "status_history": [
      {"status": "pending_payment", "timestamp": "2024-12-16T10:00:00Z"},
      {"status": "payment_confirmed", "timestamp": "2024-12-16T10:05:00Z"},
      {"status": "shipped", "timestamp": "2024-12-16T15:00:00Z"}
    ],
    "updated_at": "2024-12-16T15:00:00Z"
  }
}
```

#### Implementation Template
```typescript
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type, x-api-key",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

const IMMUTABLE_FIELDS = ["id", "story_id", "created_at"];

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response(null, { headers: corsHeaders });
  }

  if (req.method !== "POST") {
    return new Response(
      JSON.stringify({ success: false, error: "Method not allowed" }),
      { status: 405, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  }

  try {
    const apiKey = req.headers.get("x-api-key");
    const expectedApiKey = Deno.env.get("PDF_API_KEY");

    if (!apiKey || apiKey !== expectedApiKey) {
      return new Response(
        JSON.stringify({ success: false, error: "Unauthorized" }),
        { status: 401, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    const { order_id, updates } = await req.json();

    if (!order_id || !updates) {
      return new Response(
        JSON.stringify({ success: false, error: "order_id and updates are required" }),
        { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    const supabase = createClient(
      Deno.env.get("SUPABASE_URL")!,
      Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!
    );

    // Fetch current order for status history update
    const { data: currentOrder } = await supabase
      .from("orders")
      .select("status, status_history")
      .eq("id", order_id)
      .single();

    if (!currentOrder) {
      return new Response(
        JSON.stringify({ success: false, error: "Order not found", error_code: "not_found" }),
        { status: 200, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    // Build safe updates
    const safeUpdates = { ...updates };
    IMMUTABLE_FIELDS.forEach(field => delete safeUpdates[field]);
    safeUpdates.updated_at = new Date().toISOString();

    // If status changed, update status_history
    if (updates.status && updates.status !== currentOrder.status) {
      const history = currentOrder.status_history || [];
      history.push({
        status: updates.status,
        previous_status: currentOrder.status,
        timestamp: new Date().toISOString(),
      });
      safeUpdates.status_history = history;
    }

    const { data, error } = await supabase
      .from("orders")
      .update(safeUpdates)
      .eq("id", order_id)
      .select()
      .single();

    if (error) {
      console.error("Error updating order:", error);
      return new Response(
        JSON.stringify({ success: false, error: "Failed to update order" }),
        { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    return new Response(
      JSON.stringify({ success: true, data }),
      { status: 200, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );

  } catch (error) {
    console.error("Unexpected error:", error);
    return new Response(
      JSON.stringify({ success: false, error: "Internal server error" }),
      { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  }
});
```

---

### 2.11 get-orders-by-status

**Status**: 🔲 TO BE IMPLEMENTED

Retrieves orders filtered by status.

#### Endpoint
```
POST /functions/v1/get-orders-by-status
```

#### Request Body
```json
{
  "status": "pending_payment",
  "limit": 100
}
```

#### Response (Success - 200)
```json
{
  "success": true,
  "data": [
    {
      "id": "uuid-string",
      "story_id": "uuid-string",
      "status": "pending_payment",
      "customer_email": "customer@example.com",
      "created_at": "2024-12-16T10:00:00Z"
    }
  ]
}
```

#### Implementation Template
```typescript
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type, x-api-key",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

const MAX_LIMIT = 500;

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response(null, { headers: corsHeaders });
  }

  if (req.method !== "POST") {
    return new Response(
      JSON.stringify({ success: false, error: "Method not allowed" }),
      { status: 405, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  }

  try {
    const apiKey = req.headers.get("x-api-key");
    const expectedApiKey = Deno.env.get("PDF_API_KEY");

    if (!apiKey || apiKey !== expectedApiKey) {
      return new Response(
        JSON.stringify({ success: false, error: "Unauthorized" }),
        { status: 401, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    const { status, limit = 100 } = await req.json();

    if (!status) {
      return new Response(
        JSON.stringify({ success: false, error: "status is required" }),
        { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    const effectiveLimit = Math.min(limit, MAX_LIMIT);

    const supabase = createClient(
      Deno.env.get("SUPABASE_URL")!,
      Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!
    );

    const { data, error } = await supabase
      .from("orders")
      .select("*")
      .eq("status", status)
      .order("created_at", { ascending: false })
      .limit(effectiveLimit);

    if (error) {
      console.error("Error fetching orders:", error);
      return new Response(
        JSON.stringify({ success: false, error: "Failed to fetch orders" }),
        { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    return new Response(
      JSON.stringify({ success: true, data: data || [] }),
      { status: 200, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );

  } catch (error) {
    console.error("Unexpected error:", error);
    return new Response(
      JSON.stringify({ success: false, error: "Internal server error" }),
      { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  }
});
```

---

### 2.12 get-orders-by-customer

**Status**: 🔲 TO BE IMPLEMENTED

Retrieves orders for a specific customer by email.

#### Endpoint
```
POST /functions/v1/get-orders-by-customer
```

#### Request Body
```json
{
  "customer_email": "customer@example.com",
  "limit": 50
}
```

#### Response (Success - 200)
```json
{
  "success": true,
  "data": [
    {
      "id": "uuid-string",
      "story_id": "uuid-string",
      "status": "delivered",
      "format": "hardcover",
      "total_amount": 49.99,
      "created_at": "2024-12-10T10:00:00Z"
    },
    {
      "id": "uuid-string",
      "story_id": "uuid-string",
      "status": "pending_payment",
      "format": "digital",
      "total_amount": 19.99,
      "created_at": "2024-12-16T10:00:00Z"
    }
  ]
}
```

#### Implementation Template
```typescript
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type, x-api-key",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

const MAX_LIMIT = 200;

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response(null, { headers: corsHeaders });
  }

  if (req.method !== "POST") {
    return new Response(
      JSON.stringify({ success: false, error: "Method not allowed" }),
      { status: 405, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  }

  try {
    const apiKey = req.headers.get("x-api-key");
    const expectedApiKey = Deno.env.get("PDF_API_KEY");

    if (!apiKey || apiKey !== expectedApiKey) {
      return new Response(
        JSON.stringify({ success: false, error: "Unauthorized" }),
        { status: 401, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    const { customer_email, limit = 50 } = await req.json();

    if (!customer_email) {
      return new Response(
        JSON.stringify({ success: false, error: "customer_email is required" }),
        { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    // Basic email validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(customer_email)) {
      return new Response(
        JSON.stringify({ success: false, error: "Invalid email format" }),
        { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    const effectiveLimit = Math.min(limit, MAX_LIMIT);

    const supabase = createClient(
      Deno.env.get("SUPABASE_URL")!,
      Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!
    );

    const { data, error } = await supabase
      .from("orders")
      .select("*")
      .eq("customer_email", customer_email.toLowerCase())
      .order("created_at", { ascending: false })
      .limit(effectiveLimit);

    if (error) {
      console.error("Error fetching orders:", error);
      return new Response(
        JSON.stringify({ success: false, error: "Failed to fetch orders" }),
        { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    return new Response(
      JSON.stringify({ success: true, data: data || [] }),
      { status: 200, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );

  } catch (error) {
    console.error("Unexpected error:", error);
    return new Response(
      JSON.stringify({ success: false, error: "Internal server error" }),
      { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  }
});
```

---

## 3. Standard Response Format

All backend Edge Functions follow this response format:

### Success Response
```json
{
  "success": true,
  "data": { /* resource data */ }
}
```

### Error Response
```json
{
  "success": false,
  "error": "Human-readable error message",
  "error_code": "OPTIONAL_ERROR_CODE",
  "details": "Optional additional details"
}
```

---

## 4. Error Codes

| Code | Description |
|------|-------------|
| `not_found` | Resource does not exist |
| `validation_error` | Request validation failed |
| `unauthorized` | Invalid or missing API key |
| `database_error` | Database operation failed |
| `internal_error` | Unexpected server error |

---

## 5. Database Schema Reference

### stories Table
```sql
CREATE TABLE stories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id),
    child_name VARCHAR(100) NOT NULL,
    child_age INT NOT NULL,
    theme VARCHAR(50) NOT NULL,
    art_style VARCHAR(50),
    character_json JSONB,
    gender VARCHAR(20),
    skin_tone VARCHAR(50),
    hair_color VARCHAR(50),
    hair_style VARCHAR(50),
    eye_color VARCHAR(50),
    occasion VARCHAR(100),
    special_details TEXT,
    photo_url TEXT,
    status VARCHAR(30) DEFAULT 'generating',
    cover_image_url TEXT,
    error_json JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### pages Table
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

### orders Table
```sql
CREATE TABLE orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    shopify_order_id VARCHAR(100) UNIQUE,
    shopify_order_number VARCHAR(50),
    story_id UUID NOT NULL REFERENCES stories(id),
    format VARCHAR(20) NOT NULL,
    book_size VARCHAR(20) DEFAULT '8x8',
    quantity INT DEFAULT 1,
    base_price DECIMAL(10,2) NOT NULL DEFAULT 0,
    shipping_cost DECIMAL(10,2) DEFAULT 0,
    gift_wrap_cost DECIMAL(10,2) DEFAULT 0,
    discount_amount DECIMAL(10,2) DEFAULT 0,
    tax_amount DECIMAL(10,2) DEFAULT 0,
    total_amount DECIMAL(10,2) NOT NULL DEFAULT 0,
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
    status VARCHAR(30) NOT NULL DEFAULT 'pending_payment',
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

---

## 6. Deployment Checklist

### Environment Variables Setup

In the Supabase Dashboard → Edge Functions → Secrets:

```bash
# Required for all functions
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJhbG...
SUPABASE_ANON_KEY=eyJhbG...

# Required for backend functions
PDF_API_KEY=your-secure-api-key

# Required for weave-story
RAILWAY_API_URL=https://taleom-production.up.railway.app
ALLOWED_ORIGINS=https://your-app.com,https://www.your-app.com
RATE_LIMIT_MAX=3
RATE_LIMIT_WINDOW_HOURS=24
```

### Deployment Commands

```bash
# Deploy all functions
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
supabase functions deploy get-story-for-pdf
supabase functions deploy weave-story
```

### Verification

After deployment, test each function:

```bash
# Test backend function
curl -X POST \
  'https://your-project.supabase.co/functions/v1/get-story' \
  -H 'Content-Type: application/json' \
  -H 'x-api-key: your-pdf-api-key' \
  -d '{"story_id": "test-uuid"}'
```

---

## 7. Summary

| Function | Status | Auth Type | Purpose |
|----------|--------|-----------|---------|
| weave-story | ✅ | JWT | Create story (user-facing) |
| get-story-for-pdf | ✅ | API Key | Fetch story for PDF |
| create-story | 🔲 | API Key | Create story record |
| get-story | 🔲 | API Key | Get story by ID |
| update-story | 🔲 | API Key | Update story |
| create-page | 🔲 | API Key | Create page |
| get-pages | 🔲 | API Key | Get story pages |
| update-page | 🔲 | API Key | Update page |
| create-order | 🔲 | API Key | Create order |
| get-order | 🔲 | API Key | Get order |
| update-order | 🔲 | API Key | Update order |
| get-orders-by-status | 🔲 | API Key | Query orders by status |
| get-orders-by-customer | 🔲 | API Key | Query customer orders |

**Legend:**
- ✅ IMPLEMENTED - Already deployed and working
- 🔲 TO BE IMPLEMENTED - Specification complete, needs deployment

---

*Last updated: December 16, 2024*

