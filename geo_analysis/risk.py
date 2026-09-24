"""Risk scoring.

The risk layer consumes normalized outputs from Person 3A and other analysis
modules. It deliberately does NOT recalculate geographic distances or wind
directions.

All component scores are expected to be normalized to [0, 1].
"""

from __future__ import annotations

import math
from typing import Any, Mapping, Optional


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def fire_proximity_score(
    distance_km: float,
    *,
    max_distance_km: float = 100.0,
) -> float:
    """Convert fire distance into a proximity score.

    0 km -> 1.0
    max_distance_km or farther -> 0.0

    The default is intentionally simple for the MVP. Tune the threshold with
    the project team when domain requirements become clearer.
    """
    if distance_km < 0:
        raise ValueError("distance_km cannot be negative")
    if max_distance_km <= 0:
        raise ValueError("max_distance_km must be > 0")

    score = 1.0 - (float(distance_km) / max_distance_km)
    return round(_clamp(score), 4)


def wind_alignment_score(
    alignment: Optional[float] = None,
    *,
    downwind: Optional[bool] = None,
) -> float:
    """Normalize Person 3A's wind evidence to [0, 1].

    Preferred input:
        alignment: a value already calculated by Person 3A, e.g. 0.97.

    Fallback:
        downwind=True -> 1.0
        downwind=False -> 0.0
    """
    if alignment is not None:
        return round(_clamp(alignment), 4)

    if downwind is not None:
        return 1.0 if downwind else 0.0

    return 0.0


def air_quality_anomaly_score(
    anomaly: float,
    *,
    anomaly_cap: float = 3.0,
) -> float:
    """Convert a relative air-quality anomaly into [0, 1].

    `anomaly` is a ratio, not a percentage:
        baseline 20 -> observed 60
        anomaly = (60 - 20) / 20 = 2.0

    The cap prevents an extreme measurement from dominating the whole risk
    score. A 2.0 anomaly with the default cap gives 2/3.
    """
    if anomaly < 0:
        raise ValueError("anomaly cannot be negative")
    if anomaly_cap <= 0:
        raise ValueError("anomaly_cap must be > 0")

    return round(_clamp(anomaly / anomaly_cap), 4)


def temporal_correlation_score(correlation: float) -> float:
    """Clamp a temporal correlation score to [0, 1]."""
    return round(_clamp(correlation), 4)


def calculate_risk(
    *,
    proximity_score: float,
    wind_alignment: float,
    air_quality_anomaly: float,
    temporal_correlation: float,
    weights: Optional[Mapping[str, float]] = None,
) -> float:
    """Combine evidence scores into one normalized risk score.

    Default weights:
        proximity          25%
        wind alignment     30%
        air-quality       25%
        temporal           20%

    The weights are normalized internally, so they do not have to sum to 1.
    """
    default_weights = {
        "proximity": 0.25,
        "wind": 0.30,
        "air_quality": 0.25,
        "temporal": 0.20,
    }

    if weights is None:
        weights = default_weights

    required = set(default_weights)
    if set(weights) != required:
        raise ValueError(
            f"weights must contain exactly: {sorted(required)}"
        )

    total_weight = sum(float(value) for value in weights.values())
    if total_weight <= 0:
        raise ValueError("weights must have a positive total")

    components = {
        "proximity": _clamp(proximity_score),
        "wind": _clamp(wind_alignment),
        "air_quality": _clamp(air_quality_anomaly),
        "temporal": _clamp(temporal_correlation),
    }

    weighted_sum = sum(
        components[name] * float(weights[name])
        for name in components
    )

    return round(_clamp(weighted_sum / total_weight), 4)


def calculate_risk_from_spatial(
    spatial_evidence: Mapping[str, Any],
    *,
    air_quality_anomaly: float,
    temporal_correlation: float,
    weights: Optional[Mapping[str, float]] = None,
) -> dict[str, Any]:
    """Convenience wrapper for the Person 3A -> Person 3B interface.

    Expected Person 3A fields:
        event_id
        target_id
        distance_km
        proximity_score
        wind_alignment
        downwind
    """
    proximity = spatial_evidence.get("proximity_score")
    if proximity is None:
        proximity = fire_proximity_score(
            spatial_evidence["distance_km"]
        )

    wind = wind_alignment_score(
        spatial_evidence.get("wind_alignment"),
        downwind=spatial_evidence.get("downwind"),
    )

    score = calculate_risk(
        proximity_score=proximity,
        wind_alignment=wind,
        air_quality_anomaly=air_quality_anomaly,
        temporal_correlation=temporal_correlation,
        weights=weights,
    )

    return {
        "event_id": spatial_evidence.get("event_id"),
        "target_id": spatial_evidence.get("target_id"),
        "risk_score": score,
        "components": {
            "proximity": round(_clamp(proximity), 4),
            "wind_alignment": wind,
            "air_quality_anomaly": round(_clamp(air_quality_anomaly), 4),
            "temporal_correlation": round(_clamp(temporal_correlation), 4),
        },
    }
