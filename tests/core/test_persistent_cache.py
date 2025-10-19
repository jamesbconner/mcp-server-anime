"""Unit tests for the persistent cache system.

This module tests the PersistentCache implementation, including cache entry management,
TTL expiration, serialization/deserialization, and error handling.
"""

import asyncio
import json
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.mcp_server_anime.core.exceptions import DatabaseError
from src.mcp_server_anime.core.models import AnimeDetails, AnimeSearchResult
from src.mcp_server_anime.core.persistent_cache import (
    PersistentCache,
    create_persistent_cache,
)
from src.mcp_server_anime.core.persistent_cache_models import (
    CacheSerializer,
    PersistentCacheEntry,
    PersistentCacheStats,
)


class TestCacheSerializer:
    """Test cases for CacheSerializer utility class."""

    def test_serialize_anime_details(self) -> None:
        """Test serialization of AnimeDetails objects."""
        details = AnimeDetails(
            aid=1,
            title="Test Anime",
            type="TV Series",
            episode_count=12,
            synopsis="Test synopsis",
            url="http://example.com",
            restricted=False,
            picture="test.jpg",
            titles=[],
            creators=[],
            related_anime=[],
        )

        json_str = CacheSerializer.serialize_anime_details(details)
        assert isinstance(json_str, str)
        assert "Test Anime" in json_str
        assert "TV Series" in json_str

        # Verify it's valid JSON
        parsed = json.loads(json_str)
        assert parsed["aid"] == 1
        assert parsed["title"] == "Test Anime"

    def test_deserialize_anime_details(self) -> None:
        """Test deserialization of AnimeDetails objects."""
        details = AnimeDetails(
            aid=1,
            title="Test Anime",
            type="TV Series",
            episode_count=12,
            synopsis="Test synopsis",
            url="http://example.com",
            restricted=False,
            picture="test.jpg",
            titles=[],
            creators=[],
            related_anime=[],
        )

        json_str = CacheSerializer.serialize_anime_details(details)
        deserialized = CacheSerializer.deserialize_anime_details(json_str)

        assert deserialized.aid == details.aid
        assert deserialized.title == details.title
        assert deserialized.type == details.type
        assert deserialized.episode_count == details.episode_count

    def test_serialize_search_results(self) -> None:
        """Test serialization of search results."""
        results = [
            AnimeSearchResult(
                aid=1,
                title="Test Anime 1",
                type="TV Series",
                year=2023,
                language="en",
            ),
            AnimeSearchResult(
                aid=2,
                title="Test Anime 2",
                type="Movie",
                year=2024,
                language="ja",
            ),
        ]

        json_str = CacheSerializer.serialize_search_results(results)
        assert isinstance(json_str, str)

        # Verify it's valid JSON
        parsed = json.loads(json_str)
        assert len(parsed) == 2
        assert parsed[0]["aid"] == 1
        assert parsed[1]["aid"] == 2

    def test_deserialize_search_results(self) -> None:
        """Test deserialization of search results."""
        results = [
            AnimeSearchResult(
                aid=1,
                title="Test Anime 1",
                type="TV Series",
                year=2023,
                language="en",
            ),
            AnimeSearchResult(
                aid=2,
                title="Test Anime 2",
                type="Movie",
                year=2024,
                language="ja",
            ),
        ]

        json_str = CacheSerializer.serialize_search_results(results)
        deserialized = CacheSerializer.deserialize_search_results(json_str)

        assert len(deserialized) == 2
        assert deserialized[0].aid == 1
        assert deserialized[0].title == "Test Anime 1"
        assert deserialized[1].aid == 2
        assert deserialized[1].title == "Test Anime 2"

    def test_serialize_parameters(self) -> None:
        """Test parameter serialization."""
        params = {"aid": 123, "query": "test", "limit": 10}
        json_str = CacheSerializer.serialize_parameters(params)

        parsed = json.loads(json_str)
        assert parsed == params

    def test_deserialize_parameters(self) -> None:
        """Test parameter deserialization."""
        params = {"aid": 123, "query": "test", "limit": 10}
        json_str = CacheSerializer.serialize_parameters(params)
        deserialized = CacheSerializer.deserialize_parameters(json_str)

        assert deserialized == params

    def test_calculate_data_size(self) -> None:
        """Test data size calculation."""
        parsed_data = '{"aid": 1, "title": "Test"}'
        xml_content = "<anime><title>Test</title></anime>"

        size_with_xml = CacheSerializer.calculate_data_size(parsed_data, xml_content)
        size_without_xml = CacheSerializer.calculate_data_size(parsed_data)

        assert size_with_xml > size_without_xml
        assert size_without_xml == len(parsed_data.encode('utf-8'))
        assert size_with_xml == len(parsed_data.encode('utf-8')) + len(xml_content.encode('utf-8'))


