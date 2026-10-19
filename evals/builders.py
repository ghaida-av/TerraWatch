"""Small helpers that build normalized `Evidence` envelopes for eval scenarios.

Scenarios describe the *physical situation* (fire distance, wind, PM2.5 history); these builders turn
that into the same envelopes the real adapters produce, so the whole analysis pipeline is exercised.
"""
from __future__ import annotations

from typing import List, Optional

from data.schemas.models import ErrorInfo, Evidence, GeoPoint

TARGET = {"name": "Evalville", "lat": 30.0444, "lon": 31.2357}
NOW = "2026-09-29T12:00:00Z"


def _base(kind: str, source: str, status: str = "ok", **kw) -> Evidence:
    return Evidence(
        evidence_id=f"ev_{kind}_eval", source=source, kind=kind, status=status, data_mode="mock",
        timestamp=kw.pop("timestamp", NOW), fetched_at=NOW,
        location=GeoPoint(lat=TARGET["lat"], lon=TARGET["lon"]), **kw,
    )


def failed(kind: str, source: str, status: str = "error") -> Evidence:
    err = ErrorInfo(type="timeout", message="eval: simulated upstream failure", retryable=True) if status == "error" else None
    return _base(kind, source, status=status, error=err)


def weather(wind_speed_kmh: float, wind_from_deg: float) -> Evidence:
    return _base("weather", "open-meteo", measurements={"current": {
        "time": NOW, "temperature_c": 31.0, "wind_speed_kmh": wind_speed_kmh,
        "wind_direction_deg": wind_from_deg, "wind_gusts_kmh": wind_speed_kmh * 1.5,
    }})


def fire(distance_km: Optional[float], bearing_fire_to_target_deg: float = 0.0,
         detected_at: str = "2026-09-29T09:00:00Z", count: int = 1) -> Evidence:
    """`distance_km=None` means: satellite reachable, zero hotspots (absence of fire IS evidence)."""
    if distance_km is None:
        return _base("fire", "nasa_firms", measurements={"hotspot_count": 0, "radius_km": 150.0, "window_days": 1,
                                                          "product": "VIIRS", "closest_fires": []})
    hotspot = {"lat": 30.2, "lon": 31.4, "distance_km": distance_km,
               "bearing_fire_to_location_deg": bearing_fire_to_target_deg,
               "detected_at": detected_at, "frp_mw": 40.0, "confidence": "high"}
    return _base("fire", "nasa_firms", measurements={
        "hotspot_count": count, "radius_km": 150.0, "window_days": 1, "product": "VIIRS",
        "nearest_km": distance_km, "closest_fires": [hotspot]})


def air_quality(pm25: float, history: Optional[List[float]] = None, modeled: bool = False) -> Evidence:
    obs = [{"parameter": "pm25", "pm25": v} for v in (history or [])]
    obs.append({"parameter": "pm25", "pm25": pm25})
    return _base("air_quality", "open-meteo-air-quality" if modeled else "openaq",
                 measurements={"pm25": pm25}, observations=obs, is_modeled=modeled,
                 timestamp="2026-09-29T11:00:00Z")
