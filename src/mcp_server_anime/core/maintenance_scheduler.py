"""Automated database maintenance scheduler for optimal performance.

This module provides automated scheduling for database maintenance tasks including
VACUUM, ANALYZE, index optimization, and health monitoring to ensure optimal
database performance and reliability.
"""

import asyncio
import os
import sqlite3
from datetime import datetime, timedelta
from typing import Any

from .database_config import get_local_db_config
from .exceptions import DatabaseError
from .index_optimization import create_index_optimizer
from .logging_config import get_logger

logger = get_logger(__name__)


class MaintenanceTask:
    """Represents a database maintenance task."""

    def __init__(
        self,
        name: str,
        description: str,
        interval_hours: int,
        task_func,
        priority: int = 5,
        max_duration_minutes: int = 30,
    ):
        """Initialize maintenance task.

        Args:
            name: Task name
            description: Task description
            interval_hours: Hours between task executions
            task_func: Async function to execute
            priority: Task priority (1-10, lower is higher priority)
            max_duration_minutes: Maximum expected duration
        """
        self.name = name
        self.description = description
        self.interval_hours = interval_hours
        self.task_func = task_func
        self.priority = priority
        self.max_duration_minutes = max_duration_minutes
        self.last_run: datetime | None = None
        self.last_duration_seconds: float | None = None
        self.last_result: dict[str, Any] | None = None
        self.run_count = 0
        self.failure_count = 0

    def is_due(self) -> bool:
        """Check if task is due to run."""
        if self.last_run is None:
            return True

        time_since_last = datetime.now() - self.last_run
        return time_since_last >= timedelta(hours=self.interval_hours)

    def get_next_run_time(self) -> datetime | None:
        """Get the next scheduled run time."""
        if self.last_run is None:
            return datetime.now()

        return self.last_run + timedelta(hours=self.interval_hours)

    async def execute(self) -> dict[str, Any]:
        """Execute the maintenance task."""
        start_time = datetime.now()

        try:
            logger.info(f"Starting maintenance task: {self.name}")

            result = await self.task_func()

            duration = (datetime.now() - start_time).total_seconds()

            self.last_run = start_time
            self.last_duration_seconds = duration
            self.last_result = result
            self.run_count += 1

            logger.info(f"Completed maintenance task: {self.name} in {duration:.1f}s")

            return {
                "success": True,
                "task": self.name,
                "duration_seconds": duration,
                "result": result,
                "timestamp": start_time.isoformat(),
            }

        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()

            self.last_run = start_time
            self.last_duration_seconds = duration
            self.failure_count += 1

            logger.error(f"Maintenance task failed: {self.name} - {e}")

            return {
                "success": False,
                "task": self.name,
                "duration_seconds": duration,
                "error": str(e),
                "timestamp": start_time.isoformat(),
            }


