"""Pydantic schemas for the TerraWatch API layer."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CreateInvestigationRequest(BaseModel):
    """Payload to trigger an environmental crisis investigation."""
    location: str = Field(..., description="Target city or location name", examples=["Cairo"])
    question: str = Field(
        default="What environmental risks exist?",
        description="Crisis query or hypothesis to evaluate",
        examples=["Is smoke from nearby fires reaching the city?"],
    )
    sources: Optional[List[str]] = Field(
        default=None,
        description="List of data sources to query (defaults to ['weather', 'air_quality', 'fire'])",
        examples=[["weather", "air_quality", "fire"]],
    )
    country_hint: str = Field(
        default="",
        description="Country hint to disambiguate target (e.g. 'Egypt')",
        examples=["Egypt"],
    )


class InvestigationSummary(BaseModel):
    """Lightweight metadata for listing past investigations."""
    investigation_id: str
    target_name: str
    lat: float
    lon: float
    question: str
    risk_level: str
    risk_score: float
    confidence: float
    created_at: str


class InvestigationListResponse(BaseModel):
    total: int
    items: List[InvestigationSummary]


class HealthResponse(BaseModel):
    status: str
    mode: str
    version: str
    active_sources: List[str]
