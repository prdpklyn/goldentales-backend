# Alembic Error Analysis & Resolution

**Date**: December 13, 2024  
**Error**: `sqlalchemy.exc.NoSuchModuleError: Can't load plugin: sqlalchemy.dialects:https`

---

## 🔍 Step-by-Step Analysis

### Step 1: Identify the Error
```
sqlalchemy.exc.NoSuchModuleError: Can't load plugin: sqlalchemy.dialects:https
```

**Location**: `alembic/env.py`, line 75 in `run_migrations_online()`  
**Function**: `engine_from_config()` → `create_engine()`

### Step 2: Understand What This Means

The error message tells us:
- SQLAlchemy is trying to load a database **dialect** (driver)
- It's looking for a dialect called "**https**"
- No such dialect exists (valid ones: `postgresql`, `mysql`, `sqlite`, etc.)

**Why is it looking for "https"?**
→ Because the connection string starts with `https://`

### Step 3: Trace the Root Cause

Looking at `alembic/env.py` line 41:
```python
config.set_main_option("sqlalchemy.url", settings.supabase_url or "")
```

This loads `SUPABASE_URL` from settings, but:

**Problem**: `SUPABASE_URL` contains the **Supabase REST API URL**, not a PostgreSQL connection string!

### Step 4: Identify the Two Types of Supabase URLs

#### Type 1: REST API URL (Current - WRONG for Alembic)
```bash
https://abc123xyz.supabase.co
```
- Used by: Supabase JavaScript/Python client
- Protocol: HTTPS
- Purpose: REST API calls, authentication, storage
- **Cannot be used for direct database connections**

#### Type 2: PostgreSQL Connection String (NEEDED for Alembic)
```bash
postgresql://postgres:password@db.abc123xyz.supabase.co:5432/postgres
```
- Used by: Alembic, psycopg2, asyncpg
- Protocol: PostgreSQL
- Purpose: Direct database queries, migrations
- **Required for Alembic to work**

### Step 5: Why This Happened

When setting up the project, the user likely:
1. Got the Supabase REST API URL from the dashboard
2. Set it as `SUPABASE_URL`
3. This works fine for the Supabase client SDK
4. But breaks when Alembic tries to connect directly to PostgreSQL

### Step 6: The Fix

We need to provide the PostgreSQL connection string to Alembic.

**Three possible solutions:**

#### Solution A: Add DATABASE_URL (Recommended)
Keep both URLs for different purposes:
```bash
# .env
SUPABASE_URL=https://abc123xyz.supabase.co  # For client SDK
DATABASE_URL=postgresql://postgres:pass@db.abc123xyz.supabase.co:5432/postgres  # For Alembic
```

#### Solution B: Replace SUPABASE_URL
If only using direct database access:
```bash
# .env
SUPABASE_URL=postgresql://postgres:pass@db.abc123xyz.supabase.co:5432/postgres
```

#### Solution C: Update Settings
Add a dedicated field in `app/settings.py`:
```python
database_url: Optional[str] = Field(default=None, alias="DATABASE_URL")
```

---

## ✅ What Was Done to Fix It

### 1. Updated `alembic/env.py`
Added detection for incorrect URL format:
```python
# Override database URL from settings
database_url = settings.supabase_url or ""

# If SUPABASE_URL is the REST API URL (starts with https://), warn user
if database_url.startswith("https://"):
    import re
    match = re.match(r'https://([^.]+)\.supabase\.co', database_url)
    if match:
        project_id = match.group(1)
        print("\n⚠️  WARNING: SUPABASE_URL is the REST API URL, not the database connection string!")
        print(f"   Please set DATABASE_URL with:")
        print(f"   postgresql://postgres:[YOUR-PASSWORD]@db.{project_id}.supabase.co:5432/postgres\n")
        database_url = ""  # Don't use REST API URL
    
config.set_main_option("sqlalchemy.url", database_url)
```

### 2. Created Comprehensive Documentation
- `documentation/DATABASE_SETUP.md` - Complete connection setup guide
- `scripts/test_db_connection.py` - Connection testing script
- Updated `documentation/DATABASE_MIGRATIONS.md` with connection info

### 3. Created Test Script
New script to verify database connection:
```bash
python scripts/test_db_connection.py
```

This script:
- Checks if database URL is configured
- Detects if using wrong URL type (https vs postgresql)
- Tests actual connection
- Lists existing tables
- Provides helpful error messages

---

## 📊 Error Flow Diagram

