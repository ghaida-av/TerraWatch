"""Recorded known-good responses for DEMO mode.

Layout:  data/fixtures/<source>/<lat>_<lon>.json   (or <slug>.json for geocoding)
Recorded with:  python -m scripts.record_fixtures   (needs real API keys, run once before the demo)
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, Optional

from data.config import fixtures_dir
from data.core.geo import haversine_km
from data.core.timeutil import utc_now


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "x"


def _path(source: str, lat: Optional[float], lon: Optional[float], match_key: Optional[str]):
    name = _slug(match_key) if match_key else f"{lat:.2f}_{lon:.2f}"
    return fixtures_dir() / source / f"{name}.json"


def save(source: str, lat: Optional[float], lon: Optional[float], params: Dict[str, Any],
         fetched: Dict[str, Any], match_key: Optional[str] = None) -> None:
    p = _path(source, lat, lon, match_key)
    p.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "source": source,
        "recorded_at": utc_now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "location": None if lat is None else {"lat": lat, "lon": lon},
        "match_key": match_key,
        "query": params,
        "fetched": fetched,
    }
    p.write_text(json.dumps(record, indent=2, default=str))


def lookup(source: str, lat: Optional[float], lon: Optional[float], match_key: Optional[str] = None,
           max_km: float = 30.0) -> Optional[Dict[str, Any]]:
    """Exact match on `match_key` (geocoding) or nearest recorded location within `max_km`."""
    d = fixtures_dir() / source
    if not d.exists():
        return None
    if match_key:
        p = _path(source, None, None, match_key)
        return json.loads(p.read_text()) if p.exists() else None
    best, best_km = None, max_km
    for f in d.glob("*.json"):
        try:
            rec = json.loads(f.read_text())
            loc = rec.get("location")
            if not loc:
                continue
            km = haversine_km(lat, lon, loc["lat"], loc["lon"])
            if km <= best_km:
                best, best_km = rec, km
        except Exception:
            continue
    return best
