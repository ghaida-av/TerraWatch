"""Investigation management routes."""

from __future__ import annotations

import json
from typing import Any, AsyncGenerator, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from agent.investigator import investigate, investigate_stream
from agent.models import InvestigationReport
from apps.api.models import (
    CreateInvestigationRequest,
    InvestigationListResponse,
)
from apps.api.storage import (
    get_investigation_async,
    list_investigations_async,
    save_investigation_async,
)

router = APIRouter(prefix="/investigations", tags=["Investigations"])


@router.post("", response_model=InvestigationReport, status_code=status.HTTP_201_CREATED)
async def create_investigation(payload: CreateInvestigationRequest) -> InvestigationReport:
    """Run an end-to-end environmental crisis investigation asynchronously.
    
    Collects normalized evidence across requested data sources, computes deterministic
    geo and risk metrics, runs reasoner synthesis, persists the result with SQLAlchemy,
    and returns the structured report.
    """
    try:
        report = investigate(
            location=payload.location,
            question=payload.question,
            sources=payload.sources,
            country_hint=payload.country_hint,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Investigation failed: {str(exc)}",
        ) from exc

    # Persist report asynchronously via SQLAlchemy
    await save_investigation_async(report)
    return report


@router.get("/stream")
async def stream_investigation_endpoint(
    location: str = Query(..., description="Target location to investigate"),
    question: str = Query(
        default="What environmental risks exist?",
        description="Crisis or inquiry question",
    ),
    sources: Optional[List[str]] = Query(
        default=None,
        description="Sources to query (e.g. weather, air_quality, fire)",
    ),
    country_hint: str = Query(default="", description="Optional country hint"),
) -> StreamingResponse:
    """Server-Sent Events (SSE) stream yielding real-time progress events.

    Streams each stage: geocoding, collecting_evidence, geo_analysis, reasoning, completed.
    Automatically persists the completed investigation report to the database.
    """
    async def event_generator() -> AsyncGenerator[str, None]:
        completed_report: Optional[InvestigationReport] = None
        try:
            async for event_data in investigate_stream(
                location=location,
                question=question,
                sources=sources,
                country_hint=country_hint,
            ):
                event_type = event_data.get("event", "message")
                payload_str = json.dumps(event_data)
                yield f"event: {event_type}\ndata: {payload_str}\n\n"

                if event_data.get("stage") == "completed" and "report" in event_data:
                    completed_report = InvestigationReport.model_validate(event_data["report"])

            # Save report to DB upon completion
            if completed_report is not None:
                await save_investigation_async(completed_report)

        except Exception as exc:
            err_payload = json.dumps({"event": "error", "message": str(exc)})
            yield f"event: error\ndata: {err_payload}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("", response_model=InvestigationListResponse)
async def get_all_investigations(
    limit: int = Query(default=50, ge=1, le=100, description="Max items to return"),
    offset: int = Query(default=0, ge=0, description="Pagination offset"),
) -> InvestigationListResponse:
    """Retrieve historical investigations with pagination asynchronously."""
    return await list_investigations_async(limit=limit, offset=offset)


@router.get("/{investigation_id}", response_model=InvestigationReport)
async def get_investigation_by_id(investigation_id: str) -> InvestigationReport:
    """Retrieve complete investigation report by ID asynchronously."""
    report = await get_investigation_async(investigation_id)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investigation '{investigation_id}' not found.",
        )
    return report


@router.get("/{investigation_id}/graph")
async def get_investigation_graph(investigation_id: str) -> Dict[str, Any]:
    """Retrieve specifically the evidence graph for visualizer consumption."""
    report = await get_investigation_async(investigation_id)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investigation '{investigation_id}' not found.",
        )
    return report.evidence_graph
