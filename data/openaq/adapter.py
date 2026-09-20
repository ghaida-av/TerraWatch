"""AirQualityAdapter — OpenAQ v3 (ground-station measurements), with an explicit modeled fallback.

Fixes vs the notebook prototype:
  * OpenAQ v3 `/locations/{id}/latest` returns only `sensorsId` + `value` (no pollutant name).
    Pollutants are joined via the `sensors` list on the *location* object.
  * Picks the nearest station that actually reports PM2.5 and has fresh data (limit=1 could return a
    dead or PM-less station).
  * "No station nearby" is `status="no_data"` (or falls back to CAMS model output from Open-Meteo,
    labelled `is_modeled=True`) — never silently treated as clean air.
  * Optional hourly PM2.5 history so Person 3's `air_quality_anomaly` has a baseline.
"""
from __future__ import annotations

import math
from datetime import timedelta
from typing import Any, Dict, List, Optional

from data.adapters.base import BaseAdapter, Fetched
from data.config import get_secret
from data.core import http, mock_scenario as ms
from data.core.errors import AdapterError, ErrorType, NoCoverage
from data.core.geo import haversine_km
from data.core.timeutil import parse_utc, to_utc_iso, utc_now
from data.schemas.models import AirQualityMeasurements, AirQualityPoint, AirQualityStation

OPENAQ = "https://api.openaq.org/v3"
OPENMETEO_AQ = "https://air-quality-api.open-meteo.com/v1/air-quality"
POLLUTANTS = ("pm25", "pm10", "no2", "o3", "co", "so2")
OM_MAP = {"pm2_5": "pm25", "pm10": "pm10", "nitrogen_dioxide": "no2", "ozone": "o3",
          "carbon_monoxide": "co", "sulphur_dioxide": "so2"}


