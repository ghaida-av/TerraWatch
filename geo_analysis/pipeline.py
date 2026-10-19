"""Pipeline bridge connecting data/ Evidence to deterministic geo_analysis.

This module consumes normalized `data.schemas.models.Evidence` objects, runs
spatial, wind, air quality, and temporal correlations, and outputs a deterministic
RiskAssessment and EvidenceGraph without involving any LLM.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence
from datetime import datetime, timezone

from data.schemas.models import Evidence
from geo_analysis.spatial_and_wind import (
    calculate_bearing,
    haversine_distance,
    is_downwind,
    wind_alignment,
)
from geo_analysis.temporal import temporal_correlation
from geo_analysis.risk import (
    air_quality_anomaly_score,
    calculate_risk,
    fire_proximity_score,
    temporal_correlation_score,
    wind_alignment_score,
)
from geo_analysis.evidence_graph import (
    add_node,
    add_relationship,
    create_evidence_graph,
)


def _risk_level(score: float) -> str:
    if score >= 0.70:
        return "CRITICAL"
    if score >= 0.50:
        return "HIGH"
    if score >= 0.25:
        return "MODERATE"
    return "LOW"


def analyze_evidence(
    evidence_list: Sequence[Evidence],
    *,
    target_name: Optional[str] = None,
    target_lat: Optional[float] = None,
    target_lon: Optional[float] = None,
) -> Dict[str, Any]:
    """Ingests normalized Evidence items from data layer and computes deterministic risk metrics.

    Returns a structured dictionary with:
      - target: {name, lat, lon}
      - risk_score: float (0.0 to 1.0)
      - risk_level: LOW | MODERATE | HIGH | CRITICAL
      - components: {proximity, wind_alignment, air_quality_anomaly, temporal_correlation}
      - primary_signals: key findings from spatial/wind analysis
      - evidence_graph: nodes & relationships graph
      - evidence_ids: list of source evidence IDs used
    """
    by_kind: Dict[str, Evidence] = {}
    for ev in evidence_list:
        by_kind[ev.kind] = ev

    # 1. Resolve Target Coordinates & Name
    resolved_name = target_name or "Target Location"
    lat = target_lat
    lon = target_lon

    if "geocode" in by_kind and by_kind["geocode"].location:
        g = by_kind["geocode"]
        lat = g.location.lat
        lon = g.location.lon
        resolved_name = g.measurements.get("matched_name") or resolved_name
    elif lat is None or lon is None:
        for ev in evidence_list:
            if ev.location:
                lat = ev.location.lat
                lon = ev.location.lon
                break

    lat = lat if lat is not None else 0.0
    lon = lon if lon is not None else 0.0

    target_info = {"name": resolved_name, "lat": round(lat, 4), "lon": round(lon, 4)}

    # 2. Weather & Wind Processing
    weather_ev = by_kind.get("weather")
    wind_speed_kmh = 0.0
    wind_dir_from_deg = 0.0
    current_temp_c = None

    if weather_ev and weather_ev.status == "ok":
        current_w = weather_ev.measurements.get("current") or {}
        wind_speed_kmh = float(current_w.get("wind_speed_kmh") or 0.0)
        wind_dir_from_deg = float(current_w.get("wind_direction_deg") or 0.0)
        current_temp_c = current_w.get("temperature_c")

    # 3. Fire & Spatial Processing
    fire_ev = by_kind.get("fire")
    primary_fire = None
    fire_distance_km = 999.0
    proximity = 0.0
    bearing_fire_to_target = 0.0
    alignment = 0.0
    downwind = False
    fire_count = 0

    if fire_ev and fire_ev.status == "ok":
        fire_count = fire_ev.measurements.get("hotspot_count", 0)
        closest_fires = fire_ev.measurements.get("closest_fires", [])
        if closest_fires:
            primary_fire = closest_fires[0]
            fire_distance_km = float(primary_fire.get("distance_km", 999.0))
            bearing_fire_to_target = float(
                primary_fire.get("bearing_fire_to_location_deg")
                or calculate_bearing(primary_fire["lat"], primary_fire["lon"], lat, lon)
            )
            proximity = fire_proximity_score(fire_distance_km, max_distance_km=150.0)
            # Weather APIs report the direction the wind blows FROM (meteorological convention), but smoke
            # travels TO the opposite side. Compare the fire->target bearing with the direction of travel,
            # otherwise upwind and downwind are swapped.
            wind_to_deg = (wind_dir_from_deg + 180.0) % 360.0
            alignment = wind_alignment(bearing_fire_to_target, wind_to_deg)
            downwind = is_downwind(bearing_fire_to_target, wind_to_deg, tolerance_deg=35.0)

    # 4. Air Quality & Anomaly Processing
    aq_ev = by_kind.get("air_quality")
    pm25_val = None
    aq_anomaly = 0.0

    if aq_ev and aq_ev.status == "ok":
        pm25_val = aq_ev.measurements.get("pm25")
        if pm25_val is not None:
            pm25_val = float(pm25_val)
            # Baseline from observations if available
            history = [
                float(obs["pm25"])
                for obs in aq_ev.observations
                if obs.get("pm25") is not None
            ]
            if len(history) > 1:
                baseline = sum(history[:-1]) / len(history[:-1])
                if baseline > 0:
                    aq_anomaly = max(0.0, (pm25_val - baseline) / baseline)
            else:
                # Fallback to WHO 24h standard benchmark (15.0 ug/m3)
                aq_anomaly = max(0.0, (pm25_val - 15.0) / 15.0)

    aq_score = air_quality_anomaly_score(aq_anomaly, anomaly_cap=3.0)

    # 5. Temporal Correlation
    temporal_score = 0.0
    if primary_fire and aq_ev and primary_fire.get("detected_at") and aq_ev.timestamp:
        try:
            temporal_score = temporal_correlation(
                primary_fire["detected_at"],
                aq_ev.timestamp,
                expected_delay_hours=2.0,
                tolerance_hours=8.0,
            )
        except Exception:
            temporal_score = 0.0

    # 6. Combined Deterministic Risk
    final_risk = calculate_risk(
        proximity_score=proximity,
        wind_alignment=alignment if fire_count > 0 else 0.0,
        air_quality_anomaly=aq_score,
        temporal_correlation=temporal_score if fire_count > 0 else 0.0,
    )

    # 7. Evidence Graph Construction
    graph = create_evidence_graph()
    target_node_id = f"target:{resolved_name.lower().replace(' ', '_')}"
    add_node(
        graph,
        node_id=target_node_id,
        node_type="location",
        properties=target_info,
    )

    if weather_ev:
        weather_node_id = f"weather:{weather_ev.evidence_id}"
        add_node(
            graph,
            node_id=weather_node_id,
            node_type="weather",
            properties={
                "wind_speed_kmh": wind_speed_kmh,
                "wind_direction_deg": wind_dir_from_deg,
                "temperature_c": current_temp_c,
            },
        )
        add_relationship(
            graph,
            source_id=weather_node_id,
            relationship="WINDS_AT",
            target_id=target_node_id,
            properties={"wind_dir_deg": wind_dir_from_deg, "wind_speed_kmh": wind_speed_kmh},
        )

    if primary_fire:
        fire_node_id = f"fire:{primary_fire.get('detected_at', 'event')}"
        add_node(
            graph,
            node_id=fire_node_id,
            node_type="fire_cluster",
            properties={
                "distance_km": round(fire_distance_km, 2),
                "frp_mw": primary_fire.get("frp_mw"),
                "detected_at": primary_fire.get("detected_at"),
            },
        )
        add_relationship(
            graph,
            source_id=fire_node_id,
            relationship="THREATENS_LOCATION",
            target_id=target_node_id,
            properties={
                "distance_km": round(fire_distance_km, 2),
                "bearing_deg": round(bearing_fire_to_target, 2),
                "downwind": downwind,
            },
        )

    if aq_ev and pm25_val is not None:
        aq_node_id = f"air_quality:{aq_ev.evidence_id}"
        add_node(
            graph,
            node_id=aq_node_id,
            node_type="air_quality_station",
            properties={
                "pm25": pm25_val,
                "anomaly_ratio": round(aq_anomaly, 2),
                "is_modeled": aq_ev.is_modeled,
            },
        )
        add_relationship(
            graph,
            source_id=aq_node_id,
            relationship="MEASURES_EXPOSURE_AT",
            target_id=target_node_id,
            properties={"pm25": pm25_val, "anomaly": round(aq_anomaly, 2)},
        )

    earthquake_ev = by_kind.get("earthquake")
    if earthquake_ev and earthquake_ev.status == "ok":
        eq_count = earthquake_ev.measurements.get("event_count", 0)
        if eq_count > 0:
            eq_node_id = f"earthquake:{earthquake_ev.evidence_id}"
            add_node(
                graph,
                node_id=eq_node_id,
                node_type="seismic_events",
                properties={
                    "event_count": eq_count,
                    "max_magnitude": earthquake_ev.measurements.get("max_magnitude"),
                    "nearest_km": earthquake_ev.measurements.get("nearest_km"),
                },
            )
            add_relationship(
                graph,
                source_id=eq_node_id,
                relationship="SEISMIC_ACTIVITY_NEAR",
                target_id=target_node_id,
                properties={"nearest_km": earthquake_ev.measurements.get("nearest_km")},
            )

    return {
        "target": target_info,
        "risk_score": final_risk,
        "risk_level": _risk_level(final_risk),
        "components": {
            "proximity": proximity,
            "wind_alignment": alignment,
            "air_quality_anomaly": aq_score,
            "temporal_correlation": temporal_score,
        },
        "signals": {
            "fire_count": fire_count,
            "nearest_fire_km": round(fire_distance_km, 2) if fire_count > 0 else None,
            "is_downwind_of_fire": downwind,
            "wind_speed_kmh": wind_speed_kmh,
            "wind_direction_deg": wind_dir_from_deg,
            "pm25_ug_m3": pm25_val,
            "pm25_anomaly_ratio": round(aq_anomaly, 2),
        },
        "evidence_graph": graph,
        "evidence_ids_used": [ev.evidence_id for ev in evidence_list],
    }
