#  Data / API layer 


```
External APIs → adapters → Evidence (normalized) → agent / analysis / backend / UI
```

Drop the `data/` folder (and `scripts/`, `tests/`) into the monorepo root (plan §11). Run everything from the repo root.

## Quick start

```bash
pip install -r requirements.txt
python -m pytest                                  

# no keys, no network :
TERRAWATCH_MODE=mock python -c "from data import collect_evidence; print(collect_evidence(30.0444, 31.2357)[2].for_llm())"

#  real keys  that validates the live paths:
export OPENAQ_API_KEY=... FIRMS_MAP_KEY=... GEOAPIFY_API_KEY=...
python -m scripts.live_check                       # hits the real APIs for Cairo, prints one line per source
python -m scripts.live_check --record              # + records DEMO fixtures for Cairo / LA / Tokyo → commit them
```

```python
from data import collect_evidence, geocode, get_evidence

geo = geocode("Cairo", "Egypt")                                 # Evidence(kind="geocode")
evs = collect_evidence(30.0444, 31.2357,                        # runs sources in parallel
                       sources=["weather", "air_quality", "fire"],   # default = the Day-1 MVP trio
                       params={"fire": {"radius_km": 300}})
evs[2].for_llm()                                                # compact view for the LLM
get_evidence(evs[2].evidence_id).observations                   # full rows for the analysis engine
```


## The contract — `data/schemas/models.py`

JSON Schemas for Person 4/5: `data/schemas/json/` (regenerate: `python -m scripts.export_schemas`).

```json
{
  "evidence_id": "ev_nasa_firms_e29e67993d",
  "source": "nasa_firms",
  "kind": "fire",
  "status": "ok",
  "data_mode": "mock",
  "timestamp": "2026-09-19T05:24:00Z",
  "fetched_at": "2026-09-19T12:00:05Z",
  "location": {
    "lat": 30.0444,
    "lon": 31.2357
  },
  "measurements": {
    "hotspot_count": 5,
    "radius_km": 150.0,
    "window_days": 1,
    "product": "MOCK",
    "nearest_km": 58.0,
    "total_frp_mw": 232.5,
    "max_frp_mw": 65.5,
    "high_confidence_count": 3,
    "earliest_detection": "2026-09-19T03:48:00Z",
    "latest_detection": "2026-09-19T05:24:00Z",
    "closest_fires": [
      {
        "lat": 30.4314,
        "lon": 31.6405,
        "distance_km": 58.0,
        "bearing_fire_to_location_deg": 222.2,
        "detected_at": "2026-09-19T04:00:00Z",
        "frp_mw": 65.5,
        "brightness_k": 362.0,
        "confidence": "high",
        "daynight": "D",
        "satellite": "N20"
      },
      "\u2026"
    ]
  },
  "units": {
    "distance_km": "km",
    "frp_mw": "MW",
    "brightness_k": "K",
    "bearing": "degrees (compass)"
  },
  "raw_reference": "mock://nasa_firms",
  "warnings": [],
  "error": null,
  "is_modeled": false,
  "observation_count": 5
}
```

Rules :

* **`status`**: `ok` · `no_data` · `error`. `ok` with 0 fires / 0 quakes is real evidence of absence.
  `no_data` (e.g. no air-quality station in range) is **absence of coverage — never "clean air"**.
* **`data_mode`**: `live | cache | stale_cache | demo | mock`. The UI should badge anything that isn't live/cache.
* **`is_modeled`**: `true` when values are model output (CAMS air quality fallback), not sensor readings. The agent must say so.
* **Time**: every timestamp is UTC `…Z`. Distances are km.
* **Wind**: `wind_direction_deg` is meteorological — the direction the wind blows **FROM** (matches `is_location_downwind`).
* **Fire bearing**: `bearing_fire_to_location_deg` is the compass bearing from the fire *toward* the location.
* **`measurements`** = compact summary for the LLM. **`observations`** = every row for analysis (hourly weather, PM2.5
  history, all hotspots/quakes/places). `for_llm()` strips `observations`; fetch them with `get_evidence(evidence_id)`.
