"""Unit tests for the Meterless Nightshift / NVIDIA providers (agent/llm.py) and the reasoner chain."""
from __future__ import annotations

import json
import os

import pytest

from agent import llm as providers
from agent.reasoner import generate_synthesis


class _FakeResponse:
    def __init__(self, payload=None, status_error=False):
        self._payload = payload if payload is not None else {}
        self.text = json.dumps(self._payload)

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


@pytest.fixture(autouse=True)
def provider_env(monkeypatch):
    for key in ("METERLESS_BASE_URL", "METERLESS_RUNTIME_TOKEN", "METERLESS_MODEL",
                "MODEL_BASE_URL", "MODEL_API_KEY", "NEMOTRON_MODEL"):
        monkeypatch.delenv(key, raising=False)
    yield


def _configure_meterless(monkeypatch, base="http://127.0.0.1:8088/v1", token="tok-123",
                         model="nvidia/nemotron-3.5-bolt-e4b"):
    monkeypatch.setenv("METERLESS_BASE_URL", base)
    monkeypatch.setenv("METERLESS_RUNTIME_TOKEN", token)
    monkeypatch.setenv("METERLESS_MODEL", model)


def test_meterless_unconfigured_by_default():
    assert not providers.meterless_configured()
    assert providers.meterless_llm() is None


def test_meterless_chat_contract(monkeypatch):
    """The runtime contract: Bearer auth + meterless-app + meterless-scope headers, OpenAI payload."""
    _configure_meterless(monkeypatch)
    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured.update(url=url, headers=headers, payload=json, timeout=timeout)
        return _FakeResponse({"choices": [{"message": {"content": "ready"}}]})

    monkeypatch.setattr(providers.requests, "post", fake_post)
    fn = providers.meterless_llm()
    assert fn("hello") == "ready"

    assert captured["url"] == "http://127.0.0.1:8088/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer tok-123"
    assert captured["headers"]["meterless-app"] == "terrawatch"
    assert captured["headers"]["meterless-scope"] == "user"
    assert captured["payload"]["model"] == "nvidia/nemotron-3.5-bolt-e4b"
    assert captured["payload"]["messages"] == [{"role": "user", "content": "hello"}]


def test_discovery_endpoint(monkeypatch):
    _configure_meterless(monkeypatch)
    captured = {}

    def fake_get(url, headers=None, timeout=None):
        captured.update(url=url, headers=headers)
        return _FakeResponse({"data": [{"id": "nvidia/nemotron-3.5-bolt-e4b"}, {"id": "meterless/auto"}]})

    monkeypatch.setattr(providers.requests, "get", fake_get)
    models = providers.discover_models()
    assert models == ["nvidia/nemotron-3.5-bolt-e4b", "meterless/auto"]
    assert captured["url"] == "http://127.0.0.1:8088/v1/models"
    assert captured["headers"]["Authorization"] == "Bearer tok-123"
    assert captured["headers"]["meterless-app"] == "terrawatch"


def test_connection_reports_provider_and_reply(monkeypatch):
    _configure_meterless(monkeypatch)
    monkeypatch.setattr(providers.requests, "get",
                        lambda *a, **kw: _FakeResponse({"data": [{"id": "m1"}]}))
    monkeypatch.setattr(providers.requests, "post",
                        lambda *a, **kw: _FakeResponse({"choices": [{"message": {"content": " ready "}}]}))
    info = providers.test_connection(timeout=5)
    assert info["provider"] == "meterless-nightshift"
    assert info["reply"] == "ready"
    assert "nemotron" in str(info["model"]).lower()
    assert info["models_available"] == 1


def test_nvidia_direct_fallback_route(monkeypatch):
    monkeypatch.setenv("MODEL_BASE_URL", "https://integrate.api.nvidia.com/v1")
    monkeypatch.setenv("MODEL_API_KEY", "nvapi-x")
    monkeypatch.setenv("NEMOTRON_MODEL", "nvidia/nemotron-3.5-lightning-30b-a3b")
    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured.update(url=url, headers=headers, payload=json)
        return _FakeResponse({"choices": [{"message": {"content": "ok"}}]})

    monkeypatch.setattr(providers.requests, "post", fake_post)
    fn = providers.nvidia_llm()
    assert fn("ping") == "ok"
    assert captured["url"] == "https://integrate.api.nvidia.com/v1/v1/chat/completions" or \
        captured["url"].endswith("/v1/chat/completions")
    assert captured["headers"]["Authorization"] == "Bearer nvapi-x"


def test_empty_choices_and_empty_content_raise(monkeypatch):
    _configure_meterless(monkeypatch)
    monkeypatch.setattr(providers.requests, "post", lambda *a, **kw: _FakeResponse({"choices": []}))
    with pytest.raises(RuntimeError):
        providers.meterless_llm()("hi")
    monkeypatch.setattr(
        providers.requests, "post",
        lambda *a, **kw: _FakeResponse({"choices": [{"message": {"content": "  "}}]}))
    with pytest.raises(RuntimeError):
        providers.meterless_llm()("hi")


def test_load_env_file_does_not_override_real_env(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("A_VAR=b\n# comment\nB_VAR=c\nA_VAR=ignored\n")
    monkeypatch.setenv("A_VAR", "a")
    os.environ.pop("B_VAR", None)
    try:
        applied = providers.load_env_file(str(env_file))
        assert applied == 1  # B_VAR applied; A_VAR skipped because it is already in the environment
        assert os.environ["A_VAR"] == "a"
        assert os.environ["B_VAR"] == "c"
    finally:
        os.environ.pop("B_VAR", None)


def _tiny_analysis(target="Cairo", risk_level="LOW", risk_score=0.1):
    return {
        "target": {"name": target, "lat": 30.0, "lon": 31.0},
        "risk_level": risk_level,
        "risk_score": risk_score,
        "signals": {},
        "components": {"proximity": 0, "wind_alignment": 0, "air_quality_anomaly": 0,
                       "temporal_correlation": 0},
    }


def test_reasoner_chain_prefers_nightshift(monkeypatch):
    called = {}

    def nightshift(prompt):
        called["provider"] = "nightshift"
        return ("Environmental risk at Cairo rated LOW (score 0.10). No elevated indicators in the "
                "available data.")

    monkeypatch.setattr("agent.reasoner._nightshift_llm", lambda: nightshift)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    out = generate_synthesis("q", _tiny_analysis(), [], llm=None)
    assert called["provider"] == "nightshift"
    assert out["summary_source"] == "llm"


def test_reasoner_falls_back_on_provider_error(monkeypatch):
    def boom(prompt):
        raise RuntimeError("nightshift down")

    monkeypatch.setattr("agent.reasoner._nightshift_llm", lambda: boom)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    out = generate_synthesis("q", _tiny_analysis(), [], llm=None)
    assert out["summary_source"] == "deterministic_fallback"
    assert any("LLM call failed" in n for n in out["guardrail_notes"])
