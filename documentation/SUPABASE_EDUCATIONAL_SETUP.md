# Educational Features Setup for Supabase/Lovable

## Overview

This guide explains how to set up the educational storybook features in your Lovable-managed Supabase environment.

## Architecture

```
Frontend (Lovable) 
    ↓
Supabase Edge Functions 
    ↓
FastAPI Backend (this app)
    ↓
Supabase Database
```

## Step 1: Run Database Migration in Supabase

### Option A: Using Supabase Dashboard (Recommended)

1. Go to your Supabase project dashboard
2. Navigate to **SQL Editor**
3. Click **New Query**
4. Copy the entire contents of `migrations/003_educational_tables.sql`
5. Paste and click **Run**
6. Verify success message appears

### Option B: Using Supabase CLI

```bash
# If you have supabase CLI installed
supabase db push --file migrations/003_educational_tables.sql
```

## Step 2: Verify Tables Created

In Supabase Dashboard → **Database** → **Tables**, you should see:

- ✅ `educational_topics`
- ✅ `learner_profiles`
- ✅ `learning_series`
- ✅ `series_chapters`
- ✅ `concept_characters`
- ✅ `series_character_bibles`

## Step 3: Configure Row Level Security (RLS)

The migration already sets up RLS policies, but verify:

### For Public Access (Frontend)
- Topics are readable by everyone (for browsing)
- Concept characters are readable if marked reusable

### For Backend Service
- Backend uses **service role key** for full access
- No RLS restrictions on service role operations

## Step 4: Update Environment Variables

Ensure your FastAPI backend has:

```bash
# .env
SUPABASE_URL=your_supabase_project_url
SUPABASE_SERVICE_KEY=your_service_role_key  # Not anon key!
GEMINI_API_KEY=your_gemini_key
FAL_KEY=your_fal_key  # For image generation
```

## Step 5: Backend Service Configuration

The existing services already work with Supabase. They use:

```python
from app.services.database import DatabaseService

# In your services
self.db = DatabaseService()  # Uses Supabase client
```

No changes needed - the services I created follow this pattern.

## Step 6: Create Supabase Edge Functions (Optional)

If you want to call educational endpoints through edge functions:

### Example Edge Function: `generate-educational-series`

```typescript
// supabase/functions/generate-educational-series/index.ts
import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

serve(async (req) => {
  try {
    const { topic, learner_name, learner_level } = await req.json()
    
    // Call your FastAPI backend
    const response = await fetch('YOUR_BACKEND_URL/api/v2/education/series', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': Deno.env.get('BACKEND_API_KEY')
      },
      body: JSON.stringify({
        topic,
        topic_slug: topic.toLowerCase().replace(/\s+/g, '_'),
        topic_category: 'stem',
        learner_name,
        learner_level,
        age_band: 'adult',
        art_style: 'cartoon',
        target_chapters: 5
      })
    })
    
    const data = await response.json()
    
    return new Response(JSON.stringify(data), {
      headers: { 'Content-Type': 'application/json' },
    })
  } catch (error) {
    return new Response(JSON.stringify({ error: error.message }), {
      status: 400,
      headers: { 'Content-Type': 'application/json' },
    })
  }
})
```

Deploy:
```bash
supabase functions deploy generate-educational-series
```

## Step 7: Frontend Integration (Lovable)

### Call Backend API Directly

```typescript
// In your Lovable frontend
const createLearningSeries = async (data) => {
  const response = await fetch('YOUR_BACKEND_URL/api/v2/education/series', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': 'your_api_key'
    },
    body: JSON.stringify(data)
  })
  
  return response.json()
}
```

### Or Call Through Edge Function

```typescript
// Call your edge function
const createLearningSeries = async (data) => {
  const { data: result, error } = await supabase.functions.invoke(
    'generate-educational-series',
    { body: data }
  )
  
  if (error) throw error
  return result
}
```

## Step 8: Test the Setup

### 1. Test Database Access

```sql
-- In Supabase SQL Editor
SELECT * FROM educational_topics;
-- Should return 3 seed topics
```

### 2. Test Backend API

```bash
# List topics
curl -H "X-API-Key: your_key" \
  https://your-backend.com/api/v2/education/topics

# Generate quiz
curl -H "X-API-Key: your_key" \
  "https://your-backend.com/api/v2/education/quiz/reinforcement_learning?topic_category=stem&num_questions=5"
```

### 3. Test Series Creation

