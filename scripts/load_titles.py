#!/usr/bin/env python3
"""Script to manually load AniDB titles from existing file."""

import asyncio
import gzip
from pathlib import Path
import sys

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from mcp_server_anime.core.multi_provider_db import get_multi_provider_database
from mcp_server_anime.providers.anidb.titles_downloader import TitlesDownloader


async def load_titles_from_file():
    """Load titles from the existing file into the database."""
    print("🔄 Loading AniDB titles from existing file...")
    
    # Initialize database and downloader
    db = get_multi_provider_database()
    downloader = TitlesDownloader()
    provider_name = "anidb"
    
    # Ensure provider is initialized
    await db.initialize_provider(provider_name)
    
    # Check if file exists
    titles_file_path = downloader.titles_file_path
    if not titles_file_path.exists():
        print(f"❌ Titles file not found: {titles_file_path}")
        return False
    
    print(f"📁 Found titles file: {titles_file_path}")
    print(f"📏 File size: {titles_file_path.stat().st_size:,} bytes")
    
    # Load titles data
    titles_data = []
    
    try:
        with gzip.open(titles_file_path, 'rt', encoding='utf-8') as f:
            line_count = 0
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                
                # Skip comments and empty lines
                if not line or line.startswith('#'):
                    continue
                
                try:
                    parts = line.split('|', 3)
                    if len(parts) != 4:
                        print(f"⚠️  Invalid line {line_num}: {line}")
                        continue
                    
                    aid = int(parts[0])
                    title_type = int(parts[1])
                    language = parts[2]
                    title = parts[3]
                    
                    titles_data.append((aid, title_type, language, title))
                    line_count += 1
                    
                    # Progress indicator
                    if line_count % 10000 == 0:
                        print(f"📖 Processed {line_count:,} titles...")
                        
                except (ValueError, IndexError) as e:
                    print(f"⚠️  Failed to parse line {line_num}: {line} - {e}")
                    continue
        
        print(f"📚 Parsed {len(titles_data):,} titles from file")
        
        # Bulk insert into database
        print("💾 Inserting titles into database...")
        titles_loaded = await db.bulk_insert_titles(provider_name, titles_data)
        print(f"✅ Successfully loaded {titles_loaded:,} titles into database")
        
        # Update metadata
        from datetime import datetime
        await db.set_provider_metadata(
            provider_name, "last_load_timestamp", datetime.now().isoformat()
        )
        await db.set_provider_metadata(
            provider_name, "last_load_count", str(titles_loaded)
        )
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to load titles: {e}")
        return False


async def main():
    """Main function."""
    success = await load_titles_from_file()
    if success:
        print("\n🎉 Titles loading completed successfully!")
        print("You can now test the search functionality.")
    else:
        print("\n💥 Titles loading failed!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())