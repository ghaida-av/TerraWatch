"""TerraWatch normalized data model.

The agent, analysis engine, backend and UI only ever see `Evidence`. No adapter leaks its
upstream API format. All timestamps are UTC ISO-8601 (…Z). All distances are km.
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

SCHEMA_VERSION = "1.0"

EvidenceKind = Literal["weather", "air_quality", "fire", "earthquake", "geo", "geocode"]
EvidenceStatus = Literal[
    "ok",       # data returned (an empty list of fires/quakes is still "ok": absence of events is evidence)
    "no_data",  # source reachable but has NO coverage here (e.g. no air-quality station). NOT "clean air".
    "error",    # source failed; see `error`
]
DataMode = Literal["live", "cache", "stale_cache", "demo", "mock"]


class GeoPoint(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)


class ErrorInfo(BaseModel):
    type: str           # timeout | network | rate_limited | auth | missing_credentials | not_found | ...
    message: str
    retryable: bool = False
    http_status: Optional[int] = None


class Evidence(BaseModel):
    """The single envelope every adapter returns."""

    schema_version: str = SCHEMA_VERSION
    evidence_id: str                      # stable id for citations / evidence-graph nodes
    source: str                           # open-meteo | openaq | open-meteo-air-quality | nasa_firms | usgs | geoapify | ...
    kind: EvidenceKind
    status: EvidenceStatus
    data_mode: DataMode                   # where this answer really came from — the UI should badge demo/mock/stale
    timestamp: str                        # time the data refers to (UTC). Falls back to fetched_at
    fetched_at: str                       # when TerraWatch produced this evidence (UTC)
    location: Optional[GeoPoint] = None
    query: Dict[str, Any] = Field(default_factory=dict)         # normalized params actually used
    measurements: Dict[str, Any] = Field(default_factory=dict)  # compact summary — what the LLM reads
    units: Dict[str, str] = Field(default_factory=dict)
    observations: List[Dict[str, Any]] = Field(default_factory=list)  # full-fidelity rows for the analysis engine
    raw_reference: Optional[str] = None   # key-free upstream URL for traceability
    warnings: List[str] = Field(default_factory=list)
    error: Optional[ErrorInfo] = None
    is_modeled: bool = False              # True when values are model output, not sensor/satellite observations

    def for_llm(self) -> Dict[str, Any]:
        """Token-light view for the agent: drops `observations` (kept in the evidence store)."""
        d = self.model_dump(mode="json", exclude={"observations", "query", "schema_version"})
        d["observation_count"] = len(self.observations)
        return d


# ------------------------------------------------------------------ weather
class WeatherPoint(BaseModel):
    time: str
    temperature_c: Optional[float] = None
    relative_humidity_pct: Optional[float] = None
    wind_speed_kmh: Optional[float] = None
    wind_direction_deg: Optional[float] = None   # METEOROLOGICAL: direction the wind blows FROM
    wind_gusts_kmh: Optional[float] = None
    precipitation_mm: Optional[float] = None


class WeatherMeasurements(BaseModel):
    current: Optional[WeatherPoint] = None
    window_start: Optional[str] = None
    window_end: Optional[str] = None
    hourly_count: int = 0


# ------------------------------------------------------------------ air quality
class AirQualityStation(BaseModel):
    id: int
    name: Optional[str] = None
    lat: float
    lon: float
    distance_km: float
    last_updated: Optional[str] = None
    provider: Optional[str] = None


class AirQualityMeasurements(BaseModel):
    pm25: Optional[float] = None
    pm10: Optional[float] = None
    no2: Optional[float] = None
    o3: Optional[float] = None
    co: Optional[float] = None
    so2: Optional[float] = None
    observed_at: Dict[str, str] = Field(default_factory=dict)   # per-pollutant observation time
    station: Optional[AirQualityStation] = None                 # None when values are modeled


class AirQualityPoint(BaseModel):
    parameter: str
    time: str
    value: float
    unit: Optional[str] = None


# ------------------------------------------------------------------ fire
class FireHotspot(BaseModel):
    lat: float
    lon: float
    distance_km: float                           # fire -> requested location
    bearing_fire_to_location_deg: float          # compass bearing from the fire toward the location
    detected_at: Optional[str] = None
    frp_mw: Optional[float] = None               # fire radiative power
    brightness_k: Optional[float] = None
    confidence: Optional[str] = None             # low | nominal | high
    daynight: Optional[str] = None
    satellite: Optional[str] = None


class FireMeasurements(BaseModel):
    hotspot_count: int
    radius_km: float
    window_days: int
    product: str
    nearest_km: Optional[float] = None
    total_frp_mw: float = 0.0
    max_frp_mw: Optional[float] = None
    high_confidence_count: int = 0
    earliest_detection: Optional[str] = None
    latest_detection: Optional[str] = None
    closest_fires: List[FireHotspot] = Field(default_factory=list)


# ------------------------------------------------------------------ earthquake
class QuakeEvent(BaseModel):
    id: str
    magnitude: Optional[float] = None
    place: Optional[str] = None
    time: Optional[str] = None
    lat: float
    lon: float
    depth_km: Optional[float] = None
    distance_km: float
    url: Optional[str] = None
    alert: Optional[str] = None
    tsunami: Optional[int] = None


class EarthquakeMeasurements(BaseModel):
    event_count: int
    radius_km: float
    window_days: int
    min_magnitude: float
    max_magnitude: Optional[float] = None
    nearest_km: Optional[float] = None
    strongest: List[QuakeEvent] = Field(default_factory=list)
    closest: List[QuakeEvent] = Field(default_factory=list)


# ------------------------------------------------------------------ geo / infrastructure
class Place(BaseModel):
    name: Optional[str] = None
    categories: List[str] = Field(default_factory=list)
    lat: float
    lon: float
    distance_km: float


class GeoMeasurements(BaseModel):
    feature_count: int
    radius_m: int
    categories_requested: str
    by_category: Dict[str, int] = Field(default_factory=dict)
    nearest: List[Place] = Field(default_factory=list)


# ------------------------------------------------------------------ geocode
class GeocodeMeasurements(BaseModel):
    matched_name: Optional[str] = None
    tz_name: str = "UTC"
    country: Optional[str] = None
    country_code: Optional[str] = None
