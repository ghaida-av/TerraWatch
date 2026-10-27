"""TerraWatch all-in-one smoke test (Open Agent Hackathon 2026 "Verify your setup" Check 3).

Adapted to this project's architecture:
  - Data check : a full investigation runs through the TerraWatch pipeline (mock mode: deterministic,
                 offline, no network) and produces a structured report.
  - Power check: a real chat request is served through the Meterless Nightshift Runtime
                 (METERLESS_BASE_URL/_RUNTIME_TOKEN/_MODEL from .env), i.e. app -> Nightshift -> Nemotron lane.
  - Engine check: the H-MEM persistent investigation memory round-trips a fact across two "sessions"
                 (remember -> new store instance -> recall), the Build-rule feature.

Run from the repo root while Nightshift is running:
    .venv/bin/python smoke_test.py
"""

from __future__ import annotations

import os
import sys
import tempfile

results = []


def check(name, fn):
    try:
        detail = fn()
        results.append(("PASS", name, detail))
    except Exception as error:  # noqa: BLE001 - report every failure the way the guide's script does
        results.append(("FAIL", name, str(error)[:160]))


def data_investigation():
    os.environ["TERRAWATCH_MODE"] = "mock"
    os.environ.pop("GROQ_API_KEY", None)
    from agent import memory as memory_pkg
    from agent.investigator import investigate

    os.environ["TERRAWATCH_MEMORY_DB"] = os.path.join(tempfile.mkdtemp(), "memory_test.db")
    memory_pkg.reset()
    memory_pkg.set_enabled(True)

    report = investigate("Cairo")
    if report.status != "completed" or not report.risk_level:
        raise AssertionError("investigation did not complete")
    if report.summary_source not in ("deterministic", "llm"):
        raise AssertionError(f"unexpected summary source: {report.summary_source}")
    return f"report={report.investigation_id} risk={report.risk_level} ({report.risk_score:.2f})"


def data_memory_roundtrip():
    from agent import memory as memory_pkg
    from agent.models import InvestigationLocation, InvestigationReport, RiskComponents

    db = os.path.join(tempfile.mkdtemp(), "memory_test.db")
    os.environ["TERRAWATCH_MEMORY_DB"] = db
    memory_pkg.reset()
    memory_pkg.set_enabled(True)

    report = InvestigationReport(
        investigation_id="inv_smoketest1",
        target=InvestigationLocation(name="Cairo", lat=30.0444, lon=31.2357),
        question="What environmental risks exist?",
        risk_level="HIGH",
        risk_score=0.71,
        confidence=0.9,
        components=RiskComponents(proximity=0.6, wind_alignment=0.8, air_quality_anomaly=0.7,
                                  temporal_correlation=0.5),
        signals={"fire_count": 3, "nearest_fire_km": 45.0},
        key_findings=["Detected 3 active thermal hotspot(s), closest at 45 km."],
        risk_indicators=["Elevated fire proximity risk."],
        executive_summary="risk HIGH",
        evidence_graph={},
        evidence_citations=[],
    )
    memory_pkg.remember(report)
    memory_pkg.reset_for_tests()  # simulate a new session / fresh process state
    facts = memory_pkg.recall("Cairo", 30.0444, 31.2357)
    if not facts:
        raise AssertionError("H-MEM recall returned no facts after remember()")
    if not any("HIGH" in fact for fact in facts):
        raise AssertionError(f"memory facts do not carry the prior risk level: {facts[:2]}")
    return f"{len(facts)} fact(s) recalled: {facts[0][:60]}..."


def power_nightshift():
    from agent import llm as llm_providers

    if not llm_providers.meterless_configured():
        raise AssertionError(
            "Meterless not configured: set METERLESS_BASE_URL, METERLESS_RUNTIME_TOKEN, METERLESS_MODEL in .env"
        )
    info = llm_providers.test_connection(timeout=40)
    models = info["models_available"]
    # Large catalogs may report 0 if discovery is disabled; the real requirement is the chat reply.
    return f"via={info['model']} reply='{info['reply']}' (models known: {models})"


def main() -> int:
    check("Data: investigation pipeline (mock, offline)", data_investigation)
    check("Data: H-MEM memory round-trip across sessions", data_memory_roundtrip)
    check("Power: Nemotron replies via Meterless Nightshift", power_nightshift)

    failures = 0
    for status, name, detail in results:
        print(f"{status} {name} {detail or ''}")
        failures += status == "FAIL"

    if failures:
        print(f"\n{failures} check(s) failed. See README 'Meterless provider settings'.")
    else:
        print("\nAll checks passed - TerraWatch Data, Build (H-MEM) and Power (Nightshift) are ready.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