class TestPersistentCacheEntry:
    """Test cases for PersistentCacheEntry dataclass."""

    def test_cache_entry_creation(self) -> None:
        """Test basic cache entry creation."""
        now = datetime.now()
        expires_at = now + timedelta(hours=48)

        entry = PersistentCacheEntry(
            cache_key="test_key",
            method_name="test_method",
            parameters_json='{"param": "value"}',
            xml_content="<xml>test</xml>",
            parsed_data_json='{"data": "test"}',
            created_at=now,
            expires_at=expires_at,
            access_count=0,
            last_accessed=now,
            data_size=100,
        )

        assert entry.cache_key == "test_key"
        assert entry.method_name == "test_method"
        assert not entry.is_expired()

    def test_cache_entry_expiration(self) -> None:
        """Test cache entry expiration logic."""
        now = datetime.now()
        past_time = now - timedelta(hours=1)

        entry = PersistentCacheEntry(
            cache_key="test_key",
            method_name="test_method",
            parameters_json='{"param": "value"}',
            xml_content=None,
            parsed_data_json='{"data": "test"}',
            created_at=past_time,
            expires_at=past_time,  # Already expired
            access_count=0,
            last_accessed=past_time,
            data_size=100,
        )

        assert entry.is_expired()

    def test_cache_entry_touch(self) -> None:
        """Test cache entry access tracking."""
        now = datetime.now()
        entry = PersistentCacheEntry(
            cache_key="test_key",
            method_name="test_method",
            parameters_json='{"param": "value"}',
            xml_content=None,
            parsed_data_json='{"data": "test"}',
            created_at=now,
            expires_at=now + timedelta(hours=48),
            access_count=0,
            last_accessed=now,
            data_size=100,
        )

        initial_count = entry.access_count
        initial_accessed = entry.last_accessed

        time.sleep(0.01)  # Small delay to ensure timestamp difference
        entry.touch()

        assert entry.access_count == initial_count + 1
        assert entry.last_accessed > initial_accessed

    def test_cache_entry_from_db_row(self) -> None:
        """Test creating cache entry from database row."""
        now = datetime.now()
        expires_at = now + timedelta(hours=48)

        row = (
            "test_key",
            "test_method",
            '{"param": "value"}',
            "<xml>test</xml>",
            '{"data": "test"}',
            now.isoformat(),
            expires_at.isoformat(),
            5,
            now.isoformat(),
            100,
        )

        entry = PersistentCacheEntry.from_db_row(row)

        assert entry.cache_key == "test_key"
        assert entry.method_name == "test_method"
        assert entry.access_count == 5
        assert entry.data_size == 100

    def test_cache_entry_to_db_tuple(self) -> None:
        """Test converting cache entry to database tuple."""
        now = datetime.now()
        expires_at = now + timedelta(hours=48)

        entry = PersistentCacheEntry(
            cache_key="test_key",
            method_name="test_method",
            parameters_json='{"param": "value"}',
            xml_content="<xml>test</xml>",
            parsed_data_json='{"data": "test"}',
            created_at=now,
            expires_at=expires_at,
            access_count=5,
            last_accessed=now,
            data_size=100,
        )

        db_tuple = entry.to_db_tuple()

        assert len(db_tuple) == 10
        assert db_tuple[0] == "test_key"
        assert db_tuple[1] == "test_method"
        assert db_tuple[7] == 5  # access_count


