import json

import pytest

from data.adapters import FireAdapter, WeatherAdapter
from data.core import http
from data.core.errors import AdapterError, ErrorType
from data import collect_evidence
from tests.test_live_parsing import FIRMS_CSV

CAIRO = (30.0444, 31.2357)


class FakeResp:
    def __init__(self, code, text=""):
        self.status_code, self.text = code, text


@pytest.mark.parametrize("code,etype,retry", [
    (401, ErrorType.AUTH, False), (403, ErrorType.AUTH, False), (404, ErrorType.NOT_FOUND, False),
    (429, ErrorType.RATE_LIMITED, True), (400, ErrorType.BAD_REQUEST, False), (503, ErrorType.SERVER, True)])
def test_http_status_mapping(code, etype, retry):
    with pytest.raises(AdapterError) as ei:
        http._raise_for_status(FakeResp(code, "nope"))
    assert ei.value.type == etype and ei.value.retryable is retry and ei.value.http_status == code


def test_redact_scrubs_known_keys_and_query_params():
    s = http.redact("GET https://x/y?apiKey=abc123&z=1 failed; token=zzz; firms-secret-key-456 leaked")
    assert "abc123" not in s and "zzz" not in s and "firms-secret-key-456" not in s


def test_cache_then_stale_recovery(monkeypatch):
    calls = {"n": 0, "fail": False}
    csv_text = FIRMS_CSV

    def fake(url, **k):
        calls["n"] += 1
        if calls["fail"]:
            raise AdapterError(ErrorType.RATE_LIMITED, "429", http_status=429, retryable=True)
        return csv_text

    monkeypatch.setattr(http, "get_text", fake)
    ad = FireAdapter()
    a = ad.fetch(*CAIRO)
    assert a.data_mode == "live"
    b = ad.fetch(*CAIRO)
    assert b.data_mode == "cache" and calls["n"] == 1                      # second call never hit the API

    ad.ttl_seconds = 0                                                      # force "expired but still stale-usable"
    calls["fail"] = True
    c = ad.fetch(*CAIRO)
    assert c.status == "ok" and c.data_mode == "stale_cache"
    assert "rate_limited" in c.warnings[0]
    assert c.measurements == a.measurements


def test_failure_without_cache_returns_error_evidence_never_raises(monkeypatch):
    def boom(*a, **k):
        raise AdapterError(ErrorType.TIMEOUT, "Request timed out", retryable=True)

    monkeypatch.setattr(http, "get_json", boom)
    ev = WeatherAdapter().fetch(*CAIRO)
    assert ev.status == "error" and ev.error.type == "timeout" and ev.error.retryable
    assert ev.measurements == {}


def test_unexpected_exception_is_contained(monkeypatch):
    monkeypatch.setattr(http, "get_text", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("kaboom key=firms-secret-key-456")))
    ev = FireAdapter().fetch(*CAIRO)
    assert ev.status == "error" and ev.error.type == "bad_response"
    assert "firms-secret-key-456" not in ev.error.message


def test_simulated_outage_only_hits_named_source(monkeypatch):
    monkeypatch.setenv("TERRAWATCH_MODE", "mock")
    monkeypatch.setenv("TERRAWATCH_SIMULATE_FAILURES", "fire")
    ev = {e.kind: e for e in collect_evidence(*CAIRO, sources=["weather", "air_quality", "fire"])}
    assert ev["fire"].status == "error" and ev["fire"].error.type == "simulated_outage"
    assert ev["weather"].status == "ok" and ev["air_quality"].status == "ok"


def test_collect_evidence_isolates_one_failure(monkeypatch):
    monkeypatch.setenv("TERRAWATCH_MODE", "mock")
    monkeypatch.setenv("TERRAWATCH_SIMULATE_FAILURES", "all")
    out = collect_evidence(*CAIRO)
    assert len(out) == 3 and all(e.status == "error" for e in out)


def test_unknown_source_name_is_a_clear_error():
    with pytest.raises(ValueError, match="Unknown source"):
        collect_evidence(*CAIRO, sources=["volcano"])


def test_extra_llm_args_ignored(monkeypatch):
    monkeypatch.setenv("TERRAWATCH_MODE", "mock")
    ev = WeatherAdapter().fetch(*CAIRO, tz_name="Africa/Cairo", bogus=1)
    assert ev.status == "ok" and "bogus" not in ev.query


def test_demo_mode_replays_recorded_fixture_without_network(monkeypatch):
    # 1) record while "live"
    monkeypatch.setenv("TERRAWATCH_RECORD_FIXTURES", "1")
    monkeypatch.setattr(http, "get_text", lambda url, **k: FIRMS_CSV)
    live = FireAdapter().fetch(*CAIRO)
    assert live.data_mode == "live"
    # 2) demo mode: network must not be touched, nearby coordinates still match
    def no_network(*a, **k):
        raise AssertionError("network used in demo mode")

    monkeypatch.delenv("TERRAWATCH_RECORD_FIXTURES")
    monkeypatch.setenv("TERRAWATCH_MODE", "demo")
    monkeypatch.setattr(http, "get_text", no_network)
    demo = FireAdapter().fetch(30.05, 31.24)
    assert demo.data_mode == "demo" and demo.measurements == live.measurements
    assert "recorded response" in demo.warnings[0]


def test_demo_mode_without_fixture_falls_back_to_labelled_mock(monkeypatch):
    monkeypatch.setenv("TERRAWATCH_MODE", "demo")
    ev = FireAdapter().fetch(*CAIRO)
    assert ev.data_mode == "mock" and "no recorded" in ev.warnings[0]


def test_legacy_demo_mode_env_flag(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "True")
    ev = FireAdapter().fetch(*CAIRO)
    assert ev.data_mode == "mock" and "Demo mode" in ev.warnings[0]


def test_evidence_id_is_deterministic_for_identical_data(monkeypatch):
    monkeypatch.setenv("TERRAWATCH_MODE", "mock")
    from data.core import mock_scenario as ms
    from datetime import datetime, timezone
    fixed = datetime(2026, 9, 19, 12, tzinfo=timezone.utc)
    monkeypatch.setattr(ms, "now_hour", lambda: fixed)
    a, b = FireAdapter().fetch(*CAIRO), FireAdapter().fetch(*CAIRO)
    assert a.evidence_id == b.evidence_id
    assert json.loads(a.model_dump_json())["evidence_id"].startswith("ev_nasa_firms_")
