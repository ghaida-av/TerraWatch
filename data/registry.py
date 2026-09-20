"""Single entry point for the agent / backend.

    from data import collect_evidence
    evidence = collect_evidence(30.0444, 31.2357, sources=["weather", "air_quality", "fire"])

Sources run in parallel (all I/O bound). One failing source never blocks the others — its
Evidence just has status="error".
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, Iterable, List, Optional

from data.adapters import (AirQualityAdapter, EarthquakeAdapter, FireAdapter, GeoAdapter, GeocodeAdapter,
                           WeatherAdapter)
from data.schemas.models import Evidence

ADAPTERS = {
    "weather": WeatherAdapter(),
    "air_quality": AirQualityAdapter(),
    "fire": FireAdapter(),
    "earthquake": EarthquakeAdapter(),
    "geo": GeoAdapter(),
}
GEOCODER = GeocodeAdapter()

MVP_SOURCES = ("weather", "air_quality", "fire")  # the Day-1 vertical slice
ALL_SOURCES = tuple(ADAPTERS)


def collect_evidence(lat: float, lon: float, sources: Optional[Iterable[str]] = None,
                     params: Optional[Dict[str, Dict[str, Any]]] = None) -> List[Evidence]:
    """`params` optionally overrides per-source arguments, e.g. {"fire": {"radius_km": 300}}."""
    names = list(sources) if sources is not None else list(MVP_SOURCES)
    unknown = [n for n in names if n not in ADAPTERS]
    if unknown:
        raise ValueError(f"Unknown source(s) {unknown}; choose from {list(ADAPTERS)}")
    params = params or {}
    with ThreadPoolExecutor(max_workers=len(names) or 1) as pool:
        futures = [pool.submit(ADAPTERS[n].fetch, lat, lon, **params.get(n, {})) for n in names]
        return [f.result() for f in futures]


def geocode(city: str, country_or_continent: str = "") -> Evidence:
    return GEOCODER.fetch(city, country_or_continent)
