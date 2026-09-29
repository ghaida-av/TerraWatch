"""Evidence drill-down routes."""

from __future__ import annotations

from typing import Any, Dict
from fastapi import APIRouter, HTTPException, status

from data.schemas.models import Evidence
from data.store import get_evidence

router = APIRouter(prefix="/evidence", tags=["Evidence"])


@router.get("/{evidence_id}", response_model=Evidence)
def get_raw_evidence(evidence_id: str) -> Evidence:
    """Retrieve full-fidelity evidence envelope by ID (including all observations)."""
    ev = get_evidence(evidence_id)
    if ev is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evidence with ID '{evidence_id}' not found in store.",
        )
    return ev
