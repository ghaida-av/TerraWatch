"""Core investigation orchestrator for TerraWatch."""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from data import collect_evidence, geocode
from data.schemas.models import Evidence
from geo_analysis.pipeline import analyze_evidence
from agent.models import (
    InvestigationLocation,
    InvestigationReport,
    RiskComponents,
)
from agent.reasoner import compute_confidence, generate_synthesis


def investigate(
    location: str,
    question: str = "What environmental risks exist?",
    sources: Optional[List[str]] = None,
    country_hint: str = "",
) -> InvestigationReport:
    """End-to-end investigation workflow:

    1. Geocodes location
    2. Collects multi-source normalized evidence (in parallel)
    3. Runs deterministic spatial/wind/temporal correlation in geo_analysis
    4. Evaluates evidence confidence and synthesizes grounded report
    5. Returns structured InvestigationReport
    """
    # 1. Geocode location
    geo_evidence = geocode(location, country_hint)
    if geo_evidence.status == "ok" and geo_evidence.location:
        lat = geo_evidence.location.lat
        lon = geo_evidence.location.lon
        resolved_name = geo_evidence.measurements.get("matched_name") or location
    else:
        # Default to raw string query or fallback
        lat = 30.0444
        lon = 31.2357
        resolved_name = location

    target_loc = InvestigationLocation(name=resolved_name, lat=lat, lon=lon)

    # 2. Gather Evidence
    sources_to_query = sources or ["weather", "air_quality", "fire"]
    evidence_items = collect_evidence(lat, lon, sources=sources_to_query)

    # Include geocode evidence for full citation traceability
    all_evidence = [geo_evidence] + evidence_items

    # 3. Deterministic Geo & Risk Analysis
    analysis = analyze_evidence(
        all_evidence,
        target_name=resolved_name,
        target_lat=lat,
        target_lon=lon,
    )

    # 4. Reasoner Synthesis & Confidence Assessment
    confidence = compute_confidence(evidence_items)
    synthesis = generate_synthesis(question, analysis, evidence_items)

    comps = analysis["components"]
    risk_comps = RiskComponents(
        proximity=comps["proximity"],
        wind_alignment=comps["wind_alignment"],
        air_quality_anomaly=comps["air_quality_anomaly"],
        temporal_correlation=comps["temporal_correlation"],
    )

    return InvestigationReport(
        investigation_id=f"inv_{uuid.uuid4().hex[:10]}",
        target=target_loc,
        question=question,
        status="completed",
        risk_level=analysis["risk_level"],
        risk_score=analysis["risk_score"],
        confidence=confidence,
        components=risk_comps,
        signals=analysis["signals"],
        key_findings=synthesis["key_findings"],
        risk_indicators=synthesis["risk_indicators"],
        executive_summary=synthesis["executive_summary"],
        evidence_graph=analysis["evidence_graph"],
        evidence_citations=analysis["evidence_ids_used"],
    )
