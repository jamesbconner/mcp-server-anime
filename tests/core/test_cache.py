"""Unit tests for the caching mechanism.

This module tests the TTL cache implementation, including cache entry management,
TTL expiration, size-based eviction, and cache key generation.
"""

import asyncio
import time

import pytest

from src.mcp_server_anime.core.cache import (
    CacheEntry,
    CacheStats,
    TTLCache,
    create_cache,
    generate_cache_key,
)


class TestCacheEntry:
    """Test cases for CacheEntry class."""

    def test_cache_entry_creation(self) -> None:
        """Test basic cache entry creation."""
        value = {"test": "data"}
        ttl = 3600.0

        entry = CacheEntry(value=value, ttl=ttl)

        assert entry.value == value
        assert entry.ttl == ttl
        assert entry.access_count == 0
        assert isinstance(entry.created_at, float)
        assert isinstance(entry.last_accessed, float)
        assert not entry.is_expired()

    def test_cache_entry_expiration(self) -> None:
        """Test cache entry expiration logic."""
        value = {"test": "data"}
        ttl = 0.1  # 100ms TTL

        entry = CacheEntry(value=value, ttl=ttl)
        assert not entry.is_expired()

        # Wait for expiration
        time.sleep(0.15)
        assert entry.is_expired()

    def test_cache_entry_touch(self) -> None:
        """Test cache entry access tracking."""
        entry = CacheEntry(value="test", ttl=3600.0)

        initial_access_count = entry.access_count
        initial_last_accessed = entry.last_accessed

        # Small delay to ensure timestamp difference
        time.sleep(0.01)
        entry.touch()

        assert entry.access_count == initial_access_count + 1
        assert entry.last_accessed > initial_last_accessed

    def test_cache_entry_age_and_time_to_expiry(self) -> None:
        """Test cache entry age and time to expiry calculations."""
        ttl = 10.0
        entry = CacheEntry(value="test", ttl=ttl)

        # Age should be close to 0 initially
        assert 0 <= entry.age() < 0.1

        # Time to expiry should be close to TTL initially
        assert ttl - 0.1 < entry.time_to_expiry() <= ttl

        # Wait a bit and check again
        time.sleep(0.1)
        assert 0.1 <= entry.age() < 0.2
        assert ttl - 0.2 < entry.time_to_expiry() <= ttl - 0.1


class TestCacheStats:
    """Test cases for CacheStats class."""

    def test_cache_stats_creation(self) -> None:
        """Test cache stats creation with default values."""
        stats = CacheStats()

        assert stats.hits == 0
        assert stats.misses == 0
        assert stats.evictions == 0
        assert stats.expirations == 0
        assert stats.total_entries == 0
        assert stats.max_size == 0
        assert stats.hit_rate == 0.0

    def test_hit_rate_calculation(self) -> None:
        """Test hit rate calculation."""
        stats = CacheStats()

        # No requests yet
        assert stats.hit_rate == 0.0

        # Add some hits and misses
        stats.hits = 7
        stats.misses = 3
        assert stats.hit_rate == 70.0

        # All hits
        stats.hits = 10
        stats.misses = 0
        assert stats.hit_rate == 100.0

        # All misses
        stats.hits = 0
        stats.misses = 5
        assert stats.hit_rate == 0.0


