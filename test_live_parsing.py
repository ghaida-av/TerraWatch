"""Each adapter's live path, fed with responses shaped like the real APIs' documented formats.

NOTE: these prove our parsing/normalization logic. They do not prove the upstream APIs still
return these shapes — run scripts/live_smoke_test.py with real keys for that.
"""
from datetime import timedelta

import pytest

from data.adapters import (AirQualityAdapter, EarthquakeAdapter, FireAdapter, GeoAdapter, GeocodeAdapter,
                           WeatherAdapter)
from data.core import http
from data.core.errors import AdapterError, ErrorType
from data.core.timeutil import utc_now

CAIRO = (30.0444, 31.2357)


def z(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def om(dt):  # Open-Meteo style naive UTC
    return dt.strftime("%Y-%m-%dT%H:%M")


# ------------------------------------------------------------------ weather
def test_weather_normalizes_units_and_filters_window(monkeypatch):
    now = utc_now().replace(minute=0, second=0, microsecond=0)
    times = [om(now + timedelta(hours=h)) for h in range(-30, 6)]
    hourly = {"time": times, **{k: [float(i) for i in range(len(times))] for k in (
        "temperature_2m", "relative_humidity_2m", "wind_speed_10m", "wind_direction_10m", "wind_gusts_10m", "precipitation")}}
    resp = {"current": {"time": om(now), "temperature_2m": 31.5, "relative_humidity_2m": 40, "wind_speed_10m": 18.2,
                        "wind_direction_10m": 45, "wind_gusts_10m": 30.0, "precipitation": 0.0}, "hourly": hourly}
    seen = {}

    def fake(url, params=None, headers=None, timeout=None):
        seen.update(params)
        return resp

    monkeypatch.setattr(http, "get_json", fake)
    ev = WeatherAdapter().fetch(*CAIRO, hours_back=12)
    assert ev.status == "ok" and ev.data_mode == "live"
    assert seen["timezone"] == "UTC" and seen["wind_speed_unit"] == "kmh"
    cur = ev.measurements["current"]
    assert cur["wind_direction_deg"] == 45 and cur["wind_speed_kmh"] == 18.2 and cur["time"].endswith("Z")
    assert len(ev.observations) == 13  # exactly the last 12 h + current hour, forecast hours dropped
    assert "FROM" in ev.units["wind_direction_deg"]


def test_weather_empty_response_is_error_not_crash(monkeypatch):
    monkeypatch.setattr(http, "get_json", lambda *a, **k: {})
    ev = WeatherAdapter().fetch(*CAIRO)
    assert ev.status == "error" and ev.error.type == "bad_response"


# ------------------------------------------------------------------ air quality
def _station(id_, lat, lon, last, params, name=None):
    return {"id": id_, "name": name or f"Station {id_}", "coordinates": {"latitude": lat, "longitude": lon},
            "datetimeLast": {"utc": z(last), "local": z(last)}, "provider": {"name": "TestProv"},
            "sensors": [{"id": id_ * 10 + i, "name": p, "parameter": {"id": i, "name": p, "units": u, "displayName": p}}
                        for i, (p, u) in enumerate(params)]}


def test_openaq_joins_sensors_and_picks_best_station(monkeypatch):
    now = utc_now()
    stations = [
        _station(1, 30.05, 31.24, now - timedelta(days=30), [("pm25", "µg/m³")]),        # nearest but DEAD
        _station(2, 30.06, 31.25, now - timedelta(hours=1), [("no2", "µg/m³")]),         # fresh, no PM2.5
        _station(3, 30.10, 31.30, now - timedelta(hours=1), [("pm25", "µg/m³"), ("pm10", "µg/m³"), ("o3", "ppm")]),
    ]
    latest = {"results": [
        {"datetime": {"utc": z(now - timedelta(minutes=30))}, "value": 88.0, "sensorsId": 30, "locationsId": 3},
        {"datetime": {"utc": z(now - timedelta(minutes=30))}, "value": 140.0, "sensorsId": 31, "locationsId": 3},
        {"datetime": {"utc": z(now - timedelta(minutes=30))}, "value": -999.0, "sensorsId": 32, "locationsId": 3},
    ]}
    hours = {"results": [{"value": 50.0, "period": {"datetimeFrom": {"utc": z(now - timedelta(hours=2))}}},
                         {"value": 88.0, "period": {"datetimeFrom": {"utc": z(now - timedelta(hours=1))}}}]}
    calls = []

    def fake(url, params=None, headers=None, timeout=None):
        calls.append(url)
        assert headers["X-API-Key"]
        if url.endswith("/locations"):
            return {"results": stations}
        if url.endswith("/latest"):
            assert "/locations/3/" in url
            return latest
        if "/sensors/30/hours" in url:
            return hours
        raise AssertionError(url)

    monkeypatch.setattr(http, "get_json", fake)
    ev = AirQualityAdapter().fetch(*CAIRO)
    assert ev.source == "openaq" and ev.status == "ok" and not ev.is_modeled
    m = ev.measurements
    assert m["pm25"] == 88.0 and m["pm10"] == 140.0 and m["o3"] is None      # -999 rejected
    assert m["station"]["id"] == 3 and m["station"]["distance_km"] > 0
    assert ev.units["pm25"] == "µg/m³"
    assert [o["value"] for o in ev.observations] == [50.0, 88.0]             # history sorted, PM2.5 only
    assert any("Ignored invalid o3" in w for w in ev.warnings)


def test_openaq_no_station_falls_back_to_modeled_and_says_so(monkeypatch):
    now = utc_now().replace(minute=0, second=0, microsecond=0)

    def fake(url, params=None, headers=None, timeout=None):
        if "openaq" in url:
            return {"results": []}
        return {"current": {"time": om(now), "pm2_5": 21.0, "pm10": 33.0, "ozone": 70.0, "nitrogen_dioxide": 12.0,
                            "carbon_monoxide": 200.0, "sulphur_dioxide": 4.0},
                "current_units": {"pm2_5": "μg/m³"},
                "hourly": {"time": [om(now - timedelta(hours=1)), om(now)], "pm2_5": [19.0, 21.0]},
                "hourly_units": {"pm2_5": "μg/m³"}}

    monkeypatch.setattr(http, "get_json", fake)
    ev = AirQualityAdapter().fetch(*CAIRO)
    assert ev.source == "open-meteo-air-quality" and ev.is_modeled is True
    assert ev.measurements["pm25"] == 21.0 and ev.measurements["station"] is None
    assert "modeled" in ev.warnings[0].lower() and len(ev.observations) == 2


def test_openaq_no_station_without_fallback_is_no_data_not_clean_air(monkeypatch):
    monkeypatch.setattr(http, "get_json", lambda *a, **k: {"results": []})
    ev = AirQualityAdapter().fetch(*CAIRO, allow_model_fallback=False)
    assert ev.status == "no_data"
    assert "NOT clean air" in ev.warnings[0]
    assert ev.measurements["pm25"] is None


def test_openaq_missing_key_and_fallback_down_reports_first_cause(monkeypatch):
    monkeypatch.delenv("OPENAQ_API_KEY")

    def fake(url, params=None, headers=None, timeout=None):
        raise AdapterError(ErrorType.SERVER, "boom", http_status=503, retryable=True)

    monkeypatch.setattr(http, "get_json", fake)
    ev = AirQualityAdapter().fetch(*CAIRO)
    assert ev.status == "error" and ev.error.type == "missing_credentials"
    assert "Open-Meteo AQ fallback" in ev.error.message


# ------------------------------------------------------------------ fire
FIRMS_CSV = (
    "latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,satellite,instrument,confidence,version,bright_ti5,frp,daynight\n"
    "30.60,31.70,345.1,0.4,0.4,2026-09-19,534,N20,VIIRS,h,2.0NRT,300.1,22.5,D\n"
    "30.30,31.40,330.0,0.4,0.4,2026-09-19,1210,N20,VIIRS,n,2.0NRT,290.0,8.1,D\n"
    "35.00,35.00,330.0,0.4,0.4,2026-09-19,1210,N20,VIIRS,n,2.0NRT,290.0,8.1,D\n"       # ~900 km away
    "bad,row,,,,2026-09-19,1210,N20,VIIRS,l,2.0NRT,,,D\n"
)


def test_firms_parses_csv_filters_radius_and_hides_key(monkeypatch):
    monkeypatch.setattr(http, "get_text", lambda url, **k: FIRMS_CSV)
    ev = FireAdapter().fetch(*CAIRO, radius_km=150)
    m = ev.measurements
    assert m["hotspot_count"] == 2 and m["nearest_km"] < m["closest_fires"][1]["distance_km"]
    first = m["closest_fires"][0]
    assert first["confidence"] == "nominal" and first["detected_at"] == "2026-09-19T12:10:00Z"
    far = m["closest_fires"][1]
    assert far["detected_at"] == "2026-09-19T05:34:00Z" and far["confidence"] == "high"   # "534" zero-padded
    assert m["high_confidence_count"] == 1 and m["total_frp_mw"] == 30.6
    assert "firms-secret-key-456" not in ev.raw_reference and "***" in ev.raw_reference
    assert any("malformed" in w for w in ev.warnings)


def test_firms_zero_hotspots_is_ok_not_error(monkeypatch):
    header = FIRMS_CSV.splitlines()[0] + "\n"
    monkeypatch.setattr(http, "get_text", lambda url, **k: header)
    ev = FireAdapter().fetch(*CAIRO)
    assert ev.status == "ok" and ev.measurements["hotspot_count"] == 0 and ev.measurements["nearest_km"] is None


def test_firms_plaintext_error_reply_detected(monkeypatch):
    monkeypatch.setattr(http, "get_text", lambda url, **k: "Invalid MAP_KEY.")
    ev = FireAdapter().fetch(*CAIRO)
    assert ev.status == "error" and ev.error.type == "auth"


# ------------------------------------------------------------------ earthquake
def test_usgs_keeps_coordinates_depth_distance(monkeypatch):
    t = int((utc_now() - timedelta(days=1)).timestamp() * 1000)
    resp = {"features": [
        {"id": "us1", "properties": {"mag": 4.6, "place": "X", "time": t, "url": "https://u/1", "tsunami": 0},
         "geometry": {"coordinates": [31.9, 30.9, 12.5]}},
        {"id": "us2", "properties": {"mag": 2.7, "place": "Y", "time": t, "url": None},
         "geometry": {"coordinates": [31.3, 30.1, 5.0]}},
    ]}
    monkeypatch.setattr(http, "get_json", lambda *a, **k: resp)
    ev = EarthquakeAdapter().fetch(*CAIRO)
    m = ev.measurements
    assert m["event_count"] == 2 and m["max_magnitude"] == 4.6
    assert m["strongest"][0]["id"] == "us1" and m["closest"][0]["id"] == "us2"
    assert m["closest"][0]["depth_km"] == 5.0 and ev.observations[0]["time"].endswith("Z")


def test_usgs_zero_events_ok(monkeypatch):
    monkeypatch.setattr(http, "get_json", lambda *a, **k: {"features": []})
    ev = EarthquakeAdapter().fetch(*CAIRO)
    assert ev.status == "ok" and ev.measurements["event_count"] == 0 and ev.measurements["max_magnitude"] is None


# ------------------------------------------------------------------ geo + geocode
def test_geoapify_places_distance_and_key_hidden(monkeypatch):
    resp = {"features": [
        {"properties": {"name": "Far", "categories": ["healthcare", "healthcare.hospital"], "lat": 30.09, "lon": 31.30}},
        {"properties": {"name": "Near", "categories": ["service", "service.fire_station"], "lat": 30.05, "lon": 31.24}},
        {"properties": {"name": "NoCoords"}},
    ]}
    monkeypatch.setattr(http, "get_json", lambda *a, **k: resp)
    ev = GeoAdapter().fetch(*CAIRO, categories="critical_infrastructure")
    assert [p["name"] for p in ev.measurements["nearest"]] == ["Near", "Far"]
    assert ev.measurements["by_category"] == {"service.fire_station": 1, "healthcare.hospital": 1}
    assert "geoapify-secret-key-789" not in ev.raw_reference


def test_geocode_geoapify_and_open_meteo_fallback(monkeypatch):
    def ok(url, params=None, **k):
        return {"results": [{"lat": 30.04, "lon": 31.23, "formatted": "Cairo, Egypt", "country": "Egypt",
                             "country_code": "eg", "timezone": {"name": "Africa/Cairo"}}]}

    monkeypatch.setattr(http, "get_json", ok)
    ev = GeocodeAdapter().fetch("Cairo", "Egypt")
    assert ev.location.lat == 30.04 and ev.measurements["tz_name"] == "Africa/Cairo"

    def flaky(url, params=None, **k):
        if "geoapify" in url:
            raise AdapterError(ErrorType.RATE_LIMITED, "429", http_status=429, retryable=True)
        return {"results": [{"name": "Cairo", "latitude": 39.0, "longitude": -89.2, "timezone": "America/Chicago",
                             "country": "United States", "country_code": "US", "admin1": "Illinois"},
                            {"name": "Cairo", "latitude": 30.04, "longitude": 31.23, "timezone": "Africa/Cairo",
                             "country": "Egypt", "country_code": "EG", "admin1": "Cairo"}]}

    from data.core.cache import get_cache
    get_cache().clear()                                   # otherwise the first call's cached answer is (correctly) reused
    monkeypatch.setattr(http, "get_json", flaky)
    ev2 = GeocodeAdapter().fetch("Cairo", "Egypt", )
    assert ev2.status == "ok" and ev2.location.lat == 30.04           # country hint resolves the ambiguity
    assert ev2.source == "open-meteo-geocoding" and any("Geoapify" in w for w in ev2.warnings)


def test_geocode_requires_city():
    ev = GeocodeAdapter().fetch("")
    assert ev.status == "error" and ev.error.type == "bad_request"


@pytest.mark.parametrize("bad", [(91, 0), (0, 181), ("abc", 1), (None, 1)])
def test_invalid_coordinates_rejected(bad):
    ev = WeatherAdapter().fetch(*bad)
    assert ev.status == "error" and ev.error.type == "bad_request" and ev.location is None
