"""Investigation management routes."""

from __future__ import annotations

from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException, Query, status

from agent.investigator import investigate
from agent.models import InvestigationReport
from apps.api.models import (
    CreateInvestigationRequest,
    InvestigationListResponse,
)
from apps.api.storage import (
    get_investigation,
    list_investigations,
    save_investigation,
)

router = APIRouter(prefix="/investigations", tags=["Investigations"])


@router.post("", response_model=InvestigationReport, status_code=status.HTTP_201_CREATED)
def create_investigation(payload: CreateInvestigationRequest) -> InvestigationReport:
    """Run an end-to-end environmental crisis investigation.
    
    Collects normalized evidence across requested data sources, computes deterministic
    geo and risk metrics, runs reasoner synthesis, persists the result, and returns
    the structured report.
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

    # Persist report to SQLite
    save_investigation(report)
    return report


@router.get("", response_model=InvestigationListResponse)
def get_all_investigations(
    limit: int = Query(default=50, ge=1, le=100, description="Max items to return"),
    offset: int = Query(default=0, ge=0, description="Pagination offset"),
) -> InvestigationListResponse:
    """Retrieve historical investigations with pagination."""
    return list_investigations(limit=limit, offset=offset)


@router.get("/{investigation_id}", response_model=InvestigationReport)
def get_investigation_by_id(investigation_id: str) -> InvestigationReport:
    """Retrieve complete investigation report by ID."""
    report = get_investigation(investigation_id)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investigation '{investigation_id}' not found.",
        )
    return report


@router.get("/{investigation_id}/graph")
def get_investigation_graph(investigation_id: str) -> Dict[str, Any]:
    """Retrieve specifically the evidence graph for visualizer consumption."""
    report = get_investigation(investigation_id)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investigation '{investigation_id}' not found.",
        )
    return report.evidence_graph
