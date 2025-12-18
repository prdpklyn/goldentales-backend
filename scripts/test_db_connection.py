#!/usr/bin/env python3
"""
Test Database Connection
========================
Simple script to verify database connection works.

Usage:
    python scripts/test_db_connection.py
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from app.settings import settings
    import asyncpg
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("   Run: pip install -r requirements.txt")
    sys.exit(1)


import pytest

@pytest.mark.asyncio
async def test_connection():
    """Test database connection."""
    database_url = settings.supabase_url
    
    if not database_url:
        print("❌ ERROR: No database URL configured!")
        print("\n   Please set one of:")
        print("   - DATABASE_URL in .env")
        print("   - SUPABASE_URL in .env (PostgreSQL format)")
        print("\n   Format: postgresql://user:pass@host:port/database")
        return False
    
    # Check if it's the wrong type of URL
    if database_url.startswith("https://"):
        print("❌ ERROR: SUPABASE_URL is the REST API URL, not the database connection!")
        print(f"   Current: {database_url}")
        print("\n   You need the PostgreSQL connection string instead:")
        print("   postgresql://postgres:PASSWORD@db.xxxxx.supabase.co:5432/postgres")
        print("\n   To find it:")
        print("   1. Go to https://app.supabase.com")
        print("   2. Project Settings → Database")
        print("   3. Copy 'Connection string' (URI format)")
        print("   4. Replace [YOUR-PASSWORD] with your database password")
        print("   5. Add to .env as DATABASE_URL")
        return False
    
    # Check format
    if not database_url.startswith("postgresql://"):
        print(f"⚠️  WARNING: Database URL should start with 'postgresql://'")
        print(f"   Current: {database_url[:50]}...")
        print("\n   Expected format: postgresql://user:pass@host:port/database")
        return False
    
    # Test connection
    print(f"🔍 Testing connection to database...")
    print(f"   Host: {database_url.split('@')[1].split('/')[0] if '@' in database_url else 'unknown'}")
    
    try:
        conn = await asyncpg.connect(database_url)
        version = await conn.fetchval("SELECT version();")
        
        print("\n✅ Database connection successful!")
        print(f"   PostgreSQL: {version.split(',')[0]}")
        
        # Check if tables exist
        tables = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        
        if tables:
            print(f"   Tables found: {len(tables)}")
            for table in tables:
                print(f"     - {table['table_name']}")
        else:
            print("   ⚠️  No tables found - run migrations:")
            print("      python scripts/db_migrate.py upgrade")
        
        await conn.close()
        return True
        
    except asyncpg.InvalidPasswordError:
        print("\n❌ Connection failed: Invalid password")
        print("   Check your database password in .env")
        return False
    except asyncpg.InvalidAuthorizationSpecificationError:
        print("\n❌ Connection failed: Authentication error")
        print("   Check username and password")
        return False
    except asyncpg.CannotConnectNowError:
        print("\n❌ Connection failed: Cannot connect to database")
        print("   Database may be starting up - try again in a moment")
        return False
    except Exception as e:
        print(f"\n❌ Connection failed: {type(e).__name__}")
        print(f"   {str(e)}")
        return False


def main():
    """Main entry point."""
    import asyncio
    
    print("=" * 50)
    print("GoldenTales Database Connection Test")
    print("=" * 50)
    print()
    
    try:
        result = asyncio.run(test_connection())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

