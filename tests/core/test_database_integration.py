"""Tests for database integration components.

This module tests the new database integration components including
TitlesDatabase, MultiProviderDatabase, SchemaManager, TransactionLogger,
MaintenanceScheduler, and AnalyticsScheduler using comprehensive mocks.
"""

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from src.mcp_server_anime.core.exceptions import (
    DatabaseNotInitializedError,
    TransactionLoggingError,
)
from src.mcp_server_anime.core.models import AnimeDetails, AnimeSearchResult
from tests.fixtures.database_mocks import (
    MockAnalyticsScheduler,
    MockMaintenanceScheduler,
    MockMultiProviderDatabase,
    MockSchemaManager,
    MockTitlesDatabase,
    MockTransactionLogger,
)


class TestTitlesDatabase:
    """Test TitlesDatabase mock functionality."""

    def test_initialization(self, mock_titles_database: MockTitlesDatabase) -> None:
        """Test database initialization."""
        assert not mock_titles_database.is_initialized
        assert not mock_titles_database.is_closed
        assert mock_titles_database.db_path == Path(":memory:")

    @pytest.mark.asyncio
    async def test_initialize_and_close(
        self, mock_titles_database: MockTitlesDatabase
    ) -> None:
        """Test database initialization and closing."""
        # Initialize
        await mock_titles_database.initialize()
        assert mock_titles_database.is_initialized
        assert not mock_titles_database.is_closed

        # Check call log
        call_log = mock_titles_database.get_call_log()
        assert len(call_log) == 1
        assert call_log[0]["method"] == "initialize"

        # Close
        await mock_titles_database.close()
        assert not mock_titles_database.is_initialized
        assert mock_titles_database.is_closed

        # Check call log
        call_log = mock_titles_database.get_call_log()
        assert len(call_log) == 2
        assert call_log[1]["method"] == "close"

    @pytest.mark.asyncio
    async def test_search_anime_not_initialized(
        self, mock_titles_database: MockTitlesDatabase
    ) -> None:
        """Test search when database not initialized."""
        with pytest.raises(DatabaseNotInitializedError):
            await mock_titles_database.search_anime("test")

    @pytest.mark.asyncio
    async def test_search_anime_success(
        self,
        mock_titles_database: MockTitlesDatabase,
        sample_anime_search_results: list[AnimeSearchResult],
    ) -> None:
        """Test successful anime search."""
        await mock_titles_database.initialize()

        # Set up mock results
        mock_titles_database.setup_search_result(
            "evangelion", sample_anime_search_results
        )

        # Search
        results = await mock_titles_database.search_anime("evangelion", 10)
        assert results == sample_anime_search_results

        # Check call log
        call_log = mock_titles_database.get_call_log()
        search_call = next(
            call for call in call_log if call["method"] == "search_anime"
        )
        assert search_call["query"] == "evangelion"
        assert search_call["limit"] == 10

    @pytest.mark.asyncio
    async def test_get_anime_details_success(
        self,
        mock_titles_database: MockTitlesDatabase,
        sample_anime_details: AnimeDetails,
    ) -> None:
        """Test successful anime details retrieval."""
        await mock_titles_database.initialize()

        # Set up mock details
        mock_titles_database.setup_anime_details(1, sample_anime_details)

        # Get details
        details = await mock_titles_database.get_anime_details(1)
        assert details == sample_anime_details

        # Check call log
        call_log = mock_titles_database.get_call_log()
        details_call = next(
            call for call in call_log if call["method"] == "get_anime_details"
        )
        assert details_call["aid"] == 1

    @pytest.mark.asyncio
    async def test_update_titles(
        self, mock_titles_database: MockTitlesDatabase
    ) -> None:
        """Test titles update."""
        await mock_titles_database.initialize()

        titles_data = b"mock titles data"
        result = await mock_titles_database.update_titles(titles_data)

        assert result["processed_count"] == 1000
        assert result["updated_count"] == 50
        assert result["new_count"] == 25
        assert "duration" in result

        # Check call log
        call_log = mock_titles_database.get_call_log()
        update_call = next(
            call for call in call_log if call["method"] == "update_titles"
        )
        assert update_call["data_size"] == len(titles_data)

    @pytest.mark.asyncio
    async def test_get_database_stats(
        self, mock_titles_database: MockTitlesDatabase
    ) -> None:
        """Test database statistics retrieval."""
        await mock_titles_database.initialize()

        stats = await mock_titles_database.get_database_stats()

        assert "total_anime" in stats
        assert "total_titles" in stats
        assert "database_size" in stats
        assert "last_updated" in stats

        # Check call log
        call_log = mock_titles_database.get_call_log()
        stats_call = next(
            call for call in call_log if call["method"] == "get_database_stats"
        )
        assert stats_call["method"] == "get_database_stats"