```bash
curl -X POST https://your-backend.com/api/v2/education/series \
  -H "X-API-Key: your_key" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "Reinforcement Learning",
    "topic_slug": "reinforcement_learning",
    "topic_category": "stem",
    "learner_name": "Alex",
    "learner_level": "beginner",
    "age_band": "adult",
    "art_style": "cartoon",
    "target_chapters": 5
  }'
```

## Security Considerations

### Service Role Key
- **NEVER** expose service role key to frontend
- Only use in backend services
- Store in secure environment variables

### API Keys
- Backend API keys authenticate client requests
- Implement rate limiting
- Consider API key tiers (free/premium)

### RLS Policies
The migration includes RLS policies that:
- Allow public read of topics and reusable concept characters
- Restrict write operations to service role
- Protect learner profiles and series data

## Monitoring

### Check Database Usage

```sql
-- In Supabase SQL Editor
-- Check series count
SELECT COUNT(*) FROM learning_series;

-- Check chapter count
SELECT COUNT(*) FROM series_chapters;

-- Most popular topics
SELECT topic_slug, COUNT(*) as series_count
FROM learning_series
GROUP BY topic_slug
ORDER BY series_count DESC;
```

### Check API Logs

In Supabase Dashboard:
1. Go to **Edge Functions** → **Logs**
2. Monitor invocations and errors
3. Check response times

## Troubleshooting

### Issue: Tables not created
- **Solution**: Run migration again, check for errors in SQL Editor

### Issue: RLS blocking access
- **Solution**: Verify backend uses service role key, not anon key

### Issue: Can't connect to backend
- **Solution**: Check CORS settings, verify API key, check environment variables

### Issue: Series creation fails
- **Solution**: Check Gemini API key is configured, verify topic_slug is valid

## Performance Optimization

### Database Indexes
Already created by migration:
- Topic slug lookup
- Series by learner
- Chapters by series
- Concept characters by topic

### Caching
Consider caching:
- Educational topics list (rarely changes)
- Concept characters (reusable across series)
- Quiz questions (can be reused)

### Background Jobs
For long-running operations (chapter generation):
- Consider using Supabase Edge Functions with longer timeout
- Or implement job queue (pg_cron, external queue)

## Cost Considerations

### Supabase
- **Database**: ~20-50 KB per series, ~100-200 KB per chapter
- **Storage**: Image URLs stored, actual images in Fal.ai
- **Edge Functions**: Charged per invocation

### External Services
- **Gemini API**: ~$0.01-0.05 per educational story/quiz
- **Fal.ai**: ~$0.02-0.10 per image (if generating illustrations)

## Next Steps

1. ✅ Run migration in Supabase
2. ✅ Verify tables and RLS policies
3. ✅ Test backend API endpoints
4. 🔄 Create edge functions (optional)
5. 🔄 Integrate with Lovable frontend
6. 🔄 Add monitoring and analytics
7. 🔄 Implement caching strategy

## Support

For issues or questions:
- Check Supabase logs for database errors
- Review FastAPI logs for backend issues
- Test each component individually
- Verify environment variables are correct

## Example: Complete Flow

```typescript
// Frontend (Lovable) example flow
async function createEducationalBook() {
  // 1. Assess learner level
  const assessment = await fetch(BACKEND_URL + '/api/v2/education/assess', {
    method: 'POST',
    headers: { 'X-API-Key': API_KEY, 'Content-Type': 'application/json' },
    body: JSON.stringify({
      topic: 'reinforcement_learning',
      topic_category: 'stem',
      self_reported_level: 'beginner'
    })
  }).then(r => r.json())
  
  // 2. Create series
  const series = await fetch(BACKEND_URL + '/api/v2/education/series', {
    method: 'POST',
    headers: { 'X-API-Key': API_KEY, 'Content-Type': 'application/json' },
    body: JSON.stringify({
      topic: 'Reinforcement Learning',
      topic_slug: 'reinforcement_learning',
      topic_category: 'stem',
      learner_name: 'Alex',
      learner_level: assessment.calibrated_level,
      age_band: 'adult',
      art_style: 'cartoon',
      target_chapters: 5
    })
  }).then(r => r.json())
  
  // 3. Generate first chapter
  const chapter = await fetch(
    BACKEND_URL + `/api/v2/education/series/${series.series_id}/chapters`,
    {
      method: 'POST',
      headers: { 'X-API-Key': API_KEY, 'Content-Type': 'application/json' },
      body: JSON.stringify({ custom_focus: null })
    }
  ).then(r => r.json())
  
  console.log('Chapter created:', chapter)
}
```

---

**Ready to go!** Run the migration and start creating educational storybooks. 🚀
