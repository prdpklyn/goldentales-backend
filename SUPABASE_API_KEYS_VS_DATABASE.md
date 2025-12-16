# Supabase API Keys vs Database Connection

**Understanding the difference and why you need both**

---

## 🎯 The Key Distinction

You're using **Supabase API Keys** (publishable/secret keys) for your application, which is correct! However, Alembic needs a **direct PostgreSQL connection string**, which is different.

---

## 📋 Two Separate Connection Methods

### 1. Supabase Client SDK (Your Application Code)

**What you have:**
```bash
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_PUBLISHABLE_KEY=sb_publishable_xxxxxxxxxxxxx
```

**Used by:**
- `app/services/database.py` - Your Supabase client
- REST API calls via Supabase Python SDK
- Row Level Security (RLS) policies
- Authentication flows
- Storage operations

**How it works:**
```python
from supabase import create_client

client = create_client(
    settings.supabase_url,      # REST API URL
    settings.supabase_key       # Publishable/Secret key
)
```

**Reference**: [Supabase API Keys Documentation](https://supabase.com/docs/guides/api/api-keys)

---

### 2. Direct PostgreSQL Connection (Alembic Migrations)

**What you need to add:**
```bash
DATABASE_URL=postgresql://postgres:password@db.xxxxx.supabase.co:5432/postgres
```

**Used by:**
- Alembic migrations
- Direct database queries
- Database administration tools
- Schema changes

**How it works:**
```python
# Alembic uses this directly with SQLAlchemy
engine = create_engine("postgresql://postgres:pass@host:5432/db")
```

---

## 🔍 Why Two Different Methods?

| Aspect | Supabase Client SDK | Direct PostgreSQL |
|--------|---------------------|-------------------|
| **Protocol** | HTTPS REST API | PostgreSQL protocol |
| **Authentication** | API Keys (publishable/secret) | Database username/password |
| **RLS Policies** | ✅ Enforced | ❌ Bypassed (direct access) |
| **Use Case** | Application queries | Schema migrations |
| **Security** | Row-level security | Full database access |

---

## ✅ Solution: Add DATABASE_URL

You need **both** in your `.env` file:

```bash
# For your application code (Supabase client SDK)
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_PUBLISHABLE_KEY=sb_publishable_xxxxxxxxxxxxx

# For Alembic migrations (direct PostgreSQL)
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@db.xxxxx.supabase.co:5432/postgres
```

---

## 🔧 How to Get Your PostgreSQL Connection String

1. **Go to Supabase Dashboard**
   - https://app.supabase.com
   - Select your project

2. **Navigate to Database Settings**
   - Click "Settings" (gear icon)
   - Go to "Database" section

3. **Copy Connection String**
   - Find "Connection string" section
   - Select "URI" tab
   - Copy the connection string

4. **Replace Password Placeholder**
   - The string will have `[YOUR-PASSWORD]`
   - Replace with your actual database password
   - This is your **database password**, not your API key!

5. **Add to `.env`**
   ```bash
   DATABASE_URL=postgresql://postgres:actual_password@db.xxxxx.supabase.co:5432/postgres
   ```

---

## 📊 Updated Settings

The `app/settings.py` now supports both:

```python
class Settings(BaseSettings):
    # Supabase REST API (for client SDK)
    supabase_url: Optional[str] = Field(default=None, alias="SUPABASE_URL")
    supabase_key: Optional[str] = Field(default=None, alias="SUPABASE_PUBLISHABLE_KEY")
    
    # PostgreSQL Database (for Alembic)
    supabase_db_url: Optional[str] = Field(default=None, alias="SUPABASE_DATABASE_URL")
    database_url: Optional[str] = Field(default=None, alias="DATABASE_URL")
    
    @property
    def db_connection_string(self) -> Optional[str]:
        """Get PostgreSQL connection string for database operations."""
        return self.database_url or self.supabase_db_url
```

---

## 🚀 Quick Fix Steps

1. **Get PostgreSQL connection string** from Supabase dashboard
2. **Add to `.env`**:
   ```bash
   DATABASE_URL=postgresql://postgres:password@db.xxxxx.supabase.co:5432/postgres
   ```
3. **Test connection**:
   ```bash
   python scripts/test_db_connection.py
   ```
4. **Run Alembic**:
   ```bash
   alembic current
   python scripts/db_migrate.py upgrade
   ```

---

## 💡 Why This Architecture?

### Supabase Client SDK (REST API)
- ✅ Respects Row Level Security
- ✅ Uses API keys (publishable/secret)
- ✅ Works through Supabase API Gateway
- ✅ Better for application code
- ✅ Automatic connection pooling

### Direct PostgreSQL (Alembic)
- ✅ Direct database access
- ✅ Required for schema migrations
- ✅ Bypasses RLS (needed for migrations)
- ✅ Uses standard PostgreSQL protocol
- ✅ Works with any PostgreSQL tool

---

## 🔐 Security Notes

### API Keys (Publishable)
- ✅ Safe to expose in client-side code
- ✅ Respects RLS policies
- ✅ Limited privileges

### API Keys (Secret)
- ⚠️ **Never expose publicly**
- ⚠️ Bypasses RLS
- ⚠️ Full database access
- ✅ Use only in backend/server code

### Database Password
- ⚠️ **Never expose publicly**
- ⚠️ Full database access
- ✅ Required for migrations
- ✅ Store securely in `.env`

---

## 📚 References

- **Supabase API Keys**: https://supabase.com/docs/guides/api/api-keys
- **Database Connection**: https://supabase.com/docs/guides/database/connecting-to-postgres
- **Internal Guide**: `documentation/DATABASE_SETUP.md`

---

## ✅ Summary

**You're doing it right** with Supabase API keys for your application! 

Just add `DATABASE_URL` for Alembic migrations, and you'll have both:
- ✅ Application code → Uses Supabase client SDK (API keys)
- ✅ Migrations → Uses direct PostgreSQL connection (DATABASE_URL)

Both are needed because they serve different purposes! 🎉

