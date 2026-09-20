
from __future__ import annotations

import os
from enum import Enum
from pathlib import Path
from typing import Dict, Optional, Set


class Mode(str, Enum):
    LIVE = "live"   # real APIs, with cache + stale-cache recovery
    DEMO = "demo"   # recorded fixtures only
    MOCK = "mock"   # deterministic synthetic data (dev / tests)


_TRUTHY = {"1", "true", "yes", "on"}


def get_mode() -> Mode:
    raw = os.getenv("TERRAWATCH_MODE", "").strip().lower()
    if raw:
        try:
            return Mode(raw)
        except ValueError:
            raise ValueError(f"TERRAWATCH_MODE must be one of live/demo/mock, got {raw!r}")
    
    if os.getenv("DEMO_MODE", "").strip().lower() in _TRUTHY:
        return Mode.DEMO
    return Mode.LIVE


SECRET_NAMES = ("GEOAPIFY_API_KEY", "OPENAQ_API_KEY", "FIRMS_MAP_KEY")
_secret_cache: Dict[str, str] = {}


def get_secret(name: str) -> Optional[str]:
    
    val = os.getenv(name)
    if val:
        return val
    if name in _secret_cache:
        return _secret_cache[name]
    try:  # pragma: no cover - only inside Colab
        from google.colab import userdata  # type: ignore

        val = userdata.get(name)
        if val:
            _secret_cache[name] = val
            return val
    except Exception:
        pass
    return None


def known_secret_values() -> Set[str]:
    """Used by the HTTP layer to scrub keys out of error messages ."""
    vals = {os.getenv(n) or _secret_cache.get(n) for n in SECRET_NAMES}
    return {v for v in vals if v}


def fixtures_dir() -> Path:
    return Path(os.getenv("TERRAWATCH_FIXTURES_DIR") or Path(__file__).parent / "fixtures")


def cache_dir() -> Path:
    return Path(os.getenv("TERRAWATCH_CACHE_DIR") or ".terrawatch_cache")


def record_fixtures_enabled() -> bool:
    return os.getenv("TERRAWATCH_RECORD_FIXTURES", "").strip().lower() in _TRUTHY


def simulated_failures() -> Set[str]:
    """TERRAWATCH_SIMULATE_FAILURES for the API-failure ."""
    raw = os.getenv("TERRAWATCH_SIMULATE_FAILURES", "")
    return {p.strip().lower() for p in raw.split(",") if p.strip()}