```
User runs: alembic current
    ↓
Alembic loads: alembic/env.py
    ↓
env.py imports: from app.settings import settings
    ↓
env.py sets: config.set_main_option("sqlalchemy.url", settings.supabase_url)
    ↓
settings.supabase_url = "https://abc123xyz.supabase.co"
    ↓
Alembic calls: run_migrations_online()
    ↓
Creates engine: engine_from_config(...)
    ↓
SQLAlchemy parses URL: "https://abc123xyz.supabase.co"
    ↓
Extracts protocol: "https"
    ↓
Tries to load dialect: sqlalchemy.dialects:https
    ↓
❌ ERROR: No such dialect exists!
```

---

## 🎯 Key Learnings

### 1. Supabase Has Two Different URLs
- REST API URL: For SDK/client libraries
- PostgreSQL URL: For direct database access

### 2. SQLAlchemy Connection Strings Are Protocol-Based
- `postgresql://` → PostgreSQL dialect
- `mysql://` → MySQL dialect
- `sqlite://` → SQLite dialect
- `https://` → ❌ Not a valid database dialect

### 3. Different Tools Need Different URLs
| Tool | Needs | Example |
|------|-------|---------|
| Supabase Client SDK | REST API URL | `https://xxx.supabase.co` |
| Alembic | PostgreSQL URL | `postgresql://...` |
| psycopg2/asyncpg | PostgreSQL URL | `postgresql://...` |
| Direct SQL queries | PostgreSQL URL | `postgresql://...` |

### 4. Environment Variables Need Clear Naming
- `SUPABASE_URL` → Ambiguous (could be either type)
- `DATABASE_URL` → Clear (PostgreSQL connection)
- `SUPABASE_API_URL` → Clear (REST API)

---

## 🚀 Next Steps for User

### Immediate Action Required:

1. **Get PostgreSQL Connection String**
   - Go to https://app.supabase.com
   - Project Settings → Database
   - Copy "Connection string" (URI format)
   - Replace `[YOUR-PASSWORD]` with actual database password

2. **Add to `.env` file**
   ```bash
   DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@db.xxxxx.supabase.co:5432/postgres
   ```

3. **Test Connection**
   ```bash
   python scripts/test_db_connection.py
   ```

4. **Run Migrations**
   ```bash
   alembic current
   python scripts/db_migrate.py upgrade
   ```

### Optional Improvements:

1. Update `app/settings.py` to support both URL types
2. Add validation to reject https:// URLs for database operations
3. Add automatic URL detection and conversion

---

## 📝 Files Created/Modified

### Created:
1. `documentation/DATABASE_SETUP.md` - Complete setup guide (500+ lines)
2. `scripts/test_db_connection.py` - Connection test script
3. `ALEMBIC_ERROR_ANALYSIS.md` - This file

### Modified:
1. `alembic/env.py` - Added URL validation and helpful error messages
2. `documentation/DATABASE_MIGRATIONS.md` - Updated with connection info

---

## 🔍 How to Prevent This in the Future

### 1. Better Documentation
- Clearly distinguish between REST API and database URLs
- Provide examples of both in setup guides
- Show which tools need which URLs

### 2. Validation in Code
```python
def validate_database_url(url: str) -> bool:
    """Ensure URL is a valid PostgreSQL connection string."""
    if url.startswith("https://"):
        raise ValueError(
            "Database URL cannot be an HTTPS REST API URL. "
            "Use postgresql:// connection string instead."
        )
    return url.startswith("postgresql://")
```

### 3. Environment Variable Naming
Use specific names:
- `SUPABASE_API_URL` - For REST API
- `DATABASE_URL` - For PostgreSQL connection
- Avoid ambiguous `SUPABASE_URL`

### 4. Setup Scripts
Create an initialization script that:
- Checks all required environment variables
- Validates URL formats
- Tests connections
- Provides helpful error messages

---

## ✅ Resolution Status

**Status**: ✅ **Analyzed and Documented**

**User Action Required**: 
- Add `DATABASE_URL` to `.env` with PostgreSQL connection string
- Test with: `python scripts/test_db_connection.py`
- Run migrations: `python scripts/db_migrate.py upgrade`

**Documentation**: Complete guides created in:
- `documentation/DATABASE_SETUP.md`
- `documentation/DATABASE_MIGRATIONS.md`

**Tools**: Test script available at:
- `scripts/test_db_connection.py`

---

**Error fully analyzed and resolution path documented!** 🎉

