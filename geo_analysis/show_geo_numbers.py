"""Explain the geographic and risk calculations from the command line."""

from __future__ import annotations
import argparse
import math
from typing import Any
from geo_analysis.risk import calculate_risk_from_spatial
from geo_analysis.spatial import calculate_bearing, haversine_distance
from geo_analysis.wind import is_downwind, wind_alignment

DEFAULTS = {
    "lat1": 30.0444,
    "lon1": 31.2357,
    "lat2": 30.4,
    "lon2": 31.8,
    "wind_direction": 180.0,
    "distance_km": 78.4,
    "proximity_score": 0.78,
    "air_quality_anomaly": 0.82,
    "temporal_correlation": 0.91,
    "downwind_tolerance": 5.0,
}

def calculate_numbers(
    *,
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
    wind_direction: float,
    distance_km: float,
    proximity_score: float,
    air_quality_anomaly: float,
    temporal_correlation: float,
    downwind_tolerance: float,
) -> dict[str, Any]:
    """Calculate all values shown by the CLI for a set of user inputs."""
    distance = haversine_distance(lat1, lon1, lat2, lon2)
    bearing = calculate_bearing(lat1, lon1, lat2, lon2)
    alignment = wind_alignment(bearing, wind_direction)
    downwind = is_downwind(
        bearing,
        wind_direction,
        tolerance_deg=downwind_tolerance,
    )
    risk_result = calculate_risk_from_spatial(
        {
            "event_id": "F001",
            "target_id": "CUSTOM_TARGET",
            "distance_km": distance_km,
            "proximity_score": proximity_score,
            "wind_alignment": alignment,
            "downwind": downwind,
        },
        air_quality_anomaly=air_quality_anomaly,
        temporal_correlation=temporal_correlation,
    )

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2.0) ** 2
    )
    computed_distance = 2 * 6371.0 * math.asin(math.sqrt(min(1.0, a)))

    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    lon_delta = math.radians(lon2 - lon1)
    x = math.sin(lon_delta) * math.cos(p2)
    y = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(lon_delta)
    computed_bearing = (math.degrees(math.atan2(x, y)) + 360.0) % 360.0
    wind_diff = abs((wind_direction - bearing + 180.0) % 360.0 - 180.0)

    return {
        "lat1": lat1,
        "lon1": lon1,
    "lat2": lat2,
    "lon2": lon2,
    "distance": distance,
    "bearing": bearing,
    "alignment": alignment,
    "downwind": downwind,
    "a": a,
    "computed_distance": computed_distance,
    "computed_bearing": computed_bearing,
    "wind_diff": wind_diff,
    "wind_direction": wind_direction,
    "downwind_tolerance": downwind_tolerance,
    "distance_km": distance_km,
    "proximity_score": proximity_score,
    "air_quality_anomaly": air_quality_anomaly,
        "temporal_correlation": temporal_correlation,
        "risk": risk_result["risk_score"],
    }

def print_report(values: dict[str, Any]) -> None:
    """Print the calculation explanation for the supplied values."""
    print("=== Why these numbers came out this way ===")
    print()
    print("Sample points:")
    print(f"   A = ({values['lat1']}, {values['lon1']})")
    print(f"   B = ({values['lat2']}, {values['lon2']})")
    print()
    print("Distance formula:")
    print("   a = sin^2(dlat/2) + cos(lat1)*cos(lat2)*sin^2(dlon/2)")
    print("   distance = 2 * R * asin(sqrt(a))")
    print(f"   computed a = {values['a']:.12f}")
    print(f"   computed distance = {values['computed_distance']:.4f} km")
    print(f"   returned distance = {values['distance']:.4f} km")
    print()
    print("Bearing formula:")
    print("   x = sin(dlon) * cos(lat2)")
    print("   y = cos(lat1) * sin(lat2) - sin(lat1) * cos(lat2) * cos(dlon)")
    print("   bearing = (atan2(x, y) + 360) % 360")
    print(f"   computed bearing = {values['computed_bearing']:.4f}°")
    print(f"   returned bearing = {values['bearing']:.4f}°")
    print()
    print("Wind alignment formula:")
    print("   diff = abs((wind_dir - target_bearing + 180) % 360 - 180)")
    print("   alignment = 1 - diff / 180")
    print(f"   diff = {values['wind_diff']:.4f}°")
    print(f"   raw alignment = {1.0 - values['wind_diff'] / 180.0:.4f}")
    print(f"   normalized alignment = {values['alignment']:.4f}")
    print()
    print("Downwind check:")
    print("   is_downwind = diff <= tolerance")
    print(f"   diff = {values['wind_diff']:.4f}°")
    print(f"   tolerance = {values['downwind_tolerance']}°")
    print(f"   downwind = {values['downwind']}")
    print()
    print("Risk formula:")
    print("   risk = 0.25 * proximity + 0.30 * wind + 0.25 * air_quality + 0.20 * temporal")
    print(
        "   = 0.25*{0} + 0.30*{1:.4f} + 0.25*{2} + 0.20*{3}".format(
            values["proximity_score"],
            values["alignment"],
            values["air_quality_anomaly"],
            values["temporal_correlation"],
        )
    )
    print(f"   returned risk = {values['risk']:.4f}")
    print()
    print("Final output:")
    print(
        {
            "distance_km": round(values["distance"], 4),
            "bearing_deg": round(values["bearing"], 4),
            "wind_alignment": round(values["alignment"], 4),
            "downwind": values["downwind"],
            "risk_score": round(values["risk"], 4),
        }
    )


def _finite_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise argparse.ArgumentTypeError("must be a finite number")
    return parsed

def _prompt_float(label: str, default: float) -> float:
    while True:
        raw_value = input(f"{label} [{default}]: ").strip()
        if not raw_value:
            return default
        try:
            return _finite_float(raw_value)
        except (argparse.ArgumentTypeError, ValueError):
            print("Please enter a finite number.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Explain TerraWatch geographic and risk calculations."
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="prompt for calculation values in the terminal",
    )
    for name, default in DEFAULTS.items():
        parser.add_argument(
            f"--{name.replace('_', '-')}",
            type=_finite_float,
            default=None,
            metavar="NUMBER",
            help=f"override {name} (default: {default})",
        )
    return parser


def _values_from_args(args: argparse.Namespace) -> dict[str, float]:
    values = {
        name: getattr(args, name) if getattr(args, name) is not None else default
        for name, default in DEFAULTS.items()
    }
    if args.interactive:
        values = {
            name: _prompt_float(name.replace("_", " ").title(), value)
            for name, value in values.items()
        }
    return values


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    print_report(calculate_numbers(**_values_from_args(args)))


if __name__ == "__main__":
    main()

