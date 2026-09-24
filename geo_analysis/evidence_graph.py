"""Evidence graph"".

The graph is intentionally dependency-free. It produces a JSON-serializable
dictionary containing nodes and relationships, so the backend/LLM/UI can
consume it without needing a graph database for the MVP.

Node IDs should be stable and meaningful when possible:
    fire:F001
    city:CAIRO
    wind:W001
    air_quality:AQ001
"""

from __future__ import annotations

from typing import Any, Mapping, Optional


def create_evidence_graph() -> dict[str, list[dict[str, Any]]]:
    """Create an empty evidence graph."""
    return {
        "nodes": [],
        "relationships": [],
    }


def add_node(
    graph: dict[str, list[dict[str, Any]]],
    *,
    node_id: str,
    node_type: str,
    properties: Optional[Mapping[str, Any]] = None,
) -> dict[str, list[dict[str, Any]]]:
    """Add or replace a node by ID."""
    if not node_id:
        raise ValueError("node_id is required")
    if not node_type:
        raise ValueError("node_type is required")

    graph["nodes"] = [
        node for node in graph["nodes"] if node["id"] != node_id
    ]

    graph["nodes"].append({
        "id": node_id,
        "type": node_type,
        "properties": dict(properties or {}),
    })
    return graph


def add_relationship(
    graph: dict[str, list[dict[str, Any]]],
    *,
    source_id: str,
    relationship: str,
    target_id: str,
    properties: Optional[Mapping[str, Any]] = None,
) -> dict[str, list[dict[str, Any]]]:
    """Add a directed relationship between two nodes.

    Example:
        fire:F001 -- 78.4_km --> city:CAIRO
    """
    if not source_id or not target_id:
        raise ValueError("source_id and target_id are required")
    if not relationship:
        raise ValueError("relationship is required")

    graph["relationships"].append({
        "source": source_id,
        "type": relationship,
        "target": target_id,
        "properties": dict(properties or {}),
    })
    return graph


def build_incident_graph(
    spatial_evidence: Mapping[str, Any],
    *,
    risk_result: Optional[Mapping[str, Any]] = None,
    fire: Optional[Mapping[str, Any]] = None,
    target: Optional[Mapping[str, Any]] = None,
    wind: Optional[Mapping[str, Any]] = None,
    air_quality: Optional[Mapping[str, Any]] = None,
    temporal: Optional[Mapping[str, Any]] = None,
) -> dict[str, list[dict[str, Any]]]:
    """Build a small evidence graph from one incident.

    `spatial_evidence` is the contract produced by Person 3A.
    Other arguments are optional because each source may be available at a
    different stage of the pipeline.
    """
    graph = create_evidence_graph()

    event_id = str(spatial_evidence.get("event_id", "unknown_event"))
    target_id = str(spatial_evidence.get("target_id", "unknown_target"))

    fire_id = f"fire:{event_id}"
    target_node_id = f"target:{target_id}"

    add_node(
        graph,
        node_id=fire_id,
        node_type="fire",
        properties=dict(fire or {"event_id": event_id}),
    )
    add_node(
        graph,
        node_id=target_node_id,
        node_type="target",
        properties=dict(target or {"target_id": target_id}),
    )

    add_relationship(
        graph,
        source_id=fire_id,
        relationship="NEAR",
        target_id=target_node_id,
        properties={
            "distance_km": spatial_evidence.get("distance_km"),
            "proximity_score": spatial_evidence.get("proximity_score"),
        },
    )

    if spatial_evidence.get("downwind") is not None or spatial_evidence.get("wind_alignment") is not None:
        wind_id = f"wind:{event_id}"
        add_node(graph, node_id=wind_id, node_type="wind", properties=dict(wind or {}))
        add_relationship(
            graph,
            source_id=wind_id,
            relationship="SUPPORTS_DOWNWIND",
            target_id=target_node_id,
            properties={
                "alignment": spatial_evidence.get("wind_alignment"),
                "downwind": spatial_evidence.get("downwind"),
            },
        )

    if air_quality is not None:
        aq_id = f"air_quality:{event_id}"
        add_node(graph, node_id=aq_id, node_type="air_quality", properties=dict(air_quality))
        add_relationship(
            graph,
            source_id=fire_id,
            relationship="ASSOCIATED_WITH",
            target_id=aq_id,
            properties={
                "anomaly": air_quality.get("anomaly"),
                "anomaly_score": air_quality.get("anomaly_score"),
            },
        )

    if temporal is not None:
        temporal_id = f"temporal:{event_id}"
        add_node(graph, node_id=temporal_id, node_type="temporal_evidence", properties=dict(temporal))
        add_relationship(
            graph,
            source_id=fire_id,
            relationship="TEMPORALLY_ASSOCIATED",
            target_id=temporal_id,
            properties={
                "correlation_score": temporal.get("correlation_score"),
                "delay_hours": temporal.get("delay_hours"),
            },
        )

    if risk_result is not None:
        risk_id = f"risk:{event_id}"
        add_node(graph, node_id=risk_id, node_type="risk", properties=dict(risk_result))
        add_relationship(
            graph,
            source_id=fire_id,
            relationship="HAS_RISK",
            target_id=risk_id,
            properties={
                "risk_score": risk_result.get("risk_score"),
            },
        )

    return graph
