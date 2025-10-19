"""Data models for persistent cache system.

This module defines the data structures used for storing and retrieving
cached anime data in the SQLite database with TTL support.
"""

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from pydantic import BaseModel, Field

from .logging_config import get_logger
from .models import AnimeDetails, AnimeSearchResult

logger = get_logger(__name__)


@dataclass
class PersistentCacheEntry:
    """Represents a cache entry in the database.
    
    This class encapsulates all the metadata and data for a single cache entry,
    including both the raw XML content and parsed results for debugging and
    potential re-parsing scenarios.
    
    Attributes:
        cache_key: Unique identifier for the cache entry
        provider_source: Source provider name (e.g., "anidb", "anilist")
        method_name: Name of the method that generated this cache entry
        parameters_json: JSON string of the parameters used for the original request
        source_data: Raw source data (XML for AniDB, JSON for AniList, etc.)
        parsed_data_json: JSON serialized parsed data (AnimeDetails or search results)
        created_at: Timestamp when the entry was created
        expires_at: Timestamp when the entry expires
        access_count: Number of times this entry has been accessed
        last_accessed: Timestamp of the most recent access
        data_size: Size of the cached data in bytes
    """
    
    cache_key: str
    provider_source: str
    method_name: str
    parameters_json: str
    source_data: str | None
    parsed_data_json: str
    created_at: datetime
    expires_at: datetime
    access_count: int
    last_accessed: datetime
    data_size: int

    def is_expired(self) -> bool:
        """Check if the cache entry has expired.
        
        Returns:
            True if the entry has expired, False otherwise
        """
        return datetime.now() >= self.expires_at

    def time_to_expiry(self) -> timedelta:
        """Get the time remaining until expiry.
        
        Returns:
            Timedelta until expiry (negative if already expired)
        """
        return self.expires_at - datetime.now()

    def age(self) -> timedelta:
        """Get the age of the cache entry.
        
        Returns:
            Timedelta since creation
        """
        return datetime.now() - self.created_at

    def touch(self) -> None:
        """Update access statistics for the cache entry."""
        self.access_count += 1
        self.last_accessed = datetime.now()

    @classmethod
    def from_db_row(cls, row: tuple) -> "PersistentCacheEntry":
        """Create a PersistentCacheEntry from a database row.
        
        Args:
            row: Database row tuple with cache entry data
            
        Returns:
            PersistentCacheEntry instance
        """
        (
            cache_key,
            provider_source,
            method_name,
            parameters_json,
            source_data,
            parsed_data_json,
            created_at_str,
            expires_at_str,
            access_count,
            last_accessed_str,
            data_size,
        ) = row

        return cls(
            cache_key=cache_key,
            provider_source=provider_source,
            method_name=method_name,
            parameters_json=parameters_json,
            source_data=source_data,
            parsed_data_json=parsed_data_json,
            created_at=datetime.fromisoformat(created_at_str),
            expires_at=datetime.fromisoformat(expires_at_str),
            access_count=access_count,
            last_accessed=datetime.fromisoformat(last_accessed_str),
            data_size=data_size,
        )

    def to_db_tuple(self) -> tuple:
        """Convert the cache entry to a database tuple for insertion.
        
        Returns:
            Tuple suitable for database insertion
        """
        return (
            self.cache_key,
            self.provider_source,
            self.method_name,
            self.parameters_json,
            self.source_data,
            self.parsed_data_json,
            self.created_at.isoformat(),
            self.expires_at.isoformat(),
            self.access_count,
            self.last_accessed.isoformat(),
            self.data_size,
        )


class PersistentCacheStats(BaseModel):
    """Statistics about persistent cache performance and usage.
    
    This class provides comprehensive metrics for monitoring cache effectiveness,
    including separate statistics for memory and database cache layers.
    
    Attributes:
        memory_hits: Number of cache hits from memory cache
        memory_misses: Number of cache misses from memory cache
        memory_entries: Current number of entries in memory cache
        db_hits: Number of cache hits from database cache
        db_misses: Number of cache misses from database cache
        db_entries: Current number of entries in database cache
        total_hits: Combined hits from both cache layers
        total_misses: Combined misses from both cache layers
        hit_rate: Overall cache hit rate as a percentage
        avg_memory_access_time: Average access time for memory cache in milliseconds
        avg_db_access_time: Average access time for database cache in milliseconds
        db_size_bytes: Size of the database cache in bytes
        memory_size_estimate: Estimated size of memory cache in bytes
        db_available: Whether database cache is available and functioning
    """
    
    # Memory cache statistics
    memory_hits: int = 0
    memory_misses: int = 0
    memory_entries: int = 0
    
    # Database cache statistics
    db_hits: int = 0
    db_misses: int = 0
    db_entries: int = 0
    
    # Combined statistics
    total_hits: int = 0
    total_misses: int = 0
    
    # Performance metrics
    avg_memory_access_time: float = 0.0  # milliseconds
    avg_db_access_time: float = 0.0  # milliseconds
    
    # Storage metrics
    db_size_bytes: int = 0
    memory_size_estimate: int = 0
    
    # Status indicators
    db_available: bool = True

    @property
    def hit_rate(self) -> float:
        """Calculate overall cache hit rate as a percentage.
        
        Returns:
            Hit rate percentage (0.0 to 100.0)
        """
        total_requests = self.total_hits + self.total_misses
        if total_requests == 0:
            return 0.0
        return (self.total_hits / total_requests) * 100.0

    @property
    def memory_hit_rate(self) -> float:
        """Calculate memory cache hit rate as a percentage.
        
        Returns:
            Memory cache hit rate percentage (0.0 to 100.0)
        """
        memory_requests = self.memory_hits + self.memory_misses
        if memory_requests == 0:
            return 0.0
        return (self.memory_hits / memory_requests) * 100.0

    @property
    def db_hit_rate(self) -> float:
        """Calculate database cache hit rate as a percentage.
        
        Returns:
            Database cache hit rate percentage (0.0 to 100.0)
        """
        db_requests = self.db_hits + self.db_misses
        if db_requests == 0:
            return 0.0
        return (self.db_hits / db_requests) * 100.0


