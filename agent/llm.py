"""LLM providers for TerraWatch: Meterless Nightshift Runtime (primary) + NVIDIA direct (fallback).

Power rule (Open Agent Hackathon 2026): the application's AI features call Meterless Nightshift as the
primary provider. Nightshift serves requests through the model lanes configured in its console, which for
this project is an NVIDIA Nemotron lane.

Runtime contract implemented here:
  - Authorization: Bearer <METERLESS_RUNTIME_TOKEN>
  - meterless-app: terrawatch
  - meterless-scope: user  (for chat requests)
  - GET  {base}/v1/models   -> model discovery
  - POST {base}/v1/chat/completions  -> OpenAI-compatible completion

The NVIDIA key itself lives inside Nightshift's Providers tab; this module only needs the Console-supplied
Nightshift URL + Runtime token, read from environment (see .env.example / README).
"""

from __future__ import annotations

import logging
import os
from typing import Callable, Dict, List, Optional

import requests

logger = logging.getLogger("terrawatch.llm")

# An LLM is just "prompt in, text out" (same convention as agent.reasoner). Injectable for tests.
LLM = Callable[[str], str]

APP_HEADER = "terrawatch"
DEFAULT_METERLESS_URL = "http://127.0.0.1:8088/v1"
DEFAULT_METERLESS_MODEL = "meterless/auto"
REQUEST_TIMEOUT = 30  # seconds; Nightshift may route to a cloud lane on first call


class ProviderNotConfigured(RuntimeError):
    """Raised when the environment does not carry the credentials for a provider route."""


def load_env_file(path: Optional[str] = None) -> int:
    """Dependency-free .env loader: sets OS environment variables that are not already set.

    Keeps the guide's contract (secrets live in .env at the project root) without adding python-dotenv.
    Returns the number of variables applied. Never overrides values already present in the environment
    (real editors/CI/wsexported vars win) and never logs values.
    """
    import pathlib

    env_file = pathlib.Path(path) if path else pathlib.Path(__file__).resolve().parents[1] / ".env"
    applied = 0
    try:
        lines = env_file.read_text(encoding="utf-8").splitlines() if env_file.is_file() else []
    except OSError:
        return 0
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, raw = line.partition("=")
        key = key.strip()
        if not key or key in os.environ:
            continue
        os.environ[key] = raw.strip().strip('"').strip("'")
        applied += 1
    return applied


def _settings() -> Dict[str, Optional[str]]:
    """Reads both provider routes from the environment (Meterless primary, NVIDIA direct fallback)."""
    return {
        "meterless_url": os.getenv("METERLESS_BASE_URL") or None,
        "meterless_token": os.getenv("METERLESS_RUNTIME_TOKEN") or None,
        "meterless_model": os.getenv("METERLESS_MODEL") or None,
        "nvidia_url": os.getenv("MODEL_BASE_URL") or None,
        "nvidia_key": os.getenv("MODEL_API_KEY") or None,
        "nvidia_model": os.getenv("NEMOTRON_MODEL") or None,
    }


def _merge_settings(**overrides: Optional[str]) -> Dict[str, Optional[str]]:
    """_settings() with explicit call-time overrides applied only when provided (not None)."""
    merged = _settings()
    for key, value in overrides.items():
        if value is not None:
            merged[key] = value
    return merged


def meterless_configured(**settings: Optional[str]) -> bool:
    """True when a Meterless Runtime URL, token and model are all present."""
    s = _merge_settings(**settings)
    return bool(s["meterless_url"] and s["meterless_token"] and s["meterless_model"])


def _chat(base_url: str, api_key: str, model: str, prompt: str, extra_headers: Dict[str, str],
          timeout: int) -> str:
    """OpenAI-compatible POST /chat/completions; returns the assistant text or raises."""
    url = base_url.rstrip("/") +("/chat/completions" if base_url.rstrip("/").endswith("/v1") else "/v1/chat/completions")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        **extra_headers,
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
    }
    response = requests.post(url, headers=headers, json=payload, timeout=timeout)
    response.raise_for_status()
    data = response.json()
    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError(f"model returned no choices: {str(data)[:120]}")
    content = (choices[0].get("message") or {}).get("content") or ""
    if not content.strip():
        raise RuntimeError("model returned an empty message")
    return str(content)


