"""
Rate Limiter Bridge
====================
Wraps quantpylib's RateSemaphore for use across the SDK.
Prevents Hyperliquid API rate limit violations.
"""

import logging
import asyncio
from typing import Callable, Any, Optional

logger = logging.getLogger(__name__)

try:
    from quantpylib.throttler.rate_semaphore import RateSemaphore, AsyncRateSemaphore
    HAS_THROTTLER = True
except ImportError:
    HAS_THROTTLER = False
    logger.info("quantpylib throttler not available - using basic rate limiting")


class RateLimiter:
    """
    Rate limiter for Hyperliquid API calls.

    Uses quantpylib's credit-based RateSemaphore when available,
    falls back to simple asyncio.Semaphore otherwise.

    Usage:
        limiter = RateLimiter(max_requests_per_second=10)

        # Async context
        async with limiter:
            result = await some_api_call()

        # Or explicit acquire/release
        await limiter.acquire()
        try:
            result = await some_api_call()
        finally:
            limiter.release()
    """

    # Default limits for Hyperliquid API
    DEFAULT_CREDITS = 1200       # requests per minute
    DEFAULT_REFUND_TIME = 60     # seconds

    def __init__(
        self,
        max_requests_per_minute: int = DEFAULT_CREDITS,
        refund_time: float = DEFAULT_REFUND_TIME,
    ):
        self.max_requests = max_requests_per_minute
        self.refund_time = refund_time

        if HAS_THROTTLER:
            self._semaphore = AsyncRateSemaphore(credits=max_requests_per_minute)
            self._mode = "quantpylib"
        else:
            # Fallback: simple concurrency limiter
            self._semaphore = asyncio.Semaphore(max_requests_per_minute // 6)
            self._mode = "fallback"

        logger.debug(f"RateLimiter initialized (mode={self._mode}, limit={max_requests_per_minute}/min)")

    async def acquire(self, credits: int = 1):
        """Acquire rate limit credits before making an API call."""
        if self._mode == "quantpylib":
            await self._semaphore.acquire(credits=credits, refund_time=self.refund_time)
        else:
            await self._semaphore.acquire()

    def release(self):
        """Release rate limit credits (only for fallback mode)."""
        if self._mode == "fallback":
            self._semaphore.release()

    async def __aenter__(self):
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.release()
        return False

    async def execute(self, func: Callable, *args, credits: int = 1, **kwargs) -> Any:
        """Execute a function with rate limiting."""
        async with self:
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            return func(*args, **kwargs)