class TestTTLCache:
    """Test cases for TTLCache class."""

    @pytest.fixture
    def cache(self) -> TTLCache:
        """Create a test cache instance."""
        return TTLCache(max_size=3, default_ttl=1.0)

    async def test_cache_initialization(self) -> None:
        """Test cache initialization."""
        max_size = 100
        default_ttl = 3600.0

        cache = TTLCache(max_size=max_size, default_ttl=default_ttl)

        assert cache.max_size == max_size
        assert cache.default_ttl == default_ttl
        assert cache.size() == 0

        stats = await cache.get_stats()
        assert stats.max_size == max_size
        assert stats.total_entries == 0

    async def test_basic_get_set_operations(self, cache: TTLCache) -> None:
        """Test basic cache get and set operations."""
        key = "test_key"
        value = {"data": "test_value"}

        # Key should not exist initially
        result = await cache.get(key)
        assert result is None

        # Set value
        await cache.set(key, value)
        assert cache.size() == 1

        # Get value
        result = await cache.get(key)
        assert result == value

        # Check stats
        stats = await cache.get_stats()
        assert stats.hits == 1
        assert stats.misses == 1
        assert stats.total_entries == 1

    async def test_ttl_expiration(self) -> None:
        """Test TTL-based expiration."""
        cache = TTLCache(max_size=10, default_ttl=0.1)  # 100ms TTL

        key = "expire_test"
        value = "test_value"

        await cache.set(key, value)

        # Should be available immediately
        result = await cache.get(key)
        assert result == value

        # Wait for expiration
        await asyncio.sleep(0.15)

        # Should be expired now
        result = await cache.get(key)
        assert result is None

        # Check that expired entry was removed
        assert cache.size() == 0

        stats = await cache.get_stats()
        assert stats.expirations == 1

    async def test_custom_ttl(self, cache: TTLCache) -> None:
        """Test setting custom TTL for individual entries."""
        key1 = "short_ttl"
        key2 = "long_ttl"
        value = "test_value"

        # Set with short TTL
        await cache.set(key1, value, ttl=0.1)
        # Set with longer TTL
        await cache.set(key2, value, ttl=1.0)

        # Both should be available initially
        assert await cache.get(key1) == value
        assert await cache.get(key2) == value

        # Wait for short TTL to expire
        await asyncio.sleep(0.15)

        # Short TTL should be expired, long TTL should still be available
        assert await cache.get(key1) is None
        assert await cache.get(key2) == value

    async def test_size_based_eviction(self, cache: TTLCache) -> None:
        """Test LRU eviction when cache reaches max size."""
        import asyncio

        # Fill cache to max capacity (cache max_size is 3) with delays to ensure different timestamps
        await cache.set("key_0", "value_0")
        await asyncio.sleep(0.01)
        await cache.set("key_1", "value_1")
        await asyncio.sleep(0.01)
        await cache.set("key_2", "value_2")

        assert cache.size() == cache.max_size

        # Access key_0 to make it recently used (this updates last_accessed)
        await asyncio.sleep(0.01)  # Ensure access time is different
        result = await cache.get("key_0")
        assert result == "value_0"

        # Access key_2 as well to make key_1 the LRU
        await asyncio.sleep(0.01)
        result = await cache.get("key_2")
        assert result == "value_2"

        # Now key_1 should be the LRU (oldest last_accessed time)
        await asyncio.sleep(0.01)

        # Add one more item, should evict LRU (key_1)
        await cache.set("new_key", "new_value")

        assert cache.size() == cache.max_size
        assert await cache.get("key_0") is not None  # Recently accessed, should remain
        assert await cache.get("key_1") is None  # Should be evicted (LRU)
        assert await cache.get("key_2") is not None  # Recently accessed, should remain
        assert await cache.get("new_key") is not None  # New item should be present

        stats = await cache.get_stats()
        assert stats.evictions == 1

    async def test_delete_operation(self, cache: TTLCache) -> None:
        """Test manual deletion of cache entries."""
        key = "delete_test"
        value = "test_value"

        await cache.set(key, value)
        assert await cache.get(key) == value

        # Delete the key
        deleted = await cache.delete(key)
        assert deleted is True
        assert cache.size() == 0

        # Try to get deleted key
        result = await cache.get(key)
        assert result is None

        # Try to delete non-existent key
        deleted = await cache.delete("non_existent")
        assert deleted is False

    async def test_clear_operation(self, cache: TTLCache) -> None:
        """Test clearing all cache entries."""
        # Add multiple entries
        for i in range(3):
            await cache.set(f"key_{i}", f"value_{i}")

        assert cache.size() == 3

        # Clear cache
        await cache.clear()

        assert cache.size() == 0

        # Verify all entries are gone
        for i in range(3):
            result = await cache.get(f"key_{i}")
            assert result is None

    async def test_cleanup_expired(self) -> None:
        """Test manual cleanup of expired entries."""
        cache = TTLCache(max_size=10, default_ttl=0.1)

        # Add entries with short TTL
        for i in range(3):
            await cache.set(f"key_{i}", f"value_{i}")

        assert cache.size() == 3

        # Wait for expiration
        await asyncio.sleep(0.15)

        # Cleanup expired entries
        expired_count = await cache.cleanup_expired()

        assert expired_count == 3
        assert cache.size() == 0

        stats = await cache.get_stats()
        assert stats.expirations == 3

    async def test_get_keys(self, cache: TTLCache) -> None:
        """Test getting all cache keys."""
        keys = ["key1", "key2", "key3"]

        # Add entries
        for key in keys:
            await cache.set(key, f"value_{key}")

        # Get all keys
        cache_keys = await cache.get_keys()

        assert len(cache_keys) == len(keys)
        assert set(cache_keys) == set(keys)

    async def test_concurrent_access(self) -> None:
        """Test concurrent cache operations."""
        cache = TTLCache(max_size=100, default_ttl=1.0)

        async def set_values(start: int, count: int) -> None:
            for i in range(start, start + count):
                await cache.set(f"key_{i}", f"value_{i}")

        async def get_values(start: int, count: int) -> list[str | None]:
            results = []
            for i in range(start, start + count):
                result = await cache.get(f"key_{i}")
                results.append(result)
            return results

        # Run concurrent set operations
        await asyncio.gather(set_values(0, 10), set_values(10, 10), set_values(20, 10))

        assert cache.size() == 30

        # Run concurrent get operations
        results = await asyncio.gather(
            get_values(0, 10), get_values(10, 10), get_values(20, 10)
        )

        # Verify all values were retrieved correctly
        for result_batch in results:
            assert len(result_batch) == 10
            assert all(result is not None for result in result_batch)


