"""Full integration tests for database components.

This module provides comprehensive integration tests that exercise
all database components together using the enhanced mock fixtures.
"""

from datetime import datetime, timedelta

import pytest

from src.mcp_server_anime.core.database_config import LocalDatabaseIntegrationConfig
from src.mcp_server_anime.core.models import AnimeDetails, AnimeSearchResult
from tests.fixtures.database_mocks import (
    MockAnalyticsScheduler,
    MockMaintenanceScheduler,
    MockMultiProviderDatabase,
    MockSchemaManager,
    MockTitlesDatabase,
    MockTransactionLogger,
)


@pytest.mark.integration
class TestFullDatabaseIntegration:
    """Test full database integration workflow."""

    @pytest.fixture
    def integration_components(
        self,
        mock_titles_database: MockTitlesDatabase,
        mock_multi_provider_database: MockMultiProviderDatabase,
        mock_schema_manager: MockSchemaManager,
        mock_transaction_logger: MockTransactionLogger,
        mock_maintenance_scheduler: MockMaintenanceScheduler,
        mock_analytics_scheduler: MockAnalyticsScheduler,
    ) -> dict:
        """Provide all integration components."""
        return {
            "titles_db": mock_titles_database,
            "multi_db": mock_multi_provider_database,
            "schema_mgr": mock_schema_manager,
            "transaction_logger": mock_transaction_logger,
            "maintenance_scheduler": mock_maintenance_scheduler,
            "analytics_scheduler": mock_analytics_scheduler,
        }

    @pytest.mark.asyncio
    async def test_complete_system_initialization(
        self,
        integration_components: dict,
        local_db_config: LocalDatabaseIntegrationConfig,
    ) -> None:
        """Test complete system initialization workflow."""
        components = integration_components

        # 1. Schema validation and migration
        schema_mgr = components["schema_mgr"]
        validation_result = await schema_mgr.validate_schema()
        assert validation_result["valid"] is True

        # Check if migration is needed
        needs_migration = await schema_mgr.needs_migration()
        if needs_migration:
            migration_result = await schema_mgr.migrate()
            assert migration_result["migrated"] is True

        # 2. Initialize databases
        titles_db = components["titles_db"]
        multi_db = components["multi_db"]

        await titles_db.initialize()
        await multi_db.initialize()

        assert titles_db.is_initialized
        assert multi_db.is_initialized

        # 3. Register providers
        await multi_db.register_provider("anidb", "1.0.0")
        await multi_db.register_provider("local_titles", "1.0.0")

        providers = await multi_db.list_providers()
        assert "anidb" in providers
        assert "local_titles" in providers

        # 4. Initialize logging and schedulers
        transaction_logger = components["transaction_logger"]
        maintenance_scheduler = components["maintenance_scheduler"]
        analytics_scheduler = components["analytics_scheduler"]

        await transaction_logger.initialize()
        await maintenance_scheduler.start()
        await analytics_scheduler.start()

        assert transaction_logger.is_initialized
        assert maintenance_scheduler.is_running
        assert analytics_scheduler.is_running

    @pytest.mark.asyncio
    async def test_search_workflow_with_logging(
        self,
        integration_components: dict,
        sample_anime_search_results: list[AnimeSearchResult],
    ) -> None:
        """Test complete search workflow with transaction logging."""
        components = integration_components

        # Initialize components
        titles_db = components["titles_db"]
        transaction_logger = components["transaction_logger"]

        await titles_db.initialize()
        await transaction_logger.initialize()

        # Set up search data
        titles_db.setup_search_result("evangelion", sample_anime_search_results)

        # Perform search
        start_time = datetime.now()
        results = await titles_db.search_anime("evangelion", 10)
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # Log the transaction
        await transaction_logger.log_search(
            query="evangelion",
            provider="local_titles",
            result_count=len(results),
            duration=duration,
            success=True,
        )

        # Verify results
        assert len(results) == len(sample_anime_search_results)

        # Verify logging
        transactions = transaction_logger.get_transactions()
        assert len(transactions) == 1

        transaction = transactions[0]
        assert transaction["type"] == "search"
        assert transaction["query"] == "evangelion"
        assert transaction["result_count"] == len(results)
        assert transaction["success"] is True

    @pytest.mark.asyncio
    async def test_details_workflow_with_logging(
        self,
        integration_components: dict,
        sample_anime_details: AnimeDetails,
    ) -> None:
        """Test complete details workflow with transaction logging."""
        components = integration_components

        # Initialize components
        titles_db = components["titles_db"]
        transaction_logger = components["transaction_logger"]

        await titles_db.initialize()
        await transaction_logger.initialize()

        # Set up details data
        titles_db.setup_anime_details(1, sample_anime_details)

        # Get details
        start_time = datetime.now()
        details = await titles_db.get_anime_details(1)
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # Log the transaction
        await transaction_logger.log_details(
            aid=1,
            provider="local_titles",
            duration=duration,
            success=True,
        )

        # Verify results
        assert details == sample_anime_details

        # Verify logging
        transactions = transaction_logger.get_transactions()
        assert len(transactions) == 1

        transaction = transactions[0]
        assert transaction["type"] == "details"
        assert transaction["aid"] == 1
        assert transaction["success"] is True

    @pytest.mark.asyncio
    async def test_maintenance_workflow(
        self,
        integration_components: dict,
    ) -> None:
        """Test maintenance workflow."""
        components = integration_components

        # Initialize components
        titles_db = components["titles_db"]
        maintenance_scheduler = components["maintenance_scheduler"]

        await titles_db.initialize()
        await maintenance_scheduler.start()

        # Schedule maintenance tasks
        schedule_time = datetime.now() + timedelta(minutes=5)

        task_id1 = await maintenance_scheduler.schedule_task(
            task_name="Database Vacuum",
            task_type="vacuum",
            schedule_time=schedule_time,
        )

        task_id2 = await maintenance_scheduler.schedule_task(
            task_name="Index Optimization",
            task_type="optimize",
            schedule_time=schedule_time,
        )

        # Run maintenance
        maintenance_result = await maintenance_scheduler.run_maintenance()

        assert maintenance_result["tasks_run"] == 2
        assert maintenance_result["total_duration"] > 0

        # Check task statuses
        task1_status = await maintenance_scheduler.get_task_status(task_id1)
        task2_status = await maintenance_scheduler.get_task_status(task_id2)

        assert task1_status["status"] == "completed"
        assert task2_status["status"] == "completed"

        # Get maintenance stats
        stats = await maintenance_scheduler.get_maintenance_stats()
        assert stats["completed_tasks"] == 2
        assert stats["scheduled_tasks"] == 0  # All completed

    @pytest.mark.asyncio
    async def test_analytics_workflow(
        self,
        integration_components: dict,
    ) -> None:
        """Test analytics workflow."""
        components = integration_components

        # Initialize components
        transaction_logger = components["transaction_logger"]
        analytics_scheduler = components["analytics_scheduler"]

        await transaction_logger.initialize()
        await analytics_scheduler.start()

        # Generate some transaction data
        await transaction_logger.log_search("evangelion", "anidb", 5, 1.2, True)
        await transaction_logger.log_search("cowboy bebop", "anidb", 3, 0.8, True)
        await transaction_logger.log_search(
            "nonexistent", "anidb", 0, 0.3, False, "Not found"
        )
        await transaction_logger.log_details(123, "anidb", 0.5, True)

        # Run analytics
        analytics_result = await analytics_scheduler.run_analytics()

        assert "run_id" in analytics_result
        assert "duration" in analytics_result
        assert "metrics_calculated" in analytics_result

        # Get transaction analytics
        analytics = await transaction_logger.get_analytics()

        assert analytics["total_transactions"] == 4
        assert analytics["search_transactions"] == 3
        assert analytics["details_transactions"] == 1
        assert analytics["success_rate"] == 0.75  # 3 out of 4 successful

        # Check analytics history
        history = await analytics_scheduler.get_analytics_history()
        assert len(history) == 1
        assert history[0]["run_id"] == analytics_result["run_id"]

    @pytest.mark.asyncio
    async def test_titles_update_workflow(
        self,
        integration_components: dict,
    ) -> None:
        """Test titles update workflow."""
        components = integration_components

        # Initialize components
        titles_db = components["titles_db"]
        transaction_logger = components["transaction_logger"]
        maintenance_scheduler = components["maintenance_scheduler"]

        await titles_db.initialize()
        await transaction_logger.initialize()
        await maintenance_scheduler.start()

        # Simulate titles update
        mock_titles_data = b"mock anime titles data"
        update_result = await titles_db.update_titles(mock_titles_data)

        assert update_result["processed_count"] > 0
        assert update_result["updated_count"] >= 0
        assert update_result["new_count"] >= 0

        # Schedule post-update maintenance
        schedule_time = datetime.now() + timedelta(minutes=1)
        await maintenance_scheduler.schedule_task(
            task_name="Post-Update Optimization",
            task_type="optimize",
            schedule_time=schedule_time,
        )

        # Run maintenance
        maintenance_result = await maintenance_scheduler.run_maintenance("optimize")
        assert maintenance_result["tasks_run"] == 1

        # Get updated database stats
        stats = await titles_db.get_database_stats()
        assert "total_anime" in stats
        assert "last_updated" in stats

    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(
        self,
        integration_components: dict,
    ) -> None:
        """Test error handling and recovery scenarios."""
        components = integration_components

        # Initialize components
        titles_db = components["titles_db"]
        transaction_logger = components["transaction_logger"]

        await titles_db.initialize()
        await transaction_logger.initialize()

        # Test search with no results
        empty_results = await titles_db.search_anime("nonexistent_anime_xyz", 10)
        assert len(empty_results) == 0

        # Log failed search
        await transaction_logger.log_search(
            query="nonexistent_anime_xyz",
            provider="local_titles",
            result_count=0,
            duration=0.1,
            success=False,
            error="No results found",
        )

        # Test details for non-existent anime
        details = await titles_db.get_anime_details(999999)
        assert details is None

        # Log failed details lookup
        await transaction_logger.log_details(
            aid=999999,
            provider="local_titles",
            duration=0.05,
            success=False,
            error="Anime not found",
        )

        # Verify error logging
        analytics = await transaction_logger.get_analytics()
        assert analytics["total_transactions"] == 2
        assert analytics["success_rate"] == 0.0  # Both failed

    @pytest.mark.asyncio
    async def test_system_shutdown_workflow(
        self,
        integration_components: dict,
    ) -> None:
        """Test proper system shutdown workflow."""
        components = integration_components

        # Initialize all components
        titles_db = components["titles_db"]
        multi_db = components["multi_db"]
        transaction_logger = components["transaction_logger"]
        maintenance_scheduler = components["maintenance_scheduler"]
        analytics_scheduler = components["analytics_scheduler"]

        await titles_db.initialize()
        await multi_db.initialize()
        await transaction_logger.initialize()
        await maintenance_scheduler.start()
        await analytics_scheduler.start()

        # Verify all components are running
        assert titles_db.is_initialized
        assert multi_db.is_initialized
        assert transaction_logger.is_initialized
        assert maintenance_scheduler.is_running
        assert analytics_scheduler.is_running

        # Shutdown in proper order
        await analytics_scheduler.stop()
        await maintenance_scheduler.stop()
        await transaction_logger.close()
        await multi_db.close()
        await titles_db.close()

        # Verify all components are stopped
        assert not analytics_scheduler.is_running
        assert not maintenance_scheduler.is_running
        assert not transaction_logger.is_initialized
        assert not multi_db.is_initialized
        assert titles_db.is_closed

    @pytest.mark.asyncio
    async def test_concurrent_operations(
        self,
        integration_components: dict,
        sample_anime_search_results: list[AnimeSearchResult],
    ) -> None:
        """Test concurrent database operations."""
        import asyncio

        components = integration_components

        # Initialize components
        titles_db = components["titles_db"]
        transaction_logger = components["transaction_logger"]

        await titles_db.initialize()
        await transaction_logger.initialize()

        # Set up test data
        titles_db.setup_search_result("query1", sample_anime_search_results[:2])
        titles_db.setup_search_result("query2", sample_anime_search_results[1:])

        # Define concurrent operations
        async def search_and_log(query: str, provider: str) -> None:
            results = await titles_db.search_anime(query, 10)
            await transaction_logger.log_search(
                query=query,
                provider=provider,
                result_count=len(results),
                duration=0.1,
                success=True,
            )

        # Run concurrent searches
        await asyncio.gather(
            search_and_log("query1", "local_titles"),
            search_and_log("query2", "local_titles"),
            search_and_log("query1", "local_titles"),  # Duplicate query
        )

        # Verify all transactions were logged
        transactions = transaction_logger.get_transactions()
        assert len(transactions) == 3

        # Verify analytics
        analytics = await transaction_logger.get_analytics()
        assert analytics["total_transactions"] == 3
        assert analytics["success_rate"] == 1.0

        # Check top queries
        top_queries = analytics["top_queries"]
        query1_count = next(
            (q["count"] for q in top_queries if q["query"] == "query1"), 0
        )
        query2_count = next(
            (q["count"] for q in top_queries if q["query"] == "query2"), 0
        )

        assert query1_count == 2  # query1 was searched twice
        assert query2_count == 1  # query2 was searched once
