"""Test suite for TerraWatch Backend API (apps/api)."""

import os
import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from apps.api.storage import clear_investigations, init_db


@pytest.fixture(autouse=True)
def setup_test_db(tmp_path, monkeypatch):
    """Use a temporary SQLite database for each test."""
    test_db = str(tmp_path / "test_terrawatch.db")
    monkeypatch.setenv("TERRAWATCH_MODE", "mock")
    monkeypatch.setattr("apps.api.config.settings.DB_PATH", test_db)
    init_db(test_db)
    yield
    clear_investigations(test_db)


@pytest.fixture
def client():
    """Create TestClient."""
    with TestClient(app) as test_client:
        yield test_client


def test_root_and_health(client):
    """Test root and health check endpoints."""
    res_root = client.get("/")
    assert res_root.status_code == 200
    assert res_root.json()["name"] == "TerraWatch API"

    res_health = client.get("/api/health")
    assert res_health.status_code == 200
    data = res_health.json()
    assert data["status"] == "ok"
    assert data["mode"] == "mock"
    assert "weather" in data["active_sources"]


def test_sources_endpoint(client):
    """Test data sources telemetry."""
    res = client.get("/api/sources")
    assert res.status_code == 200
    data = res.json()
    assert data["total_sources"] >= 5
    source_ids = [s["id"] for s in data["sources"]]
    assert "weather" in source_ids
    assert "fire" in source_ids
    assert "air_quality" in source_ids


def test_create_and_fetch_investigation(client):
    """Test full cycle: create investigation, list it, and fetch by ID."""
    # 1. Create Investigation
    payload = {
        "location": "Cairo",
        "question": "Is smoke from recent fires reaching the city?",
        "sources": ["weather", "air_quality", "fire"],
    }
    create_res = client.post("/api/investigations", json=payload)
    assert create_res.status_code == 201
    report = create_res.json()

    inv_id = report["investigation_id"]
    assert inv_id.startswith("inv_")
    assert "Cairo" in report["target"]["name"]
    assert report["risk_level"] in ["LOW", "MODERATE", "HIGH", "CRITICAL"]
    assert 0.0 <= report["risk_score"] <= 1.0
    assert report["confidence"] > 0
    assert "proximity" in report["components"]
    assert len(report["evidence_citations"]) > 0
    assert "nodes" in report["evidence_graph"]
    assert "relationships" in report["evidence_graph"]

    # 2. List investigations
    list_res = client.get("/api/investigations")
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total"] >= 1
    matching = [item for item in list_data["items"] if item["investigation_id"] == inv_id]
    assert len(matching) == 1
    assert matching[0]["risk_level"] == report["risk_level"]

    # 3. Fetch single investigation
    get_res = client.get(f"/api/investigations/{inv_id}")
    assert get_res.status_code == 200
    assert get_res.json()["investigation_id"] == inv_id

    # 4. Fetch evidence graph specifically
    graph_res = client.get(f"/api/investigations/{inv_id}/graph")
    assert graph_res.status_code == 200
    assert "nodes" in graph_res.json()
    assert len(graph_res.json()["nodes"]) >= 3


def test_evidence_drilldown(client):
    """Test retrieving full raw evidence observations via citation ID."""
    create_res = client.post(
        "/api/investigations",
        json={"location": "Cairo", "sources": ["weather", "fire"]},
    )
    assert create_res.status_code == 201
    citations = create_res.json()["evidence_citations"]
    assert len(citations) > 0

    target_citation = citations[0]
    ev_res = client.get(f"/api/evidence/{target_citation}")
    assert ev_res.status_code == 200
    ev_data = ev_res.json()
    assert ev_data["evidence_id"] == target_citation
    assert "measurements" in ev_data
    assert "status" in ev_data


def test_404_handling(client):
    """Test not found behaviors."""
    res_inv = client.get("/api/investigations/inv_doesnotexist")
    assert res_inv.status_code == 404
    assert "not found" in res_inv.json()["detail"].lower()

    res_ev = client.get("/api/evidence/ev_doesnotexist")
    assert res_ev.status_code == 404
    assert "not found" in res_ev.json()["detail"].lower()


