"""Backward-compatible wrapper around the canonical spatial_and_wind module.

The real implementation lives in spatial_and_wind.py. This file only re-exports
those symbols so older imports and existing tests continue to work without
copying the logic into two places.
"""

from .spatial_and_wind import (
    EARTH_RADIUS_KM,
    SpatialAnalyzer,
    SpatialWindAnalyzer,
    WindAnalyzer,
    calculate_bearing,
    haversine_distance,
    is_downwind,
    wind_alignment,
)

__all__ = [
    "EARTH_RADIUS_KM",
    "SpatialAnalyzer",
    "SpatialWindAnalyzer",
    "WindAnalyzer",
    "calculate_bearing",
    "haversine_distance",
    "is_downwind",
    "wind_alignment",
]
