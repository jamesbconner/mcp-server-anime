#!/usr/bin/env python3
"""Debug the cache workflow using local XML file."""

import argparse
import asyncio
import sys
from pathlib import Path

from src.mcp_server_anime.core.cache import generate_cache_key
from src.mcp_server_anime.core.persistent_cache import create_persistent_cache
from src.mcp_server_anime.providers.anidb.config import load_config
from src.mcp_server_anime.providers.anidb.xml_parser import parse_anime_details


async def debug_cache_workflow_with_local_xml(xml_filename: str):
    """Debug the cache workflow using local XML file.

    Args:
        xml_filename: Name of the XML file to use for testing
    """
    print(f"🔍 Debugging cache workflow with local XML file: {xml_filename}")

    # Step 1: Load local XML file
    xml_file = Path(xml_filename)
    if not xml_file.exists():
        print(f"❌ XML file not found: {xml_file}")
        print("   Please ensure the file exists in the current directory")
        return

    xml_content = xml_file.read_text(encoding="utf-8")
    print(f"✅ Loaded XML file: {len(xml_content)} characters")

    # Step 2: Parse XML to get anime details
    try:
        details = parse_anime_details(xml_content)
        print(f"✅ Parsed anime details: {details.title} (AID: {details.aid})")
    except Exception as e:
        print(f"❌ Failed to parse XML: {e}")
        return

    # Step 3: Load config
    config = load_config()
    print("✅ Config loaded:")
    print(f"  - persistent_cache_enabled: {config.persistent_cache_enabled}")
    print(f"  - persistent_cache_ttl: {config.persistent_cache_ttl}")
    print(f"  - cache_ttl: {config.cache_ttl}")
    print(f"  - cache_db_path: {config.cache_db_path}")

    # Step 4: Create persistent cache directly
    cache = await create_persistent_cache(
        provider_source="anidb",
        db_path=config.cache_db_path,
        memory_ttl=float(config.cache_ttl),
        persistent_ttl=float(config.persistent_cache_ttl),
        max_memory_size=config.memory_cache_size,
    )
    print(f"✅ Cache created: {type(cache).__name__}")
    print(f"  - Provider source: {cache.provider_source}")
    print(f"  - DB available: {cache._db_available}")

    try:
        # Step 5: Get initial cache stats
        initial_stats = await cache.get_stats()
        print("✅ Initial cache stats:")
        print(f"  - Memory entries: {initial_stats.memory_entries}")
        print(f"  - DB entries: {initial_stats.db_entries}")
        print(f"  - DB available: {initial_stats.db_available}")

        # Step 6: Generate cache key and store data manually
        cache_key = generate_cache_key("get_anime_details", aid=details.aid)
        print(f"✅ Generated cache key: {cache_key}")

        # Step 7: Store in cache with XML content
        print("\n💾 Storing anime details in cache...")
        try:
            await cache.set(cache_key, details, source_data=xml_content)
            print("✅ Data stored in cache successfully")
        except Exception as e:
            print(f"❌ Failed to store in cache: {e}")
            import traceback

            traceback.print_exc()
            return

        # Step 8: Check cache stats after storage
        after_store_stats = await cache.get_stats()
        print("✅ After storage stats:")
        print(f"  - Memory entries: {after_store_stats.memory_entries}")
        print(f"  - DB entries: {after_store_stats.db_entries}")
        print(f"  - Total hits: {after_store_stats.total_hits}")
        print(f"  - Total misses: {after_store_stats.total_misses}")

        # Step 9: Check database directly
        try:
            db_stats = await cache._db.get_cache_stats()
            print("✅ Direct DB stats:")
            print(f"  - Total entries: {db_stats.get('total_entries', 'N/A')}")
            print(f"  - Active entries: {db_stats.get('active_entries', 'N/A')}")
            if "providers" in db_stats:
                providers = db_stats["providers"]
                print(f"  - Providers: {list(providers.keys())}")
                for provider, stats in providers.items():
                    print(
                        f"    - {provider}: {stats['count']} entries, {stats['total_size']} bytes"
                    )
        except Exception as e:
            print(f"❌ Failed to get DB stats: {e}")
            import traceback

            traceback.print_exc()

        # Step 10: Clear memory cache and try to retrieve (should hit DB)
        print("\n🧹 Clearing memory cache...")
        await cache._memory_cache.clear()

        # Step 11: Try to retrieve from cache (should hit database)
        print("🔄 Retrieving from cache (should hit database)...")
        retrieved = await cache.get(cache_key)
        if retrieved:
            print(f"✅ Retrieved from cache: {retrieved.title}")
        else:
            print("❌ Failed to retrieve from cache")

        # Step 12: Final cache stats
        final_stats = await cache.get_stats()
        print("✅ Final cache stats:")
        print(f"  - Memory hits: {final_stats.memory_hits}")
        print(f"  - Memory misses: {final_stats.memory_misses}")
        print(f"  - DB hits: {final_stats.db_hits}")
        print(f"  - DB misses: {final_stats.db_misses}")
        print(f"  - Total hits: {final_stats.total_hits}")
        print(f"  - Total misses: {final_stats.total_misses}")
        print(f"  - Hit rate: {final_stats.hit_rate:.1f}%")

    except Exception as e:
        print(f"❌ Error during cache operations: {e}")
        import traceback

        traceback.print_exc()

    finally:
        # Don't clear cache so we can inspect it
        print("\n💡 Cache entries preserved for inspection")
        print(f"   Database: {cache._db.db_path}")


def main():
    """Main function to handle command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Debug the cache workflow using local XML file",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    # Use default 22.xml file
  %(prog)s 17550.xml          # Use specific XML file
  %(prog)s evangelion.xml     # Use custom XML file
        """,
    )

    parser.add_argument(
        "xml_file",
        nargs="?",
        default="22.xml",
        help="XML file to use for testing (default: 22.xml)",
    )

    args = parser.parse_args()

    # Validate file exists before running async function
    xml_path = Path(args.xml_file)
    if not xml_path.exists():
        print(f"❌ Error: XML file not found: {xml_path}")
        print("   Please ensure the file exists in the current directory")
        print("   Available XML files:")

        # List available XML files in current directory
        xml_files = list(Path(".").glob("*.xml"))
        if xml_files:
            for xml_file in sorted(xml_files):
                print(f"     - {xml_file.name}")
        else:
            print("     (no XML files found in current directory)")

        sys.exit(1)

    # Run the async function
    asyncio.run(debug_cache_workflow_with_local_xml(args.xml_file))


if __name__ == "__main__":
    main()
