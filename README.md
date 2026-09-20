# TerraWatch — Data / API layer (Person 2)

Turns five fragmented external APIs into **one normalized `Evidence` object** that the agent,
analysis engine, backend and UI can all rely on. Nobody downstream ever sees an Open-Meteo, OpenAQ,
FIRMS, USGS or Geoapify response format.

```
External APIs → adapters → Evidence (normalized) → agent / analysis / backend / UI
```

Drop the `data/` folder (and `scripts/`, `tests/`) into the monorepo root (plan §11). Run everything from the repo root.

## Quick start

```bash
pip install -r requirements.txt
python -m pytest                                   # 39 tests, no network / keys needed

# no keys, no network — deterministic synthetic incident for building against:
TERRAWATCH_MODE=mock python -c "from data import collect_evidence; print(collect_evidence(30.0444, 31.2357)[2].for_llm())"

# with real keys — do this FIRST, it's the only thing that validates the live paths:
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

## Modes — `TERRAWATCH_MODE`

| Mode | Behaviour | Use for |
|---|---|---|
| `live` (default) | fresh cache → real API → **stale cache if the API fails** (flagged) | development with keys, real runs |
| `demo` | replays **recorded** fixtures, never touches the network. No fixture nearby → labelled synthetic data | the judging demo |
| `mock` | deterministic synthetic incident (fire upwind → wind shift → PM2.5 rise) | building UI/analysis, tests, CI |

`DEMO_MODE=true` (the notebook's old flag) still works. `TERRAWATCH_SIMULATE_FAILURES=fire,openaq` (or `all`)
forces outages in any mode — this *is* Person 6's "API failure / incomplete-data" scenario.

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

Rules everyone should code against:

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

## What changed vs. the notebook prototype (and why)

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

## Not verified — read before the demo

* **These adapters have not touched the live APIs.** The build sandbox blocks those hosts (`scripts.live_check` shows the
  failure path working, nothing more). Tests feed each adapter responses shaped like the documented formats. Run
  `python -m scripts.live_check` with real keys before anything else; fix any drift in the matching `adapter.py`.
* Least certain spots: OpenAQ `/sensors/{id}/hours` params (failure only drops PM2.5 history, with a warning) · Geoapify
  category names in `PRESETS` and the `format=json` geocode shape · FIRMS' switch to `VIIRS_SNPP_SP` for dates older than 60 days ·
  Open-Meteo archive-vs-forecast cutoff for historical weather.
* Gas units come straight from the OpenAQ sensor (some report ppm, others µg/m³) — **no conversion** is done.
* OpenAQ has no historical query yet (latest + 24 h PM2.5 history only). Historical scenarios are covered for weather, fire
  and earthquakes.
* The cache is per-process (diskcache). If Person 4 runs several API workers, point `TERRAWATCH_CACHE_DIR` at a shared
  volume or swap `ResponseCache` for Redis (one small class in `data/core/cache.py`).

## Hand-offs

| Who | What they need from this layer |
|---|---|
| **1 Agent** | Swap in `data.tools`. Branch on `status` / `error.retryable`; never treat `no_data` as safe; mention `is_modeled` and `data_mode` in reports. |
| **3 Analysis** | `get_evidence(id).observations` for full rows. PM2.5 baseline = `air_quality` observations; wind series = `weather` observations; fire rows carry `bearing_fire_to_location_deg`. Agree on one haversine/bearing implementation (`data/core/geo.py` mirrors the notebook's). |
| **4 Backend** | Call `collect_evidence()`; serialise with `model_dump(mode="json")`; types from `data/schemas/json/`. Env vars: `TERRAWATCH_MODE`, `TERRAWATCH_CACHE_DIR`, `TERRAWATCH_FIXTURES_DIR`, the three API keys. |
| **5 Frontend** | Badge `data_mode` (DEMO / MOCK / STALE) and `is_modeled`; render `warnings`; link `raw_reference` as the source reference; `evidence_id` = graph node id. |
| **6 QA / Demo** | `TERRAWATCH_SIMULATE_FAILURES` for scenario 10; `--record` before the demo; `mock` incident is internally consistent (see `tests/test_mock_scenario.py`) for eval fixtures. |

## Adding a source (e.g. a volcano feed)

Subclass `BaseAdapter` in `data/adapters/<name>/adapter.py`: set `source`, `kind`, `defaults`, `ttl_seconds`; implement `_fetch_live`
(use `data.core.http`, return `Fetched(...)`) and `_fetch_mock`; add a Pydantic measurements model in `schemas/models.py`; register it in
`registry.py` and `tools.py`. Mode switching, caching, stale recovery, error envelopes, evidence ids and fixtures come for free.

## Layout

```
data/
  adapters/{openmeteo,openaq,firms,usgs,osm}/adapter.py   one folder per source (plan §11); base.py = shared behaviour
  core/        http (retries, typed errors, redaction) · cache (TTL + stale) · fixtures · geo · mock_scenario · timeutil
  schemas/     models.py (Pydantic) + json/ (exported JSON Schemas)
  registry.py  collect_evidence(), geocode()          tools.py  LangChain wrappers          store.py  evidence store
scripts/       live_check.py (--record) · export_schemas.py
tests/         39 tests: live parsing, reliability, mock-scenario physics
```
