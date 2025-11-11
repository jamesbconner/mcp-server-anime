"""SQLite database for AniDB titles with search functionality.

This module manages a local SQLite database of anime titles for fast searching.
It supports fuzzy matching and handles the AniDB titles file format.
"""

import gzip
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from .exceptions import DatabaseError
from .logging_config import get_logger

logger = get_logger(__name__)


class TitlesDatabase:
    """SQLite database for anime titles with search capabilities."""

    def __init__(self, db_path: str | None = None):
        """Initialize the titles database.

        Args:
            db_path: Path to SQLite database file. If None, uses default location.
        """
        if db_path is None:
            # Use user's cache directory
            cache_dir = Path.home() / ".cache" / "mcp-server-anime"
            cache_dir.mkdir(parents=True, exist_ok=True)
            db_path = cache_dir / "anime_titles.db"

        self.db_path = str(db_path)
        self.titles_file_path = str(Path(db_path).parent / "anime-titles.dat.gz")
        self._init_database()

    def _init_database(self) -> None:
        """Initialize the database schema."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS anime_titles (
                        aid INTEGER NOT NULL,
                        type INTEGER NOT NULL,
                        language TEXT NOT NULL,
                        title TEXT NOT NULL,
                        title_lower TEXT NOT NULL,
                        PRIMARY KEY (aid, type, language, title)
                    )
                """)

                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_title_lower
                    ON anime_titles(title_lower)
                """)

                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_aid
                    ON anime_titles(aid)
                """)

                conn.execute("""
                    CREATE TABLE IF NOT EXISTS metadata (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL
                    )
                """)

                conn.commit()
                logger.info("Database initialized successfully")

        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to initialize database: {e}") from e

    def get_last_update(self) -> datetime | None:
        """Get the timestamp of the last database update.

        Returns:
            Datetime of last update, or None if never updated
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT value FROM metadata WHERE key = 'last_update'"
                )
                result = cursor.fetchone()
                if result:
                    return datetime.fromisoformat(result[0])
                return None
        except sqlite3.Error as e:
            logger.error(f"Failed to get last update time: {e}")
            return None

    def needs_update(self) -> bool:
        """Check if the database needs updating.

        Returns:
            True if database should be updated (older than 1 day or empty)
        """
        last_update = self.get_last_update()
        if last_update is None:
            return True

        # Update if older than 23 hours (to be safe with daily limit)
        return datetime.now() - last_update > timedelta(hours=23)

    def load_from_file(self, file_path: str | None = None) -> int:
        """Load titles from AniDB titles file into database.

        Args:
            file_path: Path to anime-titles.dat.gz file. Uses default if None.

        Returns:
            Number of titles loaded

        Raises:
            DatabaseError: If loading fails
        """
        if file_path is None:
            file_path = self.titles_file_path

        if not os.path.exists(file_path):
            raise DatabaseError(f"Titles file not found: {file_path}")

        try:
            titles_loaded = 0

            with sqlite3.connect(self.db_path) as conn:
                # Clear existing data
                conn.execute("DELETE FROM anime_titles")

                # Load new data
                with gzip.open(file_path, "rt", encoding="utf-8") as f:
                    for line_num, line in enumerate(f, 1):
                        line = line.strip()

                        # Skip comments and empty lines
                        if not line or line.startswith("#"):
                            continue

                        try:
                            parts = line.split("|", 3)
                            if len(parts) != 4:
                                logger.warning(f"Invalid line {line_num}: {line}")
                                continue

                            aid = int(parts[0])
                            title_type = int(parts[1])
                            language = parts[2]
                            title = parts[3]
                            title_lower = title.lower()

                            conn.execute(
                                """
                                INSERT OR IGNORE INTO anime_titles
                                (aid, type, language, title, title_lower)
                                VALUES (?, ?, ?, ?, ?)
                            """,
                                (aid, title_type, language, title, title_lower),
                            )

                            titles_loaded += 1

                        except (ValueError, IndexError) as e:
                            logger.warning(
                                f"Failed to parse line {line_num}: {line} - {e}"
                            )
                            continue

                # Update metadata
                conn.execute(
                    """
                    INSERT OR REPLACE INTO metadata (key, value)
                    VALUES ('last_update', ?)
                """,
                    (datetime.now().isoformat(),),
                )

                conn.commit()

            logger.info(f"Loaded {titles_loaded} titles into database")
            return titles_loaded

        except (sqlite3.Error, OSError, gzip.BadGzipFile) as e:
            raise DatabaseError(f"Failed to load titles from file: {e}") from e

    def search_titles(
        self, query: str, limit: int = 10
    ) -> list[tuple[int, str, str, int]]:
        """Search for anime titles.

        Args:
            query: Search query string
            limit: Maximum number of results

        Returns:
            List of tuples: (aid, title, language, type)
            Sorted by relevance (exact matches first, then partial matches)
        """
        if not query or len(query.strip()) < 2:
            return []

        query_lower = query.strip().lower()

        try:
            with sqlite3.connect(self.db_path) as conn:
                # First, try exact matches
                exact_results = conn.execute(
                    """
                    SELECT DISTINCT aid, title, language, type
                    FROM anime_titles
                    WHERE title_lower = ?
                    ORDER BY type ASC, language ASC
                    LIMIT ?
                """,
                    (query_lower, limit),
                ).fetchall()

                if len(exact_results) >= limit:
                    return exact_results

                # Then try prefix matches
                remaining_limit = limit - len(exact_results)
                prefix_results = conn.execute(
                    """
                    SELECT DISTINCT aid, title, language, type
                    FROM anime_titles
                    WHERE title_lower LIKE ? AND title_lower != ?
                    ORDER BY type ASC, language ASC
                    LIMIT ?
                """,
                    (f"{query_lower}%", query_lower, remaining_limit),
                ).fetchall()

                # Combine results
                all_results = exact_results + prefix_results
                if len(all_results) >= limit:
                    return all_results[:limit]

                # Finally, try substring matches
                remaining_limit = limit - len(all_results)
                substring_results = conn.execute(
                    """
                    SELECT DISTINCT aid, title, language, type
                    FROM anime_titles
                    WHERE title_lower LIKE ?
                    AND title_lower NOT LIKE ?
                    AND title_lower != ?
                    ORDER BY type ASC, language ASC
                    LIMIT ?
                """,
                    (
                        f"%{query_lower}%",
                        f"{query_lower}%",
                        query_lower,
                        remaining_limit,
                    ),
                ).fetchall()

                return (all_results + substring_results)[:limit]

        except sqlite3.Error as e:
            logger.error(f"Search failed: {e}")
            return []

    def get_titles_for_aid(self, aid: int) -> list[tuple[str, str, int]]:
        """Get all titles for a specific anime ID.

        Args:
            aid: Anime ID

        Returns:
            List of tuples: (title, language, type)
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                return conn.execute(
                    """
                    SELECT title, language, type
                    FROM anime_titles
                    WHERE aid = ?
                    ORDER BY type ASC, language ASC
                """,
                    (aid,),
                ).fetchall()
        except sqlite3.Error as e:
            logger.error(f"Failed to get titles for aid {aid}: {e}")
            return []

    def get_stats(self) -> dict:
        """Get database statistics.

        Returns:
            Dictionary with database statistics
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                total_titles = conn.execute(
                    "SELECT COUNT(*) FROM anime_titles"
                ).fetchone()[0]
                unique_anime = conn.execute(
                    "SELECT COUNT(DISTINCT aid) FROM anime_titles"
                ).fetchone()[0]
                last_update = self.get_last_update()

                return {
                    "total_titles": total_titles,
                    "unique_anime": unique_anime,
                    "last_update": last_update.isoformat() if last_update else None,
                    "needs_update": self.needs_update(),
                }
        except sqlite3.Error as e:
            logger.error(f"Failed to get database stats: {e}")
            return {"error": str(e)}
