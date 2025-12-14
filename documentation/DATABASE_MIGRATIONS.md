# GoldenTales Database Migrations Guide

Complete guide for managing database migrations using Alembic.

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Setup](#setup)
3. [Common Tasks](#common-tasks)
4. [Migration Workflow](#migration-workflow)
5. [Best Practices](#best-practices)
6. [Troubleshooting](#troubleshooting)

---

## Overview

GoldenTales uses **Alembic** for database schema migrations with Supabase (PostgreSQL).

### Why Alembic?

- ✅ Version control for database schema
- ✅ Automatic migration generation
- ✅ Rollback support
- ✅ Environment-specific migrations
- ✅ Team collaboration

### Directory Structure

```
GoldenTales/
├── alembic/                    # Alembic configuration
│   ├── env.py                  # Alembic environment config
│   ├── script.py.mako          # Migration template
│   ├── README                  # Alembic info
│   └── versions/               # Migration scripts
│       └── 001_initial_schema.py
├── alembic.ini                 # Alembic settings
├── migrations/                 # SQL reference files
│   ├── 001_create_orders_table.sql
│   └── 002_create_config_tables.sql
└── scripts/                    # Helper scripts
    ├── db_migrate.py           # Python migration helper
    └── db_status.sh            # Check migration status
```

---

## Setup

### 1. Install Alembic

```bash
pip install alembic==1.13.1
```

Or install all requirements:

```bash
pip install -r requirements.txt
```

### 2. Configure Database URL

Set your Supabase connection string:

```bash
export SUPABASE_URL="postgresql://user:pass@host:port/database"
```

Or add to `.env`:

```bash
SUPABASE_URL=postgresql://user:pass@host:port/database
```

### 3. Verify Setup

```bash
# Check configuration
alembic current

# Or use helper script
./scripts/db_status.sh
```

---

## Common Tasks

### Apply Migrations (Upgrade)

**Upgrade to latest:**

```bash
# Using Alembic directly
alembic upgrade head

# Using helper script (recommended)
python scripts/db_migrate.py upgrade
```

**Upgrade to specific revision:**

```bash
alembic upgrade <revision_id>
```

### Rollback Migrations (Downgrade)

**Rollback one migration:**

```bash
# Using Alembic
alembic downgrade -1

# Using helper script
python scripts/db_migrate.py downgrade
```

**Rollback to specific revision:**

```bash
alembic downgrade <revision_id>
```

**Rollback all migrations:**

```bash
alembic downgrade base
```

### Check Migration Status

```bash
# Show current revision
python scripts/db_migrate.py current

# Show migration history
python scripts/db_migrate.py history

# Full status check
./scripts/db_status.sh
```

### Create New Migration

**Manual migration:**

```bash
# Using Alembic
alembic revision -m "add users table"

# Using helper script
python scripts/db_migrate.py create "add users table"
```

**Auto-generate migration (if using SQLAlchemy models):**

```bash
python scripts/db_migrate.py auto "detected schema changes"
```

---

## Migration Workflow

### Development Workflow

1. **Check current status**
   ```bash
   ./scripts/db_status.sh
   ```

2. **Create migration**
   ```bash
   python scripts/db_migrate.py create "add new feature"
   ```

3. **Edit migration file**
   ```bash
   # Edit: alembic/versions/XXX_add_new_feature.py
   ```

4. **Test migration**
   ```bash
   # Apply
   python scripts/db_migrate.py upgrade
   
   # Verify
   # Check database
   
   # Rollback if needed
   python scripts/db_migrate.py downgrade
   ```

5. **Commit to git**
   ```bash
   git add alembic/versions/
   git commit -m "Add migration: add new feature"
   ```

### Production Deployment

1. **Backup database**
   ```bash
   pg_dump $DATABASE_URL > backup.sql
   ```

2. **Review pending migrations**
   ```bash
   alembic current
   alembic history
   ```

3. **Apply migrations**
   ```bash
   python scripts/db_migrate.py upgrade
   ```

4. **Verify**
   ```bash
   # Check application
   # Run smoke tests
   ```

5. **Rollback if needed**
   ```bash
   python scripts/db_migrate.py downgrade
   # Restore from backup if necessary
   ```

---

## Migration File Structure

### Example Migration

```python
"""Add users table

Revision ID: 002
Revises: 001
Create Date: 2024-12-13

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# Revision identifiers
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Apply migration."""
    op.execute("""
        CREATE TABLE users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email VARCHAR(255) UNIQUE NOT NULL,
            name VARCHAR(200),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)


def downgrade() -> None:
    """Rollback migration."""
    op.execute("DROP TABLE IF EXISTS users CASCADE;")
```

### Key Components

- **`revision`**: Unique identifier for this migration
- **`down_revision`**: Previous migration (creates chain)
- **`upgrade()`**: SQL to apply changes
- **`downgrade()`**: SQL to rollback changes

---

## Best Practices

### DO ✅

1. **Always test migrations locally first**
   ```bash
   # Apply
   python scripts/db_migrate.py upgrade
   # Test app
   # Rollback
   python scripts/db_migrate.py downgrade
   ```

2. **Write reversible migrations**
   - Always implement both `upgrade()` and `downgrade()`
   - Test rollback works

3. **Use transactions**
   - Alembic wraps each migration in a transaction
   - All changes succeed or all fail

4. **Keep migrations small**
   - One logical change per migration
   - Easier to review and rollback

5. **Document complex migrations**
   ```python
   def upgrade() -> None:
       """
       Add users table with email verification.
       
       Changes:
       - Create users table
       - Add email_verified column
       - Create index on email
       """
   ```

6. **Backup before production migrations**
   ```bash
   pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql
   ```

### DON'T ❌

1. **Don't edit applied migrations**
   - Create a new migration instead
   - Exception: Migration not yet deployed

2. **Don't skip migrations**
   - Always upgrade sequentially
   - Don't cherry-pick migrations

3. **Don't use database-specific features without checking**
   - Test on same database as production
   - PostgreSQL-specific: Use conditional checks

4. **Don't forget to commit migrations**
   ```bash
   git add alembic/versions/
   git commit -m "Add migration"
   ```

5. **Don't apply untested migrations in production**
   - Test in staging first
   - Review changes carefully

---

## Helper Scripts

### `scripts/db_migrate.py`

Python helper for common migration tasks.

**Usage:**

```bash
# Apply all pending migrations
python scripts/db_migrate.py upgrade

# Rollback last migration
python scripts/db_migrate.py downgrade

# Show current version
python scripts/db_migrate.py current

# Show history
python scripts/db_migrate.py history

# Create new migration
python scripts/db_migrate.py create "description"

# Auto-generate migration
python scripts/db_migrate.py auto "detected changes"
```

### `scripts/db_status.sh`

Shell script to check migration status.

**Usage:**

```bash
./scripts/db_status.sh
```

**Output:**

```
==================================
GoldenTales Database Status
==================================

📍 Current Revision:
001 (head)

📜 Migration History:
001 -> 002 (head), add users table
<base> -> 001, initial schema

🔍 Checking for pending migrations...
✅ Database is up to date

==================================
```

---

## Troubleshooting

### Error: "Alembic not installed"

```bash
pip install alembic==1.13.1
```

### Error: "Can't locate revision identified by 'XXX'"

**Problem**: Migration file deleted or not in sync

**Solution**:
```bash
# Check what's in database
alembic current

# Check what files exist
ls alembic/versions/

# Reset to base if needed
alembic stamp base
alembic upgrade head
```

### Error: "Target database is not up to date"

**Problem**: Database has migrations not in codebase

**Solution**:
```bash
# Check database version
alembic current

# Check codebase versions
alembic history

# Either:
# 1. Pull missing migrations from git
# 2. Downgrade database to match codebase
alembic downgrade <matching_revision>
```

### Error: "Multiple head revisions"

**Problem**: Parallel migrations created (branching)

**Solution**:
```bash
# Show heads
alembic heads

# Merge branches
alembic merge -m "merge branches" <rev1> <rev2>
```

### Error: "Permission denied"

**Problem**: Database user lacks permissions

**Solution**:
- Check database credentials
- Ensure user has CREATE/ALTER/DROP permissions
- Contact database administrator

### Migration Failed Mid-Way

**Problem**: Migration partially applied

**Solution**:
```bash
# Check current state
alembic current

# Manual cleanup if needed
psql $DATABASE_URL
# ... fix database manually ...

# Mark migration as applied
alembic stamp head

# Or rollback
alembic downgrade -1
```

---

## Advanced Topics

### Multiple Environments

```bash
# Development
export DATABASE_URL=postgresql://localhost/goldentales_dev
alembic upgrade head

# Staging
export DATABASE_URL=postgresql://staging.db/goldentales
alembic upgrade head

# Production
export DATABASE_URL=postgresql://prod.db/goldentales
alembic upgrade head
```

### Branching and Merging

```bash
# Create branch
alembic revision -m "feature A" --head=001

# Create another branch
alembic revision -m "feature B" --head=001

# Merge branches
alembic merge -m "merge features" 002 003
```

### SQL-Only Migrations

For complex SQL that's easier to write directly:

```python
def upgrade() -> None:
    op.execute("""
        -- Your complex SQL here
        CREATE TABLE ...;
        CREATE INDEX ...;
        INSERT INTO ...;
    """)

def downgrade() -> None:
    op.execute("""
        DROP TABLE ...;
    """)
```

---

## Quick Reference

| Task | Command |
|------|---------|
| Install | `pip install alembic==1.13.1` |
| Upgrade | `python scripts/db_migrate.py upgrade` |
| Downgrade | `python scripts/db_migrate.py downgrade` |
| Status | `./scripts/db_status.sh` |
| Create | `python scripts/db_migrate.py create "msg"` |
| Current | `alembic current` |
| History | `alembic history` |
| Stamp | `alembic stamp head` |

---

## Resources

- **Alembic Documentation**: https://alembic.sqlalchemy.org/
- **SQLAlchemy Documentation**: https://www.sqlalchemy.org/
- **PostgreSQL Documentation**: https://www.postgresql.org/docs/
- **Supabase Documentation**: https://supabase.com/docs

---

**Need help?** Check the troubleshooting section or review existing migrations in `alembic/versions/`.

