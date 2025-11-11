"""Database index optimization utilities and monitoring.

This module provides utilities for monitoring and optimizing database indexes
to ensure optimal search performance across all providers.
"""

import sqlite3
from datetime import datetime
from typing import Any

from .exceptions import DatabaseError
from .logging_config import get_logger
from .security import SecureQueryHelper, TableNameValidator

logger = get_logger(__name__)


class IndexOptimizer:
    """Utilities for database index optimization and monitoring."""

    def __init__(self, db_path: str):
        """Initialize index optimizer.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path

    def analyze_query_performance(
        self, provider_name: str, query: str
    ) -> dict[str, Any]:
        """Analyze query performance using EXPLAIN QUERY PLAN.

        Args:
            provider_name: Name of the provider
            query: SQL query to analyze

        Returns:
            Dictionary with query plan analysis

        Raises:
            DatabaseError: If analysis fails
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get query plan
                cursor = conn.execute(f"EXPLAIN QUERY PLAN {query}")
                query_plan = cursor.fetchall()

                # Analyze plan for index usage
                uses_index = any("USING INDEX" in str(row) for row in query_plan)
                table_scan = any("SCAN TABLE" in str(row) for row in query_plan)

                return {
                    "query": query,
                    "provider": provider_name,
                    "query_plan": [
                        {
                            "id": row[0],
                            "parent": row[1],
                            "notused": row[2],
                            "detail": row[3],
                        }
                        for row in query_plan
                    ],
                    "uses_index": uses_index,
                    "has_table_scan": table_scan,
                    "performance_rating": "good"
                    if uses_index and not table_scan
                    else "poor",
                    "analyzed_at": datetime.now().isoformat(),
                }

        except sqlite3.Error as e:
            raise DatabaseError(f"Query analysis failed: {e}") from e

    def get_index_usage_stats(self, provider_name: str) -> dict[str, Any]:
        """Get statistics about index usage for a provider.

        Args:
            provider_name: Name of the provider

        Returns:
            Dictionary with index usage statistics

        Raises:
            DatabaseError: If stats retrieval fails
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                titles_table = f"{provider_name}_titles"

                # Get table info
                cursor = conn.execute(f"PRAGMA table_info({titles_table})")
                columns = [row[1] for row in cursor.fetchall()]

                # Get index list
                cursor = conn.execute(f"PRAGMA index_list({titles_table})")
                indexes = cursor.fetchall()

                index_details = {}
                for index_info in indexes:
                    index_name = index_info[1]

                    # Get index info
                    cursor = conn.execute(f"PRAGMA index_info({index_name})")
                    index_columns = [row[2] for row in cursor.fetchall()]

                    index_details[index_name] = {
                        "unique": bool(index_info[2]),
                        "columns": index_columns,
                        "origin": index_info[
                            3
                        ],  # 'c' for CREATE INDEX, 'u' for UNIQUE, 'pk' for PRIMARY KEY
                    }

                return {
                    "provider": provider_name,
                    "table": titles_table,
                    "columns": columns,
                    "indexes": index_details,
                    "index_count": len(index_details),
                    "analyzed_at": datetime.now().isoformat(),
                }

        except sqlite3.Error as e:
            raise DatabaseError(f"Index stats retrieval failed: {e}") from e

    def benchmark_search_queries(
        self, provider_name: str, test_queries: list[str]
    ) -> dict[str, Any]:
        """Benchmark search query performance.

        Args:
            provider_name: Name of the provider
            test_queries: List of test queries to benchmark

        Returns:
            Dictionary with benchmark results

        Raises:
            DatabaseError: If benchmarking fails
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Validate table name for security
                titles_table = TableNameValidator.validate_table_name(
                    f"{provider_name}_titles", provider_name
                )
                benchmark_results = []

                for query_term in test_queries:
                    query_lower = query_term.lower()

                    # Test exact match query using secure query helper
                    start_time = datetime.now()
                    exact_query, exact_params = SecureQueryHelper.build_count_query(
                        titles_table, "title_normalized = ?"
                    )
                    cursor = conn.execute(exact_query, [query_lower] + exact_params)
                    exact_count = cursor.fetchone()[0]
                    exact_time = (datetime.now() - start_time).total_seconds() * 1000

                    # Test prefix match query using secure query helper
                    start_time = datetime.now()
                    prefix_query, prefix_params = SecureQueryHelper.build_count_query(
                        titles_table, "title_normalized LIKE ?"
                    )
                    cursor = conn.execute(
                        prefix_query, [f"{query_lower}%"] + prefix_params
                    )
                    prefix_count = cursor.fetchone()[0]
                    prefix_time = (datetime.now() - start_time).total_seconds() * 1000

                    # Test substring match query using secure query helper
                    start_time = datetime.now()
                    substring_query, substring_params = (
                        SecureQueryHelper.build_count_query(
                            titles_table, "title_normalized LIKE ?"
                        )
                    )
                    cursor = conn.execute(
                        substring_query, [f"%{query_lower}%"] + substring_params
                    )
                    substring_count = cursor.fetchone()[0]
                    substring_time = (
                        datetime.now() - start_time
                    ).total_seconds() * 1000

                    benchmark_results.append(
                        {
                            "query_term": query_term,
                            "exact_match": {
                                "count": exact_count,
                                "time_ms": round(exact_time, 2),
                            },
                            "prefix_match": {
                                "count": prefix_count,
                                "time_ms": round(prefix_time, 2),
                            },
                            "substring_match": {
                                "count": substring_count,
                                "time_ms": round(substring_time, 2),
                            },
                        }
                    )

                # Calculate summary statistics
                all_times = []
                for result in benchmark_results:
                    all_times.extend(
                        [
                            result["exact_match"]["time_ms"],
                            result["prefix_match"]["time_ms"],
                            result["substring_match"]["time_ms"],
                        ]
                    )

                avg_time = sum(all_times) / len(all_times) if all_times else 0
                max_time = max(all_times) if all_times else 0
                min_time = min(all_times) if all_times else 0

                return {
                    "provider": provider_name,
                    "test_queries": test_queries,
                    "results": benchmark_results,
                    "summary": {
                        "avg_time_ms": round(avg_time, 2),
                        "max_time_ms": round(max_time, 2),
                        "min_time_ms": round(min_time, 2),
                        "total_queries": len(benchmark_results) * 3,
                        "performance_rating": "excellent"
                        if avg_time < 10
                        else "good"
                        if avg_time < 50
                        else "poor",
                    },
                    "benchmarked_at": datetime.now().isoformat(),
                }

        except sqlite3.Error as e:
            raise DatabaseError(f"Benchmark failed: {e}") from e

    def optimize_database(self, provider_name: str | None = None) -> dict[str, Any]:
        """Optimize database performance.

        Args:
            provider_name: Specific provider to optimize (None for all)

        Returns:
            Dictionary with optimization results

        Raises:
            DatabaseError: If optimization fails
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                optimization_results = {
                    "started_at": datetime.now().isoformat(),
                    "operations": [],
                    "success": False,
                }

                # Run ANALYZE to update query planner statistics
                logger.info("Running ANALYZE to update query planner statistics")
                start_time = datetime.now()
                conn.execute("ANALYZE")
                analyze_time = (datetime.now() - start_time).total_seconds() * 1000

                optimization_results["operations"].append(
                    {
                        "operation": "ANALYZE",
                        "time_ms": round(analyze_time, 2),
                        "description": "Updated query planner statistics",
                    }
                )

                # Run VACUUM to defragment and reclaim space
                logger.info("Running VACUUM to optimize database file")
                start_time = datetime.now()
                conn.execute("VACUUM")
                vacuum_time = (datetime.now() - start_time).total_seconds() * 1000

                optimization_results["operations"].append(
                    {
                        "operation": "VACUUM",
                        "time_ms": round(vacuum_time, 2),
                        "description": "Defragmented database and reclaimed space",
                    }
                )

                # Update database metadata
                conn.execute(
                    """
                    INSERT OR REPLACE INTO database_metadata (key, value, updated_at)
                    VALUES ('last_optimization', ?, ?)
                """,
                    (datetime.now().isoformat(), datetime.now().isoformat()),
                )

                optimization_results["success"] = True
                optimization_results["completed_at"] = datetime.now().isoformat()
                optimization_results["total_time_ms"] = round(
                    analyze_time + vacuum_time, 2
                )

                logger.info(
                    f"Database optimization completed in {optimization_results['total_time_ms']}ms"
                )
                return optimization_results

        except sqlite3.Error as e:
            raise DatabaseError(f"Database optimization failed: {e}") from e

    def validate_index_effectiveness(self, provider_name: str) -> dict[str, Any]:
        """Validate that indexes are being used effectively.

        Args:
            provider_name: Name of the provider to validate

        Returns:
            Dictionary with validation results

        Raises:
            DatabaseError: If validation fails
        """
        # Validate table name for security
        titles_table = TableNameValidator.validate_table_name(
            f"{provider_name}_titles", provider_name
        )

        # Test queries that should use indexes (using secure construction)
        test_cases = [
            {
                "name": "exact_match_normalized",
                "query": f"SELECT aid, title FROM {titles_table} WHERE title_normalized = ?",
                "params": ["evangelion"],
                "expected_index": f"idx_{provider_name}_titles_normalized",
            },
            {
                "name": "prefix_match_normalized",
                "query": f"SELECT aid, title FROM {titles_table} WHERE title_normalized LIKE ?",
                "params": ["eva%"],
                "expected_index": f"idx_{provider_name}_titles_normalized",
            },
            {
                "name": "aid_lookup",
                "query": f"SELECT title FROM {titles_table} WHERE aid = ?",
                "params": [30],
                "expected_index": f"idx_{provider_name}_titles_aid",
            },
            {
                "name": "composite_search",
                "query": f"SELECT aid, title FROM {titles_table} WHERE title_normalized = ? AND title_type = ?",
                "params": ["evangelion", 1],
                "expected_index": f"idx_{provider_name}_search_composite",
            },
        ]

        validation_results = {
            "provider": provider_name,
            "test_cases": [],
            "overall_score": 0,
            "validated_at": datetime.now().isoformat(),
        }

        passed_tests = 0

        for test_case in test_cases:
            try:
                # For EXPLAIN QUERY PLAN, we need the full query with values
                # Since these are hardcoded test values, we can safely construct the query
                full_query = test_case["query"]
                for param in test_case["params"]:
                    if isinstance(param, str):
                        full_query = full_query.replace("?", f"'{param}'", 1)
                    else:
                        full_query = full_query.replace("?", str(param), 1)

                analysis = self.analyze_query_performance(provider_name, full_query)

                # Check if expected index is mentioned in query plan
                uses_expected_index = any(
                    test_case["expected_index"].upper() in detail["detail"].upper()
                    for detail in analysis["query_plan"]
                )

                test_result = {
                    "name": test_case["name"],
                    "query": test_case["query"],
                    "expected_index": test_case["expected_index"],
                    "uses_expected_index": uses_expected_index,
                    "uses_any_index": analysis["uses_index"],
                    "has_table_scan": analysis["has_table_scan"],
                    "passed": uses_expected_index and not analysis["has_table_scan"],
                }

                if test_result["passed"]:
                    passed_tests += 1

                validation_results["test_cases"].append(test_result)

            except Exception as e:
                logger.error(
                    f"Index validation test failed for {test_case['name']}: {e}"
                )
                validation_results["test_cases"].append(
                    {"name": test_case["name"], "error": str(e), "passed": False}
                )

        validation_results["overall_score"] = (passed_tests / len(test_cases)) * 100
        validation_results["passed_tests"] = passed_tests
        validation_results["total_tests"] = len(test_cases)

        return validation_results


def create_index_optimizer(db_path: str) -> IndexOptimizer:
    """Create an index optimizer instance.

    Args:
        db_path: Path to SQLite database file

    Returns:
        IndexOptimizer instance
    """
    return IndexOptimizer(db_path)


def benchmark_provider_performance(db_path: str, provider_name: str) -> dict[str, Any]:
    """Benchmark search performance for a provider.

    Args:
        db_path: Path to SQLite database file
        provider_name: Name of the provider to benchmark

    Returns:
        Dictionary with benchmark results
    """
    optimizer = create_index_optimizer(db_path)

    # Standard test queries for benchmarking
    test_queries = [
        "evangelion",
        "attack",
        "naruto",
        "one piece",
        "dragon ball",
        "studio ghibli",
        "miyazaki",
        "a",  # Short query
        "the",  # Common word
    ]

    return optimizer.benchmark_search_queries(provider_name, test_queries)