class MaintenanceScheduler:
    """Automated database maintenance scheduler."""

    def __init__(self, db_path: str | None = None):
        """Initialize the maintenance scheduler.

        Args:
            db_path: Database path (uses config default if None)
        """
        self.config = get_local_db_config()
        self.db_path = db_path or self.config.database.database_path
        self.optimizer = create_index_optimizer(self.db_path)

        self.tasks: list[MaintenanceTask] = []
        self._running = False
        self._scheduler_task: asyncio.Task | None = None
        self._maintenance_history: list[dict[str, Any]] = []

        # Initialize maintenance tasks
        self._setup_maintenance_tasks()

    def _setup_maintenance_tasks(self) -> None:
        """Set up the standard maintenance tasks."""

        # Database VACUUM task
        vacuum_task = MaintenanceTask(
            name="database_vacuum",
            description="Defragment database and reclaim space",
            interval_hours=self.config.database.vacuum_interval_hours,
            task_func=self._vacuum_database,
            priority=3,
            max_duration_minutes=60,
        )
        self.tasks.append(vacuum_task)

        # Database ANALYZE task
        analyze_task = MaintenanceTask(
            name="database_analyze",
            description="Update query planner statistics",
            interval_hours=self.config.database.analyze_interval_hours,
            task_func=self._analyze_database,
            priority=2,
            max_duration_minutes=15,
        )
        self.tasks.append(analyze_task)

        # Index optimization task
        index_task = MaintenanceTask(
            name="index_optimization",
            description="Optimize database indexes",
            interval_hours=24,  # Daily
            task_func=self._optimize_indexes,
            priority=4,
            max_duration_minutes=30,
        )
        self.tasks.append(index_task)

        # Health check task
        health_task = MaintenanceTask(
            name="health_check",
            description="Perform database health checks",
            interval_hours=6,  # Every 6 hours
            task_func=self._health_check,
            priority=1,
            max_duration_minutes=5,
        )
        self.tasks.append(health_task)

        # Transaction cleanup task
        if self.config.transaction.enable_logging:
            cleanup_task = MaintenanceTask(
                name="transaction_cleanup",
                description="Clean up old transaction logs",
                interval_hours=self.config.transaction.cleanup_interval_hours,
                task_func=self._cleanup_transactions,
                priority=5,
                max_duration_minutes=10,
            )
            self.tasks.append(cleanup_task)

        # Integrity check task (weekly)
        integrity_task = MaintenanceTask(
            name="integrity_check",
            description="Check database integrity",
            interval_hours=168,  # Weekly
            task_func=self._integrity_check,
            priority=6,
            max_duration_minutes=45,
        )
        self.tasks.append(integrity_task)

        # Sort tasks by priority
        self.tasks.sort(key=lambda t: t.priority)

    async def _vacuum_database(self) -> dict[str, Any]:
        """Perform database VACUUM operation."""
        if not self.config.database.auto_vacuum:
            return {"skipped": True, "reason": "auto_vacuum disabled"}

        try:
            start_time = datetime.now()

            with sqlite3.connect(self.db_path) as conn:
                # Get database size before vacuum
                cursor = conn.execute("PRAGMA page_count")
                pages_before = cursor.fetchone()[0]

                cursor = conn.execute("PRAGMA page_size")
                page_size = cursor.fetchone()[0]

                size_before = pages_before * page_size

                # Perform VACUUM
                conn.execute("VACUUM")

                # Get size after vacuum
                cursor = conn.execute("PRAGMA page_count")
                pages_after = cursor.fetchone()[0]

                size_after = pages_after * page_size
                space_reclaimed = size_before - size_after

                duration = (datetime.now() - start_time).total_seconds()

                return {
                    "size_before_bytes": size_before,
                    "size_after_bytes": size_after,
                    "space_reclaimed_bytes": space_reclaimed,
                    "space_reclaimed_mb": space_reclaimed / (1024 * 1024),
                    "duration_seconds": duration,
                }

        except sqlite3.Error as e:
            raise DatabaseError(f"VACUUM operation failed: {e}") from e

    async def _analyze_database(self) -> dict[str, Any]:
        """Perform database ANALYZE operation."""
        try:
            start_time = datetime.now()

            with sqlite3.connect(self.db_path) as conn:
                # Run ANALYZE on all tables
                conn.execute("ANALYZE")

                # Get statistics
                cursor = conn.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name NOT LIKE 'sqlite_%'
                """)
                tables = [row[0] for row in cursor.fetchall()]

                duration = (datetime.now() - start_time).total_seconds()

                return {
                    "tables_analyzed": len(tables),
                    "table_names": tables,
                    "duration_seconds": duration,
                }

        except sqlite3.Error as e:
            raise DatabaseError(f"ANALYZE operation failed: {e}") from e

    async def _optimize_indexes(self) -> dict[str, Any]:
        """Optimize database indexes."""
        try:
            # Use the index optimizer
            result = self.optimizer.optimize_database()
            return result

        except Exception as e:
            raise DatabaseError(f"Index optimization failed: {e}") from e

    async def _health_check(self) -> dict[str, Any]:
        """Perform database health check."""
        try:
            health_info = {
                "database_accessible": False,
                "file_exists": False,
                "file_size_bytes": 0,
                "connection_test": False,
                "table_count": 0,
                "issues": [],
            }

            # Check if database file exists
            if os.path.exists(self.db_path):
                health_info["file_exists"] = True
                health_info["file_size_bytes"] = os.path.getsize(self.db_path)
            else:
                health_info["issues"].append("Database file does not exist")

            # Test database connection
            try:
                with sqlite3.connect(self.db_path, timeout=5) as conn:
                    health_info["connection_test"] = True
                    health_info["database_accessible"] = True

                    # Count tables
                    cursor = conn.execute("""
                        SELECT COUNT(*) FROM sqlite_master 
                        WHERE type='table' AND name NOT LIKE 'sqlite_%'
                    """)
                    health_info["table_count"] = cursor.fetchone()[0]

                    # Check for corruption
                    cursor = conn.execute("PRAGMA integrity_check(1)")
                    integrity_result = cursor.fetchone()[0]

                    if integrity_result != "ok":
                        health_info["issues"].append(
                            f"Integrity check failed: {integrity_result}"
                        )

            except sqlite3.Error as e:
                health_info["issues"].append(f"Connection failed: {e}")

            # Check disk space
            try:
                import shutil

                free_space = shutil.disk_usage(os.path.dirname(self.db_path)).free
                health_info["free_disk_space_bytes"] = free_space

                if free_space < 100 * 1024 * 1024:  # Less than 100MB
                    health_info["issues"].append("Low disk space (< 100MB)")

            except Exception:
                health_info["issues"].append("Could not check disk space")

            health_info["healthy"] = len(health_info["issues"]) == 0

            return health_info

        except Exception as e:
            raise DatabaseError(f"Health check failed: {e}") from e

    async def _cleanup_transactions(self) -> dict[str, Any]:
        """Clean up old transaction logs."""
        try:
            from .transaction_logger import get_transaction_logger

            transaction_logger = get_transaction_logger()
            deleted_count = await transaction_logger.cleanup_old_transactions(
                self.config.transaction.retention_days
            )

            return {
                "deleted_transactions": deleted_count,
                "retention_days": self.config.transaction.retention_days,
            }

        except Exception as e:
            raise DatabaseError(f"Transaction cleanup failed: {e}") from e

    async def _integrity_check(self) -> dict[str, Any]:
        """Perform comprehensive database integrity check."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Full integrity check
                cursor = conn.execute("PRAGMA integrity_check")
                integrity_results = cursor.fetchall()

                # Foreign key check
                cursor = conn.execute("PRAGMA foreign_key_check")
                fk_violations = cursor.fetchall()

                # Quick check
                cursor = conn.execute("PRAGMA quick_check")
                quick_results = cursor.fetchall()

                is_healthy = (
                    len(integrity_results) == 1
                    and integrity_results[0][0] == "ok"
                    and len(fk_violations) == 0
                    and len(quick_results) == 1
                    and quick_results[0][0] == "ok"
                )

                return {
                    "healthy": is_healthy,
                    "integrity_check": [row[0] for row in integrity_results],
                    "foreign_key_violations": len(fk_violations),
                    "quick_check": [row[0] for row in quick_results],
                }

        except sqlite3.Error as e:
            raise DatabaseError(f"Integrity check failed: {e}") from e

    async def start_scheduler(self) -> None:
        """Start the maintenance scheduler."""
        if self._running:
            logger.warning("Maintenance scheduler is already running")
            return

        self._running = True
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())

        logger.info(f"Maintenance scheduler started with {len(self.tasks)} tasks")

    async def stop_scheduler(self) -> None:
        """Stop the maintenance scheduler."""
        if not self._running:
            return

        self._running = False

        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass

        logger.info("Maintenance scheduler stopped")

    async def _scheduler_loop(self) -> None:
        """Main scheduler loop."""
        while self._running:
            try:
                # Check for due tasks
                due_tasks = [task for task in self.tasks if task.is_due()]

                if due_tasks:
                    # Sort by priority (lower number = higher priority)
                    due_tasks.sort(key=lambda t: t.priority)

                    for task in due_tasks:
                        if not self._running:
                            break

                        try:
                            result = await task.execute()
                            self._maintenance_history.append(result)

                            # Keep only last 100 maintenance records
                            if len(self._maintenance_history) > 100:
                                self._maintenance_history = self._maintenance_history[
                                    -100:
                                ]

                        except Exception as e:
                            logger.error(
                                f"Maintenance task execution failed: {task.name} - {e}"
                            )

                # Sleep for 1 hour before checking again
                await asyncio.sleep(3600)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Maintenance scheduler error: {e}")
                await asyncio.sleep(3600)  # Continue after error

    async def run_task_now(self, task_name: str) -> dict[str, Any]:
        """Run a specific maintenance task immediately.

        Args:
            task_name: Name of the task to run

        Returns:
            Task execution result
        """
        task = next((t for t in self.tasks if t.name == task_name), None)
        if not task:
            raise ValueError(f"Task not found: {task_name}")

        return await task.execute()

    def get_scheduler_status(self) -> dict[str, Any]:
        """Get current scheduler status.

        Returns:
            Dictionary with scheduler status
        """
        task_status = []

        for task in self.tasks:
            next_run = task.get_next_run_time()

            task_info = {
                "name": task.name,
                "description": task.description,
                "interval_hours": task.interval_hours,
                "priority": task.priority,
                "is_due": task.is_due(),
                "last_run": task.last_run.isoformat() if task.last_run else None,
                "next_run": next_run.isoformat() if next_run else None,
                "run_count": task.run_count,
                "failure_count": task.failure_count,
                "last_duration_seconds": task.last_duration_seconds,
                "last_result": task.last_result,
            }

            task_status.append(task_info)

        return {
            "running": self._running,
            "total_tasks": len(self.tasks),
            "due_tasks": len([t for t in self.tasks if t.is_due()]),
            "tasks": task_status,
            "maintenance_history_count": len(self._maintenance_history),
            "status_timestamp": datetime.now().isoformat(),
        }

    def get_maintenance_history(self, limit: int = 20) -> list[dict[str, Any]]:
        """Get recent maintenance history.

        Args:
            limit: Maximum number of records to return

        Returns:
            List of maintenance records
        """
        return self._maintenance_history[-limit:] if self._maintenance_history else []


# Global maintenance scheduler instance
_maintenance_scheduler: MaintenanceScheduler | None = None


def get_maintenance_scheduler(db_path: str | None = None) -> MaintenanceScheduler:
    """Get the global maintenance scheduler instance.

    Args:
        db_path: Database path (only used for first call)

    Returns:
        MaintenanceScheduler instance
    """
    global _maintenance_scheduler
    if _maintenance_scheduler is None:
        _maintenance_scheduler = MaintenanceScheduler(db_path)
    return _maintenance_scheduler


async def start_maintenance_automation(db_path: str | None = None) -> None:
    """Start automated database maintenance.

    Args:
        db_path: Database path
    """
    scheduler = get_maintenance_scheduler(db_path)
    await scheduler.start_scheduler()


async def stop_maintenance_automation() -> None:
    """Stop automated database maintenance."""
    scheduler = get_maintenance_scheduler()
    await scheduler.stop_scheduler()
