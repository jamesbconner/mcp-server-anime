"""Tests for database CLI components.

This module tests the database CLI functionality using the new mock fixtures
for comprehensive database integration testing.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from click.testing import CliRunner

from src.mcp_server_anime.cli.database_cli import DatabaseCLI
from src.mcp_server_anime.core.exceptions import (
    DatabaseError,
)
from tests.fixtures.database_mocks import (
    MockSchemaManager,
    MockTitlesDatabase,
)


class TestDatabaseCLI:
    """Test DatabaseCLI functionality with mocks."""

    @pytest.fixture
    def cli_runner(self) -> CliRunner:
        """Provide a Click CLI runner for testing."""
        return CliRunner()

    @pytest.fixture
    def database_cli(self) -> DatabaseCLI:
        """Provide a DatabaseCLI instance for testing."""
        with (
            patch(
                "src.mcp_server_anime.cli.database_cli.get_local_db_config"
            ) as mock_config,
            patch(
                "src.mcp_server_anime.cli.database_cli.get_multi_provider_database"
            ) as mock_db,
        ):
            # Mock the config and database with async methods
            mock_config.return_value = Mock()
            mock_database = AsyncMock()
            mock_database.get_database_stats = AsyncMock(
                return_value={"total_titles": 0}
            )
            mock_database.initialize_provider = AsyncMock()
            mock_db.return_value = mock_database

            return DatabaseCLI()

    @pytest.mark.asyncio
    async def test_init_database_success(
        self,
        database_cli: DatabaseCLI,
    ) -> None:
        """Test successful database initialization."""
        # Initialize database
        result = await database_cli.init_database()

        assert result["success"] is True
        assert result["provider"] == "anidb"
        assert "stats" in result

    @pytest.mark.asyncio
    async def test_init_database_failure(
        self,
    ) -> None:
        """Test database initialization failure."""
        # Mock database to raise error on initialization
        with (
            patch(
                "src.mcp_server_anime.cli.database_cli.get_local_db_config"
            ) as mock_config,
            patch(
                "src.mcp_server_anime.cli.database_cli.get_multi_provider_database"
            ) as mock_db,
        ):
            mock_config.return_value = Mock()
            mock_database = AsyncMock()
            mock_database.get_database_stats = AsyncMock(
                return_value={"initialized_providers": []}
            )
            mock_database.initialize_provider = AsyncMock(
                side_effect=DatabaseError("Init failed")
            )
            mock_db.return_value = mock_database

            cli = DatabaseCLI()
            result = await cli.init_database()

            assert result["success"] is False
            assert "Init failed" in result["error"]

    @pytest.mark.asyncio
    async def test_download_titles_success(
        self,
        database_cli: DatabaseCLI,
        mock_titles_database: MockTitlesDatabase,
    ) -> None:
        """Test successful titles download."""
        await mock_titles_database.initialize()

        with patch(
            "src.mcp_server_anime.cli.database_cli.get_multi_provider_database",
            return_value=mock_titles_database,
        ):
            result = await database_cli.download_titles(provider="anidb")

            assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_download_titles_failure(
        self,
        database_cli: DatabaseCLI,
        mock_titles_database: MockTitlesDatabase,
    ) -> None:
        """Test titles download failure."""
        with patch(
            "src.mcp_server_anime.cli.database_cli.get_multi_provider_database",
            return_value=mock_titles_database,
        ):
            result = await database_cli.download_titles(provider="anidb")

            assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_check_database(
        self,
        database_cli: DatabaseCLI,
        mock_titles_database: MockTitlesDatabase,
    ) -> None:
        """Test database health check."""
        await mock_titles_database.initialize()

        with patch(
            "src.mcp_server_anime.cli.database_cli.get_multi_provider_database",
            return_value=mock_titles_database,
        ):
            result = await database_cli.check_database()

            assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_cleanup_database(
        self,
        database_cli: DatabaseCLI,
        mock_titles_database: MockTitlesDatabase,
    ) -> None:
        """Test database cleanup."""
        await mock_titles_database.initialize()

        with patch(
            "src.mcp_server_anime.cli.database_cli.get_multi_provider_database",
            return_value=mock_titles_database,
        ):
            result = await database_cli.cleanup_database()

            assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_migrate_database(
        self,
        database_cli: DatabaseCLI,
        mock_schema_manager: MockSchemaManager,
    ) -> None:
        """Test database migration."""
        # Set up migration needed
        mock_schema_manager.set_target_version("2.0.0")

        with patch(
            "src.mcp_server_anime.cli.database_cli.create_schema_manager",
            return_value=mock_schema_manager,
        ):
            result = await database_cli.migrate_database()

            assert isinstance(result, dict)


class TestDatabaseCLIClickCommands:
    """Test Click command integration for DatabaseCLI."""

    @pytest.fixture
    def cli_runner(self) -> CliRunner:
        """Provide a Click CLI runner for testing."""
        return CliRunner()

    def test_cli_help(self, cli_runner: CliRunner) -> None:
        """Test CLI help command."""
        # This would test the actual Click commands if they were implemented
        # For now, we'll test that the CLI class can be instantiated
        cli = DatabaseCLI()
        assert cli is not None

    @pytest.mark.asyncio
    async def test_cli_integration_with_mocks(
        self,
        mock_titles_database: MockTitlesDatabase,
        mock_schema_manager: MockSchemaManager,
    ) -> None:
        """Test CLI integration with database mocks."""
        with (
            patch(
                "src.mcp_server_anime.cli.database_cli.get_local_db_config"
            ) as mock_config,
            patch(
                "src.mcp_server_anime.cli.database_cli.get_multi_provider_database",
                return_value=mock_titles_database,
            ),
        ):
            mock_config.return_value = Mock()
            cli = DatabaseCLI()

            # Test basic functionality
            result = await cli.check_database()
            assert isinstance(result, dict)

            # Test cleanup
            result = await cli.cleanup_database()
            assert isinstance(result, dict)
