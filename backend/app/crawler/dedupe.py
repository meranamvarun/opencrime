"""Redis-backed FIR deduplication.

Fingerprint = SHA-256 of (state_code:district:fir_number:year).
Keys expire after 35 days so updated/re-issued FIRs are re-crawled
on the next weekly run (after ~5 weekly cycles).
"""
from __future__ import annotations

import hashlib
import logging

import redis as redis_lib

from app.core.config import settings

logger = logging.getLogger(__name__)

_TTL_SECONDS = 35 * 24 * 3600   # 35 days
_KEY_PREFIX = "fir_crawled:"


class FIRDeduplicator:
    def __init__(self) -> None:
        self._redis = redis_lib.from_url(settings.REDIS_URL, decode_responses=True)

    def fingerprint(self, key: str) -> str:
        """Return a hex SHA-256 of *key* (e.g. 'UP:Lucknow:0042:2024')."""
        return hashlib.sha256(key.encode()).hexdigest()

    def seen(self, fingerprint: str) -> bool:
        return bool(self._redis.exists(f"{_KEY_PREFIX}{fingerprint}"))

    def mark_seen(self, fingerprint: str) -> None:
        self._redis.setex(f"{_KEY_PREFIX}{fingerprint}", _TTL_SECONDS, "1")

    def bulk_seen(self, fingerprints: list[str]) -> list[bool]:
        pipe = self._redis.pipeline()
        for fp in fingerprints:
            pipe.exists(f"{_KEY_PREFIX}{fp}")
        return [bool(r) for r in pipe.execute()]

    def stats(self) -> dict:
        count = len(self._redis.keys(f"{_KEY_PREFIX}*"))
        return {"dedupe_keys": count}
