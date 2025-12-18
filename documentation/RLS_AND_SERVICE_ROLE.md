# RLS (Row Level Security) and Service Role Key

**Understanding RLS policies and when to use service_role key**

---

## 🔍 The Problem

Your `stories` table has RLS policies that restrict access:

| Policy | Command | Applies To | Rule |
|--------|---------|------------|------|
| `stories_select_owner` | SELECT | `authenticated` | `user_id = auth.uid()` |
| `stories_insert_owner` | INSERT | `authenticated` | `user_id = auth.uid()` |
| `stories_update_owner` | UPDATE | `authenticated` | `user_id = auth.uid()` |
| `stories_delete_owner` | DELETE | `authenticated` | `user_id = auth.uid()` |

**What this means:**
- Only `authenticated` users can access stories
- Users can only see stories where `user_id = auth.uid()`
- The `publishable` key uses the `anon` role (not authenticated)
- **Result**: Backend services using publishable key can't read stories!

---

## ✅ Solution: Service Role Key

For backend operations (print jobs, admin tasks, migrations), use the **service_role key** which:
- ✅ Bypasses all RLS policies
- ✅ Has full database access
- ✅ Perfect for server-side operations
- ⚠️ **NEVER expose in client-side code!**

---

## 🔧 Configuration

### Step 1: Get Your Service Role Key

1. Go to Supabase Dashboard
2. Project Settings → API
3. Find "service_role" key (under "Project API keys")
4. Copy the key (starts with `eyJ...` or `sb_secret_...`)

### Step 2: Add to `.env`

```bash
# Existing (for client SDK)
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_PUBLISHABLE_KEY=sb_publishable_xxxxxxxxxxxxx

# NEW: Service role key for backend operations
SUPABASE_SERVICE_ROLE_KEY=sb_secret_xxxxxxxxxxxxx
# OR (if using JWT-based key):
# SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Step 3: Code Already Updated!

The `DatabaseService` now automatically:
- Uses `service_role` key if available
- Falls back to `publishable` key if not set
- Logs which key type is being used

---

## 📊 When to Use Which Key

| Use Case | Key Type | Why |
|----------|----------|-----|
| **Client-side app** | `publishable` | Respects RLS, safe to expose |
| **User authentication** | `publishable` | Works with Supabase Auth |
| **Print jobs** | `service_role` | Needs to read all stories |
| **Admin operations** | `service_role` | Needs full access |
| **Migrations** | `service_role` | Needs to modify schema |
| **Background jobs** | `service_role` | Needs to access all data |

---

## 🔐 Security Best Practices

### DO ✅
- Use `service_role` key **only** in backend/server code
- Store in environment variables (`.env`)
- Never commit to git (already in `.gitignore`)
- Use different keys for different environments
- Rotate keys regularly

### DON'T ❌
- Never use `service_role` in client-side code
- Never expose in browser, mobile apps, or public APIs
- Never log the full key (log first 6 chars only)
- Never share in chat/email
- Never use in URLs or query parameters

---

## 🧪 Testing

After adding `SUPABASE_SERVICE_ROLE_KEY`:

```bash
# Test print job
python test_print_job.py --story-id "5eb41ff4-6d98-47d0-a6ed-af5a81222a42" --creative
```

You should see:
```
Supabase client initialized with service_role key
✓ Found story: ...
```

---

## 🔄 Alternative: Create Service Account User

If you prefer not to use service_role key, you can:

1. **Create a service account user** in Supabase Auth
2. **Authenticate as that user** before queries
3. **Update RLS policies** to allow that user

But this is more complex and service_role is the recommended approach for backend operations.

---

## 📚 References

- [Supabase RLS Documentation](https://supabase.com/docs/guides/database/postgres/row-level-security)
- [Supabase API Keys](https://supabase.com/docs/guides/api/api-keys)
- [Service Role Key Best Practices](https://supabase.com/docs/guides/api/api-keys#service_role-and-secret-keys)

---

## ✅ Summary

**Problem**: RLS policies block `publishable` key from reading stories  
**Solution**: Use `service_role` key for backend operations  
**Status**: Code updated to automatically use service_role if available

Just add `SUPABASE_SERVICE_ROLE_KEY` to your `.env` file and you're good to go! 🚀


