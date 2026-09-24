"""Spatial + wind analysis for TerraWatch.

This module is the canonical Person 3A implementation. It keeps the core
geodesy and wind logic in one place so the project can test and use it without
depending on a separate standalone spatial module.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Iterable, Mapping, Optional, Sequence, TypedDict

EARTH_RADIUS_KM = 6371.0


class SpatialEvidence(TypedDict, total=False):
    event_id: str
    target_id: str
    distance_km: float
    proximity_score: float
    wind_alignment: float
    downwind: bool
    bearing_deg: float
    wind_direction_deg: float


class WindAnalysis(TypedDict, total=False):
    wind_direction_deg: float
    wind_speed_ms: float
    bearing_to_target_deg: float
    alignment_score: float
    is_downwind: bool


@dataclass
class Location:
    id: str
    name: str
    lat: float
    lon: float
    population: Optional[int] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "lat": self.lat,
            "lon": self.lon,
            "population": self.population,
        }


@dataclass
class Event:
    id: str
    event_type: str
    lat: float
    lon: float
    timestamp: datetime
    magnitude: Optional[float] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "event_type": self.event_type,
            "lat": self.lat,
            "lon": self.lon,
            "timestamp": self.timestamp.isoformat(),
            "magnitude": self.magnitude,
            "metadata": self.metadata,
        }


def haversine_distance(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    """Return the great-circle distance in kilometers between two lat/lon pairs."""
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(lat1_rad)
        * math.cos(lat2_rad)
        * math.sin(dlon / 2.0) ** 2
    )
    c = 2.0 * math.asin(min(1.0, math.sqrt(a)))
    return round(EARTH_RADIUS_KM * c, 4)


def calculate_bearing(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    """Return the initial compass bearing in degrees from point 1 to point 2."""
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    dlon_rad = math.radians(lon2 - lon1)

    x = math.sin(dlon_rad) * math.cos(lat2_rad)
    y = (
        math.cos(lat1_rad) * math.sin(lat2_rad)
        - math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(dlon_rad)
    )
    bearing = math.degrees(math.atan2(x, y))
    return round((bearing + 360.0) % 360.0, 4)


def _angular_difference_deg(a_deg: float, b_deg: float) -> float:
    diff = abs((a_deg - b_deg + 180.0) % 360.0 - 180.0)
    return float(diff)


def wind_alignment(
    target_bearing_deg: float,
    wind_direction_deg: float | None = None,
    *,
    tolerance_deg: float = 45.0,
) -> float:
    """Return a normalized alignment score between 0 and 1."""
    try:
        score_value = float(target_bearing_deg)
        if 0.0 <= score_value <= 1.0 and (wind_direction_deg is None or 0.0 <= float(wind_direction_deg) <= 1.0):
            return round(max(0.0, min(1.0, score_value)), 4)
    except (TypeError, ValueError):
        pass

    if wind_direction_deg is None:
        return round(max(0.0, min(1.0, float(target_bearing_deg))), 4)

    diff = _angular_difference_deg(float(target_bearing_deg), float(wind_direction_deg))
    score = 1.0 - (diff / 180.0)
    return round(max(0.0, min(1.0, score)), 4)


def is_downwind(
    bearing_to_target_deg: float,
    wind_direction_deg: float,
    *,
    tolerance_deg: float = 5.0,
) -> bool:
    """Return True when the wind is aligned with the target within a tolerance."""
    diff = _angular_difference_deg(float(bearing_to_target_deg), float(wind_direction_deg))
    return diff <= abs(float(tolerance_deg))


class WindAnalyzer:
    @staticmethod
    def calculate_wind_alignment(
        bearing_to_target_deg: float,
        wind_direction_deg: float,
        tolerance_deg: float = 45.0,
    ) -> tuple[float, bool]:
        wind_towards = (float(wind_direction_deg) + 180.0) % 360.0
        diff = abs(wind_towards - float(bearing_to_target_deg))
        if diff > 180.0:
            diff = 360.0 - diff

        alignment_score = max(0.0, 1.0 - (diff / 180.0))
        is_aligned = diff <= tolerance_deg
        return alignment_score, is_aligned

    @staticmethod
    def analyze_wind(
        event: Event,
        target: Location,
        wind_direction_deg: float,
        wind_speed_ms: float = 5.0,
    ) -> WindAnalysis:
        bearing = calculate_bearing(event.lat, event.lon, target.lat, target.lon)
        alignment, is_downwind_flag = WindAnalyzer.calculate_wind_alignment(
            bearing,
            wind_direction_deg,
        )
        return {
            "wind_direction_deg": wind_direction_deg,
            "wind_speed_ms": wind_speed_ms,
            "bearing_to_target_deg": bearing,
            "alignment_score": alignment,
            "is_downwind": is_downwind_flag,
        }


class SpatialAnalyzer:
    @staticmethod
    def calculate_distance(event: Event, target: Location) -> float:
        return round(
            haversine_distance(event.lat, event.lon, target.lat, target.lon),
            3,
        )

    @staticmethod
    def calculate_bearing(event: Event, target: Location) -> float:
        return round(
            calculate_bearing(event.lat, event.lon, target.lat, target.lon) % 360.0,
            2,
        )

    @staticmethod
    def calculate_proximity_score(
        distance_km: float,
        max_distance_km: float = 500.0,
    ) -> float:
        if distance_km < 0:
            raise ValueError("distance_km cannot be negative.")
        if max_distance_km <= 0:
            raise ValueError("max_distance_km must be greater than zero.")
        score = 1.0 - (distance_km / max_distance_km)
        return round(max(0.0, min(1.0, score)), 3)

    def analyze_proximity(
        self,
        event: Event,
        target: Location,
        max_distance_km: float = 500.0,
    ) -> SpatialEvidence:
        distance = self.calculate_distance(event, target)
        bearing = self.calculate_bearing(event, target)
        proximity = self.calculate_proximity_score(distance, max_distance_km)
        return {
            "event_id": event.id,
            "target_id": target.id,
            "distance_km": distance,
            "proximity_score": proximity,
            "bearing_deg": bearing,
        }


class SpatialWindAnalyzer:
    def __init__(self):
        self.spatial = SpatialAnalyzer()
        self.wind = WindAnalyzer()

    def analyze_event_impact(
        self,
        event: Event,
        target: Location,
        wind_direction_deg: float,
        wind_speed_ms: float = 5.0,
        max_distance_km: float = 500.0,
    ) -> dict[str, Any]:
        spatial = self.spatial.analyze_proximity(event, target, max_distance_km)
        wind = self.wind.analyze_wind(event, target, wind_direction_deg, wind_speed_ms)
        spatial["wind_alignment"] = round(wind["alignment_score"], 3)
        spatial["downwind"] = wind["is_downwind"]
        spatial["wind_direction_deg"] = wind["wind_direction_deg"]
        return spatial

    def analyze_multiple_targets(
        self,
        event: Event,
        targets: Iterable[Location],
        wind_direction_deg: float,
        wind_speed_ms: float = 5.0,
        max_distance_km: float = 500.0,
    ) -> list[dict[str, Any]]:
        results = [
            self.analyze_event_impact(event, target, wind_direction_deg, wind_speed_ms, max_distance_km)
            for target in targets
        ]
        return sorted(results, key=lambda item: item["distance_km"])


def _demo_payload() -> dict[str, Any]:
    cairo_lat, cairo_lon = 30.0444, 31.2357
    giza_lat, giza_lon = 29.9759, 31.1371

    fire = Event(
        id="FIRE_001",
        event_type="fire",
        lat=29.8,
        lon=31.0,
        timestamp=datetime.now(),
        magnitude=None,
        metadata={"intensity": "high", "source": "NASA FIRMS"},
    )
    target = Location("CAIRO", "Cairo", cairo_lat, cairo_lon, population=20_000_000)

    distance = haversine_distance(cairo_lat, cairo_lon, giza_lat, giza_lon)
    bearing = calculate_bearing(cairo_lat, cairo_lon, giza_lat, giza_lon)
    alignment = wind_alignment(0.97, 0.0)
    downwind = is_downwind(180, 180, tolerance_deg=5)

    return {
        "distance_km": distance,
        "bearing_deg": bearing,
        "wind_alignment": alignment,
        "downwind": downwind,
        "event_impact": SpatialWindAnalyzer().analyze_event_impact(
            fire,
            target,
            wind_direction_deg=270,
            wind_speed_ms=8.0,
            max_distance_km=500.0,
        ),
    }


if __name__ == "__main__":
    payload = _demo_payload()
    print(json.dumps(payload, indent=2))
