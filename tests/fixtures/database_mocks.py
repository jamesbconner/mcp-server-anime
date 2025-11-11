"""Mock fixtures for database-related components.

This module provides comprehensive mocks for the new database integration
components including TitlesDatabase, MultiProviderDatabase, SchemaManager,
TransactionLogger, MaintenanceScheduler, and AnalyticsScheduler.
"""

from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from src.mcp_server_anime.core.database_config import (
    DatabaseConfig,
    LocalDatabaseIntegrationConfig,
    TransactionConfig,
)
from src.mcp_server_anime.core.exceptions import (
    DatabaseError,
    DatabaseNotInitializedError,
    TransactionLoggingError,
)
from src.mcp_server_anime.core.models import AnimeDetails, AnimeSearchResult


class MockTitlesDatabase:
    """Mock implementation of TitlesDatabase for testing."""

    def __init__(self, db_path: Path | None = None) -> None:
        """Initialize mock titles database."""
        self.db_path = db_path or Path(":memory:")
        self.is_initialized = False
        self.is_closed = False
        self._search_results: dict[str, list[AnimeSearchResult]] = {}
        self._anime_details: dict[int, AnimeDetails] = {}
        self._call_log: list[dict[str, Any]] = []

    async def initialize(self) -> None:
        """Mock database initialization."""
        if self.is_closed:
            raise DatabaseError("Cannot initialize closed database")
        self.is_initialized = True
        self._log_call("initialize")

    async def close(self) -> None:
        """Mock database close."""
        self.is_closed = True
        self.is_initialized = False
        self._log_call("close")

    async def search_anime(
        self, query: str, limit: int = 10
    ) -> list[AnimeSearchResult]:
        """Mock anime search."""
        if not self.is_initialized:
            raise DatabaseNotInitializedError("Database not initialized")

        self._log_call("search_anime", query=query, limit=limit)
        return self._search_results.get(query.lower(), [])[:limit]

    async def get_anime_details(self, aid: int) -> AnimeDetails | None:
        """Mock anime details retrieval."""
        if not self.is_initialized:
            raise DatabaseNotInitializedError("Database not initialized")

        self._log_call("get_anime_details", aid=aid)
        return self._anime_details.get(aid)

    async def update_titles(self, titles_data: bytes) -> dict[str, Any]:
        """Mock titles update."""
        if not self.is_initialized:
            raise DatabaseNotInitializedError("Database not initialized")

        self._log_call("update_titles", data_size=len(titles_data))
        return {
            "processed_count": 1000,
            "updated_count": 50,
            "new_count": 25,
            "duration": 5.2,
        }

    async def get_database_stats(self) -> dict[str, Any]:
        """Mock database statistics."""
        if not self.is_initialized:
            raise DatabaseNotInitializedError("Database not initialized")

        self._log_call("get_database_stats")
        return {
            "total_anime": len(self._anime_details),
            "total_titles": sum(
                len(results) for results in self._search_results.values()
            ),
            "database_size": 1024 * 1024,  # 1MB
            "last_updated": datetime.now().isoformat(),
        }

    def setup_search_result(self, query: str, results: list[AnimeSearchResult]) -> None:
        """Set up mock search results for a query."""
        self._search_results[query.lower()] = results

    def setup_anime_details(self, aid: int, details: AnimeDetails) -> None:
        """Set up mock anime details for an ID."""
        self._anime_details[aid] = details

    def get_call_log(self) -> list[dict[str, Any]]:
        """Get log of method calls."""
        return self._call_log.copy()

    def clear_call_log(self) -> None:
        """Clear the call log."""
        self._call_log.clear()

    def _log_call(self, method: str, **kwargs: Any) -> None:
        """Log a method call."""
        self._call_log.append(
            {
                "method": method,
                "timestamp": datetime.now().isoformat(),
                **kwargs,
            }
        )


