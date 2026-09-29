import pytest
from agent.investigator import investigate
from agent.models import InvestigationReport


def test_investigate_mock_mode(monkeypatch):
    monkeypatch.setenv("TERRAWATCH_MODE", "mock")

    report = investigate(
        location="Cairo",
        question="What environmental risks exist?",
        sources=["weather", "air_quality", "fire"],
    )

    assert isinstance(report, InvestigationReport)
    assert report.status == "completed"
    assert "Cairo" in report.target.name
    assert 0.0 <= report.risk_score <= 1.0
    assert report.risk_level in ("LOW", "MODERATE", "HIGH", "CRITICAL")
    assert 0.0 <= report.confidence <= 1.0
    assert len(report.key_findings) > 0
    assert len(report.evidence_citations) > 0
    assert "nodes" in report.evidence_graph
    assert "relationships" in report.evidence_graph


def test_investigate_cli_json_export(monkeypatch):
    monkeypatch.setenv("TERRAWATCH_MODE", "mock")
    report = investigate(location="Cairo")
    raw_json = report.model_dump_json()
    assert "investigation_id" in raw_json
    assert "target" in raw_json
