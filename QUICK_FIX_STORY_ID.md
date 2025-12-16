# Quick Fix: Story ID Issue

## 🔍 Problem Identified

Looking at your table screenshot, the story ID appears to be:
```
5eb41fff4-6d98-47d0-a6ed-af5a81222a42
```

But your command used:
```
5eb41ff4-6d98-47d0-a6ed-af5a81222a42
```

**Notice the difference**: The first segment has an extra 'f' in the image!

## ✅ Quick Fix

Try running the command with the correct ID:

```bash
python test_print_job.py --story-id "5eb41fff4-6d98-47d0-a6ed-af5a81222a42" --creative
```

## 🔍 Other Possible Issues

If the ID is correct but still not found, check:

### 1. Row Level Security (RLS)
The `SUPABASE_PUBLISHABLE_KEY` might not have permission to read the `stories` table.

**Solution**: Check RLS policies in Supabase:
1. Go to Supabase Dashboard → Table Editor → `stories` table
2. Check "RLS" tab
3. Ensure there's a policy allowing SELECT for `anon` or `authenticated` role

Or temporarily use `service_role` key for testing (backend only!)

### 2. Table/Column Name Mismatch
The code queries `stories` table with `id` column. Verify:
- Table name is exactly `stories` (not `story`)
- Column name is exactly `id` (not `story_id` or `uuid`)

### 3. Database Project Mismatch
Ensure you're querying the correct Supabase project.

## 🛠️ Diagnostic Script

Run this to debug:

```bash
python scripts/debug_story_query.py "5eb41fff4-6d98-47d0-a6ed-af5a81222a42"
```

This will:
- Test table access
- List all available story IDs
- Try alternative queries
- Show detailed error messages

## 📋 Steps to Verify

1. **Copy the exact ID from Supabase dashboard**
   - Go to Table Editor → `stories` table
   - Copy the ID directly (don't type it)

2. **Check RLS policies**
   - Settings → Database → Row Level Security
   - Ensure `stories` table has SELECT policy

3. **Test with service_role key** (temporarily)
   - Use `SUPABASE_SERVICE_ROLE_KEY` instead of publishable key
   - This bypasses RLS for testing

4. **Run diagnostic script**
   ```bash
   python scripts/debug_story_query.py "<exact-story-id>"
   ```