class TestMultiProviderDatabase:
    """Test MultiProviderDatabase mock functionality."""

    @pytest.mark.asyncio
    async def test_provider_registration(
        self, mock_multi_provider_database: MockMultiProviderDatabase
    ) -> None:
        """Test provider registration."""
        await mock_multi_provider_database.initialize()

        # Register provider
        await mock_multi_provider_database.register_provider("anidb", "1.0.0")

        # Check provider info
        info = await mock_multi_provider_database.get_provider_info("anidb")
        assert info is not None
        assert info["schema_version"] == "1.0.0"
        assert "registered_at" in info

        # List providers
        providers = await mock_multi_provider_database.list_providers()
        assert "anidb" in providers

    @pytest.mark.asyncio
    async def test_provider_not_found(
        self, mock_multi_provider_database: MockMultiProviderDatabase
    ) -> None:
        """Test provider info for non-existent provider."""
        await mock_multi_provider_database.initialize()

        info = await mock_multi_provider_database.get_provider_info("nonexistent")
        assert info is None


class TestSchemaManager:
    """Test SchemaManager mock functionality."""

    @pytest.mark.asyncio
    async def test_version_management(
        self, mock_schema_manager: MockSchemaManager
    ) -> None:
        """Test schema version management."""
        # Check initial versions
        current = await mock_schema_manager.get_current_version()
        target = await mock_schema_manager.get_target_version()
        assert current == "1.0.0"
        assert target == "1.0.0"

        # Check migration needed
        needs_migration = await mock_schema_manager.needs_migration()
        assert not needs_migration

    @pytest.mark.asyncio
    async def test_migration_needed(
        self, mock_schema_manager: MockSchemaManager
    ) -> None:
        """Test migration when versions differ."""
        # Set different target version
        mock_schema_manager.set_target_version("2.0.0")

        needs_migration = await mock_schema_manager.needs_migration()
        assert needs_migration

        # Perform migration
        result = await mock_schema_manager.migrate()
        assert result["migrated"] is True
        assert result["from_version"] == "1.0.0"
        assert result["to_version"] == "2.0.0"

        # Check migration log
        migration_log = mock_schema_manager.get_migration_log()
        assert len(migration_log) == 1
        assert migration_log[0]["migrated"] is True

    @pytest.mark.asyncio
    async def test_no_migration_needed(
        self, mock_schema_manager: MockSchemaManager
    ) -> None:
        """Test migration when no migration needed."""
        result = await mock_schema_manager.migrate()
        assert result["migrated"] is False
        assert "Already at target version" in result["reason"]

    @pytest.mark.asyncio
    async def test_schema_validation(
        self, mock_schema_manager: MockSchemaManager
    ) -> None:
        """Test schema validation."""
        result = await mock_schema_manager.validate_schema()
        assert result["valid"] is True
        assert result["version"] == "1.0.0"
        assert "tables_checked" in result
        assert "indexes_checked" in result


