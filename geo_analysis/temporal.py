"""Temporal analysis"".

This module answers: WHEN did related events happen, and how strongly do
their timestamps support a relationship?

All timestamps are expected to be UTC ISO-8601 strings, preferably ending in Z.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable, Mapping, Optional, Sequence


def _parse_time(value: Any) -> datetime:
    """Convert an ISO timestamp / datetime into a timezone-aware UTC datetime."""
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).strip().replace("Z", "+00:00")
        dt = datetime.fromisoformat(text)

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(timezone.utc)


def time_difference(
    earlier: Any,
    later: Any,
    *,
    unit: str = "hours",
) -> float:
    """Return the absolute time difference between two timestamps.

    Parameters
    ----------
    earlier, later:
        ISO-8601 timestamps or datetime objects.
    unit:
        "seconds", "minutes", or "hours".

    The function does not assume that the first timestamp is actually earlier;
    it returns the absolute difference.
    """
    seconds = abs((_parse_time(later) - _parse_time(earlier)).total_seconds())

    if unit == "seconds":
        return seconds
    if unit == "minutes":
        return seconds / 60.0
    if unit == "hours":
        return seconds / 3600.0

    raise ValueError("unit must be 'seconds', 'minutes', or 'hours'")


def find_events_in_window(
    events: Iterable[Mapping[str, Any]],
    center_time: Any,
    window_hours: float,
    *,
    time_key: str = "time",
) -> list[dict[str, Any]]:
    """Return events whose timestamps are within +/- window_hours of center_time.

    Events without a valid timestamp are ignored.
    """
    center = _parse_time(center_time)
    window_seconds = window_hours * 3600.0
    result: list[dict[str, Any]] = []

    for event in events:
        value = event.get(time_key)
        if value is None:
            continue

        try:
            event_time = _parse_time(value)
        except (TypeError, ValueError):
            continue

        if abs((event_time - center).total_seconds()) <= window_seconds:
            result.append(dict(event))

    result.sort(key=lambda item: _parse_time(item[time_key]))
    return result


def temporal_correlation(
    source_time: Any,
    target_time: Any,
    *,
    expected_delay_hours: float = 0.0,
    tolerance_hours: float = 6.0,
) -> float:
    """Score how well two events match an expected temporal relationship.

    Score:
        1.0 -> exact expected delay
        0.0 -> outside the tolerance window

    Example:
        Fire at 12:00, PM2.5 at 14:00, expected delay=2h, tolerance=6h
        -> score = 1.0

    This is a simple evidence score, not a causal claim.
    """
    if tolerance_hours <= 0:
        raise ValueError("tolerance_hours must be > 0")
    if expected_delay_hours < 0:
        raise ValueError("expected_delay_hours must be >= 0")

    actual_delay = (
        _parse_time(target_time) - _parse_time(source_time)
    ).total_seconds() / 3600.0

    error = abs(actual_delay - expected_delay_hours)
    score = 1.0 - (error / tolerance_hours)
    return round(max(0.0, min(1.0, score)), 4)
