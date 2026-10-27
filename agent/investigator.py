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
from agent import memory as investigation_memory


def investigate(
    location: str,
    question: str = "What environmental risks exist?",
    sources: Optional[List[str]] = None,
    country_hint: str = "",
    memory: bool = True,
) -> InvestigationReport:
    """End-to-end synchronous investigation workflow:

    1. Geocodes location
    2. Recalls H-MEM persistent investigation memory for this target (agent/memory.py)
    3. Collects multi-source normalized evidence (in parallel)
    4. Runs deterministic spatial/wind/temporal correlation in geo_analysis
    5. Evaluates evidence confidence and synthesizes grounded report
    6. Persists the report back into H-MEM for future investigations
    Returns structured InvestigationReport
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

    # 2. H-MEM recall: deterministic memory facts from prior investigations of this target
    memory_lines: List[str] = (
        investigation_memory.recall(resolved_name, lat, lon) if (memory and location and geo_evidence.status == "ok") else []
    )
    memory_used = bool(memory_lines)

    # 3. Gather Evidence
    sources_to_query = sources or ["weather", "air_quality", "fire"]
    evidence_items = collect_evidence(lat, lon, sources=sources_to_query)

    # Include geocode evidence for full citation traceability
    all_evidence = [geo_evidence] + evidence_items

    # 4. Deterministic Geo & Risk Analysis
    analysis = analyze_evidence(
        all_evidence,
        target_name=resolved_name,
        target_lat=lat,
        target_lon=lon,
    )

    # 5. Reasoner Synthesis & Confidence Assessment
    confidence = compute_confidence(evidence_items)
    synthesis = generate_synthesis(question, analysis, evidence_items, memory_lines=memory_lines)

    comps = analysis["components"]
    risk_comps = RiskComponents(
        proximity=comps["proximity"],
        wind_alignment=comps["wind_alignment"],
        air_quality_anomaly=comps["air_quality_anomaly"],
        temporal_correlation=comps["temporal_correlation"],
    )

    report = InvestigationReport(
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
        summary_source=synthesis["summary_source"],
        guardrail_notes=synthesis["guardrail_notes"],
        data_gaps=synthesis["data_gaps"],
        memory_used=memory_used,
        memory_notes=memory_lines,
    )

    # 6. H-MEM store: future investigations of this target will recall today's facts
    investigation_memory.remember(report)
    return report


async def investigate_stream(
    location: str,
    question: str = "What environmental risks exist?",
    sources: Optional[List[str]] = None,
    country_hint: str = "",
    memory: bool = True,
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

    # H-MEM recall (deterministic, offline): prior-investigation facts for this target
    memory_lines: List[str] = (
        investigation_memory.recall(resolved_name, lat, lon) if (memory and geo_evidence.status == "ok") else []
    )
    if memory_lines:
        yield {
            "event": "stage",
            "stage": "memory_recalled",
            "message": f"H-MEM recalled {len(memory_lines)} fact(s) from prior investigation(s) of {resolved_name}",
            "memory_notes": memory_lines,
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
        functools.partial(generate_synthesis, question, analysis, evidence_items,
                          memory_lines=memory_lines),
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
        summary_source=synthesis["summary_source"],
        guardrail_notes=synthesis["guardrail_notes"],
        data_gaps=synthesis["data_gaps"],
        memory_used=bool(memory_lines),
        memory_notes=memory_lines,
    )

    # H-MEM store: future investigations of this target will recall today's facts
    if memory:
        await loop.run_in_executor(None, functools.partial(investigation_memory.remember, report))

    # Stage 5: Completed
    yield {
        "event": "completed",
        "stage": "completed",
        "message": "Investigation completed successfully",
        "investigation_id": investigation_id,
        "report": report.model_dump(),
    }
