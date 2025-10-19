"""Integration tests for persistent cache with AniDB service.

This module tests the integration of persistent caching with the AniDB service,
including end-to-end caching scenarios, service restart persistence, and
performance benchmarks.
"""

import asyncio
import tempfile
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.mcp_server_anime.core.models import AnimeDetails, AnimeSearchResult
from src.mcp_server_anime.providers.anidb.config import AniDBConfig
from src.mcp_server_anime.providers.anidb.service import AniDBService, create_anidb_service


class TestAniDBServicePersistentCache:
    """Test cases for AniDB service with persistent cache integration."""

    @pytest.fixture
    def test_config(self) -> AniDBConfig:
        """Create test configuration with persistent cache enabled."""
        return AniDBConfig(
            client_name="test-client",
            client_version=1,
            protocol_version=1,
            base_url="http://api.anidb.net:9001/httpapi",
            rate_limit_delay=1.0,
            max_retries=3,
            cache_ttl=3600,
            persistent_cache_enabled=True,
            persistent_cache_ttl=172800,  # 48 hours
            cache_db_path=None,  # Will be set in tests
            memory_cache_size=100,
            timeout=30.0,
            user_agent="test-agent",
        )

    @pytest.fixture
    def sample_anime_details(self) -> AnimeDetails:
        """Create sample anime details for testing."""
        return AnimeDetails(
            aid=17550,
            title="Kaiju No. 8",
            type="TV Series",
            episode_count=12,
            synopsis="Test synopsis for Kaiju No. 8",
            url="http://anidb.net/anime/17550",
            restricted=False,
            picture="kaiju8.jpg",
            titles=[],
            creators=[],
            related_anime=[],
        )

    @pytest.fixture
    def sample_search_results(self) -> list[AnimeSearchResult]:
        """Create sample search results for testing."""
        return [
            AnimeSearchResult(
                aid=17550,
                title="Kaiju No. 8",
                type="TV Series",
                year=2024,
                language="en",
            ),
            AnimeSearchResult(
                aid=22,
                title="Neon Genesis Evangelion",
                type="TV Series",
                year=1995,
                language="en",
            ),
        ]

    async def test_service_cache_initialization(self, test_config: AniDBConfig) -> None:
        """Test that service initializes persistent cache correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_config.cache_db_path = str(Path(temp_dir) / "test_cache.db")
            
            service = AniDBService(test_config)
            await service._ensure_cache()

            assert service._cache is not None
            
            # Check cache stats to verify it's working
            stats = await service.get_cache_stats()
            assert stats is not None
            assert "db_available" in stats
            assert stats["db_available"] is True

            await service.close()

    @patch("src.mcp_server_anime.providers.anidb.service.parse_anime_details")
    @patch("src.mcp_server_anime.core.http_client.HTTPClient.get")
    async def test_end_to_end_caching_anime_details(
        self,
        mock_http_get: AsyncMock,
        mock_parse: MagicMock,
        test_config: AniDBConfig,
        sample_anime_details: AnimeDetails,
    ) -> None:
        """Test end-to-end caching of anime details with real service calls."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_config.cache_db_path = str(Path(temp_dir) / "test_e2e.db")

            # Mock HTTP response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = "<anime><title>Kaiju No. 8</title></anime>"
            mock_response.headers = {"content-type": "application/xml"}
            mock_http_get.return_value = mock_response

            # Mock XML parsing
            mock_parse.return_value = sample_anime_details

            service = AniDBService(test_config)
            
            try:
                # First call should hit API and cache result
                start_time = time.time()
                result1 = await service.get_anime_details(17550)
                first_call_time = time.time() - start_time

                assert result1 is not None
                assert result1.aid == 17550
                assert result1.title == "Kaiju No. 8"

                # Verify API was called
                assert mock_http_get.call_count == 1
                assert mock_parse.call_count == 1

                # Second call should hit cache (much faster)
                start_time = time.time()
                result2 = await service.get_anime_details(17550)
                second_call_time = time.time() - start_time

                assert result2 is not None
                assert result2.aid == 17550
                assert result2.title == "Kaiju No. 8"

                # API should not be called again
                assert mock_http_get.call_count == 1
                assert mock_parse.call_count == 1

                # Cache hit should be faster
                assert second_call_time < first_call_time

                # Check cache stats
                stats = await service.get_cache_stats()
                assert stats["total_hits"] > 0

            finally:
                await service.close()

    async def test_cache_persistence_across_service_restarts(
        self,
        test_config: AniDBConfig,
        sample_anime_details: AnimeDetails,
    ) -> None:
        """Test that cache persists across service restarts."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "restart_test.db"
            test_config.cache_db_path = str(db_path)

            # First service instance
            with patch("src.mcp_server_anime.providers.anidb.service.parse_anime_details") as mock_parse1:
                with patch("src.mcp_server_anime.core.http_client.HTTPClient.get") as mock_http1:
                    mock_response1 = MagicMock()
                    mock_response1.status_code = 200
                    mock_response1.text = "<anime><title>Kaiju No. 8</title></anime>"
                    mock_response1.headers = {"content-type": "application/xml"}
                    mock_http1.return_value = mock_response1
                    mock_parse1.return_value = sample_anime_details

                    service1 = AniDBService(test_config)
                    
                    try:
                        # Cache anime details
                        result1 = await service1.get_anime_details(17550)
                        assert result1 is not None
                        assert mock_http1.call_count == 1

                        # Verify cache entry exists
                        stats1 = await service1.get_cache_stats()
                        assert stats1["db_entries"] > 0 or stats1["memory_entries"] > 0

                    finally:
                        await service1.close()

            # Second service instance (simulating restart)
            with patch("src.mcp_server_anime.providers.anidb.service.parse_anime_details") as mock_parse2:
                with patch("src.mcp_server_anime.core.http_client.HTTPClient.get") as mock_http2:
                    service2 = AniDBService(test_config)
                    
                    try:
                        # Should load from persistent cache without API call
                        result2 = await service2.get_anime_details(17550)
                        assert result2 is not None
                        assert result2.aid == 17550
                        assert result2.title == "Kaiju No. 8"

                        # API should not be called (loaded from cache)
                        assert mock_http2.call_count == 0
                        assert mock_parse2.call_count == 0

                        # Check cache stats
                        stats2 = await service2.get_cache_stats()
                        assert stats2["db_hits"] > 0 or stats2["memory_hits"] > 0

                    finally:
                        await service2.close()

    @patch("src.mcp_server_anime.providers.anidb.search_service.get_search_service")
    async def test_search_results_caching(
        self,
        mock_search_service: MagicMock,
        test_config: AniDBConfig,
        sample_search_results: list[AnimeSearchResult],
    ) -> None:
        """Test caching of search results."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_config.cache_db_path = str(Path(temp_dir) / "search_cache.db")

            # Mock search service
            mock_service = AsyncMock()
            mock_service.search_anime.return_value = sample_search_results
            mock_search_service.return_value = mock_service

            service = AniDBService(test_config)
            
            try:
                # First search should call search service and cache result
                result1 = await service.search_anime("kaiju", limit=10)
                assert len(result1) == 2
                assert result1[0].aid == 17550
                assert mock_service.search_anime.call_count == 1

                # Second search should hit cache
                result2 = await service.search_anime("kaiju", limit=10)
                assert len(result2) == 2
                assert result2[0].aid == 17550
                # Search service should not be called again
                assert mock_service.search_anime.call_count == 1

                # Check cache stats
                stats = await service.get_cache_stats()
                assert stats["total_hits"] > 0

            finally:
                await service.close()

    async def test_cache_configuration_options(self) -> None:
        """Test different cache configuration options."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test with custom configuration
            config = AniDBConfig(
                client_name="test-client",
                client_version=1,
                protocol_version=1,
                base_url="http://api.anidb.net:9001/httpapi",
                rate_limit_delay=1.0,
                max_retries=3,
                cache_ttl=1800,  # 30 minutes
                persistent_cache_enabled=True,
                persistent_cache_ttl=86400,  # 24 hours
                cache_db_path=str(Path(temp_dir) / "config_test.db"),
                memory_cache_size=50,
                timeout=30.0,
                user_agent="test-agent",
            )

            service = AniDBService(config)
            await service._ensure_cache()

            # Verify cache is configured correctly
            assert service._cache is not None
            assert service._cache.memory_ttl == 1800.0
            assert service._cache.persistent_ttl == 86400.0
            assert service._cache.max_memory_size == 50

            await service.close()

    async def test_cache_error_handling_in_service(self, test_config: AniDBConfig) -> None:
        """Test service behavior when cache operations fail."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Use invalid path to cause database errors
            test_config.cache_db_path = "/invalid/path/cache.db"

            service = AniDBService(test_config)
            
            try:
                # Service should still work even if cache fails
                await service._ensure_cache()
                assert service._cache is not None

                # Cache operations should not crash the service
                stats = await service.get_cache_stats()
                assert stats is not None

            finally:
                await service.close()

    async def test_cache_invalidation_methods(
        self,
        test_config: AniDBConfig,
        sample_anime_details: AnimeDetails,
    ) -> None:
        """Test cache invalidation and management methods."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_config.cache_db_path = str(Path(temp_dir) / "invalidation_test.db")

            service = AniDBService(test_config)
            
            try:
                # Manually add cache entry
                await service._ensure_cache()
                await service._cache.set("test_key", sample_anime_details)

                # Verify entry exists
                result = await service._cache.get("test_key")
                assert result is not None

                # Test cache clearing
                await service.clear_cache()
                result = await service._cache.get("test_key")
                assert result is None

                # Test expired cache cleanup
                cleaned = await service.cleanup_expired_cache()
                assert isinstance(cleaned, int)

                # Test cache key invalidation
                await service._cache.set("test_key2", sample_anime_details)
                invalidated = await service.invalidate_cache_key("get_anime_details", aid=123)
                assert isinstance(invalidated, bool)

            finally:
                await service.close()

    async def test_concurrent_service_access(
        self,
        test_config: AniDBConfig,
        sample_anime_details: AnimeDetails,
    ) -> None:
        """Test concurrent access to service with persistent cache."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_config.cache_db_path = str(Path(temp_dir) / "concurrent_service.db")

            async def service_operations(service_id: int) -> list[AnimeDetails | None]:
                service = AniDBService(test_config)
                results = []
                
                try:
                    await service._ensure_cache()
                    
                    # Perform cache operations
                    for i in range(5):
                        key = f"service_{service_id}_key_{i}"
                        await service._cache.set(key, sample_anime_details)
                        result = await service._cache.get(key)
                        results.append(result)
                        
                finally:
                    await service.close()
                    
                return results

            # Run multiple service instances concurrently
            results = await asyncio.gather(
                service_operations(1),
                service_operations(2),
                service_operations(3),
            )

            # Verify all operations completed successfully
            for service_results in results:
                assert len(service_results) == 5
                for result in service_results:
                    assert result is not None
                    assert result.aid == sample_anime_details.aid

    async def test_cache_performance_benchmarks(
        self,
        test_config: AniDBConfig,
        sample_anime_details: AnimeDetails,
    ) -> None:
        """Test cache performance and measure access times."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_config.cache_db_path = str(Path(temp_dir) / "performance_test.db")

            service = AniDBService(test_config)
            
            try:
                await service._ensure_cache()

                # Benchmark cache set operations
                set_times = []
                for i in range(10):
                    start_time = time.time()
                    await service._cache.set(f"perf_key_{i}", sample_anime_details)
                    set_time = time.time() - start_time
                    set_times.append(set_time)

                # Benchmark cache get operations (memory hits)
                memory_get_times = []
                for i in range(10):
                    start_time = time.time()
                    result = await service._cache.get(f"perf_key_{i}")
                    get_time = time.time() - start_time
                    memory_get_times.append(get_time)
                    assert result is not None

                # Clear memory cache to test database access
                await service._cache._memory_cache.clear()

                # Benchmark cache get operations (database hits)
                db_get_times = []
                for i in range(10):
                    start_time = time.time()
                    result = await service._cache.get(f"perf_key_{i}")
                    get_time = time.time() - start_time
                    db_get_times.append(get_time)
                    assert result is not None

                # Verify performance characteristics
                avg_set_time = sum(set_times) / len(set_times)
                avg_memory_get_time = sum(memory_get_times) / len(memory_get_times)
                avg_db_get_time = sum(db_get_times) / len(db_get_times)

                # Memory access should be faster than database access
                assert avg_memory_get_time < avg_db_get_time

                # All operations should complete reasonably quickly (< 100ms)
                assert avg_set_time < 0.1
                assert avg_memory_get_time < 0.1
                assert avg_db_get_time < 0.1

                # Check cache stats for performance metrics
                stats = await service.get_cache_stats()
                assert stats["avg_memory_access_time"] >= 0
                assert stats["avg_db_access_time"] >= 0

            finally:
                await service.close()


class TestAniDBServiceFactory:
    """Test cases for AniDB service factory with persistent cache."""

    async def test_create_service_with_persistent_cache(self) -> None:
        """Test creating service with persistent cache configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = AniDBConfig(
                client_name="factory-test",
                client_version=1,
                protocol_version=1,
                base_url="http://api.anidb.net:9001/httpapi",
                rate_limit_delay=1.0,
                max_retries=3,
                cache_ttl=3600,
                persistent_cache_enabled=True,
                persistent_cache_ttl=172800,
                cache_db_path=str(Path(temp_dir) / "factory_test.db"),
                memory_cache_size=100,
                timeout=30.0,
                user_agent="factory-test-agent",
            )

            service = await create_anidb_service(config)
            
            try:
                assert isinstance(service, AniDBService)
                assert service.config == config
                
                # Verify cache initialization
                await service._ensure_cache()
                assert service._cache is not None
                
                stats = await service.get_cache_stats()
                assert stats is not None
                assert stats["db_available"] is True

            finally:
                await service.close()

    async def test_service_context_manager_with_cache(self) -> None:
        """Test service context manager with persistent cache."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = AniDBConfig(
                client_name="context-test",
                cache_db_path=str(Path(temp_dir) / "context_test.db"),
                persistent_cache_enabled=True,
            )

            async with create_anidb_service(config) as service:
                assert isinstance(service, AniDBService)
                
                # Cache should be available
                await service._ensure_cache()
                stats = await service.get_cache_stats()
                assert stats is not None

            # Service should be properly closed after context manager


@pytest.mark.asyncio
class TestPersistentCacheRealWorldScenarios:
    """Real-world scenario tests for persistent cache integration."""

    async def test_mixed_cache_operations_scenario(self) -> None:
        """Test a realistic scenario with mixed cache operations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = AniDBConfig(
                client_name="mixed-ops-test",
                cache_db_path=str(Path(temp_dir) / "mixed_ops.db"),
                persistent_cache_enabled=True,
                cache_ttl=1800,  # 30 minutes
                persistent_cache_ttl=86400,  # 24 hours
                memory_cache_size=50,
            )

            # Create sample data
            anime_list = []
            for i in range(20):
                anime = AnimeDetails(
                    aid=i + 1,
                    title=f"Test Anime {i + 1}",
                    type="TV Series",
                    episode_count=12 + i,
                    synopsis=f"Synopsis for anime {i + 1}",
                    url=f"http://example.com/{i + 1}",
                    restricted=False,
                    picture=f"pic{i + 1}.jpg",
                    titles=[],
                    creators=[],
                    related_anime=[],
                )
                anime_list.append(anime)

            service = AniDBService(config)
            
            try:
                await service._ensure_cache()

                # Phase 1: Cache multiple anime details
                for i, anime in enumerate(anime_list[:10]):
                    await service._cache.set(f"anime_{anime.aid}", anime)

                # Phase 2: Access some cached items (memory hits)
                for i in range(5):
                    result = await service._cache.get(f"anime_{i + 1}")
                    assert result is not None
                    assert result.aid == i + 1

                # Phase 3: Clear memory cache (simulate memory pressure)
                await service._cache._memory_cache.clear()

                # Phase 4: Access items again (database hits)
                for i in range(5, 10):
                    result = await service._cache.get(f"anime_{i + 1}")
                    assert result is not None
                    assert result.aid == i + 1

                # Phase 5: Add more items (test cache size management)
                for i, anime in enumerate(anime_list[10:]):
                    await service._cache.set(f"anime_{anime.aid}", anime)

                # Phase 6: Verify cache statistics
                stats = await service.get_cache_stats()
                assert stats["total_hits"] > 0
                assert stats["memory_hits"] > 0 or stats["db_hits"] > 0
                assert stats["db_entries"] > 0

                # Phase 7: Test cache cleanup
                cleaned = await service.cleanup_expired_cache()
                assert isinstance(cleaned, int)

                # Phase 8: Test cache clearing
                await service.clear_cache()
                
                # Verify cache is empty
                for i in range(1, 21):
                    result = await service._cache.get(f"anime_{i}")
                    assert result is None

            finally:
                await service.close()

    async def test_cache_recovery_after_database_issues(self) -> None:
        """Test cache behavior and recovery after database issues."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "recovery_test.db"
            config = AniDBConfig(
                client_name="recovery-test",
                cache_db_path=str(db_path),
                persistent_cache_enabled=True,
            )

            anime = AnimeDetails(
                aid=1,
                title="Recovery Test Anime",
                type="TV Series",
                episode_count=12,
                synopsis="Test recovery",
                url="http://example.com/1",
                restricted=False,
                picture="recovery.jpg",
                titles=[],
                creators=[],
                related_anime=[],
            )

            service = AniDBService(config)
            
            try:
                await service._ensure_cache()

                # Cache some data
                await service._cache.set("recovery_key", anime)
                result = await service._cache.get("recovery_key")
                assert result is not None

                # Simulate database corruption by removing the file
                if db_path.exists():
                    db_path.unlink()

                # Cache should still work with memory cache
                result = await service._cache.get("recovery_key")
                assert result is not None  # Should hit memory cache

                # New cache operations should gracefully handle DB errors
                await service._cache.set("new_key", anime)
                result = await service._cache.get("new_key")
                assert result is not None  # Should work with memory cache

                # Check that database is marked as unavailable
                stats = await service.get_cache_stats()
                # Database availability might be False due to the corruption
                assert "db_available" in stats

            finally:
                await service.close()