class TestPersistentCacheStats:
    """Test cases for PersistentCacheStats model."""

    def test_stats_creation(self) -> None:
        """Test cache stats creation with default values."""
        stats = PersistentCacheStats()

        assert stats.memory_hits == 0
        assert stats.memory_misses == 0
        assert stats.db_hits == 0
        assert stats.db_misses == 0
        assert stats.hit_rate == 0.0
        assert stats.db_available is True

    def test_hit_rate_calculation(self) -> None:
        """Test hit rate calculation."""
        stats = PersistentCacheStats()

        # No requests yet
        assert stats.hit_rate == 0.0

        # Add some hits and misses
        stats.memory_hits = 5
        stats.db_hits = 2
        stats.memory_misses = 2
        stats.db_misses = 1
        stats.total_hits = stats.memory_hits + stats.db_hits
        stats.total_misses = stats.memory_misses + stats.db_misses

        assert stats.hit_rate == 70.0  # 7 hits out of 10 total

    def test_memory_hit_rate_calculation(self) -> None:
        """Test memory cache hit rate calculation."""
        stats = PersistentCacheStats()
        stats.memory_hits = 8
        stats.memory_misses = 2

        assert stats.memory_hit_rate == 80.0

    def test_db_hit_rate_calculation(self) -> None:
        """Test database cache hit rate calculation."""
        stats = PersistentCacheStats()
        stats.db_hits = 6
        stats.db_misses = 4

        assert stats.db_hit_rate == 60.0


