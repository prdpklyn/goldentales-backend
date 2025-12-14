#!/usr/bin/env python3
"""
Database Migration Helper Script
=================================
Simplifies common Alembic migration tasks.

Usage:
    python scripts/db_migrate.py upgrade      # Run migrations
    python scripts/db_migrate.py downgrade    # Rollback one migration
    python scripts/db_migrate.py current      # Show current revision
    python scripts/db_migrate.py history      # Show migration history
    python scripts/db_migrate.py create "message"  # Create new migration
"""

import sys
import subprocess
from pathlib import Path

# Ensure we're in the project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def run_alembic(command: list[str]) -> int:
    """Run an Alembic command."""
    try:
        result = subprocess.run(
            ["alembic"] + command,
            cwd=PROJECT_ROOT,
            capture_output=False
        )
        return result.returncode
    except FileNotFoundError:
        print("❌ Error: Alembic not installed!")
        print("   Run: pip install alembic==1.13.1")
        return 1


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python scripts/db_migrate.py [command]")
        print("\nCommands:")
        print("  upgrade       - Apply pending migrations")
        print("  downgrade     - Rollback last migration")
        print("  current       - Show current database version")
        print("  history       - Show migration history")
        print("  create <msg>  - Create new migration")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "upgrade":
        print("🔄 Applying database migrations...")
        return run_alembic(["upgrade", "head"])
    
    elif command == "downgrade":
        print("⏪ Rolling back last migration...")
        return run_alembic(["downgrade", "-1"])
    
    elif command == "current":
        print("📍 Current database version:")
        return run_alembic(["current"])
    
    elif command == "history":
        print("📜 Migration history:")
        return run_alembic(["history", "--verbose"])
    
    elif command == "create":
        if len(sys.argv) < 3:
            print("❌ Error: Please provide a migration message")
            print("   Example: python scripts/db_migrate.py create \"add users table\"")
            return 1
        
        message = sys.argv[2]
        print(f"📝 Creating new migration: {message}")
        return run_alembic(["revision", "-m", message])
    
    elif command == "auto":
        print("🤖 Auto-generating migration (requires SQLAlchemy models)...")
        if len(sys.argv) < 3:
            message = "auto generated changes"
        else:
            message = sys.argv[2]
        return run_alembic(["revision", "--autogenerate", "-m", message])
    
    else:
        print(f"❌ Unknown command: {command}")
        print("   Run without arguments to see available commands")
        return 1


if __name__ == "__main__":
    sys.exit(main())

