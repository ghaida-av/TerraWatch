"""Public Geo analysis API for TerraWatch.

This package exposes the combined spatial + wind implementation as the canonical
Person 3A API. The standalone spatial module was removed intentionally, and the
module now lives in spatial_and_wind.py.
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
