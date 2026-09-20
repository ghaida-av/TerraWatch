"""One internally-consistent synthetic incident, shared by all mock adapters.

Story (relative to `now`, all UTC):
  T-8h  satellite detects a cluster of fires 58-96 km NE of the requested location
  T-7h  wind shifts from WSW (250°) to NE (45°) and strengthens  -> smoke is carried toward the location
  T-6h  PM2.5 starts climbing from ~32 to ~80 µg/m³

So `fire_proximity`, `wind_alignment`, `air_quality_anomaly` and `temporal_correlation` all have
something meaningful to chew on before real data is wired in. Everything is deterministic given
(lat, lon, now).
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from data.core.geo import bearing_deg, destination_point, haversine_km

WIND_FROM_AFTER_SHIFT = 45.0    # wind coming FROM the NE -> blows toward the SW
WIND_FROM_BEFORE_SHIFT = 250.0
SHIFT_HOURS_AGO = 7
PM25_RAMP_HOURS_AGO = 6


def now_hour() -> datetime:
    return datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def weather_hours(now: datetime, back: int = 24) -> List[Dict[str, Any]]:
    rows = []
    for h in range(-back, 1):
        t = now + timedelta(hours=h)
        shifted = h >= -SHIFT_HOURS_AGO
        rows.append({
            "time": iso(t),
            "temperature_c": round(29 + 5 * math.sin((t.hour - 9) / 24 * 2 * math.pi), 1),
            "relative_humidity_pct": 38.0,
            "wind_speed_kmh": 24.0 if shifted else 11.0,
            "wind_direction_deg": WIND_FROM_AFTER_SHIFT if shifted else WIND_FROM_BEFORE_SHIFT,
            "wind_gusts_kmh": 38.0 if shifted else 18.0,
            "precipitation_mm": 0.0,
        })
    return rows


def pm25_hours(now: datetime, back: int = 24) -> List[float]:
    vals = []
    for h in range(-back, 1):
        since_ramp = h + PM25_RAMP_HOURS_AGO
        vals.append(32.0 if since_ramp <= 0 else 32.0 + 8.0 * since_ramp)
    return vals


def fires(lat: float, lon: float, now: datetime) -> List[Dict[str, Any]]:
    out = []
    spec = [(58, -3, 8), (64, 2, 8), (71, -1, 7), (83, 4, 6), (96, 0, 6)]  # dist_km, bearing offset, hours ago
    for i, (dist, off, hours_ago) in enumerate(spec):
        b = (WIND_FROM_AFTER_SHIFT + off) % 360  # fires lie in the direction the wind comes FROM
        f_lat, f_lon = destination_point(lat, lon, b, dist)
        out.append({
            "lat": round(f_lat, 4), "lon": round(f_lon, 4),
            "distance_km": round(haversine_km(f_lat, f_lon, lat, lon), 2),
            "bearing_fire_to_location_deg": round(bearing_deg(f_lat, f_lon, lat, lon), 2),
            "detected_at": iso(now - timedelta(hours=hours_ago, minutes=12 * i)),
            "frp_mw": round(18.0 + 9.5 * (5 - i), 1),
            "brightness_k": round(342.0 + 4 * (5 - i), 1),
            "confidence": "high" if i < 3 else "nominal",
            "daynight": "D",
            "satellite": "N20",
        })
    return out


def quakes(lat: float, lon: float, now: datetime) -> List[Dict[str, Any]]:
    out = []
    for i, (dist, brg, mag, depth, days_ago) in enumerate([(140, 200, 3.1, 10.0, 2), (260, 120, 4.4, 25.0, 9)]):
        q_lat, q_lon = destination_point(lat, lon, brg, dist)
        out.append({
            "id": f"mock{i:04d}", "magnitude": mag, "place": f"{dist} km {'SSW' if brg == 200 else 'ESE'} of mock-city",
            "time": iso(now - timedelta(days=days_ago)), "lat": round(q_lat, 4), "lon": round(q_lon, 4),
            "depth_km": depth, "distance_km": round(haversine_km(q_lat, q_lon, lat, lon), 2),
            "url": None, "alert": None, "tsunami": 0,
        })
    return out


def places(lat: float, lon: float) -> List[Dict[str, Any]]:
    spec = [("Mock General Hospital", ["healthcare", "healthcare.hospital"], 3.0, 40),
            ("Mock Fire Station 4", ["service", "service.fire_station"], 4.2, 130),
            ("Mock Industrial Park", ["building", "building.industrial"], 6.5, 300),
            ("Mock International Airport", ["airport"], 18.0, 80)]
    out = []
    for name, cats, dist, brg in spec:
        p_lat, p_lon = destination_point(lat, lon, brg, dist)
        out.append({"name": name, "categories": cats, "lat": round(p_lat, 5), "lon": round(p_lon, 5),
                    "distance_km": round(haversine_km(p_lat, p_lon, lat, lon), 3)})
    return out
