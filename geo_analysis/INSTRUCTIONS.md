# Person 3B — Temporal + Risk + Evidence

This package contains **only Person 3B's work**.

## 1. Your responsibility

You handle three things:

1. **Temporal analysis** — understand WHEN events happen relative to each other.
2. **Risk scoring** — combine normalized evidence from Person 3A + air quality + temporal evidence.
3. **Evidence graph** — turn the results into structured nodes and relationships.

You do **not** recalculate geographic distance or wind direction.

---

## 2. Files

```text
geo_analysis/
├── temporal.py          # WHEN things happened
├── risk.py              # combine evidence into risk score
├── evidence_graph.py    # build the final evidence graph
└── __init__.py
```

`models.py` is intentionally NOT included because it is a shared/team file.

---

## 3. Person 3A → Person 3B interface

Person 3A should give you a dictionary like:

```python
spatial_evidence = {
    "event_id": "F001",
    "target_id": "CITY_CAIRO",
    "distance_km": 78.4,
    "proximity_score": 0.78,
    "wind_alignment": 0.97,
    "downwind": True,
}
```

You don't need to know how they calculated these values.

Then:

```python
from geo_analysis.risk import calculate_risk_from_spatial

result = calculate_risk_from_spatial(
    spatial_evidence,
    air_quality_anomaly=0.82,
    temporal_correlation=0.91,
)

print(result)
```

Expected shape:

```python
{
    "event_id": "F001",
    "target_id": "CITY_CAIRO",
    "risk_score": 0.86,
    "components": {
        "proximity": 0.78,
        "wind_alignment": 0.97,
        "air_quality_anomaly": 0.82,
        "temporal_correlation": 0.91
    }
}
```

The exact score depends on the configured weights.

---

## 4. Temporal analysis

### `time_difference()`

Use it when you simply need to know how far apart two events are.

```python
time_difference(
    "2026-09-21T12:00:00Z",
    "2026-09-21T14:00:00Z",
)
```

Result:

```text
2.0 hours
```

You can also request `"minutes"` or `"seconds"`.

### `find_events_in_window()`

Use it to find events around a specific time.

Example:

```python
events = [
    {"id": "fire", "time": "2026-09-21T12:00:00Z"},
    {"id": "wind", "time": "2026-09-21T13:00:00Z"},
    {"id": "pm25", "time": "2026-09-21T14:00:00Z"},
]

find_events_in_window(
    events,
    "2026-09-21T13:00:00Z",
    window_hours=2,
)
```

This returns events between 11:00 and 15:00 UTC.

### `temporal_correlation()`

This produces a normalized evidence score from 0 to 1.

Example:

```python
temporal_correlation(
    "2026-09-21T12:00:00Z",  # fire
    "2026-09-21T14:00:00Z",  # PM2.5
    expected_delay_hours=2,
    tolerance_hours=6,
)
```

Result:

```text
1.0
```

Important: this is a **temporal association score**, not proof that the fire caused the PM2.5 increase.

---

## 5. Air-quality anomaly

The expected calculation is:

```text
anomaly = (observed - baseline) / baseline
```

Example:

```text
baseline = 20
observed = 60

anomaly = (60 - 20) / 20
        = 2.0
```

Then convert it into the normalized score used by risk:

```python
from geo_analysis.risk import air_quality_anomaly_score

score = air_quality_anomaly_score(2.0)
```

With the default cap of `3.0`, this gives:

```text
0.6667
```

The cap prevents one extreme measurement from dominating the complete risk score.

---

## 6. Risk score

Default weights are:

```text
Fire proximity       25%
Wind alignment       30%
Air-quality anomaly  25%
Temporal evidence    20%
```

So conceptually:

```text
Risk =
    0.25 × proximity
  + 0.30 × wind
  + 0.25 × air quality
  + 0.20 × temporal
```

Every input must be between `0` and `1`.

### Why normalize?

Because the raw values have different units:

```text
distance = km
wind alignment = 0..1
PM2.5 anomaly = ratio
time correlation = 0..1
```

You cannot safely add those raw values together.

So first convert everything into comparable evidence scores from `0` to `1`.

---

## 7. Evidence graph

The graph is a simple JSON-serializable Python dictionary.

Example:

```python
from geo_analysis.evidence_graph import create_evidence_graph

graph = create_evidence_graph()
```

It starts as:

```python
{
    "nodes": [],
    "relationships": []
}
```

Add a node:

```python
from geo_analysis.evidence_graph import add_node

add_node(
    graph,
    node_id="fire:F001",
    node_type="fire",
    properties={"event_id": "F001"},
)
```

Add a relationship:

```python
from geo_analysis.evidence_graph import add_relationship

add_relationship(
    graph,
    source_id="fire:F001",
    relationship="NEAR",
    target_id="target:CITY_CAIRO",
    properties={"distance_km": 78.4},
)
```

Conceptually:

```text
Fire F001
   |
   | 78.4 km
   ↓
Cairo
```

---

## 8. Build the complete incident graph

Once the other evidence is available:

```python
from geo_analysis.evidence_graph import build_incident_graph

graph = build_incident_graph(
    spatial_evidence,
    risk_result=risk_result,
    fire={"detected_at": "2026-09-21T12:00:00Z"},
    target={"name": "Cairo"},
    wind={"direction_deg": 85, "speed_kmh": 24},
    air_quality={
        "anomaly": 2.0,
        "anomaly_score": 0.6667,
    },
    temporal={
        "delay_hours": 2.0,
        "correlation_score": 0.91,
    },
)
```

The resulting graph contains nodes such as:

```text
fire:F001
target:CITY_CAIRO
wind:F001
air_quality:F001
temporal:F001
risk:F001
```

and relationships connecting them.

---

## 9. Important project rule

Do not put business logic from Person 3A into these files.

For example, **do not** calculate:

```text
haversine distance
bearing
wind direction
nearest city
nearest station
downwind geometry
```

Person 3A owns those calculations.

Your code consumes their normalized result.

That separation lets both of you work independently.

---

## 10. Suggested workflow

Work in:

```text
feature/temporal-risk
```

First implement/test:

```text
temporal.py
```

Then:

```text
risk.py
```

Then connect everything through:

```text
evidence_graph.py
```

The most important contract is the Person 3A dictionary:

```python
{
    "event_id": "...",
    "target_id": "...",
    "distance_km": ...,
    "proximity_score": ...,
    "wind_alignment": ...,
    "downwind": ...
}
```

Once that contract is stable, your work can proceed without waiting for Person 3A's internal implementation.