class TestCacheKeyGeneration:
    """Test cases for cache key generation."""

    def test_basic_key_generation(self) -> None:
        """Test basic cache key generation."""
        method = "test_method"
        params = {"param1": "value1", "param2": 42}

        key = generate_cache_key(method, **params)

        assert isinstance(key, str)
        assert key.startswith(f"{method}:")
        assert len(key) > len(method) + 1

    def test_key_consistency(self) -> None:
        """Test that identical parameters produce identical keys."""
        method = "search_anime"

        key1 = generate_cache_key(method, query="evangelion", limit=10)
        key2 = generate_cache_key(method, query="evangelion", limit=10)

        assert key1 == key2

    def test_parameter_order_independence(self) -> None:
        """Test that parameter order doesn't affect key generation."""
        method = "search_anime"

        key1 = generate_cache_key(method, query="evangelion", limit=10, type="tv")
        key2 = generate_cache_key(method, limit=10, type="tv", query="evangelion")
        key3 = generate_cache_key(method, type="tv", query="evangelion", limit=10)

        assert key1 == key2 == key3

    def test_different_parameters_different_keys(self) -> None:
        """Test that different parameters produce different keys."""
        method = "search_anime"

        key1 = generate_cache_key(method, query="evangelion", limit=10)
        key2 = generate_cache_key(method, query="evangelion", limit=20)
        key3 = generate_cache_key(method, query="cowboy bebop", limit=10)

        assert key1 != key2
        assert key1 != key3
        assert key2 != key3

    def test_different_methods_different_keys(self) -> None:
        """Test that different methods produce different keys."""
        params = {"aid": 1}

        key1 = generate_cache_key("get_anime_details", **params)
        key2 = generate_cache_key("get_anime_info", **params)

        assert key1 != key2

    def test_complex_parameter_types(self) -> None:
        """Test key generation with complex parameter types."""
        method = "complex_method"

        # Test with various data types
        key1 = generate_cache_key(
            method,
            string_param="test",
            int_param=42,
            float_param=3.14,
            bool_param=True,
            list_param=[1, 2, 3],
            dict_param={"nested": "value"},
        )

        key2 = generate_cache_key(
            method,
            string_param="test",
            int_param=42,
            float_param=3.14,
            bool_param=True,
            list_param=[1, 2, 3],
            dict_param={"nested": "value"},
        )

        assert key1 == key2

    def test_none_parameters(self) -> None:
        """Test key generation with None parameters."""
        method = "test_method"

        key1 = generate_cache_key(method, param1="value", param2=None)
        key2 = generate_cache_key(method, param1="value", param2=None)
        key3 = generate_cache_key(method, param1="value", param2="other")

        assert key1 == key2
        assert key1 != key3


