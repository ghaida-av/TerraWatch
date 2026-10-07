"""Database persistence layer for TerraWatch investigations.

Supports:
1. Native SQLite connection (backward-compatible).
2. SQLAlchemy 2.0 ORM & Declarative Models.
3. Async session management via aiosqlite and async engines.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import AsyncGenerator, List, Optional

from sqlalchemy import Float, Index, Integer, String, Text, delete, func, select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from agent.models import InvestigationReport
from apps.api.config import settings
from apps.api.models import InvestigationListResponse, InvestigationSummary


# ---------------------------------------------------------------------------
# SQLAlchemy Declarative Models
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    pass


class InvestigationRecord(Base):
    __tablename__ = "investigations"

    investigation_id: Mapped[str] = mapped_column(String, primary_key=True)
    target_name: Mapped[str] = mapped_column(String, nullable=False)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lon: Mapped[float] = mapped_column(Float, nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    risk_level: Mapped[str] = mapped_column(String, nullable=False)
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[str] = mapped_column(String, nullable=False, index=True)
    report_json: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        Index("idx_investigations_created_at", "created_at"),
    )


# Cache for async engines by db_url
_async_engines: dict[str, AsyncEngine] = {}


def get_async_engine(db_path: Optional[str] = None) -> AsyncEngine:
    path = db_path if db_path is not None else settings.DB_PATH
    db_url = f"sqlite+aiosqlite:///{path}"
    if db_url not in _async_engines:
        _async_engines[db_url] = create_async_engine(
            db_url,
            echo=False,
            future=True,
            connect_args={"check_same_thread": False},
        )
    return _async_engines[db_url]


def get_async_session_maker(db_path: Optional[str] = None) -> async_sessionmaker[AsyncSession]:
    engine = get_async_engine(db_path)
    return async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


# ---------------------------------------------------------------------------
# Original Native SQLite Functions (Retained for 100% Backward Compatibility)
# ---------------------------------------------------------------------------

def get_db_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Return a raw sqlite3 connection with Row factory."""
    path = db_path if db_path is not None else settings.DB_PATH
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Optional[str] = None) -> None:
    """Initialize SQLite tables for investigations using raw SQLite."""
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
    """Persist an investigation report via raw SQLite."""
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
    """Retrieve historical investigations list with pagination via raw SQLite."""
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
    """Retrieve full investigation report by ID via raw SQLite."""
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
    """Clear all records via raw SQLite."""
    conn = get_db_connection(db_path)
    try:
        with conn:
            conn.execute("DELETE FROM investigations")
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# SQLAlchemy 2.0 Async Storage API
# ---------------------------------------------------------------------------

async def init_db_async(db_path: Optional[str] = None) -> None:
    """Initialize database tables using SQLAlchemy async engine metadata."""
    engine = get_async_engine(db_path)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def save_investigation_async(
    report: InvestigationReport,
    created_at: Optional[str] = None,
    db_path: Optional[str] = None,
) -> None:
    """Persist an investigation report using SQLAlchemy async session."""
    timestamp = created_at or datetime.now(timezone.utc).isoformat()
    session_factory = get_async_session_maker(db_path)

    async with session_factory() as session:
        async with session.begin():
            # Check existing record
            record = await session.get(InvestigationRecord, report.investigation_id)
            if record is None:
                record = InvestigationRecord(
                    investigation_id=report.investigation_id,
                    target_name=report.target.name,
                    lat=report.target.lat,
                    lon=report.target.lon,
                    question=report.question,
                    risk_level=report.risk_level,
                    risk_score=report.risk_score,
                    confidence=report.confidence,
                    created_at=timestamp,
                    report_json=report.model_dump_json(),
                )
                session.add(record)
            else:
                record.target_name = report.target.name
                record.lat = report.target.lat
                record.lon = report.target.lon
                record.question = report.question
                record.risk_level = report.risk_level
                record.risk_score = report.risk_score
                record.confidence = report.confidence
                record.created_at = timestamp
                record.report_json = report.model_dump_json()


async def list_investigations_async(
    limit: int = 50,
    offset: int = 0,
    db_path: Optional[str] = None,
) -> InvestigationListResponse:
    """Retrieve paginated investigations using SQLAlchemy async query."""
    session_factory = get_async_session_maker(db_path)
    async with session_factory() as session:
        # Total count
        count_query = select(func.count()).select_from(InvestigationRecord)
        total_result = await session.execute(count_query)
        total = total_result.scalar_one() or 0

        # Paginated items
        items_query = (
            select(InvestigationRecord)
            .order_by(InvestigationRecord.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        items_result = await session.execute(items_query)
        records = items_result.scalars().all()

        items = [
            InvestigationSummary(
                investigation_id=r.investigation_id,
                target_name=r.target_name,
                lat=r.lat,
                lon=r.lon,
                question=r.question,
                risk_level=r.risk_level,
                risk_score=r.risk_score,
                confidence=r.confidence,
                created_at=r.created_at,
            )
            for r in records
        ]

        return InvestigationListResponse(total=total, items=items)


async def get_investigation_async(
    investigation_id: str,
    db_path: Optional[str] = None,
) -> Optional[InvestigationReport]:
    """Retrieve full investigation report using SQLAlchemy async session."""
    session_factory = get_async_session_maker(db_path)
    async with session_factory() as session:
        record = await session.get(InvestigationRecord, investigation_id)
        if record is None:
            return None
        return InvestigationReport.model_validate_json(record.report_json)


async def clear_investigations_async(db_path: Optional[str] = None) -> None:
    """Clear all investigation records using SQLAlchemy async session."""
    session_factory = get_async_session_maker(db_path)
    async with session_factory() as session:
        async with session.begin():
            await session.execute(delete(InvestigationRecord))
