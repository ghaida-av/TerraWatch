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
