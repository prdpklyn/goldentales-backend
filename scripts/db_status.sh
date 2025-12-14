#!/bin/bash
# Database Migration Status Check
# Shows current migration status and pending migrations

echo "=================================="
echo "GoldenTales Database Status"
echo "=================================="
echo ""

# Check if Alembic is installed
if ! command -v alembic &> /dev/null; then
    echo "❌ Error: Alembic not installed"
    echo "   Run: pip install alembic==1.13.1"
    exit 1
fi

# Check if database URL is configured
if [ -z "$SUPABASE_URL" ]; then
    echo "⚠️  Warning: SUPABASE_URL not set"
    echo "   Database operations may fail"
    echo ""
fi

# Show current revision
echo "📍 Current Revision:"
alembic current
echo ""

# Show migration history
echo "📜 Migration History:"
alembic history --verbose
echo ""

# Check for pending migrations
echo "🔍 Checking for pending migrations..."
CURRENT=$(alembic current 2>/dev/null | tail -n 1)
HEAD=$(alembic heads 2>/dev/null | tail -n 1)

if [ "$CURRENT" = "$HEAD" ]; then
    echo "✅ Database is up to date"
else
    echo "⚠️  Pending migrations detected"
    echo "   Run: python scripts/db_migrate.py upgrade"
fi

echo ""
echo "=================================="

