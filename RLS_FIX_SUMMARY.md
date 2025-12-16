# RLS Issue - Fixed! ✅

## 🔍 Problem Identified

Your `stories` table has RLS policies that:
- Only allow `authenticated` users
- Require `user_id = auth.uid()` match
- Block `publishable` key (uses `anon` role)

**Result**: Backend print jobs can't read stories!

---

## ✅ Solution Implemented

### 1. Added Service Role Key Support

**Updated Files:**
- `app/settings.py` - Added `supabase_service_role_key` field
- `app/services/database.py` - Auto-uses service_role key if available
- `app/services/storage_service.py` - Also uses service_role key

### 2. How It Works

The code now:
1. **Checks for `SUPABASE_SERVICE_ROLE_KEY` first** (bypasses RLS)
2. **Falls back to `SUPABASE_PUBLISHABLE_KEY`** if not set
3. **Logs which key type is being used**

---

## 🚀 Quick Setup

### Step 1: Get Service Role Key

1. Go to **Supabase Dashboard**
2. **Project Settings** → **API**
3. Find **"service_role"** key (under "Project API keys")
4. Copy the key

### Step 2: Add to `.env`

```bash
# Existing (keep these)
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_PUBLISHABLE_KEY=sb_publishable_xxxxxxxxxxxxx

# NEW: Add this for backend operations
SUPABASE_SERVICE_ROLE_KEY=sb_secret_xxxxxxxxxxxxx
```

### Step 3: Test

```bash
python test_print_job.py --story-id "5eb41ff4-6d98-47d0-a6ed-af5a81222a42" --creative
```

You should see:
```
Supabase client initialized with service_role key
✓ Found story: ...
```

---

## 🔐 Security Notes

**Service Role Key:**
- ✅ Bypasses all RLS policies
- ✅ Full database access
- ⚠️ **NEVER expose in client-side code!**
- ⚠️ **Only use in backend/server code**

**Publishable Key:**
- ✅ Safe for client-side
- ✅ Respects RLS policies
- ✅ Works with Supabase Auth

---

## 📊 What Changed

| Component | Before | After |
|-----------|--------|-------|
| **Database Service** | Uses publishable key only | Uses service_role if available |
| **Storage Service** | Uses publishable key only | Uses service_role if available |
| **RLS Access** | Blocked by policies | Bypassed with service_role |

---

## ✅ Status

**Code Updated**: ✅  
**Documentation Created**: ✅  
**Ready to Use**: ✅ (just add the key!)

---

**Next Step**: Add `SUPABASE_SERVICE_ROLE_KEY` to your `.env` file and test! 🚀

