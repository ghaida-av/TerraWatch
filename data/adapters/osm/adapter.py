"""GeoAdapter (OpenStreetMap-derived) via Geoapify Places, + GeocodeAdapter.

Geoapify Places is built on OpenStreetMap data, so this covers the plan's "OpenStreetMap" source
while reusing the Geoapify key the team already has. Every feature carries lat/lon and distance so
Person 3 can compute infrastructure proximity.

CATEGORY NAMES: presets below follow Geoapify's dotted category scheme but were NOT verified against
a live key in this build. If a name is wrong Geoapify replies 400 and the error surfaces as
`bad_request` with the message — fix it in PRESETS.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from data.adapters.base import BaseAdapter, Fetched
from data.config import get_secret
from data.core import http, mock_scenario as ms
from data.core.errors import AdapterError, ErrorType
from data.core.geo import haversine_km
from data.schemas.models import GeocodeMeasurements, GeoMeasurements, Place

PLACES_URL = "https://api.geoapify.com/v2/places"
GEOCODE_URL = "https://api.geoapify.com/v1/geocode/search"
OM_GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"

PRESETS = {
    "population": "populated_place",
    "critical_infrastructure": "healthcare.hospital,service.fire_station,airport",
    "industrial": "building.industrial",
}


class GeoAdapter(BaseAdapter):
    source = "geoapify"
    kind = "geo"
    ttl_seconds = 24 * 3600
    max_stale_seconds = 7 * 24 * 3600
    defaults = {"radius_m": 5000, "categories": "populated_place", "limit": 50, "top_k": 10}

    def _fetch_live(self, lat, lon, params) -> Fetched:
        key = get_secret("GEOAPIFY_API_KEY")
        if not key:
            raise AdapterError(ErrorType.MISSING_CREDENTIALS, "GEOAPIFY_API_KEY is not set")
        radius = max(100, min(int(params["radius_m"]), 50000))
        cats = PRESETS.get(str(params["categories"]), str(params["categories"]))
        q = {"categories": cats, "filter": f"circle:{lon},{lat},{radius}", "bias": f"proximity:{lon},{lat}",
             "limit": max(1, min(int(params["limit"]), 100)), "apiKey": key}
        data = http.get_json(PLACES_URL, params=q)
        places: List[Dict[str, Any]] = []
        for f in data.get("features") or []:
            p = f.get("properties") or {}
            p_lat, p_lon = p.get("lat"), p.get("lon")
            if p_lat is None or p_lon is None:
                continue
            places.append(Place(name=p.get("name"), categories=p.get("categories") or [], lat=p_lat, lon=p_lon,
                                distance_km=round(haversine_km(lat, lon, p_lat, p_lon), 3)).model_dump())
        return self._package(places, radius, cats, int(params["top_k"]),
                             http.reference_url(PLACES_URL, {**q, "apiKey": "***"}))

    @staticmethod
    def _package(places, radius, cats, top_k, ref) -> Fetched:
        places = sorted(places, key=lambda p: p["distance_km"])
        by_cat: Dict[str, int] = {}
        for p in places:
            top = (p["categories"] or ["uncategorized"])[-1]  # most specific category
            by_cat[top] = by_cat.get(top, 0) + 1
        m = GeoMeasurements(feature_count=len(places), radius_m=radius, categories_requested=cats,
                            by_category=by_cat, nearest=places[:top_k]).model_dump()
        return Fetched(measurements=m, observations=places, units={"distance_km": "km"}, raw_reference=ref)

    def _fetch_mock(self, lat, lon, params) -> Fetched:
        pl = [Place(**p).model_dump() for p in ms.places(lat, lon)]
        return self._package(pl, int(params["radius_m"]), str(params["categories"]), int(params["top_k"]), "mock://geoapify")


class GeocodeAdapter(BaseAdapter):
    """City name -> lat/lon/timezone. Geoapify first, Open-Meteo geocoding (no key) as fallback."""

    source = "geoapify_geocode"
    kind = "geocode"
    ttl_seconds = 7 * 24 * 3600
    max_stale_seconds = 30 * 24 * 3600
    defaults = {"city": "", "country_or_continent": ""}

    def fetch(self, city: str = "", country_or_continent: str = "", **_: Any):  # type: ignore[override]
        params = self._normalize({"city": (city or "").strip(), "country_or_continent": (country_or_continent or "").strip()})
        if not params["city"]:
            err = AdapterError(ErrorType.BAD_REQUEST, "city is required")
            from data.core.timeutil import utc_now
            return self._error_evidence(err, None, None, params, utc_now())
        match_key = f"{params['city']}|{params['country_or_continent']}".lower()
        return self._run(None, None, params, match_key=match_key)

    def _fetch_live(self, lat, lon, params) -> Fetched:
        city, hint = params["city"], params["country_or_continent"]
        key = get_secret("GEOAPIFY_API_KEY")
        first: Optional[AdapterError] = None
        if key:
            try:
                return self._geoapify(city, hint, key)
            except AdapterError as e:
                first = e
        try:
            fb = self._open_meteo(city, hint)
        except AdapterError as e2:
            raise first or e2
        fb.warnings.append(f"Geoapify geocoding unavailable ({first.type.value if first else 'no key'}); used Open-Meteo geocoding.")
        return fb

    def _geoapify(self, city, hint, key) -> Fetched:
        q = {"text": f"{city}, {hint}".strip(", "), "limit": 1, "format": "json", "apiKey": key}
        data = http.get_json(GEOCODE_URL, params=q)
        results = data.get("results") or [f.get("properties") or {} for f in (data.get("features") or [])]
        if not results or results[0].get("lat") is None:
            raise AdapterError(ErrorType.NOT_FOUND, f"No geocoding result for {city!r}")
        r = results[0]
        tz = (r.get("timezone") or {}).get("name") or "UTC"
        m = GeocodeMeasurements(matched_name=r.get("formatted"), tz_name=tz, country=r.get("country"),
                                country_code=r.get("country_code")).model_dump()
        return Fetched(measurements=m, location={"lat": r["lat"], "lon": r["lon"]},
                       raw_reference=http.reference_url(GEOCODE_URL, {**q, "apiKey": "***"}), source="geoapify_geocode")

    def _open_meteo(self, city, hint) -> Fetched:
        q = {"name": city, "count": 10, "language": "en", "format": "json"}
        results = (http.get_json(OM_GEOCODE_URL, params=q).get("results") or [])
        if not results:
            raise AdapterError(ErrorType.NOT_FOUND, f"No geocoding result for {city!r}")
        h = hint.lower()
        pick = next((r for r in results if h and h in " ".join(str(r.get(k, "")) for k in ("country", "country_code", "admin1")).lower()),
                    results[0])
        m = GeocodeMeasurements(matched_name=", ".join(str(pick[k]) for k in ("name", "admin1", "country") if pick.get(k)),
                                tz_name=pick.get("timezone") or "UTC", country=pick.get("country"),
                                country_code=pick.get("country_code")).model_dump()
        return Fetched(measurements=m, location={"lat": pick["latitude"], "lon": pick["longitude"]},
                       raw_reference=http.reference_url(OM_GEOCODE_URL, q), source="open-meteo-geocoding")

    def _fetch_mock(self, lat, lon, params) -> Fetched:
        known = {"cairo": (30.0444, 31.2357, "Africa/Cairo", "Egypt", "EG"),
                 "sharjah": (25.3463, 55.4209, "Asia/Dubai", "United Arab Emirates", "AE"),
                 "tokyo": (35.6762, 139.6503, "Asia/Tokyo", "Japan", "JP"),
                 "los angeles": (34.0522, -118.2437, "America/Los_Angeles", "United States", "US")}
        la, lo, tz, country, cc = known.get(params["city"].lower(), (30.0444, 31.2357, "Africa/Cairo", "Egypt", "EG"))
        m = GeocodeMeasurements(matched_name=f"{params['city']} (mock)", tz_name=tz, country=country, country_code=cc).model_dump()
        return Fetched(measurements=m, location={"lat": la, "lon": lo}, raw_reference="mock://geocode",
                       source="geoapify_geocode")
