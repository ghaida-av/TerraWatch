"""All TerraWatch timestamps are UTC ISO-8601 with a trailing Z."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def to_utc_iso(value: Any) -> Optional[str]:
    """Accepts ISO strings (naive => UTC), datetimes, or epoch milliseconds."""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        dt = datetime.fromtimestamp(value / 1000.0, tz=timezone.utc)
    elif isinstance(value, datetime):
        dt = value
    else:
        s = str(value).strip().replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
