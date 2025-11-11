"""Search transaction logging system for analytics and monitoring.

This module provides comprehensive logging of all search operations across providers
for usage analytics, performance monitoring, and system optimization.
"""

import asyncio
import sqlite3
from datetime import datetime, timedelta
from typing import Any

from .exceptions import DatabaseError
from .logging_config import get_logger
from .multi_provider_db import get_multi_provider_database

logger = get_logger(__name__)


class TransactionLogger:
    """Logs and analyzes search transactions for monitoring and analytics."""

    def __init__(self, db_path: str | None = None):
        """Initialize the transaction logger.

        Args:
            db_path: Optional database path (uses default multi-provider DB if None)
        """
        self.db = get_multi_provider_database(db_path)
        self._lock = asyncio.Lock()

    async def log_search(
        self,
        provider: str,
        query: str,
        result_count: int,
        response_time_ms: float,
        client_id: str | None = None,
    ) -> None:
        """Log a search transaction.

        Args:
            provider: Name of the provider used for search
            query: Search query string
            result_count: Number of results returned
            response_time_ms: Response time in milliseconds
            client_id: Optional client identifier for tracking

        Raises:
            DatabaseError: If logging fails (non-critical, won't prevent search)
        """
        async with self._lock:
            try:
                # Use the existing search_transactions table from multi-provider DB
                with sqlite3.connect(self.db.db_path) as conn:
                    conn.execute(
                        """
                        INSERT INTO search_transactions
                        (timestamp, provider, query, result_count, response_time_ms, client_identifier)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """,
                        (
                            datetime.now().isoformat(),
                            provider,
                            query,
                            result_count,
                            response_time_ms,
                            client_id,
                        ),
                    )
                    conn.commit()

                logger.debug(
                    f"Search transaction logged: {provider} query='{query}' "
                    f"results={result_count} time={response_time_ms}ms"
                )

            except sqlite3.Error as e:
                # Log error but don't raise - transaction logging should not break search
                logger.warning(f"Failed to log search transaction: {e}")

    async def get_search_stats(self, provider: str, hours: int = 24) -> dict[str, Any]:
        """Get search statistics for a provider.

        Args:
            provider: Provider name to get stats for
            hours: Number of hours to look back (default: 24)

        Returns:
            Dictionary with search statistics

        Raises:
            DatabaseError: If stats retrieval fails
        """
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)

            with sqlite3.connect(self.db.db_path) as conn:
                # Total searches
                cursor = conn.execute(
                    """
                    SELECT COUNT(*) FROM search_transactions
                    WHERE provider = ? AND timestamp >= ?
                """,
                    (provider, cutoff_time.isoformat()),
                )
                total_searches = cursor.fetchone()[0]

                # Average response time
                cursor = conn.execute(
                    """
                    SELECT AVG(response_time_ms) FROM search_transactions
                    WHERE provider = ? AND timestamp >= ?
                """,
                    (provider, cutoff_time.isoformat()),
                )
                avg_response_time = cursor.fetchone()[0] or 0

                # Average results per search
                cursor = conn.execute(
                    """
                    SELECT AVG(result_count) FROM search_transactions
                    WHERE provider = ? AND timestamp >= ?
                """,
                    (provider, cutoff_time.isoformat()),
                )
                avg_results = cursor.fetchone()[0] or 0

                # Most common queries
                cursor = conn.execute(
                    """
                    SELECT query, COUNT(*) as count FROM search_transactions
                    WHERE provider = ? AND timestamp >= ?
                    GROUP BY query
                    ORDER BY count DESC
                    LIMIT 10
                """,
                    (provider, cutoff_time.isoformat()),
                )
                popular_queries = [
                    {"query": row[0], "count": row[1]} for row in cursor.fetchall()
                ]

                # Searches by hour
                cursor = conn.execute(
                    """
                    SELECT
                        strftime('%H', timestamp) as hour,
                        COUNT(*) as count,
                        AVG(response_time_ms) as avg_time
                    FROM search_transactions
                    WHERE provider = ? AND timestamp >= ?
                    GROUP BY hour
                    ORDER BY hour
                """,
                    (provider, cutoff_time.isoformat()),
                )
                hourly_stats = [
                    {
                        "hour": int(row[0]),
                        "searches": row[1],
                        "avg_response_time_ms": round(row[2], 2) if row[2] else 0,
                    }
                    for row in cursor.fetchall()
                ]

                # Performance distribution
                cursor = conn.execute(
                    """
                    SELECT
                        CASE
                            WHEN response_time_ms < 10 THEN 'excellent'
                            WHEN response_time_ms < 50 THEN 'good'
                            WHEN response_time_ms < 100 THEN 'fair'
                            ELSE 'poor'
                        END as performance,
                        COUNT(*) as count
                    FROM search_transactions
                    WHERE provider = ? AND timestamp >= ?
                    GROUP BY performance
                """,
                    (provider, cutoff_time.isoformat()),
                )
                performance_dist = {row[0]: row[1] for row in cursor.fetchall()}

                return {
                    "provider": provider,
                    "time_period_hours": hours,
                    "total_searches": total_searches,
                    "avg_response_time_ms": round(avg_response_time, 2),
                    "avg_results_per_search": round(avg_results, 1),
                    "popular_queries": popular_queries,
                    "hourly_distribution": hourly_stats,
                    "performance_distribution": performance_dist,
                    "generated_at": datetime.now().isoformat(),
                }

        except sqlite3.Error as e:
            raise DatabaseError(
                f"Failed to get search stats for {provider}: {e}"
            ) from e

    async def get_overall_stats(self, hours: int = 24) -> dict[str, Any]:
        """Get overall search statistics across all providers.

        Args:
            hours: Number of hours to look back (default: 24)

        Returns:
            Dictionary with overall statistics

        Raises:
            DatabaseError: If stats retrieval fails
        """
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)

            with sqlite3.connect(self.db.db_path) as conn:
                # Overall totals
                cursor = conn.execute(
                    """
                    SELECT
                        COUNT(*) as total_searches,
                        COUNT(DISTINCT provider) as active_providers,
                        AVG(response_time_ms) as avg_response_time,
                        AVG(result_count) as avg_results
                    FROM search_transactions
                    WHERE timestamp >= ?
                """,
                    (cutoff_time.isoformat(),),
                )

                row = cursor.fetchone()
                total_searches = row[0]
                active_providers = row[1]
                avg_response_time = row[2] or 0
                avg_results = row[3] or 0

                # Stats by provider
                cursor = conn.execute(
                    """
                    SELECT
                        provider,
                        COUNT(*) as searches,
                        AVG(response_time_ms) as avg_time,
                        AVG(result_count) as avg_results
                    FROM search_transactions
                    WHERE timestamp >= ?
                    GROUP BY provider
                    ORDER BY searches DESC
                """,
                    (cutoff_time.isoformat(),),
                )

                provider_stats = [
                    {
                        "provider": row[0],
                        "searches": row[1],
                        "avg_response_time_ms": round(row[2], 2) if row[2] else 0,
                        "avg_results": round(row[3], 1) if row[3] else 0,
                    }
                    for row in cursor.fetchall()
                ]

                # Recent activity (last 10 searches)
                cursor = conn.execute(
                    """
                    SELECT timestamp, provider, query, result_count, response_time_ms
                    FROM search_transactions
                    WHERE timestamp >= ?
                    ORDER BY timestamp DESC
                    LIMIT 10
                """,
                    (cutoff_time.isoformat(),),
                )

                recent_activity = [
                    {
                        "timestamp": row[0],
                        "provider": row[1],
                        "query": row[2],
                        "result_count": row[3],
                        "response_time_ms": row[4],
                    }
                    for row in cursor.fetchall()
                ]

                return {
                    "time_period_hours": hours,
                    "summary": {
                        "total_searches": total_searches,
                        "active_providers": active_providers,
                        "avg_response_time_ms": round(avg_response_time, 2),
                        "avg_results_per_search": round(avg_results, 1),
                    },
                    "by_provider": provider_stats,
                    "recent_activity": recent_activity,
                    "generated_at": datetime.now().isoformat(),
                }

        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to get overall search stats: {e}") from e

    async def cleanup_old_transactions(self, retention_days: int = 30) -> int:
        """Clean up old search transactions.

        Args:
            retention_days: Number of days to retain transactions

        Returns:
            Number of transactions deleted

        Raises:
            DatabaseError: If cleanup fails
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=retention_days)

            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.execute(
                    """
                    DELETE FROM search_transactions
                    WHERE created_at < ?
                """,
                    (cutoff_date.isoformat(),),
                )

                deleted_count = cursor.rowcount
                conn.commit()

                if deleted_count > 0:
                    logger.info(
                        f"Cleaned up {deleted_count} old search transactions (older than {retention_days} days)"
                    )

                return deleted_count

        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to cleanup old transactions: {e}") from e

    async def get_query_analytics(
        self, provider: str, hours: int = 24
    ) -> dict[str, Any]:
        """Get detailed query analytics for a provider.

        Args:
            provider: Provider name to analyze
            hours: Number of hours to look back

        Returns:
            Dictionary with query analytics
        """
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)

            with sqlite3.connect(self.db.db_path) as conn:
                # Query length distribution
                cursor = conn.execute(
                    """
                    SELECT
                        CASE
                            WHEN LENGTH(query) < 3 THEN 'short'
                            WHEN LENGTH(query) < 10 THEN 'medium'
                            ELSE 'long'
                        END as length_category,
                        COUNT(*) as count,
                        AVG(result_count) as avg_results
                    FROM search_transactions
                    WHERE provider = ? AND timestamp >= ?
                    GROUP BY length_category
                """,
                    (provider, cutoff_time.isoformat()),
                )

                length_dist = [
                    {
                        "category": row[0],
                        "count": row[1],
                        "avg_results": round(row[2], 1) if row[2] else 0,
                    }
                    for row in cursor.fetchall()
                ]

                # Zero result queries
                cursor = conn.execute(
                    """
                    SELECT query, COUNT(*) as count
                    FROM search_transactions
                    WHERE provider = ? AND timestamp >= ? AND result_count = 0
                    GROUP BY query
                    ORDER BY count DESC
                    LIMIT 10
                """,
                    (provider, cutoff_time.isoformat()),
                )

                zero_result_queries = [
                    {"query": row[0], "count": row[1]} for row in cursor.fetchall()
                ]

                # High result queries
                cursor = conn.execute(
                    """
                    SELECT query, AVG(result_count) as avg_results, COUNT(*) as searches
                    FROM search_transactions
                    WHERE provider = ? AND timestamp >= ? AND result_count > 0
                    GROUP BY query
                    HAVING searches >= 2
                    ORDER BY avg_results DESC
                    LIMIT 10
                """,
                    (provider, cutoff_time.isoformat()),
                )

                high_result_queries = [
                    {
                        "query": row[0],
                        "avg_results": round(row[1], 1),
                        "searches": row[2],
                    }
                    for row in cursor.fetchall()
                ]

                return {
                    "provider": provider,
                    "time_period_hours": hours,
                    "query_length_distribution": length_dist,
                    "zero_result_queries": zero_result_queries,
                    "high_result_queries": high_result_queries,
                    "generated_at": datetime.now().isoformat(),
                }

        except sqlite3.Error as e:
            raise DatabaseError(
                f"Failed to get query analytics for {provider}: {e}"
            ) from e

    async def get_performance_metrics(
        self, provider: str, hours: int = 24
    ) -> dict[str, Any]:
        """Get detailed performance metrics for a provider.

        Args:
            provider: Provider name to analyze
            hours: Number of hours to look back

        Returns:
            Dictionary with performance metrics
        """
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)

            with sqlite3.connect(self.db.db_path) as conn:
                # Response time percentiles
                cursor = conn.execute(
                    """
                    SELECT response_time_ms
                    FROM search_transactions
                    WHERE provider = ? AND timestamp >= ?
                    ORDER BY response_time_ms
                """,
                    (provider, cutoff_time.isoformat()),
                )

                response_times = [row[0] for row in cursor.fetchall()]

                if response_times:
                    count = len(response_times)
                    p50_idx = int(count * 0.5)
                    p90_idx = int(count * 0.9)
                    p95_idx = int(count * 0.95)
                    p99_idx = int(count * 0.99)

                    percentiles = {
                        "p50": response_times[p50_idx] if p50_idx < count else 0,
                        "p90": response_times[p90_idx] if p90_idx < count else 0,
                        "p95": response_times[p95_idx] if p95_idx < count else 0,
                        "p99": response_times[p99_idx] if p99_idx < count else 0,
                        "min": min(response_times),
                        "max": max(response_times),
                        "avg": sum(response_times) / count,
                    }
                else:
                    percentiles = {
                        "p50": 0,
                        "p90": 0,
                        "p95": 0,
                        "p99": 0,
                        "min": 0,
                        "max": 0,
                        "avg": 0,
                    }

                # SLA compliance (sub-100ms target)
                cursor = conn.execute(
                    """
                    SELECT
                        COUNT(CASE WHEN response_time_ms < 100 THEN 1 END) as under_100ms,
                        COUNT(*) as total
                    FROM search_transactions
                    WHERE provider = ? AND timestamp >= ?
                """,
                    (provider, cutoff_time.isoformat()),
                )

                row = cursor.fetchone()
                under_100ms = row[0]
                total = row[1]
                sla_compliance = (under_100ms / total * 100) if total > 0 else 0

                return {
                    "provider": provider,
                    "time_period_hours": hours,
                    "response_time_percentiles": percentiles,
                    "sla_compliance": {
                        "target_ms": 100,
                        "compliance_percentage": round(sla_compliance, 1),
                        "compliant_searches": under_100ms,
                        "total_searches": total,
                    },
                    "generated_at": datetime.now().isoformat(),
                }

        except sqlite3.Error as e:
            raise DatabaseError(
                f"Failed to get performance metrics for {provider}: {e}"
            ) from e


# Global transaction logger instance
_transaction_logger: TransactionLogger | None = None


def get_transaction_logger(db_path: str | None = None) -> TransactionLogger:
    """Get the global transaction logger instance.

    Args:
        db_path: Optional database path (only used for first call)

    Returns:
        TransactionLogger instance
    """
    global _transaction_logger
    if _transaction_logger is None:
        _transaction_logger = TransactionLogger(db_path)
    return _transaction_logger


async def log_search_transaction(
    provider: str,
    query: str,
    result_count: int,
    response_time_ms: float,
    client_id: str | None = None,
) -> None:
    """Convenience function to log a search transaction.

    Args:
        provider: Name of the provider used for search
        query: Search query string
        result_count: Number of results returned
        response_time_ms: Response time in milliseconds
        client_id: Optional client identifier for tracking
    """
    logger_instance = get_transaction_logger()
    await logger_instance.log_search(
        provider, query, result_count, response_time_ms, client_id
    )
