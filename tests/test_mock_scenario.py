
from datetime import datetime, timezone

from data.core import mock_scenario as ms
from data.core.geo import bearing_deg, haversine_km

NOW = datetime(2026, 9, 19, 12, tzinfo=timezone.utc)


def angdiff(a, b):
    return abs((a - b + 180) % 360 - 180)


def test_fires_are_upwind_of_the_city():
    lat, lon = 30.0444, 31.2357
    wind_blows_toward = (ms.WIND_FROM_AFTER_SHIFT + 180) % 360
    for f in ms.fires(lat, lon, NOW):
        assert angdiff(f["bearing_fire_to_location_deg"], wind_blows_toward) < 10
        assert 50 < f["distance_km"] < 100


def test_timeline_fire_then_wind_then_pm25():
    weather, pm = ms.weather_hours(NOW), ms.pm25_hours(NOW)
    first_shift = next(i for i, r in enumerate(weather) if r["wind_direction_deg"] == ms.WIND_FROM_AFTER_SHIFT)
    first_rise = next(i for i in range(1, len(pm)) if pm[i] > pm[i - 1])
    earliest_fire = min(f["detected_at"] for f in ms.fires(30.0, 31.0, NOW))
    hours = lambda i: 24 - i  # index -> hours ago
    assert hours(first_shift) == ms.SHIFT_HOURS_AGO and hours(first_rise) < hours(first_shift)
    assert earliest_fire < weather[first_shift]["time"] < ms.iso(NOW)


def test_quake_and_place_distances_are_consistent():
    for q in ms.quakes(35.68, 139.65, NOW):
        assert q["distance_km"] > 100
    for p in ms.places(35.68, 139.65):
        assert haversine_km(35.68, 139.65, p["lat"], p["lon"]) - p["distance_km"] < 0.01
