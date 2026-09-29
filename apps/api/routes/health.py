"""Health check and telemetry routes."""

from __future__ import annotations

import os
from typing import Any, Dict, List
from fastapi import APIRouter

from apps.api.config import settings
from apps.api.models import HealthResponse
from data.registry import ADAPTERS, ALL_SOURCES, MVP_SOURCES

router = APIRouter(tags=["Health & Telemetry"])


@router.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    """Return health check and runtime mode information."""
    return HealthResponse(
        status="ok",
        mode=os.getenv("TERRAWATCH_MODE", settings.MODE),
        version="0.1.0",
        active_sources=list(ALL_SOURCES),
    )


@router.get("/sources")
def get_sources() -> Dict[str, Any]:
    """Return status and metadata for all available evidence adapters."""
    mode = os.getenv("TERRAWATCH_MODE", settings.MODE)
    sources_info = []

    for name, adapter_instance in ADAPTERS.items():
        sources_info.append(
            {
                "id": name,
                "kind": adapter_instance.kind,
                "is_mvp": name in MVP_SOURCES,
                "mode": mode,
            }
        )


    return {
        "mode": mode,
        "total_sources": len(sources_info),
        "sources": sources_info,
    }

