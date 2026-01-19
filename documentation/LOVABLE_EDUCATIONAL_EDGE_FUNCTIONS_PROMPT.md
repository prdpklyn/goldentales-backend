# Lovable.dev Prompt: Supabase Edge Functions for Educational Storybooks

> Copy and paste this prompt into Lovable.dev to generate all required Supabase Edge Functions for the educational storybook feature.

---

## 🚀 THE PROMPT

```
Create Supabase Edge Functions for an educational storybook platform called "GoldenTales Learning". The backend needs Edge Functions that handle CRUD operations for educational topics, learning series, chapters, and learner profiles.

## Project Context

GoldenTales Learning creates AI-generated educational storybooks that teach any topic through illustrated narratives. Users select a topic, take a level assessment, and generate multi-chapter learning series with consistent characters.

## Authentication

All functions use API key authentication via the `x-api-key` header:
- Header: `x-api-key: <EDUCATION_API_KEY>`
- Validate against environment variable `EDUCATION_API_KEY`
- Return 401 if invalid/missing

## Environment Variables (all functions need these)

- `SUPABASE_URL` - Project URL
- `SUPABASE_SERVICE_ROLE_KEY` - Service role key for bypassing RLS
- `EDUCATION_API_KEY` - API key for authentication

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

### educational_topics table
```sql
CREATE TABLE educational_topics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    topic_name VARCHAR(200) NOT NULL,
    topic_slug VARCHAR(200) UNIQUE NOT NULL,
    category VARCHAR(50) NOT NULL,
    description TEXT,
    prerequisites JSONB DEFAULT '[]',
    difficulty_mapping JSONB DEFAULT '{}',
    suggested_chapters INT DEFAULT 5,
    key_concepts JSONB DEFAULT '[]',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### learner_profiles table
```sql
CREATE TABLE learner_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    learner_name VARCHAR(100) NOT NULL,
    age_band VARCHAR(20),
    topic_slug VARCHAR(200),
    self_reported_level VARCHAR(50),
    quiz_results JSONB DEFAULT '{}',
    calibrated_level VARCHAR(50),
    confidence_score DECIMAL(3,2),
    character_bible JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### learning_series table
```sql
CREATE TABLE learning_series (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(300) NOT NULL,
    topic_slug VARCHAR(200),
    topic_category VARCHAR(50) NOT NULL,
    learner_profile_id UUID REFERENCES learner_profiles(id),
    learner_name VARCHAR(100) NOT NULL,
    learner_level VARCHAR(50) NOT NULL,
    age_band VARCHAR(20) NOT NULL,
    target_chapters INT DEFAULT 5,
    current_chapter INT DEFAULT 0,
    concept_progression JSONB DEFAULT '[]',
    art_style VARCHAR(50) NOT NULL,
    series_character_bible JSONB DEFAULT '{}',
    include_quiz_between_chapters BOOLEAN DEFAULT false,
    completed_chapters JSONB DEFAULT '[]',
    quiz_scores JSONB DEFAULT '[]',
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);
```

### series_chapters table
```sql
CREATE TABLE series_chapters (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    series_id UUID NOT NULL REFERENCES learning_series(id) ON DELETE CASCADE,
    chapter_number INT NOT NULL,
    title VARCHAR(300) NOT NULL,
    concepts_covered JSONB DEFAULT '[]',
    story_pages JSONB NOT NULL,
    cover_url TEXT,
    page_images JSONB DEFAULT '[]',
    characters_used JSONB DEFAULT '{}',
    quiz_questions JSONB DEFAULT '[]',
    quiz_score DECIMAL(3,2),
    generation_time_ms INT,
    custom_focus TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    UNIQUE(series_id, chapter_number)
);
```

### concept_characters table
```sql
CREATE TABLE concept_characters (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    character_name VARCHAR(100) NOT NULL,
    character_slug VARCHAR(100) NOT NULL,
    character_type VARCHAR(50) NOT NULL,
    topic_slug VARCHAR(200),
    concept_name VARCHAR(200) NOT NULL,
    character_bible TEXT NOT NULL,
    visual_traits JSONB DEFAULT '{}',
    art_style_variants JSONB DEFAULT '{}',
    reference_images JSONB DEFAULT '[]',
    is_reusable BOOLEAN DEFAULT true,
    usage_count INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(character_slug, topic_slug)
);
```

## Edge Functions to Create

### 1. get-educational-topics
POST - Gets all active educational topics, optionally filtered by category

Request:
```json
{
  "category": "stem" // optional filter
}
```

Response (200):
```json
{
  "success": true,
  "data": [
    {
      "id": "uuid",
      "topic_name": "Reinforcement Learning",
      "topic_slug": "reinforcement_learning",
      "category": "stem",
      "description": "Learn RL through stories",
      "suggested_chapters": 5,
      "key_concepts": ["agents", "environments", "rewards"]
    }
  ]
}
```

Filter by `is_active = true`. Order by topic_name ASC.

### 2. create-learner-profile
POST - Creates a learner profile with assessment results

Request:
```json
{
  "learner_name": "Alex",
  "age_band": "adult",
  "topic_slug": "reinforcement_learning",
  "self_reported_level": "beginner",
  "quiz_results": {
    "score": 0.8,
    "answers": [{"question": 1, "correct": true}]
  },
  "calibrated_level": "intermediate",
  "confidence_score": 0.85,
  "character_bible": {}
}
```

Response (201):
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "learner_name": "Alex",
    "calibrated_level": "intermediate",
    "created_at": "2026-01-19T10:00:00Z"
  }
}
```

