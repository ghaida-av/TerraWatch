"""Public Geo analysis API for TerraWatch.

Exposes spatial & wind analysis, temporal correlation, risk scoring,
evidence graph generation, and the unified pipeline bridge.
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
from .pipeline import analyze_evidence
from .risk import (
    calculate_risk,
    calculate_risk_from_spatial,
    fire_proximity_score,
    wind_alignment_score,
    air_quality_anomaly_score,
    temporal_correlation_score,
)
from .temporal import time_difference, temporal_correlation
from .evidence_graph import (
    create_evidence_graph,
    add_node,
    add_relationship,
    build_incident_graph,
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
    "analyze_evidence",
    "calculate_risk",
    "calculate_risk_from_spatial",
    "fire_proximity_score",
    "wind_alignment_score",
    "air_quality_anomaly_score",
    "temporal_correlation_score",
    "time_difference",
    "temporal_correlation",
    "create_evidence_graph",
    "add_node",
    "add_relationship",
    "build_incident_graph",
]