* **`evidence_id`** is a content hash — stable for identical data; use it as the evidence-graph node id / citation.
* Adapters **never raise**. Failures come back as `status="error"` with `error.type` ∈ `timeout, network, rate_limited, auth,
  missing_credentials, not_found, bad_request, server_error, bad_response, simulated_outage`, plus `retryable`.

## Sources

| Adapter | Upstream | Key | Cache TTL | Notes |
|---|---|---|---|---|
| `WeatherAdapter` | Open-Meteo forecast / archive | – | 30 min | current + hourly window (`hours_back`, `hours_ahead`) or `start_date`/`end_date` for history |
| `AirQualityAdapter` | OpenAQ v3 → falls back to Open-Meteo CAMS | `OPENAQ_API_KEY` | 15 min | nearest **fresh** station with PM2.5; 24 h PM2.5 history for baselines; fallback is `is_modeled=true` |
| `FireAdapter` | NASA FIRMS VIIRS | `FIRMS_MAP_KEY` | 2 h | `radius_km`, `days` (1–5); keeps detection time, FRP, confidence |
| `EarthquakeAdapter` | USGS FDSN | – | 1 h | coords + depth + distance per event |
| `GeoAdapter` | Geoapify Places (OSM-derived) | `GEOAPIFY_API_KEY` | 24 h | `categories` or presets: `population`, `critical_infrastructure`, `industrial` |
| `GeocodeAdapter` | Geoapify → Open-Meteo geocoding | optional | 7 d | resolves the "Cairo, Egypt vs Cairo, Illinois" ambiguity via the country hint |

Keys are read from env vars, then Colab secrets. They are scrubbed from every `raw_reference`, error message and log line.

## Use it from the notebook / agent

`data/tools.py` exposes the **same six tool names and signatures** the notebook planner already uses, so Person 1's swap is:

```python
import sys; sys.path.insert(0, "/content/Connected-Data-Agents")   # or wherever the repo lives
from data.tools import TOOLS, TOOLS_BY_NAME                       # replaces notebook cells 2, 6–9, 10 (adapters) and 11
```

Everything else in the orchestrator keeps working (`geocode.invoke(...)["measurements"]["tz_name"]`, `["location"]`,
`json.dumps(result)`). Tool results are the compact view; `tz_name` is accepted and ignored (UTC everywhere now).
Keep the notebook's `haversine`/`bearing` helpers only until Person 3's `analysis/spatial` replaces them.

## What changed vs. the notebook prototype 

1. **OpenAQ parsing was broken.** `/v3/locations/{id}/latest` returns only `sensorsId` + `value` (per OpenAQ's docs); the prototype
   read `m["parameter"]["name"]`, so every call errored. Pollutants are now joined through the location's `sensors` list.
2. **Demo fixtures collided.** They were saved/loaded by source name only, so the Cairo file answered for Tokyo. Now keyed by
   location (nearest recorded point within 30 km).
3. **`DEMO_MODE` was read at import**, so flipping it later did nothing. Now read per call.
4. **Analysis-critical fields were dropped**: fire detection time/FRP/confidence and earthquake lat/lon/depth. Without them
   `temporal_correlation` and `earthquake_proximity` can't exist.
5. **API keys could leak** through exception text (FIRMS puts the key in the URL path, Geoapify in the query string) into
   `raw_reference` → LLM → UI. Now redacted.
6. **One error shape.** Errors used to lack timestamp/location/measurements; now every outcome is the same envelope.
7. **Resilience**: bounded retries on 5xx, typed errors, stale-cache recovery, parser failures contained.
8. Nearest OpenAQ station could be dead or lack PM2.5 (`limit=1`); now ranked by freshness and PM2.5 availability.
9. Local-timezone timestamps → UTC, so cross-source time comparison is sound.