class MockMultiProviderDatabase:
    """Mock implementation of MultiProviderDatabase for testing."""

    def __init__(self, db_path: Path | None = None) -> None:
        """Initialize mock multi-provider database."""
        self.db_path = db_path or Path(":memory:")
        self.is_initialized = False
        self.is_closed = False
        self._providers: dict[str, dict[str, Any]] = {}
        self._call_log: list[dict[str, Any]] = []

    async def initialize(self) -> None:
        """Mock database initialization."""
        if self.is_closed:
            raise DatabaseError("Cannot initialize closed database")
        self.is_initialized = True
        self._log_call("initialize")

    async def close(self) -> None:
        """Mock database close."""
        self.is_closed = True
        self.is_initialized = False
        self._log_call("close")

    async def register_provider(self, provider_name: str, schema_version: str) -> None:
        """Mock provider registration."""
        if not self.is_initialized:
            raise DatabaseNotInitializedError("Database not initialized")

        self._providers[provider_name] = {
            "schema_version": schema_version,
            "registered_at": datetime.now().isoformat(),
        }
        self._log_call(
            "register_provider",
            provider_name=provider_name,
            schema_version=schema_version,
        )

    async def get_provider_info(self, provider_name: str) -> dict[str, Any] | None:
        """Mock provider info retrieval."""
        if not self.is_initialized:
            raise DatabaseNotInitializedError("Database not initialized")

        self._log_call("get_provider_info", provider_name=provider_name)
        return self._providers.get(provider_name)

    async def list_providers(self) -> list[str]:
        """Mock provider listing."""
        if not self.is_initialized:
            raise DatabaseNotInitializedError("Database not initialized")

        self._log_call("list_providers")
        return list(self._providers.keys())

    def get_call_log(self) -> list[dict[str, Any]]:
        """Get log of method calls."""
        return self._call_log.copy()

    def clear_call_log(self) -> None:
        """Clear the call log."""
        self._call_log.clear()

    def _log_call(self, method: str, **kwargs: Any) -> None:
        """Log a method call."""
        self._call_log.append(
            {
                "method": method,
                "timestamp": datetime.now().isoformat(),
                **kwargs,
            }
        )


class MockSchemaManager:
    """Mock implementation of SchemaManager for testing."""

    def __init__(self, db_path: Path | None = None) -> None:
        """Initialize mock schema manager."""
        self.db_path = db_path or Path(":memory:")
        self._current_version = "1.0.0"
        self._target_version = "1.0.0"
        self._migration_log: list[dict[str, Any]] = []
        self._call_log: list[dict[str, Any]] = []

    async def get_current_version(self) -> str:
        """Mock current version retrieval."""
        self._log_call("get_current_version")
        return self._current_version

    async def get_target_version(self) -> str:
        """Mock target version retrieval."""
        self._log_call("get_target_version")
        return self._target_version

    async def needs_migration(self) -> bool:
        """Mock migration check."""
        self._log_call("needs_migration")
        return self._current_version != self._target_version

    async def migrate(self) -> dict[str, Any]:
        """Mock schema migration."""
        if not await self.needs_migration():
            self._log_call("migrate", result="no_migration_needed")
            return {"migrated": False, "reason": "Already at target version"}

        # Simulate migration
        old_version = self._current_version
        self._current_version = self._target_version

        migration_result = {
            "migrated": True,
            "from_version": old_version,
            "to_version": self._current_version,
            "duration": 0.5,
            "steps_executed": 3,
        }

        self._migration_log.append(migration_result)
        self._log_call("migrate", result="success", **migration_result)
        return migration_result

    async def validate_schema(self) -> dict[str, Any]:
        """Mock schema validation."""
        self._log_call("validate_schema")
        return {
            "valid": True,
            "version": self._current_version,
            "tables_checked": 5,
            "indexes_checked": 8,
        }

    def set_current_version(self, version: str) -> None:
        """Set mock current version."""
        self._current_version = version

    def set_target_version(self, version: str) -> None:
        """Set mock target version."""
        self._target_version = version

    def get_migration_log(self) -> list[dict[str, Any]]:
        """Get migration log."""
        return self._migration_log.copy()

    def get_call_log(self) -> list[dict[str, Any]]:
        """Get log of method calls."""
        return self._call_log.copy()

    def clear_call_log(self) -> None:
        """Clear the call log."""
        self._call_log.clear()

    def _log_call(self, method: str, **kwargs: Any) -> None:
        """Log a method call."""
        self._call_log.append(
            {
                "method": method,
                "timestamp": datetime.now().isoformat(),
                **kwargs,
            }
        )


