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
    for k in ("TERRAWATCH_MODE", "DEMO_MODE", "TERRAWATCH_SIMULATE_FAILURES", "TERRAWATCH_RECORD_FIXTURES"):
        monkeypatch.delenv(k, raising=False)
    for k, v in FAKE_KEYS.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setenv("TERRAWATCH_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("TERRAWATCH_FIXTURES_DIR", str(tmp_path / "fixtures"))
    cache_mod.reset_cache()
    store.clear()
    yield
    cache_mod.reset_cache()
