# Database Setup Guide

Complete guide for setting up database connections for GoldenTales.

---

## 🔍 Issue Analysis: Alembic Connection Error

### Error Message
```
sqlalchemy.exc.NoSuchModuleError: Can't load plugin: sqlalchemy.dialects:https
```

### Root Cause
**The `SUPABASE_URL` environment variable contains the REST API URL (https://...), NOT the PostgreSQL database connection string.**

SQLAlchemy (used by Alembic) needs a PostgreSQL connection string, not an HTTPS REST API URL.

---

## 📋 Two Types of Supabase URLs

### 1. REST API URL + API Key (for Supabase Client SDK)
```bash
# REST API URL:
SUPABASE_URL=https://xxxxxxxxxxxxx.supabase.co

# API Key (Publishable or Secret):
SUPABASE_PUBLISHABLE_KEY=sb_publishable_xxxxxxxxxxxxx

# Used by:
- Supabase Python/JavaScript client SDK
- REST API calls via client library
- Authentication
- Storage operations
- Row Level Security (RLS) policies
```

**Reference**: [Supabase API Keys Documentation](https://supabase.com/docs/guides/api/api-keys)

### 2. PostgreSQL Connection String (for Direct DB Access)
```bash
# Format:
DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.xxxxxxxxxxxxx.supabase.co:5432/postgres

# Used by:
- Alembic migrations
- psycopg2/asyncpg
- Direct database queries
- Database tools (psql, pgAdmin, etc.)
- Bypasses RLS (requires service_role or direct connection)
```

**Important**: These are **two separate things**:
- **REST API** = For application code using Supabase client SDK
- **PostgreSQL** = For migrations and direct database access

---

## ✅ Solution: Configure Database Connection

You have **3 options** to fix this:

### Option 1: Add DATABASE_URL (Recommended)

Add a dedicated database connection string alongside your existing Supabase API keys:

```bash
# In .env file - Keep your existing Supabase API keys
SUPABASE_URL=https://xxxxxxxxxxxxx.supabase.co
SUPABASE_PUBLISHABLE_KEY=sb_publishable_xxxxxxxxxxxxx

# Add this NEW line for Alembic/direct database access
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@db.xxxxxxxxxxxxx.supabase.co:5432/postgres
```

**Why both?**
- `SUPABASE_URL` + `SUPABASE_PUBLISHABLE_KEY` = For your application code (Supabase client SDK)
- `DATABASE_URL` = For Alembic migrations and direct database queries

The `alembic/env.py` is already configured to use `DATABASE_URL` or `SUPABASE_DATABASE_URL`.

### Option 2: Use SUPABASE_DATABASE_URL (Alternative Name)

If you prefer a Supabase-specific name:

```bash
# In .env file
SUPABASE_URL=https://xxxxxxxxxxxxx.supabase.co
SUPABASE_PUBLISHABLE_KEY=sb_publishable_xxxxxxxxxxxxx
SUPABASE_DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@db.xxxxxxxxxxxxx.supabase.co:5432/postgres
```

Both `DATABASE_URL` and `SUPABASE_DATABASE_URL` work - use whichever you prefer.

### ✅ Settings Already Updated!

The `app/settings.py` has been updated to support both:

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

And `alembic/env.py` uses `settings.db_connection_string` automatically.

---

## 🔧 How to Find Your PostgreSQL Connection String

### Step 1: Go to Supabase Dashboard
1. Open your project at https://app.supabase.com
2. Click on "Project Settings" (gear icon)
3. Navigate to "Database" section

### Step 2: Find Connection Info
Look for "Connection string" section with tabs:
- **JDBC**
- **URI** ← Select this one
- **Session pooler**
- **Transaction pooler**

### Step 3: Copy the URI
You'll see something like:
```
postgresql://postgres.[project-ref]:[YOUR-PASSWORD]@aws-0-us-east-1.pooler.supabase.com:5432/postgres
```

Or for direct connection:
```
postgresql://postgres:[YOUR-PASSWORD]@db.[project-ref].supabase.co:5432/postgres
```

### Step 4: Replace [YOUR-PASSWORD]
Replace `[YOUR-PASSWORD]` with your actual database password.

**⚠️ Important**: This is your **database password**, not your project API key!

---

## 🚀 Quick Fix Commands

### Check Current Configuration
```bash
# Check what SUPABASE_URL is set to
cd /Users/thepradeeps/Taleom
grep SUPABASE_URL .env

# Test Alembic connection
alembic current
```

### Apply Fix (Option 1 - Recommended)

```bash
# 1. Add DATABASE_URL to .env
echo "DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@db.xxxxx.supabase.co:5432/postgres" >> .env

# 2. Test connection
alembic current

# 3. Run migrations
python scripts/db_migrate.py upgrade
```

---

## 🔐 Security Best Practices

### DO ✅
1. **Store database credentials in `.env` file** (never commit to git)
2. **Use environment variables** for all sensitive data
3. **Use different passwords** for development and production
4. **Rotate passwords regularly**
5. **Use connection pooling** for production (Supabase Pooler)

### DON'T ❌
1. **Don't commit `.env` file to git** (already in `.gitignore`)
2. **Don't share database credentials** in code or documentation
3. **Don't use REST API URL for database connections**
4. **Don't hardcode passwords** in code

---

## 📊 Connection String Format Reference

### PostgreSQL Connection String Parts

```
postgresql://user:password@host:port/database?options
           └──┬──┘ └──┬───┘  └─┬─┘ └┬┘ └───┬──┘ └───┬──┘
              │       │        │    │      │         │
           Username  Pass    Host  Port  DBName   Options
```

### Supabase-Specific Examples

**Direct Connection** (for migrations):
```
postgresql://postgres:your_password@db.abc123xyz.supabase.co:5432/postgres
```

**Session Pooler** (for many short connections):
```
postgresql://postgres.abc123xyz:your_password@aws-0-us-east-1.pooler.supabase.com:5432/postgres
```

**Transaction Pooler** (for long-running connections):
```
postgresql://postgres.abc123xyz:your_password@aws-0-us-east-1.pooler.supabase.com:6543/postgres
```

### When to Use Each

| Connection Type | Use Case | Port | pgBouncer Mode |
|----------------|----------|------|----------------|
| **Direct** | Migrations, Admin | 5432 | N/A |
| **Session Pooler** | App queries | 5432 | Session |
| **Transaction Pooler** | Long transactions | 6543 | Transaction |

**For Alembic migrations**: Use **Direct Connection** (port 5432)

---

## 🧪 Testing Database Connection

### Test 1: Python Script
```python
# test_db_connection.py
import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

try:
    conn = psycopg2.connect(DATABASE_URL)
    print("✅ Database connection successful!")
    print(f"PostgreSQL version: {conn.server_version}")
    conn.close()
except Exception as e:
    print(f"❌ Connection failed: {e}")
```

Run:
```bash
python test_db_connection.py
```

### Test 2: psql Command
```bash
# Install psql if needed
brew install postgresql

# Test connection
psql "postgresql://postgres:PASSWORD@db.xxxxx.supabase.co:5432/postgres" -c "SELECT version();"
```

### Test 3: Alembic
```bash
# Should show current revision or "Base"
alembic current

# Should list available migrations
alembic history
```

---

## 🐛 Troubleshooting

### Error: "Can't load plugin: sqlalchemy.dialects:https"
**Cause**: Using REST API URL instead of PostgreSQL connection string  
**Fix**: Use Option 1 above - add DATABASE_URL with PostgreSQL format

### Error: "password authentication failed"
**Cause**: Wrong database password  
**Fix**: 
1. Go to Supabase Dashboard → Settings → Database
2. Reset database password
3. Update in `.env` file

### Error: "could not connect to server"
**Cause**: Wrong host or firewall blocking  
**Fix**: 
1. Check host format: `db.[project-ref].supabase.co`
2. Check network connectivity
3. Verify Supabase project is running

### Error: "SSL connection required"
**Cause**: Supabase requires SSL connections  
**Fix**: Add `?sslmode=require` to connection string:
```
postgresql://postgres:pass@db.xxx.supabase.co:5432/postgres?sslmode=require
```

---

## 📝 Complete Example Configuration

### `.env` file
```bash
# Supabase REST API (for client SDK) - Keep these!
SUPABASE_URL=https://abc123xyz.supabase.co
SUPABASE_PUBLISHABLE_KEY=sb_publishable_xxxxxxxxxxxxx

# PostgreSQL Database (for Alembic) - Add this!
DATABASE_URL=postgresql://postgres:your_secure_password@db.abc123xyz.supabase.co:5432/postgres

# Other settings...
FAL_KEY=your_fal_key
GEMINI_API_KEY=your_gemini_key
```

**Note**: You need **both**:
- `SUPABASE_URL` + `SUPABASE_PUBLISHABLE_KEY` → For your application code (Supabase client SDK)
- `DATABASE_URL` → For Alembic migrations (direct PostgreSQL connection)

### How It Works

1. **Your Application Code** (`app/services/database.py`):
   ```python
   # Uses SUPABASE_URL + SUPABASE_PUBLISHABLE_KEY
   client = create_client(settings.supabase_url, settings.supabase_key)
   ```

2. **Alembic Migrations** (`alembic/env.py`):
   ```python
   # Uses DATABASE_URL or SUPABASE_DATABASE_URL
   database_url = settings.db_connection_string
   ```

These are **separate** because:
- Supabase client SDK = REST API calls with RLS policies
- Alembic = Direct PostgreSQL access for schema changes

---

## ✅ Verification Checklist

After configuration:

- [ ] `.env` file has `DATABASE_URL` with PostgreSQL connection string
- [ ] Database password is correct (test with psql)
- [ ] `alembic current` runs without errors
- [ ] `python scripts/db_migrate.py upgrade` works
- [ ] Database tables are created successfully

---

## 📚 Additional Resources

- **Supabase Database Docs**: https://supabase.com/docs/guides/database
- **Alembic Documentation**: https://alembic.sqlalchemy.org/
- **PostgreSQL Connection Strings**: https://www.postgresql.org/docs/current/libpq-connect.html
- **Internal Migration Guide**: `DATABASE_MIGRATIONS.md`

---

**Need more help?** Check the error message carefully and compare your connection string format with the examples above.

