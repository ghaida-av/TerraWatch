"""EarthquakeAdapter — USGS FDSN event service (free, no key).

Returns coordinates, depth and distance per event (the notebook dropped them, which made
`earthquake_proximity` impossible). Zero events is a valid `ok` result.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List

from data.adapters.base import BaseAdapter, Fetched
from data.core import http, mock_scenario as ms
from data.core.errors import AdapterError, ErrorType
from data.core.geo import haversine_km
from data.core.timeutil import to_utc_iso, utc_now
from data.schemas.models import EarthquakeMeasurements, QuakeEvent

USGS_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"
MAX_OBSERVATIONS = 200


class EarthquakeAdapter(BaseAdapter):
    source = "usgs"
    kind = "earthquake"
    ttl_seconds = 3600
    defaults = {"radius_km": 300.0, "days": 30, "min_mag": 2.5, "top_k": 5, "start_date": None, "end_date": None}

    def _fetch_live(self, lat, lon, params) -> Fetched:
        radius = max(1.0, min(float(params["radius_km"]), 2000.0))
        days, min_mag = max(1, int(params["days"])), float(params["min_mag"])
        if params["start_date"]:
            try:
                d0 = date.fromisoformat(str(params["start_date"]))
                d1 = date.fromisoformat(str(params["end_date"] or params["start_date"]))
            except ValueError:
                raise AdapterError(ErrorType.BAD_REQUEST, "start_date/end_date must be YYYY-MM-DD")
            start = datetime(d0.year, d0.month, d0.day, tzinfo=timezone.utc)
            end = datetime(d1.year, d1.month, d1.day, 23, 59, 59, tzinfo=timezone.utc)
            days = max(1, (d1 - d0).days + 1)
        else:
            end = utc_now()
            start = end - timedelta(days=days)
        q = {"format": "geojson", "latitude": lat, "longitude": lon, "maxradiuskm": radius,
             "starttime": start.strftime("%Y-%m-%dT%H:%M:%S"), "endtime": end.strftime("%Y-%m-%dT%H:%M:%S"),
             "minmagnitude": min_mag, "orderby": "time", "limit": MAX_OBSERVATIONS}
        data = http.get_json(USGS_URL, params=q)
        events = []
        for f in data.get("features") or []:
            try:
                p, (q_lon, q_lat, *rest) = f["properties"], f["geometry"]["coordinates"]
                events.append(QuakeEvent(
                    id=str(f.get("id")), magnitude=p.get("mag"), place=p.get("place"), time=to_utc_iso(p.get("time")),
                    lat=q_lat, lon=q_lon, depth_km=rest[0] if rest else None,
                    distance_km=round(haversine_km(q_lat, q_lon, lat, lon), 2),
                    url=p.get("url"), alert=p.get("alert"), tsunami=p.get("tsunami"),
                ).model_dump())
            except (KeyError, TypeError, ValueError):
                continue
        return self._package(events, radius, days, min_mag, int(params["top_k"]), http.reference_url(USGS_URL, q))

    @staticmethod
    def _package(events: List[Dict[str, Any]], radius, days, min_mag, top_k, ref) -> Fetched:
        mags = [e["magnitude"] for e in events if e["magnitude"] is not None]
        m = EarthquakeMeasurements(
            event_count=len(events), radius_km=radius, window_days=days, min_magnitude=min_mag,
            max_magnitude=max(mags) if mags else None,
            nearest_km=min((e["distance_km"] for e in events), default=None),
            strongest=sorted(events, key=lambda e: -(e["magnitude"] or 0))[:top_k],
            closest=sorted(events, key=lambda e: e["distance_km"])[:top_k],
        ).model_dump()
        times = sorted(e["time"] for e in events if e["time"])
        return Fetched(measurements=m, observations=events, units={"magnitude": "moment/local (see magnitude type)",
                       "depth_km": "km", "distance_km": "km"}, timestamp=times[-1] if times else None,
                       raw_reference=ref)

    def _fetch_mock(self, lat, lon, params) -> Fetched:
        ev = [QuakeEvent(**e).model_dump() for e in ms.quakes(lat, lon, ms.now_hour())]
        return self._package(ev, float(params["radius_km"]), int(params["days"]), float(params["min_mag"]),
                             int(params["top_k"]), "mock://usgs")
