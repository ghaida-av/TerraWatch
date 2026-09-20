"""BaseAdapter — every source implements only `_fetch_live` and `_fetch_mock`.

The base class owns everything that must behave identically across sources:

    mode switch (live / demo / mock)  ->  cache  ->  live API  ->  stale-cache recovery
    -> error envelope (never raises to the agent)  ->  stable evidence_id  ->  evidence store
"""
from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from data import store
from data.config import Mode, get_mode, record_fixtures_enabled, simulated_failures
from data.core import fixtures
from data.core.cache import get_cache, make_key
from data.core.errors import AdapterError, ErrorType
from data.core.http import redact
from data.core.timeutil import utc_now
from data.schemas.models import ErrorInfo, Evidence, GeoPoint

log = logging.getLogger("terrawatch.data")


@dataclass
class Fetched:
    """What an adapter's `_fetch_*` returns. JSON-serializable so it can be cached / recorded."""

    measurements: Dict[str, Any]
    observations: List[Dict[str, Any]] = field(default_factory=list)
    units: Dict[str, str] = field(default_factory=dict)
    timestamp: Optional[str] = None
    raw_reference: Optional[str] = None
    status: str = "ok"                       # "ok" | "no_data"
    warnings: List[str] = field(default_factory=list)
    source: Optional[str] = None             # override when a fallback source answered
    is_modeled: bool = False
    location: Optional[Dict[str, float]] = None  # override (geocoding returns the resolved point)


def validate_coords(lat: Any, lon: Any) -> Tuple[float, float]:
    try:
        lat_f, lon_f = float(lat), float(lon)
    except (TypeError, ValueError):
        raise AdapterError(ErrorType.BAD_REQUEST, f"lat/lon must be numbers, got lat={lat!r}, lon={lon!r}")
    if not (-90 <= lat_f <= 90 and -180 <= lon_f <= 180):
        raise AdapterError(ErrorType.BAD_REQUEST, f"Coordinates out of range: lat={lat_f}, lon={lon_f}")
    return lat_f, lon_f


def _age_text(seconds: float) -> str:
    if seconds < 90:
        return f"{int(seconds)}s"
    if seconds < 5400:
        return f"{int(seconds // 60)}min"
    return f"{seconds / 3600:.1f}h"