def test_stream_investigation_endpoint(client):
    """Test SSE streaming endpoint yields stage events and persists report."""
    with client.stream(
        "GET",
        "/api/investigations/stream",
        params={"location": "Alexandria", "sources": ["weather", "fire"]},
    ) as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")

        events = []
        for line in response.iter_lines():
            if line.startswith("data: "):
                data_str = line[len("data: "):]
                events.append(data_str)

        assert len(events) >= 4  # geocoding, geocoded, collecting_evidence, geo_analysis, completed
        assert any('"geocoding"' in e for e in events)
        assert any('"completed"' in e for e in events)

    # Verify report was persisted in database by stream completion
    list_res = client.get("/api/investigations")
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert any("Alexandria" in item["target_name"] for item in list_data["items"])


def test_sqlite_and_sqlalchemy_coexistence():
    """Verify raw SQLite functions and SQLAlchemy async storage coexist seamlessly."""
    import asyncio
    from apps.api.config import settings
    from apps.api.storage import (
        clear_investigations,
        get_investigation,
        get_investigation_async,
        list_investigations,
        list_investigations_async,
        save_investigation,
        save_investigation_async,
    )
    from agent.investigator import investigate

    # 1. Run investigation and save via native SQLite function
    report1 = investigate("Giza", sources=["weather"])
    save_investigation(report1)

    # Read back via raw SQLite
    sync_read = get_investigation(report1.investigation_id)
    assert sync_read is not None
    assert sync_read.investigation_id == report1.investigation_id

    # Read back via SQLAlchemy async
    async_read = asyncio.run(get_investigation_async(report1.investigation_id))
    assert async_read is not None
    assert async_read.investigation_id == report1.investigation_id

    # 2. Save another via SQLAlchemy async and read via raw SQLite
    report2 = investigate("Luxor", sources=["weather"])
    asyncio.run(save_investigation_async(report2))

    sync_list = list_investigations()
    assert sync_list.total >= 2
    assert any(item.target_name == report2.target.name for item in sync_list.items)

    async_list = asyncio.run(list_investigations_async())
    assert async_list.total == sync_list.total


def test_monitor_events_mock(client):
    r = client.get("/api/monitor/events?window=day&min_mag=3")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == len(body["events"]) > 0
    assert body["mode"] == "mock"
    assert body["source_status"] == "ok"
    assert all(e["id"].startswith("mock") for e in body["events"])
    assert all(e["magnitude"] >= 3 for e in body["events"])
    assert set(body["summary"]["levels"]) == {"LOW", "MODERATE", "HIGH", "CRITICAL"}


def test_monitor_live_feed_failure_is_not_replaced_with_mock(client, monkeypatch):
    from data.adapters.usgs import global_feed
    from data.core.errors import AdapterError, ErrorType

    monkeypatch.setenv("TERRAWATCH_MODE", "live")
    global_feed._cache.clear()

    def fail_live_feed(window, min_mag):
        raise AdapterError(ErrorType.NETWORK, "USGS is unreachable")

    monkeypatch.setattr(global_feed, "_live_events", fail_live_feed)
    response = client.get("/api/monitor/events?window=day&min_mag=2.5")

    assert response.status_code == 502
    assert response.json()["detail"] == "Live USGS earthquake feed unavailable: USGS is unreachable"


def test_monitor_live_feed_returns_upstream_events(client, monkeypatch):
    from data.adapters.usgs import global_feed

    monkeypatch.setenv("TERRAWATCH_MODE", "live")
    global_feed._cache.clear()
    upstream_event = {
        "id": "us7000test",
        "magnitude": 4.2,
        "place": "10 km north of Test City",
        "time": "2026-10-13T12:00:00Z",
        "lat": 12.0,
        "lon": 34.0,
        "depth_km": 8.0,
        "level": "MODERATE",
        "url": "https://earthquake.usgs.gov/test",
    }
    monkeypatch.setattr(global_feed, "_live_events", lambda window, min_mag: [upstream_event])

    response = client.get("/api/monitor/events?window=day&min_mag=2.5")
    body = response.json()

    assert response.status_code == 200
    assert body["mode"] == "live"
    assert body["events"] == [upstream_event]