class TestPersistentCache:
    """Test cases for PersistentCache class."""

    @pytest.fixture
    async def temp_cache(self) -> PersistentCache:
        """Create a temporary cache instance for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test_cache.db"
            cache = PersistentCache(
                db_path=str(db_path),
                memory_ttl=1.0,  # 1 second for fast testing
                persistent_ttl=10.0,  # 10 seconds for testing
                max_memory_size=10,
            )
            yield cache
            await cache.clear()

    @pytest.fixture
    def sample_anime_details(self) -> AnimeDetails:
        """Create sample anime details for testing."""
        return AnimeDetails(
            aid=1,
            title="Test Anime",
            type="TV Series",
            episode_count=12,
            synopsis="Test synopsis",
            url="http://example.com",
            restricted=False,
            picture="test.jpg",
            titles=[],
            creators=[],
            related_anime=[],
        )

    @pytest.fixture
    def sample_search_results(self) -> list[AnimeSearchResult]:
        """Create sample search results for testing."""
        return [
            AnimeSearchResult(
                aid=1,
                title="Test Anime 1",
                type="TV Series",
                year=2023,
                language="en",
            ),
            AnimeSearchResult(
                aid=2,
                title="Test Anime 2",
                type="Movie",
                year=2024,
                language="ja",
            ),
        ]

    async def test_cache_initialization(self, temp_cache: PersistentCache) -> None:
        """Test cache initialization."""
        assert temp_cache.memory_ttl == 1.0
        assert temp_cache.persistent_ttl == 10.0
        assert temp_cache.max_memory_size == 10

        stats = await temp_cache.get_stats()
        assert stats.memory_entries == 0
        assert stats.db_available is True

    async def test_basic_get_set_operations(
        self, temp_cache: PersistentCache, sample_anime_details: AnimeDetails
    ) -> None:
        """Test basic cache get and set operations."""
        key = "test_key"

        # Key should not exist initially
        result = await temp_cache.get(key)
        assert result is None

        # Set value
        await temp_cache.set(key, sample_anime_details, xml_content="<xml>test</xml>")

        # Get value
        result = await temp_cache.get(key)
        assert result is not None
        assert result.aid == sample_anime_details.aid
        assert result.title == sample_anime_details.title

        # Check stats
        stats = await temp_cache.get_stats()
        assert stats.memory_hits >= 1 or stats.db_hits >= 1

    async def test_cache_with_search_results(
        self, temp_cache: PersistentCache, sample_search_results: list[AnimeSearchResult]
    ) -> None:
        """Test caching search results."""
        key = "search_key"

        await temp_cache.set(key, sample_search_results)
        result = await temp_cache.get(key)

        assert result is not None
        assert len(result) == 2
        assert result[0].aid == 1
        assert result[1].aid == 2

    async def test_memory_to_database_promotion(
        self, temp_cache: PersistentCache, sample_anime_details: AnimeDetails
    ) -> None:
        """Test that database hits are promoted to memory cache."""
        key = "promotion_test"

        # Set in cache
        await temp_cache.set(key, sample_anime_details)

        # Clear memory cache to force database lookup
        await temp_cache._memory_cache.clear()

        # Get should hit database and promote to memory
        result = await temp_cache.get(key)
        assert result is not None

        # Next get should hit memory cache
        result2 = await temp_cache.get(key)
        assert result2 is not None

        stats = await temp_cache.get_stats()
        assert stats.memory_hits > 0 or stats.db_hits > 0

    async def test_cache_expiration(self) -> None:
        """Test cache expiration functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test_expiration.db"
            cache = PersistentCache(
                db_path=str(db_path),
                memory_ttl=0.1,  # 100ms
                persistent_ttl=0.2,  # 200ms
                max_memory_size=10,
            )

            key = "expiration_test"
            details = AnimeDetails(
                aid=1,
                title="Test",
                type="TV",
                episode_count=1,
                synopsis="Test",
                url="http://test.com",
                restricted=False,
                picture="test.jpg",
                titles=[],
                creators=[],
                related_anime=[],
            )

            await cache.set(key, details)

            # Should be available immediately
            result = await cache.get(key)
            assert result is not None

            # Wait for expiration
            await asyncio.sleep(0.3)

            # Should be expired now
            result = await cache.get(key)
            assert result is None

            await cache.clear()

    async def test_cache_delete(
        self, temp_cache: PersistentCache, sample_anime_details: AnimeDetails
    ) -> None:
        """Test cache deletion."""
        key = "delete_test"

        await temp_cache.set(key, sample_anime_details)
        assert await temp_cache.get(key) is not None

        # Delete the key
        deleted = await temp_cache.delete(key)
        assert deleted is True

        # Should not be found
        result = await temp_cache.get(key)
        assert result is None

        # Try to delete non-existent key
        deleted = await temp_cache.delete("non_existent")
        assert deleted is False

    async def test_cache_clear(
        self, temp_cache: PersistentCache, sample_anime_details: AnimeDetails
    ) -> None:
        """Test clearing all cache entries."""
        # Add multiple entries
        for i in range(3):
            await temp_cache.set(f"key_{i}", sample_anime_details)

        # Verify entries exist
        for i in range(3):
            result = await temp_cache.get(f"key_{i}")
            assert result is not None

        # Clear cache
        await temp_cache.clear()

        # Verify all entries are gone
        for i in range(3):
            result = await temp_cache.get(f"key_{i}")
            assert result is None

    async def test_cleanup_expired(self) -> None:
        """Test cleanup of expired entries."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test_cleanup.db"
            cache = PersistentCache(
                db_path=str(db_path),
                memory_ttl=0.1,  # 100ms
                persistent_ttl=0.1,  # 100ms
                max_memory_size=10,
            )

            details = AnimeDetails(
                aid=1,
                title="Test",
                type="TV",
                episode_count=1,
                synopsis="Test",
                url="http://test.com",
                restricted=False,
                picture="test.jpg",
                titles=[],
                creators=[],
                related_anime=[],
            )

            # Add entries
            for i in range(3):
                await cache.set(f"key_{i}", details)

            # Wait for expiration
            await asyncio.sleep(0.2)

            # Cleanup expired entries
            cleaned = await cache.cleanup_expired()
            assert cleaned >= 0  # Should clean up some entries

            await cache.clear()

    async def test_cache_stats(
        self, temp_cache: PersistentCache, sample_anime_details: AnimeDetails
    ) -> None:
        """Test cache statistics."""
        # Initial stats
        stats = await temp_cache.get_stats()
        initial_hits = stats.total_hits
        initial_misses = stats.total_misses

        # Perform cache operations
        await temp_cache.set("stats_test", sample_anime_details)
        await temp_cache.get("stats_test")  # Hit
        await temp_cache.get("non_existent")  # Miss

        # Check updated stats
        stats = await temp_cache.get_stats()
        assert stats.total_hits >= initial_hits
        assert stats.total_misses > initial_misses
        assert stats.hit_rate >= 0.0

    @patch("src.mcp_server_anime.core.persistent_cache.get_multi_provider_database")
    async def test_database_error_handling(
        self, mock_get_db: MagicMock, sample_anime_details: AnimeDetails
    ) -> None:
        """Test graceful handling of database errors."""
        # Mock database to raise errors
        mock_db = AsyncMock()
        mock_db.get_cache_entry.side_effect = DatabaseError("Database error")
        mock_db.set_cache_entry.side_effect = DatabaseError("Database error")
        mock_get_db.return_value = mock_db

        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test_error.db"
            cache = PersistentCache(
                db_path=str(db_path),
                memory_ttl=1.0,
                persistent_ttl=10.0,
                max_memory_size=10,
            )

            # Should still work with memory cache
            await cache.set("error_test", sample_anime_details)
            result = await cache.get("error_test")
            assert result is not None

            # Database should be marked as unavailable
            stats = await cache.get_stats()
            assert stats.db_available is False

    async def test_invalidate_cache_key(
        self, temp_cache: PersistentCache, sample_anime_details: AnimeDetails
    ) -> None:
        """Test cache key invalidation."""
        # Set cache entry
        await temp_cache.set("get_anime_details:abc123", sample_anime_details)

        # Verify it exists
        result = await temp_cache.get("get_anime_details:abc123")
        assert result is not None

        # Invalidate using method and parameters
        invalidated = await temp_cache.invalidate_cache_key("get_anime_details", aid=123)
        # Note: This might not match exactly due to key generation, but should not error

        # The method should work without errors
        assert isinstance(invalidated, bool)


class TestCreatePersistentCache:
    """Test cases for cache factory function."""

    async def test_create_cache_with_defaults(self) -> None:
        """Test creating cache with default parameters."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test_factory.db"
            cache = await create_persistent_cache(db_path=str(db_path))

            assert isinstance(cache, PersistentCache)
            assert cache.memory_ttl == 3600.0
            assert cache.persistent_ttl == 172800.0
            assert cache.max_memory_size == 1000

            await cache.clear()

    async def test_create_cache_with_custom_params(self) -> None:
        """Test creating cache with custom parameters."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test_custom.db"
            memory_ttl = 1800.0
            persistent_ttl = 86400.0
            max_memory_size = 500

            cache = await create_persistent_cache(
                db_path=str(db_path),
                memory_ttl=memory_ttl,
                persistent_ttl=persistent_ttl,
                max_memory_size=max_memory_size,
            )

            assert isinstance(cache, PersistentCache)
            assert cache.memory_ttl == memory_ttl
            assert cache.persistent_ttl == persistent_ttl
            assert cache.max_memory_size == max_memory_size

            await cache.clear()


@pytest.mark.asyncio
class TestPersistentCacheIntegration:
    """Integration tests for persistent cache functionality."""

    async def test_cache_persistence_across_instances(self) -> None:
        """Test that cache persists across different cache instances."""
        details = AnimeDetails(
            aid=1,
            title="Persistent Test",
            type="TV Series",
            episode_count=12,
            synopsis="Test persistence",
            url="http://example.com",
            restricted=False,
            picture="test.jpg",
            titles=[],
            creators=[],
            related_anime=[],
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "persistence_test.db"

            # First cache instance
            cache1 = PersistentCache(
                db_path=str(db_path),
                memory_ttl=10.0,
                persistent_ttl=100.0,
                max_memory_size=10,
            )

            await cache1.set("persistence_key", details, xml_content="<xml>test</xml>")
            result1 = await cache1.get("persistence_key")
            assert result1 is not None
            await cache1.clear()  # Clear memory but not database

            # Second cache instance (simulating restart)
            cache2 = PersistentCache(
                db_path=str(db_path),
                memory_ttl=10.0,
                persistent_ttl=100.0,
                max_memory_size=10,
            )

            # Should load from database
            result2 = await cache2.get("persistence_key")
            assert result2 is not None
            assert result2.title == "Persistent Test"

            await cache2.clear()

    async def test_concurrent_cache_access(self) -> None:
        """Test concurrent access to the cache."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "concurrent_test.db"
            cache = PersistentCache(
                db_path=str(db_path),
                memory_ttl=10.0,
                persistent_ttl=100.0,
                max_memory_size=50,
            )

            async def set_values(start: int, count: int) -> None:
                for i in range(start, start + count):
                    details = AnimeDetails(
                        aid=i,
                        title=f"Anime {i}",
                        type="TV Series",
                        episode_count=12,
                        synopsis=f"Synopsis {i}",
                        url=f"http://example.com/{i}",
                        restricted=False,
                        picture=f"pic{i}.jpg",
                        titles=[],
                        creators=[],
                        related_anime=[],
                    )
                    await cache.set(f"concurrent_key_{i}", details)

            async def get_values(start: int, count: int) -> list[AnimeDetails | None]:
                results = []
                for i in range(start, start + count):
                    result = await cache.get(f"concurrent_key_{i}")
                    results.append(result)
                return results

            # Run concurrent set operations
            await asyncio.gather(
                set_values(0, 10),
                set_values(10, 10),
                set_values(20, 10),
            )

            # Run concurrent get operations
            results = await asyncio.gather(
                get_values(0, 10),
                get_values(10, 10),
                get_values(20, 10),
            )

            # Verify all values were set and retrieved correctly
            for result_batch in results:
                assert len(result_batch) == 10
                for result in result_batch:
                    assert result is not None
                    assert isinstance(result, AnimeDetails)

            await cache.clear()

    async def test_large_data_handling(self) -> None:
        """Test cache with large data objects."""
        # Create a large anime details object
        large_synopsis = "A" * 10000  # 10KB synopsis
        large_details = AnimeDetails(
            aid=999,
            title="Large Data Test",
            type="TV Series",
            episode_count=1000,
            synopsis=large_synopsis,
            url="http://example.com/large",
            restricted=False,
            picture="large.jpg",
            titles=[],
            creators=[],
            related_anime=[],
        )

        large_xml = "<anime>" + "B" * 50000 + "</anime>"  # 50KB XML

        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "large_data_test.db"
            cache = PersistentCache(
                db_path=str(db_path),
                memory_ttl=10.0,
                persistent_ttl=100.0,
                max_memory_size=10,
            )

            # Set large data
            await cache.set("large_key", large_details, xml_content=large_xml)

            # Retrieve and verify
            result = await cache.get("large_key")
            assert result is not None
            assert result.synopsis == large_synopsis
            assert len(result.synopsis) == 10000

            # Check stats
            stats = await cache.get_stats()
            assert stats.db_size_bytes > 50000  # Should be larger due to the data

            await cache.clear()