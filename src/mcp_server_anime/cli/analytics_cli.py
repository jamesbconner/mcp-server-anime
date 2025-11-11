#!/usr/bin/env python3
"""Analytics and monitoring CLI for MCP Anime Server.

This module provides command-line tools for viewing search analytics,
performance metrics, and generating reports from transaction data.
"""

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Handle imports for both direct execution and module execution
try:
    # Try relative imports first (when run as module with python -m)
    from ..core.analytics_scheduler import get_analytics_scheduler
    from ..core.database_config import get_local_db_config
    from ..core.index_optimization import create_index_optimizer
    from ..core.multi_provider_db import get_multi_provider_database
    from ..core.transaction_logger import get_transaction_logger
    from ..providers.anidb.config import load_config
    from ..providers.anidb.service import create_anidb_service
except ImportError:
    # Fall back to absolute imports (when run directly)
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))
    from mcp_server_anime.core.analytics_scheduler import get_analytics_scheduler
    from mcp_server_anime.core.database_config import get_local_db_config
    from mcp_server_anime.core.index_optimization import create_index_optimizer
    from mcp_server_anime.core.multi_provider_db import get_multi_provider_database
    from mcp_server_anime.core.transaction_logger import get_transaction_logger
    from mcp_server_anime.providers.anidb.config import load_config
    from mcp_server_anime.providers.anidb.service import create_anidb_service


