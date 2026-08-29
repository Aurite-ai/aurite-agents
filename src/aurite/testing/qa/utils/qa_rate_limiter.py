"""
Rate limiting and retry logic for QA testing.

This module provides rate limiting and retry functionality with exponential backoff
to handle LLM API rate limits during parallel test execution.
"""

import asyncio
import logging
import random
from typing import Awaitable, Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RateLimiter:
    """
    Manages rate limiting and retry logic for QA test execution.

    This class handles:
    - Semaphore-based concurrency control
    - Exponential backoff with jitter for rate limit errors
    - Configurable retry attempts
    """

    def __init__(
        self,
        max_concurrent: int = 3,
        retry_count: int = 3,
        base_delay: float = 1.0,
    ):
        """
        Initialize the rate limiter.

        Args:
            max_concurrent: Maximum number of concurrent operations
            retry_count: Number of retry attempts for rate limit errors
            base_delay: Base delay in seconds for exponential backoff
        """
        self.max_concurrent = max_concurrent
        self.retry_count = retry_count
        self.base_delay = base_delay
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.logger = logging.getLogger(__name__)

        self.logger.info(f"Initialized rate limiter with max {max_concurrent} concurrent operations")

    async def execute_with_retry(
        self,
        operation: Callable[[], Awaitable[T]],
        operation_id: str,
    ) -> T:
        """
        Execute an async operation with rate limiting and retry logic.

        Args:
            operation: Async callable to execute
            operation_id: Identifier for logging purposes

        Returns:
            Result from the operation

        Raises:
            Exception: Re-raises the last exception if all retries fail
        """
        async with self.semaphore:
            last_exception = None

            for retry_attempt in range(self.retry_count):
                try:
                    result = await operation()
                    return result

                except Exception as e:
                    last_exception = e
                    error_msg = str(e).lower()

                    # Check if this is a rate limit error
                    if self._is_rate_limit_error(error_msg):
                        if retry_attempt < self.retry_count - 1:
                            # Calculate exponential backoff with jitter
                            delay = self._calculate_backoff_delay(retry_attempt)

                            self.logger.warning(
                                f"Rate limit hit for {operation_id}, "
                                f"retrying in {delay:.2f} seconds "
                                f"(attempt {retry_attempt + 1}/{self.retry_count})"
                            )
                            await asyncio.sleep(delay)
                            continue
                        else:
                            self.logger.error(f"Max retries exceeded for {operation_id} due to rate limiting")

                    # Re-raise the exception if not a rate limit error or max retries exceeded
                    raise

            # If we get here, all retries failed - raise the last exception
            if last_exception:
                raise last_exception
            else:
                raise RuntimeError(f"Failed to execute {operation_id} after {self.retry_count} attempts")

    def _is_rate_limit_error(self, error_msg: str) -> bool:
        """
        Check if an error message indicates a rate limit error.

        Args:
            error_msg: Lowercase error message

        Returns:
            True if this is a rate limit error
        """
        rate_indicators = ["rate limit", "too many requests", "429", "rate_limit"]
        return any(indicator in error_msg for indicator in rate_indicators)

    def _calculate_backoff_delay(self, retry_attempt: int) -> float:
        """
        Calculate exponential backoff delay with jitter.

        Args:
            retry_attempt: Current retry attempt number (0-indexed)

        Returns:
            Total delay in seconds
        """
        # Calculate exponential backoff
        delay = self.base_delay * (2**retry_attempt)

        # Add up to 30% jitter to prevent thundering herd
        jitter = random.uniform(0, delay * 0.3)

        return delay + jitter