class TestTransactionLogger:
    """Test TransactionLogger mock functionality."""

    @pytest.mark.asyncio
    async def test_search_logging(
        self, mock_transaction_logger: MockTransactionLogger
    ) -> None:
        """Test search transaction logging."""
        await mock_transaction_logger.initialize()

        # Log search transaction
        await mock_transaction_logger.log_search(
            query="evangelion",
            provider="anidb",
            result_count=5,
            duration=1.2,
            success=True,
        )

        # Check transactions
        transactions = mock_transaction_logger.get_transactions()
        assert len(transactions) == 1

        transaction = transactions[0]
        assert transaction["type"] == "search"
        assert transaction["query"] == "evangelion"
        assert transaction["provider"] == "anidb"
        assert transaction["result_count"] == 5
        assert transaction["duration"] == 1.2
        assert transaction["success"] is True

    @pytest.mark.asyncio
    async def test_details_logging(
        self, mock_transaction_logger: MockTransactionLogger
    ) -> None:
        """Test details transaction logging."""
        await mock_transaction_logger.initialize()

        # Log details transaction
        await mock_transaction_logger.log_details(
            aid=123,
            provider="anidb",
            duration=0.8,
            success=True,
        )

        # Check transactions
        transactions = mock_transaction_logger.get_transactions()
        assert len(transactions) == 1

        transaction = transactions[0]
        assert transaction["type"] == "details"
        assert transaction["aid"] == 123
        assert transaction["provider"] == "anidb"
        assert transaction["duration"] == 0.8
        assert transaction["success"] is True

    @pytest.mark.asyncio
    async def test_analytics_generation(
        self, mock_transaction_logger: MockTransactionLogger
    ) -> None:
        """Test analytics generation."""
        await mock_transaction_logger.initialize()

        # Log multiple transactions
        await mock_transaction_logger.log_search("query1", "anidb", 3, 1.0, True)
        await mock_transaction_logger.log_search(
            "query2", "anidb", 0, 0.5, False, "No results"
        )
        await mock_transaction_logger.log_details(123, "anidb", 0.8, True)

        # Get analytics
        analytics = await mock_transaction_logger.get_analytics()

        assert analytics["total_transactions"] == 3
        assert analytics["search_transactions"] == 2
        assert analytics["details_transactions"] == 1
        assert analytics["success_rate"] == 2 / 3  # 2 successful out of 3
        assert analytics["average_duration"] == (1.0 + 0.5 + 0.8) / 3
        assert len(analytics["top_queries"]) == 2

    @pytest.mark.asyncio
    async def test_not_initialized_error(
        self, mock_transaction_logger: MockTransactionLogger
    ) -> None:
        """Test error when logger not initialized."""
        with pytest.raises(TransactionLoggingError):
            await mock_transaction_logger.log_search("test", "anidb", 1, 1.0)


class TestMaintenanceScheduler:
    """Test MaintenanceScheduler mock functionality."""

    @pytest.mark.asyncio
    async def test_scheduler_lifecycle(
        self, mock_maintenance_scheduler: MockMaintenanceScheduler
    ) -> None:
        """Test scheduler start and stop."""
        assert not mock_maintenance_scheduler.is_running

        # Start scheduler
        await mock_maintenance_scheduler.start()
        assert mock_maintenance_scheduler.is_running

        # Stop scheduler
        await mock_maintenance_scheduler.stop()
        assert not mock_maintenance_scheduler.is_running

    @pytest.mark.asyncio
    async def test_task_scheduling(
        self, mock_maintenance_scheduler: MockMaintenanceScheduler
    ) -> None:
        """Test task scheduling."""
        await mock_maintenance_scheduler.start()

        # Schedule task
        schedule_time = datetime.now() + timedelta(hours=1)
        task_id = await mock_maintenance_scheduler.schedule_task(
            task_name="Test Task",
            task_type="cleanup",
            schedule_time=schedule_time,
        )

        assert task_id.startswith("task_")

        # Check task status
        status = await mock_maintenance_scheduler.get_task_status(task_id)
        assert status is not None
        assert status["name"] == "Test Task"
        assert status["type"] == "cleanup"
        assert status["status"] == "scheduled"

    @pytest.mark.asyncio
    async def test_maintenance_execution(
        self, mock_maintenance_scheduler: MockMaintenanceScheduler
    ) -> None:
        """Test maintenance execution."""
        await mock_maintenance_scheduler.start()

        # Schedule multiple tasks
        schedule_time = datetime.now() + timedelta(hours=1)
        task_id1 = await mock_maintenance_scheduler.schedule_task(
            "Task 1", "cleanup", schedule_time
        )
        task_id2 = await mock_maintenance_scheduler.schedule_task(
            "Task 2", "optimization", schedule_time
        )

        # Run maintenance
        result = await mock_maintenance_scheduler.run_maintenance()

        assert result["tasks_run"] == 2
        assert result["total_duration"] > 0
        assert len(result["tasks"]) == 2

        # Check task statuses
        status1 = await mock_maintenance_scheduler.get_task_status(task_id1)
        status2 = await mock_maintenance_scheduler.get_task_status(task_id2)
        assert status1["status"] == "completed"
        assert status2["status"] == "completed"

    @pytest.mark.asyncio
    async def test_maintenance_stats(
        self, mock_maintenance_scheduler: MockMaintenanceScheduler
    ) -> None:
        """Test maintenance statistics."""
        await mock_maintenance_scheduler.start()

        # Schedule and run tasks
        schedule_time = datetime.now() + timedelta(hours=1)
        await mock_maintenance_scheduler.schedule_task(
            "Task 1", "cleanup", schedule_time
        )
        await mock_maintenance_scheduler.run_maintenance()

        # Get stats
        stats = await mock_maintenance_scheduler.get_maintenance_stats()

        assert stats["scheduled_tasks"] == 0  # All completed
        assert stats["completed_tasks"] == 1
        assert stats["total_tasks"] == 1
        assert stats["last_maintenance"] is not None


