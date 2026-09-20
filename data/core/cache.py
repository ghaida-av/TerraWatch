"""TTL cache with *stale* reads.

We keep entries much longer than their TTL so that when a live API fails (outage, rate limit)
the adapter can still serve the last good answer — clearly flagged as `stale_cache`.
Uses diskcache when installed, otherwise an in-process dict.
"""
from __future__ import annotations

import hashlib
import json
import threading
import time
from typing import Any, Dict, Optional

from data.config import cache_dir


def make_key(source: str, lat: Optional[float], lon: Optional[float], params: Dict[str, Any]) -> str:
    loc = "none" if lat is None or lon is None else f"{lat:.3f}:{lon:.3f}"  # ~110 m buckets
    digest = hashlib.sha1(json.dumps(params, sort_keys=True, default=str).encode()).hexdigest()[:10]
    return f"{source}:{loc}:{digest}"


class ResponseCache:
    def __init__(self) -> None:
        self._mem: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._disk = None
        try:
            import diskcache  # type: ignore

            self._disk = diskcache.Cache(str(cache_dir()))
        except Exception:
            self._disk = None

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Returns {"stored_at": epoch_seconds, "payload": {...}} or None."""
        if self._disk is not None:
            try:
                return self._disk.get(key)
            except Exception:
                pass
        with self._lock:
            entry = self._mem.get(key)
            if entry and entry["expires_at"] < time.time():
                self._mem.pop(key, None)
                return None
            return entry

    def set(self, key: str, payload: Dict[str, Any], keep_seconds: int) -> None:
        entry = {"stored_at": time.time(), "payload": payload}
        if self._disk is not None:
            try:
                self._disk.set(key, entry, expire=keep_seconds)
                return
            except Exception:
                pass
        with self._lock:
            self._mem[key] = {**entry, "expires_at": time.time() + keep_seconds}

    def clear(self) -> None:
        with self._lock:
            self._mem.clear()
        if self._disk is not None:
            try:
                self._disk.clear()
            except Exception:
                pass


_cache: Optional[ResponseCache] = None
_cache_lock = threading.Lock()


def get_cache() -> ResponseCache:
    global _cache
    with _cache_lock:
        if _cache is None:
            _cache = ResponseCache()
        return _cache


def reset_cache() -> None:
    global _cache
    with _cache_lock:
        _cache = None