class AnalyticsCLI:
    """Command-line interface for analytics and monitoring."""

    def __init__(self):
        """Initialize the CLI."""
        self.config = get_local_db_config()
        self.transaction_logger = get_transaction_logger()
        self.analytics_scheduler = get_analytics_scheduler()

    async def show_stats(
        self, provider: str = "anidb", hours: int = 24, json_output: bool = False
    ) -> dict[str, Any]:
        """Show search statistics for a provider.

        Args:
            provider: Provider to show stats for
            hours: Hours to look back
            json_output: Output as JSON

        Returns:
            Dictionary with statistics
        """
        try:
            stats = await self.transaction_logger.get_search_stats(provider, hours)

            if json_output:
                print(json.dumps(stats, indent=2))
                return stats

            print(f"📊 Search Statistics for {provider.upper()} (last {hours} hours)")
            print("=" * 60)

            print(f"Total Searches: {stats['total_searches']}")
            print(f"Average Response Time: {stats['avg_response_time_ms']:.1f}ms")
            print(f"Average Results per Search: {stats['avg_results_per_search']:.1f}")
            print()

            # Popular queries
            if stats["popular_queries"]:
                print("🔥 Popular Queries:")
                for i, query_info in enumerate(stats["popular_queries"][:5], 1):
                    print(
                        f"  {i}. '{query_info['query']}' ({query_info['count']} searches)"
                    )
                print()

            # Performance distribution
            if stats["performance_distribution"]:
                print("⚡ Performance Distribution:")
                total = sum(stats["performance_distribution"].values())
                for perf, count in stats["performance_distribution"].items():
                    percentage = (count / total * 100) if total > 0 else 0
                    print(f"  {perf}: {count} searches ({percentage:.1f}%)")
                print()

            # Hourly distribution
            if stats["hourly_distribution"]:
                print("🕐 Hourly Distribution:")
                for hour_info in stats["hourly_distribution"]:
                    hour = hour_info["hour"]
                    searches = hour_info["searches"]
                    avg_time = hour_info["avg_response_time_ms"]
                    print(
                        f"  {hour:02d}:00 - {searches} searches (avg: {avg_time:.1f}ms)"
                    )

            return stats

        except Exception as e:
            print(f"❌ Failed to get statistics: {e}")
            return {"success": False, "error": str(e)}

    async def show_performance(
        self, provider: str = "anidb", hours: int = 24, json_output: bool = False
    ) -> dict[str, Any]:
        """Show performance metrics for a provider.

        Args:
            provider: Provider to show metrics for
            hours: Hours to look back
            json_output: Output as JSON

        Returns:
            Dictionary with performance metrics
        """
        try:
            metrics = await self.transaction_logger.get_performance_metrics(
                provider, hours
            )

            if json_output:
                print(json.dumps(metrics, indent=2))
                return metrics

            print(f"⚡ Performance Metrics for {provider.upper()} (last {hours} hours)")
            print("=" * 60)

            percentiles = metrics["response_time_percentiles"]
            print("Response Time Percentiles:")
            print(f"  P50 (median): {percentiles['p50']:.1f}ms")
            print(f"  P90: {percentiles['p90']:.1f}ms")
            print(f"  P95: {percentiles['p95']:.1f}ms")
            print(f"  P99: {percentiles['p99']:.1f}ms")
            print(f"  Min: {percentiles['min']:.1f}ms")
            print(f"  Max: {percentiles['max']:.1f}ms")
            print(f"  Average: {percentiles['avg']:.1f}ms")
            print()

            sla = metrics["sla_compliance"]
            print(f"SLA Compliance (< {sla['target_ms']}ms):")
            print(f"  Compliance: {sla['compliance_percentage']:.1f}%")
            print(
                f"  Compliant searches: {sla['compliant_searches']}/{sla['total_searches']}"
            )

            return metrics

        except Exception as e:
            print(f"❌ Failed to get performance metrics: {e}")
            return {"success": False, "error": str(e)}

    async def show_query_analytics(
        self, provider: str = "anidb", hours: int = 24, json_output: bool = False
    ) -> dict[str, Any]:
        """Show query analytics for a provider.

        Args:
            provider: Provider to show analytics for
            hours: Hours to look back
            json_output: Output as JSON

        Returns:
            Dictionary with query analytics
        """
        try:
            analytics = await self.transaction_logger.get_query_analytics(
                provider, hours
            )

            if json_output:
                print(json.dumps(analytics, indent=2))
                return analytics

            print(f"🔍 Query Analytics for {provider.upper()} (last {hours} hours)")
            print("=" * 60)

            # Query length distribution
            print("Query Length Distribution:")
            for dist in analytics["query_length_distribution"]:
                print(
                    f"  {dist['category']}: {dist['count']} queries (avg results: {dist['avg_results']:.1f})"
                )
            print()

            # Zero result queries
            if analytics["zero_result_queries"]:
                print("🚫 Queries with No Results:")
                for query_info in analytics["zero_result_queries"][:5]:
                    print(f"  '{query_info['query']}' ({query_info['count']} times)")
                print()

            # High result queries
            if analytics["high_result_queries"]:
                print("📈 High-Result Queries:")
                for query_info in analytics["high_result_queries"][:5]:
                    print(
                        f"  '{query_info['query']}' (avg: {query_info['avg_results']:.1f} results, {query_info['searches']} searches)"
                    )

            return analytics

        except Exception as e:
            print(f"❌ Failed to get query analytics: {e}")
            return {"success": False, "error": str(e)}

    async def generate_report(
        self, provider: str = "anidb", output_file: str | None = None
    ) -> dict[str, Any]:
        """Generate comprehensive analytics report.

        Args:
            provider: Provider to generate report for
            output_file: Optional file to save report to

        Returns:
            Dictionary with report data
        """
        try:
            print(f"📋 Generating analytics report for {provider.upper()}...")

            report = await self.analytics_scheduler.generate_daily_report(provider)

            if output_file:
                with open(output_file, "w") as f:
                    json.dump(report, f, indent=2)
                print(f"✅ Report saved to: {output_file}")
            else:
                print(json.dumps(report, indent=2))

            return report

        except Exception as e:
            print(f"❌ Failed to generate report: {e}")
            return {"success": False, "error": str(e)}

    async def benchmark_performance(
        self, provider: str = "anidb", json_output: bool = False
    ) -> dict[str, Any]:
        """Benchmark search performance.

        Args:
            provider: Provider to benchmark
            json_output: Output as JSON

        Returns:
            Dictionary with benchmark results
        """
        try:
            print(f"🏃 Benchmarking search performance for {provider.upper()}...")

            optimizer = create_index_optimizer(self.config.database.database_path)

            # Standard benchmark queries
            test_queries = [
                "evangelion",
                "attack on titan",
                "naruto",
                "one piece",
                "dragon ball",
                "studio ghibli",
                "miyazaki",
                "anime",
                "the",
            ]

            benchmark_results = optimizer.benchmark_search_queries(
                provider, test_queries
            )

            if json_output:
                print(json.dumps(benchmark_results, indent=2))
                return benchmark_results

            print("📊 Benchmark Results:")
            print("=" * 50)

            summary = benchmark_results["summary"]
            print(f"Average Response Time: {summary['avg_time_ms']:.1f}ms")
            print(f"Fastest Query: {summary['min_time_ms']:.1f}ms")
            print(f"Slowest Query: {summary['max_time_ms']:.1f}ms")
            print(f"Performance Rating: {summary['performance_rating'].upper()}")
            print(f"Total Queries Tested: {summary['total_queries']}")
            print()

            print("Individual Query Results:")
            for result in benchmark_results["results"][:5]:  # Show top 5
                query = result["query_term"]
                exact_time = result["exact_match"]["time_ms"]
                prefix_time = result["prefix_match"]["time_ms"]
                substring_time = result["substring_match"]["time_ms"]

                print(f"  '{query}':")
                print(
                    f"    Exact: {exact_time:.1f}ms, Prefix: {prefix_time:.1f}ms, Substring: {substring_time:.1f}ms"
                )

            return benchmark_results

        except Exception as e:
            print(f"❌ Benchmark failed: {e}")
            return {"success": False, "error": str(e)}

    async def show_scheduler_status(self, json_output: bool = False) -> dict[str, Any]:
        """Show analytics scheduler status.

        Args:
            json_output: Output as JSON

        Returns:
            Dictionary with scheduler status
        """
        try:
            status = await self.analytics_scheduler.get_scheduler_status()

            if json_output:
                print(json.dumps(status, indent=2))
                return status

            print("🤖 Analytics Scheduler Status:")
            print("=" * 40)

            print(f"Running: {'✅ Yes' if status['running'] else '❌ No'}")
            print(f"Cleanup Interval: {status['cleanup_interval_hours']} hours")
            print(f"Retention Period: {status['retention_days']} days")

            if status["last_cleanup"]:
                print(f"Last Cleanup: {status['last_cleanup']}")
            else:
                print("Last Cleanup: Never")

            print(
                f"Next Cleanup Due: {'✅ Yes' if status['next_cleanup_due'] else '❌ No'}"
            )

            if status["uptime_hours"] > 0:
                print(f"Uptime: {status['uptime_hours']:.1f} hours")

            return status

        except Exception as e:
            print(f"❌ Failed to get scheduler status: {e}")
            return {"success": False, "error": str(e)}

    async def cleanup_transactions(
        self, retention_days: int | None = None, json_output: bool = False
    ) -> dict[str, Any]:
        """Clean up old transaction data.

        Args:
            retention_days: Days to retain (uses config default if None)
            json_output: Output as JSON

        Returns:
            Dictionary with cleanup results
        """
        try:
            retention = retention_days or self.config.transaction.retention_days
            print(f"🧹 Cleaning up transactions older than {retention} days...")

            deleted_count = await self.transaction_logger.cleanup_old_transactions(
                retention
            )

            result = {
                "success": True,
                "deleted_count": deleted_count,
                "retention_days": retention,
                "cleanup_time": datetime.now().isoformat(),
            }

            if json_output:
                print(json.dumps(result, indent=2))
            else:
                print(f"✅ Cleanup completed: {deleted_count} transactions removed")

            return result

        except Exception as e:
            print(f"❌ Cleanup failed: {e}")
            return {"success": False, "error": str(e)}

    async def show_cache_stats(
        self, provider: str = "anidb", json_output: bool = False
    ) -> dict[str, Any]:
        """Show cache statistics for a provider.

        Args:
            provider: Provider to show cache stats for
            json_output: Output as JSON

        Returns:
            Dictionary with cache statistics
        """
        try:
            if provider == "anidb":
                # Try to get service cache stats (with timeout to avoid hanging)
                service_stats = None
                service_available = False
                try:
                    config = load_config()
                    service = await create_anidb_service(config)

                    # Use asyncio.wait_for to add a timeout
                    async def get_service_stats():
                        async with service:
                            return await service.get_cache_stats()

                    service_stats = await asyncio.wait_for(
                        get_service_stats(), timeout=3.0
                    )
                    service_available = True
                except TimeoutError:
                    logger.debug("Service cache stats retrieval timed out")
                    service_available = False
                except Exception as e:
                    logger.debug(f"Could not get service cache stats: {e}")
                    service_available = False

                # Get persistent database stats directly
                db_stats = None
                try:
                    db = get_multi_provider_database(self.config.database.database_path)
                    db_stats = await db.get_cache_stats()
                except Exception as e:
                    logger.debug(f"Could not get database cache stats: {e}")

                # If neither service nor database is available, return error
                if not service_available and db_stats is None:
                    result = {
                        "success": False,
                        "error": "Neither service cache nor persistent database available",
                        "provider": provider,
                    }

                    if json_output:
                        print(json.dumps(result, indent=2))
                    else:
                        print(f"❌ Cache not available for {provider}")

                    return result

                # Process database stats (handle None case)
                providers = {}
                methods = {}

                if db_stats is not None:
                    providers = {
                        prov_name: stats["count"]
                        for prov_name, stats in db_stats.get("providers", {}).items()
                    }

                    methods = {
                        method: stats["count"]
                        for method, stats in db_stats.get("methods", {}).items()
                    }

                # Combine service and database stats
                combined_stats = {}

                # Add service cache stats if available
                if service_stats:
                    combined_stats.update(
                        service_stats.model_dump()
                        if hasattr(service_stats, "model_dump")
                        else service_stats
                    )
                else:
                    # Service cache is available but empty/not initialized
                    combined_stats.update(
                        {
                            "memory_entries": 0,
                            "hits": 0,
                            "misses": 0,
                            "memory_hits": 0,
                            "memory_misses": 0,
                            "db_hits": 0,
                            "db_misses": 0,
                            "total_hits": 0,
                            "total_misses": 0,
                            "db_available": db_stats is not None,
                        }
                    )

                # Add database stats if available
                if db_stats is not None:
                    combined_stats.update(
                        {
                            "persistent_entries": db_stats.get("total_entries", 0),
                            "persistent_active_entries": db_stats.get(
                                "active_entries", 0
                            ),
                            "persistent_expired_entries": db_stats.get(
                                "expired_entries", 0
                            ),
                            "persistent_providers": providers,
                            "persistent_methods": methods,
                            "total_data_size": db_stats.get("total_data_size", 0),
                            "db_file_size": db_stats.get("db_file_size", 0),
                            "total_entries": combined_stats.get("memory_entries", 0)
                            + db_stats.get("total_entries", 0),
                            "db_entries": db_stats.get("total_entries", 0),
                        }
                    )

                # Calculate metrics
                total_requests = combined_stats.get("hits", 0) + combined_stats.get(
                    "misses", 0
                )
                hit_rate = (
                    (combined_stats.get("hits", 0) / total_requests * 100)
                    if total_requests > 0
                    else 0
                )

                memory_requests = combined_stats.get(
                    "memory_hits", 0
                ) + combined_stats.get("memory_misses", 0)
                memory_hit_rate = (
                    (combined_stats.get("memory_hits", 0) / memory_requests * 100)
                    if memory_requests > 0
                    else 0
                )

                db_requests = combined_stats.get("db_hits", 0) + combined_stats.get(
                    "db_misses", 0
                )
                db_hit_rate = (
                    (combined_stats.get("db_hits", 0) / db_requests * 100)
                    if db_requests > 0
                    else 0
                )

                # Create result structure
                result = {
                    "success": True,
                    "provider": provider,
                    "service_cache_available": service_available,
                    "service_cache_active": service_stats is not None,
                    "persistent_database_available": db_stats is not None,
                    "cache_stats": combined_stats,
                    "calculated_metrics": {
                        "total_requests": total_requests,
                        "overall_hit_rate": round(hit_rate, 2),
                        "memory_hit_rate": round(memory_hit_rate, 2),
                        "db_hit_rate": round(db_hit_rate, 2),
                    },
                    "timestamp": datetime.now().isoformat(),
                }

                if json_output:
                    print(json.dumps(result, indent=2))
                    return result

                # Pretty print the stats
                print(f"📊 Cache Statistics for {provider.upper()}")
                print("=" * 50)
                print()

                # Show cache status
                print("🔧 Cache Status:")
                if service_available:
                    if service_stats:
                        service_status = f"✅ Active ({combined_stats.get('memory_entries', 0)} entries)"
                    else:
                        service_status = "✅ Available (0 entries)"
                else:
                    service_status = "❌ Not Available"

                db_status = (
                    "✅ Available" if db_stats is not None else "❌ Not Available"
                )
                print(f"  Service cache: {service_status}")
                print(f"  Persistent database: {db_status}")
                print()

                print("🗄️  Storage:")
                print(f"  Total entries: {combined_stats.get('total_entries', 0)}")
                print(f"  Memory entries: {combined_stats.get('memory_entries', 0)}")
                print(f"  Database entries: {combined_stats.get('db_entries', 0)}")

                if db_stats is not None:
                    print(f"  Active entries: {db_stats.get('active_entries', 0)}")
                    print(f"  Expired entries: {db_stats.get('expired_entries', 0)}")

                if providers:
                    print("  Persistent entries by provider:")
                    for prov, count in providers.items():
                        print(f"    {prov}: {count} entries")

                if methods:
                    print("  Persistent entries by method:")
                    for method, count in methods.items():
                        print(f"    {method}: {count} entries")

                if db_stats is not None:
                    data_size_mb = db_stats.get("total_data_size", 0) / (1024 * 1024)
                    print(f"  Total cached data size: {data_size_mb:.2f} MB")

                    db_size_mb = db_stats.get("db_file_size", 0) / (1024 * 1024)
                    print(f"  Database file size: {db_size_mb:.2f} MB")

                print()

                if total_requests > 0:
                    print("📈 Performance (Runtime Stats):")
                    print(f"  Total requests: {total_requests}")
                    print(f"  Overall hit rate: {hit_rate:.1f}%")
                    print(f"  Cache hits: {combined_stats.get('hits', 0)}")
                    print(f"  Cache misses: {combined_stats.get('misses', 0)}")
                    print()

                    print("💾 Memory Cache:")
                    print(f"  Memory hits: {combined_stats.get('memory_hits', 0)}")
                    print(f"  Memory misses: {combined_stats.get('memory_misses', 0)}")
                    print(f"  Memory hit rate: {memory_hit_rate:.1f}%")
                    if "avg_memory_access_time" in combined_stats:
                        print(
                            f"  Avg access time: {combined_stats['avg_memory_access_time']:.3f}ms"
                        )
                    print()

                    print("🗃️  Database Cache:")
                    print(f"  DB hits: {combined_stats.get('db_hits', 0)}")
                    print(f"  DB misses: {combined_stats.get('db_misses', 0)}")
                    print(f"  DB hit rate: {db_hit_rate:.1f}%")
                    if "avg_db_access_time" in combined_stats:
                        print(
                            f"  Avg access time: {combined_stats['avg_db_access_time']:.3f}ms"
                        )
                    print()
                else:
                    if service_available:
                        print(
                            "📈 Performance: No runtime statistics yet (service cache available but no requests processed)"
                        )
                    else:
                        print(
                            "📈 Performance: No runtime statistics available (service cache not accessible)"
                        )

                return result
            else:
                result = {
                    "success": False,
                    "error": f"Cache stats not supported for provider: {provider}",
                    "supported_providers": ["anidb"],
                }

                if json_output:
                    print(json.dumps(result, indent=2))
                else:
                    print(f"❌ Cache stats not supported for provider: {provider}")
                    print("   Supported providers: anidb")

                return result

        except Exception as e:
            result = {"success": False, "error": str(e), "provider": provider}

            if json_output:
                print(json.dumps(result, indent=2))
            else:
                print(f"❌ Failed to get cache stats for {provider}: {e}")

            return result


