"""Base spider interface and shared data types."""
from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Iterator, Optional

import httpx


@dataclass
class FIRDocument:
    state: str
    state_code: str
    district: str
    fir_number: str
    year: int
    content: bytes
    file_ext: str          # "pdf" | "jpg" | "png"
    source_url: str
    police_station: str = ""
    extra: dict = field(default_factory=dict)

    @property
    def fingerprint_key(self) -> str:
        """Unique identity string for deduplication."""
        return f"{self.state_code}:{self.district}:{self.fir_number}:{self.year}"


class BaseSpider(ABC):
    # Subclasses must declare these
    state: str
    state_code: str          # two-letter code, e.g. "UP"
    districts: list[str]
    base_url: str

    requires_captcha: bool = False
    requires_playwright: bool = False
    rate_limit_rps: float = 1.0       # requests per second (per domain)

    # Common browser-like headers for government portals
    DEFAULT_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-IN,en;q=0.9,hi;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    def __init__(self, proxy_url: Optional[str] = None):
        self.proxy_url = proxy_url
        self.logger = logging.getLogger(f"crawler.{self.state_code}")
        self._client: Optional[httpx.Client] = None
        self._last_request_at: float = 0.0

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    @abstractmethod
    def crawl_district(self, district: str) -> Iterator[FIRDocument]:
        """Yield FIRDocument for every new FIR found in this district."""

    def crawl_all(self) -> Iterator[FIRDocument]:
        for district in self.districts:
            self.logger.info("Crawling %s / %s", self.state, district)
            yield from self.crawl_district(district)

    def close(self) -> None:
        if self._client:
            self._client.close()
            self._client = None

    # ------------------------------------------------------------------
    # HTTP helpers
    # ------------------------------------------------------------------

    @property
    def client(self) -> httpx.Client:
        if self._client is None:
            proxy_map = {"all://": self.proxy_url} if self.proxy_url else None
            self._client = httpx.Client(
                proxy=proxy_map,
                follow_redirects=True,
                timeout=httpx.Timeout(30.0, connect=10.0),
                headers=self.DEFAULT_HEADERS,
            )
        return self._client

    def get(self, url: str, **kwargs) -> httpx.Response:
        self._throttle()
        resp = self.client.get(url, **kwargs)
        resp.raise_for_status()
        return resp

    def post(self, url: str, **kwargs) -> httpx.Response:
        self._throttle()
        resp = self.client.post(url, **kwargs)
        resp.raise_for_status()
        return resp

    def _throttle(self) -> None:
        gap = 1.0 / self.rate_limit_rps
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < gap:
            time.sleep(gap - elapsed)
        self._last_request_at = time.monotonic()
