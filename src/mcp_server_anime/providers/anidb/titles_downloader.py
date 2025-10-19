"""Safe downloader for AniDB titles file with enhanced 36-hour rate limiting.

This module handles downloading the anime-titles.dat.gz file from AniDB
with strict 36-hour rate limiting and provider metadata integration to prevent bans.
"""

import gzip
from datetime import datetime, timedelta
from pathlib import Path

import httpx

from ...core.exceptions import APIError, NetworkError
from ...core.logging_config import get_logger
from ...core.multi_provider_db import get_multi_provider_database

logger = get_logger(__name__)


class TitlesDownloader:
    """Safe downloader for AniDB titles file with 36-hour rate limiting."""

    TITLES_URL = "https://anidb.net/api/anime-titles.dat.gz"
    PROTECTION_HOURS = 36  # Strict 36-hour protection period

    def __init__(self, cache_dir: str | None = None, protection_hours: int = 36):
        """Initialize the downloader with enhanced protection.

        Args:
            cache_dir: Directory to store downloaded files. Uses default if None.
            protection_hours: Hours to wait between downloads (default: 36)
        """
        if cache_dir is None:
            cache_dir = Path.home() / ".cache" / "mcp-server-anime"

        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.protection_hours = protection_hours

        self.titles_file_path = self.cache_dir / "anime-titles.dat.gz"
        self.download_log_path = self.cache_dir / "download_log.txt"

        # Initialize database connection for metadata storage
        self.db = get_multi_provider_database()
        self.provider_name = "anidb"

    def _log_download_attempt(self) -> None:
        """Log a download attempt with timestamp."""
        try:
            with open(self.download_log_path, "a", encoding="utf-8") as f:
                f.write(f"{datetime.now().isoformat()}\n")
        except OSError as e:
            logger.warning(f"Failed to log download attempt: {e}")

    def _get_last_download_time(self) -> datetime | None:
        """Get the timestamp of the last download attempt.

        Returns:
            Datetime of last download, or None if never downloaded
        """
        if not self.download_log_path.exists():
            return None

        try:
            with open(self.download_log_path, encoding="utf-8") as f:
                lines = f.readlines()
                if lines:
                    last_line = lines[-1].strip()
                    return datetime.fromisoformat(last_line)
        except (OSError, ValueError) as e:
            logger.warning(f"Failed to read download log: {e}")

        return None

    async def can_download(self) -> tuple[bool, str | None]:
        """Check if it's safe to download with enhanced 36-hour protection.

        Returns:
            Tuple of (can_download, error_message)
            - can_download: True if download is allowed
            - error_message: Detailed error message if download not allowed
        """
        # Initialize provider in database if needed
        await self.db.initialize_provider(self.provider_name)

        # Check database metadata first (preferred method)
        last_download_str = await self.db.get_provider_metadata(
            self.provider_name, "last_download_timestamp"
        )

        last_download = None
        if last_download_str:
            try:
                last_download = datetime.fromisoformat(last_download_str)
            except ValueError:
                logger.warning(
                    f"Invalid last download timestamp in database: {last_download_str}"
                )

        # Fallback to file-based log if no database record
        if last_download is None:
            last_download = self._get_last_download_time()

        if last_download is None:
            return True, None

        # Calculate time since last download
        time_since_last = datetime.now() - last_download
        hours_since_last = time_since_last.total_seconds() / 3600

        if hours_since_last < self.protection_hours:
            hours_remaining = self.protection_hours - hours_since_last
            next_allowed = last_download + timedelta(hours=self.protection_hours)

            error_message = (
                f"Download rate limited. Last download was {hours_since_last:.1f} hours ago. "
                f"Must wait {self.protection_hours} hours between downloads. "
                f"Next download allowed at {next_allowed.isoformat()} "
                f"({hours_remaining:.1f} hours remaining)."
            )

            return False, error_message

        return True, None

    def get_file_info(self) -> dict:
        """Get information about the current titles file.

        Returns:
            Dictionary with file information
        """
        if not self.titles_file_path.exists():
            return {"exists": False, "size": 0, "modified": None, "age_hours": None}

        stat = self.titles_file_path.stat()
        modified = datetime.fromtimestamp(stat.st_mtime)
        age_hours = (datetime.now() - modified).total_seconds() / 3600

        return {
            "exists": True,
            "size": stat.st_size,
            "modified": modified.isoformat(),
            "age_hours": age_hours,
        }

    def needs_download(self) -> bool:
        """Check if the titles file needs to be downloaded.

        Returns:
            True if file should be downloaded
        """
        file_info = self.get_file_info()

        # Download if file doesn't exist
        if not file_info["exists"]:
            return True

        # Download if file is older than 24 hours
        if file_info["age_hours"] and file_info["age_hours"] > 24:
            return True

        # Download if file is empty or very small (likely corrupted)
        if file_info["size"] < 1000:  # Expect at least 1KB
            return True

        return False

    async def download_titles_file(self, force: bool = False) -> bool:
        """Download the AniDB titles file with enhanced protection.

        Args:
            force: If True, bypass safety checks (use with caution!)

        Returns:
            True if download was successful, False otherwise

        Raises:
            APIError: If download is not allowed due to rate limiting
            NetworkError: If download fails due to network issues
        """
        # Safety check: respect 36-hour download limit
        if not force:
            can_download, error_message = await self.can_download()
            if not can_download:
                # Log the download attempt for audit trail
                await self._log_download_attempt_to_db("blocked", error_message)
                raise APIError(error_message, code="DOWNLOAD_RATE_LIMITED")

        # Check if download is actually needed
        if not force and not self.needs_download():
            logger.info("Titles file is up to date, skipping download")
            return True

        logger.info(f"Downloading titles file from {self.TITLES_URL}")

        try:
            # Log the download attempt to both file and database
            self._log_download_attempt()
            await self._log_download_attempt_to_db("started", "Download initiated")

            # Download with proper timeout and user agent
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(60.0),  # 60 second timeout
                follow_redirects=True,  # Follow HTTP redirects (301, 302, etc.)
                headers={
                    "User-Agent": "mcp-server-anime/1.0 (https://github.com/example/mcp-server-anime)"
                },
            ) as client:
                response = await client.get(self.TITLES_URL)
                response.raise_for_status()

                # Log response details for debugging
                logger.info(
                    f"Download response: status={response.status_code}, size={len(response.content)} bytes, content-type={response.headers.get('content-type', 'unknown')}"
                )

                # Verify it's a gzip file
                if not response.content.startswith(b"\x1f\x8b"):
                    raise APIError(
                        "Downloaded file is not a valid gzip file", code="INVALID_FILE"
                    )

                # Test that we can decompress it - try full decompression for small files
                try:
                    if (
                        len(response.content) < 10000000
                    ):  # Less than 10MB, decompress fully
                        gzip.decompress(response.content)
                    else:
                        gzip.decompress(
                            response.content[:1000]
                        )  # Test first 1KB for large files
                except gzip.BadGzipFile as e:
                    raise APIError(
                        f"Downloaded file is corrupted: {e}", code="CORRUPTED_FILE"
                    )

                # Save to temporary file first
                temp_path = self.titles_file_path.with_suffix(".tmp")
                with open(temp_path, "wb") as f:
                    f.write(response.content)

                # Verify file size is reasonable (should be several MB)
                if temp_path.stat().st_size < 100000:  # Less than 100KB is suspicious
                    temp_path.unlink()
                    raise APIError(
                        "Downloaded file is too small, likely invalid",
                        code="INVALID_FILE",
                    )

                # Move to final location
                temp_path.replace(self.titles_file_path)

                # Update database metadata with successful download
                download_timestamp = datetime.now().isoformat()
                file_size = self.titles_file_path.stat().st_size

                await self.db.set_provider_metadata(
                    self.provider_name, "last_download_timestamp", download_timestamp
                )
                await self.db.set_provider_metadata(
                    self.provider_name, "last_download_size", str(file_size)
                )
                await self.db.set_provider_metadata(
                    self.provider_name, "last_download_status", "success"
                )

                # Log successful download
                await self._log_download_attempt_to_db(
                    "success", f"Successfully downloaded {file_size} bytes"
                )

                logger.info(f"Successfully downloaded titles file: {file_size} bytes")
                return True

        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP error downloading titles file: {e.response.status_code}"
            await self._log_download_attempt_to_db("failed", error_msg)
            raise NetworkError(error_msg) from e
        except httpx.RequestError as e:
            error_msg = f"Network error downloading titles file: {e}"
            await self._log_download_attempt_to_db("failed", error_msg)
            raise NetworkError(error_msg) from e
        except OSError as e:
            error_msg = f"File system error: {e}"
            await self._log_download_attempt_to_db("failed", error_msg)
            raise APIError(error_msg, code="FILE_ERROR") from e

    def verify_file_integrity(self) -> bool:
        """Verify the integrity of the downloaded titles file.

        Returns:
            True if file appears to be valid
        """
        if not self.titles_file_path.exists():
            return False

        try:
            # Test decompression and basic format
            with gzip.open(self.titles_file_path, "rt", encoding="utf-8") as f:
                line_count = 0
                valid_lines = 0

                for line in f:
                    line_count += 1
                    line = line.strip()

                    # Skip comments
                    if line.startswith("#") or not line:
                        continue

                    # Check basic format: aid|type|lang|title
                    parts = line.split("|", 3)
                    if len(parts) == 4:
                        try:
                            int(parts[0])  # aid should be integer
                            int(parts[1])  # type should be integer
                            valid_lines += 1
                        except ValueError:
                            pass

                    # Don't check entire file, just first 1000 lines
                    if line_count > 1000:
                        break

                # File should have at least some valid lines
                return valid_lines > 100

        except (gzip.BadGzipFile, OSError, UnicodeDecodeError) as e:
            logger.error(f"File integrity check failed: {e}")
            return False

    async def _log_download_attempt_to_db(self, status: str, message: str) -> None:
        """Log download attempt to database metadata.

        Args:
            status: Status of the download attempt (started, success, failed, blocked)
            message: Detailed message about the attempt
        """
        try:
            await self.db.initialize_provider(self.provider_name)

            # Store the attempt with timestamp
            attempt_data = {
                "timestamp": datetime.now().isoformat(),
                "status": status,
                "message": message,
                "protection_hours": self.protection_hours,
            }

            await self.db.set_provider_metadata(
                self.provider_name,
                f"download_attempt_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                str(attempt_data),
            )

            # Update latest attempt status
            await self.db.set_provider_metadata(
                self.provider_name, "last_download_attempt_status", status
            )
            await self.db.set_provider_metadata(
                self.provider_name, "last_download_attempt_message", message
            )

        except Exception as e:
            logger.warning(f"Failed to log download attempt to database: {e}")

    async def get_download_status(self) -> dict:
        """Get comprehensive download status information.

        Returns:
            Dictionary with download status details
        """
        # Initialize provider if needed
        await self.db.initialize_provider(self.provider_name)

        # Get database metadata
        last_download_str = await self.db.get_provider_metadata(
            self.provider_name, "last_download_timestamp"
        )
        last_download_size = await self.db.get_provider_metadata(
            self.provider_name, "last_download_size"
        )
        last_download_status = await self.db.get_provider_metadata(
            self.provider_name, "last_download_status"
        )

        # Check download capability
        can_download, error_message = await self.can_download()

        # Calculate next allowed download time
        next_allowed_download = None
        if last_download_str:
            try:
                last_download = datetime.fromisoformat(last_download_str)
                next_allowed_download = (
                    last_download + timedelta(hours=self.protection_hours)
                ).isoformat()
            except ValueError:
                pass

        return {
            "file_info": self.get_file_info(),
            "can_download": can_download,
            "download_error": error_message,
            "needs_download": self.needs_download(),
            "protection_hours": self.protection_hours,
            "last_download": last_download_str,
            "last_download_size": int(last_download_size)
            if last_download_size
            else None,
            "last_download_status": last_download_status,
            "next_allowed_download": next_allowed_download,
            "file_valid": self.verify_file_integrity()
            if self.titles_file_path.exists()
            else False,
        }

    async def get_download_history(self, limit: int = 10) -> list:
        """Get recent download attempt history.

        Args:
            limit: Maximum number of attempts to return

        Returns:
            List of recent download attempts
        """
        try:
            await self.db.initialize_provider(self.provider_name)

            # This would require a more sophisticated metadata query system
            # For now, return basic info from current metadata
            last_status = await self.db.get_provider_metadata(
                self.provider_name, "last_download_attempt_status"
            )
            last_message = await self.db.get_provider_metadata(
                self.provider_name, "last_download_attempt_message"
            )
            last_timestamp = await self.db.get_provider_metadata(
                self.provider_name, "last_download_timestamp"
            )

            history = []
            if last_status and last_timestamp:
                history.append(
                    {
                        "timestamp": last_timestamp,
                        "status": last_status,
                        "message": last_message or "No message",
                        "protection_hours": self.protection_hours,
                    }
                )

            return history

        except Exception as e:
            logger.error(f"Failed to get download history: {e}")
            return []

    async def validate_download_integrity(self) -> dict:
        """Validate download integrity with comprehensive checks.

        Returns:
            Dictionary with validation results
        """
        validation_result = {
            "file_exists": False,
            "file_size_valid": False,
            "file_format_valid": False,
            "content_valid": False,
            "metadata_consistent": False,
            "overall_valid": False,
            "issues": [],
            "file_info": {},
            "validation_timestamp": datetime.now().isoformat(),
        }

        try:
            # Check file existence
            if not self.titles_file_path.exists():
                validation_result["issues"].append("Titles file does not exist")
                return validation_result

            validation_result["file_exists"] = True
            file_info = self.get_file_info()
            validation_result["file_info"] = file_info

            # Check file size
            if file_info["size"] < 100000:  # Less than 100KB is suspicious
                validation_result["issues"].append(
                    f"File size too small: {file_info['size']} bytes"
                )
            else:
                validation_result["file_size_valid"] = True

            # Check file format (gzip)
            try:
                with open(self.titles_file_path, "rb") as f:
                    header = f.read(2)
                    if header == b"\x1f\x8b":
                        validation_result["file_format_valid"] = True
                    else:
                        validation_result["issues"].append(
                            "File is not a valid gzip file"
                        )
            except OSError as e:
                validation_result["issues"].append(f"Cannot read file: {e}")

            # Check content validity
            if self.verify_file_integrity():
                validation_result["content_valid"] = True
            else:
                validation_result["issues"].append("File content validation failed")

            # Check metadata consistency
            await self.db.initialize_provider(self.provider_name)
            stored_size = await self.db.get_provider_metadata(
                self.provider_name, "last_download_size"
            )

            if stored_size and int(stored_size) == file_info["size"]:
                validation_result["metadata_consistent"] = True
            else:
                validation_result["issues"].append(
                    f"File size mismatch: file={file_info['size']}, metadata={stored_size}"
                )

            # Overall validation
            validation_result["overall_valid"] = (
                validation_result["file_exists"]
                and validation_result["file_size_valid"]
                and validation_result["file_format_valid"]
                and validation_result["content_valid"]
                and validation_result["metadata_consistent"]
            )

        except Exception as e:
            validation_result["issues"].append(f"Validation error: {e}")
            logger.error(f"Download validation failed: {e}")

        return validation_result

    async def cleanup_old_metadata(self, retention_days: int = 30) -> dict:
        """Clean up old download metadata entries.

        Args:
            retention_days: Number of days to retain metadata

        Returns:
            Dictionary with cleanup results
        """
        cleanup_result = {
            "cleaned_entries": 0,
            "retention_days": retention_days,
            "cleanup_timestamp": datetime.now().isoformat(),
            "success": False,
        }

        try:
            await self.db.initialize_provider(self.provider_name)

            # Note: This is a simplified cleanup since we don't have a full
            # metadata query system yet. In a full implementation, we would
            # query for old download_attempt_* entries and remove them.

            # For now, just log the cleanup attempt
            await self.db.set_provider_metadata(
                self.provider_name, "last_metadata_cleanup", datetime.now().isoformat()
            )

            cleanup_result["success"] = True
            logger.info(
                f"Metadata cleanup completed (retention: {retention_days} days)"
            )

        except Exception as e:
            logger.error(f"Metadata cleanup failed: {e}")
            cleanup_result["error"] = str(e)

        return cleanup_result

    async def reset_download_protection(self) -> dict:
        """Reset download protection (emergency use only).

        Returns:
            Dictionary with reset results
        """
        reset_result = {
            "success": False,
            "reset_timestamp": datetime.now().isoformat(),
            "warning": "This bypasses safety protections and should only be used in emergencies",
        }

        try:
            await self.db.initialize_provider(self.provider_name)

            # Clear download timestamp to allow immediate download
            await self.db.set_provider_metadata(
                self.provider_name, "last_download_timestamp", ""
            )

            # Log the reset for audit trail
            await self._log_download_attempt_to_db(
                "protection_reset",
                "Download protection manually reset - emergency override",
            )

            reset_result["success"] = True
            logger.warning(
                "Download protection has been reset - use with extreme caution"
            )

        except Exception as e:
            logger.error(f"Failed to reset download protection: {e}")
            reset_result["error"] = str(e)

        return reset_result
