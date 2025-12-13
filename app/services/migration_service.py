# app/services/migration_service.py
"""
GoldenTales Database Migration Service
======================================
Lightweight migration system for Supabase PostgreSQL.

Features:
- Tracks applied migrations in a database table
- Runs SQL migrations in order
- Supports idempotent operations (safe to re-run)
- Works with raw SQL files

Usage:
    from app.services.migration_service import MigrationService

    service = MigrationService(database_url)
    await service.run_migrations()
    await service.get_migration_status()
"""

import os
import re
import asyncio
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

import asyncpg

from app.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class Migration:
    """Represents a database migration."""
    version: str
    name: str
    filename: str
    sql_up: str
    sql_down: Optional[str] = None
    applied_at: Optional[datetime] = None


class MigrationService:
    """
    Database migration service for GoldenTales.

    Manages schema migrations using raw SQL files.
    Compatible with Supabase PostgreSQL.
    """

    MIGRATIONS_TABLE = "schema_migrations"
    MIGRATIONS_DIR = "migrations"

    def __init__(
        self,
        database_url: str,
        migrations_dir: Optional[str] = None
    ):
        """
        Initialize migration service.

        Args:
            database_url: PostgreSQL connection URL
            migrations_dir: Path to migrations directory (default: ./migrations)
        """
        self.database_url = database_url
        self.migrations_dir = Path(migrations_dir or self.MIGRATIONS_DIR)
        self._pool: Optional[asyncpg.Pool] = None

    async def connect(self) -> asyncpg.Pool:
        """Get or create connection pool."""
        if self._pool is None:
            self._pool = await asyncpg.create_pool(
                self.database_url,
                min_size=1,
                max_size=5
            )
        return self._pool

    async def close(self):
        """Close connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None

    async def _ensure_migrations_table(self):
        """Create migrations tracking table if it doesn't exist."""
        pool = await self.connect()
        async with pool.acquire() as conn:
            await conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.MIGRATIONS_TABLE} (
                    version VARCHAR(50) PRIMARY KEY,
                    name VARCHAR(200) NOT NULL,
                    filename VARCHAR(255) NOT NULL,
                    applied_at TIMESTAMP DEFAULT NOW(),
                    checksum VARCHAR(64)
                );

                COMMENT ON TABLE {self.MIGRATIONS_TABLE} IS
                    'Tracks applied database migrations';
            """)

    def _parse_migration_filename(self, filename: str) -> Optional[tuple[str, str]]:
        """
        Parse migration filename to extract version and name.

        Expected format: XXX_description.sql (e.g., 001_create_orders_table.sql)

        Returns:
            Tuple of (version, name) or None if invalid format
        """
        match = re.match(r'^(\d{3})_(.+)\.sql$', filename)
        if match:
            return match.group(1), match.group(2)
        return None

    def _load_migration_file(self, filepath: Path) -> str:
        """Load SQL content from migration file."""
        with open(filepath, 'r') as f:
            return f.read()

    def _compute_checksum(self, sql: str) -> str:
        """Compute checksum of SQL content."""
        import hashlib
        return hashlib.sha256(sql.encode()).hexdigest()[:16]

    def discover_migrations(self) -> List[Migration]:
        """
        Discover all migration files in the migrations directory.

        Returns:
            List of Migration objects, sorted by version
        """
        migrations = []

        if not self.migrations_dir.exists():
            logger.warning(f"Migrations directory not found: {self.migrations_dir}")
            return migrations

        for filepath in sorted(self.migrations_dir.glob("*.sql")):
            parsed = self._parse_migration_filename(filepath.name)
            if parsed:
                version, name = parsed
                sql_up = self._load_migration_file(filepath)

                # Check for down migration
                down_filepath = self.migrations_dir / f"{version}_{name}.down.sql"
                sql_down = None
                if down_filepath.exists():
                    sql_down = self._load_migration_file(down_filepath)

                migrations.append(Migration(
                    version=version,
                    name=name,
                    filename=filepath.name,
                    sql_up=sql_up,
                    sql_down=sql_down
                ))

        return sorted(migrations, key=lambda m: m.version)

    async def get_applied_migrations(self) -> Dict[str, datetime]:
        """
        Get all applied migrations from database.

        Returns:
            Dict mapping version to applied_at timestamp
        """
        await self._ensure_migrations_table()

        pool = await self.connect()
        async with pool.acquire() as conn:
            rows = await conn.fetch(f"""
                SELECT version, applied_at
                FROM {self.MIGRATIONS_TABLE}
                ORDER BY version
            """)

            return {row['version']: row['applied_at'] for row in rows}

    async def run_migrations(
        self,
        target_version: Optional[str] = None,
        dry_run: bool = False
    ) -> List[Migration]:
        """
        Run pending migrations up to target version.

        Args:
            target_version: Optional version to migrate to (default: latest)
            dry_run: If True, show what would be run without executing

        Returns:
            List of migrations that were applied (or would be in dry_run)
        """
        await self._ensure_migrations_table()

        all_migrations = self.discover_migrations()
        applied = await self.get_applied_migrations()

        pending = [m for m in all_migrations if m.version not in applied]

        if target_version:
            pending = [m for m in pending if m.version <= target_version]

        if not pending:
            logger.info("No pending migrations")
            return []

        logger.info(f"Found {len(pending)} pending migration(s)")

        applied_migrations = []
        pool = await self.connect()

        for migration in pending:
            if dry_run:
                logger.info(f"[DRY RUN] Would apply: {migration.filename}")
                applied_migrations.append(migration)
                continue

            logger.info(f"Applying migration: {migration.filename}")

            try:
                async with pool.acquire() as conn:
                    # Run in transaction
                    async with conn.transaction():
                        # Execute migration SQL
                        await conn.execute(migration.sql_up)

                        # Record migration
                        checksum = self._compute_checksum(migration.sql_up)
                        await conn.execute(f"""
                            INSERT INTO {self.MIGRATIONS_TABLE}
                            (version, name, filename, checksum)
                            VALUES ($1, $2, $3, $4)
                        """, migration.version, migration.name,
                            migration.filename, checksum)

                logger.info(f"Successfully applied: {migration.filename}")
                applied_migrations.append(migration)

            except Exception as e:
                logger.error(f"Failed to apply {migration.filename}: {e}")
                raise

        return applied_migrations

    async def rollback(
        self,
        steps: int = 1,
        dry_run: bool = False
    ) -> List[Migration]:
        """
        Rollback migrations.

        Args:
            steps: Number of migrations to rollback
            dry_run: If True, show what would be rolled back

        Returns:
            List of migrations that were rolled back
        """
        await self._ensure_migrations_table()

        all_migrations = self.discover_migrations()
        applied = await self.get_applied_migrations()

        # Get applied migrations with down scripts
        rollback_candidates = []
        for m in reversed(all_migrations):
            if m.version in applied and m.sql_down:
                rollback_candidates.append(m)
                if len(rollback_candidates) >= steps:
                    break

        if not rollback_candidates:
            logger.info("No migrations to rollback (or no down scripts available)")
            return []

        rolled_back = []
        pool = await self.connect()

        for migration in rollback_candidates:
            if dry_run:
                logger.info(f"[DRY RUN] Would rollback: {migration.filename}")
                rolled_back.append(migration)
                continue

            logger.info(f"Rolling back: {migration.filename}")

            try:
                async with pool.acquire() as conn:
                    async with conn.transaction():
                        # Execute down migration
                        await conn.execute(migration.sql_down)

                        # Remove from tracking
                        await conn.execute(f"""
                            DELETE FROM {self.MIGRATIONS_TABLE}
                            WHERE version = $1
                        """, migration.version)

                logger.info(f"Successfully rolled back: {migration.filename}")
                rolled_back.append(migration)

            except Exception as e:
                logger.error(f"Failed to rollback {migration.filename}: {e}")
                raise

        return rolled_back

    async def get_status(self) -> Dict[str, Any]:
        """
        Get migration status.

        Returns:
            Dict with migration status info
        """
        await self._ensure_migrations_table()

        all_migrations = self.discover_migrations()
        applied = await self.get_applied_migrations()

        pending = [m for m in all_migrations if m.version not in applied]

        return {
            "total_migrations": len(all_migrations),
            "applied_count": len(applied),
            "pending_count": len(pending),
            "applied": [
                {
                    "version": m.version,
                    "name": m.name,
                    "applied_at": applied[m.version].isoformat()
                }
                for m in all_migrations if m.version in applied
            ],
            "pending": [
                {
                    "version": m.version,
                    "name": m.name,
                    "filename": m.filename
                }
                for m in pending
            ],
            "current_version": max(applied.keys()) if applied else None
        }

    async def verify_checksums(self) -> Dict[str, Any]:
        """
        Verify that applied migrations match current files.

        Useful for detecting if migration files were modified after being applied.

        Returns:
            Dict with verification results
        """
        await self._ensure_migrations_table()

        all_migrations = self.discover_migrations()

        pool = await self.connect()
        async with pool.acquire() as conn:
            rows = await conn.fetch(f"""
                SELECT version, filename, checksum
                FROM {self.MIGRATIONS_TABLE}
            """)

        stored_checksums = {row['version']: row['checksum'] for row in rows}

        mismatches = []
        for migration in all_migrations:
            if migration.version in stored_checksums:
                current_checksum = self._compute_checksum(migration.sql_up)
                stored = stored_checksums[migration.version]
                if stored and current_checksum != stored:
                    mismatches.append({
                        "version": migration.version,
                        "filename": migration.filename,
                        "stored_checksum": stored,
                        "current_checksum": current_checksum
                    })

        return {
            "valid": len(mismatches) == 0,
            "mismatches": mismatches
        }


# Singleton instance
_migration_service: Optional[MigrationService] = None


def get_migration_service(database_url: Optional[str] = None) -> MigrationService:
    """Get migration service singleton."""
    global _migration_service

    if _migration_service is None:
        if database_url is None:
            from app.settings import settings
            database_url = settings.supabase_db_url

        _migration_service = MigrationService(database_url)

    return _migration_service


async def run_migrations_on_startup():
    """
    Run pending migrations on application startup.

    Call this from application lifespan:
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            await run_migrations_on_startup()
            yield
    """
    from app.settings import settings

    if not settings.supabase_db_url:
        logger.warning("No database URL configured, skipping migrations")
        return

    try:
        service = get_migration_service(settings.supabase_db_url)
        applied = await service.run_migrations()

        if applied:
            logger.info(f"Applied {len(applied)} migration(s) on startup")
        else:
            logger.info("Database schema is up to date")

    except Exception as e:
        logger.error(f"Migration failed on startup: {e}")
        # Don't crash the app, but log the error
        # In production, you might want to raise here