async def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="MCP Anime Server Analytics CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s stats --provider anidb --hours 24
  %(prog)s performance --provider anidb
  %(prog)s queries --provider anidb --hours 48
  %(prog)s cache-stats --provider anidb
  %(prog)s report --provider anidb --output report.json
  %(prog)s benchmark --provider anidb
  %(prog)s scheduler-status
  %(prog)s cleanup --retention-days 30
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # stats command
    stats_parser = subparsers.add_parser("stats", help="Show search statistics")
    stats_parser.add_argument(
        "--provider", default="anidb", help="Provider to show stats for"
    )
    stats_parser.add_argument(
        "--hours", type=int, default=24, help="Hours to look back"
    )
    stats_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # performance command
    perf_parser = subparsers.add_parser("performance", help="Show performance metrics")
    perf_parser.add_argument(
        "--provider", default="anidb", help="Provider to show metrics for"
    )
    perf_parser.add_argument("--hours", type=int, default=24, help="Hours to look back")
    perf_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # queries command
    queries_parser = subparsers.add_parser("queries", help="Show query analytics")
    queries_parser.add_argument(
        "--provider", default="anidb", help="Provider to analyze"
    )
    queries_parser.add_argument(
        "--hours", type=int, default=24, help="Hours to look back"
    )
    queries_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # cache-stats command
    cache_parser = subparsers.add_parser("cache-stats", help="Show cache statistics")
    cache_parser.add_argument(
        "--provider", default="anidb", help="Provider to show cache stats for"
    )
    cache_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # report command
    report_parser = subparsers.add_parser(
        "report", help="Generate comprehensive report"
    )
    report_parser.add_argument(
        "--provider", default="anidb", help="Provider to generate report for"
    )
    report_parser.add_argument("--output", help="Output file for report")

    # benchmark command
    benchmark_parser = subparsers.add_parser(
        "benchmark", help="Benchmark search performance"
    )
    benchmark_parser.add_argument(
        "--provider", default="anidb", help="Provider to benchmark"
    )
    benchmark_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # scheduler-status command
    scheduler_parser = subparsers.add_parser(
        "scheduler-status", help="Show scheduler status"
    )
    scheduler_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # cleanup command
    cleanup_parser = subparsers.add_parser(
        "cleanup", help="Clean up old transaction data"
    )
    cleanup_parser.add_argument("--retention-days", type=int, help="Days to retain")
    cleanup_parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    cli = AnalyticsCLI()

    try:
        if args.command == "stats":
            await cli.show_stats(args.provider, args.hours, args.json)

        elif args.command == "performance":
            await cli.show_performance(args.provider, args.hours, args.json)

        elif args.command == "queries":
            await cli.show_query_analytics(args.provider, args.hours, args.json)

        elif args.command == "cache-stats":
            await cli.show_cache_stats(args.provider, args.json)

        elif args.command == "report":
            await cli.generate_report(args.provider, args.output)

        elif args.command == "benchmark":
            await cli.benchmark_performance(args.provider, args.json)

        elif args.command == "scheduler-status":
            await cli.show_scheduler_status(args.json)

        elif args.command == "cleanup":
            await cli.cleanup_transactions(args.retention_days, args.json)

    except KeyboardInterrupt:
        print("\n⚠️  Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