class MockTransactionLogger:
    """Mock implementation of TransactionLogger for testing."""

    def __init__(self, config: TransactionConfig | None = None) -> None:
        """Initialize mock transaction logger."""
        self.config = config or TransactionConfig()
        self.is_initialized = False
        self._transactions: list[dict[str, Any]] = []
        self._call_log: list[dict[str, Any]] = []

    async def initialize(self) -> None:
        """Mock logger initialization."""
        self.is_initialized = True
        self._log_call("initialize")

    async def close(self) -> None:
        """Mock logger close."""
        self.is_initialized = False
        self._log_call("close")

    async def log_search(
        self,
        query: str,
        provider: str,
        result_count: int,
        duration: float,
        success: bool = True,
        error: str | None = None,
    ) -> None:
        """Mock search transaction logging."""
        if not self.is_initialized:
            raise TransactionLoggingError("Logger not initialized")

        transaction = {
            "type": "search",
            "query": query,
            "provider": provider,
            "result_count": result_count,
            "duration": duration,
            "success": success,
            "error": error,
            "timestamp": datetime.now().isoformat(),
        }

        self._transactions.append(transaction)
        self._log_call("log_search", **transaction)

    async def log_details(
        self,
        aid: int,
        provider: str,
        duration: float,
        success: bool = True,
        error: str | None = None,
    ) -> None:
        """Mock details transaction logging."""
        if not self.is_initialized:
            raise TransactionLoggingError("Logger not initialized")

        transaction = {
            "type": "details",
            "aid": aid,
            "provider": provider,
            "duration": duration,
            "success": success,
            "error": error,
            "timestamp": datetime.now().isoformat(),
        }

        self._transactions.append(transaction)
        self._log_call("log_details", **transaction)

    async def get_analytics(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> dict[str, Any]:
        """Mock analytics retrieval."""
        if not self.is_initialized:
            raise TransactionLoggingError("Logger not initialized")

        # Filter transactions by time range if specified
        filtered_transactions = self._transactions
        if start_time or end_time:
            filtered_transactions = [
                t
                for t in self._transactions
                if self._transaction_in_range(t, start_time, end_time)
            ]

        analytics = {
            "total_transactions": len(filtered_transactions),
            "search_transactions": len(
                [t for t in filtered_transactions if t["type"] == "search"]
            ),
            "details_transactions": len(
                [t for t in filtered_transactions if t["type"] == "details"]
            ),
            "success_rate": self._calculate_success_rate(filtered_transactions),
            "average_duration": self._calculate_average_duration(filtered_transactions),
            "top_queries": self._get_top_queries(filtered_transactions),
        }

        self._log_call("get_analytics", **analytics)
        return analytics

    def get_transactions(self) -> list[dict[str, Any]]:
        """Get all logged transactions."""
        return self._transactions.copy()

    def clear_transactions(self) -> None:
        """Clear all logged transactions."""
        self._transactions.clear()

    def get_call_log(self) -> list[dict[str, Any]]:
        """Get log of method calls."""
        return self._call_log.copy()

    def clear_call_log(self) -> None:
        """Clear the call log."""
        self._call_log.clear()

    def _transaction_in_range(
        self,
        transaction: dict[str, Any],
        start_time: datetime | None,
        end_time: datetime | None,
    ) -> bool:
        """Check if transaction is in time range."""
        timestamp = datetime.fromisoformat(transaction["timestamp"])
        if start_time and timestamp < start_time:
            return False
        return not (end_time and timestamp > end_time)

    def _calculate_success_rate(self, transactions: list[dict[str, Any]]) -> float:
        """Calculate success rate for transactions."""
        if not transactions:
            return 0.0
        successful = len([t for t in transactions if t["success"]])
        return successful / len(transactions)

    def _calculate_average_duration(self, transactions: list[dict[str, Any]]) -> float:
        """Calculate average duration for transactions."""
        if not transactions:
            return 0.0
        total_duration = sum(t["duration"] for t in transactions)
        return total_duration / len(transactions)

    def _get_top_queries(
        self, transactions: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Get top queries from transactions."""
        search_transactions = [t for t in transactions if t["type"] == "search"]
        query_counts: dict[str, int] = {}

        for transaction in search_transactions:
            query = transaction["query"]
            query_counts[query] = query_counts.get(query, 0) + 1

        return [
            {"query": query, "count": count}
            for query, count in sorted(
                query_counts.items(), key=lambda x: x[1], reverse=True
            )[:10]
        ]

    def _log_call(self, method: str, **kwargs: Any) -> None:
        """Log a method call."""
        self._call_log.append(
            {
                "method": method,
                "timestamp": datetime.now().isoformat(),
                **kwargs,
            }
        )


class MockMaintenanceScheduler:
    """Mock implementation of MaintenanceScheduler for testing."""

    def __init__(self, config: DatabaseConfig | None = None) -> None:
        """Initialize mock maintenance scheduler."""
        self.config = config or DatabaseConfig()
        self.is_running = False
        self._scheduled_tasks: list[dict[str, Any]] = []
        self._completed_tasks: list[dict[str, Any]] = []
        self._call_log: list[dict[str, Any]] = []

    async def start(self) -> None:
        """Mock scheduler start."""
        if self.is_running:
            return

        self.is_running = True
        self._log_call("start")

    async def stop(self) -> None:
        """Mock scheduler stop."""
        if not self.is_running:
            return

        self.is_running = False
        self._log_call("stop")

    async def schedule_task(
        self,
        task_name: str,
        task_type: str,
        schedule_time: datetime,
        **kwargs: Any,
    ) -> str:
        """Mock task scheduling."""
        task_id = f"task_{len(self._scheduled_tasks) + 1}"
        task = {
            "id": task_id,
            "name": task_name,
            "type": task_type,
            "schedule_time": schedule_time.isoformat(),
            "status": "scheduled",
            "created_at": datetime.now().isoformat(),
            **kwargs,
        }

        self._scheduled_tasks.append(task)
        self._log_call("schedule_task", task_id=task_id, **task)
        return task_id

    async def run_maintenance(self, task_type: str | None = None) -> dict[str, Any]:
        """Mock maintenance execution."""
        tasks_run = []

        # Find tasks to run
        for task in self._scheduled_tasks:
            if task_type is None or task["type"] == task_type:
                if task["status"] == "scheduled":
                    # Mark as completed
                    task["status"] = "completed"
                    task["completed_at"] = datetime.now().isoformat()
                    task["duration"] = 1.5  # Mock duration

                    tasks_run.append(task)
                    self._completed_tasks.append(task.copy())

        result = {
            "tasks_run": len(tasks_run),
            "total_duration": sum(task.get("duration", 0) for task in tasks_run),
            "tasks": tasks_run,
        }

        self._log_call("run_maintenance", **result)
        return result

    async def get_task_status(self, task_id: str) -> dict[str, Any] | None:
        """Mock task status retrieval."""
        for task in self._scheduled_tasks:
            if task["id"] == task_id:
                self._log_call(
                    "get_task_status", task_id=task_id, status=task["status"]
                )
                return task

        self._log_call("get_task_status", task_id=task_id, status="not_found")
        return None

    async def get_maintenance_stats(self) -> dict[str, Any]:
        """Mock maintenance statistics."""
        stats = {
            "scheduled_tasks": len(
                [t for t in self._scheduled_tasks if t["status"] == "scheduled"]
            ),
            "completed_tasks": len(self._completed_tasks),
            "total_tasks": len(self._scheduled_tasks),
            "last_maintenance": (
                max(t["completed_at"] for t in self._completed_tasks)
                if self._completed_tasks
                else None
            ),
        }

        self._log_call("get_maintenance_stats", **stats)
        return stats

    def get_scheduled_tasks(self) -> list[dict[str, Any]]:
        """Get all scheduled tasks."""
        return self._scheduled_tasks.copy()

    def get_completed_tasks(self) -> list[dict[str, Any]]:
        """Get all completed tasks."""
        return self._completed_tasks.copy()

    def get_call_log(self) -> list[dict[str, Any]]:
        """Get log of method calls."""
        return self._call_log.copy()

    def clear_call_log(self) -> None:
        """Clear the call log."""
        self._call_log.clear()

    def _log_call(self, method: str, **kwargs: Any) -> None:
        """Log a method call."""
        self._call_log.append(
            {
                "method": method,
                "timestamp": datetime.now().isoformat(),
                **kwargs,
            }
        )


class MockAnalyticsScheduler:
    """Mock implementation of AnalyticsScheduler for testing."""

    def __init__(self, config: TransactionConfig | None = None) -> None:
        """Initialize mock analytics scheduler."""
        self.config = config or TransactionConfig()
        self.is_running = False
        self._analytics_runs: list[dict[str, Any]] = []
        self._call_log: list[dict[str, Any]] = []

    async def start(self) -> None:
        """Mock scheduler start."""
        if self.is_running:
            return

        self.is_running = True
        self._log_call("start")

    async def stop(self) -> None:
        """Mock scheduler stop."""
        if not self.is_running:
            return

        self.is_running = False
        self._log_call("stop")

    async def run_analytics(self) -> dict[str, Any]:
        """Mock analytics execution."""
        analytics_result = {
            "run_id": f"analytics_{len(self._analytics_runs) + 1}",
            "timestamp": datetime.now().isoformat(),
            "duration": 2.3,
            "metrics_calculated": 15,
            "reports_generated": 3,
        }

        self._analytics_runs.append(analytics_result)
        self._log_call("run_analytics", **analytics_result)
        return analytics_result

    async def get_analytics_history(self) -> list[dict[str, Any]]:
        """Mock analytics history retrieval."""
        self._log_call("get_analytics_history", count=len(self._analytics_runs))
        return self._analytics_runs.copy()

    def get_call_log(self) -> list[dict[str, Any]]:
        """Get log of method calls."""
        return self._call_log.copy()

    def clear_call_log(self) -> None:
        """Clear the call log."""
        self._call_log.clear()

    def _log_call(self, method: str, **kwargs: Any) -> None:
        """Log a method call."""
        self._call_log.append(
            {
                "method": method,
                "timestamp": datetime.now().isoformat(),
                **kwargs,
            }
        )


# Pytest fixtures for database mocks
@pytest.fixture
def mock_titles_database() -> MockTitlesDatabase:
    """Provide a mock TitlesDatabase for testing."""
    return MockTitlesDatabase()


@pytest.fixture
def mock_multi_provider_database() -> MockMultiProviderDatabase:
    """Provide a mock MultiProviderDatabase for testing."""
    return MockMultiProviderDatabase()


@pytest.fixture
def mock_schema_manager() -> MockSchemaManager:
    """Provide a mock SchemaManager for testing."""
    return MockSchemaManager()


@pytest.fixture
def mock_transaction_logger() -> MockTransactionLogger:
    """Provide a mock TransactionLogger for testing."""
    return MockTransactionLogger()


@pytest.fixture
def mock_maintenance_scheduler() -> MockMaintenanceScheduler:
    """Provide a mock MaintenanceScheduler for testing."""
    return MockMaintenanceScheduler()


@pytest.fixture
def mock_analytics_scheduler() -> MockAnalyticsScheduler:
    """Provide a mock AnalyticsScheduler for testing."""
    return MockAnalyticsScheduler()


@pytest.fixture
def database_config() -> DatabaseConfig:
    """Provide a test database configuration."""
    return DatabaseConfig(
        path=Path(":memory:"),
        enable_wal=False,  # Disable WAL for testing
        cache_size=1000,
        timeout=5.0,
    )


@pytest.fixture
def transaction_config() -> TransactionConfig:
    """Provide a test transaction configuration."""
    return TransactionConfig(
        enable_logging=True,
        log_level="DEBUG",
        batch_size=100,
        flush_interval=1.0,  # Fast flush for testing
    )


@pytest.fixture
def local_db_config(
    database_config: DatabaseConfig,
    transaction_config: TransactionConfig,
) -> LocalDatabaseIntegrationConfig:
    """Provide a complete local database integration configuration."""
    return LocalDatabaseIntegrationConfig(
        database=database_config,
        transaction=transaction_config,
    )


# Sample data fixtures
@pytest.fixture
def sample_anime_search_results() -> list[AnimeSearchResult]:
    """Provide sample anime search results for testing."""
    return [
        AnimeSearchResult(aid=1, title="Test Anime 1", type="TV Series", year=2020),
        AnimeSearchResult(aid=2, title="Test Anime 2", type="Movie", year=2021),
        AnimeSearchResult(aid=3, title="Test Anime 3", type="OVA", year=2022),
    ]


@pytest.fixture
def sample_anime_details() -> AnimeDetails:
    """Provide sample anime details for testing."""
    return AnimeDetails(
        aid=1,
        title="Test Anime",
        type="TV Series",
        episode_count=12,
        start_date="2020-01-01",
        end_date="2020-03-31",
        description="A test anime for unit testing.",
        titles=[],
        creators=[],
        related_anime=[],
    )


# Context managers for patching database components
@pytest.fixture
def patch_titles_database(mock_titles_database: MockTitlesDatabase):
    """Patch TitlesDatabase with mock implementation."""
    with patch(
        "src.mcp_server_anime.core.titles_db.TitlesDatabase",
        return_value=mock_titles_database,
    ):
        yield mock_titles_database


@pytest.fixture
def patch_multi_provider_database(
    mock_multi_provider_database: MockMultiProviderDatabase,
):
    """Patch MultiProviderDatabase with mock implementation."""
    with patch(
        "src.mcp_server_anime.core.multi_provider_db.MultiProviderDatabase",
        return_value=mock_multi_provider_database,
    ):
        yield mock_multi_provider_database


@pytest.fixture
def patch_schema_manager(mock_schema_manager: MockSchemaManager):
    """Patch SchemaManager with mock implementation."""
    with patch(
        "src.mcp_server_anime.core.schema_manager.SchemaManager",
        return_value=mock_schema_manager,
    ):
        yield mock_schema_manager


@pytest.fixture
def patch_transaction_logger(mock_transaction_logger: MockTransactionLogger):
    """Patch TransactionLogger with mock implementation."""
    with patch(
        "src.mcp_server_anime.core.transaction_logger.TransactionLogger",
        return_value=mock_transaction_logger,
    ):
        yield mock_transaction_logger


@pytest.fixture
def patch_maintenance_scheduler(mock_maintenance_scheduler: MockMaintenanceScheduler):
    """Patch MaintenanceScheduler with mock implementation."""
    with patch(
        "src.mcp_server_anime.core.maintenance_scheduler.MaintenanceScheduler",
        return_value=mock_maintenance_scheduler,
    ):
        yield mock_maintenance_scheduler


@pytest.fixture
def patch_analytics_scheduler(mock_analytics_scheduler: MockAnalyticsScheduler):
    """Patch AnalyticsScheduler with mock implementation."""
    with patch(
        "src.mcp_server_anime.core.analytics_scheduler.AnalyticsScheduler",
        return_value=mock_analytics_scheduler,
    ):
        yield mock_analytics_scheduler


@pytest.fixture
def patch_all_database_components(
    patch_titles_database: MockTitlesDatabase,
    patch_multi_provider_database: MockMultiProviderDatabase,
    patch_schema_manager: MockSchemaManager,
    patch_transaction_logger: MockTransactionLogger,
    patch_maintenance_scheduler: MockMaintenanceScheduler,
    patch_analytics_scheduler: MockAnalyticsScheduler,
):
    """Patch all database components with mock implementations."""
    return {
        "titles_database": patch_titles_database,
        "multi_provider_database": patch_multi_provider_database,
        "schema_manager": patch_schema_manager,
        "transaction_logger": patch_transaction_logger,
        "maintenance_scheduler": patch_maintenance_scheduler,
        "analytics_scheduler": patch_analytics_scheduler,
    }
