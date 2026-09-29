import os
import pytest

from data import collect_evidence, geocode
from geo_analysis.pipeline import analyze_evidence


def test_analyze_evidence_with_mock_data(monkeypatch):
    monkeypatch.setenv("TERRAWATCH_MODE", "mock")

    # Day-1 MVP sources
    evs = collect_evidence(30.0444, 31.2357, sources=["weather", "air_quality", "fire"])
    assert len(evs) == 3

    analysis = analyze_evidence(evs, target_name="Cairo")

    assert analysis["target"]["name"] == "Cairo"
    assert "risk_score" in analysis
    assert 0.0 <= analysis["risk_score"] <= 1.0
    assert analysis["risk_level"] in ("LOW", "MODERATE", "HIGH", "CRITICAL")
    assert "components" in analysis
    assert "signals" in analysis

    # Evidence graph validation
    graph = analysis["evidence_graph"]
    assert "nodes" in graph
    assert "relationships" in graph
    assert len(graph["nodes"]) >= 3
    assert len(graph["relationships"]) >= 2

    # Evidence IDs citations
    assert len(analysis["evidence_ids_used"]) == 3


def test_analyze_evidence_handles_empty_or_no_fire():
    from data.schemas.models import Evidence, GeoPoint

    dummy_weather = Evidence(
        evidence_id="ev_weather_test",
        source="open-meteo",
        kind="weather",
        status="ok",
        data_mode="mock",
        timestamp="2026-09-29T12:00:00Z",
        fetched_at="2026-09-29T12:00:00Z",
        location=GeoPoint(lat=30.0, lon=31.0),
        measurements={"current": {"wind_speed_kmh": 15.0, "wind_direction_deg": 180.0, "temperature_c": 28.0}},
    )

    analysis = analyze_evidence([dummy_weather], target_name="Test City")
    assert analysis["risk_level"] == "LOW"
    assert analysis["signals"]["fire_count"] == 0
    assert analysis["signals"]["nearest_fire_km"] is None
