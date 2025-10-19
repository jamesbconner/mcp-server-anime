#!/usr/bin/env python3
"""Analytics and monitoring CLI for MCP Anime Server.

This module provides command-line tools for viewing search analytics,
performance metrics, and generating reports from transaction data.
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from mcp_server_anime.core.analytics_scheduler import get_analytics_scheduler
from mcp_server_anime.core.database_config import get_local_db_config
from mcp_server_anime.core.index_optimization import create_index_optimizer
from mcp_server_anime.core.transaction_logger import get_transaction_logger


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
