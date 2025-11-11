"""Database schema management and migration system.

This module handles database schema versioning, migrations, and validation
to ensure database integrity across different versions of the application.
"""

import sqlite3
from datetime import datetime
from typing import ClassVar

from .exceptions import ConfigurationError, DatabaseError
from .logging_config import get_logger

logger = get_logger(__name__)


class SchemaVersion:
    """Represents a database schema version with migration information."""

    def __init__(
        self,
        version: str,
        description: str,
        migration_sql: list[str],
        rollback_sql: list[str] | None = None,
    ):
        """Initialize schema version.

        Args:
            version: Version string (e.g., "1.0", "1.1")
            description: Human-readable description of changes
            migration_sql: List of SQL statements to apply this version
            rollback_sql: Optional list of SQL statements to rollback this version
        """
        self.version = version
        self.description = description
        self.migration_sql = migration_sql
        self.rollback_sql = rollback_sql or []

    def __str__(self) -> str:
        return f"SchemaVersion({self.version}: {self.description})"

    def __repr__(self) -> str:
        return self.__str__()


class SchemaManager:
    """Manages database schema versions and migrations."""

    # Define all schema versions in order
    SCHEMA_VERSIONS: ClassVar[list] = [
        SchemaVersion(
            version="1.0",
            description="Initial multi-provider database schema",
            migration_sql=[
                """
                CREATE TABLE IF NOT EXISTS search_transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    provider TEXT NOT NULL,
                    query TEXT NOT NULL,
                    result_count INTEGER NOT NULL,
                    response_time_ms REAL NOT NULL,
                    client_identifier TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """,
                """
                CREATE INDEX IF NOT EXISTS idx_search_transactions_provider
                ON search_transactions(provider)
                """,
                """
                CREATE INDEX IF NOT EXISTS idx_search_transactions_timestamp
                ON search_transactions(timestamp)
                """,
                """
                CREATE TABLE IF NOT EXISTS database_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """,
                """
                INSERT OR REPLACE INTO database_metadata (key, value)
                VALUES ('schema_version', '1.0')
                """,
            ],
            rollback_sql=[
                "DROP TABLE IF EXISTS search_transactions",
                "DROP TABLE IF EXISTS database_metadata",
            ],
        ),
        SchemaVersion(
            version="1.1",
            description="Add performance indexes and transaction cleanup",
            migration_sql=[
                """
                CREATE INDEX IF NOT EXISTS idx_search_transactions_created_at
                ON search_transactions(created_at)
                """,
                """
                CREATE INDEX IF NOT EXISTS idx_search_transactions_composite
                ON search_transactions(provider, timestamp)
                """,
                """
                INSERT OR REPLACE INTO database_metadata (key, value)
                VALUES ('schema_version', '1.1')
                """,
            ],
            rollback_sql=[
                "DROP INDEX IF EXISTS idx_search_transactions_created_at",
                "DROP INDEX IF EXISTS idx_search_transactions_composite",
                """
                INSERT OR REPLACE INTO database_metadata (key, value)
                VALUES ('schema_version', '1.0')
                """,
            ],
        ),
    ]

    def __init__(self, db_path: str):
        """Initialize schema manager.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.current_version = self._get_latest_version()

    def _get_latest_version(self) -> str:
        """Get the latest schema version."""
        if not self.SCHEMA_VERSIONS:
            return "0.0"
        return self.SCHEMA_VERSIONS[-1].version

    def get_current_database_version(self) -> str | None:
        """Get the current database schema version.

        Returns:
            Current schema version or None if not set

        Raises:
            DatabaseError: If unable to read database version
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Check if metadata table exists
                cursor = conn.execute("""
                    SELECT name FROM sqlite_master
                    WHERE type='table' AND name='database_metadata'
                """)

                if not cursor.fetchone():
                    return None

                # Get schema version
                cursor = conn.execute("""
                    SELECT value FROM database_metadata WHERE key = 'schema_version'
                """)
                result = cursor.fetchone()
                return result[0] if result else None

        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to get database version: {e}") from e

    def needs_migration(self) -> bool:
        """Check if database needs migration to latest schema.

        Returns:
            True if migration is needed
        """
        current_db_version = self.get_current_database_version()

        # New database needs migration
        if current_db_version is None:
            return True

        # Check if current version is older than latest
        return self._compare_versions(current_db_version, self.current_version) < 0

    def _compare_versions(self, version1: str, version2: str) -> int:
        """Compare two version strings.

        Args:
            version1: First version string
            version2: Second version string

        Returns:
            -1 if version1 < version2, 0 if equal, 1 if version1 > version2
        """

        def version_tuple(v: str) -> tuple[int, ...]:
            return tuple(map(int, v.split(".")))

        v1_tuple = version_tuple(version1)
        v2_tuple = version_tuple(version2)

        if v1_tuple < v2_tuple:
            return -1
        elif v1_tuple > v2_tuple:
            return 1
        else:
            return 0

    def get_migration_path(
        self, from_version: str | None = None, to_version: str | None = None
    ) -> list[SchemaVersion]:
        """Get the migration path between two versions.

        Args:
            from_version: Starting version (None for new database)
            to_version: Target version (None for latest)

        Returns:
            List of schema versions to apply in order

        Raises:
            ConfigurationError: If migration path is invalid
        """
        if to_version is None:
            to_version = self.current_version

        # For new database, apply all versions up to target
        if from_version is None:
            migration_versions = []
            for schema_version in self.SCHEMA_VERSIONS:
                if self._compare_versions(schema_version.version, to_version) <= 0:
                    migration_versions.append(schema_version)
            return migration_versions

        # Find migration path from current to target version
        migration_versions = []
        start_found = False

        for schema_version in self.SCHEMA_VERSIONS:
            # Start collecting after we pass the from_version
            if not start_found:
                if self._compare_versions(schema_version.version, from_version) > 0:
                    start_found = True
                else:
                    continue

            # Stop when we reach the target version
            if self._compare_versions(schema_version.version, to_version) > 0:
                break

            migration_versions.append(schema_version)

        return migration_versions

    def migrate_database(
        self, target_version: str | None = None, dry_run: bool = False
    ) -> dict[str, any]:
        """Migrate database to target schema version.

        Args:
            target_version: Target version (None for latest)
            dry_run: If True, only validate migration without applying

        Returns:
            Dictionary with migration results

        Raises:
            DatabaseError: If migration fails
        """
        if target_version is None:
            target_version = self.current_version

        current_db_version = self.get_current_database_version()
        migration_path = self.get_migration_path(current_db_version, target_version)

        migration_info = {
            "from_version": current_db_version,
            "to_version": target_version,
            "migrations_needed": len(migration_path),
            "migration_versions": [v.version for v in migration_path],
            "dry_run": dry_run,
            "success": False,
            "applied_migrations": [],
            "error": None,
        }

        if not migration_path:
            migration_info["success"] = True
            migration_info["message"] = "No migration needed"
            logger.info(f"Database already at version {target_version}")
            return migration_info

        if dry_run:
            migration_info["success"] = True
            migration_info["message"] = f"Would apply {len(migration_path)} migrations"
            logger.info(
                f"Dry run: Would migrate from {current_db_version} to {target_version}"
            )
            return migration_info

        # Apply migrations
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Enable foreign keys
                conn.execute("PRAGMA foreign_keys = ON")

                # Start transaction
                conn.execute("BEGIN TRANSACTION")

                try:
                    for schema_version in migration_path:
                        logger.info(
                            f"Applying migration {schema_version.version}: {schema_version.description}"
                        )

                        for sql_statement in schema_version.migration_sql:
                            if sql_statement.strip():
                                conn.execute(sql_statement)

                        migration_info["applied_migrations"].append(
                            schema_version.version
                        )

                    # Commit all migrations
                    conn.execute("COMMIT")
                    migration_info["success"] = True
                    migration_info["message"] = (
                        f"Successfully migrated to version {target_version}"
                    )

                    logger.info(
                        f"Database migration completed: {current_db_version} -> {target_version}"
                    )

                except sqlite3.Error as e:
                    # Rollback on error
                    conn.execute("ROLLBACK")
                    raise DatabaseError(
                        f"Migration failed at version {schema_version.version}: {e}"
                    ) from e

        except sqlite3.Error as e:
            migration_info["error"] = str(e)
            raise DatabaseError(f"Database migration failed: {e}") from e

        return migration_info

    def rollback_to_version(self, target_version: str) -> dict[str, any]:
        """Rollback database to a previous schema version.

        Args:
            target_version: Version to rollback to

        Returns:
            Dictionary with rollback results

        Raises:
            DatabaseError: If rollback fails
            ConfigurationError: If rollback is not supported
        """
        current_db_version = self.get_current_database_version()

        if current_db_version is None:
            raise ConfigurationError("Cannot rollback: database version unknown")

        if self._compare_versions(target_version, current_db_version) >= 0:
            raise ConfigurationError(
                f"Cannot rollback to {target_version}: not older than current {current_db_version}"
            )

        rollback_info = {
            "from_version": current_db_version,
            "to_version": target_version,
            "success": False,
            "rolled_back_versions": [],
            "error": None,
        }

        # Find versions to rollback (in reverse order)
        rollback_versions = []
        for schema_version in reversed(self.SCHEMA_VERSIONS):
            if self._compare_versions(schema_version.version, current_db_version) <= 0:
                if self._compare_versions(schema_version.version, target_version) > 0:
                    rollback_versions.append(schema_version)

        if not rollback_versions:
            rollback_info["success"] = True
            rollback_info["message"] = "No rollback needed"
            return rollback_info

        # Check if all versions support rollback
        for schema_version in rollback_versions:
            if not schema_version.rollback_sql:
                raise ConfigurationError(
                    f"Version {schema_version.version} does not support rollback"
                )

        # Apply rollbacks
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("PRAGMA foreign_keys = ON")
                conn.execute("BEGIN TRANSACTION")

                try:
                    for schema_version in rollback_versions:
                        logger.info(f"Rolling back version {schema_version.version}")

                        for sql_statement in schema_version.rollback_sql:
                            if sql_statement.strip():
                                conn.execute(sql_statement)

                        rollback_info["rolled_back_versions"].append(
                            schema_version.version
                        )

                    # Update version metadata
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO database_metadata (key, value, updated_at)
                        VALUES ('schema_version', ?, ?)
                    """,
                        (target_version, datetime.now().isoformat()),
                    )

                    conn.execute("COMMIT")
                    rollback_info["success"] = True
                    rollback_info["message"] = (
                        f"Successfully rolled back to version {target_version}"
                    )

                    logger.info(
                        f"Database rollback completed: {current_db_version} -> {target_version}"
                    )

                except sqlite3.Error as e:
                    conn.execute("ROLLBACK")
                    raise DatabaseError(f"Rollback failed: {e}") from e

        except sqlite3.Error as e:
            rollback_info["error"] = str(e)
            raise DatabaseError(f"Database rollback failed: {e}") from e

        return rollback_info

    def validate_database_integrity(self) -> dict[str, any]:
        """Validate database schema integrity.

        Returns:
            Dictionary with validation results

        Raises:
            DatabaseError: If validation fails
        """
        validation_info = {
            "valid": False,
            "current_version": None,
            "expected_version": self.current_version,
            "issues": [],
            "table_checks": {},
            "index_checks": {},
        }

        try:
            with sqlite3.connect(self.db_path) as conn:
                # Check database version
                current_version = self.get_current_database_version()
                validation_info["current_version"] = current_version

                if current_version is None:
                    validation_info["issues"].append("Database version not set")
                elif current_version != self.current_version:
                    validation_info["issues"].append(
                        f"Version mismatch: expected {self.current_version}, got {current_version}"
                    )

                # Check required tables exist
                required_tables = ["search_transactions", "database_metadata"]

                cursor = conn.execute("""
                    SELECT name FROM sqlite_master WHERE type='table'
                """)
                existing_tables = {row[0] for row in cursor.fetchall()}

                for table in required_tables:
                    if table in existing_tables:
                        validation_info["table_checks"][table] = "exists"
                    else:
                        validation_info["table_checks"][table] = "missing"
                        validation_info["issues"].append(
                            f"Required table missing: {table}"
                        )

                # Check required indexes exist
                required_indexes = [
                    "idx_search_transactions_provider",
                    "idx_search_transactions_timestamp",
                ]

                cursor = conn.execute("""
                    SELECT name FROM sqlite_master WHERE type='index'
                """)
                existing_indexes = {
                    row[0] for row in cursor.fetchall() if row[0]
                }  # Filter out None values

                for index in required_indexes:
                    if index in existing_indexes:
                        validation_info["index_checks"][index] = "exists"
                    else:
                        validation_info["index_checks"][index] = "missing"
                        validation_info["issues"].append(
                            f"Required index missing: {index}"
                        )

                # Check foreign key constraints
                conn.execute("PRAGMA foreign_key_check")

                validation_info["valid"] = len(validation_info["issues"]) == 0

        except sqlite3.Error as e:
            validation_info["issues"].append(f"Database error: {e}")
            raise DatabaseError(f"Database validation failed: {e}") from e

        return validation_info

    def get_schema_info(self) -> dict[str, any]:
        """Get comprehensive schema information.

        Returns:
            Dictionary with schema information
        """
        return {
            "current_database_version": self.get_current_database_version(),
            "latest_available_version": self.current_version,
            "needs_migration": self.needs_migration(),
            "available_versions": [v.version for v in self.SCHEMA_VERSIONS],
            "schema_versions": [
                {
                    "version": v.version,
                    "description": v.description,
                    "has_rollback": bool(v.rollback_sql),
                }
                for v in self.SCHEMA_VERSIONS
            ],
        }


def create_schema_manager(db_path: str) -> SchemaManager:
    """Create a schema manager instance.

    Args:
        db_path: Path to SQLite database file

    Returns:
        SchemaManager instance
    """
    return SchemaManager(db_path)


def ensure_database_schema(
    db_path: str, target_version: str | None = None
) -> dict[str, any]:
    """Ensure database is at the correct schema version.

    Args:
        db_path: Path to SQLite database file
        target_version: Target version (None for latest)

    Returns:
        Dictionary with migration results
    """
    schema_manager = create_schema_manager(db_path)

    if schema_manager.needs_migration():
        return schema_manager.migrate_database(target_version)
    else:
        return {
            "success": True,
            "message": "Database already at target version",
            "from_version": schema_manager.get_current_database_version(),
            "to_version": target_version or schema_manager.current_version,
            "migrations_needed": 0,
        }
