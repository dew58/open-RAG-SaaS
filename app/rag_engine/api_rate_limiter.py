"""
API-level rate limiters for Google AI Free Tier.

Architecture Decision:
- Thread-safe (threading.Lock) because ChromaDB/LangChain calls run in ThreadPoolExecutor
- Two separate limiters: embeddings (100 RPM) and LLM generation (30 RPM)
- Minimum inter-request delay enforced BEFORE each API call
- tenacity exponential backoff handles transient 429 errors that slip through
- All sleeps are logged with structlog for operational visibility

Rate Limits (Google AI Free Tier):
- Embedding (gemini-embedding-001): 100 RPM → 0.6s min between requests
- LLM (gemma-3-12b):                30 RPM → 2.5s min between requests (with margin)
"""

import threading
import time

import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)


class APIRateLimiter:
    """
    Thread-safe rate limiter that enforces a minimum delay between API calls.

    Uses a simple timestamp-based approach:
    - Record the time of each API call
    - Before the next call, sleep if not enough time has elapsed
    - Thread-safe via threading.Lock (not asyncio.Lock — runs in executor threads)
    """

    def __init__(self, name: str, requests_per_minute: int):
        self.name = name
        self.rpm = requests_per_minute
        self.min_interval = 60.0 / requests_per_minute  # seconds between requests
        self._last_request_time: float = 0.0
        self._lock = threading.Lock()
        self._request_count: int = 0

        logger.info(
            "Rate limiter initialized",
            limiter=self.name,
            rpm=self.rpm,
            min_interval_seconds=round(self.min_interval, 2),
        )

    def wait(self) -> None:
        """
        Block until it is safe to make the next API request.
        Must be called BEFORE each API call.
        Logs sleep duration when throttling occurs.
        """
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_request_time
            wait_time = self.min_interval - elapsed

            if wait_time > 0:
                logger.info(
                    "Rate limit throttle: sleeping",
                    limiter=self.name,
                    sleep_seconds=round(wait_time, 2),
                    request_number=self._request_count + 1,
                )
                time.sleep(wait_time)

            self._last_request_time = time.monotonic()
            self._request_count += 1

    def log_request_complete(
        self,
        *,
        input_tokens: int = 0,
        output_tokens: int = 0,
        extra: dict | None = None,
    ) -> None:
        """Log completion of an API request with optional token usage."""
        log_data = {
            "limiter": self.name,
            "request_number": self._request_count,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        }
        if extra:
            log_data.update(extra)

        logger.info("API request completed", **log_data)

    @property
    def total_requests(self) -> int:
        """Total number of requests made through this limiter."""
        return self._request_count

    def reset_counter(self) -> None:
        """Reset the request counter (useful per-document)."""
        self._request_count = 0


# ── Module-level singleton instances ──────────────────────────────────────────

embedding_rate_limiter = APIRateLimiter(
    name="embedding",
    requests_per_minute=settings.EMBEDDING_RPM,
)

llm_rate_limiter = APIRateLimiter(
    name="llm",
    requests_per_minute=settings.LLM_RPM,
)