class TestAnalyticsScheduler:
    """Test AnalyticsScheduler mock functionality."""

    @pytest.mark.asyncio
    async def test_scheduler_lifecycle(
        self, mock_analytics_scheduler: MockAnalyticsScheduler
    ) -> None:
        """Test scheduler start and stop."""
        assert not mock_analytics_scheduler.is_running

        # Start scheduler
        await mock_analytics_scheduler.start()
        assert mock_analytics_scheduler.is_running

        # Stop scheduler
        await mock_analytics_scheduler.stop()
        assert not mock_analytics_scheduler.is_running

    @pytest.mark.asyncio
    async def test_analytics_execution(
        self, mock_analytics_scheduler: MockAnalyticsScheduler
    ) -> None:
        """Test analytics execution."""
        await mock_analytics_scheduler.start()

        # Run analytics
        result = await mock_analytics_scheduler.run_analytics()

        assert "run_id" in result
        assert "timestamp" in result
        assert "duration" in result
        assert "metrics_calculated" in result
        assert "reports_generated" in result

        # Check history
        history = await mock_analytics_scheduler.get_analytics_history()
        assert len(history) == 1
        assert history[0] == result


class TestDatabaseIntegration:
    """Test integration between database components."""

    @pytest.mark.asyncio
    async def test_full_integration_workflow(
        self,
        mock_titles_database: MockTitlesDatabase,
        mock_schema_manager: MockSchemaManager,
        mock_transaction_logger: MockTransactionLogger,
        sample_anime_search_results: list[AnimeSearchResult],
    ) -> None:
        """Test full integration workflow with multiple components."""
        # Initialize components
        await mock_schema_manager.validate_schema()
        await mock_titles_database.initialize()
        await mock_transaction_logger.initialize()

        # Set up data
        mock_titles_database.setup_search_result(
            "evangelion", sample_anime_search_results
        )

        # Perform search and log transaction
        results = await mock_titles_database.search_anime("evangelion", 10)
        await mock_transaction_logger.log_search(
            query="evangelion",
            provider="local_db",
            result_count=len(results),
            duration=0.5,
            success=True,
        )

        # Verify results
        assert len(results) == len(sample_anime_search_results)

        # Check transaction log
        transactions = mock_transaction_logger.get_transactions()
        assert len(transactions) == 1
        assert transactions[0]["query"] == "evangelion"
        assert transactions[0]["result_count"] == len(results)

        # Get analytics
        analytics = await mock_transaction_logger.get_analytics()
        assert analytics["total_transactions"] == 1
        assert analytics["success_rate"] == 1.0