class AirQualityAdapter(BaseAdapter):
    source = "openaq"
    kind = "air_quality"
    ttl_seconds = 900
    defaults = {"radius_m": 25000, "max_age_hours": 48, "history_hours": 24, "allow_model_fallback": True}

    # ------------------------------------------------------------------ live
    def _fetch_live(self, lat, lon, params) -> Fetched:
        reason: str
        try:
            return self._openaq(lat, lon, params)
        except NoCoverage as e:
            reason = str(e)
            if not params["allow_model_fallback"]:
                return Fetched(measurements=AirQualityMeasurements().model_dump(), status="no_data",
                               warnings=[f"{reason} This means no monitoring coverage, NOT clean air."])
            openaq_err: Optional[AdapterError] = None
        except AdapterError as e:
            if not params["allow_model_fallback"]:
                raise
            reason, openaq_err = f"OpenAQ unavailable ({e.type.value}: {e.message})", e

        try:
            fb = self._open_meteo(lat, lon, params)
        except AdapterError as e2:
            if openaq_err is not None:
                raise AdapterError(openaq_err.type, f"OpenAQ: {openaq_err.message} | Open-Meteo AQ fallback: {e2.message}",
                                   http_status=openaq_err.http_status, retryable=openaq_err.retryable)
            return Fetched(measurements=AirQualityMeasurements().model_dump(), status="no_data",
                           warnings=[f"{reason} Model fallback also failed: {e2.message}. "
                                     "This means no coverage, NOT clean air."])
        fb.warnings.insert(0, f"{reason} Using modeled (CAMS) estimates from Open-Meteo instead of ground measurements.")
        return fb

    def _openaq(self, lat, lon, params) -> Fetched:
        key = get_secret("OPENAQ_API_KEY")
        if not key:
            raise AdapterError(ErrorType.MISSING_CREDENTIALS, "OPENAQ_API_KEY is not set")
        headers = {"X-API-Key": key}
        radius = max(1000, min(int(params["radius_m"]), 25000))  # OpenAQ caps radius at 25 km
        max_age = float(params["max_age_hours"])
        now = utc_now()

        q = {"coordinates": f"{lat},{lon}", "radius": radius, "limit": 20}
        locs = http.get_json(f"{OPENAQ}/locations", params=q, headers=headers)
        station = self._pick_station(locs.get("results") or [], lat, lon, now, max_age)
        if station is None:
            raise NoCoverage(f"No OpenAQ station with fresh data within {radius / 1000:.0f} km.")

        latest = http.get_json(f"{OPENAQ}/locations/{station['id']}/latest", headers=headers)
        readings: Dict[str, Dict[str, Any]] = {}
        warnings: List[str] = []
        for m in latest.get("results") or []:
            p = station["sensor_params"].get(m.get("sensorsId"))
            name = ((p or {}).get("name") or "").lower()
            if name not in POLLUTANTS:
                continue
            value = m.get("value")
            if value is None or value < 0:
                warnings.append(f"Ignored invalid {name} reading ({value}).")
                continue
            when = to_utc_iso((m.get("datetime") or {}).get("utc"))
            if when is None or (now - parse_utc(when)).total_seconds() > max_age * 3600:
                continue
            if name not in readings or when > readings[name]["time"]:
                readings[name] = {"value": float(value), "time": when, "unit": p.get("units"), "sensor": m.get("sensorsId")}
        if not readings:
            raise NoCoverage(f"OpenAQ station '{station['name']}' has no readings newer than {max_age:.0f} h.")

        observations: List[Dict[str, Any]] = []
        pm25 = readings.get("pm25")
        if pm25 and int(params["history_hours"]) > 0:
            try:
                observations = self._history(headers, pm25["sensor"], pm25["unit"], now, int(params["history_hours"]))
            except AdapterError as e:
                warnings.append(f"PM2.5 history unavailable: {e.message}")

        measurements = AirQualityMeasurements(
            **{n: r["value"] for n, r in readings.items()},
            observed_at={n: r["time"] for n, r in readings.items()},
            station=AirQualityStation(id=station["id"], name=station["name"], lat=station["lat"], lon=station["lon"],
                                      distance_km=round(station["distance_km"], 2), last_updated=station["last"],
                                      provider=station["provider"]),
        ).model_dump()
        return Fetched(
            measurements=measurements, observations=observations,
            units={n: r["unit"] for n, r in readings.items() if r["unit"]},
            timestamp=max(r["time"] for r in readings.values()),
            raw_reference=http.reference_url(f"{OPENAQ}/locations/{station['id']}/latest"),
            warnings=warnings, source="openaq",
        )

    @staticmethod
    def _pick_station(results, lat, lon, now, max_age_h) -> Optional[Dict[str, Any]]:
        ranked = []
        for r in results:
            c = r.get("coordinates") or {}
            if c.get("latitude") is None or c.get("longitude") is None:
                continue
            last_raw = r.get("datetimeLast")
            last = to_utc_iso(last_raw.get("utc") if isinstance(last_raw, dict) else last_raw)
            if last is None or (now - parse_utc(last)).total_seconds() > max_age_h * 3600:
                continue  # dead / stale station
            sensor_params = {s["id"]: (s.get("parameter") or {}) for s in (r.get("sensors") or []) if "id" in s}
            has_pm25 = any((p.get("name") or "").lower() == "pm25" for p in sensor_params.values())
            dist = haversine_km(lat, lon, c["latitude"], c["longitude"])
            prov = r.get("provider")
            ranked.append((0 if has_pm25 else 1, dist, {
                "id": r["id"], "name": r.get("name"), "lat": c["latitude"], "lon": c["longitude"],
                "distance_km": dist, "last": last, "sensor_params": sensor_params,
                "provider": prov.get("name") if isinstance(prov, dict) else prov,
            }))
        ranked.sort(key=lambda t: (t[0], t[1]))
        return ranked[0][2] if ranked else None

    @staticmethod
    def _history(headers, sensor_id, unit, now, hours) -> List[Dict[str, Any]]:
        q = {"datetime_from": to_utc_iso(now - timedelta(hours=hours)), "datetime_to": to_utc_iso(now),
             "limit": min(hours + 1, 1000)}
        data = http.get_json(f"{OPENAQ}/sensors/{sensor_id}/hours", params=q, headers=headers)
        rows = []
        for r in data.get("results") or []:
            period = (r.get("period") or {}).get("datetimeFrom") or {}
            t, v = to_utc_iso(period.get("utc")), r.get("value")
            if t and v is not None and v >= 0:
                rows.append(AirQualityPoint(parameter="pm25", time=t, value=float(v), unit=unit).model_dump())
        rows.sort(key=lambda x: x["time"])
        return rows

    def _open_meteo(self, lat, lon, params) -> Fetched:
        hist = int(params["history_hours"])
        q: Dict[str, Any] = {"latitude": lat, "longitude": lon, "timezone": "UTC",
                             "current": ",".join(OM_MAP), "forecast_days": 1}
        if hist > 0:
            q.update({"hourly": "pm2_5", "past_days": max(1, min(math.ceil(hist / 24), 7))})
        data = http.get_json(OPENMETEO_AQ, params=q)
        cur = data.get("current") or {}
        cur_units = data.get("current_units") or {}
        vals = {OM_MAP[k]: cur[k] for k in OM_MAP if cur.get(k) is not None}
        if not vals:
            raise AdapterError(ErrorType.BAD_RESPONSE, "Open-Meteo air-quality response had no current values")
        when = to_utc_iso(cur.get("time"))
        obs: List[Dict[str, Any]] = []
        h = data.get("hourly") or {}
        if hist > 0 and h.get("time"):
            lo = utc_now() - timedelta(hours=hist)
            for t, v in zip(h["time"], h.get("pm2_5") or []):
                ts = to_utc_iso(t)
                if v is not None and parse_utc(ts) >= lo and parse_utc(ts) <= utc_now():
                    obs.append(AirQualityPoint(parameter="pm25", time=ts, value=float(v),
                                               unit=(data.get("hourly_units") or {}).get("pm2_5", "μg/m³")).model_dump())
        measurements = AirQualityMeasurements(**vals, observed_at={n: when for n in vals}).model_dump()
        return Fetched(
            measurements=measurements, observations=obs,
            units={OM_MAP[k]: cur_units.get(k, "μg/m³") for k in OM_MAP if OM_MAP[k] in vals},
            timestamp=when, raw_reference=http.reference_url(OPENMETEO_AQ, q),
            source="open-meteo-air-quality", is_modeled=True,
        )

    # ------------------------------------------------------------------ mock
    def _fetch_mock(self, lat, lon, params) -> Fetched:
        now = ms.now_hour()
        back = max(1, min(int(params["history_hours"]) or 24, 48))
        series = ms.pm25_hours(now, back)
        obs = [AirQualityPoint(parameter="pm25", time=ms.iso(now + timedelta(hours=i - back)), value=v,
                               unit="µg/m³").model_dump() for i, v in enumerate(series)]
        station = AirQualityStation(id=999001, name="Mock Downtown Station", lat=round(lat + 0.02, 4),
                                    lon=round(lon + 0.02, 4),
                                    distance_km=round(haversine_km(lat, lon, lat + 0.02, lon + 0.02), 2),
                                    last_updated=ms.iso(now), provider="mock")
        m = AirQualityMeasurements(pm25=series[-1], pm10=series[-1] * 2.1, no2=41.0, o3=58.0, co=620.0, so2=9.0,
                                   observed_at={p: ms.iso(now) for p in POLLUTANTS}, station=station).model_dump()
        return Fetched(measurements=m, observations=obs, units={p: "µg/m³" for p in POLLUTANTS},
                       timestamp=ms.iso(now), raw_reference="mock://openaq", source="openaq")