class BaseAdapter:
    source: str = ""            # canonical source id used in fixtures / cache / simulated failures
    kind: str = ""
    defaults: Dict[str, Any] = {}
    ttl_seconds: int = 3600
    max_stale_seconds: int = 24 * 3600

    # ---------------------------------------------------------------- public API
    def fetch(self, lat: Any, lon: Any, **params: Any) -> Evidence:
        try:
            lat_f, lon_f = validate_coords(lat, lon)
        except AdapterError as e:
            return self._error_evidence(e, None, None, params, utc_now())
        return self._run(lat_f, lon_f, self._normalize(params))

    # ---------------------------------------------------------------- subclass hooks
    def _fetch_live(self, lat: Optional[float], lon: Optional[float], params: Dict[str, Any]) -> Fetched:
        raise NotImplementedError

    def _fetch_mock(self, lat: Optional[float], lon: Optional[float], params: Dict[str, Any]) -> Fetched:
        raise NotImplementedError

    # ---------------------------------------------------------------- internals
    def _normalize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Fill defaults, drop unknown keys (LLMs love to add extras like tz_name)."""
        merged = dict(self.defaults)
        merged.update({k: v for k, v in params.items() if k in self.defaults and v is not None})
        return merged

    def _run(self, lat: Optional[float], lon: Optional[float], params: Dict[str, Any],
             match_key: Optional[str] = None) -> Evidence:
        started = utc_now()
        warnings: List[str] = []
        try:
            fetched, data_mode = self._resolve(lat, lon, params, match_key, warnings)
        except AdapterError as e:
            return self._error_evidence(e, lat, lon, params, started)
        except Exception as e:  # a parser bug must never crash the investigation
            log.exception("Unexpected failure in %s adapter", self.source)
            err = AdapterError(ErrorType.BAD_RESPONSE,
                               f"Unexpected error processing {self.source} data: {type(e).__name__}: {redact(e)}")
            return self._error_evidence(err, lat, lon, params, started)

        warnings = warnings + list(fetched.warnings)
        src = fetched.source or self.source
        loc = fetched.location or ({"lat": lat, "lon": lon} if lat is not None else None)
        ev = Evidence(
            evidence_id=self._evidence_id(src, lat, lon, params, fetched.measurements),
            source=src,
            kind=self.kind,  # type: ignore[arg-type]
            status=fetched.status,  # type: ignore[arg-type]
            data_mode=data_mode,  # type: ignore[arg-type]
            timestamp=fetched.timestamp or started.strftime("%Y-%m-%dT%H:%M:%SZ"),
            fetched_at=started.strftime("%Y-%m-%dT%H:%M:%SZ"),
            location=GeoPoint(**loc) if loc else None,
            query=params,
            measurements=fetched.measurements,
            units=fetched.units,
            observations=fetched.observations,
            raw_reference=fetched.raw_reference,
            warnings=warnings,
            is_modeled=fetched.is_modeled,
        )
        store.put(ev)
        return ev

    def _resolve(self, lat, lon, params, match_key, warnings: List[str]) -> Tuple[Fetched, str]:
        failing = simulated_failures()
        if "all" in failing or self.source in failing or self.kind in failing:
            raise AdapterError(ErrorType.SIMULATED_OUTAGE,
                               f"Simulated outage of {self.source} (TERRAWATCH_SIMULATE_FAILURES)", retryable=True)

        mode = get_mode()
        if mode is Mode.MOCK:
            return self._fetch_mock(lat, lon, params), "mock"

        if mode is Mode.DEMO:
            rec = fixtures.lookup(self.source, lat, lon, match_key)
            if rec:
                warnings.append(f"Demo mode: replaying recorded response from {rec.get('recorded_at')}.")
                return Fetched(**rec["fetched"]), "demo"
            warnings.append(f"Demo mode: no recorded {self.source} fixture near this location — using synthetic data.")
            return self._fetch_mock(lat, lon, params), "mock"

        # ---- LIVE: fresh cache -> live API -> stale cache
        cache = get_cache()
        key = make_key(self.source, lat, lon, params)
        entry = cache.get(key)
        now = time.time()
        if entry and now - entry["stored_at"] <= self.ttl_seconds:
            return Fetched(**entry["payload"]), "cache"
        try:
            fetched = self._fetch_live(lat, lon, params)
        except AdapterError as e:
            if entry and now - entry["stored_at"] <= self.max_stale_seconds:
                warnings.append(
                    f"Live {self.source} request failed ({e.type.value}); serving cached data that is "
                    f"{_age_text(now - entry['stored_at'])} old."
                )
                return Fetched(**entry["payload"]), "stale_cache"
            raise
        payload = asdict(fetched)
        cache.set(key, payload, keep_seconds=self.max_stale_seconds)
        if record_fixtures_enabled():
            fixtures.save(self.source, lat, lon, params, payload, match_key)
        return fetched, "live"

    def _evidence_id(self, source, lat, lon, params, body) -> str:
        blob = json.dumps([source, None if lat is None else round(lat, 3), None if lon is None else round(lon, 3),
                           params, body], sort_keys=True, default=str)
        return f"ev_{source.replace('-', '_')}_{hashlib.sha1(blob.encode()).hexdigest()[:10]}"

    def _error_evidence(self, e: AdapterError, lat, lon, params, started) -> Evidence:
        ts = started.strftime("%Y-%m-%dT%H:%M:%SZ")
        ev = Evidence(
            evidence_id=self._evidence_id(self.source, lat, lon, params, {"error": e.type.value, "t": ts}),
            source=self.source,
            kind=self.kind,  # type: ignore[arg-type]
            status="error",
            data_mode="live" if get_mode() is Mode.LIVE else get_mode().value,  # type: ignore[arg-type]
            timestamp=ts,
            fetched_at=ts,
            location=GeoPoint(lat=lat, lon=lon) if lat is not None else None,
            query=params,
            error=ErrorInfo(type=e.type.value, message=redact(e.message), retryable=e.retryable,
                            http_status=e.http_status),
        )
        store.put(ev)
        return ev
