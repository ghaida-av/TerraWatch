"""SQLite persistence for TerraWatch investigations."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import List, Optional

from agent.models import InvestigationReport
from apps.api.config import settings
from apps.api.models import InvestigationListResponse, InvestigationSummary


def get_db_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    path = db_path if db_path is not None else settings.DB_PATH
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Optional[str] = None) -> None:
    """Initialize SQLite tables for investigations."""
    conn = get_db_connection(db_path)
    try:
        with conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS investigations (
                    investigation_id TEXT PRIMARY KEY,
                    target_name TEXT NOT NULL,
                    lat REAL NOT NULL,
                    lon REAL NOT NULL,
                    question TEXT NOT NULL,
                    risk_level TEXT NOT NULL,
                    risk_score REAL NOT NULL,
                    confidence REAL NOT NULL,
                    created_at TEXT NOT NULL,
                    report_json TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_investigations_created_at ON investigations (created_at DESC)"
            )
    finally:
        conn.close()


def save_investigation(
    report: InvestigationReport,
    created_at: Optional[str] = None,
    db_path: Optional[str] = None,
) -> None:
    """Persist an investigation report."""
    timestamp = created_at or datetime.now(timezone.utc).isoformat()
    conn = get_db_connection(db_path)
    try:
        with conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO investigations (
                    investigation_id,
                    target_name,
                    lat,
                    lon,
                    question,
                    risk_level,
                    risk_score,
                    confidence,
                    created_at,
                    report_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    report.investigation_id,
                    report.target.name,
                    report.target.lat,
                    report.target.lon,
                    report.question,
                    report.risk_level,
                    report.risk_score,
                    report.confidence,
                    timestamp,
                    report.model_dump_json(),
                ),
            )
    finally:
        conn.close()


def list_investigations(
    limit: int = 50,
    offset: int = 0,
    db_path: Optional[str] = None,
) -> InvestigationListResponse:
    """Retrieve historical investigations list with pagination."""
    conn = get_db_connection(db_path)
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM investigations")
        total = cur.fetchone()[0]

        cur.execute(
            """
            SELECT
                investigation_id,
                target_name,
                lat,
                lon,
                question,
                risk_level,
                risk_score,
                confidence,
                created_at
            FROM investigations
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        )
        rows = cur.fetchall()

        items = [
            InvestigationSummary(
                investigation_id=r["investigation_id"],
                target_name=r["target_name"],
                lat=r["lat"],
                lon=r["lon"],
                question=r["question"],
                risk_level=r["risk_level"],
                risk_score=r["risk_score"],
                confidence=r["confidence"],
                created_at=r["created_at"],
            )
            for r in rows
        ]

        return InvestigationListResponse(total=total, items=items)
    finally:
        conn.close()


def get_investigation(
    investigation_id: str,
    db_path: Optional[str] = None,
) -> Optional[InvestigationReport]:
    """Retrieve full investigation report by ID."""
    conn = get_db_connection(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT report_json FROM investigations WHERE investigation_id = ?",
            (investigation_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return InvestigationReport.model_validate_json(row["report_json"])
    finally:
        conn.close()


def clear_investigations(db_path: Optional[str] = None) -> None:
    """Clear all records (primarily for testing)."""
    conn = get_db_connection(db_path)
    try:
        with conn:
            conn.execute("DELETE FROM investigations")
    finally:
        conn.close()
