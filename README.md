# TerraWatch 🌍🛰️ — Environmental Crisis Intelligence

```
TerraWatch/
├── apps/api/         FastAPI HTTP layer: routes, storage, and config
├── agent/            investigator + LLM reasoner (explains, never calculates)
├── geo_analysis/     deterministic maths: distance, wind, risk score, evidence graph
├── data/             5 adapters (FIRMS, OpenAQ, Open-Meteo, USGS, OSM) + global earthquake feed
├── tests/            backend test suite
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

Contributor notes: `AGENTS.md`.
