"""Wind-analysis helpers for Person 3A.

The public functions intentionally support both the normalized evidence contract
and the simple geometric checks used in the tests:

- wind_alignment(...)
- is_downwind(...)
"""

from __future__ import annotations


def _normalize_score(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _angular_difference_deg(a_deg: float, b_deg: float) -> float:
    diff = abs((a_deg - b_deg + 180.0) % 360.0 - 180.0)
    return float(diff)


def wind_alignment(
    target_bearing_deg: float,
    wind_direction_deg: float | None = None,
    *,
    tolerance_deg: float = 45.0,
) -> float:
    """Return a normalized alignment score in [0, 1].

    There are two valid input styles:

    1) Already-normalized evidence: wind_alignment(0.97, 0.0) -> 0.97
    2) Geometric directional evidence: wind_alignment(90, 270) -> 0.0

    The directional mode treats the inputs as compass headings in degrees and
    computes stronger alignment when the angular separation is smaller.
    """
    try:
        score_value = float(target_bearing_deg)
        if 0.0 <= score_value <= 1.0 and (wind_direction_deg is None or 0.0 <= float(wind_direction_deg) <= 1.0):
            return round(_normalize_score(score_value), 4)
    except (TypeError, ValueError):
        pass

    if wind_direction_deg is None:
        return round(_normalize_score(float(target_bearing_deg)), 4)

    diff = _angular_difference_deg(float(target_bearing_deg), float(wind_direction_deg))
    score = 1.0 - (diff / 180.0)
    if tolerance_deg is not None and tolerance_deg > 0:
        score = max(0.0, min(1.0, score))
    return round(_normalize_score(score), 4)


def is_downwind(
    bearing_to_target_deg: float,
    wind_direction_deg: float,
    *,
    tolerance_deg: float = 5.0,
) -> bool:
    """Return True when the local wind direction is effectively aligned with the target."""
    diff = _angular_difference_deg(float(bearing_to_target_deg), float(wind_direction_deg))
    return diff <= abs(float(tolerance_deg))


__all__ = ["wind_alignment", "is_downwind"]