### 3. create-learning-series
POST - Creates a new learning series

Request:
```json
{
  "title": "Alex's Reinforcement Learning Journey",
  "topic_slug": "reinforcement_learning",
  "topic_category": "stem",
  "learner_profile_id": "uuid", // optional
  "learner_name": "Alex",
  "learner_level": "intermediate",
  "age_band": "adult",
  "target_chapters": 5,
  "concept_progression": [
    ["agents", "environments"],
    ["states", "observations"],
    ["actions", "policies"],
    ["rewards", "value functions"],
    ["learning", "exploration"]
  ],
  "art_style": "cartoon",
  "series_character_bible": {},
  "include_quiz_between_chapters": true
}
```

Response (201):
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "title": "Alex's Reinforcement Learning Journey",
    "status": "active",
    "current_chapter": 0,
    "created_at": "2026-01-19T10:00:00Z"
  }
}
```

Set status = 'active', current_chapter = 0.

### 4. get-learning-series
POST - Gets a learning series by ID

Request:
```json
{
  "series_id": "uuid"
}
```

Response (200):
```json
{
  "success": true,
  "data": { /* full series object */ }
}
```

If not found, return `{ "success": false, "error": "Series not found", "error_code": "not_found" }`.

### 5. update-learning-series
POST - Updates a learning series (progress, status)

Request:
```json
{
  "series_id": "uuid",
  "updates": {
    "current_chapter": 2,
    "completed_chapters": ["chapter-1-uuid", "chapter-2-uuid"],
    "status": "active"
  }
}
```

Don't allow updating: id, created_at
Always set updated_at to current timestamp.
If status changes to 'completed', set completed_at.

### 6. create-chapter
POST - Creates a chapter for a series

Request:
```json
{
  "series_id": "uuid",
  "chapter_number": 1,
  "title": "Chapter 1: Agents & Environments",
  "concepts_covered": ["agents", "environments"],
  "story_pages": [
    {
      "page_number": 1,
      "text": "Alex began their journey...",
      "scene_description": "...",
      "teaching_focus": "introduction",
      "mood": "curious"
    }
  ],
  "cover_url": "https://...",
  "page_images": ["url1", "url2"],
  "characters_used": {},
  "quiz_questions": [],
  "generation_time_ms": 120000
}
```

Verify series exists before creating. Update series.current_chapter.

Response (201):
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "series_id": "uuid",
    "chapter_number": 1,
    "title": "Chapter 1: Agents & Environments",
    "created_at": "2026-01-19T10:00:00Z"
  }
}
```

### 7. get-chapters-by-series
POST - Gets all chapters for a series

Request:
```json
{
  "series_id": "uuid"
}
```

Response:
```json
{
  "success": true,
  "data": [
    { "id": "uuid", "chapter_number": 1, "title": "...", "concepts_covered": [...] },
    { "id": "uuid", "chapter_number": 2, "title": "...", "concepts_covered": [...] }
  ]
}
```

Order by `chapter_number ASC`.

### 8. update-chapter
POST - Updates a chapter (quiz score, completion)

Request:
```json
{
  "chapter_id": "uuid",
  "updates": {
    "quiz_score": 0.85,
    "completed_at": "2026-01-19T12:00:00Z"
  }
}
```

Don't allow updating: id, series_id, chapter_number, created_at

### 9. get-concept-character
POST - Gets a concept character by slug and topic

Request:
```json
{
  "character_slug": "agent_alpha",
  "topic_slug": "reinforcement_learning"
}
```

