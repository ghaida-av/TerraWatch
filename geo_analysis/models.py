from __future__ import annotations

from typing import Any, TypedDict


class SpatialEvidence(TypedDict, total=False):
    event_id: str
    target_id: str
    distance_km: float
    proximity_score: float
    wind_alignment: float
    downwind: bool
    bearing_deg: float


class TemporalEvidence(TypedDict, total=False):
    event_id: str
    source_time: str
    target_time: str
    delay_hours: float
    correlation_score: float


class RiskResult(TypedDict, total=False):
    event_id: str
    target_id: str
    risk_score: float
    components: dict[str, float]


class EvidenceNode(TypedDict):
    id: str
    type: str
    properties: dict[str, Any]


class EvidenceRelationship(TypedDict):
    source: str
    type: str
    target: str
    properties: dict[str, Any]
