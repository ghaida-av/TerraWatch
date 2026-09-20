"""FireAdapter — NASA FIRMS VIIRS active-fire detections.

Fixes vs the notebook prototype:
  * keeps detection TIME (acq_date + acq_time, UTC), FRP, confidence — temporal correlation needs them
  * parses by CSV header instead of column index; detects FIRMS's plain-text error replies (HTTP 200!)
  * radius in km with a true haversine filter (a degree box is ~111 km N-S but shrinks E-W with latitude)
  * the API key never appears in `raw_reference` or error messages
"""
from __future__ import annotations

import csv
import io
from datetime import date
from typing import Any, Dict, List

from data.adapters.base import BaseAdapter, Fetched
from data.config import get_secret
from data.core import http, mock_scenario as ms
from data.core.errors import AdapterError, ErrorType
from data.core.geo import bbox_from_radius, bearing_deg, haversine_km
from data.core.timeutil import to_utc_iso, utc_now
from data.schemas.models import FireHotspot, FireMeasurements

FIRMS_URL = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"
NRT_MAX_AGE_DAYS = 60  # beyond this we switch to the standard-processing archive product
CONFIDENCE = {"l": "low", "n": "nominal", "h": "high"}
MAX_OBSERVATIONS = 200


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


class FireAdapter(BaseAdapter):
    source = "nasa_firms"
    kind = "fire"
    ttl_seconds = 7200
    defaults = {"radius_km": 150.0, "days": 1, "top_k": 5, "start_date": None, "product": "VIIRS_NOAA20_NRT"}

    def _fetch_live(self, lat, lon, params) -> Fetched:
        key = get_secret("FIRMS_MAP_KEY")
        if not key:
            raise AdapterError(ErrorType.MISSING_CREDENTIALS, "FIRMS_MAP_KEY is not set")
        radius = max(1.0, min(float(params["radius_km"]), 500.0))
        days = max(1, min(int(params["days"]), 5))  # FIRMS area API allows 1-5 days per request
        product, start = params["product"], params["start_date"]
        warnings: List[str] = []
        if start:
            try:
                age = (utc_now().date() - date.fromisoformat(str(start))).days
            except ValueError:
                raise AdapterError(ErrorType.BAD_REQUEST, f"start_date must be YYYY-MM-DD, got {start!r}")
            if age > NRT_MAX_AGE_DAYS and product.endswith("_NRT"):
                product = "VIIRS_SNPP_SP"
                warnings.append("Requested date is old: using standard-processing product VIIRS_SNPP_SP (unverified coverage).")

        w, s, e, n = bbox_from_radius(lat, lon, radius)
        path = f"{FIRMS_URL}/{{key}}/{product}/{w:.4f},{s:.4f},{e:.4f},{n:.4f}/{days}" + (f"/{start}" if start else "")
        text = http.get_text(path.format(key=key))
        ref = path.format(key="***")

        reader = csv.DictReader(io.StringIO(text.strip()))
        if not reader.fieldnames or "latitude" not in reader.fieldnames:
            snippet = http.redact(text[:150]).replace("\n", " ")
            etype = ErrorType.AUTH if "map_key" in text.lower() or "invalid" in text.lower() else ErrorType.BAD_RESPONSE
            raise AdapterError(etype, f"FIRMS did not return CSV: {snippet}")

        hotspots: List[Dict[str, Any]] = []
        skipped = 0
        for row in reader:
            f_lat, f_lon = _f(row.get("latitude")), _f(row.get("longitude"))
            if f_lat is None or f_lon is None:
                skipped += 1
                continue
            dist = haversine_km(f_lat, f_lon, lat, lon)
            if dist > radius:
                continue
            hhmm = str(row.get("acq_time") or "0000").zfill(4)
            detected = to_utc_iso(f"{row.get('acq_date')}T{hhmm[:2]}:{hhmm[2:]}:00") if row.get("acq_date") else None
            conf = str(row.get("confidence") or "").strip().lower()
            hotspots.append(FireHotspot(
                lat=f_lat, lon=f_lon, distance_km=round(dist, 2),
                bearing_fire_to_location_deg=round(bearing_deg(f_lat, f_lon, lat, lon), 2),
                detected_at=detected, frp_mw=_f(row.get("frp")), brightness_k=_f(row.get("bright_ti4")),
                confidence=CONFIDENCE.get(conf, conf or None), daynight=row.get("daynight"),
                satellite=row.get("satellite"),
            ).model_dump())
        if skipped:
            warnings.append(f"Skipped {skipped} malformed FIRMS rows.")
        hotspots.sort(key=lambda h: h["distance_km"])
        return self._package(hotspots, radius, days, product, int(params["top_k"]), ref, warnings)

    @staticmethod
    def _package(hotspots, radius, days, product, top_k, ref, warnings) -> Fetched:
        times = sorted(h["detected_at"] for h in hotspots if h["detected_at"])
        frps = [h["frp_mw"] for h in hotspots if h["frp_mw"] is not None]
        m = FireMeasurements(
            hotspot_count=len(hotspots), radius_km=radius, window_days=days, product=product,
            nearest_km=hotspots[0]["distance_km"] if hotspots else None,
            total_frp_mw=round(sum(frps), 1), max_frp_mw=max(frps) if frps else None,
            high_confidence_count=sum(1 for h in hotspots if h["confidence"] == "high"),
            earliest_detection=times[0] if times else None, latest_detection=times[-1] if times else None,
            closest_fires=hotspots[:top_k],
        ).model_dump()
        return Fetched(measurements=m, observations=hotspots[:MAX_OBSERVATIONS],
                       units={"distance_km": "km", "frp_mw": "MW", "brightness_k": "K", "bearing": "degrees (compass)"},
                       timestamp=times[-1] if times else None, raw_reference=ref, warnings=warnings)

    def _fetch_mock(self, lat, lon, params) -> Fetched:
        hs = [FireHotspot(**h).model_dump() for h in ms.fires(lat, lon, ms.now_hour())]
        return self._package(hs, float(params["radius_km"]), int(params["days"]), "MOCK", int(params["top_k"]),
                             "mock://nasa_firms", [])
