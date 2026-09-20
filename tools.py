"""LangChain tool wrappers with the SAME names/signatures the notebook's planner already uses
(geocode, geo_adapter, weather_adapter, air_quality_adapter, fire_adapter, earthquake_adapter).

Swap in for Person 1's notebook:

    from data.tools import TOOLS, TOOLS_BY_NAME

Tools return the compact LLM view + `evidence_id`. The analysis engine fetches the full
observation rows with `data.get_evidence(evidence_id)`.
`tz_name` is accepted for backwards compatibility and ignored: all timestamps are UTC now.
"""
from __future__ import annotations

from langchain_core.tools import tool

from data.registry import ADAPTERS, GEOCODER


@tool
def geocode(city: str, country_or_continent: str = "") -> dict:
    """Resolve a city name to latitude/longitude and IANA timezone."""
    return GEOCODER.fetch(city, country_or_continent).for_llm()


@tool
def geo_adapter(lat: float, lon: float, tz_name: str = "UTC", radius_m: int = 5000,
                categories: str = "populated_place") -> dict:
    """Find nearby geographic features / infrastructure around a point (OpenStreetMap-derived).
    `categories` is a Geoapify category list or a preset: population | critical_infrastructure | industrial."""
    return ADAPTERS["geo"].fetch(lat, lon, radius_m=radius_m, categories=categories).for_llm()


@tool
def weather_adapter(lat: float, lon: float, tz_name: str = "UTC", hours_back: int = 24) -> dict:
    """Current weather (temperature, wind speed/direction, precipitation) for a location via Open-Meteo.
    wind_direction_deg is where the wind blows FROM."""
    return ADAPTERS["weather"].fetch(lat, lon, hours_back=hours_back).for_llm()


@tool
def air_quality_adapter(lat: float, lon: float, tz_name: str = "UTC", radius_m: int = 25000) -> dict:
    """Latest PM2.5/PM10/NO2/O3/CO/SO2 from the nearest OpenAQ station (falls back to modeled data, flagged is_modeled)."""
    return ADAPTERS["air_quality"].fetch(lat, lon, radius_m=radius_m).for_llm()


@tool
def fire_adapter(lat: float, lon: float, tz_name: str = "UTC", radius_km: float = 150.0, days: int = 1) -> dict:
    """Active fire/hotspot detections (NASA FIRMS VIIRS) within radius_km, with distance/bearing to the location."""
    return ADAPTERS["fire"].fetch(lat, lon, radius_km=radius_km, days=days).for_llm()


@tool
def earthquake_adapter(lat: float, lon: float, tz_name: str = "UTC", radius_km: int = 300, days: int = 30,
                       min_mag: float = 2.5) -> dict:
    """Recent earthquakes near a location via USGS, with magnitude, depth and distance."""
    return ADAPTERS["earthquake"].fetch(lat, lon, radius_km=radius_km, days=days, min_mag=min_mag).for_llm()


TOOLS = [geocode, geo_adapter, weather_adapter, air_quality_adapter, fire_adapter, earthquake_adapter]
TOOLS_BY_NAME = {t.name: t for t in TOOLS}
