"""Data models for the TerraWatch Agent layer."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class InvestigationLocation(BaseModel):
    name: str
    lat: float
    lon: float


class RiskComponents(BaseModel):
    proximity: float
    wind_alignment: float
    air_quality_anomaly: float
    temporal_correlation: float


class InvestigationReport(BaseModel):
    investigation_id: str
    target: InvestigationLocation
    question: str
    status: str = "completed"
    risk_level: str  # LOW | MODERATE | HIGH | CRITICAL
    risk_score: float  # 0.0 to 1.0
    confidence: float  # 0.0 to 1.0
    components: RiskComponents
    signals: Dict[str, Any]
    key_findings: List[str]
    risk_indicators: List[str]
    executive_summary: str
    evidence_graph: Dict[str, Any]
    evidence_citations: List[str]