Response:
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "character_name": "Agent Alpha",
    "character_type": "agent",
    "concept_name": "RL Agent",
    "character_bible": "A friendly blue robot..."
  }
}
```

### 10. create-concept-character
POST - Creates a reusable concept character

Request:
```json
{
  "character_name": "Agent Alpha",
  "character_slug": "agent_alpha",
  "character_type": "agent",
  "topic_slug": "reinforcement_learning",
  "concept_name": "RL Agent",
  "character_bible": "A friendly blue robot with silver accents...",
  "visual_traits": {
    "colors": ["blue", "silver"],
    "form": "robot"
  },
  "is_reusable": true
}
```

Response (201):
```json
{
  "success": true,
  "data": { /* character object */ }
}
```

Set usage_count = 0 initially.

### 11. increment-character-usage
POST - Increments usage count for a concept character

Request:
```json
{
  "character_id": "uuid"
}
```

Increment `usage_count` by 1, update `updated_at`.

### 12. get-learner-series
POST - Gets all series for a learner

Request:
```json
{
  "learner_name": "Alex",
  "limit": 10
}
```

Response:
```json
{
  "success": true,
  "data": [
    { "id": "uuid", "title": "...", "status": "active", "current_chapter": 2 },
    { "id": "uuid", "title": "...", "status": "completed", "current_chapter": 5 }
  ]
}
```

Filter by learner_name (case-insensitive). Order by created_at DESC. Max limit: 50.

## Technical Requirements

1. Use Deno runtime with Supabase client v2
2. All functions use POST method
3. Handle CORS with preflight OPTIONS requests
4. Use service role key to bypass RLS
5. Validate UUID format for IDs
6. Log errors to console with context
7. Return proper HTTP status codes (200, 201, 400, 401, 404, 500)
8. Use `.maybeSingle()` for single record fetches

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
    if (!apiKey || apiKey !== Deno.env.get("EDUCATION_API_KEY")) {
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

Please create all 12 Edge Functions following these specifications. Each function should be production-ready with proper error handling, validation, and logging.
```

---

## 📋 INDIVIDUAL FUNCTION PROMPTS

If Lovable has token limits, use these individual prompts:

### Prompt for get-educational-topics

```
Create a Supabase Edge Function called "get-educational-topics" for an educational platform.

Authentication: x-api-key header validated against EDUCATION_API_KEY env var

Request (POST):
{
  "category": "stem" // optional filter
}

Table: educational_topics with columns: id, topic_name, topic_slug, category, description, prerequisites (jsonb), suggested_chapters, key_concepts (jsonb), is_active, created_at

Query:
- Filter by is_active = true
- If category provided, filter by category
- Order by topic_name ASC

Response: { "success": true, "data": [ /* topics */ ] }

Use Deno runtime, @supabase/supabase-js@2, service role key. Handle CORS.
```

### Prompt for create-learning-series

```
Create a Supabase Edge Function called "create-learning-series" for an educational storybook platform.

Authentication: x-api-key header validated against EDUCATION_API_KEY env var

Request (POST):
{
  "title": "Alex's Learning Journey", // required
  "topic_slug": "reinforcement_learning", // required
  "topic_category": "stem", // required
  "learner_name": "Alex", // required
  "learner_level": "intermediate", // required
  "age_band": "adult", // required
  "target_chapters": 5,
  "concept_progression": [["concept1"], ["concept2"]], // optional
  "art_style": "cartoon", // required
  "include_quiz_between_chapters": false
}

Table: learning_series with columns: id, title, topic_slug, topic_category, learner_profile_id, learner_name, learner_level, age_band, target_chapters, current_chapter, concept_progression (jsonb), art_style, series_character_bible (jsonb), include_quiz_between_chapters, completed_chapters (jsonb), quiz_scores (jsonb), status, created_at, updated_at

Set defaults:
- status = 'active'
- current_chapter = 0
- completed_chapters = []
- quiz_scores = []

Return 201 on success. Use Deno runtime, @supabase/supabase-js@2, service role key. Handle CORS.
```

### Prompt for create-chapter

```
Create a Supabase Edge Function called "create-chapter" for educational storybook chapters.

Authentication: x-api-key header validated against EDUCATION_API_KEY env var

Request (POST):
{
  "series_id": "uuid", // required
  "chapter_number": 1, // required
  "title": "Chapter 1: Introduction", // required
  "concepts_covered": ["concept1", "concept2"],
  "story_pages": [ /* page objects */ ], // required
  "cover_url": "https://...",
  "page_images": ["url1", "url2"],
  "characters_used": {},
  "quiz_questions": [],
  "generation_time_ms": 120000
}

Tables:
- series_chapters: id, series_id, chapter_number, title, concepts_covered (jsonb), story_pages (jsonb), cover_url, page_images (jsonb), characters_used (jsonb), quiz_questions (jsonb), quiz_score, generation_time_ms, created_at
- learning_series: update current_chapter when creating

Rules:
1. Verify series exists first
2. Insert chapter
3. Update series.current_chapter = chapter_number
4. Update series.updated_at

Return 201 on success. Handle UNIQUE constraint on (series_id, chapter_number).

Use Deno runtime, @supabase/supabase-js@2, service role key. Handle CORS.
```

