"""Regression: weather reports where the wind blows FROM; smoke travels the opposite way."""
from evals import builders as b
from geo_analysis.pipeline import analyze_evidence

T = b.TARGET


def _analyze(wind_from_deg, fire_bearing_to_target=225.0):
    evs = [b.weather(20, wind_from_deg), b.fire(30, fire_bearing_to_target), b.air_quality(10, [10, 10])]
    return analyze_evidence(evs, target_name=T["name"], target_lat=T["lat"], target_lon=T["lon"])


def test_wind_from_the_fire_side_is_downwind():
    a = _analyze(wind_from_deg=45)          # wind from NE, fire is NE of town -> smoke reaches town
    assert a["signals"]["is_downwind_of_fire"] is True
    assert a["components"]["wind_alignment"] > 0.95


def test_wind_from_the_opposite_side_is_not_downwind():
    a = _analyze(wind_from_deg=225)         # wind from SW blows the smoke away from town
    assert a["signals"]["is_downwind_of_fire"] is False
    assert a["components"]["wind_alignment"] < 0.05


def test_crosswind_is_not_downwind():
    assert _analyze(wind_from_deg=135)["signals"]["is_downwind_of_fire"] is False


def test_project_mock_incident_is_downwind(monkeypatch):
    """The mock story says 'smoke is carried toward the location'; the analysis must agree."""
    monkeypatch.setenv("TERRAWATCH_MODE", "mock")
    from agent.investigator import investigate
    assert investigate("Cairo").signals["is_downwind_of_fire"] is True
