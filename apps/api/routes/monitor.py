"""Earth Monitor routes (global event feed for the map screen)."""
from __future__ import annotations

from typing import Any, Dict
from fastapi import APIRouter, HTTPException, Query

from data.adapters.usgs.global_feed import get_global_events
from data.core.errors import AdapterError

router = APIRouter(prefix="/monitor", tags=["Earth Monitor"])


@router.get("/events")
def global_events(
    window: str = Query(default="day", pattern="^(hour|day|week)$", description="Time window"),
    min_mag: float = Query(default=2.5, ge=0, le=9, description="Minimum magnitude"),
    limit: int = Query(default=100, ge=1, le=500),
) -> Dict[str, Any]:
    """Recent earthquakes worldwide (live USGS feed or explicit mock mode)."""
    try:
        return get_global_events(window=window, min_mag=min_mag, limit=limit)
    except AdapterError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Live USGS earthquake feed unavailable: {exc.message}",
        ) from exc
