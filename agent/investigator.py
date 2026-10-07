"""Core investigation orchestrator for TerraWatch."""

from __future__ import annotations

import asyncio
import uuid
from typing import Any, AsyncGenerator, Dict, List, Optional

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
    """End-to-end synchronous investigation workflow:

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


async def investigate_stream(
    location: str,
    question: str = "What environmental risks exist?",
    sources: Optional[List[str]] = None,
    country_hint: str = "",
) -> AsyncGenerator[Dict[str, Any], None]:
    """Asynchronous generator yielding stage-by-stage events during investigation.

    Yields:
        {"stage": "geocoding", "message": "...", "data": {...}}
        {"stage": "collecting_evidence", "message": "...", "data": {...}}
        {"stage": "geo_analysis", "message": "...", "data": {...}}
        {"stage": "reasoning", "message": "...", "data": {...}}
        {"stage": "completed", "message": "...", "report": InvestigationReport}
    """
    investigation_id = f"inv_{uuid.uuid4().hex[:10]}"

    # Stage 1: Geocoding
    yield {
        "event": "stage",
        "stage": "geocoding",
        "message": f"Geocoding target location '{location}'...",
        "investigation_id": investigation_id,
    }
    await asyncio.sleep(0)  # Yield control to event loop

    geo_evidence = geocode(location, country_hint)
    if geo_evidence.status == "ok" and geo_evidence.location:
        lat = geo_evidence.location.lat
        lon = geo_evidence.location.lon
        resolved_name = geo_evidence.measurements.get("matched_name") or location
    else:
        lat = 30.0444
        lon = 31.2357
        resolved_name = location

    target_loc = InvestigationLocation(name=resolved_name, lat=lat, lon=lon)

    yield {
        "event": "stage",
        "stage": "geocoded",
        "message": f"Resolved target '{resolved_name}' at ({lat:.4f}, {lon:.4f})",
        "target": target_loc.model_dump(),
        "investigation_id": investigation_id,
    }

    # Stage 2: Collecting Evidence
    sources_to_query = sources or ["weather", "air_quality", "fire"]
    yield {
        "event": "stage",
        "stage": "collecting_evidence",
        "message": f"Gathering evidence from {len(sources_to_query)} sources: {', '.join(sources_to_query)}...",
        "sources": sources_to_query,
        "investigation_id": investigation_id,
    }
    await asyncio.sleep(0)

    # Run evidence collection in threadpool if sync I/O to avoid blocking event loop
    loop = asyncio.get_running_loop()
    evidence_items = await loop.run_in_executor(
        None, collect_evidence, lat, lon, sources_to_query
    )
    all_evidence = [geo_evidence] + evidence_items

    yield {
        "event": "stage",
        "stage": "evidence_collected",
        "message": f"Collected {len(evidence_items)} evidence envelopes",
        "evidence_count": len(evidence_items),
        "citations": [e.evidence_id for e in all_evidence],
        "investigation_id": investigation_id,
    }

    # Stage 3: Geo & Deterministic Risk Analysis
    yield {
        "event": "stage",
        "stage": "geo_analysis",
        "message": "Computing deterministic spatial distances, wind vectors, and anomaly delta...",
        "investigation_id": investigation_id,
    }
    await asyncio.sleep(0)

    import functools
    analysis_func = functools.partial(
        analyze_evidence,
        all_evidence,
        target_name=resolved_name,
        target_lat=lat,
        target_lon=lon,
    )
    analysis = await loop.run_in_executor(None, analysis_func)

    yield {
        "event": "stage",
        "stage": "analysis_computed",
        "message": f"Risk level computed: {analysis['risk_level']} (Score: {analysis['risk_score']:.2f})",
        "risk_level": analysis["risk_level"],
        "risk_score": analysis["risk_score"],
        "components": analysis["components"],
        "investigation_id": investigation_id,
    }

    # Stage 4: Reasoner Synthesis
    yield {
        "event": "stage",
        "stage": "reasoning",
        "message": "Evaluating evidence confidence and generating grounded synthesis...",
        "investigation_id": investigation_id,
    }
    await asyncio.sleep(0)

    confidence = compute_confidence(evidence_items)
    synthesis = await loop.run_in_executor(
        None,
        generate_synthesis,
        question,
        analysis,
        evidence_items,
    )

    comps = analysis["components"]
    risk_comps = RiskComponents(
        proximity=comps["proximity"],
        wind_alignment=comps["wind_alignment"],
        air_quality_anomaly=comps["air_quality_anomaly"],
        temporal_correlation=comps["temporal_correlation"],
    )

    report = InvestigationReport(
        investigation_id=investigation_id,
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

    # Stage 5: Completed
    yield {
        "event": "completed",
        "stage": "completed",
        "message": "Investigation completed successfully",
        "investigation_id": investigation_id,
        "report": report.model_dump(),
    }
