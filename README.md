# TerraWatch 🌍🛰️

**Autonomous Environmental Crisis Intelligence Platform** — built for the **Connected Data Agents** track.

TerraWatch breaks data silos across satellite imagery, meteorological models, and in-situ ground sensors. It connects fragmented environmental signals, computes deterministic geospatial risk correlations outside the LLM, and serves grounded crisis intelligence via a FastAPI backend and agent CLI.

```
External APIs (NASA FIRMS, OpenAQ, Open-Meteo, USGS, OSM)
                     │
                     ▼
       Normalized Evidence Envelopes (data/)
                     │
                     ▼
  Deterministic Spatial & Vector Math (geo_analysis/)
  • Proximity • Wind Alignment • PM2.5 Anomaly • Temporal Delta
                     │
                     ▼
       Evidence Graph & Citations Engine
                     │
                     ▼
    Grounded LLM Reasoner & Synthesis (agent/)
                     │
                     ▼
        FastAPI REST API (apps/api/)
                     │
                     ▼
         Web Console UI (apps/web/)
```

---

## Core Architecture Principles

1. **Deterministic Analysis First**: Raw data never goes straight to an LLM. Python engines compute exact distances, wind transport bearings, and anomaly ratios first. The LLM explains and synthesizes; Python calculates.
2. **Unified Evidence Contract**: Every adapter outputs a normalized `Evidence` envelope with UTC timestamps (`…Z`), metric units, and content-hash IDs (`evidence_id`).
3. **Resilience & Zero Crashes**: Adapters never raise uncaught exceptions. Outages return structured error envelopes. Offline mock and recorded demo modes allow full execution without live API keys.

---

## Quick Start

### 1. Setup Environment
```bash
# Clone and enter repo
cd TerraWatch

# Install dependencies (requires uv or standard pip)
uv pip install -r requirements.txt
```

### 2. Run Test Suite
```bash
uv run pytest
# 60 unit and integration tests passing in < 0.5s
```

### 3. Run Agent CLI (Offline Mock Mode)
```bash
# Instant terminal dashboard report
TERRAWATCH_MODE=mock uv run python -m agent "Cairo"

# Pipe structured JSON report
TERRAWATCH_MODE=mock uv run python -m agent "Cairo" --json | jq .
```

### 4. Run Backend API Server
```bash
# Start FastAPI backend on port 8000
TERRAWATCH_MODE=mock uv run uvicorn apps.api.main:app --reload --port 8000
```
Open **[http://localhost:8000/docs](http://localhost:8000/docs)** for interactive Swagger UI.

---

## API Endpoints (`apps/api`)

All endpoints are prefixed with `/api` and support CORS for frontend integration:

| Method | Endpoint | Description | Sample Output |
|---|---|---|---|
| `GET` | `/api/health` | System health, telemetry, and runtime mode | `{"status": "ok", "mode": "mock", ...}` |
| `GET` | `/api/sources` | Metadata & live readiness for all 5 adapters | `{"total_sources": 5, "sources": [...]}` |
| `POST` | `/api/investigations` | Run full investigation asynchronously, persist to DB via SQLAlchemy, return report | `{"investigation_id": "inv_...", ...}` |
| `GET` | `/api/investigations/stream` | **SSE Stream**: Real-time event stream of investigation progress stages | `event: stage\ndata: {"stage": "geocoding", ...}\n\n` |
| `GET` | `/api/investigations` | Paginated history of investigations | `{"total": 12, "items": [...]}` |
| `GET` | `/api/investigations/{id}` | Full investigation report by ID | Complete `InvestigationReport` |
| `GET` | `/api/investigations/{id}/graph` | Evidence graph nodes and relationships | `{"nodes": [...], "relationships": [...]}` |
| `GET` | `/api/evidence/{id}` | Full raw evidence envelope + all observations | Raw `Evidence` (e.g. all hotspot GPS rows) |

### Trigger Investigation Example:
```bash
curl -X POST http://localhost:8000/api/investigations \
  -H "Content-Type: application/json" \
  -d '{
    "location": "Cairo",
    "question": "Is smoke from nearby agricultural fires reaching the city?",
    "sources": ["weather", "air_quality", "fire"]
  }'
```

### Real-Time SSE Streaming Example:
```bash
# Listen to live progression events (geocoding -> evidence collection -> geo analysis -> reasoning -> completed)
curl -N "http://localhost:8000/api/investigations/stream?location=Cairo"
```

---

## Storage & Database Layer

TerraWatch features a flexible persistence architecture in `apps/api/storage.py`:
- **SQLAlchemy 2.0 ORM & Async Engine**: Uses `AsyncSession` with `aiosqlite` for asynchronous non-blocking queries and background tasks.
- **Native SQLite Engine**: Preserves complete backward compatibility for synchronous workflows, scripts, and legacy tests.

---

## Docker Deployment

Build and run the production container locally:

```bash
# 1. Build Docker image
docker build -t terrawatch:latest .

# 2. Run container
docker run -d --name terrawatch -p 8000:8000 \
  -e TERRAWATCH_MODE=mock \
  terrawatch:latest

# 3. Check container logs & health
curl http://localhost:8000/api/health
```

## Data Sources & Adapters

| Source | Adapter | Upstream Provider | Cache TTL | Purpose |
|---|---|---|---|---|
| **Weather** | `WeatherAdapter` | Open-Meteo | 30 min | Wind speed, direction, temperature, gusts, precipitation |
| **Air Quality** | `AirQualityAdapter` | OpenAQ v3 (CAMS fallback) | 15 min | Real sensor PM2.5, 24h baseline history, anomaly ratio |
| **Fire** | `FireAdapter` | NASA FIRMS (VIIRS NOAA-20) | 2 hours | Thermal hotspots, FRP (fire radiative power), detection time |
| **Earthquake** | `EarthquakeAdapter` | USGS FDSN | 1 hour | Seismic events, magnitude, depth, distance |
| **Places / Geo** | `GeoAdapter` | Geoapify (OpenStreetMap) | 24 hours | Hospitals, schools, critical infrastructure proximity |
| **Geocode** | `GeocodeAdapter` | Geoapify / Open-Meteo | 7 days | Ambiguity-free geocoding (e.g. Cairo, Egypt vs Cairo, IL) |

---

## Environment Variables

For live mode execution, configure your API keys (optional — offline mock mode works out of the box):

```bash
# Set mode: live | mock | demo
export TERRAWATCH_MODE=live

# Data Upstream Keys
export OPENAQ_API_KEY="your-openaq-key"
export FIRMS_MAP_KEY="your-nasa-firms-key"
export GEOAPIFY_API_KEY="your-geoapify-key"

# Optional LLM Executive Synthesis Key
export GROQ_API_KEY="your-groq-key"

# Backend Settings (optional)
export TERRAWATCH_API_PORT=8000
export TERRAWATCH_DB_PATH="terrawatch.db"
```

---

## Live API Health & Verification Script

Verify upstream live connectivity or record demo fixtures:
```bash
# Hit live APIs for Cairo and print status per source
python -m scripts.live_check

# Record new demo fixtures for offline tests
python -m scripts.live_check --record
```
