"""H-MEM engine for TerraWatch: persistent investigation memory.

Build rule (Open Agent Hackathon 2026): at least one Meterless Engine must power a working feature with a
reproducible test. TerraWatch integrates **H-MEM** — Meterless's persistent memory & retrieval engine — as
the feature that lets the agent *remember prior investigations per location*.

What it does:
  - remember(report): extracts a compact fact sheet from a completed InvestigationReport and persists it
    as one memory entry keyed to the target location (name + coordinates).
  - recall(name, lat, lon): retrieves memories for the same/nearby location (<50 km geodesic, data.core.geo
    haversine) and renders them as deterministic fact lines.

Where it powers the product:
  - agent.investigator.investigate() / investigate_stream() recall memory right after geocoding and inject
    ("memory:" prefixed) lines into key findings and the LLM synthesis prompt, then store the new report.
  - a report pays tribute via InvestigationReport.memory_used / memory_notes.

Design keeps the repo rule intact: memory retrieval is deterministic Python; the LLM merely explains what
memory + fresh evidence say. Memory numbers are added to the guardrail allow-list so summaries citing them
are not rejected.

Env:
  - TERRAWATCH_MEMORY_DB   sqlite path (default: <repo>/terrawatch.db, shared with the API storage)
  - TERRAWATCH_MEMORY      "0"/"false" disables the feature entirely
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from data.core.geo import haversine_km

MATCH_RADIUS_KM = 50.0
MAX_ENTRIES_PER_LOCATION = 10
MAX_FACT_CHARS = 240

_LOCK = threading.Lock()
_ENABLED = None  # lazy tri-state: None -> read env once
_DB_PATH = None  # lazy path cache (tests override via TERRAWATCH_MEMORY_DB + reset())
_conn: Optional[sqlite3.Connection] = None

_DDL = """
CREATE TABLE IF NOT EXISTS investigation_memory (
    fact_id          TEXT PRIMARY KEY,
    target_name      TEXT NOT NULL,
    lat              REAL NOT NULL,
    lon              REAL NOT NULL,
    risk_level       TEXT NOT NULL,
    risk_score       REAL NOT NULL,
    investigation_id TEXT NOT NULL,
    created_at       TEXT NOT NULL,
    facts_json       TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_memory_target ON investigation_memory (target_name);
"""


# ---------------------------------------------------------------------------
# configuration & lifecycle
# ---------------------------------------------------------------------------

def set_enabled(value: bool) -> None:
    """Explicitly enable/disable the H-MEM feature (takes precedence over TERRAWATCH_MEMORY)."""
    global _ENABLED
    _ENABLED = bool(value)


def is_enabled() -> bool:
    """H-MEM is on by default; TERRAWATCH_MEMORY=0/false/off turns it off."""
    global _ENABLED
    if _ENABLED is None:
        flag = (os.getenv("TERRAWATCH_MEMORY") or "").strip().lower()
        _ENABLED = flag not in {"0", "false", "off"}
    return _ENABLED


def db_path() -> str:
    path = os.getenv("TERRAWATCH_MEMORY_DB")
    if path:
        return path
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(root, "terrawatch.db")


def _connection() -> sqlite3.Connection:
    global _conn, _DB_PATH
    path = db_path()
    if _conn is None or _DB_PATH != path:
        if _conn is not None:
            _conn.close()
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        _conn = sqlite3.connect(path, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.executescript(_DDL)
        _DB_PATH = path
    return _conn


def reset() -> None:
    """Drops the process-level connection cache (next call re-opens the configured DB)."""
    global _conn, _DB_PATH
    with _LOCK:
        if _conn is not None:
            _conn.close()
        _conn = None
        _DB_PATH = None


def reset_for_tests() -> None:
    """Test hook alias: simulates a fresh session without touching stored rows."""
    reset()


# ---------------------------------------------------------------------------
# fact extraction / persistence
# ---------------------------------------------------------------------------

def _facts_from_report(report) -> List[str]:
    """Deterministic fact extraction from an InvestigationReport (numbers only from the report)."""
    comps = report.components
    facts = [
        f"risk rated {report.risk_level} (score {report.risk_score:.2f})",
        f"components: proximity {comps.proximity:.2f}, wind alignment {comps.wind_alignment:.2f}, "
        f"air quality anomaly {comps.air_quality_anomaly:.2f}, temporal correlation "
        f"{comps.temporal_correlation:.2f}",
        f"confidence {report.confidence:.2f}",
    ]
    top_signals = [
        (k, report.signals[k]) for k in ("fire_count", "nearest_fire_km", "wind_speed_kmh",
                                         "pm25_ug_m3") if k in report.signals and report.signals[k]
    ]
    if top_signals:
        facts.append("key signals: " + ", ".join(f"{k}={v}" for k, v in top_signals))
    if report.risk_indicators:
        facts.append("risk indicators: " + "; ".join(report.risk_indicators[:3]))
    return facts


def remember(report, created_at: Optional[str] = None) -> bool:
    """Persists one memory entry per completed investigation. Returns True when stored."""
    if not is_enabled():
        return False
    try:
        facts = _facts_from_report(report)
    except Exception:  # model validation error on foreign Report-like objects: never break the run
        return False
    if not facts:
        return False

    timestamp = created_at or datetime.now(timezone.utc).isoformat()
    fact_id = f"mem_{report.investigation_id}"
    with _LOCK:
        conn = _connection()
        with conn:
            conn.execute(
                "DELETE FROM investigation_memory WHERE fact_id = ?",
                (fact_id,),
            )
            conn.execute(
                "INSERT INTO investigation_memory (fact_id, target_name, lat, lon, risk_level, "
                "risk_score, investigation_id, created_at, facts_json) VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    fact_id, report.target.name, float(report.target.lat), float(report.target.lon),
                    report.risk_level, float(report.risk_score), report.investigation_id,
                    timestamp, json.dumps(facts),
                ),
            )
            conn.execute(
                # keep only the MAX_ENTRIES_PER_LOCATION newest memories for this location overall
                "DELETE FROM investigation_memory WHERE target_name = ? AND fact_id NOT IN ("
                "  SELECT fact_id FROM investigation_memory WHERE target_name = ?"
                "  ORDER BY created_at DESC, fact_id DESC LIMIT ?)",
                (report.target.name, report.target.name, MAX_ENTRIES_PER_LOCATION),
            )
    return True


def _row_as_fact(row: sqlite3.Row) -> Tuple[str, Dict[str, Any]]:
    created = (row["created_at"] or "").split("T")[0]
    summary = (
        f"memory: investigation {row['investigation_id']} on {created} for {row['target_name']} "
        f"rated {row['risk_level']} (score {float(row['risk_score']):.2f})."
    )
    payload = json.loads(row["facts_json"])
    return summary, {"investigation_id": row["investigation_id"], "created_at": row["created_at"],
                     "risk_level": row["risk_level"], "risk_score": float(row["risk_score"]),
                     "facts": payload}


def recall(name: str, lat: float, lon: float) -> List[str]:
    """Deterministic retrieval: memories for this exact location name or within MATCH_RADIUS_KM.

    Returns human-readable fact lines ("memory: ..."). Empty list when nothing applies / feature off.
    """
    if not is_enabled():
        return []
    with _LOCK:
        conn = _connection()
        cur = conn.execute(
            "SELECT * FROM investigation_memory ORDER BY created_at DESC, fact_id DESC "
            "LIMIT 200"
        )
        rows = cur.fetchall()
    wanted = (name or "").strip().lower()
    out: List[str] = []
    for row in rows:
        same_place = wanted and row["target_name"].strip().lower() == wanted
        near = (lat is not None and lon is not None and
                haversine_km(lat, lon, row["lat"], row["lon"]) <= MATCH_RADIUS_KM)
        if not (same_place or near):
            continue
        summary, _meta = _row_as_fact(row)
        out.append(summary)
        if len(out) >= 3:  # keep the client prompt bounded
            break
    return out


def stats() -> Dict[str, Any]:
    """Small introspection helper for demos/tests: entry count + db path."""
    if not is_enabled():
        return {"enabled": False, "entries": 0, "db": db_path()}
    with _LOCK:
        conn = _connection()
        count = conn.execute("SELECT COUNT(*) FROM investigation_memory").fetchone()[0]
    return {"enabled": True, "entries": count, "db": db_path()}


def clear() -> int:
    """Removes every memory entry (demo reset). Returns the number of deleted rows."""
    with _LOCK:
        conn = _connection()
        with conn:
            deleted = conn.execute("DELETE FROM investigation_memory").rowcount
    return deleted
