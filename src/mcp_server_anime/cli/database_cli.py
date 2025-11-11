#!/usr/bin/env python3
"""Database management CLI for MCP Anime Server.

This module provides command-line tools for database initialization, maintenance,
health checking, and troubleshooting of the local anime database.
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Handle imports for both direct execution and module execution
try:
    # Try relative imports first (when run as module with python -m)
    from mcp_server_anime.core.database_config import (
        get_local_db_config,
        validate_config,
    )
    from mcp_server_anime.core.index_optimization import create_index_optimizer
    from mcp_server_anime.core.multi_provider_db import get_multi_provider_database
    from mcp_server_anime.core.schema_manager import create_schema_manager
    from mcp_server_anime.core.transaction_logger import get_transaction_logger
    from mcp_server_anime.providers.anidb.search_service import get_search_service
    from mcp_server_anime.providers.anidb.titles_downloader import TitlesDownloader
except ImportError:
    # Fall back to absolute imports (when run directly)
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))
    from mcp_server_anime.core.database_config import (
        get_local_db_config,
        validate_config,
    )
    from mcp_server_anime.core.index_optimization import create_index_optimizer
    from mcp_server_anime.core.multi_provider_db import get_multi_provider_database
    from mcp_server_anime.core.schema_manager import create_schema_manager
    from mcp_server_anime.core.transaction_logger import get_transaction_logger
    from mcp_server_anime.providers.anidb.search_service import get_search_service
    from mcp_server_anime.providers.anidb.titles_downloader import TitlesDownloader


class DatabaseCLI:
    """Command-line interface for database management."""

    def __init__(self):
        """Initialize the CLI."""
        self.config = get_local_db_config()
        self.db = get_multi_provider_database(self.config.database.database_path)

    async def init_database(
        self, provider: str = "anidb", force: bool = False
    ) -> dict[str, Any]:
        """Initialize database for a provider.

        Args:
            provider: Provider name to initialize
            force: Force reinitialization if already exists

        Returns:
            Dictionary with initialization results
        """
        print(f"🔧 Initializing database for provider: {provider}")

        try:
            # Check if already initialized
            if not force:
                stats = await self.db.get_database_stats()
                if provider in stats.get("initialized_providers", []):
                    provider_stats = stats.get("providers", {}).get(provider, {})
                    if provider_stats.get("total_titles", 0) > 0:
                        print(
                            f"⚠️  Provider {provider} already initialized with {provider_stats['total_titles']} titles"
                        )
                        print("   Use --force to reinitialize")
                        return {
                            "success": False,
                            "reason": "already_initialized",
                            "stats": provider_stats,
                        }

            # Initialize provider
            await self.db.initialize_provider(provider)
            print(f"✅ Provider {provider} initialized successfully")

            # Get updated stats
            stats = await self.db.get_database_stats()
            provider_stats = stats.get("providers", {}).get(provider, {})

            return {
                "success": True,
                "provider": provider,
                "stats": provider_stats,
                "initialized_at": datetime.now().isoformat(),
            }

        except Exception as e:
            print(f"❌ Failed to initialize database: {e}")
            return {"success": False, "error": str(e)}

    async def check_database(self, provider: str | None = None) -> dict[str, Any]:
        """Check database health and status.

        Args:
            provider: Specific provider to check (None for all)

        Returns:
            Dictionary with health check results
        """
        print("🔍 Checking database health...")

        try:
            # Get overall database stats
            stats = await self.db.get_database_stats()

            # Check schema
            schema_manager = create_schema_manager(self.config.database.database_path)
            schema_info = schema_manager.get_schema_info()
            validation_info = schema_manager.validate_database_integrity()

            # Check configuration
            config_issues = validate_config()

            health_report = {
                "timestamp": datetime.now().isoformat(),
                "overall_health": "healthy"
                if validation_info["valid"] and not config_issues
                else "issues",
                "database_stats": stats,
                "schema_info": schema_info,
                "validation": validation_info,
                "configuration_issues": config_issues,
                "providers": {},
            }

            # Check specific providers
            providers_to_check = (
                [provider] if provider else stats.get("initialized_providers", [])
            )

            for prov in providers_to_check:
                provider_stats = stats.get("providers", {}).get(prov, {})

                # Check if provider has data
                has_data = provider_stats.get("total_titles", 0) > 0
                last_update = provider_stats.get("last_update")

                provider_health = {
                    "initialized": prov in stats.get("initialized_providers", []),
                    "has_data": has_data,
                    "total_titles": provider_stats.get("total_titles", 0),
                    "unique_anime": provider_stats.get("unique_anime", 0),
                    "last_update": last_update,
                    "status": "healthy" if has_data else "no_data",
                }

                health_report["providers"][prov] = provider_health

            # Print summary
            print(f"📊 Database Health: {health_report['overall_health'].upper()}")
            print(
                f"   Initialized providers: {len(stats.get('initialized_providers', []))}"
            )
            print(
                f"   Total searches logged: {stats.get('search_transactions', {}).get('total_searches', 0)}"
            )

            if config_issues:
                print(f"⚠️  Configuration issues: {len(config_issues)}")
                for issue in config_issues:
                    print(f"   - {issue}")

            for prov, prov_health in health_report["providers"].items():
                status_icon = "✅" if prov_health["status"] == "healthy" else "⚠️"
                print(f"   {status_icon} {prov}: {prov_health['total_titles']} titles")

            return health_report

        except Exception as e:
            print(f"❌ Health check failed: {e}")
            return {"success": False, "error": str(e)}

    async def cleanup_database(
        self, provider: str | None = None, retention_days: int | None = None
    ) -> dict[str, Any]:
        """Clean up old data and optimize database.

        Args:
            provider: Specific provider to clean (None for all)
            retention_days: Days to retain transaction data

        Returns:
            Dictionary with cleanup results
        """
        print("🧹 Starting database cleanup...")

        try:
            cleanup_results = {
                "timestamp": datetime.now().isoformat(),
                "operations": [],
                "total_cleaned": 0,
            }

            # Clean up transaction logs
            transaction_logger = get_transaction_logger()
            retention = retention_days or self.config.transaction.retention_days

            deleted_transactions = await transaction_logger.cleanup_old_transactions(
                retention
            )
            cleanup_results["operations"].append(
                {
                    "operation": "transaction_cleanup",
                    "deleted_count": deleted_transactions,
                    "retention_days": retention,
                }
            )
            cleanup_results["total_cleaned"] += deleted_transactions

            print(f"   🗑️  Cleaned {deleted_transactions} old transaction records")

            # Optimize database
            optimizer = create_index_optimizer(self.config.database.database_path)
            optimization_results = optimizer.optimize_database(provider)

            cleanup_results["operations"].append(
                {"operation": "database_optimization", "results": optimization_results}
            )

            print("   ⚡ Database optimization completed")

            print(
                f"✅ Cleanup completed: {cleanup_results['total_cleaned']} items cleaned"
            )
            return cleanup_results

        except Exception as e:
            print(f"❌ Cleanup failed: {e}")
            return {"success": False, "error": str(e)}

    async def migrate_database(
        self, target_version: str | None = None, dry_run: bool = False
    ) -> dict[str, Any]:
        """Migrate database schema to target version.

        Args:
            target_version: Target schema version (None for latest)
            dry_run: Only validate migration without applying

        Returns:
            Dictionary with migration results
        """
        action = "Validating" if dry_run else "Migrating"
        print(f"🔄 {action} database schema...")

        try:
            schema_manager = create_schema_manager(self.config.database.database_path)

            current_version = schema_manager.get_current_database_version()
            latest_version = schema_manager.current_version
            target = target_version or latest_version

            print(f"   Current version: {current_version or 'None'}")
            print(f"   Target version: {target}")

            if not schema_manager.needs_migration():
                print("✅ Database is already at the latest version")
                return {
                    "success": True,
                    "message": "No migration needed",
                    "current_version": current_version,
                    "target_version": target,
                }

            # Perform migration
            migration_results = schema_manager.migrate_database(target, dry_run=dry_run)

            if migration_results["success"]:
                if dry_run:
                    print(
                        f"✅ Migration validation successful: {migration_results['migrations_needed']} migrations would be applied"
                    )
                else:
                    print(
                        f"✅ Migration completed: {migration_results['migrations_needed']} migrations applied"
                    )
            else:
                print(
                    f"❌ Migration failed: {migration_results.get('error', 'Unknown error')}"
                )

            return migration_results

        except Exception as e:
            print(f"❌ Migration failed: {e}")
            return {"success": False, "error": str(e)}

    async def download_titles(
        self, provider: str = "anidb", force: bool = False
    ) -> dict[str, Any]:
        """Download titles file for a provider.

        Args:
            provider: Provider to download titles for
            force: Force download bypassing rate limits

        Returns:
            Dictionary with download results
        """
        print(f"📥 Downloading titles for provider: {provider}")

        if provider != "anidb":
            print(f"❌ Provider {provider} not supported for downloads")
            return {"success": False, "error": "Provider not supported"}

        try:
            downloader = TitlesDownloader(
                protection_hours=self.config.download.protection_hours
            )

            # Check download status
            if not force:
                can_download, error_message = await downloader.can_download()
                if not can_download:
                    print(f"⚠️  {error_message}")
                    return {
                        "success": False,
                        "reason": "rate_limited",
                        "message": error_message,
                    }

            # Perform download
            if force:
                print("⚠️  Forcing download (bypassing rate limits)")

            success = await downloader.download_titles_file(force=force)

            if success:
                # Load into database
                search_service = get_search_service()
                await (
                    search_service.force_update()
                ) if force else await search_service.ensure_database_ready()

                # Get updated stats
                stats = await self.db.get_database_stats()
                provider_stats = stats.get("providers", {}).get(provider, {})

                print(
                    f"✅ Download completed: {provider_stats.get('total_titles', 0)} titles loaded"
                )

                return {
                    "success": True,
                    "provider": provider,
                    "titles_loaded": provider_stats.get("total_titles", 0),
                    "download_time": datetime.now().isoformat(),
                }
            else:
                print("❌ Download failed")
                return {"success": False, "error": "Download failed"}

        except Exception as e:
            print(f"❌ Download failed: {e}")
            return {"success": False, "error": str(e)}

    def print_config(self) -> None:
        """Print current configuration."""
        print("⚙️  Current Configuration:")
        print("=" * 50)

        summary = self.config.get_summary()

        print(f"Environment: {summary['environment']}")
        print(f"Debug Mode: {summary['debug_mode']}")
        print()

        print("Database:")
        for key, value in summary["database"].items():
            print(f"  {key}: {value}")
        print()

        print("Download:")
        for key, value in summary["download"].items():
            print(f"  {key}: {value}")
        print()

        print("Search:")
        for key, value in summary["search"].items():
            print(f"  {key}: {value}")
        print()

        print("Transaction:")
        for key, value in summary["transaction"].items():
            print(f"  {key}: {value}")


async def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="MCP Anime Server Database Management CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s init-database --provider anidb
  %(prog)s check-database
  %(prog)s cleanup-database --retention-days 30
  %(prog)s migrate-database --dry-run
  %(prog)s download-titles --provider anidb
  %(prog)s config
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # init-database command
    init_parser = subparsers.add_parser(
        "init-database", help="Initialize database for a provider"
    )
    init_parser.add_argument(
        "--provider", default="anidb", help="Provider to initialize (default: anidb)"
    )
    init_parser.add_argument(
        "--force", action="store_true", help="Force reinitialization"
    )

    # check-database command
    check_parser = subparsers.add_parser(
        "check-database", help="Check database health and status"
    )
    check_parser.add_argument("--provider", help="Specific provider to check")
    check_parser.add_argument(
        "--json", action="store_true", help="Output results as JSON"
    )

    # cleanup-database command
    cleanup_parser = subparsers.add_parser(
        "cleanup-database", help="Clean up old data and optimize"
    )
    cleanup_parser.add_argument("--provider", help="Specific provider to clean")
    cleanup_parser.add_argument(
        "--retention-days", type=int, help="Days to retain transaction data"
    )
    cleanup_parser.add_argument(
        "--json", action="store_true", help="Output results as JSON"
    )

    # migrate-database command
    migrate_parser = subparsers.add_parser(
        "migrate-database", help="Migrate database schema"
    )
    migrate_parser.add_argument("--target-version", help="Target schema version")
    migrate_parser.add_argument(
        "--dry-run", action="store_true", help="Validate migration without applying"
    )
    migrate_parser.add_argument(
        "--json", action="store_true", help="Output results as JSON"
    )

    # download-titles command
    download_parser = subparsers.add_parser(
        "download-titles", help="Download titles file"
    )
    download_parser.add_argument(
        "--provider", default="anidb", help="Provider to download for (default: anidb)"
    )
    download_parser.add_argument(
        "--force", action="store_true", help="Force download bypassing rate limits"
    )
    download_parser.add_argument(
        "--json", action="store_true", help="Output results as JSON"
    )

    # config command
    subparsers.add_parser("config", help="Show current configuration")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    cli = DatabaseCLI()

    try:
        if args.command == "init-database":
            result = await cli.init_database(args.provider, args.force)
            if hasattr(args, "json") and args.json:
                print(json.dumps(result, indent=2))

        elif args.command == "check-database":
            result = await cli.check_database(args.provider)
            if args.json:
                print(json.dumps(result, indent=2))

        elif args.command == "cleanup-database":
            result = await cli.cleanup_database(args.provider, args.retention_days)
            if args.json:
                print(json.dumps(result, indent=2))

        elif args.command == "migrate-database":
            result = await cli.migrate_database(args.target_version, args.dry_run)
            if args.json:
                print(json.dumps(result, indent=2))

        elif args.command == "download-titles":
            result = await cli.download_titles(args.provider, args.force)
            if args.json:
                print(json.dumps(result, indent=2))

        elif args.command == "config":
            cli.print_config()

    except KeyboardInterrupt:
        print("\n⚠️  Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
