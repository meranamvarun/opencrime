"""Rotating proxy pool for crawler requests.

Proxies are loaded from the CRAWLER_PROXY_URLS env var (comma-separated).
Budget: $100/month residential (BrightData/Oxylabs ~$8-10/GB).
Round-robin rotation with automatic removal of consistently failing proxies.

Format: http://user:pass@host:port  or  socks5://user:pass@host:port
"""
from __future__ import annotations

import itertools
import logging
import threading
from typing import Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_HEALTH_CHECK_URL = "https://httpbin.org/ip"
_MAX_CONSECUTIVE_FAILURES = 5


class ProxyPool:
    """Thread-safe round-robin proxy pool with failure tracking."""

    def __init__(self) -> None:
        raw = getattr(settings, "CRAWLER_PROXY_URLS", "")
        proxies = [p.strip() for p in raw.split(",") if p.strip()] if raw else []
        self._proxies = proxies
        self._failures: dict[str, int] = {p: 0 for p in proxies}
        self._lock = threading.Lock()
        self._cycle = itertools.cycle(proxies) if proxies else None
        if not proxies:
            logger.warning("No proxies configured — crawling without proxy (high ban risk)")

    def get_proxy(self) -> Optional[str]:
        """Return the next healthy proxy URL, or None if pool is empty."""
        if not self._cycle:
            return None
        with self._lock:
            for _ in range(len(self._proxies)):
                proxy = next(self._cycle)
                if self._failures.get(proxy, 0) < _MAX_CONSECUTIVE_FAILURES:
                    return proxy
        logger.error("All proxies exhausted — falling back to direct connection")
        return None

    def report_failure(self, proxy: str) -> None:
        with self._lock:
            self._failures[proxy] = self._failures.get(proxy, 0) + 1
            if self._failures[proxy] >= _MAX_CONSECUTIVE_FAILURES:
                logger.warning("Proxy %s marked unhealthy after %d failures", proxy, _MAX_CONSECUTIVE_FAILURES)

    def report_success(self, proxy: str) -> None:
        with self._lock:
            self._failures[proxy] = 0

    def health_check(self) -> dict[str, bool]:
        """Synchronously check all proxies. Returns {proxy_url: is_healthy}."""
        results = {}
        for proxy in self._proxies:
            try:
                r = httpx.get(
                    _HEALTH_CHECK_URL,
                    proxy=proxy,
                    timeout=10.0,
                )
                results[proxy] = r.status_code == 200
            except Exception:
                results[proxy] = False
        return results

    @property
    def size(self) -> int:
        return len(self._proxies)


# Module-level singleton — shared across all spider instances in one worker process
_pool: Optional[ProxyPool] = None
_pool_lock = threading.Lock()


def get_pool() -> ProxyPool:
    global _pool
    if _pool is None:
        with _pool_lock:
            if _pool is None:
                _pool = ProxyPool()
    return _pool
