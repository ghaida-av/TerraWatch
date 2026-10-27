import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from data import store  # noqa: E402
from data.core import cache as cache_mod  # noqa: E402

FAKE_KEYS = {"OPENAQ_API_KEY": "openaq-secret-key-123", "FIRMS_MAP_KEY": "firms-secret-key-456",
             "GEOAPIFY_API_KEY": "geoapify-secret-key-789"}


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch, tmp_path):
    for k in ("TERRAWATCH_MODE", "DEMO_MODE", "TERRAWATCH_SIMULATE_FAILURES", "TERRAWATCH_RECORD_FIXTURES",
              # keep every test offline/deterministic: strip live provider creds loaded from .env
              "METERLESS_BASE_URL", "METERLESS_RUNTIME_TOKEN", "METERLESS_MODEL",
              "MODEL_BASE_URL", "MODEL_API_KEY", "NEMOTRON_MODEL", "GROQ_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    for k, v in FAKE_KEYS.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setenv("TERRAWATCH_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("TERRAWATCH_FIXTURES_DIR", str(tmp_path / "fixtures"))
    monkeypatch.setenv("TERRAWATCH_MEMORY_DB", str(tmp_path / "memory" / "memory.db"))
    cache_mod.reset_cache()
    store.clear()
    from agent import memory as investigation_memory
    investigation_memory.reset()  # re-open against the tmp memory DB for every test
    yield
    investigation_memory.reset()
    cache_mod.reset_cache()