class CacheSerializer:
    """Utility class for serializing and deserializing cache data.
    
    This class handles the conversion between Python objects and JSON strings
    for storage in the database, with special handling for anime-specific data types.
    """

    @staticmethod
    def serialize_anime_details(details: AnimeDetails) -> str:
        """Serialize AnimeDetails object to JSON string.
        
        Args:
            details: AnimeDetails object to serialize
            
        Returns:
            JSON string representation of the anime details
            
        Raises:
            ValueError: If serialization fails
        """
        try:
            return details.model_dump_json()
        except Exception as e:
            logger.error(f"Failed to serialize AnimeDetails: {e}")
            raise ValueError(f"Failed to serialize AnimeDetails: {e}") from e

    @staticmethod
    def deserialize_anime_details(json_str: str) -> AnimeDetails:
        """Deserialize JSON string to AnimeDetails object.
        
        Args:
            json_str: JSON string to deserialize
            
        Returns:
            AnimeDetails object
            
        Raises:
            ValueError: If deserialization fails
        """
        try:
            return AnimeDetails.model_validate_json(json_str)
        except Exception as e:
            logger.error(f"Failed to deserialize AnimeDetails: {e}")
            raise ValueError(f"Failed to deserialize AnimeDetails: {e}") from e

    @staticmethod
    def serialize_search_results(results: list[AnimeSearchResult]) -> str:
        """Serialize list of AnimeSearchResult objects to JSON string.
        
        Args:
            results: List of AnimeSearchResult objects to serialize
            
        Returns:
            JSON string representation of the search results
            
        Raises:
            ValueError: If serialization fails
        """
        try:
            # Convert to list of dictionaries and then to JSON
            results_data = [result.model_dump() for result in results]
            return json.dumps(results_data, ensure_ascii=False, separators=(',', ':'))
        except Exception as e:
            logger.error(f"Failed to serialize search results: {e}")
            raise ValueError(f"Failed to serialize search results: {e}") from e

    @staticmethod
    def deserialize_search_results(json_str: str) -> list[AnimeSearchResult]:
        """Deserialize JSON string to list of AnimeSearchResult objects.
        
        Args:
            json_str: JSON string to deserialize
            
        Returns:
            List of AnimeSearchResult objects
            
        Raises:
            ValueError: If deserialization fails
        """
        try:
            results_data = json.loads(json_str)
            return [AnimeSearchResult.model_validate(result) for result in results_data]
        except Exception as e:
            logger.error(f"Failed to deserialize search results: {e}")
            raise ValueError(f"Failed to deserialize search results: {e}") from e

    @staticmethod
    def serialize_parameters(params: dict[str, Any]) -> str:
        """Serialize parameters dictionary to JSON string.
        
        Args:
            params: Parameters dictionary to serialize
            
        Returns:
            JSON string representation of the parameters
            
        Raises:
            ValueError: If serialization fails
        """
        try:
            return json.dumps(params, sort_keys=True, separators=(',', ':'))
        except Exception as e:
            logger.error(f"Failed to serialize parameters: {e}")
            raise ValueError(f"Failed to serialize parameters: {e}") from e

    @staticmethod
    def deserialize_parameters(json_str: str) -> dict[str, Any]:
        """Deserialize JSON string to parameters dictionary.
        
        Args:
            json_str: JSON string to deserialize
            
        Returns:
            Parameters dictionary
            
        Raises:
            ValueError: If deserialization fails
        """
        try:
            return json.loads(json_str)
        except Exception as e:
            logger.error(f"Failed to deserialize parameters: {e}")
            raise ValueError(f"Failed to deserialize parameters: {e}") from e

    @staticmethod
    def calculate_data_size(
        parsed_data_json: str, source_data: str | None = None
    ) -> int:
        """Calculate the total size of cached data in bytes.
        
        Args:
            parsed_data_json: JSON string of parsed data
            source_data: Optional raw source data (XML, JSON, etc.)
            
        Returns:
            Total size in bytes
        """
        size = len(parsed_data_json.encode('utf-8'))
        if source_data:
            size += len(source_data.encode('utf-8'))
        return size