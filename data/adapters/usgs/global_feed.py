"""Global earthquake feed (USGS summary GeoJSON) for the Earth Monitor screen.

In other words: the EarthquakeAdapter answers "what happened NEAR this city?";
this module answers "what is happening ON THE WHOLE PLANET right now?".
"""
from __future__ import annotations

import time
from datetime import timedelta
from typing import Any, Dict, List

from data.config import Mode, get_mode
from data.core import http
from data.core.timeutil import to_utc_iso, utc_now

FEED_URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/{mag}_{window}.geojson"
WINDOWS = {"hour": "hour", "day": "day", "week": "week"}
MAG_FEEDS = {0.0: "all", 1.0: "1.0", 2.5: "2.5", 4.5: "4.5"}  # USGS only publishes these thresholds
CACHE_TTL = 120  # seconds
_cache: Dict[str, Any] = {}


def level_for(mag: float | None) -> str:
    """Severity label used by the UI badges (display only, not part of the risk score)."""
    m = mag or 0.0
    return "CRITICAL" if m >= 6 else "HIGH" if m >= 5 else "MODERATE" if m >= 4 else "LOW"


def _mock_events() -> List[Dict[str, Any]]:
    now = utc_now().replace(minute=0, second=0, microsecond=0)
    seeds = [  # (place, lat, lon, mag, depth_km)
        ("6 km NW of Diego Garcia", -7.27, 72.36, 4.8, 10.0), ("12 km E of Port Louis, Mauritius", -20.16, 57.60, 3.1, 33.0),
        ("18 km S of Seychelles", -4.80, 55.45, 2.7, 12.0), ("Off the coast of Mozambique", -18.9, 36.5, 5.4, 18.0),
        ("Southern Mid-Atlantic Ridge", -33.6, -14.1, 4.3, 10.0), ("Near St. Helena", -15.9, -5.7, 3.9, 10.0),
        ("Cairo, Egypt region", 29.9, 31.3, 3.2, 15.0), ("Gulf of Suez", 28.2, 33.1, 4.1, 14.0),
        ("Izmit, Turkey", 40.8, 29.9, 4.6, 9.0), ("Peloponnese, Greece", 37.4, 22.4, 3.8, 20.0),
        ("Tonga region", -20.5, -175.2, 6.2, 55.0), ("Bismarck Sea, PNG", -5.9, 150.4, 5.1, 40.0),
        ("Central Chile", -33.0, -71.5, 4.9, 35.0), ("Alaska Peninsula", 55.1, -160.2, 4.4, 28.0),
        ("Honshu, Japan", 37.6, 141.5, 5.6, 45.0), ("Sumatra, Indonesia", 2.1, 96.8, 4.2, 22.0),
    ]
    return [{
        "id": f"mock{i:03d}", "magnitude": mag, "place": place, "time": to_utc_iso(now - timedelta(minutes=7 * i + 4)),
        "lat": lat, "lon": lon, "depth_km": depth, "level": level_for(mag), "url": None,
    } for i, (place, lat, lon, mag, depth) in enumerate(seeds)]


def _live_events(window: str, min_mag: float) -> List[Dict[str, Any]]:
    feed = MAG_FEEDS[min(MAG_FEEDS, key=lambda k: abs(k - min_mag))]
    data = http.get_json(FEED_URL.format(mag=feed, window=WINDOWS[window]))
    out: List[Dict[str, Any]] = []
    for f in data.get("features") or []:
        try:
            p, (lon, lat, *rest) = f["properties"], f["geometry"]["coordinates"]
            out.append({"id": str(f.get("id")), "magnitude": p.get("mag"), "place": p.get("place"),
                        "time": to_utc_iso(p.get("time")), "lat": lat, "lon": lon,
                        "depth_km": rest[0] if rest else None, "level": level_for(p.get("mag")), "url": p.get("url")})
        except (KeyError, TypeError, ValueError):
            continue
    return out


def get_global_events(window: str = "day", min_mag: float = 2.5, limit: int = 100) -> Dict[str, Any]:
    """Return recent global events + a small summary.

    Live source errors are allowed to propagate so the API cannot label synthetic
    fallback events as a successful live feed.
    """
    window = window if window in WINDOWS else "day"
    mode = get_mode()
    key = f"{mode.value}:{window}:{min_mag}"
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < CACHE_TTL:
        events, source_status = hit[1], hit[2]
    else:
        source_status = "ok"
        if mode == Mode.LIVE:
            events = _live_events(window, min_mag)
        else:
            events = _mock_events()
        events = [e for e in events if (e["magnitude"] or 0) >= min_mag]
        events.sort(key=lambda e: e["time"] or "", reverse=True)
        _cache[key] = (time.time(), events, source_status)

    events = events[:limit]
    mags = [e["magnitude"] for e in events if e["magnitude"] is not None]
    levels = {k: sum(1 for e in events if e["level"] == k) for k in ("LOW", "MODERATE", "HIGH", "CRITICAL")}
    return {
        "mode": mode.value, "window": window, "min_magnitude": min_mag, "source_status": source_status,
        "generated_at": to_utc_iso(utc_now()), "total": len(events),
        "summary": {"max_magnitude": max(mags) if mags else None, "levels": levels},
        "events": events,
    }