class TestCreateCache:
    """Test cases for cache factory function."""

    async def test_create_cache_with_defaults(self) -> None:
        """Test creating cache with default parameters."""
        cache = await create_cache()

        assert isinstance(cache, TTLCache)
        assert cache.max_size == 1000
        assert cache.default_ttl == 3600.0

    async def test_create_cache_with_custom_params(self) -> None:
        """Test creating cache with custom parameters."""
        max_size = 500
        default_ttl = 1800.0

        cache = await create_cache(max_size=max_size, default_ttl=default_ttl)

        assert isinstance(cache, TTLCache)
        assert cache.max_size == max_size
        assert cache.default_ttl == default_ttl


@pytest.mark.asyncio
class TestCacheIntegration:
    """Integration tests for cache functionality."""

    async def test_cache_with_real_data_structures(self) -> None:
        """Test cache with realistic data structures."""
        cache = TTLCache(max_size=10, default_ttl=1.0)

        # Simulate anime search results
        search_results = [
            {
                "aid": 1,
                "title": "Neon Genesis Evangelion",
                "type": "TV Series",
                "year": 1995,
            },
            {"aid": 2, "title": "Cowboy Bebop", "type": "TV Series", "year": 1998},
        ]

        # Simulate anime details
        anime_details = {
            "aid": 1,
            "title": "Neon Genesis Evangelion",
            "type": "TV Series",
            "episode_count": 26,
            "synopsis": "A mecha anime series...",
            "creators": [{"name": "Hideaki Anno", "type": "Director"}],
        }

        # Cache the data
        search_key = generate_cache_key("search_anime", query="evangelion", limit=10)
        details_key = generate_cache_key("get_anime_details", aid=1)

        await cache.set(search_key, search_results)
        await cache.set(details_key, anime_details)

        # Retrieve and verify
        cached_search = await cache.get(search_key)
        cached_details = await cache.get(details_key)

        assert cached_search == search_results
        assert cached_details == anime_details

        # Verify cache stats
        stats = await cache.get_stats()
        assert stats.hits == 2
        assert stats.total_entries == 2

    async def test_cache_performance_under_load(self) -> None:
        """Test cache performance with many operations."""
        cache = TTLCache(max_size=1000, default_ttl=10.0)

        # Perform many set operations
        start_time = time.time()
        for i in range(100):
            key = generate_cache_key("test_method", id=i, type="performance")
            await cache.set(key, {"id": i, "data": f"test_data_{i}"})
        set_time = time.time() - start_time

        # Perform many get operations
        start_time = time.time()
        for i in range(100):
            key = generate_cache_key("test_method", id=i, type="performance")
            result = await cache.get(key)
            assert result is not None
        get_time = time.time() - start_time

        # Performance should be reasonable (less than 1 second for 100 operations)
        assert set_time < 1.0
        assert get_time < 1.0

        # Verify final state
        assert cache.size() == 100
        stats = await cache.get_stats()
        assert stats.hits == 100
        assert stats.total_entries == 100
