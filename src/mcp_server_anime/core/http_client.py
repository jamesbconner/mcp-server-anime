"""HTTP client with rate limiting and retry logic for API requests.

This module provides an HTTP client with rate limiting, retry logic with exponential backoff,
and connection pooling. It's designed to be generic and can be used by any provider.
"""

import asyncio
import time
from typing import Any

import httpx
from pydantic import BaseModel

from .error_handler import with_error_handling
from .exceptions import APIError, RateLimitError
from .logging_config import get_logger, log_api_request

logger = get_logger(__name__)


class RateLimiter:
    """Rate limiter to ensure compliance with API rate limits.

    Implements a simple rate limiter that enforces a minimum delay between requests
    to comply with API rate limiting requirements.
    """

    def __init__(self, delay: float) -> None:
        """Initialize the rate limiter.

        Args:
            delay: Minimum delay between requests in seconds
        """
        self.delay = delay
        self._last_request_time: float | None = None
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Acquire permission to make a request, waiting if necessary.

        This method ensures that requests are spaced apart by at least the
        configured delay period.
        """
        async with self._lock:
            if self._last_request_time is not None:
                elapsed = time.time() - self._last_request_time
                if elapsed < self.delay:
                    wait_time = self.delay - elapsed
                    logger.debug(f"Rate limiting: waiting {wait_time:.2f} seconds")
                    await asyncio.sleep(wait_time)

            self._last_request_time = time.time()


class RetryConfig(BaseModel):
    """Configuration for retry logic."""

    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for a given retry attempt.

        Args:
            attempt: The retry attempt number (0-based)

        Returns:
            Delay in seconds for this attempt
        """
        delay = self.base_delay * (self.exponential_base**attempt)
        return min(delay, self.max_delay)


