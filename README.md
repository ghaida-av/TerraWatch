# TerraWatch 🌍🛰️ — Environmental Crisis Intelligence

```
TerraWatch/
├── apps/api/         FastAPI HTTP layer: routes, storage, and config
├── agent/            investigator + H-MEM memory + LLM reasoner (explains, never calculates)
├── agent/llm.py      Power: Meterless Nightshift Runtime provider (primary) + NVIDIA direct fallback
├── agent/memory.py   Build: H-MEM persistent investigation-memory engine
├── geo_analysis/     deterministic maths: distance, wind, risk score, evidence graph
├── data/             5 adapters (FIRMS, OpenAQ, Open-Meteo, USGS, OSM) + global earthquake feed
├── tests/            backend test suite
├── smoke_test.py     hackathon "Verify your setup" all-in-one check
└── frontend/         React + Vite + Tailwind (feature-based modules)
    └── src/           app · core · store · shared · features
```

## Run (two terminals)
```bash
# 1) Backend
pip install -r requirements.txt
TERRAWATCH_MODE=live python -m uvicorn apps.api.main:app --reload --port 8000   # live USGS earthquake feed; no key required

# 2) Frontend
cd frontend
npm install
npm run dev        # http://localhost:5173  (proxies /api -> :8000)
```
Modes: `live` (real APIs), `demo` (recorded fixtures), `mock` (synthetic). The global earthquake monitor uses the public [USGS GeoJSON feed](https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson); country flags use the [BigDataCloud reverse-geocoding endpoint](https://www.bigdatacloud.com/free-api/free-reverse-geocode-to-city-api) and neither requires an API key. If USGS is unreachable in live mode, the monitor shows an error instead of substituting synthetic events. Other investigation sources may use `OPENAQ_API_KEY`, `FIRMS_MAP_KEY`, or `GEOAPIFY_API_KEY`.

## Add a new screen (frontend)
1. Create `src/features/<name>/<Name>Page.jsx`
2. Add one line in `src/shared/layout/nav.js` and one `<Route>` in `src/app/router.jsx`

## API (all under `/api`)
`GET /health` · `GET /sources` · `GET /monitor/events?window=day&min_mag=2.5` (new) · `POST /investigations` · `GET /investigations/stream` (SSE) · `GET /investigations` · `GET /investigations/{id}` · `GET /investigations/{id}/graph` · `GET /evidence/{id}`

## Meterless integration (Open Agent Hackathon 2026)

**Power — Meterless Nightshift as the primary AI provider.** Every investigation's executive summary is
written through the Nightshift Runtime (`agent/llm.py`, typically an NVIDIA **Nemotron** lane, e.g.
`nvidia/nemotron-3.5-bolt-e4b`). The app only needs the Console-provided Runtime URL + token; the NVIDIA
key itself lives in Nightshift's Providers tab. Runtime contract used: `Authorization: Bearer`,
`meterless-app: terrawatch`, `meterless-scope: user`, `GET /v1/models`, `POST /v1/chat/completions`.

Provider settings (`.env`, gitignored — see `.env.example`):
```env
METERLESS_BASE_URL=http://127.0.0.1:8088/v1
METERLESS_RUNTIME_TOKEN=<nightshift-console-runtime-token>
METERLESS_MODEL=nvidia/nemotron-3.5-bolt-e4b
```
Failure handling: Nightshift unavailable → Groq (if `GROQ_API_KEY`) → deterministic summary; data analysis
always stays in Python (`geo_analysis/`), the LLM only explains verified metrics (guardrail-checked).

**Build — H-MEM engine (persistent investigation memory).** `agent/memory.py` gives the agent memory
across sessions: after each investigation it stores a fact sheet per location (SQLite,
`TERRAWATCH_MEMORY_DB`); later investigations of the same or nearby location (≤50 km) recall it, and the
facts appear as `memory:` findings and inside the Nemotron summary prompt. Disable with
`TERRAWATCH_MEMORY=0`. See `tests/test_memory.py` for the cross-session conformance test.

**Verify (Nightshift must be running):**
```bash
.venv/bin/python smoke_test.py   # 3x PASS: data pipeline · H-MEM round-trip · Nemotron via Nightshift
```
Submission evidence: `docs/meterless-evidence.txt`. Contributor notes: `AGENTS.md`.