def meterless_llm(url: Optional[str] = None, token: Optional[str] = None,
                  model: Optional[str] = None, timeout: int = REQUEST_TIMEOUT) -> Optional[LLM]:
    """Returns a Nightshift-backed LLM callable, or None when Meterless is not configured."""
    s = _merge_settings(meterless_url=url, meterless_token=token, meterless_model=model)
    base, key, mdl = s["meterless_url"], s["meterless_token"], s["meterless_model"]
    if not (base and key and mdl):
        logger.info("Meterless provider not configured (METERLESS_BASE_URL/_RUNTIME_TOKEN/_MODEL); skipping.")
        return None
    headers = {"meterless-app": APP_HEADER, "meterless-scope": "user"}

    def invoke(prompt: str) -> str:
        return _chat(base, key, mdl, prompt, headers, timeout)

    return invoke


def nvidia_llm(url: Optional[str] = None, key: Optional[str] = None,
               model: Optional[str] = None, timeout: int = REQUEST_TIMEOUT) -> Optional[LLM]:
    """Fallback route: NVIDIA's hosted endpoint directly (build.nvidia.com), no Nightshift hop."""
    s = _merge_settings(nvidia_url=url, nvidia_key=key, nvidia_model=model)
    base, k, mdl = s["nvidia_url"], s["nvidia_key"], s["nvidia_model"]
    if not (base and k and mdl):
        logger.info("Direct NVIDIA provider not configured (MODEL_BASE_URL/_API_KEY/NEMOTRON_MODEL); skipping.")
        return None
    return lambda prompt: _chat(base, k, mdl, prompt, {}, timeout)


def discover_models(url: Optional[str] = None, token: Optional[str] = None,
                    timeout: int = REQUEST_TIMEOUT) -> List[str]:
    """GET {base}/v1/models against the Nightshift Runtime; returns the advertised model ids."""
    s = _merge_settings(meterless_url=url, meterless_token=token)
    base, key = s["meterless_url"], s["meterless_token"]
    if not (base and key):
        raise ProviderNotConfigured("METERLESS_BASE_URL and METERLESS_RUNTIME_TOKEN are required")
    response = requests.get(
        base.rstrip("/") + "/models",
        headers={"Authorization": f"Bearer {key}", "meterless-app": APP_HEADER},
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json()
    data = payload.get("data") if isinstance(payload, dict) else payload
    return [m.get("id") if isinstance(m, dict) else str(m) for m in (data or [])]


def test_connection(timeout: int = REQUEST_TIMEOUT * 2) -> Dict[str, object]:
    """Connection check for smoke_test.py: discovery + one real completion via the Nightshift lane.

    Returns {"provider", "base_url", "model", "reply", "models_available"}. Raises on any failure.
    """
    s = _settings()
    if not meterless_configured():
        raise ProviderNotConfigured(
            "Meterless Nightshift is not configured: set METERLESS_BASE_URL, "
            "METERLESS_RUNTIME_TOKEN and METERLESS_MODEL (see README)."
        )
    fn = meterless_llm(timeout=timeout)
    models_available: List[str] = []
    try:
        models_available = discover_models(s["meterless_url"], s["meterless_token"], timeout=10)
    except Exception as exc:  # discovery failure must not block the real chat check
        logger.warning("Model discovery failed (%s); continuing with chat check.", exc)

    reply = (fn or (lambda p: ""))("Reply with the single word: ready")
    return {
        "provider": "meterless-nightshift",
        "base_url": s["meterless_url"],
        "model": s["meterless_model"],
        "reply": " ".join(reply.split())[:80],
        "models_available": len(models_available),
    }