class HTTPClient:
    """HTTP client with rate limiting and retry logic for API requests.

    This client provides async HTTP functionality with:
    - Rate limiting to comply with API requirements
    - Retry logic with exponential backoff for transient failures
    - Connection pooling and timeout configuration
    - Proper error handling and logging
    """

    def __init__(
        self,
        rate_limit_delay: float = 2.0,
        max_retries: int = 3,
        timeout: float = 30.0,
        headers: dict[str, str] | None = None,
    ) -> None:
        """Initialize the HTTP client.

        Args:
            rate_limit_delay: Minimum delay between requests in seconds
            max_retries: Maximum number of retry attempts
            timeout: Request timeout in seconds
            headers: Default headers to include in requests
        """
        self.rate_limiter = RateLimiter(rate_limit_delay)
        self.retry_config = RetryConfig(max_retries=max_retries)

        # Configure httpx client with connection pooling and timeouts
        default_headers = {
            "Accept-Encoding": "gzip, deflate",
            "Accept": "application/xml, text/xml, */*",
        }
        if headers:
            default_headers.update(headers)
            
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(
                connect=10.0,  # Connection timeout
                read=timeout,  # Read timeout
                write=10.0,  # Write timeout
                pool=5.0,  # Pool timeout
            ),
            limits=httpx.Limits(
                max_keepalive_connections=10,
                max_connections=20,
                keepalive_expiry=30.0,
            ),
            headers=default_headers,
            follow_redirects=True,
        )

        logger.info(f"HTTP client initialized with rate limit: {rate_limit_delay}s")

    async def __aenter__(self) -> "HTTPClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()

    async def close(self) -> None:
        """Close the HTTP client and clean up resources."""
        await self._client.aclose()
        logger.debug("HTTP client closed")

    async def get(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Make a GET request with rate limiting and retry logic.

        Args:
            url: The URL to request
            params: Query parameters to include in the request
            headers: Additional headers to include in the request

        Returns:
            The HTTP response object

        Raises:
            APIError: If the request fails after all retry attempts
            httpx.HTTPError: For non-retryable HTTP errors
        """
        return await self._make_request("GET", url, params=params, headers=headers)

    async def post(
        self,
        url: str,
        data: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Make a POST request with rate limiting and retry logic.

        Args:
            url: The URL to request
            data: Form data to include in the request
            json: JSON data to include in the request
            headers: Additional headers to include in the request

        Returns:
            The HTTP response object

        Raises:
            APIError: If the request fails after all retry attempts
            httpx.HTTPError: For non-retryable HTTP errors
        """
        return await self._make_request(
            "POST", url, data=data, json=json, headers=headers
        )

    @with_error_handling("http_request", service="http_client")
    async def _make_request(
        self,
        method: str,
        url: str,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Make an HTTP request with rate limiting and retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: The URL to request
            params: Query parameters
            data: Form data
            json: JSON data
            headers: Additional headers

        Returns:
            The HTTP response object

        Raises:
            APIError: If the request fails after all retry attempts
        """
        start_time = time.time()
        last_exception: Exception | None = None

        for attempt in range(self.retry_config.max_retries + 1):
            try:
                # Apply rate limiting before each request
                await self.rate_limiter.acquire()

                logger.debug(
                    f"Making {method} request to {url}",
                    attempt=attempt + 1,
                    max_attempts=self.retry_config.max_retries + 1,
                )

                response = await self._client.request(
                    method=method,
                    url=url,
                    params=params,
                    data=data,
                    json=json,
                    headers=headers,
                )

                # Log successful request
                duration = time.time() - start_time
                log_api_request(
                    method=method,
                    url=url,
                    status_code=response.status_code,
                    duration=duration,
                    attempt=attempt + 1,
                )

                # Check for HTTP errors that shouldn't be retried
                if response.status_code in (400, 401, 403, 404, 422):
                    # Client errors - don't retry
                    response.raise_for_status()

                # Check for server errors that should be retried
                if response.status_code >= 500:
                    response.raise_for_status()

                logger.debug(f"Request successful: {response.status_code}")
                return response

            except httpx.TimeoutException as e:
                last_exception = e
                logger.warning(
                    f"Request timeout on attempt {attempt + 1}",
                    attempt=attempt + 1,
                    timeout=getattr(e, "timeout", None),
                )

            except httpx.NetworkError as e:
                last_exception = e
                logger.warning(
                    f"Network error on attempt {attempt + 1}",
                    attempt=attempt + 1,
                    error=str(e),
                )

            except httpx.HTTPStatusError as e:
                status_code = e.response.status_code
                try:
                    response_body = (
                        e.response.text if hasattr(e.response, "text") else None
                    )
                    # Ensure response_body is a string for slicing
                    if response_body and not isinstance(response_body, str):
                        response_body = str(response_body)
                except Exception:
                    response_body = None

                if status_code < 500:
                    # Client error - don't retry
                    logger.error(
                        f"Client error {status_code}",
                        status_code=status_code,
                        response_body=response_body[:500] if response_body else None,
                    )

                    if status_code == 429:
                        retry_after = e.response.headers.get("Retry-After")
                        raise RateLimitError(
                            f"Rate limit exceeded: HTTP {status_code}",
                            status_code=status_code,
                            response_body=response_body,
                            retry_after=float(retry_after) if retry_after else None,
                        )
                    elif status_code in (401, 403):
                        raise APIError(
                            f"Authentication error: HTTP {status_code}",
                            code=f"HTTP_{status_code}",
                            details=response_body,
                        )
                    else:
                        raise APIError(
                            f"HTTP {status_code} error",
                            code=f"HTTP_{status_code}",
                            details=response_body,
                        )

                # Server error - retry
                last_exception = e
                logger.warning(
                    f"Server error on attempt {attempt + 1}",
                    attempt=attempt + 1,
                    status_code=status_code,
                )

            except Exception as e:
                # Unexpected error - don't retry
                logger.error(f"Unexpected error: {e}")
                raise APIError(
                    f"An unexpected error occurred: {e}",
                    code="UNEXPECTED_ERROR",
                )

            # If this wasn't the last attempt, wait before retrying
            if attempt < self.retry_config.max_retries:
                delay = self.retry_config.get_delay(attempt)
                logger.info(
                    f"Retrying in {delay:.2f} seconds",
                    delay=delay,
                    attempt=attempt + 1,
                    max_attempts=self.retry_config.max_retries + 1,
                )
                await asyncio.sleep(delay)

        # All retry attempts failed
        duration = time.time() - start_time
        logger.error(
            "Request failed after all retry attempts",
            attempts=self.retry_config.max_retries + 1,
            duration=duration,
            last_error=str(last_exception) if last_exception else "Unknown",
        )

        # For all retry exhaustion cases, raise APIError with MAX_RETRIES_EXCEEDED
        raise APIError(
            f"Request failed after {self.retry_config.max_retries + 1} attempts",
            code="MAX_RETRIES_EXCEEDED",
            details=str(last_exception) if last_exception else "Unknown error",
        )

    def is_closed(self) -> bool:
        """Check if the HTTP client is closed.

        Returns:
            True if the client is closed, False otherwise
        """
        return self._client.is_closed


def create_http_client(
    rate_limit_delay: float = 2.0,
    max_retries: int = 3,
    timeout: float = 30.0,
    headers: dict[str, str] | None = None,
) -> HTTPClient:
    """Create and return a configured HTTP client.

    Args:
        rate_limit_delay: Minimum delay between requests in seconds
        max_retries: Maximum number of retry attempts
        timeout: Request timeout in seconds
        headers: Default headers to include in requests

    Returns:
        Configured HTTPClient instance

    Example:
        >>> async with create_http_client(rate_limit_delay=1.0) as client:
        ...     response = await client.get("https://api.example.com/data")
    """
    return HTTPClient(
        rate_limit_delay=rate_limit_delay,
        max_retries=max_retries,
        timeout=timeout,
        headers=headers,
    )