### Prompt for get-chapters-by-series

```
Create a Supabase Edge Function called "get-chapters-by-series" that retrieves all chapters for a learning series.

Authentication: x-api-key header validated against EDUCATION_API_KEY env var

Request (POST):
{ "series_id": "uuid" }

Table: series_chapters

Query: SELECT * FROM series_chapters WHERE series_id = ? ORDER BY chapter_number ASC

Response: { "success": true, "data": [ /* chapters array */ ] }

Return empty array if no chapters found (not an error).
Validate UUID format for series_id.

Use Deno runtime, @supabase/supabase-js@2, service role key. Handle CORS.
```

### Prompt for get-concept-character

```
Create a Supabase Edge Function called "get-concept-character" that retrieves a reusable concept character.

Authentication: x-api-key header validated against EDUCATION_API_KEY env var

Request (POST):
{
  "character_slug": "agent_alpha",
  "topic_slug": "reinforcement_learning"
}

Table: concept_characters with UNIQUE(character_slug, topic_slug)

Query by both character_slug AND topic_slug.

If found: { "success": true, "data": { /* character */ } }
If not found: { "success": false, "error": "Character not found", "error_code": "not_found" }

Use Deno runtime, @supabase/supabase-js@2, service role key. Handle CORS.
```

---

## 🔧 Post-Generation Setup

After Lovable generates the functions:

1. **Set Environment Variables** in Supabase Dashboard → Edge Functions → Secrets:
   ```
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_SERVICE_ROLE_KEY=eyJhbG...
   EDUCATION_API_KEY=your-secure-random-key
   ```

2. **Deploy Functions**:
   ```bash
   supabase functions deploy get-educational-topics
   supabase functions deploy create-learner-profile
   supabase functions deploy create-learning-series
   supabase functions deploy get-learning-series
   supabase functions deploy update-learning-series
   supabase functions deploy create-chapter
   supabase functions deploy get-chapters-by-series
   supabase functions deploy update-chapter
   supabase functions deploy get-concept-character
   supabase functions deploy create-concept-character
   supabase functions deploy increment-character-usage
   supabase functions deploy get-learner-series
   ```

3. **Run Database Migration First**:
   Before deploying functions, run `migrations/003_educational_tables.sql` in Supabase SQL Editor.

4. **Test Each Function**:
   ```bash
   # Test get topics
   curl -X POST \
     'https://your-project.supabase.co/functions/v1/get-educational-topics' \
     -H 'Content-Type: application/json' \
     -H 'x-api-key: your-education-api-key' \
     -d '{"category": "stem"}'

   # Test create series
   curl -X POST \
     'https://your-project.supabase.co/functions/v1/create-learning-series' \
     -H 'Content-Type: application/json' \
     -H 'x-api-key: your-education-api-key' \
     -d '{
       "title": "Test Learning Series",
       "topic_slug": "test_topic",
       "topic_category": "stem",
       "learner_name": "Test User",
       "learner_level": "beginner",
       "age_band": "adult",
       "art_style": "cartoon",
       "target_chapters": 3
     }'
   ```

---

## 📊 Function Summary

| Function | Method | Purpose |
|----------|--------|---------|
| get-educational-topics | POST | List topics by category |
| create-learner-profile | POST | Store assessment results |
| create-learning-series | POST | Create new series |
| get-learning-series | POST | Get series details |
| update-learning-series | POST | Update progress/status |
| create-chapter | POST | Add chapter to series |
| get-chapters-by-series | POST | List all chapters |
| update-chapter | POST | Update quiz score |
| get-concept-character | POST | Get reusable character |
| create-concept-character | POST | Create new character |
| increment-character-usage | POST | Track character usage |
| get-learner-series | POST | List user's series |

---

## 🔗 Integration with FastAPI Backend

The FastAPI backend (`/api/v2/education/*`) can call these edge functions, or you can call them directly from the frontend:

**From Frontend (Direct):**
```typescript
const { data } = await supabase.functions.invoke('create-learning-series', {
  body: { title, topic_slug, learner_name, ... }
});
```

**From FastAPI (via HTTP):**
```python
response = await httpx.post(
    f"{SUPABASE_URL}/functions/v1/create-learning-series",
    headers={"x-api-key": EDUCATION_API_KEY},
    json={...}
)
```

Choose based on your architecture preferences.
