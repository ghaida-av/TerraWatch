"""WeatherAdapter — Open-Meteo (free, no API key).

Returns current conditions + an hourly window (the hourly rows are what temporal correlation
needs: "did the wind shift before PM2.5 rose?"). Everything is requested in UTC with explicit
units so the normalized schema never depends on API defaults.
"""
from __future__ import annotations

import math
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from data.adapters.base import BaseAdapter, Fetched
from data.core import http, mock_scenario as ms
from data.core.errors import AdapterError, ErrorType
from data.core.timeutil import parse_utc, to_utc_iso, utc_now
from data.schemas.models import WeatherMeasurements, WeatherPoint

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
VARS = "temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m,wind_gusts_10m,precipitation"
FIELD_MAP = {
    "temperature_2m": "temperature_c",
    "relative_humidity_2m": "relative_humidity_pct",
    "wind_speed_10m": "wind_speed_kmh",
    "wind_direction_10m": "wind_direction_deg",
    "wind_gusts_10m": "wind_gusts_kmh",
    "precipitation": "precipitation_mm",
}
UNITS = {
    "temperature_c": "°C",
    "relative_humidity_pct": "%",
    "wind_speed_kmh": "km/h",
    "wind_direction_deg": "degrees; meteorological = direction the wind blows FROM",
    "wind_gusts_kmh": "km/h",
    "precipitation_mm": "mm",
}
ARCHIVE_AFTER_DAYS = 60  # older than this -> ERA5 archive endpoint


def _point(time_value: str, values: Dict[str, Any]) -> Dict[str, Any]:
    fields = {FIELD_MAP[k]: values.get(k) for k in FIELD_MAP}
    return WeatherPoint(time=to_utc_iso(time_value), **fields).model_dump()


def _hourly_rows(hourly: Optional[Dict[str, List[Any]]]) -> List[Dict[str, Any]]:
    if not hourly or "time" not in hourly:
        return []
    rows = []
    for i, t in enumerate(hourly["time"]):
        rows.append(_point(t, {k: (hourly.get(k) or [None] * len(hourly["time"]))[i] for k in FIELD_MAP}))
    return rows


class WeatherAdapter(BaseAdapter):
    source = "open-meteo"
    kind = "weather"
    ttl_seconds = 1800
    defaults = {"hours_back": 24, "hours_ahead": 0, "start_date": None, "end_date": None}

    def _fetch_live(self, lat, lon, params) -> Fetched:
        start, end = params["start_date"], params["end_date"]
        warnings: List[str] = []
        base = {"latitude": lat, "longitude": lon, "hourly": VARS, "timezone": "UTC", "timeformat": "iso8601",
                "temperature_unit": "celsius", "wind_speed_unit": "kmh", "precipitation_unit": "mm"}

        if start:
            try:
                d0 = date.fromisoformat(str(start))
                d1 = date.fromisoformat(str(end or start))
            except ValueError:
                raise AdapterError(ErrorType.BAD_REQUEST, f"start_date/end_date must be YYYY-MM-DD, got {start!r}/{end!r}")
            today = utc_now().date()
            url = ARCHIVE_URL if (today - d0).days > ARCHIVE_AFTER_DAYS else FORECAST_URL
            if url == ARCHIVE_URL and d1 > today - timedelta(days=6):
                warnings.append("Archive data lags ~5 days; end_date clipped.")
                d1 = today - timedelta(days=6)
            query = {**base, "start_date": d0.isoformat(), "end_date": d1.isoformat()}
            current = None
        else:
            back = max(1, min(int(params["hours_back"]), 24 * 7))
            ahead = max(0, min(int(params["hours_ahead"]), 24 * 7))
            url = FORECAST_URL
            query = {**base, "current": VARS, "past_days": math.ceil(back / 24), "forecast_days": 1 + math.ceil(ahead / 24)}

        data = http.get_json(url, params=query)
        rows = _hourly_rows(data.get("hourly"))
        if not start:
            now = utc_now().replace(minute=0, second=0, microsecond=0)  # snap to the hour: hours_back=12 -> 13 rows
            lo, hi = now - timedelta(hours=back), now + timedelta(hours=ahead)
            rows = [r for r in rows if lo <= parse_utc(r["time"]) <= hi]
            cur = data.get("current")
            current = _point(cur["time"], cur) if cur and cur.get("time") else None
        if current is None and not rows:
            raise AdapterError(ErrorType.BAD_RESPONSE, "Open-Meteo returned neither current nor hourly data")

        measurements = WeatherMeasurements(
            current=current,
            window_start=rows[0]["time"] if rows else None,
            window_end=rows[-1]["time"] if rows else None,
            hourly_count=len(rows),
        ).model_dump()
        return Fetched(
            measurements=measurements, observations=rows, units=UNITS,
            timestamp=(current or rows[-1])["time"], raw_reference=http.reference_url(url, query), warnings=warnings,
        )

    def _fetch_mock(self, lat, lon, params) -> Fetched:
        now = ms.now_hour()
        back = max(1, min(int(params["hours_back"]), 24))
        rows = [WeatherPoint(**r).model_dump() for r in ms.weather_hours(now, back)]
        measurements = WeatherMeasurements(current=rows[-1], window_start=rows[0]["time"],
                                           window_end=rows[-1]["time"], hourly_count=len(rows)).model_dump()
        return Fetched(measurements=measurements, observations=rows, units=UNITS, timestamp=rows[-1]["time"],
                       raw_reference="mock://open-meteo")
