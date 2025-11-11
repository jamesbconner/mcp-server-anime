"""Automated analytics and maintenance scheduler for transaction logging.

This module provides automated scheduling for transaction cleanup, analytics generation,
and performance monitoring to maintain optimal database performance.
"""

import asyncio
import contextlib
from datetime import datetime, timedelta
from typing import Any

from .exceptions import DatabaseError
from .logging_config import get_logger
from .transaction_logger import get_transaction_logger

logger = get_logger(__name__)


class AnalyticsScheduler:
    """Automated scheduler for transaction analytics and maintenance."""

    def __init__(self, cleanup_interval_hours: int = 24, retention_days: int = 30):
        """Initialize the analytics scheduler.

        Args:
            cleanup_interval_hours: Hours between automatic cleanup runs
            retention_days: Days to retain transaction data
        """
        self.cleanup_interval_hours = cleanup_interval_hours
        self.retention_days = retention_days
        self.transaction_logger = get_transaction_logger()
        self._running = False
        self._cleanup_task: asyncio.Task | None = None
        self._last_cleanup: datetime | None = None

    async def start_scheduler(self) -> None:
        """Start the automated scheduler."""
        if self._running:
            logger.warning("Analytics scheduler is already running")
            return

        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info(
            f"Analytics scheduler started (cleanup every {self.cleanup_interval_hours}h, retention {self.retention_days}d)"
        )

    async def stop_scheduler(self) -> None:
        """Stop the automated scheduler."""
        if not self._running:
            return

        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._cleanup_task

        logger.info("Analytics scheduler stopped")

    async def _cleanup_loop(self) -> None:
        """Main cleanup loop that runs periodically."""
        while self._running:
            try:
                # Check if cleanup is needed
                if self._should_run_cleanup():
                    await self._run_cleanup()

                # Sleep for 1 hour before checking again
                await asyncio.sleep(3600)  # 1 hour

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in analytics scheduler cleanup loop: {e}")
                # Continue running despite errors
                await asyncio.sleep(3600)

    def _should_run_cleanup(self) -> bool:
        """Check if cleanup should be run."""
        if self._last_cleanup is None:
            return True

        time_since_cleanup = datetime.now() - self._last_cleanup
        return time_since_cleanup >= timedelta(hours=self.cleanup_interval_hours)

    async def _run_cleanup(self) -> None:
        """Run the cleanup process."""
        try:
            logger.info("Starting automated transaction cleanup")

            # Clean up old transactions
            deleted_count = await self.transaction_logger.cleanup_old_transactions(
                self.retention_days
            )

            # Update last cleanup time
            self._last_cleanup = datetime.now()

            logger.info(
                f"Automated cleanup completed: {deleted_count} transactions removed"
            )

        except Exception as e:
            logger.error(f"Automated cleanup failed: {e}")

    async def generate_daily_report(self, provider: str = "anidb") -> dict[str, Any]:
        """Generate a comprehensive daily analytics report.

        Args:
            provider: Provider to generate report for

        Returns:
            Dictionary with daily analytics report
        """
        try:
            logger.info(f"Generating daily analytics report for {provider}")

            # Get various analytics
            search_stats = await self.transaction_logger.get_search_stats(
                provider, hours=24
            )
            query_analytics = await self.transaction_logger.get_query_analytics(
                provider, hours=24
            )
            performance_metrics = await self.transaction_logger.get_performance_metrics(
                provider, hours=24
            )
            overall_stats = await self.transaction_logger.get_overall_stats(hours=24)

            report = {
                "report_type": "daily_analytics",
                "provider": provider,
                "report_date": datetime.now().date().isoformat(),
                "generated_at": datetime.now().isoformat(),
                "search_statistics": search_stats,
                "query_analytics": query_analytics,
                "performance_metrics": performance_metrics,
                "overall_statistics": overall_stats,
                "summary": {
                    "total_searches": search_stats["total_searches"],
                    "avg_response_time_ms": search_stats["avg_response_time_ms"],
                    "performance_rating": self._calculate_performance_rating(
                        performance_metrics
                    ),
                    "top_query": search_stats["popular_queries"][0]["query"]
                    if search_stats["popular_queries"]
                    else "N/A",
                },
            }

            logger.info(
                f"Daily report generated: {report['summary']['total_searches']} searches analyzed"
            )
            return report

        except Exception as e:
            logger.error(f"Failed to generate daily report: {e}")
            raise DatabaseError(f"Daily report generation failed: {e}") from e

    def _calculate_performance_rating(self, performance_metrics: dict[str, Any]) -> str:
        """Calculate overall performance rating based on metrics.

        Args:
            performance_metrics: Performance metrics dictionary

        Returns:
            Performance rating string
        """
        try:
            percentiles = performance_metrics["response_time_percentiles"]
            sla_compliance = performance_metrics["sla_compliance"][
                "compliance_percentage"
            ]

            # Rating based on P95 response time and SLA compliance
            p95_time = percentiles["p95"]

            if p95_time < 50 and sla_compliance > 95:
                return "excellent"
            elif p95_time < 100 and sla_compliance > 90:
                return "good"
            elif p95_time < 200 and sla_compliance > 80:
                return "fair"
            else:
                return "poor"

        except (KeyError, TypeError):
            return "unknown"

    async def get_scheduler_status(self) -> dict[str, Any]:
        """Get current scheduler status and statistics.

        Returns:
            Dictionary with scheduler status
        """
        return {
            "running": self._running,
            "cleanup_interval_hours": self.cleanup_interval_hours,
            "retention_days": self.retention_days,
            "last_cleanup": self._last_cleanup.isoformat()
            if self._last_cleanup
            else None,
            "next_cleanup_due": self._should_run_cleanup(),
            "uptime_hours": (datetime.now() - self._last_cleanup).total_seconds() / 3600
            if self._last_cleanup
            else 0,
        }

    async def force_cleanup(self) -> dict[str, Any]:
        """Force an immediate cleanup run.

        Returns:
            Dictionary with cleanup results
        """
        logger.info("Forcing immediate transaction cleanup")

        try:
            deleted_count = await self.transaction_logger.cleanup_old_transactions(
                self.retention_days
            )
            self._last_cleanup = datetime.now()

            result = {
                "success": True,
                "deleted_transactions": deleted_count,
                "cleanup_time": self._last_cleanup.isoformat(),
                "retention_days": self.retention_days,
            }

            logger.info(
                f"Forced cleanup completed: {deleted_count} transactions removed"
            )
            return result

        except Exception as e:
            logger.error(f"Forced cleanup failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "cleanup_time": datetime.now().isoformat(),
            }


# Global scheduler instance
_analytics_scheduler: AnalyticsScheduler | None = None


def get_analytics_scheduler(
    cleanup_interval_hours: int = 24, retention_days: int = 30
) -> AnalyticsScheduler:
    """Get the global analytics scheduler instance.

    Args:
        cleanup_interval_hours: Hours between cleanup runs (only used for first call)
        retention_days: Days to retain data (only used for first call)

    Returns:
        AnalyticsScheduler instance
    """
    global _analytics_scheduler
    if _analytics_scheduler is None:
        _analytics_scheduler = AnalyticsScheduler(
            cleanup_interval_hours, retention_days
        )
    return _analytics_scheduler


async def start_analytics_automation(
    cleanup_interval_hours: int = 24, retention_days: int = 30
) -> None:
    """Start automated analytics and cleanup.

    Args:
        cleanup_interval_hours: Hours between cleanup runs
        retention_days: Days to retain transaction data
    """
    scheduler = get_analytics_scheduler(cleanup_interval_hours, retention_days)
    await scheduler.start_scheduler()


async def stop_analytics_automation() -> None:
    """Stop automated analytics and cleanup."""
    scheduler = get_analytics_scheduler()
    await scheduler.stop_scheduler()
